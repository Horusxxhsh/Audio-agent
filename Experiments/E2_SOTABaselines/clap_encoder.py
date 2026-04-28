"""
CLAP (Contrastive Language-Audio Pretraining) Encoder for TMM Baseline Comparison

Reference: Wu et al., "Large-Scale Contrastive Language-Audio Pretraining", ICLR 2023
Model: LAION-CLAP (microsoft/laion-clap)

Author: Claude
Date: 2026-03-05
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import torch
import torchaudio
from transformers import AutoProcessor, ClapModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CLAPEncoder:
    """
    CLAP encoder for audio-text retrieval baseline.

    Uses LAION-CLAP model for extracting audio embeddings.
    """

    def __init__(
        self,
        model_name: str = "laion/clap-htsat-fused",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize CLAP encoder.

        Args:
            model_name: HuggingFace model name
            device: 'cuda' or 'cpu' (auto-detect if None)
            cache_dir: Directory to cache model files
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./model_cache")
        self.cache_dir.mkdir(exist_ok=True)

        logger.info(f"Initializing CLAP encoder: {model_name}")
        logger.info(f"Device: {self.device}")

        # Load model and processor
        try:
            self.processor = AutoProcessor.from_pretrained(
                model_name,
                cache_dir=self.cache_dir
            )
            self.model = ClapModel.from_pretrained(
                model_name,
                cache_dir=self.cache_dir
            ).to(self.device)
            self.model.eval()

            logger.info("CLAP model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load CLAP model: {e}")
            logger.info("Attempting to use laion/larger_clap_general...")
            # Fallback to alternative model
            self.model_name = "laion/larger_clap_general"
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = ClapModel.from_pretrained(self.model_name).to(self.device)
            self.model.eval()

    def encode_audio(
        self,
        audio_path: Union[str, Path],
        sampling_rate: int = 48000
    ) -> np.ndarray:
        """
        Encode a single audio file.

        Args:
            audio_path: Path to audio file
            sampling_rate: Target sampling rate (CLAP expects 48kHz)

        Returns:
            Audio embedding vector (512-D for base model)
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)

        # Resample if necessary
        if sr != sampling_rate:
            resampler = torchaudio.transforms.Resample(sr, sampling_rate)
            waveform = resampler(waveform)

        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Process
        inputs = self.processor(
            audios=waveform.squeeze().numpy(),
            sampling_rate=sampling_rate,
            return_tensors="pt"
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Encode
        with torch.no_grad():
            outputs = self.model.get_audio_features(**inputs)

        # Convert to numpy
        embedding = outputs.cpu().numpy().squeeze()

        return embedding

    def encode_audio_batch(
        self,
        audio_paths: List[Union[str, Path]],
        batch_size: int = 8,
        sampling_rate: int = 48000
    ) -> np.ndarray:
        """
        Encode multiple audio files in batches.

        Args:
            audio_paths: List of audio file paths
            batch_size: Batch size for processing
            sampling_rate: Target sampling rate

        Returns:
            Array of embeddings (N x 512)
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
                    # Use zero embedding as fallback
                    batch_embeddings.append(np.zeros(512))

            embeddings.extend(batch_embeddings)

            if (i // batch_size) % 10 == 0:
                logger.info(f"Processed {i}/{len(audio_paths)} files")

        return np.array(embeddings)

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text query.

        Args:
            text: Text description

        Returns:
            Text embedding vector
        """
        inputs = self.processor(
            text=text,
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)

        return outputs.cpu().numpy().squeeze()

    def compute_similarity(
        self,
        audio_embedding: np.ndarray,
        text_embedding: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between audio and text embeddings.

        Args:
            audio_embedding: Audio embedding
            text_embedding: Text embedding

        Returns:
            Cosine similarity score
        """
        # Normalize
        audio_norm = audio_embedding / (np.linalg.norm(audio_embedding) + 1e-8)
        text_norm = text_embedding / (np.linalg.norm(text_embedding) + 1e-8)

        # Cosine similarity
        similarity = np.dot(audio_norm, text_norm)

        return float(similarity)


# Test
if __name__ == "__main__":
    import tempfile
    import soundfile as sf

    # Create test audio
    sample_rate = 48000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, test_audio, sample_rate)
        test_path = f.name

    # Test encoder
    logger.info("Testing CLAP encoder...")
    encoder = CLAPEncoder()

    # Encode audio
    audio_emb = encoder.encode_audio(test_path)
    logger.info(f"Audio embedding shape: {audio_emb.shape}")
    logger.info(f"Audio embedding norm: {np.linalg.norm(audio_emb):.4f}")

    # Encode text
    text_emb = encoder.encode_text("guitar with warm distortion")
    logger.info(f"Text embedding shape: {text_emb.shape}")

    # Compute similarity
    sim = encoder.compute_similarity(audio_emb, text_emb)
    logger.info(f"Audio-text similarity: {sim:.4f}")

    # Cleanup
    Path(test_path).unlink()
    logger.info("CLAP encoder test passed!")
