import sys
import os

# Add current directory to path so we can import texture_encoder
sys.path.append(os.path.dirname(__file__))

from texture_encoder import TextureEncoder, similarity_score, SourcePurifier
import torch
import numpy as np
import soundfile as sf

def run_demo():
    print("===========================================")
    print("   Texture Resonance Retrieval (TRR) Demo  ")
    print("===========================================")
    
    # 1. Check Dependencies
    try:
        import demucs
        print("[OK] Demucs installed.")
    except ImportError:
        print("[WARN] Demucs not installed. Source Purification will be skipped/mocked.")
        
    try:
        import transformers
        print("[OK] Transformers installed.")
    except ImportError:
        print("[FAIL] Transformers not installed. Cannot run Wav2Vec2.")
        return

    # 2. Initialize Encoder
    print("\n[Init] Initializing TextureEncoder...")
    # Using smaller projection dim for demo speed/memory if needed, but 64 is already small
    encoder = TextureEncoder(project_dim=64)
    if encoder.model is None:
        print("[FAIL] Model load failed.")
        return

    # 3. Create Synthetic Audio Samples
    # We will create two "Similar" textures (e.g. constant tone + noise) 
    # and one "Different" texture (e.g. silence intervals or different freq)
    print("\n[Data] Generating synthetic audio samples...")
    sr = 16000
    dur = 3.0
    
    # Sample A: 440Hz Sine + Noise
    t = np.linspace(0, dur, int(sr*dur))
    sine_a = 0.5 * np.sin(2 * np.pi * 440 * t)
    noise_a = 0.1 * np.random.normal(0, 1, len(t))
    audio_a = sine_a + noise_a
    path_a = "temp_A_sine_noise.wav"
    sf.write(path_a, audio_a, sr)
    
    # Sample B: 440Hz Sine + Noise (Different random noise, same texture)
    # This should have HIGH similarity to A in Texture space (Gram Matrix captures correlations)
    noise_b = 0.1 * np.random.normal(0, 1, len(t)) # Different noise instance
    audio_b = sine_a + noise_b 
    path_b = "temp_B_sine_noise_diff.wav"
    sf.write(path_b, audio_b, sr)
    
    # Sample C: Pulse/Square wave (Different Timbre)
    # Square wave has different harmonics -> different layer activation correlations
    square_c = 0.5 * np.sign(np.sin(2 * np.pi * 110 * t)) # Different freq too
    path_c = "temp_C_square.wav"
    sf.write(path_c, square_c, sr)
    
    # 4. Compute Embeddings
    print("\n[Compute] Calculating Texture Embeddings...")
    emb_a = encoder.get_embedding(path_a)
    emb_b = encoder.get_embedding(path_b)
    emb_c = encoder.get_embedding(path_c)
    
    if emb_a is None or emb_b is None or emb_c is None:
        print("[FAIL] Embedding generation failed.")
        return

    # 5. Measure Similarity (Cosine)
    print("\n[Results] Cosine Similarity (Texture Space):")
    
    sim_ab = similarity_score(emb_a, emb_b)
    sim_ac = similarity_score(emb_a, emb_c)
    sim_bc = similarity_score(emb_b, emb_c)
    
    print(f"A (Sine+Noise) vs B (Sine+Noise'): {sim_ab:.4f}")
    print(f"A (Sine+Noise) vs C (Square Wave):  {sim_ac:.4f}")
    
    # 6. Interpret
    print("\n[Analysis]")
    if sim_ab > sim_ac:
        print("SUCCESS: Similar textures (A & B) have higher similarity than different intensity/timbre (A & C).")
        print(f"Margin: {sim_ab - sim_ac:.4f}")
    else:
        print("WARNING: Texture discrimination might be weak or samples are too simple.")

    # Cleanup
    for p in [path_a, path_b, path_c]:
        if os.path.exists(p):
            os.remove(p)

    print("\nDone.")

if __name__ == "__main__":
    run_demo()
