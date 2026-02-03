import os
import torch
import torch.nn as nn
import torchaudio
import numpy as np
import subprocess
from pathlib import Path
from typing import Optional, Union, List

# Try imports
try:
    from transformers import Wav2Vec2Model
except ImportError:
    Wav2Vec2Model = None
    print("Warning: transformers not installed. Feature extraction will fail.")

class SourcePurifier:
    """
    Stage 1: Source Purification
    Uses Demucs to separate the guitar track from the mix.
    """
    @staticmethod
    def separate_guitar(input_audio_path: str, output_dir: str) -> Optional[str]:
        """
        Runs demucs to separate audio stems.
        Returns the path to the separated guitar track.
        """
        input_path = Path(input_audio_path)
        if not input_path.exists():
            print(f"Error: Input file not found: {input_audio_path}")
            return None
            
        print(f"Purifying source: {input_path.name}...")
        
        # Command: demucs -n htdemucs_6s <input> -o <output>
        # htdemucs_6s includes specialized guitar separation
        cmd = [
            "demucs",
            "-n", "htdemucs_6s",
            str(input_path),
            "-o", str(output_dir)
        ]
        
        try:
            # Check if demucs is installed/runnable
            subprocess.run(cmd, check=True)
            
            # Expected output path structure: <output_dir>/htdemucs_6s/<song_name>/guitar.wav
            # Note: Demucs usually creates a folder with the input filename (minus extension)
            song_name = input_path.stem
            guitar_path = Path(output_dir) / "htdemucs_6s" / song_name / "guitar.wav"
            
            if guitar_path.exists():
                return str(guitar_path)
            else:
                # Fallback: check 'other' if guitar specific model wasn't used or failed
                other_path = Path(output_dir) / "htdemucs_6s" / song_name / "other.wav"
                if other_path.exists():
                    print("Warning: Guitar track not found, returning 'other' stem.")
                    return str(other_path)
                print(f"Error: Separation output not found at {guitar_path}")
                return None
                
        except Exception as e:
            print(f"Demucs separation failed: {e}")
            return None

class TextureEncoder:
    """
    Stage 2 & 3 & 4: Feature Extraction, Texture Encoding (Gram Matrix), and Optimization.

    P2 IMPROVEMENTS:
    - Reduced projection dimension from 64 to 32 for better generalization
    - Multi-layer Gram fusion from layers 4, 5, 6
    """
    def __init__(self, device=None, project_dim=32):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.project_dim = project_dim  # P2: 降低维度防止过拟合

        # Load Wav2Vec2 Model
        if Wav2Vec2Model:
            print("Loading Wav2Vec2 model...")
            self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base").to(self.device)
            self.model.eval()
        else:
            self.model = None

        # Random Projection Layer (Frozen)
        # P2: 优化后的投影维度（32 -> 32*32=1024维特征，更适合小数据集）
        self.projector = nn.Linear(768, self.project_dim).to(self.device)
        for param in self.projector.parameters():
            param.requires_grad = False
            
    def load_and_preprocess(self, audio_path: str) -> Optional[torch.Tensor]:
        """Loads audio, resamples to 16k, and normalizes."""
        try:
            # Prioritize direct soundfile load to avoid TorchCodec issues
            try:
                import soundfile as sf
                data, sample_rate = sf.read(audio_path)
                waveform = torch.from_numpy(data).float()
                if waveform.dim() == 1:
                    waveform = waveform.unsqueeze(0) # [1, T]
                else:
                    waveform = waveform.t() # [C, T]
            except Exception as e_sf:
                # Fallback to torchaudio if soundfile fails
                print(f"Direct soundfile load failed: {e_sf}, trying torchaudio...")
                try:
                    waveform, sample_rate = torchaudio.load(audio_path)
                except Exception as e_ta:
                    print(f"Torchaudio load also failed: {e_ta}")
                    return None
            
            # Resample to 16kHz
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000).to(waveform.device)
                waveform = resampler(waveform)
            
            # Mix to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                
            # Normalize (Crucial for timbre analysis)
            # (x - mean) / std
            waveform = (waveform - waveform.mean()) / torch.sqrt(waveform.var() + 1e-7)
            
            return waveform.to(self.device)
        except Exception as e:
            print(f"Error loading audio {audio_path}: {e}")
            return None

    def extract_features(self, input_values: torch.Tensor, layer_idx: int = 5) -> torch.Tensor:
        """Extracts features from specific Wav2Vec2 layer."""
        if self.model is None:
            raise RuntimeError("Wav2Vec2 model not initialized.")
            
        with torch.no_grad():
            outputs = self.model(input_values, output_hidden_states=True)
            
        # outputs.hidden_states is a tuple of (embedding_output, layer_1, ..., layer_12)
        # index 0 is embeddings, index 1 is layer 1...
        # The user requested layers 4-6. 
        # Layer 5 output is at index 5 in hidden_states tuple (0-based) ?
        # Actually usually hidden_states[0] is CNN output, [1] is Transformer Layer 1.
        # Let's stick to the user's snippet: outputs.hidden_states[layer_idx]
        
        feature_map = outputs.hidden_states[layer_idx]
        return feature_map # [Batch, Time, Channels]

    def compute_gram_matrix(self, features: torch.Tensor) -> torch.Tensor:
        """
        Computes Gram Matrix to capture texture (channel correlations).
        Removes temporal dimension.
        """
        # Features: [1, Time, Dim] -> [Time, Dim]
        feats = features.squeeze(0)

        n_time = feats.shape[0]

        # Projection (Optimization)
        # [Time, 768] -> [Time, project_dim]
        projected = self.projector(feats)

        # Gram Matrix: (F.T @ F) / N
        # [project_dim, Time] @ [Time, project_dim] -> [project_dim, project_dim]
        gram = torch.matmul(projected.T, projected)
        gram = gram / n_time

        return gram

    def get_embedding(self, audio_path: str) -> Union[np.ndarray, None]:
        """
        P2 IMPROVED: Full pipeline with multi-layer Gram fusion.
        Audio -> Features -> Multi-layer Projection -> Gram Fusion -> Flatten -> Norm
        """
        # 1. Preprocess
        waveform = self.load_and_preprocess(audio_path)
        if waveform is None: return None

        # 2. P2: Multi-layer Feature Extraction (Layers 4, 5, 6)
        # 这些层在中层语义特征和纹理特征之间取得平衡
        layer_indices = [4, 5, 6]
        gram_matrices = []

        for layer_idx in layer_indices:
            raw_features = self.extract_features(waveform, layer_idx=layer_idx)
            gram_matrix = self.compute_gram_matrix(raw_features)
            gram_matrices.append(gram_matrix)

        # 3. P2: 融合多个层的Gram Matrix（平均池化）
        # 每个Gram Matrix形状: [project_dim, project_dim]
        fused_gram = torch.stack(gram_matrices).mean(dim=0)

        # 4. Flatten and Normalize
        # Flatten: [project_dim, project_dim] -> [project_dim^2]
        # 对于project_dim=32: [32, 32] -> [1024]
        embedding_vec = fused_gram.flatten()

        # L2 Normalize
        embedding_vec = torch.nn.functional.normalize(embedding_vec, p=2, dim=0)

        return embedding_vec.cpu().numpy()

def similarity_score(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity for normalized vectors."""
    return float(np.dot(vec_a, vec_b))

# --- Demo / Test Logic ---
if __name__ == "__main__":
    print("--- Texture Resonance Retrieval (TRR) Unit Test ---")
    
    # 1. Create a dummy encoder
    print("Initializing Encoder...")
    if torch.cuda.is_available():
        print("Using CUDA")
    else:
        print("Using CPU")
        
    try:
        encoder = TextureEncoder(project_dim=64)
        
        # 2. Create Dummy Audio (White Noise)
        print("Creating mock audio...")
        sr = 16000
        duration = 2.0 # seconds
        dummy_wav = torch.randn(1, int(sr * duration))
        
        # Mocking the load_and_preprocess by manually setting it, 
        # or we can save it to a temp file to test the full pipeline.
        import soundfile as sf
        temp_file = "temp_test_noise.wav"
        sf.write(temp_file, dummy_wav.squeeze().numpy(), sr)
        
        # 3. Process
        print(f"Processing {temp_file}...")
        emb = encoder.get_embedding(temp_file)
        
        if emb is not None:
            print(f"Embedding Shape: {emb.shape}") # Should be 64*64 = 4096
            print(f"Embedding Norm: {np.linalg.norm(emb):.4f}") # Should be 1.0
            print("Success: Pipeline functional on mock audio.")
        else:
            print("Failed to generate embedding.")
            
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
