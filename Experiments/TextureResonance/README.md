# Texture Resonance Retrieval (TRR)

This module implements the **Texture Resonance Retrieval** system, which captures the "timbre" and "texture" of audio by analyzing the statistical correlations between deep feature channels (Gram Matrix), independent of time.

## Architecture

1.  **Source Purification**: `demucs` (htdemucs_6s) separates the guitar track.
2.  **Feature Extraction**: `wav2vec2-base` (Layer 5) extracts acoustic features.
3.  **Optimization**: Random Projection (768 -> 64 dim) reduces complexity.
4.  **Texture Encoding**: Gram Matrix calculation $(F^T \cdot F) / T$ captures channel co-occurrences.
5.  **Retrieval**: Flattened Gram Matrix (4096 dim) used for Cosine Similarity search.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements_trr.txt
    ```
    *Note: Requires `torch`, `torchaudio`, `transformers`, `demucs`.*

## Usage

### 1. Run Demo
```bash
python run_trr_demo.py
```
This script generates synthetic audio (Sine waves with different textures) and verifies that the TRR embedding correctly identifies texture similarity over timbre/frequency differences.

### 2. Use in Code
```python
from texture_encoder import TextureEncoder, SourcePurifier

# Initialize
encoder = TextureEncoder(project_dim=64)

# 1. Clean Audio (Optional but recommended)
clean_path = SourcePurifier.separate_guitar("input_mix.wav", "output_folder")

# 2. Get Embedding
embedding = encoder.get_embedding(clean_path)

# 3. Compare
sim = np.dot(emb_a, emb_b)
```

## Files
- `texture_encoder.py`: Core logic for Demucs wrapper and Wav2Vec2 Gram Matrix encoding.
- `run_trr_demo.py`: Verification script with synthetic data generation.
- `requirements_trr.txt`: Required Python packages.
- `outputs/`: Versioned comparison tables. New comparison runs write
  `outputs/texture_representation_comparison.csv` rather than the repository root.
