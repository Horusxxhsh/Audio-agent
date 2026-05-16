"""RAG bridge module.

Integrates the RAG system into the main processing pipeline.
Previously the integration point was disconnected (dead code).
This module provides the actual hook.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try importing the RAG system; fall back gracefully
try:
    from rag_system import AudioRAGSystem, initialize_knowledge_base  # noqa: PLC0415

    RAG_AVAILABLE = True
except ImportError:
    logger.warning("RAG system not available. Running in legacy mode.")
    RAG_AVAILABLE = False
    AudioRAGSystem = None  # type: ignore[assignment,misc]
    initialize_knowledge_base = None  # type: ignore[assignment,misc]


class RAGBridge:
    """Thin adapter that injects RAG results into the main pipeline."""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        if not RAG_AVAILABLE:
            self._rag: Any = None
            return

        self._rag = AudioRAGSystem(api_key=api_key, base_url=base_url)
        self._ensure_kb()

    def _ensure_kb(self) -> None:
        """Initialise knowledge base if empty."""
        if not RAG_AVAILABLE or self._rag is None:
            return
        stats = self._rag.get_collection_stats()
        if stats.get("music_knowledge_count", 0) == 0:
            logger.info("[RAG] Initialising knowledge base ...")
            initialize_knowledge_base(self._rag)

    # -------- public API -------------------------------------------------- #

    def retrieve_context(
        self,
        song_style: list[str],
        guitar_features: list[str],
    ) -> Optional[dict[str, Any]]:
        """Retrieve music knowledge + parameter recommendations.

        Returns ``None`` when RAG is unavailable.
        """
        if not RAG_AVAILABLE or self._rag is None:
            return None

        try:
            query = " ".join(song_style) + " " + " ".join(guitar_features)

            music_context = self._rag.retrieve_similar_knowledge(
                query=query,
                n_results=3,
                collection_type="music",
            )

            param_recs = self._rag.recommend_parameters(
                style_tags=song_style,
                user_description=" ".join(guitar_features),
                n_recommendations=5,
            )

            return {
                "music_context": music_context,
                "parameter_recommendations": param_recs,
            }
        except Exception as exc:
            logger.error("[RAG] Retrieval failed: %s", exc)
            return None

    def save_preset(
        self,
        preset_name: str,
        parameters: dict[str, Any],
        style_tags: list[str],
        features: list[str],
        user_rating: str = "accept",
    ) -> None:
        """Persist a generated preset into the RAG knowledge base."""
        if not RAG_AVAILABLE or self._rag is None:
            return

        try:
            self._rag.add_parameter_preset(
                preset_name=preset_name,
                parameters=parameters,
                style_tags=style_tags,
                description=" ".join(features),
                user_rating=user_rating,
            )
            logger.info("[RAG] Preset '%s' saved.", preset_name)
        except Exception as exc:
            logger.error("[RAG] Failed to save preset: %s", exc)
