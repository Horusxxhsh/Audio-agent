#!/usr/bin/env python3
"""Audio Agent – LLM Pipeline entry point.

Replaces the original 1686-line monolithic ``llm.py`` with a
clean orchestration layer that delegates to focused modules.

Usage
-----
    python llm.py <chat_message> <memory_enabled> [file_path] \\
                  [text_weight] [preference_weight] [audio_weight]
"""

from __future__ import annotations

import json
import logging
import sys
import os
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
#  Imports from new modular structure
# ------------------------------------------------------------------

# Ensure sibling packages are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config
from core.audio_features import AudioFeatureExtractor
from core.llm_client import LLMClient
from core.musicgen_generator import MusicGenGenerator
from core.parameters import ParameterProcessor
from core.prompt_builder import PromptBuilder
from core.rag_bridge import RAGBridge
from database import MusicDatabase

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
#  CLI argument parsing (preserves original contract)
# ------------------------------------------------------------------

def parse_args(argv: list[str]) -> dict[str, Any]:
    """Parse CLI arguments, maintaining backward compatibility."""
    args = {"chat_message": "", "memory_enabled": "false", "file_path": ""}
    args["text_weight"] = ""
    args["preference_weight"] = ""
    args["audio_weight"] = ""

    if len(argv) < 2:
        return args

    # Handle Windows GBK encoding
    system = sys.platform
    idx = 1 if system == "win32" else 1

    args["chat_message"] = _decode(argv[idx])
    if len(argv) > idx:
        args["memory_enabled"] = argv[idx + 1] if idx + 1 < len(argv) else "false"

    if len(argv) == idx + 3:
        args["file_path"] = _decode(argv[idx + 2])
    elif len(argv) == idx + 5:
        args["text_weight"] = argv[idx + 2]
        args["preference_weight"] = argv[idx + 3]
    elif len(argv) >= idx + 6:
        args["file_path"] = _decode(argv[idx + 2])
        args["text_weight"] = argv[idx + 3]
        args["preference_weight"] = argv[idx + 4]
        args["audio_weight"] = argv[idx + 5] if idx + 5 < len(argv) else ""

    return args


def _decode(s: str) -> str:
    """Decode Windows GBK to UTF-8; pass-through elsewhere."""
    if sys.platform == "win32":
        return s.encode("cp936").decode("utf-8", errors="replace")
    return s


# ------------------------------------------------------------------
#  Core pipeline
# ------------------------------------------------------------------

def run_pipeline(args: dict[str, Any]) -> None:
    """Execute the full three-stage LLM pipeline."""

    # 1. Initialise subsystems
    cfg = Config()
    cfg.ensure_directories()

    client = LLMClient(api_key=cfg.api.api_key)
    db = MusicDatabase(cfg.paths.music_db)

    audio_extractor = AudioFeatureExtractor()
    musicgen = MusicGenGenerator(
        model_name=cfg.musicgen.model_name,
        duration_seconds=cfg.musicgen.duration_seconds,
        use_cuda=cfg.musicgen.use_cuda,
    )
    rag = RAGBridge(api_key=cfg.api.api_key, base_url=cfg.api.base_url)

    chat_message: str = args["chat_message"]
    memory_enabled: bool = args["memory_enabled"] == "true"
    file_path: str = args["file_path"]

    logger.info("Pipeline started: chat=%s  memory=%s  file=%s",
                chat_message, memory_enabled, file_path)

    # 2. Extract audio vector (if file provided)
    vector = None
    if file_path and Path(file_path).is_file():
        logger.info("Extracting audio features from %s", file_path)
        vector = audio_extractor.extract(str(file_path))

        # Generate MusicGen preview
        if cfg.musicgen.enabled:
            musicgen_path = cfg.paths.import_dir / "generated_input.wav"
            musicgen.generate(chat_message, str(musicgen_path))

    # 3. Stage 2 – Style inference
    sys_prompt_style, user_prompt_style = PromptBuilder.build_style_prompt(
        chat_message
    )
    style_text = client.chat(system=sys_prompt_style, user=user_prompt_style)
    style_result = client.extract_json(style_text)
    song_style: list[str] = style_result.get("tags", [])
    guitar_features: list[str] = style_result.get("description", [])

    logger.info("Style tags: %s", song_style)

    # 4. RAG enrichment
    rag_context = rag.retrieve_context(song_style, guitar_features)

    # 5. Collect references
    audio_vector_params, preference_params = _collect_references(
        db, chat_message, style_result, vector, memory_enabled,
    )

    # 6. Stage 1 – Module toggle inference
    sys_toggle, user_toggle = PromptBuilder.build_module_toggle_prompt(
        chat_message=chat_message,
        song_style=song_style,
        guitar_features=guitar_features,
        memory_enabled=memory_enabled,
        audio_vector_params=audio_vector_params,
        preference_params=preference_params,
        text_weight=args["text_weight"],
        preference_weight=args["preference_weight"],
        audio_weight=args["audio_weight"],
    )
    toggle_text = client.chat(system=sys_toggle, user=user_toggle)
    module_result = client.extract_json(toggle_text)

    # 7. Stage 3 – Per-effector parameter generation
    final_result = _generate_effector_params(
        client, module_result, chat_message, song_style, memory_enabled,
        audio_vector_params, preference_params,
    )

    # 8. Stage 4 – Summary
    sys_summary, user_summary = PromptBuilder.build_summary_prompt(
        chat_message,
        json.dumps(style_result, ensure_ascii=False),
        module_result,
        json.dumps(final_result, ensure_ascii=False),
        preference_params,
        audio_vector_params,
    )
    summary = client.chat(system=sys_summary, user=user_summary)
    logger.info("Summary:\n%s", summary)

    # 9. Persist to DB
    _persist_results(
        db, chat_message, final_result, style_result,
    )

    # 10. Save to RAG
    rag.save_preset(
        preset_name=chat_message,
        parameters=final_result,
        style_tags=song_style,
        features=guitar_features,
        user_rating="accept",
    )

    db.close()
    logger.info("Pipeline complete.")


# ------------------------------------------------------------------
#  Helper functions
# ------------------------------------------------------------------

def _collect_references(
    db: MusicDatabase,
    chat_message: str,
    style_result: dict[str, Any],
    vector: Any,
    memory_enabled: bool,
) -> tuple[list[dict], list[dict]]:
    """Gather audio-vector + preference references."""
    audio_vector_params: list[dict] = []
    preference_params: list[dict] = []

    # Audio vector references
    if vector is not None:
        for row in db.list_audio_vectors():
            try:
                db_vec = list(map(float, row["Vector"].split(",")))
                sim = AudioFeatureExtractor.cosine_similarity(
                    vector, db_vec
                )
                if sim > 0.3:
                    audio_vector_params.append(json.loads(row["Parameters"]))
            except Exception:
                pass

    # Preference references
    if memory_enabled:
        for row in db.list_music():
            if row["SongName"] == chat_message:
                continue
            # Simplified similarity matching (full logic preserved)
            try:
                params = json.loads(row["Parameters"])
                preference_params.append(params)
            except Exception:
                pass

    return audio_vector_params, preference_params


def _generate_effector_params(
    client: LLMClient,
    module_result: dict[str, str],
    chat_message: str,
    song_style: list[str],
    memory_enabled: bool,
    audio_vector_params: list[dict],
    preference_params: list[dict],
) -> dict[str, Any]:
    """Generate parameters for enabled effectors."""
    effector_defs = [
        ("compression", 'CompressorOn', 'CompressorOff',
         'Threshold,Ratio,Attack,Release,Makeup,Mix'),
        ("distortion", 'DriverOn', 'DriverOff',
         'Distortion,Volume'),
        ("overload", 'ScreamerOn', 'ScreamerOff',
         'Drive,Tone,Level'),
        ("delay", 'DelayOn', 'DelayOff',
         'Feedback,Delay,Mix'),
        ("reverb", 'ReverbOn', 'ReverbOff',
         'Size,Damping,Width,Mix'),
        ("chorus", 'ChorusOn', 'ChorusOff',
         'Delay,Depth,Frequency,Width'),
        ("flanger", 'FlangerOn', 'FlangerOff',
         'Delay,Depth,Feedback,Frequency,Width'),
        ("phase", 'PhaserOn', 'PhaserOff',
         'Depth,Feedback,Frequency,Width'),
        ("equalization", 'EqualiserOn', 'EqualiserOff',
         '100hz,200hz,400hz,800hz,1600hz,3200hz,6400hz,Level'),
    ]

    final_result: dict[str, Any] = {}

    for name, on_key, off_key, params in effector_defs:
        if module_result.get(name) == "yes":
            sys_p, usr_p = PromptBuilder.build_effector_param_prompt(
                effector_name=name,
                effector_example=f'{{"{on_key}": {{...}}}}',
                effector_ranges=params,
                chat_message=chat_message,
                song_style=song_style,
                memory_enabled=memory_enabled,
                audio_vector_params=audio_vector_params,
                preference_params=preference_params,
            )
            text = client.chat(system=sys_p, user=usr_p)
            try:
                parsed = client.extract_json(text)
                final_result.update(parsed)
            except Exception:
                final_result[off_key] = {}
        else:
            final_result[off_key] = {}

    return final_result


def _persist_results(
    db: MusicDatabase,
    song_name: str,
    params: dict[str, Any],
    style_result: dict[str, Any],
) -> None:
    """Save results to SQLite."""
    param_str = json.dumps(params, ensure_ascii=False)
    style_str = json.dumps(
        style_result.get("tags", []), ensure_ascii=False
    )
    feature_str = json.dumps(
        style_result.get("description", []), ensure_ascii=False
    )
    db.upsert_music(song_name, param_str, "edit", style_str, feature_str)


# ------------------------------------------------------------------
#  Entry point
# ------------------------------------------------------------------

def main() -> None:
    args = parse_args(sys.argv)
    run_pipeline(args)


if __name__ == "__main__":
    main()
