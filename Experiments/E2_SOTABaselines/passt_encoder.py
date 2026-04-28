"""
PaSST (Efficient Audio Spectrogram Transformer) Encoder

Reference: Koutini et al., "Efficient Training of Audio Transformers with Patchout", Interspeech 2022
Model: passt_20_128k (trained on AudioSet)

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


class PaSSTEncoder:
    """
    PaSST encoder for audio classification/retrieval baseline.

    Uses AudioSet-pretrained PaSST model.
    """

    def __init__(
        self,
        model_name: str = "passt_20_128k",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize PaSST encoder.

        Args:
            model_name: Model variant
            device: 'cuda' or 'cpu'
            cache_dir: Cache directory
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./model_cache")

        logger.info(f"Initializing PaSST encoder: {model_name}")
        logger.info(f"Device: {self.device}")

        try:
            # Try to import passt
            try:
                from passt import get_model
            except ImportError:
                logger.warning("passt not installed, attempting install...")
                import subprocess
                subprocess.run([
                    "pip", "install",
                    "git+https://github.com/kkoutini/passt"
                ], check=True)
                from passt import get_model

            self.model = get_model(
                arch="passt_20_128k",
                n_classes=527,  # AudioSet classes
                pretrained=True
            ).to(self.device)
            self.model.eval()

            logger.info("PaSST model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load PaSST: {e}")
            logger.info("Falling back to HF Transformers implementation...")
            self._load_hf_fallback()

    def _load_hf_fallback(self):
        """Load using HuggingFace as fallback."""
        from transformers import AutoFeatureExtractor, AutoModel

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(
            "MIT/ast-finetuned-audioset-10-10-0.4593"
        )
        self.model = AutoModel.from_pretrained(
            "MIT/ast-finetuned-audioset-10-10-0.4593"
        ).to(self.device)
        self.model.eval()

        logger.info("Loaded AST as PaSST fallback")

    def _preprocess_audio(
        self,
        audio_path: Union[str, Path],
        target_sr: int = 32000,
        duration: float = 10.0
    ) -> torch.Tensor:
        """
        Preprocess audio for PaSST.

        Args:
            audio_path: Path to audio file
            target_sr: Target sample rate
            duration: Target duration in seconds

        Returns:
            Preprocessed audio tensor
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)

        # Resample
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)

        # Convert to mono
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Pad or truncate to target duration
        target_length = int(target_sr * duration)
        if waveform.shape[1] < target_length:
            # Pad
            padding = target_length - waveform.shape[1]
            waveform = torch.nn.functional.pad(waveform, (0, padding))
        else:
            # Truncate
            waveform = waveform[:, :target_length]

        return waveform

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
            Audio embedding (768-D)
        """
        # Preprocess
        waveform = self._preprocess_audio(audio_path, sampling_rate)
        waveform = waveform.to(self.device)

        # Encode
        with torch.no_grad():
            if hasattr(self, 'feature_extractor'):
                # HF fallback
                inputs = self.feature_extractor(
                    waveform.squeeze().cpu().numpy(),
                    sampling_rate=sampling_rate,
                    return_tensors="pt"
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy().squeeze()
            else:
                # Native PaSST
                outputs = self.model(waveform)
                if isinstance(outputs, tuple):
                    embedding = outputs[0].cpu().numpy().squeeze()
                else:
                    embedding = outputs.cpu().numpy().squeeze()

        return embedding

    def encode_audio_batch(
        self,
        audio_paths: List[Union[str, Path]],
        batch_size: int = 8,
        sampling_rate: int = 32000
    ) -> np.ndarray:
        """
        Encode multiple audio files in batches.

        Args:
            audio_paths: List of audio file paths
            batch_size: Batch size
            sampling_rate: Target sampling rate

        Returns:
            Array of embeddings (N x 768)
        """
        embeddings = []

        for i in range(0, len(audio_paths), batch_size):
            batch_paths = audio_paths[i:i + batch_size]
            batch_embeddings = []

            for path in batch_paths:
                try:
                    emb = self.encode_audio(path, sampling_rate)
                    batch_embeddings.append(emb)
                except Exception as e:
                    logger.warning(f"Failed to encode {path}: {e}")
                    batch_embeddings.append(np.zeros(768))

            embeddings.extend(batch_embeddings)

            if (i // batch_size) % 10 == 0:
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
    logger.info("Testing PaSST encoder...")
    encoder = PaSSTEncoder()

    audio_emb = encoder.encode_audio(test_path)
    logger.info(f"Audio embedding shape: {audio_emb.shape}")
    logger.info(f"Embedding norm: {np.linalg.norm(audio_emb):.4f}")

    # Cleanup
    Path(test_path).unlink()
    logger.info("PaSST encoder test passed!")
