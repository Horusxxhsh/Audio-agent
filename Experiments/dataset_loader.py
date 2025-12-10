import sqlite3
import json
import os

# Paths to databases (Relative to this script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DB_PATH = os.path.join(BASE_DIR, '..', 'music_info.db')
AUDIO_DB_PATH = os.path.join(BASE_DIR, '..', 'audio_info.db')

def load_and_merge_data():
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
    return merged_dataset

if __name__ == "__main__":
    data = load_and_merge_data()
    if data:
        print("Sample record:", json.dumps(data[0], indent=2))
