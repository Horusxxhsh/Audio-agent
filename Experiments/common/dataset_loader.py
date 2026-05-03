import sqlite3
import json
import os
import unicodedata

# Paths to databases (Relative to this script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DB_PATH = os.path.join(BASE_DIR, '..', '..', 'music_info.db')
AUDIO_DB_PATH = os.path.join(BASE_DIR, '..', '..', 'audio_info.db')

def _resolve_local_audio_paths(dataset):
    """
    Best-effort mapping from SongName -> local audio file in Data/Audio_Synthetic/.

    This keeps experiment scripts robust when the dataset JSON contains Windows paths
    or missing AudioPath values.
    """
    base_audio_dir = os.path.join(BASE_DIR, '..', '..', 'Data', 'Audio_Synthetic')
    if not os.path.exists(base_audio_dir):
        return dataset

    for item in dataset:
        song_name = item.get("SongName")
        if not song_name:
            continue

        # Keep existing path if it already points to a real file.
        cur = item.get("AudioPath")
        if cur and os.path.exists(cur):
            continue

        def sanitize(name: str) -> str:
            # Match the synthetic audio generator's filename logic (remove slashes, punctuation, etc.).
            return "".join([c for c in name if c.isalpha() or c.isdigit() or c in (" ", "-", "_")]).strip()

        def add_unicode_forms(paths, filename: str) -> None:
            for form in {
                filename,
                unicodedata.normalize("NFC", filename),
                unicodedata.normalize("NFD", filename),
            }:
                paths.append(os.path.join(base_audio_dir, form))

        candidates = []

        # 1) If AudioPath is a Windows-like absolute path, map by basename.
        # Example: "C:\\...\\Data\\Audio_Synthetic\\Dry Funk.wav" -> "<repo>/Data/Audio_Synthetic/Dry Funk.wav"
        if isinstance(cur, str) and cur:
            base = cur.replace("\\", "/").split("/")[-1]
            if base.lower().endswith(".wav"):
                add_unicode_forms(candidates, base)

        # 2) Map by SongName.
        safe_name = sanitize(str(song_name))
        add_unicode_forms(candidates, f"{safe_name}.wav")
        add_unicode_forms(candidates, f"{song_name}.wav")

        manual_aliases = {
            "Brown Sound Modern": ["Brown Sound.wav"],
            "Rotary Speaker Fast": ["Rotary Speaker.wav"],
        }
        for alias in manual_aliases.get(str(song_name), []):
            add_unicode_forms(candidates, alias)

        # 3) Many held-out queries are deterministic name variants ("<Base> - <Suffix>") that reuse the same audio.
        if " - " in str(song_name):
            base_name = str(song_name).split(" - ", 1)[0].strip()
            if base_name:
                safe_base = sanitize(base_name)
                candidates.extend(
                    [
                        os.path.join(base_audio_dir, f"{safe_base}.wav"),
                        os.path.join(base_audio_dir, f"{base_name}.wav"),
                    ]
                )
        for c in candidates:
            if os.path.exists(c):
                item["AudioPath"] = c
                break
        else:
            # Ensure missing paths don't silently remain as invalid strings (e.g., Windows paths on macOS).
            item["AudioPath"] = None

    return dataset


def load_and_merge_data():
    """
    Loads data. 
    OPTIMIZED: Prefers a unified dataset JSON if available.
    Otherwise merges from DBs.
    """
    # 1) Prefer explicit override (useful for large external datasets)
    env_json_path = (os.environ.get("AUDIO_AGENT_DATASET_JSON") or "").strip()
    if env_json_path:
        if not os.path.exists(env_json_path):
            raise FileNotFoundError(f"AUDIO_AGENT_DATASET_JSON not found: {env_json_path}")
        print(f"Loading data from AUDIO_AGENT_DATASET_JSON: {env_json_path}")
        with open(env_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _resolve_local_audio_paths(data)

    # 2) Prefer the local external dataset drop-in if present
    external_json_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "Data",
        "External_1267_211",
        "dataset",
        "dataset_full_vectors_1267.json",
    )
    if os.path.exists(external_json_path):
        print(f"Loading data from external dataset JSON: {external_json_path}")
        with open(external_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _resolve_local_audio_paths(data)

    # 3) Try repo JSON (default small/synth dataset)
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "Experiments", "dataset_full_vectors.json")
    if os.path.exists(json_path):
        print(f"Loading data from optimized JSON: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _resolve_local_audio_paths(data)

    # 2. Fallback to DB Merge
    """
    Loads data from music_info.db and audio_info.db.
    Fallback strategy: Merge by INDEX (Offset 11) because exact parameter matching failed.
    Assumes Music[0] corresponds to Audio[11] (first new imported record).
    """
    if not os.path.exists(MUSIC_DB_PATH) or not os.path.exists(AUDIO_DB_PATH):
        print("Error: Database files not found.")
        return []

    # Load from music_info.db
    # Schema: SongName, Parameters, Preferences, Style, Feature
    conn_music = sqlite3.connect(MUSIC_DB_PATH)
    cursor_music = conn_music.cursor()
    cursor_music.execute("SELECT SongName, Parameters, Style, Feature FROM music_responses ORDER BY rowid")
    music_data = cursor_music.fetchall()
    conn_music.close()

    # Load from audio_info.db
    # Schema: Parameters, Vector
    conn_audio = sqlite3.connect(AUDIO_DB_PATH)
    cursor_audio = conn_audio.cursor()
    cursor_audio.execute("SELECT Parameters, Vector FROM audio_vector ORDER BY rowid")
    audio_data = cursor_audio.fetchall()
    conn_audio.close()

    merged_dataset = []
    
    # Offset calculation: 
    # Audio has 61 records. Music has 50.
    # Assuming the last 50 Audio records correspond to the 50 Music records.
    # Start index for Audio = 61 - 50 = 11.
    audio_start_idx = len(audio_data) - len(music_data)
    if audio_start_idx < 0:
        audio_start_idx = 0 # Should not happen if assumption holds
        
    print(f"Merging by Index. Music: {len(music_data)}, Audio: {len(audio_data)}. Offset: {audio_start_idx}")

    for i in range(len(music_data)):
        song_name, params_str, style_db, feature_db = music_data[i]
        
        # Audio pairing
        audio_idx = audio_start_idx + i
        if audio_idx >= len(audio_data):
            break
            
        audio_params_str, vector_str = audio_data[audio_idx]
        
        # Parse logic
        def parse_json(s):
            if isinstance(s, str):
                try: return json.loads(s)
                except: return {}
            return s
            
        params_obj = parse_json(params_str)
        # Vector parsing handled in consumer or here? 
        # Consumer expects string or list. Let's keep consistent.
        
        # Parse Style/Feature (stored as JSON strings usually or comma lists?)
        # In DB text: "['Rock', 'Metal']" -> Need to parse safely.
        # Simple eval or json load if strict JSON.
        # Assuming they are likely string representations of lists.
        # For robustness, we treat them as strings if parsing fails.
        
        def parse_list(s):
            if not s: return []
            try: return json.loads(s.replace("'", '"')) # Fix single quotes common in python str repr
            except: 
                # fallback split by comma
                return [x.strip() for x in str(s).split(',')]

        merged_dataset.append({
            "SongName": song_name,
            "Parameters": params_obj,
            "Style": parse_list(style_db),
            "Feature": parse_list(feature_db),
            "Vector": vector_str # Keep as string or parse?
        })

    print(f"Merged {len(merged_dataset)} records.")
    
    # Optional: Resolve Local Audio Paths
    # Prioritize Synthetic Data for TRR Experiment
    merged_dataset = _resolve_local_audio_paths(merged_dataset)

    return merged_dataset

if __name__ == "__main__":
    data = load_and_merge_data()
    if data:
        print("Sample record:", json.dumps(data[0], indent=2))
