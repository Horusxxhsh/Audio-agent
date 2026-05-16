"""Tests for prompt builder module."""

from __future__ import annotations

import pytest

from core.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_style_prompt(self):
        system, user = PromptBuilder.build_style_prompt("atmospheric guitar")
        assert "music style analysis" in system.lower()
        assert "atmospheric guitar" in user

    def test_module_toggle_prompt(self):
        system, user = PromptBuilder.build_module_toggle_prompt(
            chat_message="test song",
            song_style=["ambient"],
            guitar_features=["reverb"],
            memory_enabled=True,
            audio_vector_params=[],
            preference_params=[],
        )
        assert "overload" in system
        assert "distortion" in system
        assert user == "test song"

    def test_effector_param_prompt(self):
        system, user = PromptBuilder.build_effector_param_prompt(
            effector_name="compression",
            effector_example='{"CompressorOn": {...}}',
            effector_ranges="Threshold,Ratio,Attack",
            chat_message="test",
            song_style=["metal"],
            memory_enabled=False,
            audio_vector_params=[],
            preference_params=[],
        )
        assert "compression" in system

    def test_summary_prompt(self):
        system, user = PromptBuilder.build_summary_prompt(
            chat_message="song",
            result2_str='{"tags": []}',
            result1={"reverb": "yes"},
            result_str='{}',
            preference_params=[],
            audio_vector_params=[],
        )
        assert "effects assistant" in system.lower()

    def test_style_system_prompt_content(self):
        prompt = PromptBuilder._get_style_system_prompt()
        assert "Stage 1" in prompt
        assert "Stage 2" in prompt
        assert "Stage 3" in prompt
        assert "Stage 4" in prompt
        assert "Stage 5" in prompt
