"""Centralized configuration manager for Audio Agent.

Provides cross-platform path resolution, API key management,
and MusicGen parameter configuration.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Paths:
    """Resolved filesystem paths."""

    _supertonal_dir: str | None = None
    _documents_dir: str | None = None

    @property
    def supertonal_dir(self) -> Path:
        """Base directory for Supertonal DSP data."""
        if self._supertonal_dir is None:
            raw = os.environ.get("SUPERTONAL_DIR", None)
            if raw:
                self._supertonal_dir = raw
            else:
                # Default: cross-platform documents folder
                if platform.system() == "Windows":
                    base = Path(os.environ.get("PUBLIC", "C:\\Users\\Public"))
                    self._supertonal_dir = str(base / "Documents" / "Supertonal DSP")
                else:
                    self._supertonal_dir = str(Path.home() / "Supertonal_DSP")
        return Path(self._supertonal_dir)

    @property
    def documents_dir(self) -> Path | None:
        """Optional fallback documents directory."""
        if self._documents_dir is None:
            raw = os.environ.get("DOCUMENTS_DIR", None)
            if raw:
                self._documents_dir = raw
            else:
                self._documents_dir = None
        return Path(self._documents_dir) if self._documents_dir else None

    @property
    def music_db(self) -> Path:
        return self.supertonal_dir / "music_info.db"

    @property
    def audio_db(self) -> Path:
        return self.supertonal_dir / "audio_info.db"

    @property
    def preset_dir(self) -> Path:
        return self.supertonal_dir / "HCAP"

    @property
    def vector_db_dir(self) -> Path:
        return self.supertonal_dir / "vector_db"

    @property
    def import_dir(self) -> Path:
        return self.supertonal_dir / "import"


@dataclass
class APIConfig:
    """LLM API configuration."""

    _api_key: str | None = None
    _base_url: str = "https://api.deepseek.com"
    _model_name: str = "deepseek-chat"

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = (
                os.environ.get("DEEPSEEK_API_KEY")
                or os.environ.get("OPENAI_API_KEY", "")
            )
        if not self._api_key:
            raise RuntimeError(
                "No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY."
            )
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_name(self) -> str:
        return self._model_name

    def validate(self) -> bool:
        try:
            _ = self.api_key
            return True
        except RuntimeError:
            return False


@dataclass
class MusicGenConfig:
    """MusicGen audio generation settings."""

    enabled: bool = True
    model_name: str = "facebook/musicgen-small"
    duration_seconds: int = 8
    use_cuda: bool = True


@dataclass
class Config:
    """Top-level configuration aggregator."""

    paths: Paths = field(default_factory=Paths)
    api: APIConfig = field(default_factory=APIConfig)
    musicgen: MusicGenConfig = field(default_factory=MusicGenConfig)

    # ------------------------------------------------------------------ #
    #  Convenience helpers
    # ------------------------------------------------------------------ #

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        for p in (
            self.paths.supertonal_dir,
            self.paths.preset_dir,
            self.paths.vector_db_dir,
            self.paths.import_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)
