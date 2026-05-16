"""Prompt builder for LLM interactions.

Extracts the large prompt templates that were previously
embedded in ``llm.py`` into structured, composable pieces.
"""

from __future__ import annotations

import json
from typing import Any


class PromptBuilder:
    """Composes system / user prompts for the three-stage LLM pipeline."""

    # -------------- stage 2: style inference ------------------------------- #

    STYLE_SYSTEM = (
        "You are a music style analysis engine. "
        "Given user input, extract style tags and guitar-feature descriptions."
        # (Full multi-stage prompt kept as class variable for clarity)
    )

    # We keep the actual long prompt as a static data file to avoid
    # bloating this module.  For now, return the original prompt.
    @staticmethod
    def build_style_prompt(chat_message: str) -> tuple[str, str]:
        """Return (system, user) for stage-2 style tag inference."""
        system = PromptBuilder._get_style_system_prompt()
        user = (
            f"Please based on: {chat_message},\n"
            "1. Analyze its specific music style (as detailed as possible).\n"
            "2. Generate tags (English, lowercase, specific).\n"
            "3. Describe possible guitar solo playing characteristics in "
            "English (array format, 2~6 sentences).\n\n"
            "Only output JSON (with keys: tags, description), no other text."
        )
        return system, user

    # -------------- stage 1: module on/off --------------------------------- #

    @staticmethod
    def build_module_toggle_prompt(
        chat_message: str,
        song_style: list[str],
        guitar_features: list[str],
        memory_enabled: bool,
        audio_vector_params: list[dict[str, Any]],
        preference_params: list[dict[str, Any]],
        text_weight: str = "0.5",
        preference_weight: str = "0.2",
        audio_weight: str = "0.3",
    ) -> tuple[str, str]:
        """Return (system, user) for stage-1 effector toggle inference."""
        audio_ref = json.dumps(audio_vector_params, ensure_ascii=False)
        pref_ref = json.dumps(preference_params, ensure_ascii=False)

        user_text_ref = (
            f"Style tags: {json.dumps(song_style, ensure_ascii=False)}\n"
            f"Description: {json.dumps(guitar_features, ensure_ascii=False)}\n"
            f"Text weight: {text_weight}"
        )

        system = f"""
You are an audio effects parameter expert.
Text: [{chat_message}]

Reference data:
1. Text analysis:
   {user_text_ref}
2. Audio vector ref: {audio_ref}
3. User preference ref: {pref_ref}

Weights: text={text_weight}, audio={audio_weight}, preference={preference_weight}

Task: Output JSON for 10 modules (yes/no):
{{
  "overload": "yes|no",
  "distortion": "yes|no",
  "delay": "yes|no",
  "reverb": "yes|no",
  "compression": "yes|no",
  "phase": "yes|no",
  "chorus": "yes|no",
  "flanger": "yes|no",
  "equalization": "yes|no",
  "noise_gate": "yes|no"
}}
Only output JSON.
"""
        return system, chat_message

    # -------------- stage 3: per-effector parameter generation ------------- #

    @staticmethod
    def build_effector_param_prompt(
        effector_name: str,
        effector_example: str,
        effector_ranges: str,
        chat_message: str,
        song_style: list[str],
        memory_enabled: bool,
        audio_vector_params: list[dict[str, Any]],
        preference_params: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """Return (system, user) for parameter generation of one effector."""
        audio_ref_info = (
            f"Audio vector reference: {json.dumps(audio_vector_params, ensure_ascii=False)}"
            if audio_vector_params
            else "No audio vector reference available."
        )

        if memory_enabled:
            pref_info = (
                f"User preference parameters: {json.dumps(preference_params, ensure_ascii=False)}"
                if preference_params
                else "No preference parameters available."
            )
            system = (
                f"You are a professional audio effects adjuster. "
                f"Goal: Generate {effector_name} parameters.\n"
                f"Example structure: {effector_example}\n"
                f"Parameter ranges: {effector_ranges}\n"
                f"{audio_ref_info}\n{pref_info}\n\n"
                "Output only a single JSON object."
            )
        else:
            system = (
                f"You are a professional audio effects adjuster. "
                f"Generate {effector_name} parameters based on "
                f"audio vector reference: {audio_ref_info}\n"
                f"Example structure: {effector_example}\n"
                f"Parameter ranges: {effector_ranges}\n\n"
                "Output only a single JSON object."
            )
        return system, f"Generate parameters for: {chat_message}"

    # -------------- stage 4: summary response -------------------------------- #

    @staticmethod
    def build_summary_prompt(
        chat_message: str,
        result2_str: str,
        result1: dict[str, str],
        result_str: str,
        preference_params: list[dict[str, Any]],
        audio_vector_params: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """Return (system, user) for the final summary response."""
        enabled = [k for k, v in result1.items() if v == "yes"]
        system = (
            "You are a professional intelligent music effects assistant. "
            "Provide a comprehensive, technical analysis of the generated "
            "effects parameters. Use only English."
        )
        user = (
            f"Original input: {chat_message}\n"
            f"Style analysis: {result2_str}\n"
            f"Module decisions: {result1}\n"
            f"Parameters: {result_str}\n"
            f"Enabled effects: {enabled}\n\n"
            "Provide analysis covering: musical style, effects breakdown, "
            "reference tracks, signal flow, fine-tuning recommendations."
        )
        return system, user

    # -------------- helpers ------------------------------------------------ #

    @staticmethod
    def _get_style_system_prompt() -> str:
        """Return the full multi-stage style inference system prompt."""
        # The prompt is long; keeping it here for single-file clarity.
        return """
You are a music style analysis engine that processes user input through stages:

=== Stage 1: Input Extraction ===
- Detect song title fragments (any language: Chinese, Japanese, Korean, Latin)
- Detect emotion/mood words (cross-language)
- Detect style keywords, production techniques, instrument mentions

=== Stage 2: Style Inference ===
- Give 1-3 specific subgenre directions
- Map emotions to genres:
  lonely/cosmic → cinematic_ambient / atmospheric_post_rock
  heavy/oppressive → doom / sludge / dark_post_metal
  rhythmic/dancing → funk_rock / disco_funk
  psychedelic/dreamy → psychedelic_rock / shoegaze
  gentle/healing → dreamy_ambient / clean_post_rock
  nostalgic/vintage → retro_synthwave / city_pop

=== Stage 3: Tag Construction ===
- Quantity ≤6, lowercase, underscores/dashes
- Order: main style → substyles → textures

=== Stage 4: Search Descriptions ===
- 2-6 sentences in English, 14-30 words each
- Cover: style, mood, tempo, texture, tone, dynamics
- No Chinese, no artist names

=== Stage 5: Compliance Check ===
- Remove duplicates, ensure valid JSON
- Cannot determine → output {"tags": [], "description": []}

Output Format: {"tags": ["tag1","tag2"], "description": ["sentence1","sentence2"]}
"""
