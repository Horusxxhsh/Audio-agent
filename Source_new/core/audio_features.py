"""Audio feature extraction module.

Extracts Wav2Vec embeddings from audio files.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


class AudioFeatureExtractor:
    """Wraps Wav2Vec2 feature extraction with lazy model loading."""

    def __init__(self, model_name: str = "facebook/wav2vec2-base-960h") -> None:
        self._model_name = model_name
        self._processor = None
        self._model = None

    # -------- lazy loading ------------------------------------------------ #

    def _ensure_loaded(self) -> None:
        if self._processor is None or self._model is None:
            from transformers import Wav2Vec2Model, Wav2Vec2Processor  # noqa: PLC0415

            logger.info("Loading Wav2Vec2 model: %s", self._model_name)
            self._processor = Wav2Vec2Processor.from_pretrained(self._model_name)
            self._model = Wav2Vec2Model.from_pretrained(self._model_name)
            if torch.cuda.is_available():
                self._model = self._model.to("cuda")
                logger.info("Wav2Vec2 loaded on GPU.")
            else:
                logger.info("Wav2Vec2 loaded on CPU.")

    # -------- public API -------------------------------------------------- #

    def extract(self, file_path: str, sr: int = 16000) -> np.ndarray:
        """Return a mean-pooled Wav2Vec2 embedding for *file_path*.

        Args:
            file_path: Path to a WAV / audio file.
            sr: Target sample rate for librosa loading.

        Returns:
            1-D NumPy array (float32).
        """
        import librosa  # noqa: PLC0415

        self._ensure_loaded()

        audio, _ = librosa.load(file_path, sr=sr)
        inputs = self._processor(audio, sampling_rate=sr, return_tensors="pt")

        with torch.no_grad():
            outputs = self._model(**inputs)

        audio_vector = outputs.last_hidden_state.mean(dim=1).squeeze()
        return audio_vector.cpu().numpy().astype(np.float32)

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two 1-D vectors."""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))
