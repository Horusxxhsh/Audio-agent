"""LLM client wrapper.

Provides a thin abstraction over OpenAI-compatible chat completions.
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Stateless wrapper around OpenAI-compatible chat API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(
        self,
        system: str,
        user: str,
        *,
        stream: bool = False,
    ) -> str:
        """Send a system + user message and return the assistant text."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=stream,
        )
        return response.choices[0].message.content

    def chat_with_history(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
    ) -> dict[str, str]:
        """Send arbitrary message list and return assistant response dict."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=stream,
        )
        return {"role": "assistant", "content": response.choices[0].message.content}

    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        """Best-effort JSON extraction from LLM response text.

        Strips markdown code fences and returns parsed dict.
        """
        import json  # noqa: PLC0415

        cleaned = text.replace("```json", "").replace("```", "").strip()

        # Try full parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try substring parse
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(cleaned[start:end])

        raise ValueError(f"Could not extract JSON from: {text}")
