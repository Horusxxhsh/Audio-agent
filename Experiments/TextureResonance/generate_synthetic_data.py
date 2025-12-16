import os
import json
import hashlib
import numpy as np
import soundfile as sf

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..', '..')
DATA_JSONL = os.path.join(PROJECT_ROOT, 'data.jsonl')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'Data', 'Audio_Synthetic')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_tone(freq, duration, sr=16000, type='sine'):
    t = np.linspace(0, duration, int(sr*duration))
    if type == 'sine':
        return 0.5 * np.sin(2 * np.pi * freq * t)
    elif type == 'square':
        return 0.5 * np.sign(np.sin(2 * np.pi * freq * t))
    elif type == 'saw':
        return 0.5 * (2 * (t * freq - np.floor(t * freq + 0.5)))
    else:
        return 0.5 * np.sin(2 * np.pi * freq * t)

def generate_noise(duration, sr=16000, color='white'):
    samples = int(sr * duration)
    if color == 'white':
        return np.random.normal(0, 1, samples)
    else: 
        # Simple approximation for pink/brown
        white = np.random.normal(0, 1, samples)
        return np.cumsum(white) / np.max(np.abs(np.cumsum(white)))

def generate_synthetic_audio(record, output_path):
    """
    Generates deterministic audio based on song metadata.
    """
    song_name = record.get('SongName', 'Unknown')
    style_list = record.get('Style', [])
    
    # Hash name to get deterministic seed/params
    h = hashlib.md5(song_name.encode('utf-8')).hexdigest()
    seed_val = int(h, 16) % (2**32)
    np.random.seed(seed_val)
    
    sr = 16000
    duration = 3.0
    
    # Determine base properties from Style
    # Logic: 
    # Metal/Rock -> Distortion (Square/Saw + Noise)
    # Jazz/Clean -> Clean (Sine + minimal noise)
    # Others -> Mix
    
    is_heavy = any(s.lower() in ['metal', 'rock', 'heavy', 'djent'] for s in style_list)
    is_clean = any(s.lower() in ['jazz', 'clean', 'pop', 'indie'] for s in style_list)
    
    if is_heavy:
        base_freq = 80 + (seed_val % 100) # Low pitch (80-180Hz)
        tone = generate_tone(base_freq, duration, sr, type='saw')
        noise = generate_noise(duration, sr, color='white') * 0.3
        audio = tone + noise
    elif is_clean:
        base_freq = 220 + (seed_val % 220) # Mid pitch
        tone = generate_tone(base_freq, duration, sr, type='sine')
        noise = generate_noise(duration, sr, color='white') * 0.05
        audio = tone + noise
    else:
        # Default mix
        base_freq = 110 + (seed_val % 330)
        tone = generate_tone(base_freq, duration, sr, type='square')
        noise = generate_noise(duration, sr, color='white') * 0.1
        audio = tone + noise
        
    # Normalize
    audio = audio / (np.max(np.abs(audio)) + 1e-6)
    
    # Save
    sf.write(output_path, audio, sr)
    # print(f"Generated for {song_name} -> {output_path}")

def main():
    if not os.path.exists(DATA_JSONL):
        print(f"Error: {DATA_JSONL} not found.")
        return

    ensure_dir(OUTPUT_DIR)
    
    count = 0
    with open(DATA_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                record = json.loads(line)
                song_name = record.get('SongName', f"song_{count}")
                # Sanitize filename
                safe_name = "".join([c for c in song_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
                filename = f"{safe_name}.wav"
                output_path = os.path.join(OUTPUT_DIR, filename)
                
                generate_synthetic_audio(record, output_path)
                count += 1
            except Exception as e:
                print(f"Skipping line: {e}")
                
    print(f"Successfully generated {count} synthetic audio files in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
