"""Tests for database module."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from database import MusicDatabase


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_music.db"


@pytest.fixture
def db(temp_db_path: Path) -> MusicDatabase:
    return MusicDatabase(temp_db_path)


class TestMusicDatabase:
    def test_tables_created(self, db: MusicDatabase):
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "music_responses" in tables

    def test_upsert_insert(self, db: MusicDatabase):
        db.upsert_music(
            song_name="Test Song",
            parameters='{"ReverbOn": {}}',
            preferences="accept",
            style='["ambient"]',
            feature='["test"]',
        )
        row = db.get_music("Test Song")
        assert row is not None
        assert row["SongName"] == "Test Song"
        assert row["Preferences"] == "accept"

    def test_upsert_update(self, db: MusicDatabase):
        db.upsert_music(
            song_name="Test Song",
            parameters='{"v": 1}',
            preferences="accept",
            style='[]',
            feature='[]',
        )
        db.upsert_music(
            song_name="Test Song",
            parameters='{"v": 2}',
            preferences="edit",
            style='["ambient"]',
            feature='["updated"]',
        )
        row = db.get_music("Test Song")
        assert row["Parameters"] == '{"v": 2}'
        assert row["Preferences"] == "edit"

    def test_get_missing_returns_none(self, db: MusicDatabase):
        row = db.get_music("Nonexistent")
        assert row is None

    def test_list_music(self, db: MusicDatabase):
        db.upsert_music("Song A", "{}", "accept", "[]", "[]")
        db.upsert_music("Song B", "{}", "edit", "[]", "[]")
        rows = db.list_music()
        assert len(rows) >= 2

    def test_audio_vector(self, db: MusicDatabase):
        db.upsert_audio_vector(
            parameters='{"test": 1}',
            vector="0.1,0.2,0.3",
        )
        rows = db.list_audio_vectors()
        assert any(r["Vector"] == "0.1,0.2,0.3" for r in rows)

    def test_close(self, temp_db_path: Path):
        db = MusicDatabase(temp_db_path)
        db.close()
        # Connections should be set to None after close
        assert db._conn is None
        assert db._audio_conn is None

    def test_context_manager(self, temp_db_path: Path):
        with MusicDatabase(temp_db_path) as db:
            db.upsert_music("Ctx Song", "{}", "accept", "[]", "[]")
            assert db.get_music("Ctx Song") is not None
