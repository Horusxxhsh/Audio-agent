"""Tests for config management module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from config.config_manager import (
    APIConfig,
    Config,
    MusicGenConfig,
    Paths,
)


class TestPaths:
    def test_supertonal_dir_default(self):
        p = Paths()
        assert isinstance(p.supertonal_dir, Path)

    def test_supertonal_dir_from_env(self):
        with patch.dict(os.environ, {"SUPERTONAL_DIR": "/tmp/test_supertonal"}):
            p = Paths()
            assert str(p.supertonal_dir) == "/tmp/test_supertonal"

    def test_music_db_path(self):
        p = Paths()
        assert p.music_db.name == "music_info.db"

    def test_preset_dir_path(self):
        p = Paths()
        assert p.preset_dir.name == "HCAP"

    def test_ensure_directories_on_config(self, tmp_path: Path):
        """ensure_directories lives on Config, not Paths."""
        cfg = Config()
        with patch.object(Path, "mkdir") as mock_mkdir:
            cfg.ensure_directories()
            assert mock_mkdir.call_count >= 1


class TestAPIConfig:
    def test_api_key_from_env(self):
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "test-key-123", "OPENAI_API_KEY": ""},
        ):
            cfg = APIConfig()
            assert cfg.api_key == "test-key-123"

    def test_api_key_fallback(self):
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "", "OPENAI_API_KEY": "openai-key-456"},
        ):
            cfg = APIConfig()
            assert cfg.api_key == "openai-key-456"

    def test_api_key_missing_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = APIConfig()
            with pytest.raises(RuntimeError, match="No API key found"):
                _ = cfg.api_key

    def test_validate_success(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "key"}):
            cfg = APIConfig()
            assert cfg.validate() is True

    def test_validate_failure(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = APIConfig()
            assert cfg.validate() is False

    def test_default_base_url(self):
        cfg = APIConfig()
        assert cfg.base_url == "https://api.deepseek.com"

    def test_default_model(self):
        cfg = APIConfig()
        assert cfg.model_name == "deepseek-chat"


class TestMusicGenConfig:
    def test_defaults(self):
        cfg = MusicGenConfig()
        assert cfg.enabled is True
        assert cfg.model_name == "facebook/musicgen-small"
        assert cfg.duration_seconds == 8
        assert cfg.use_cuda is True


class TestConfig:
    def test_aggregator(self):
        cfg = Config()
        assert isinstance(cfg.paths, Paths)
        assert isinstance(cfg.api, APIConfig)
        assert isinstance(cfg.musicgen, MusicGenConfig)
