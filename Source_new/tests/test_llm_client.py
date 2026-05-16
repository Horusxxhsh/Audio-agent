"""Tests for LLM client module."""

from __future__ import annotations

import pytest

from core.llm_client import LLMClient


class TestLLMClient:
    def test_extract_json_clean(self):
        text = '{"tags": ["ambient"], "description": ["test"]}'
        result = LLMClient.extract_json(text)
        assert result["tags"] == ["ambient"]

    def test_extract_json_with_fences(self):
        text = '```json\n{"tags": ["rock"]}\n```'
        result = LLMClient.extract_json(text)
        assert "tags" in result
        assert result["tags"] == ["rock"]

    def test_extract_json_with_surrounding_text(self):
        text = 'Here is the result: {"tags": ["ambient"]}'
        result = LLMClient.extract_json(text)
        assert "tags" in result
        assert result["tags"] == ["ambient"]

    def test_extract_json_invalid_raises(self):
        with pytest.raises(ValueError):
            LLMClient.extract_json("not json at all")

    def test_extract_json_malformed_partial(self):
        text = 'Some text before {"tags": ["metal"]} and after'
        result = LLMClient.extract_json(text)
        assert "tags" in result
        assert result["tags"] == ["metal"]
