"""SQLite database operations for music metadata and parameters.

Provides safe, parameterized CRUD operations.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MusicDatabase:
    """Manages ``music_info.db`` and ``audio_info.db`` lifecycles."""

    # ---------- table schemas ------------------------------------------------ #

    _MUSIC_SCHEMA = """
        CREATE TABLE IF NOT EXISTS music_responses (
            SongName TEXT PRIMARY KEY,
            Parameters TEXT,
            Preferences TEXT,
            Style TEXT,
            Feature TEXT
        )
    """

    _AUDIO_SCHEMA = """
        CREATE TABLE IF NOT EXISTS audio_vector (
            Parameters TEXT PRIMARY KEY,
            Vector TEXT
        )
    """

    # ---------- initialization ----------------------------------------------- #

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._audio_conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self._MUSIC_SCHEMA)
        self._conn.commit()

        audio_path = self._db_path.parent / "audio_info.db"
        self._audio_conn = sqlite3.connect(str(audio_path))
        self._audio_conn.row_factory = sqlite3.Row
        self._audio_conn.executescript(self._AUDIO_SCHEMA)
        self._audio_conn.commit()

    # ---- property accessors (context-manager friendly) ------------------------- #

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database connection closed.")
        return self._conn

    @property
    def audio_connection(self) -> sqlite3.Connection:
        if self._audio_conn is None:
            raise RuntimeError("Audio database connection closed.")
        return self._audio_conn

    # ---- music_responses CRUD ------------------------------------------------ #

    def upsert_music(
        self,
        song_name: str,
        parameters: str,
        preferences: str,
        style: str,
        feature: str,
    ) -> None:
        """Insert or update a music record."""
        self._conn.execute(
            """
            INSERT INTO music_responses
                (SongName, Parameters, Preferences, Style, Feature)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(SongName) DO UPDATE SET
                Parameters = excluded.Parameters,
                Preferences = excluded.Preferences,
                Style = excluded.Style,
                Feature = excluded.Feature
            """,
            (song_name, parameters, preferences, style, feature),
        )
        self._conn.commit()

    def get_music(self, song_name: str) -> dict[str, Any] | None:
        """Fetch a single music record by song name."""
        row = self._conn.execute(
            "SELECT * FROM music_responses WHERE SongName = ?",
            (song_name,),
        ).fetchone()
        return dict(row) if row else None

    def list_music(self) -> list[dict[str, Any]]:
        """Return all music records."""
        rows = self._conn.execute(
            "SELECT SongName, Parameters, Preferences, Style, Feature "
            "FROM music_responses"
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- audio_vector CRUD --------------------------------------------------- #

    def upsert_audio_vector(self, parameters: str, vector: str) -> None:
        """Insert or update an audio-vector record."""
        self._audio_conn.execute(
            """
            INSERT INTO audio_vector (Parameters, Vector)
            VALUES (?, ?)
            ON CONFLICT(Parameters) DO UPDATE SET Vector = excluded.Vector
            """,
            (parameters, vector),
        )
        self._audio_conn.commit()

    def list_audio_vectors(self) -> list[dict[str, str]]:
        """Return all audio-vector records."""
        rows = self._audio_conn.execute(
            "SELECT Parameters, Vector FROM audio_vector"
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- resource cleanup --------------------------------------------------- #

    def close(self) -> None:
        """Close all connections."""
        if self._conn:
            self._conn.close()
            self._conn = None
        if self._audio_conn:
            self._audio_conn.close()
            self._audio_conn = None

    def __enter__(self) -> "MusicDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
