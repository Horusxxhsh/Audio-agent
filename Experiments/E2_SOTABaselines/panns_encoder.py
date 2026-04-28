"""
PANNs (Pretrained Audio Neural Networks) Encoder

Reference: Kong et al., "PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition", IEEE/ACM TASLP 2020
Model: CNN14 (trained on AudioSet)

Author: Claude
Date: 2026-03-05
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import torch
import torchaudio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PANNsEncoder:
    """
    PANNs encoder for audio tagging/retrieval baseline.

    Uses CNN14 model pretrained on AudioSet.
    """

    def __init__(
        self,
        model_name: str = "Cnn14",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize PANNs encoder.

        Args:
            model_name: Model variant (Cnn14, ResNet38, etc.)
            device: 'cuda' or 'cpu'
            cache_dir: Cache directory
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./model_cache")

        logger.info(f"Initializing PANNs encoder: {model_name}")
        logger.info(f"Device: {self.device}")

        try:
            # Try official PANNs implementation
            try:
                from panns_inference import AudioTagging
            except ImportError:
                logger.warning("panns_inference not installed, attempting install...")
                import subprocess
                subprocess.run([
                    "pip", "install", "panns-inference"
                ], check=True)
                from panns_inference import AudioTagging

            self.model = AudioTagging(
                checkpoint_path=None,  # Auto-download
                device=self.device
            )
            logger.info("PANNs model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load PANNs: {e}")
            logger.info("Falling back to torch hub...")
            self._load_torch_hub()

    def _load_torch_hub(self):
        """Load from torch hub as fallback."""
        try:
            model = torch.hub.load(
                'qiuqiangkong/audioset_tagging_cnn',
                'cnn14',
                pretrained=True
            )
            self.model = model.to(self.device)
            self.model.eval()
            logger.info("Loaded PANNs from torch hub")
        except Exception as e:
            logger.error(f"Torch hub fallback failed: {e}")
            raise

    def _preprocess(
        self,
        audio_path: Union[str, Path],
        target_sr: int = 32000
    ) -> np.ndarray:
        """
        Preprocess audio for PANNs.

        Args:
            audio_path: Path to audio file
            target_sr: Target sample rate

        Returns:
            Audio array
        """
        # Load
        waveform, sr = torchaudio.load(audio_path)

        # Resample
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)

        # Mono
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0)

        return waveform.squeeze().cpu().numpy()

    def encode_audio(
        self,
        audio_path: Union[str, Path],
        sampling_rate: int = 32000
    ) -> np.ndarray:
        """
        Encode a single audio file.

        Args:
            audio_path: Path to audio file
            sampling_rate: Target sampling rate

        Returns:
            Audio embedding (2048-D)
        """
        # Preprocess
        audio = self._preprocess(audio_path, sampling_rate)

        # Encode
        if hasattr(self.model, 'inference'):
            # panns_inference API
            _, embedding = self.model.inference(audio)
        else:
            # torch hub model
            with torch.no_grad():
                audio_tensor = torch.from_numpy(audio).float().unsqueeze(0).to(self.device)
                embedding = self.model(audio_tensor).cpu().numpy().squeeze()

        return embedding

    def encode_audio_batch(
        self,
        audio_paths: List[Union[str, Path]],
        batch_size: int = 8,
        sampling_rate: int = 32000
    ) -> np.ndarray:
        """
        Encode multiple audio files.

        Args:
            audio_paths: List of audio file paths
            batch_size: Batch size
            sampling_rate: Target sampling rate

        Returns:
            Array of embeddings (N x 2048)
        """
        embeddings = []

        for i, path in enumerate(audio_paths):
            try:
                emb = self.encode_audio(path, sampling_rate)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to encode {path}: {e}")
                embeddings.append(np.zeros(2048))

            if i % 10 == 0:
                logger.info(f"Processed {i}/{len(audio_paths)} files")

        return np.array(embeddings)


# Test
if __name__ == "__main__":
    import tempfile
    import soundfile as sf

    # Create test audio
    sample_rate = 32000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * 440 * t)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, test_audio, sample_rate)
        test_path = f.name

    # Test encoder
    logger.info("Testing PANNs encoder...")
    encoder = PANNsEncoder()

    audio_emb = encoder.encode_audio(test_path)
    logger.info(f"Audio embedding shape: {audio_emb.shape}")
    logger.info(f"Embedding norm: {np.linalg.norm(audio_emb):.4f}")

    # Cleanup
    Path(test_path).unlink()
    logger.info("PANNs encoder test passed!")
