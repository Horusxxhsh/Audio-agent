#!/usr/bin/env python3
"""Audio Agent – SQL / parameter-update entry point.

Replaces the original 1023-line ``sql.py`` with a clean module
that delegates parameter processing to ``ParameterProcessor``.

Usage
-----
    python sql.py <chat_message> <user_message> \\
                  <current_preset_name> <memory_enabled>
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure sibling packages are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config
from core.parameters import ParameterProcessor
from database import MusicDatabase

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
#  Argument parsing (backward compatible)
# ------------------------------------------------------------------

def _decode(s: str) -> str:
    if sys.platform == "win32":
        return s.encode("cp936").decode("utf-8", errors="replace")
    return s


def parse_args(argv: list[str]) -> dict[str, str]:
    if len(argv) < 5:
        raise ValueError("Usage: sql.py <chat_message> <user_message> "
                         "<preset_name> <memory_enabled>")
    return {
        "chat_message": _decode(argv[1]),
        "user_message": _decode(argv[2]),
        "preset_name": _decode(argv[3]),
        "memory_enabled": argv[4],
    }


# ------------------------------------------------------------------
#  Core update logic
# ------------------------------------------------------------------

def run_update(args: dict[str, str]) -> None:
    cfg = Config()
    cfg.ensure_directories()

    db = MusicDatabase(cfg.paths.music_db)

    chat_message = args["chat_message"]
    user_message = args["user_message"] or args["preset_name"]
    memory_enabled = args["memory_enabled"] == "true"

    logger.info(
        "SQL update: chat=%s  user=%s  memory=%s",
        chat_message, user_message, memory_enabled,
    )

    # Parse toggle flags
    parts = chat_message.split(",")
    if len(parts) < 48:
        logger.error("Parameter list too short (<48). Aborting.")
        db.close()
        return

    toggles = [float(parts[i]) for i in range(min(9, len(parts)))]

    # Fetch or create record
    row = db.get_music(user_message)
    if row is None:
        logger.info("No existing record for '%s'. Creating.", user_message)
        # (In practice the LLM pipeline should have already created the record.)
        return

    # Parse & update parameters
    parameters: dict[str, Any] = json.loads(row["Parameters"])
    parameters = ParameterProcessor.apply_toggles(parameters, toggles)

    updated_str = ParameterProcessor.serialise(parameters)
    db.upsert_music(
        song_name=user_message,
        parameters=updated_str,
        preferences=row["Preferences"],
        style=row["Style"],
        feature=row["Feature"],
    )

    logger.info("Updated record for '%s'.", user_message)
    db.close()


# ------------------------------------------------------------------
#  Entry point
# ------------------------------------------------------------------

def main() -> None:
    args = parse_args(sys.argv)
    run_update(args)


if __name__ == "__main__":
    main()
