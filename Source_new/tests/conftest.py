"""Shared pytest fixtures for Audio Agent tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a dummy API key so tests don't fail on env lookup."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-dummy")
    monkeypatch.setenv("OPENAI_API_KEY", "")


@pytest.fixture(autouse=True)
def mock_supertonal_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point SUPERTONAL_DIR to a temp directory for isolation."""
    d = tmp_path / "supertonal"
    d.mkdir()
    monkeypatch.setenv("SUPERTONAL_DIR", str(d))
    return d
