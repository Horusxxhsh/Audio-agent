from asyncio.windows_events import NULL
from email.mime import audio
from pickle import FLOAT
import sys
import json
import sqlite3
import math
from networkx import preferential_attachment
from openai import OpenAI
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import numpy as np
import tempfile
import time
import scipy.io.wavfile

# --- Local MusicGen Configuration (using transformers library) ---
USE_LOCAL_MUSICGEN = True
MUSICGEN_MODEL_NAME = "facebook/musicgen-small"  # Options: small, medium, large
MUSICGEN_DURATION = 8  # seconds (max_new_tokens = duration * 50)

# Lazy-loaded model references
_musicgen_model = None
_musicgen_processor = None

def get_local_musicgen_model():
    """Load MusicGen model using transformers library (better Windows compatibility)"""
    global _musicgen_model, _musicgen_processor
    if _musicgen_model is None:
        try:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            print(f"Loading local MusicGen model: {MUSICGEN_MODEL_NAME}...")
            _musicgen_processor = AutoProcessor.from_pretrained(MUSICGEN_MODEL_NAME)
            _musicgen_model = MusicgenForConditionalGeneration.from_pretrained(MUSICGEN_MODEL_NAME)
            
            # Move to GPU if available
            if torch.cuda.is_available():
                _musicgen_model = _musicgen_model.to("cuda")
                print("MusicGen model loaded on GPU.")
            else:
                print("MusicGen model loaded on CPU (slower).")
        except ImportError as e:
            print(f"ERROR: transformers library issue: {e}")
            print("Run: pip install transformers scipy")
            return None, None
        except Exception as e:
            print(f"ERROR loading MusicGen model: {e}")
            return None, None
    return _musicgen_model, _musicgen_processor

def generate_audio_local(prompt, output_path):
    """Generate audio using local MusicGen model via transformers"""
    model, processor = get_local_musicgen_model()
    if model is None or processor is None:
        print("ERROR: Model or processor is None, cannot generate audio.")
        return False
    
    try:
        print(f"Generating audio for prompt: {prompt}")
        
        # Prepare inputs
        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )
        
        # Move to same device as model
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generate audio (duration * 50 tokens per second)
        max_new_tokens = MUSICGEN_DURATION * 50
        print(f"Generating {MUSICGEN_DURATION} seconds of audio...")
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)
        
        # Get sampling rate from model config
        sampling_rate = model.config.audio_encoder.sampling_rate
        print(f"Sampling rate: {sampling_rate}")
        
        # Convert to numpy - take first batch, first channel
        audio_data = audio_values[0, 0].cpu().numpy()
        print(f"Audio shape: {audio_data.shape}, dtype: {audio_data.dtype}")
        
        # Normalize to float32 range [-1, 1] for scipy
        audio_data = audio_data.astype(np.float32)
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95  # Normalize with some headroom
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        # Save using scipy
        scipy.io.wavfile.write(output_path, rate=int(sampling_rate), data=audio_data)
        
        if os.path.exists(output_path):
            print(f"Audio saved successfully to: {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
        else:
            print("ERROR: File was not created!")
            
        return True
    except Exception as e:
        print(f"Error generating audio: {e}")
        import traceback
        traceback.print_exc()
        return False

def safe_write_binary_file(filename, content):
    try:
        with open(filename, 'wb') as f:
            f.write(content)
            print(f"Audio file saved to current directory: {os.path.abspath(filename)}")
    except (IOError, PermissionError):
        try:
            docs_dir = os.environ.get('DOCUMENTS_DIR')
            if docs_dir:
                full_path = os.path.join(docs_dir, filename)
                with open(full_path, 'wb') as f:
                    f.write(content)
                print(f"Audio file saved to documents directory: {full_path}")
        except Exception as e:
            print(f"Failed to save audio file: {e}")
def safe_write_file(filename, content):
    try:
        # First try to write in current directory
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f"File saved to current directory: {os.path.abspath(filename)}")
    except (IOError, PermissionError):
        try:
            # If failed, try to write in documents directory specified by environment variable
            docs_dir = os.environ.get('DOCUMENTS_DIR')  # Get environment variable

            if docs_dir:
                full_path = os.path.join(docs_dir, filename)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"File saved to documents directory: {full_path}")
            else:
                # If environment variable doesn't exist, throw exception to enter next attempt
                raise FileNotFoundError("Environment variable DOCUMENTS_DIR not set")

        except (IOError, PermissionError, FileNotFoundError):
            # If still failed, try to write in system temporary directory
            temp_dir = tempfile.gettempdir()
            full_path = os.path.join(temp_dir, filename)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"File saved to temporary directory: {full_path}")

# Define Jaccard similarity function
def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

# Improved tag similarity calculation function considering semantic similarity and weights
def enhanced_tag_similarity(target_tags, hist_tags):
    """Enhanced tag similarity calculation considering semantic similarity and weights"""
    if not target_tags or not hist_tags:
        return 0.0
    
    # Calculate basic Jaccard similarity
    base_similarity = jaccard_similarity(set(target_tags), set(hist_tags))
    
    # Calculate exact match count
    exact_matches = len(set(target_tags).intersection(set(hist_tags)))
    
    # Calculate semantic similarity (based on prefix/suffix matching of tags)
    semantic_matches = 0
    for target_tag in target_tags:
        for hist_tag in hist_tags:
            # If tags have common prefix or suffix
            if target_tag == hist_tag:
                semantic_matches += 1  # Exact match already counted, no double counting here
            elif (target_tag.replace('_rock', '') == hist_tag.replace('_rock', '')) or \
                 (target_tag.replace('_metal', '') == hist_tag.replace('_metal', '')) or \
                 (target_tag.replace('_rhythm', '') == hist_tag.replace('_rhythm', '')):
                semantic_matches += 0.5  # Partial semantic similarity
    
    # Comprehensive calculation: basic similarity accounts for 70%, semantic matching accounts for 30%
    enhanced_sim = base_similarity * 0.7 + (semantic_matches / max(len(target_tags), len(hist_tags))) * 0.3
    
    return enhanced_sim


# Define text similarity function
def text_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

def audio_to_vector(file_path):
    # Load pre-trained processor and model
    processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h")

    # Load audio file (librosa default sample rate is 22050Hz, wav2vec2 usually expects 16000Hz)
    audio, sample_rate = librosa.load(file_path, sr=16000)

    # Preprocess audio: convert to input features
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

    # Get model output (without computing gradients for efficiency)
    with torch.no_grad():
        outputs = model(**inputs)

    # outputs.last_hidden_state is sequence-level features, shape [1, seq_len, hidden_size]
    # Can get vector representation of entire audio through averaging etc.
    audio_vector = outputs.last_hidden_state.mean(dim=1).squeeze()

    return audio_vector.numpy()  # Convert to numpy array and return


# Use fixed C path to connect to database
db_dir = os.environ.get('SUPERTONAL_DIR')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)  # Create directory if it doesn't exist
db_path = os.path.join(db_dir, "music_info.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Connect to external audio information database
audio_db_path = os.path.join(db_dir, "audio_info.db")
audio_conn = sqlite3.connect(audio_db_path)
audio_cursor = audio_conn.cursor()
"""
# Drop table
try:
    cursor.execute("DROP TABLE IF EXISTS music_responses")
    conn.commit()
    print("Table 'music_responses' has been dropped successfully.")
except sqlite3.Error as e:
    print(f"An error occurred while dropping the table: {e}")
"""
# Modify table structure, keep only required columns
cursor.execute('''
CREATE TABLE IF NOT EXISTS music_responses (
    SongName TEXT PRIMARY KEY,
    Parameters TEXT,
    Preferences TEXT,
    Style TEXT,
    Feature TEXT 
)
''')
conn.commit()

# Check if audio_vector table exists, create if not
audio_cursor.execute('''
CREATE TABLE IF NOT EXISTS audio_vector (
    Parameters TEXT PRIMARY KEY,
    Vector TEXT
)
''')
audio_conn.commit()

client = OpenAI(api_key="sk-0705951d960041ed96c607ab69724d0d", base_url="https://api.deepseek.com")

import platform

if len(sys.argv) > 1:
    if platform.system() == "Windows":
        print(f"sys.argv: {len(sys.argv)}")
        # Windows command line usually uses GBK encoding
        chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
        memoryEnabled = sys.argv[2]
        file_path = ""
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
        if len(sys.argv) == 4:
            file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
            text_Weight = ""
            preference_Weight = ""
            audio_Weight = ""
        if 4 < len(sys.argv) < 7:
            file_path = ""
            text_Weight = sys.argv[3]
            preference_Weight = sys.argv[4]
            audio_Weight = ""
        if len(sys.argv) > 6:
            file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
            text_Weight = sys.argv[4]
            preference_Weight = sys.argv[5]
            audio_Weight = sys.argv[6]
    else:
        # Linux/macOS usually uses UTF-8
        chat_message = sys.argv[1]
        memoryEnabled = sys.argv[2]
        file_path = ""
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
        if len(sys.argv) == 4:
            file_path = sys.argv[3]
            text_Weight = ""
            preference_Weight = ""
            audio_Weight = ""
        if 4 < len(sys.argv) < 7:
            file_path = ""
            text_Weight = sys.argv[3]
            preference_Weight = sys.argv[4]
            audio_Weight = ""
        if len(sys.argv) > 6:
            file_path = sys.argv[3]
            text_Weight = sys.argv[4]
            preference_Weight = sys.argv[5]
            audio_Weight = sys.argv[6]
else:
    chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
    memoryEnabled = sys.argv[2]
    file_path = ""
    text_Weight = ""
    preference_Weight = ""
    audio_Weight = ""
    if len(sys.argv) == 4:
        file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
    if 4 < len(sys.argv) < 7:
        file_path = ""
        text_Weight = sys.argv[3]
        preference_Weight = sys.argv[4]
        audio_Weight = ""
    if len(sys.argv) > 6:
        file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
        text_Weight = sys.argv[4]
        preference_Weight = sys.argv[5]
        audio_Weight = sys.argv[6]
print(f"Chat message: {chat_message}")
print(f"memoryEnabled: {memoryEnabled}")
print(f"text_Weight: {text_Weight}")
print(f"preference_Weight: {preference_Weight}")
print(f"audio_Weight: {audio_Weight}")
print(f"File path: {file_path}")
if file_path and file_path.strip():
    vector = audio_to_vector(file_path)
    print("Audio vector shape:", vector)
else:
    vector = None  # or empty list [], determine based on subsequent usage scenarios
    print("No valid file path provided, audio vector is empty")

# Create conversation history list
conversation_history = []
# Second system prompt (style and feature prompt)
system_prompt2 = f"""
You are a senior music analyst and style similarity search consultant. Based on user input (variable: {chat_message}) generate:
  1) Refined, structured style and technique tags (tags)
  2) Multiple English extended descriptions that incorporate user preferences and help search for "similar style songs"

(Multilingual enhanced version: supports Chinese, English, Japanese, Korean, Spanish/Portuguese/French/German/Russian song names or emotional descriptions)

==============================
Overall Goals
- tags: main style + sub-styles/textures + techniques/structural features; ≤6; search-oriented
- description: 2~6 English sentences; different dimensions; can include 1 token bundle; high information density, no redundancy

==============================
Stage 0 Input Initial Judgment
  - Classification: clear music / potentially music-related (emotions or mappable styles) / non-music
  - If clearly non-music → output {{ "tags": [], "description": [] }}
  - If only suspected song name (any language) → attempt song name recognition and style inference

==============================
Stage 1 Information Extraction (Extraction)
  A. General Extraction:
    - Songs / Artists (for internal reference only, not directly output names)
    - Styles / Substyles (post-rock, math_rock, jazz_fusion, shoegaze, dream_pop, city_pop, britpop, synthwave, vaporwave, gothic_metal, symphonic_metal, melodic_death_metal, bossa_nova_fusion, tango_nuevo, latin_rock, reggaeton, k_indie, j_rock, visual_keI (if strong visual kei hints, convert to japanese_alternative_rock + theatrical_aesthetic), k_pop_ballad, etc.)
    - Mood/Atmosphere: melancholic / uplifting / introspective / ethereal / brooding / nostalgic / cinematic / aggressive / dreamy, etc.
    - Era Signals: 80s/90s/2000s/modern (only when text or style significantly implies, e.g. city_pop → 80s inspired; synthwave → 80s retro; britpop → 90s; vaporwave → retro_digital)
    - Technique Words: tapping, sweep, legato, hybrid_picking, polyrhythm, syncopated, palm_mute, ambient_swells, fuzz, clean_arpeggios, layered_delays, reverse_reverb, sidechain_pulse, gated_reverb
    - Tone Words: clean, glassy, chimey, mid-gain, saturated, high-gain, fuzzy, reverb-drenched, modulated, tape_warmth, compressed, lo_fi, analog, shimmering
    - Rhythm/Tempo: slow, mid-tempo 100-110 bpm, fast, driving 120+, syncopated groove, straight 16ths, swung, polyrhythmic, halftime, reggaeton_dembow
    - Harmony/Mode: modal, aeolian melancholy, dorian tint, lydian lift, extended jazz chords, chromatic tension-release, droning pedal, pentatonic lyrical, harmonic_minor_color
    - Texture / Arrangement: layered guitars, sparse minimal space, dense wall-of-sound, shimmering delay pads, pulsating synth bass, atmospheric pads, rhythmic stabs, cinematic swells
  B. Multi-reference conflict handling: take main frequency + user emphasis; don't force fusion of conflicting styles unless text implies hybrid
  C. Pure emotion input mapping (cross-language): 
     - "lonely/cosmic/empty/cold/silent" → cinematic_ambient / atmospheric_post_rock / spacey_dream_pop
     - "heavy/oppressive/muddy" → doom / sludge / dark_post_metal
     - "rhythmic/dancing/beat" → funk_rock / disco_funk / groove_metal / nu_disco
     - "psychedelic/dreamy" → psychedelic_rock / space_rock / shoegaze / dream_pop
     - "complex/complicated/time signature changes/multi-layered" → math_rock / progressive_metal / polyrhythmic_fusion
     - "gentle/healing/therapeutic/comforting" → dreamy_ambient / clean_post_rock / soft_dream_pop / lofi_chill
     - "nostalgic/vintage" → retro_synthwave / city_pop_influence / vintage_analog_texture / nostalgic_90s_alt
  D. Multilingual emotion words (internal mapping, examples):
     - Japanese: setsunai=melancholic, natsukaかしい=nostalgic, gekishii=aggressive
     - Korean: 우울한=melancholic, 몽환적인=dreamy, 강렬한=intense
     - Spanish: melancólico=melancholic, atmosférico=atmospheric, bailable=danceable
     - Portuguese: sonhador=dreamy, pesado=heavy, suave=soft
     - French: rêveur=dreamy, nostalgique=nostalgic
     - German: melancholisch=melancholic, treibend=driving
     - Russian: мрачный=dark, атмосферный=atmospheric

==============================
Multilingual Song Name Recognition and Style Inference (Key Enhancement)
  1. Recognition: If input consists mainly of (Chinese / kana / Korean / Latin alphabet +少量标点/空格) and length 2~40, no clear regular sentence structure → prioritize as "song title fragment"
  2. Normalization:
     - Remove quotes, full-width spaces, ending particles, unify case
     - Remove common prefixes/suffixes (e.g. "song", "song", "lyrics", "lyric", "cover")
     - Japanese kana: katakana → hiragana normalization; can be used for fuzzy matching internally
     - Remove accents and diacritics (áàäâ→a, ñ→n, ü→u)
  3. Fuzzy matching strategy (internal):
     - Levenshtein distance ≤ max(1, title length*0.15) considered suspicious hit
     - After removing stop symbols, trigram Jaccard ≥0.72 considered suspicious hit
     - Chinese/Japanese/Korean: by character bigram; Latin languages: by substring without spaces and n-grams
  4. External injectable dictionary (if exists, variable: {{multilingual_song_dict}}):
     - Structure suggestion:
       {{
         "zh": {{"Grey Track": {{"artist":"Beyond","style_hints":["cantonese_rock","melodic_emotional_rock"]}}}},
         "ja": {{"cruelなtenshiのテーゼ": {{"style_hints":["anime_theme","90s_j_rock","anthemic"]}}}},
         "ko": {{"너의 의미": {{"style_hints":["k_pop_ballad","soft_acoustic"]}}}},
         "es": {{"despacito": {{"style_hints":["latin_pop","reggaeton","tropical_influence"]}}}}
       }}
     - If not injected, use internal common high-frequency list (not externally visible)
  5. High confidence hit:
     - Use style_hints to extract search tags (do not output artist names)
     - If style_hints contain regional/era/structural features, choose 1~2 most distinctive as tag prefixes
  6. Low confidence or conflict:
     - Don't invent specific songs; use emotion + texture generalization instead
  7. Never write actual artist names directly in output description (maintain generalizable search)

==============================
Cross-lingual Style Inference Supplement (use only when text or mapping implies):
  - city_pop: smooth_groove, soft_fusion_chords, retro_80s_gloss
  - j_rock / japanese_alternative_rock: melodic hooks + emotive anthemic lift
  - shoegaze: washed_fuzzy_layers, reverb_drenched_wall, hazy_vocals
  - dream_pop: lush_airy_textures, soft_etherial_pads
  - k_indie: intimate_clean_tones, mellow_midtempo
  - latin_rock / latin_pop: rhythmic_percussion_layers, syncopated_groove, bright_melodic
  - reggaeton: dembow_pattern, syncopated_percussion, tropical_atmosphere
  - bossa_nova_fusion: soft syncopated jazz-influenced chords, gentle swing
  - nordic_melodeath: melodic_harmonic_minor_riffs + driving double_kick (only when clear extreme metal signals)
  - synthwave: retro_analog_synths, steady_four_on_floor, neon_atmosphere
  - vaporwave: lo_fi_sampled_loops, detuned_retro, slowed_reverbed_aesthetic

==============================
Stage 2 Style Inference (Genre Inference)
  - Based on extraction & multilingual inference: give 1~3 specific directions (prefer specific subdivisions over broad)
  - Allow regional/era + texture combinations: e.g. cantonese_melodic_rock, 90s_britpop_atmospheric, retro_synthwave, latin_pop_reggaeton, japanese_dream_pop
  - Insufficient signals: can use broad+texture (ambient_dreamy, dark_atmospheric, melodic_clean)

==============================
Stage 3 Tag Construction (Tags)
  Rules:
    1. Quantity ≤6
    2. Lowercase letters/numbers/underscores/dashes
    3. Order: main/core style → substyles/regions/eras → textures/techniques (ambient_swells, layered_textures, polyrhythmic_pulse, melodic_emotion, fuzzy_wall, clean_arpeggios, syncopated_groove)
    4. No duplicates; don't create very narrow tags not implied
    5. High confidence song match: include most distinctive regional or style tags (≤2); avoid only "rock"
    6. Insufficient information: tags=[]

==============================
Stage 4 English Extended Search Descriptions (Descriptions for Similarity Retrieval)
  - 2~6 sentences; each 14~30 English words (very little info can be ≥10)
  - Each sentence has different focus, can combine dimensions:
     * Style / Subgenre Layering
     * Mood & Emotional Color
     * Tempo & Rhythmic Feel
     * Harmonic / Modal Traits
     * Texture & Arrangement
     * Instrument Roles
     * Tone & Production
     * Dynamic / Structural Arc
     * Abstract Influence Qualifiers
     * Token Bundle (1 sentence can use comma-separated dense tokens)
  - No Chinese / no actual artist names
  - No repeated sentence templates
  - If still missing information: at least 1 contains "general stylistic inference"
  - Token bundle example format:
     "melodic cantonese rock, emotional mid-gain guitars, clean-crunch layering, moderate tempo, lyrical phrasing, gradual lift"

==============================
Stage 5 Quality & Compliance Check
  - Remove duplicate sentences
  - No Chinese, no unclosed quotes, no artist names
  - If cannot determine musical features → output {{ "tags": [], "description": [] }}

==============================
Hallucination Prevention & Constraints
  - Don't infer highly specific subgenres based on single emotion words
  - No rhythm/multiple rhythm hints → don't write polyrhythmic_pulse
  - No heavy distortion → don't write death_metal / djent, etc.
  - Multilingual titles not in mapping/dictionary and no context → don't create fictional styles
  - Don't misinterpret common words as song names (e.g. "love", "rain" alone → treat as emotion/theme unless format strongly indicates title)

==============================
External Injectable Resources (Optional)
  - {{multilingual_song_dict}} if exists:
    * Priority use its style_hints to strengthen tags
    * If no match, use normal inference
  - Future expansion {{style_alias_map}} to map user common terms to standard tags (internal: {{"shoegazing":"shoegaze","mathrock":"math_rock"}})

==============================
Output Format (Only Legal)
{{
  "tags": ["tag1","tag2"],
  "description": ["sentence 1","sentence 2"]
}}

==============================
Execution
  - Complete analysis based on {chat_message}, output only final JSON

"""

user_prompt2 = f"""
Please based on: {chat_message},
1. Analyze its specific music style (as detailed as possible).
2. Generate tags (English, lowercase, specific).
3. Describe possible guitar solo playing characteristics in English (array format, 2~6 sentences).

Only output JSON (with keys: tags, description), no other text.
"""

# Save system message
system_message = {"role": "system", "content": system_prompt2}
conversation_history.append(system_message)
# Save user message
user_message = {"role": "user", "content": user_prompt2}
conversation_history.append(user_message)
# Send request
response2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
# Save assistant reply
assistant_message = {
    "role": "assistant",
    "content": response2.choices[0].message.content
}
conversation_history.append(assistant_message)

# Get response2 response data and convert to JSON
response_content2 = response2.choices[0].message.content
# Remove code block markers and newlines from front and back
cleaned_content2 = response_content2.replace("```json", "").replace("```", "").strip()
try:
    result2 = json.loads(cleaned_content2)
    result2_str = json.dumps(result2, ensure_ascii=False)
    # Get song style
    song_style = result2.get("tags", [])
    # Get guitar playing characteristics
    guitar_features = result2.get("description", [])
    # Print information
    print(f"Style: {song_style}")
    print(f"Guitar playing characteristics: {guitar_features}")
except json.JSONDecodeError:
    print(f"Error: Invalid JSON response: {cleaned_content2}")
    sys.exit(1)

effectors = [
    {
        "name": "compression",
        "example_with": '{"CompressorOn":{"Threshold":-24.0,"Ratio":4.0,"Attack":0.012,"Release":0.180,"Makeup":6.0,"Mix":0.85}}',
        "prompt_with": (
            f"Based on style tags (if generated): {song_style} and original description: {chat_message}."
            "Task: Generate compressor settings JSON for guitar or main bus (judge based on semantics)."
            "\nParameter requirements:"
            "\n1) Threshold (-128.00~0.00 dB, more aggressive=lower value; clear and dynamic preservation=higher -20~-10; heavy compression= -40~-25 or lower)."
            "\n2) Ratio (1~100, gentle:1.5~3; normal control:3~6; high control/modern metal:6~12; limiter compression:>12)."
            "\n3) Attack (0.00~1.00 ms, smaller value=faster. Preserve transient=slightly amplified ~0.10~0.30; metal high density=very fast <0.05; if creating breathing feeling can appropriately slow down >0.30)."
            "\n4) Release (0.00~1.00 ms, simulating 'second decimal' concept, relatively longer than Attack; smooth natural=0.10~0.30; pumping feel=0.05~0.12; longer for continuous atmosphere 0.30~0.60)."
            "\n5) Makeup (-128.00~64.00 dB, compensate gain reduction from compression. Light compression 2~6 dB; strong compression 8~14; if threshold very low, appropriately increase)."
            "\n6) Mix (0.00~1.00 parallel compression mix, preserve dynamic=0.5~0.8; aggressive dense=0.9~1.0; transparent preserve original=0.3~0.5)."
            "\nLogic mapping guide:"
            "\n- 'ambient, atmospheric, post-rock, cinematic': relatively mild threshold(>-30), lower Ratio(2~4), medium slower Attack to preserve transient, longer Release, higher Mix parallel for original sound."
            "\n- 'progressive_metal, djent, modern metal': low threshold(-45~-30), high Ratio(6~10+), very fast Attack, faster Release to prevent dragging, higher Makeup."
            "\n- 'blues, vintage, expressive': medium threshold(-28~-20), Ratio 2~4, moderate Attack(0.10~0.25), medium natural Release, appropriate Makeup, Mix 0.6~0.8."
            "\n- If tags mainly point to 'dynamic, touch, expressive', avoid excessive compression."
            "\n- If style cannot be determined, use neutral setting: Threshold -24, Ratio 3, Attack 0.08, Release 0.18, Makeup 4, Mix 0.7."
            "\nOutput: only return JSON:"
            '\n{"CompressorOn":{"Threshold":<float>,"Ratio":<float>,"Attack":<float>,"Release":<float>,"Makeup":<float>,"Mix":<float>}}'
            "\nEnsure values are within range, keep 2~3 decimal places, no extra text."
        )
    },
    {
        "name": "distortion",
        "example_with": '{"DriverOn":{"Distortion":0.70,"Volume":-18.4}}',
        "prompt_with": (
            f"Based on style tags {song_style} and original description {chat_message}, generate distortion parameters."
            "\nParameters: Distortion 0.00~1.00 (drive strength), Volume -64.0~0.0 dB (output compensation)."
            "\nStyle mapping:"
            "\n- 'high gain metal / djent / modern shred': Distortion 0.75~0.95; Volume moderately negative compensation based on chain (-24~-12)."
            "\n- 'classic rock / blues rock': Distortion 0.40~0.65; Volume -18~-6。"
            "\n- 'fusion / expressive mid-gain': Distortion 0.45~0.60; Volume -12~-4。"
            "\n- 'ambient / clean emphasis': Distortion 0.05~0.25; Volume -6~-2。"
            "\n- If followed by overdrive (screamer / overdrive / boost semantics), Distortion slightly converges here."
            "\nIf insufficient information, use neutral: Distortion 0.55, Volume -12。"
            '\nOutput JSON: {"DriverOn":{"Distortion":<float>,"Volume":<float>}}'
            "\nOnly output JSON, valid values, 2~3 decimal places."
        )
    },
    {
        "name": "overload",
        "example_with": '{"ScreamerOn":{"Drive":0.82,"Tone":0.55,"Level":-18.3}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message}, generate overload (Screamer type) parameters."
            "\nParameter range: Drive 0.00~1.00; Tone 0.00~1.00 (focus on mid-high frequency bite); Level -64.00~0.00 dB。"
            "\nStyle mapping:"
            "\n- Used as preamp tighten (metal, djent): Drive 0.25~0.45, Tone 0.55~0.70, Level -18~-8。"
            "\n- Lead boost sustain (fusion / prog lead): Drive 0.50~0.70, Tone 0.50~0.62, Level -14~-6。"
            "\n- Vintage/Blues: Drive 0.55~0.80, Tone 0.40~0.55, Level -10~-4。"
            "\n- Only slight edge: Drive 0.20~0.35, Tone 0.45~0.55, Level -12~-6。"
            "\nNeutral fallback: Drive 0.60, Tone 0.52, Level -12。"
            '\nOutput JSON: {"ScreamerOn":{"Drive":<float>,"Tone":<float>,"Level":<float>}}'
            "\nJSON only, no explanation."
        )
    },
    {
        "name": "delay",
        "example_with": '{"DelayOn":{"Feedback":0.32,"Delay":380.0,"Mix":0.42}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message}, generate delay parameters."
            "\nParameters: Feedback 0.00~1.00; Delay 1.00~400.00 ms; Mix 0.00~1.00。"
            "\nStyle mapping:"
            "\n- 'ambient / post-rock / cinematic': Delay 300~400ms (1/2 or dotted 1/4 feel), Feedback 0.45~0.70, Mix 0.35~0.55。"
            "\n- 'modern lead sustain': Delay 280~360ms, Feedback 0.30~0.50, Mix 0.25~0.40。"
            "\n- 'tight rhythmic / prog metal': Delay 90~160ms (slap / support), Feedback 0.18~0.30, Mix 0.12~0.25。"
            "\n- 'blues/expressive subtle': Delay 180~260ms, Feedback 0.22~0.38, Mix 0.15~0.28。"
            "\nNeutral default: Delay 320ms, Feedback 0.35, Mix 0.30。"
            '\nOutput JSON: {"DelayOn":{"Feedback":<float>,"Delay":<float>,"Mix":<float>}}'
            "\nValues 2~3 decimal places, JSON only."
        )
    },
    {
        "name": "reverb",
        "example_with": '{"ReverbOn":{"Size":0.40,"Damping":0.32,"Width":0.70,"Mix":0.36}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message}, generate reverb parameters."
            "\nParameter range: Size 0.00~1.00 (space scale), Damping 0.00~1.00 (high frequency absorption), Width 0.00~1.00 (stereo expansion), Mix 0.00~1.00。"
            "\nStyle mapping:"
            "\n- 'ambient / cinematic / atmospheric_post_rock': Size 0.65~0.90, Damping medium(0.40~0.60), Width 0.70~0.95, Mix 0.40~0.60。"
            "\n- 'tight prog / metal lead': Size 0.25~0.45, Damping 0.35~0.55, Width 0.55~0.75, Mix 0.18~0.32。"
            "\n- 'vintage blues / classic rock': Size 0.30~0.55, Damping 0.45~0.70, Width 0.50~0.70, Mix 0.20~0.35。"
            "\n- 'fusion articulate': Size 0.25~0.40, Damping 0.30~0.50, Width 0.55~0.75, Mix 0.15~0.28。"
            "\nDefault neutral: Size 0.40, Damping 0.32, Width 0.70, Mix 0.30。"
            '\nOutput JSON: {"ReverbOn":{"Size":<float>,"Damping":<float>,"Width":<float>,"Mix":<float>}}'
            "\nJSON only."
        )
    },
    {
        "name": "chorus",
        "example_with": '{"ChorusOn":{"Delay":0.028,"Depth":0.30,"Frequency":0.55,"Width":0.032}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message} generate Chorus parameters."
            "\nParameter range: Delay 0.010~0.050; Depth 0.00~1.00; Frequency 0.05~2.00; Width 0.010~0.050."
            "\nStyle mapping:"
            "\n- '80s vibe / ambient shimmer': Depth 0.45~0.70, Delay 0.028~0.040, Frequency 0.25~0.60, Width 0.030~0.045."
            "\n- 'subtle thickening (modern lead)': Depth 0.15~0.35, Delay 0.022~0.030, Frequency 0.35~0.85, Width 0.020~0.032."
            "\n- 'clean melodic chorus pop': Depth 0.35~0.55, Delay 0.030~0.042, Frequency 0.40~0.90, Width 0.028~0.040."
            "\n- 'avoid modulation (dry preference)': Depth <0.12, Mix can be controlled by backend (Mix field not included here)."
            "\nDefault: Delay 0.028, Depth 0.30, Frequency 0.55, Width 0.032."
            '\nOutput JSON: {"ChorusOn":{"Delay":<float>,"Depth":<float>,"Frequency":<float>,"Width":<float>}}'
            "\nJSON only."
        )
    },
    {
        "name": "flanger",
        "example_with": '{"FlangerOn":{"Delay":0.012,"Depth":0.40,"Feedback":0.22,"Frequency":0.55,"Width":0.012}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message} generate Flanger parameters."
            "\nParameters: Delay 0.00100~0.02000; Depth 0.00~1.00; Feedback 0.00~0.50; Frequency 0.05~2.00; Width 0.001~0.020."
            "\nStyle mapping:"
            "\n- 'dramatic jet / classic flanger sweep': Depth 0.55~0.85, Feedback 0.30~0.45, Delay 0.010~0.016."
            "\n- 'subtle movement for ambient': Depth 0.15~0.35, Feedback 0.08~0.20, Delay 0.006~0.012, Frequency 0.15~0.40."
            "\n- 'rhythmic metallic texture': Depth 0.35~0.55, Feedback 0.18~0.30, Frequency 0.50~0.90."
            "\n- 'minimal coloring': Depth 0.08~0.18, Feedback 0.05~0.12, Frequency 0.20~0.50."
            "\nDefault: Delay 0.012, Depth 0.40, Feedback 0.22, Frequency 0.55, Width 0.012."
            '\nOutput JSON: {"FlangerOn":{"Delay":<float>,"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<float>}}'
            "\nJSON only."
        )
    },
    {
        "name": "equalization",
        "example_with": '{"EqualiserOn":{"100hz":-1.5,"200hz":0.0,"400hz":0.5,"800hz":1.0,"1600hz":1.2,"3200hz":2.0,"6400hz":1.8,"Level":0.0}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message} generate Equalizer (EQ) 7-band approximate example (100/200/400/800/1600/3200/6400 Hz + Level)."
            "\nFrequency band ranges: -15.00~15.00 dB. Level is overall compensation (-15~15)."
            "\nStyle mapping:"
            "\n- 'tight metal / djent': 100hz -4~-2 (tighten low frequencies), 200hz -3~-1 control muddiness, 400hz -2~0, 800hz 0~+1, 1600/3200hz +1~+3 increase presence and attack, 6400hz +1~+4 clarity; Level fine-tune as needed."
            "\n- 'blues / vintage rock': 100hz -1~+1, 200hz 0~+1 warmth, 400hz +0.5~+1.5 (body), 800hz -0.5~0.5, 1600hz +0.5~+1.5, 3200hz +1~+2, 6400hz +0.5~+1.5."
            "\n- 'ambient / atmospheric': minimal extreme cuts/boosts, more mild sculpting: 100hz -2~0, 200hz -1~+0.5, 400hz 0~+0.5, 800hz 0~+0.8, 1600hz +0.5~+1.2, 3200hz +1~+2.2, 6400hz +1~+2.5."
            "\n- 'fusion articulate': low frequencies slightly tightened, presence and high frequencies moderately boosted."
            "\nIf uncertain, output neutral minimal sculpting: all 0."
            '\nOutput JSON: {"EqualiserOn":{"100hz":<float>,"200hz":<float>,"400hz":<float>,"800hz":<float>,"1600hz":<float>,"3200hz":<float>,"6400hz":<float>,"Level":<float>}}'
            "\nJSON only."
        )
    },
    {
        "name": "phase",
        "example_with": '{"PhaserOn":{"Depth":0.70,"Feedback":0.55,"Frequency":0.60,"Width":1200}}',
        "prompt_with": (
            f"Based on {song_style} and {chat_message} generate Phaser parameters."
            "\nParameter range: Depth 0.00~1.00; Feedback 0.00~0.90; Frequency 0.05~2.00; Width 50~3000 (represents sweep span unit assumed to be Hz range or internal scale)."
            "\nStyle mapping:"
            "\n- 'psychedelic / classic phase swirl': Depth 0.60~0.85, Feedback 0.40~0.70, Frequency 0.30~0.70, Width 1200~2200."
            "\n- 'subtle motion (modern clean / ambient)': Depth 0.20~0.40, Feedback 0.15~0.35, Frequency 0.20~0.50, Width 800~1400."
            "\n- 'pronounced modulation leads': Depth 0.50~0.70, Feedback 0.30~0.55, Frequency 0.40~0.90, Width 1600~2400."
            "\n- 'minimal coloring': Depth 0.10~0.25, Feedback 0.05~0.15, Frequency 0.25~0.45, Width 600~1200."
            "\nDefault: Depth 0.70, Feedback 0.55, Frequency 0.60, Width 1500."
            '\nOutput JSON: {"PhaserOn":{"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<int>}}'
            "\nJSON only."
        )
    }
]

final_result = {}


# Define vector cosine similarity calculation function
def vector_cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)


# Initialize three reference data sources
audio_vector_params = []  # Reference parameters from audio_vector table
preference_params = []  # User preference parameters from music_responses table
user_text_reference = {
    "style_tags": song_style,
    "description": guitar_features
}  # User input and text analysis results

# Get audio vector reference parameters (regardless of whether memory module is enabled)
if file_path and file_path.strip() and vector is not None:
    # Query audio_vector table
    audio_cursor.execute("SELECT Parameters, Vector FROM audio_vector")
    audio_rows = audio_cursor.fetchall()

    for audio_row in audio_rows:
        audio_params = audio_row[0]
        audio_vector_str = audio_row[1]

        try:
            # Calculate audio vector similarity
            db_vector = np.array([float(x.strip()) for x in audio_vector_str.split(',')])
            similarity = vector_cosine_similarity(vector, db_vector)

            if similarity > 0.3:  # Similarity threshold
                audio_vector_params.append(json.loads(audio_params))
                print(f"Audio vector similarity: {similarity:.4f}, parameter count: {len(audio_vector_params)}")
        except (ValueError, TypeError) as e:
            print(f"Error processing audio vector parameters: {e}")

# If memory module is enabled, get user preference reference parameters
if memoryEnabled == "true":
    # Query music_responses table
    cursor.execute("SELECT SongName, Parameters, Preferences, Style, Feature FROM music_responses")
    preference_rows = cursor.fetchall()

    print(f"Found {len(preference_rows)} user preference records")

    # Use tags and description from result2 directly as search content
    target_tags = set(result2.get("tags", []))
    target_description = result2.get("description", [])
    
    # Parse feature tags, handle structured data (e.g. guitar_solo: blues_rock_pentatonic, aggressive_bends...)
    parsed_features = []
    for feature in target_description:
        if isinstance(feature, str):
            # Check if contains structured data (parts separated by semicolons)
            if ";" in feature:
                # Split normal description and structured part
                parts = feature.split(";", 1)
                parsed_features.append(parts[0].strip())  # Add description part
                # Can further parse structured data here
                structured_part = parts[1].strip()
                if structured_part:
                    parsed_features.append(structured_part)
            else:
                parsed_features.append(feature)
    
    target_description = " ".join(parsed_features)
    for pref_row in preference_rows:
        song_name = pref_row[0]
        param_str = pref_row[1]
        preference = pref_row[2]
        style_str = pref_row[3]
        feature_str = pref_row[4]

        print(f"Processing record: Song={song_name}, Preference={preference}")

        # Check if song name is same as current user input, skip if same
        if song_name == chat_message:
            print(f"Skip same song: {song_name}")
            continue

        try:
            if param_str and param_str.strip():
                param_data = json.loads(param_str)
                print(f"Parsed parameters: {type(param_data)} - {param_data}")

                # Parse style tags and description features from historical records
                try:
                    hist_style = json.loads(style_str) if style_str else []
                    hist_features = json.loads(feature_str) if feature_str else []
                except json.JSONDecodeError:
                    hist_style = []
                    hist_features = []

                # Calculate similarity
                tags_similarity = enhanced_tag_similarity(target_tags, hist_style) if target_tags and hist_style else 0.0
                
                # Improved description similarity calculation: consider matching of structured features
                if target_description and hist_features:
                    desc_similarities = []
                    
                    # Convert target description to search keywords
                    target_keywords = []
                    if isinstance(target_description, str):
                        target_keywords.extend(target_description.lower().split())
                    else:
                        # If array, each element might be structured data
                        for feature in target_description:
                            if isinstance(feature, str):
                                if ";" in feature:
                                    # Process structured data
                                    parts = feature.split(";", 1)
                                    target_keywords.extend(parts[0].lower().split())
                                    # Add keywords from structured part
                                    if ":" in parts[1]:
                                        tech_name, tech_details = parts[1].split(":", 1)
                                        target_keywords.append(tech_name.strip())
                                        target_keywords.extend([d.strip() for d in tech_details.split(",")])
                                else:
                                    target_keywords.extend(feature.lower().split())
                    
                    # Calculate similarity for each historical feature
                    for hist_feature in hist_features:
                        if hist_feature.strip():
                            hist_keywords = []
                            if ";" in hist_feature:
                                # Process structured data in historical records
                                parts = hist_feature.split(";", 1)
                                hist_keywords.extend(parts[0].lower().split())
                                if ":" in parts[1]:
                                    tech_name, tech_details = parts[1].split(":", 1)
                                    hist_keywords.append(tech_name.strip())
                                    hist_keywords.extend([d.strip() for d in tech_details.split(",")])
                            else:
                                hist_keywords.extend(hist_feature.lower().split())
                            
                            # Calculate keyword intersection similarity
                            common_keywords = set(target_keywords) & set(hist_keywords)
                            union_keywords = set(target_keywords) | set(hist_keywords)
                            
                            if union_keywords:
                                keyword_similarity = len(common_keywords) / len(union_keywords)
                                desc_similarities.append(keyword_similarity)
                    
                    # Take maximum similarity as description similarity
                    desc_similarity = max(desc_similarities) if desc_similarities else 0.0
                    
                    # If historical records have multiple description sentences, give extra bonus
                    if len(hist_features) > 1:
                        desc_similarity = min(desc_similarity * 1.1, 1.0)  # Maximum not exceeding 1.0
                else:
                    desc_similarity = 0.0
                
                # Weighted overall similarity: tag similarity weight 0.6, description similarity weight 0.4
                overall_similarity = tags_similarity * 0.6 + desc_similarity * 0.4
                
                print(f"Similarity calculation - Tag similarity: {tags_similarity:.4f}, Description similarity: {desc_similarity:.4f}, Total similarity: {overall_similarity:.4f}")
                
                # Only process this preference record when similarity is greater than 0.15
                if overall_similarity > 0.3:
                    # If preference is empty, default to accept
                    actual_preference = preference if preference else "accept"

                    if actual_preference == "accept":
                        # accept parameters have highest priority
                        preference_params.insert(0, {
                            "type": "accept",
                            "parameters": param_data,
                            "similarity": overall_similarity
                        })
                        print(f"Add accept parameters to list beginning (similarity: {overall_similarity:.4f})")
                    elif actual_preference == "edit":
                        # edit parameters are second, placed after accept
                        if not any(p["type"] == "edit" for p in preference_params):
                            preference_params.append({
                                "type": "edit",
                                "parameters": param_data,
                                "similarity": overall_similarity
                            })
                            print(f"Add edit parameters (similarity: {overall_similarity:.4f})")
                    elif actual_preference == "reject":
                        # reject parameters are stored separately for avoidance
                        preference_params.append({
                            "type": "reject",
                            "parameters": param_data,
                            "similarity": overall_similarity
                        })
                        print(f"Add reject parameters (similarity: {overall_similarity:.4f})")
                else:
                    print(f"Skip record, insufficient similarity: {overall_similarity:.4f}")
        except json.JSONDecodeError as e:
            print(f"Error processing user preference parameters: {e}")
        except Exception as e:
            print(f"Error processing record: {e}")

# Initialize preference parameter list
# similar_songs and resu have been replaced by new three-reference system, no longer needed

# Print information
print("Similar song search function disabled, using new three-reference system")
print(f"Collected preference parameters: {len(preference_params)} items")
print(f"Audio vector parameters: {len(audio_vector_params)} items")

# Text analysis results are always included in reference regardless of memory module
user_text_ref = f"""
User text analysis results:
Style tags: {json.dumps(song_style, ensure_ascii=False)}
Description features: {json.dumps(guitar_features, ensure_ascii=False)}
Text weight: {text_Weight if text_Weight else "0.5"}
"""

# Create system prompt template containing three reference types
system_prompt_template = f"""
You are an audio effects parameter expert. Input may include:
- Song name (if any)
- Description / Emotion / Scenario
- Style tags / Techniques / Semantic keywords
Text: [{chat_message}]
External style tags (optional): {song_style}

Reference data:
1. Text analysis reference (always available):
   {user_text_ref}
2. Audio vector reference ({"enabled when similarity>0.3" if file_path and file_path.strip() and vector is not None else "no audio file detected"}):
   {json.dumps(audio_vector_params, ensure_ascii=False) if audio_vector_params else "[]"}
3. User preference reference ({"enabled" if memoryEnabled == "true" else "memory module not enabled"}):
   {json.dumps(preference_params, ensure_ascii=False) if preference_params else "[]"}

Weight settings:
- Text analysis weight: {text_Weight if text_Weight else "0.5"}
- Audio vector weight: {audio_Weight if audio_Weight else "0.3"}
- User preference weight: {preference_Weight if preference_Weight else "0.2"}

Task: Only output 10 audio effects module enable/disable fixed order JSON (yes/no), no other characters:
{{
  "overload": "yes|no",
  "distortion": "yes|no",
  "delay": "yes|no",
  "reverb": "yes|no",
  "compression": "yes|no",
  "phase": "yes|no",
  "chorus": "yes|no",
  "flanger": "yes|no",
  "equalization": "yes|no",
  "noise_gate": "yes|no"
}}

Priority order (high to low):
Explicit text lock > Clean strong constraint(acoustic|fingerstyle|unplugged|pure clean) > Reference hard trigger(hard ref) > Reference prevalent enable(prevalent ref) > Style baseline/tag inference > Technique/semantic enhancement > Low density completion/fallback

Process:
0) Title direct judgment lock
0.R1) Reference module hard trigger parsing (hard ref)
0.R2) Reference module prevalent enable statistics (prevalent ref, >=60% default threshold, adjustable to prevalence_threshold=0.60)
0.1) Conflict correction SC1~SC8
0.2) Explicit effect lock (locked_text)
1) Description and style tag completion (including style baseline)
2) Technique / semantic keyword enhancement
3) Mutual exclusion / constraint pruning
4) Noise gate judgment
6A) Baseline & single modulation / low density completion
5) Fallback (minimum set)
6) Pending fill no + modulation mutual exclusion final check (explicit exemption + locked_ref priority)

=== Reference Module Parsing Rules ===
Reference input may contain keys like XXXOn. Process according to following mapping and levels:
Module->effect mapping:
  CompressorOn -> compression
  DriverOn / DistortionOn / HighGainOn / PreampHighGainOn / FuzzOn -> distortion (DriverOn has threshold)
  ScreamerOn / OverdriveOn / BoostOn / ODOn -> overload
  DelayOn -> delay
  ReverbOn -> reverb
  ChorusOn -> chorus
  PhaserOn -> phase
  FlangerOn -> flanger
  EqualiserOn -> equalization
  NoiseGateOn / GateOn -> noise_gate

0.R1 Hard trigger (hard ref) logic:
  - DriverOn:
      If Distortion/Gain/Drive parameter >=0.40 exists -> distortion=yes (locked_ref)
      If 0.20 <= value <0.40 -> overload=yes (light push only, soft_ref), does not directly trigger distortion
  - DistortionOn / HighGainOn / PreampHighGainOn / FuzzOn -> distortion=yes (locked_ref)
  - FuzzOn always treated as distortion hard trigger, ignoring mid_gain suppression
  - ScreamerOn / OverdriveOn / BoostOn / ODOn -> overload=yes (soft_ref; can coexist with hard distortion)
  - CompressorOn -> compression=yes (soft_ref; can be overridden by explicit no or clean strong constraint)
  - ReverbOn: If Mix>0.02 -> reverb=yes (soft_ref but highly credible); Mix<=0.02 -> weak_ref (can be pruned later)
  - DelayOn: If Mix>0.05 and Delay>0 -> delay=yes (soft_ref); otherwise weak_ref
  - ChorusOn / PhaserOn / FlangerOn: Add to modulation candidates; if multiple On, record first, handle mutual exclusion later
  - EqualiserOn -> equalization=yes (soft_ref)
  - NoiseGateOn / GateOn -> noise_gate=yes (soft_ref; can fallback to no if final distortion chain insufficient)
  - Simultaneous ScreamerOn + DriverOn with DriverOn Distortion>=0.40 -> overload=yes + distortion=yes
  - mid_gain|crunch no longer veto locked_ref distortion
  - Clean strong constraint(acoustic|fingerstyle|unplugged|pure clean) can still override distortion related: distortion=no overload=no noise_gate=no (except explicit text directly requesting distortion)

0.R2 Prevalent enable statistics (prevalent ref):
  For each effect category, calculate the enable ratio of corresponding "On" modules in reference list:
    prevalence = (number of On modules related to this effect) / (number of reference entries)
  If prevalence >= prevalence_threshold(default 0.60) and effect not explicitly set to no by explicit/clean/hard trigger:
    Mark effect as yes (ref_prevalent, soft_ref)
  Modulation (chorus/phase/flanger) if multiple reach prevalent enable, still keep single by chorus > phase > flanger priority (unless explicit multiple locks)
  For delay/reverb if prevalent but most instances Mix near 0, can downgrade to weak_prevalent, can be pruned later

=== Special Processing Rules for Three Reference Types ===
1. Text analysis reference (weight: {text_Weight if text_Weight else "0.5"}):
   - Perform style inference based on style tags and description features
   - Directly affect basic module enable decisions (e.g., ambient->reverb+delay, metal->distortion)
   - Serve as basic reference for parameter generation

2. Audio vector reference (weight: {audio_Weight if audio_Weight else "0.3"}):
   {"- Enabled when similarity>0.3, providing high quality standard parameter reference" if audio_vector_params else "- No audio vector reference available"}
   - Parameter values validated and optimized, suitable for current audio style
   - Prioritize accept type parameter data

3. User preference reference (weight: {preference_Weight if preference_Weight else "0.2"}):
   - accept type: high priority, must be prioritized
   - edit type: medium priority, contains user-modified parameter suggestions
   - reject type: low priority, must avoid duplication
   - When referencing: {"user history data available" if memoryEnabled == "true" and preference_params else "no user history data"}

User preference data description:
{json.dumps(preference_params, ensure_ascii=False) if preference_params else "no user history data available"}

Special rules:
- If user preferences contain accept type parameters, prioritize referencing accept data
- If user preferences contain reject type parameters, avoid generating same parameters
- If user preferences contain edit type parameters, adjust based on accept data

Explicit effect lock (0.2):
  Match: "with a/an <effect> effect" "<effect> effect" "use <effect>" "<effect> sound/tone"
  effect: overdrive/drive/boost(=overload), distortion, delay, reverb, compression/comp, chorus, flanger, phaser(=phase), eq/eqing/equalizer(=equalization), gate(=noise_gate)
  -> Set yes + locked_text; only clean/noise obvious correction can change.

Style / tag and semantics:
- metal/djent/thrash/death/core/grind/heavy (+ chug|palm mute|tight|high gain optional) -> distortion=yes; if boost/drive/overdrive/tight/chug -> overload=yes
- mid_gain|mid-gain|crunch|classic_rock|blues|vintage|hard_rock -> overload=yes(light) distortion=no(if no locked_ref)
- ambient|atmospheric|post-rock|shoegaze|cinematic -> reverb=yes delay=yes; dreamy|lush->chorus; psychedelic|spacey|swirl->phase
- acoustic|fingerstyle|folk|unplugged -> reverb=yes compression=yes equalization=yes; distortion/overload/noise_gate=no
- melodic|emotional|lyrical|sustain|solo|lead -> delay=yes; reverb=yes(if not set)
- boost|overdrive|screamer|od -> overload=yes
- fuzz|wall|massive|dense|saturated -> distortion=yes
- lush|dreamy|shimmer|80s -> chorus=yes
- psychedelic|spacey|swirl -> phase=yes(if chorus not explicitly locked)
- jet|swoosh|metallic -> flanger=yes
- ambient|space|swell|pad|ethereal -> reverb+delay=yes
- hiss|noise|gate|gating|unwanted noise and distortion=yes -> noise_gate=yes
- melodic_bassline -> compression=yes equalization=yes
- clean_to_distorted -> no high gain words: overload=yes(light) distortion remains no(if no locked_ref)

Style baseline (grunge | alternative_rock | clean_to_distorted | (rock and no high gain words)):
- distortion not triggered by high gain and not locked_ref -> overload=yes compression=yes reverb=yes equalization=yes
- melodic_bassline additionally ensures compression & equalization=yes

Technique enhancement and refinement:
- tapping/sweep/shred/fast/legato + high gain context -> distortion=yes
- chug/djent/palm mute/tight/percussive -> distortion=yes; if drive/overdrive/boost appears -> overload=yes
- wall/massive/dense/saturated/fuzz -> distortion=yes
- clean sparkle/glassy -> compression=yes
- droning/drone -> reverb=yes; if melodic words and delay not set -> delay=yes
- noise words (hiss/noise/gating...) + distortion chain -> noise_gate=yes

Mutual exclusion / constraints:
- Modulation only one: chorus > phase > flanger (explicit lock multiple reserved; otherwise keep highest source by priority: locked_text > locked_ref > ref_prevalent > soft_ref > weak_ref)
- distortion=no and overload=no -> noise_gate=no
- distortion=yes and chug|djent|tight|palm mute|boost -> overload=yes & noise_gate=yes
- acoustic|fingerstyle|unplugged|pure clean -> distortion/overload/noise_gate=no(even if locked_ref, but explicit text requesting distortion can be exempted)
- mid_gain|crunch and no high gain words -> distortion=no(if not locked_ref)
- overload does not derive distortion; light push does not trigger noise gate

Noise gate:
noise_gate=yes when:
  distortion=yes and metal|djent|chug|tight|palm mute|thrash|death|core|high gain|heavy
  or hiss|noise|gate|gating|unwanted noise
Parameter refinement:
  If distortion source only DriverOn and Distortion<0.55 and no above high gain/noise words -> noise_gate=no

6A Single modulation / low density completion:
- If only 1 modulation=yes and not declared dry:
  equalization=yes; reverb=yes; compression=yes(if contains grunge|alternative_rock|rock|mid_tempo|melodic|melodic_bassline|clean_to_distorted)
  overload=yes(if baseline condition established and distortion=no)
- If final yes count <2 and not dry -> at least equalization=yes

Fallback:
- All no/undecided -> equalization=yes
- lead/solo/melodic/emotional and delay not set -> delay=yes
- ambient|space|atmospheric and reverb not set -> reverb=yes
- Still <2 yes and not dry -> equalization=yes

Final check:
- Undecided->no
- Modulation mutual exclusion (explicit exemption + locked_ref priority)
- locked_ref distortion not vetoed by mid_gain/crunch
- distortion=no and overload=no -> noise_gate=no
- If distortion=yes but source locked_ref and(DriverOn Distortion 0.40~0.55) and no high gain/noise semantics -> noise_gate=no
- Prohibit extra text

Additional:
- Explicit instructions priority
- Emotion words do not trigger gain or noise gate
- clean_to_distorted defaults to light push
- Single modulation not isolated: needs EQ+Reverb(+Compression depending on style)
- Reference hard trigger priority over prevalent enable; prevalent enable is soft_ref can be overridden by higher priority
- Prevalent enable statistics: prevalence >=0.60(adjustable), below threshold not forced
- weak_ref(Mix≈0 / parameters near zero) can be removed in mutual exclusion or final check stage
- ScreamerOn + DriverOn (Distortion>=0.40) -> overload=yes + distortion=yes
- FuzzOn always treated as distortion=yes(hard trigger)
- Do not deny explicit no due to prevalent equalization alone(if explicitly requested no, can keep no)

Output: Only output JSON (key order fixed):
{{
  "overload": "yes|no",
  "distortion": "yes|no",
  "delay": "yes|no",
  "reverb": "yes|no",
  "compression": "yes|no",
  "phase": "yes|no",
  "chorus": "yes|no",
  "flanger": "yes|no",
  "equalization": "yes|no",
  "noise_gate": "yes|no"
}}
"""

# Use updated system prompt template
print(f"system_prompt_template:{system_prompt_template}")
system_prompt = system_prompt_template
user_prompt1 = chat_message

# Save system message
system_message = {"role": "system", "content": system_prompt}
conversation_history.append(system_message)
# Save user message
user_message = {"role": "user", "content": user_prompt1}
conversation_history.append(user_message)
# Send request
response1 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
# Save assistant reply
assistant_message = {
    "role": "assistant",
    "content": response1.choices[0].message.content
}
conversation_history.append(assistant_message)

# Get response1 response data and convert to JSON
response_content1 = response1.choices[0].message.content
# Extract valid JSON part
start_index = response_content1.find("{")
end_index = response_content1.rfind("}") + 1
if start_index != -1 and end_index != -1:
    cleaned_content1 = response_content1[start_index:end_index]
else:
    print("Error: No valid JSON content found")
    sys.exit(1)

try:
    result1 = json.loads(cleaned_content1)
    print(json.dumps(result1, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print(f"Error: Invalid JSON response: {cleaned_content1}")
    sys.exit(1)

# Use for loop to process different audio effect modules
for effector in effectors:
    effector_name = effector["name"]
    if result1.get(effector_name) == "yes":
        # Build system prompt containing audio vector reference parameters (regardless of memory)
        audio_ref_info = f"Audio vector reference parameters: {json.dumps(audio_vector_params, ensure_ascii=False) if audio_vector_params else '[]'}"

        if memoryEnabled == "true":  # Simplified condition check
            system_prompt = f"""
You are a professional audio effects adjuster. Goal: For the current single audio effect module, based on similar song reference parameters {audio_vector_params} and user preferences, output the module's JSON parameters. Example format (reference structure only, not values): {effector["example_with"]}

Strict output requirements:
1. Only output one JSON object, prohibit adding explanatory text / extra fields / prefixes/suffixes.
2. If module needs to be enabled: use *On form from example (e.g. CompressorOn, DelayOn). If disabled: use *Off (e.g. CompressorOff) and assign empty object {{}}.
3. Do not directly copy example values; nor verbatim copy single parameter values from {audio_vector_params}. Must make small adjustments based on reference.
4. Only output keys related to this module, prohibit extra modules or redundant levels.

Reference data (user preference parameters, multiple JSON fragments or array form): {preference_params}
{audio_ref_info}

Parsing rules:
- Identify module On/Off: <ModuleName>On considered enabled; <ModuleName>Off considered disabled.
- Module name and processing object determined by external context effector, no need to guess other modules.
- If multiple versions appear in reference (e.g. CompressorOn and CompressorOff mixed), count: On_count and Off_count.
  - On_count > Off_count → Judge as enabled
  - Off_count > On_count → Judge as disabled
  - Tie or neither appears → Enter "heuristic judgment"

Heuristic judgment (applicable only when tied or no information):
- If module belongs to conventional basic chain (e.g. equalization, compression, light spatial processing) and common in this style → Can be enabled
- If module is modulation (chorus/phaser/flanger) and no indication in reference → Default to disabled
- If no clear style or insufficient information → Default to disabled (unless basic module like EQ)

Parameter generation logic (only when judged enabled):
1. Reference all On samples' parameter value sets for this module (from {audio_vector_params}), calculate baseline value for each parameter (default use median; if cannot parse use first On sample).
2. Generate new value based on baseline: maintain "reasonable, close, not excessive drift":
   - 0~1 normalized parameters: offset ±(0.03~0.10), clamp to [0,1]
   - Time parameters (ms, width, etc.): ±5%~12% (if original value very small <1, can add minimum adjustment 0.001~0.01)
   - dB parameters: ±(5%~15%) or ±(1~3 dB) take smaller; thresholdtype (very negative) can ±(2~6 dB)
   - Ratio: If <10 → ±(0.2~0.8); If ≥10 → ±(0.5~2.0), not below 1
   - Delay time Delay: Keep within 1.00~400.00 range
   - Integer parameters only (like some Width) can be rounded
3. Ensure not exactly same as baseline; if still same after random drift, make another micro adjustment (minimum step 0.01 or 1 unit).
4. Maintain logical consistency between parameters (e.g. Attack should not be much larger than Release if semantically inconsistent; ignore if no rule).
5. If {audio_vector_params} has no On samples but heuristic judgment enabled → Use module's neutral default:
   - Compressor: Threshold=-24, Ratio=3, Attack=0.010~0.050, Release=0.120~0.250, Makeup=4, Mix=0.70
   - Distortion/Driver: Distortion=0.55, Volume=-12
   - Overdrive/Screamer: Drive=0.55, Tone=0.52, Level=-12
   - Delay: Feedback=0.35, Delay=320, Mix=0.30
   - Reverb: Size=0.40, Damping=0.30, Width=0.70, Mix=0.30
   - Chorus: Delay=0.028, Depth=0.30, Frequency=0.60, Width=0.030
   - Flanger: Delay=0.012, Depth=0.40, Feedback=0.22, Frequency=0.55, Width=0.012
   - Phaser: Depth=0.60, Feedback=0.40, Frequency=0.60, Width=1500
   - EQ: All bands=0 (Level=0)
   - NoiseGate (if applicable): Threshold=-50~ -60, Release=0.10~0.25 (example only, can ignore if module definition differs)

Disabled state:
- Output {{"<ModuleName>Off": {{}}}} without parameter keys.
- Do not output any parameter value related hints.

Output format:
- Only allow one outermost key (On or Off)
- All numeric types remain numbers (no quotes); string parameters as-is
- Keep 2~3 decimal places (integer parameters can be int)

Prohibited items:
- Must not output explanatory text, reasons, comments
- Must not include any top-level keys other than this module's key
- Must not output null / None / NaN / Infinity
- Must not use exactly same parameter set as example (values need differences)

Now please output this module's final JSON according to above rules.
"""
        else:
            system_prompt = f"""
You are a professional audio effects adjuster. Based on audio vector reference parameters {audio_ref_info} and internal general experience, output the module's JSON. Example structure (reference format only, not values): {effector["example_with"]}

Judgment:
- If module is basic core (equalization, compression, main delay, main reverb, necessary gain stage) → Default enabled
- If modulation/effects (chorus, flanger, phaser) and no style context → Default disabled
- If high gain related (distortion/overdrive) and no context → Default disabled
- Optional strategy: if module name contains "Equaliser" then definitely enabled; "Compressor" considered enableable; "Delay"/"Reverb" can be neutrally lightly enabled to provide space; others disabled

Reference data: {audio_ref_info}

Parameter generation logic:
1. Reference all On samples' parameter value sets for this module (from {audio_vector_params}), calculate baseline value for each parameter (default use median; if cannot parse use neutral default).
2. Generate new value based on baseline: maintain "reasonable, close, not excessive drift":
   - 0~1 normalized parameters: offset ±(0.03~0.10), clamp to [0,1]
   - Time parameters (ms, width, etc.): ±5%~12% (if original value very small <1, can add minimum adjustment 0.001~0.01)
   - dB parameters: ±(5%~15%) or ±(1~3 dB) take smaller; thresholdtype (very negative) can ±(2~6 dB)
   - Ratio: If <10 → ±(0.2~0.8); If ≥10 → ±(0.5~2.0), not below 1
   - Delay time Delay: Keep within 1.00~400.00 range
   - Integer parameters only (like some Width) can be rounded
3. If {audio_vector_params} has no On samples → Use module's neutral default:
   - Compressor: Threshold=-24, Ratio=3, Attack=0.010~0.050, Release=0.120~0.250, Makeup=4, Mix=0.70
   - Distortion/Driver: Distortion=0.55, Volume=-12
   - Overdrive/Screamer: Drive=0.55, Tone=0.52, Level=-12
   - Delay: Feedback=0.35, Delay=320, Mix=0.30
   - Reverb: Size=0.40, Damping=0.30, Width=0.70, Mix=0.30
   - Chorus: Delay=0.028, Depth=0.30, Frequency=0.60, Width=0.030
   - Flanger: Delay=0.012, Depth=0.40, Feedback=0.22, Frequency=0.55, Width=0.012
   - Phaser: Depth=0.60, Feedback=0.40, Frequency=0.60, Width=1500
   - EQ: All bands=0 (Level=0)

Output requirements:
1. Only output JSON, one top-level key (On or Off), prohibit adding any explanatory text or extra fields.
2. Numeric parameters remain numeric type, no quotes.
3. Parameter range meets module requirements (e.g. Delay time 1.00~400.00).
4. Prohibit outputting null, None, NaN or Infinity.
5. If judged disabled, output like {{"CompressorOff": {{}}}}.

Now please output this module's JSON according to above rules.
"""
        print(f"system_prompt:{system_prompt}")
        user_prompt = effector["prompt_with"] + effector["example_with"]
        # Save system message
        system_message = {"role": "system", "content": system_prompt}
        conversation_history.append(system_message)
        # Save user message
        user_message = {"role": "user", "content": user_prompt}
        conversation_history.append(user_message)
        # Send request
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[system_message, user_message],
            stream=False
        )
        # Save assistant reply
        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content
        }
        conversation_history.append(assistant_message)

        # Get response data and convert to JSON
        response_content = response.choices[0].message.content
        # Remove code block markers and newlines from front and back
        cleaned_content = response_content.replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(cleaned_content)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            final_result.update(result)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response: {cleaned_content}")
            sys.exit(1)
    elif result1.get(effector_name) == "no":
        if effector_name == "compression":
            final_result["CompressorOff"] = {"Threshold": "-128.00", "Ratio": "1", "Attack": "0.00", "Release": "0.00",
                                             "Makeup": "-12.00", "Mix": "0.00"}
        elif effector_name == "distortion":
            final_result["DriverOff"] = {"Distortion": "0.00", "Volume": "-64.0"}
        elif effector_name == "overload":
            final_result["ScreamerOff"] = {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0000000"}
        elif effector_name == "delay":
            final_result["DelayOff"] = {"Feedback": "0.00", "Delay": "1.00", "Mix": "0.00"}
        elif effector_name == "reverb":
            final_result["ReverbOff"] = {"Size": "0.00", "Damping": "0.00", "Width": "0.00", "Mix": "0.00"}
        elif effector_name == "chorus":
            final_result["ChorusOff"] = {"Delay": "0.010", "Depth": "0.00", "Frequency": "0.05", "Width": "0.010"}
        elif effector_name == "flanger":
            final_result["FlangerOff"] = {"Delay": "0.00100", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.05",
                                          "Width": "0.001"}
        elif effector_name == "equalization":
            final_result["EqualiserOff"] = {"100hz": "0.00", "200hz": "0.00", "400hz": "0.00", "800hz": "0.00",
                                            "1600hz": "0.00", "3200hz": "0.00", "6400hz": "0.00", "Level": "0.00"}
        elif effector_name == "phase":
            final_result["PhaserOff"] = {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.05", "Width": "50"}

# Convert final result to string
result_str = json.dumps(final_result, ensure_ascii=False)
# Print related information
print(f"Input song name: {chat_message}")
print(f"Corresponding style and characteristics: {result2_str}")
print(f"Corresponding parameters: {result_str}")
print("-" * 50)
# Convert list to JSON string
song_style_str = json.dumps(song_style, ensure_ascii=False)
guitar_features_str = json.dumps(guitar_features, ensure_ascii=False)

print(f"Complete conversation history: {conversation_history}")
# System prompt
system_prompt3 = f'''
You are a professional intelligent music effects assistant with extensive knowledge in music production and audio processing. Your role is to:

1. Analyze user's musical input and technical requirements
2. Generate professional, precise effects parameters based on AI analysis
3. Provide clear explanations of parameter selections with musical theory foundations
4. Customize solutions according to user's style preferences and reference tracks

Based on the complete conversation history which includes:
- Original user input: "{chat_message}"
- AI style analysis: {result2_str}
- Effects module decisions: {result1}
- Generated parameters: {result_str}
- Three-reference system parameters: {preference_params}

Your response must be professional, technically accurate, and educational. Use only English.
'''

user_prompt3 = f'''
Provide a comprehensive analysis of the music style preferences and effects parameters generated. Include:

1. **Musical Style Analysis**
   - Interpret the extracted style tags: {song_style}
   - Explain the genre characteristics and playing techniques
   - Describe the overall sonic texture and mood

2. **Effects Parameters Breakdown**
   - For each enabled effect ({[k for k, v in result1.items() if v == "yes"]}):
     * Explain the purpose and sonic contribution
     * Detail how each parameter affects the sound
     * Describe the musical theory behind the settings

3. **Reference Tracks Analysis**
   - Three-reference system: Text analysis, Audio vectors, User preferences
   - Style characteristics from text analysis: {song_style}
   - User preference parameters: {preference_params}
   - Audio vector parameters: {audio_vector_params}

4. **Parameter Interaction & Signal Flow**
   - Explain how effects work together in the signal chain
   - Describe any complementary or conflicting interactions
   - Explain the order of operations rationale

5. **Fine-tuning Recommendations**
   - Provide 2-3 specific adjustment suggestions for different scenarios
   - Explain what sonic changes each adjustment would produce
   - Give context-specific advice for the identified style

6. **Technical Implementation Notes**
   - Any special considerations for the genre/style
   - Common pitfalls to avoid
   - Alternative parameter approaches for different tones

Your response must start with "Parameter generation complete!\n" followed by a well-structured, professional analysis that demonstrates deep music production expertise.
'''

# Save system message
system_message = {"role": "system", "content": system_prompt3}
# Save user message
user_message = {"role": "user", "content": user_prompt3}
# Send request
response3 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
response3_content = response3.choices[0].message.content
print(f"Cleaned response: {response3_content}")

# First convert vector to string format (corresponding to query code)
vector_str = ','.join(map(str, vector)) if vector is not None else ''

# Data validity check
valid = True
error_msg = []

# Check if song name is empty
if not chat_message or chat_message.strip() == '':
    valid = False
    error_msg.append("Song name cannot be empty")

# Check if style and feature fields are valid JSON
try:
    if song_style_str:
        json.loads(song_style_str)
    if guitar_features_str:
        json.loads(guitar_features_str)
except json.JSONDecodeError as e:
    valid = False
    error_msg.append(f"Style or feature field JSON format error: {str(e)}")

# Check vector format (if exists)
if vector_str:
    try:
        # Verify if can be restored to float list
        [float(x) for x in vector_str.split(',')]
    except ValueError:
        valid = False
        error_msg.append("Audio vector contains non-numeric values")

if not valid:
    print(f"Data validation failed: {'; '.join(error_msg)}")
    sys.exit(1)

# Write style result string to file
safe_write_file("result1.txt", song_style_str)

# Write feature result string to file
safe_write_file("result2.txt", guitar_features_str)

# Write parameter result string to file
safe_write_file("result.txt", result_str)

# Write analysis result string to file
safe_write_file("result3.txt", response3_content)

# --------------------------------------------------------------------------------
# Added: Generate import_params.json for Plugin Auto-Import
# --------------------------------------------------------------------------------

try:
    print("Starting generation of import_params.json...")
    
    # 1. Define Parameter Mapping (Moved inside try block for safety)
    param_mapping = {
        # Switch control mapping
        "CompressorOn": ("pre_compressor_on", 1.0),
        "CompressorOff": ("pre_compressor_on", 0.0),
        "ScreamerOn": ("tube_screamer_on", 1.0),
        "ScreamerOff": ("tube_screamer_on", 0.0),
        "DriverOn": ("mouse_drive_on", 1.0),
        "DriverOff": ("mouse_drive_on", 0.0),
        "DelayOn": ("delay_on", 1.0),
        "DelayOff": ("delay_on", 0.0),
        "ReverbOn": ("room_on", 1.0),
        "ReverbOff": ("room_on", 0.0),
        "ChorusOn": ("chorus_on", 1.0),
        "ChorusOff": ("chorus_on", 0.0),
        "FlangerOn": ("flanger_on", 1.0),
        "FlangerOff": ("flanger_on", 0.0),
        "PhaserOn": ("phaser_on", 1.0),
        "PhaserOff": ("phaser_on", 0.0),
        "EqualiserOn": ("pre_eq_on", 1.0),
        "EqualiserOff": ("pre_eq_on", 0.0),
        "NoiseGateOn": ("noise_gate_on", 1.0), 
        "NoiseGateOff": ("noise_gate_on", 0.0),

        # Parameter value mapping
        "CompressorOn.Threshold": "pre_comp_thresh",
        "CompressorOn.Ratio": "pre_comp_ratio",
        "CompressorOn.Attack": "pre_comp_attack",
        "CompressorOn.Release": "pre_comp_release",
        "CompressorOn.Mix": "pre_comp_blend",
        "CompressorOn.Makeup": "pre_comp_gain",
        "CompressorOff.Threshold": "pre_comp_thresh",
        "CompressorOff.Ratio": "pre_comp_ratio",
        "CompressorOff.Attack": "pre_comp_attack",
        "CompressorOff.Release": "pre_comp_release",
        "CompressorOff.Mix": "pre_comp_blend",
        "CompressorOff.Makeup": "pre_comp_gain",
        
        "ScreamerOn.Drive": "tube_screamer_drive",
        "ScreamerOn.Tone": "tube_screamer_tone",
        "ScreamerOn.Level": "tube_screamer_level",
        "ScreamerOff.Drive": "tube_screamer_drive",
        "ScreamerOff.Tone": "tube_screamer_tone",
        "ScreamerOff.Level": "tube_screamer_level",
        
        "DriverOn.Distortion": "mouse_drive_distortion",
        "DriverOn.Volume": "mouse_drive_volume",
        "DriverOff.Distortion": "mouse_drive_distortion",
        "DriverOff.Volume": "mouse_drive_volume",
        
        "DelayOn.Feedback": "delay_feedback",
        "DelayOn.Delay": "delay_left_millisecond",
        "DelayOn.Mix": "delay_mix",
        "DelayOff.Feedback": "delay_feedback",
        "DelayOff.Delay": "delay_left_millisecond",
        "DelayOff.Mix": "delay_mix",
        
        "ReverbOn.Size": "room_size",
        "ReverbOn.Damping": "room_damping",
        "ReverbOn.Width": "room_width",
        "ReverbOn.Mix": "room_mix",
        "ReverbOff.Size": "room_size",
        "ReverbOff.Damping": "room_damping",
        "ReverbOff.Width": "room_width",
        "ReverbOff.Mix": "room_mix",
        
        "ChorusOn.Delay": "chorus_delay",
        "ChorusOn.Depth": "chorus_depth",
        "ChorusOn.Frequency": "chorus_frequency",
        "ChorusOn.Width": "chorus_width",
        "ChorusOff.Delay": "chorus_delay",
        "ChorusOff.Depth": "chorus_depth",
        "ChorusOff.Frequency": "chorus_frequency",
        "ChorusOff.Width": "chorus_width",
        
        "FlangerOn.Delay": "flanger_delay",
        "FlangerOn.Depth": "flanger_depth",
        "FlangerOn.Feedback": "flanger_feedback",
        "FlangerOn.Frequency": "flanger_frequency",
        "FlangerOn.Width": "flanger_width",
        "FlangerOff.Delay": "flanger_delay",
        "FlangerOff.Depth": "flanger_depth",
        "FlangerOff.Feedback": "flanger_feedback",
        "FlangerOff.Frequency": "flanger_frequency",
        "FlangerOff.Width": "flanger_width",
        
        "PhaserOn.Depth": "phaser_depth",
        "PhaserOn.Feedback": "phaser_feedback",
        "PhaserOn.Frequency": "phaser_frequency",
        "PhaserOn.Width": "phaser_width",
        "PhaserOff.Depth": "phaser_depth",
        "PhaserOff.Feedback": "phaser_feedback",
        "PhaserOff.Frequency": "phaser_frequency",
        "PhaserOff.Width": "phaser_width",
        
        "EqualiserOn.100hz": "pre_eq_100_gain",
        "EqualiserOn.200hz": "pre_eq_200_gain",
        "EqualiserOn.400hz": "pre_eq_400_gain",
        "EqualiserOn.800hz": "pre_eq_800_gain",
        "EqualiserOn.1600hz": "pre_eq_1600_gain",
        "EqualiserOn.3200hz": "pre_eq_3200_gain",
        "EqualiserOn.6400hz": "pre_eq_6400_gain",
        "EqualiserOn.Level": "pre_eq_level_gain",
        "EqualiserOff.100hz": "pre_eq_100_gain",
        "EqualiserOff.200hz": "pre_eq_200_gain",
        "EqualiserOff.400hz": "pre_eq_400_gain",
        "EqualiserOff.800hz": "pre_eq_800_gain",
        "EqualiserOff.1600hz": "pre_eq_1600_gain",
        "EqualiserOff.3200hz": "pre_eq_3200_gain",
        "EqualiserOff.6400hz": "pre_eq_6400_gain",
        "EqualiserOff.Level": "pre_eq_level_gain"
    }

    mapped_params = {}
    
    # Process final_result
    # Check if final_result exists and is not empty
    if 'final_result' not in globals() and 'final_result' not in locals():
        print("Warning: final_result variable not found. Initializing empty.")
        final_result = {}

    for key, value in final_result.items():
        # 1. Process top-level keys
        if key in param_mapping:
            if isinstance(param_mapping[key], tuple):
                p_id, p_val = param_mapping[key]
                mapped_params[p_id] = p_val
        
        # 2. Process nested parameters
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                full_key = f"{key}.{sub_key}"
                if full_key in param_mapping:
                    param_id = param_mapping[full_key]
                    try:
                        final_val = float(sub_value)
                    except (ValueError, TypeError):
                        final_val = sub_value
                    mapped_params[param_id] = final_val

    # Write to import_params.json
    # Safer path resolution
    public_dir = os.environ.get('PUBLIC', os.environ.get('SystemDrive', 'C:') + '\\Users\\Public')
    common_docs = os.path.join(public_dir, 'Documents')
    import_dir = os.path.join(common_docs, "Supertonal", "Audio-agent")
    
    if not os.path.exists(import_dir):
        os.makedirs(import_dir)
        
    import_file_path = os.path.join(import_dir, "import_params.json")
    
    print(f"Writing to: {import_file_path}")
    with open(import_file_path, 'w', encoding='utf-8') as f:
        json.dump(mapped_params, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully wrote mapped parameters to {import_file_path}")

    # --- MusicGen Integration ---
    if chat_message:
        musicgen_prompt = str                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           (chat_message)
        musicgen_prompt = f"{musicgen_prompt}, electric guitar solo, lead guitar melody, expressive solo, no strumming, no chords"
        print(f"MusicGen final prompt: {musicgen_prompt}")
        
        audio_filename = "generated_input.wav"
        audio_full_path = os.path.join(import_dir, audio_filename)
        
        # Use local MusicGen generation
        success = generate_audio_local(musicgen_prompt, audio_full_path)
        if success:
            print(f"Generated audio saved to: {audio_full_path}")
        else:
            print("MusicGen generation failed.")
    else:
        print("Skipping MusicGen: No user input available.")
    # ----------------------------

except Exception as e:
    print(f"Error processing parameters for import: {e}")
    # Don't fail the whole script for this optional step, but print trace
    import traceback
    traceback.print_exc()

# --------------------------------------------------------------------------------
# End Added Code
# --------------------------------------------------------------------------------

# Close database connection
conn.close()
audio_conn.close()

# New: Wait for user input before closing window
input("程序执行完成，按回车键关闭窗口...")
