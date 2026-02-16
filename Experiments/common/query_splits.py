"""
Shared query split definitions for reproducible experiment scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np


CORE_5_QUERY_NAMES: List[str] = [
    "Dry Funk",
    "Tweed Breakup",
    "Reverse Psychedelic",
    "Math Rock Crystal",
    "Saturated Rhythm",
]


EXTENDED_30_QUERY_NAMES: List[str] = [
    # Original 5
    "Dry Funk",
    "Tweed Breakup",
    "Reverse Psychedelic",
    "Math Rock Crystal",
    "Saturated Rhythm",
    # +25
    "80s Hair Metal",
    "80s Pop Clean",
    "Acoustic Sim",
    "Ambient Swells",
    "Auto-Wah Funk",
    "Bitcrushed Synth",
    "Black Metal Lo-Fi",
    "Brian May Style",
    "British Invasion",
    "Brown Sound",
    "Classic Plexi",
    "Doom/Stoner Fuzz",
    "Dreamy Shoegaze",
    "Garage Rock Fuzz",
    "Grunge Dirt",
    "Hard Rock Crunch",
    "Indie Jangle",
    "Industrial Metal",
    "Infinite Sustain",
    "Jazz Box",
    "Liquid Lead",
    "Lo-Fi Hip Hop",
    "Midwest Emo",
    "Modern Djent",
    "Neo-Soul Clean",
]


FULL_31_QUERY_NAMES: List[str] = EXTENDED_30_QUERY_NAMES + ["Telephone EQ"]


_SPLIT_TO_NAMES: Dict[str, List[str]] = {
    "5": CORE_5_QUERY_NAMES,
    "30": EXTENDED_30_QUERY_NAMES,
    "31": FULL_31_QUERY_NAMES,
}


_SPLIT_ALIASES: Dict[str, str] = {
    "5": "5",
    "core": "5",
    "core5": "5",
    "30": "30",
    "default": "30",
    "extended": "30",
    "31": "31",
    "full": "31",
}


@dataclass(frozen=True)
class QuerySplitSelection:
    split: str
    requested_names: List[str]
    found_names: List[str]
    missing_names: List[str]
    test_indices: List[int]
    used_random_fallback: bool


def normalize_query_split(split_selector: Optional[str], default_split: str = "30") -> str:
    """
    Normalize user/environment split selectors to canonical split labels.
    """
    default_norm = _SPLIT_ALIASES.get((default_split or "30").strip().lower(), "30")
    raw = (split_selector or "").strip().lower()
    if not raw:
        return default_norm
    if raw not in _SPLIT_ALIASES:
        raise ValueError(
            f"Unknown query split '{split_selector}'. Supported values: "
            f"{sorted(_SPLIT_ALIASES.keys())}"
        )
    return _SPLIT_ALIASES[raw]


def get_query_names(split: str) -> List[str]:
    """
    Return canonical query-name list for a split ('5', '30', '31').
    """
    if split not in _SPLIT_TO_NAMES:
        raise ValueError(f"Unsupported split '{split}'. Must be one of {sorted(_SPLIT_TO_NAMES.keys())}.")
    return list(_SPLIT_TO_NAMES[split])


def select_query_indices(
    dataset: Sequence[Dict],
    split_selector: Optional[str],
    default_split: str = "30",
    random_seed: int = 42,
    random_fallback_size: int = 20,
) -> QuerySplitSelection:
    """
    Resolve query indices by SongName, with deterministic random fallback.
    """
    split = normalize_query_split(split_selector, default_split=default_split)
    requested_names = get_query_names(split)

    name_to_idx = {item.get("SongName"): i for i, item in enumerate(dataset)}
    found_names = [name for name in requested_names if name in name_to_idx]
    missing_names = [name for name in requested_names if name not in name_to_idx]

    if found_names:
        test_indices = [name_to_idx[name] for name in found_names]
        return QuerySplitSelection(
            split=split,
            requested_names=requested_names,
            found_names=found_names,
            missing_names=missing_names,
            test_indices=test_indices,
            used_random_fallback=False,
        )

    n = min(int(random_fallback_size), len(dataset))
    rng = np.random.default_rng(int(random_seed))
    random_indices = list(rng.choice(len(dataset), size=n, replace=False)) if n > 0 else []
    return QuerySplitSelection(
        split=split,
        requested_names=requested_names,
        found_names=[],
        missing_names=missing_names,
        test_indices=random_indices,
        used_random_fallback=True,
    )
