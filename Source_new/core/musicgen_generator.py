"""MusicGen audio generation module.

Handles lazy loading of the MusicGen model and audio synthesis.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


class MusicGenGenerator:
    """Lazy-loaded MusicGen model wrapper."""

    def __init__(
        self,
        model_name: str = "facebook/musicgen-small",
        duration_seconds: int = 8,
        use_cuda: bool = True,
    ) -> None:
        self._model_name = model_name
        self._duration = duration_seconds
        self._use_cuda = use_cuda
        self._model = None
        self._processor = None

    # -------- lazy loading ------------------------------------------------ #

    def _ensure_loaded(self) -> tuple:
        if self._model is None or self._processor is None:
            try:
                from transformers import (  # noqa: PLC0415
                    AutoProcessor,
                    MusicgenForConditionalGeneration,
                )

                logger.info("Loading MusicGen model: %s", self._model_name)
                self._processor = AutoProcessor.from_pretrained(self._model_name)
                self._model = MusicgenForConditionalGeneration.from_pretrained(
                    self._model_name
                )

                if torch.cuda.is_available() and self._use_cuda:
                    self._model = self._model.to("cuda")
                    logger.info("MusicGen loaded on GPU.")
                else:
                    logger.info("MusicGen loaded on CPU (slower).")
            except ImportError as exc:
                logger.error("transformers library issue: %s", exc)
                raise
            except Exception as exc:
                logger.error("Failed to load MusicGen: %s", exc)
                raise

        return self._model, self._processor

    # -------- public API -------------------------------------------------- #

    def generate(self, prompt: str, output_path: str) -> bool:
        """Generate audio from *prompt* and write to *output_path*.

        Returns ``True`` on success.
        """
        model, processor = self._ensure_loaded()

        try:
            logger.info("Generating audio for prompt: %s", prompt)

            inputs = processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            )

            if torch.cuda.is_available() and self._use_cuda:
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            max_new_tokens = self._duration * 50
            logger.info("Generating %d seconds of audio ...", self._duration)

            audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

            sampling_rate = model.config.audio_encoder.sampling_rate
            audio_data = audio_values[0, 0].cpu().numpy().astype(np.float32)

            # Normalize with headroom
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = audio_data / max_val * 0.95

            # Save
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            import scipy.io.wavfile  # noqa: PLC0415

            scipy.io.wavfile.write(
                output_path, rate=int(sampling_rate), data=audio_data
            )

            if os.path.exists(output_path):
                logger.info(
                    "Audio saved: %s (%d bytes)",
                    output_path,
                    os.path.getsize(output_path),
                )
                return True
            return False

        except Exception as exc:
            logger.error("Audio generation failed: %s", exc)
            return False
