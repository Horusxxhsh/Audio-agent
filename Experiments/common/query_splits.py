"""
Shared query split definitions for reproducible experiment scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_query_name_file(path: Path) -> List[str]:
    names: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        names.append(name)
    return names


def _resolve_existing_path(path_str: str) -> Optional[Path]:
    raw_path = Path(path_str).expanduser()
    candidates = [raw_path]
    if not raw_path.is_absolute():
        candidates.append(_repo_root() / raw_path)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def resolve_query_selector_file(split_selector: Optional[str]) -> Optional[Path]:
    """
    Resolve explicit file-based selectors.

    Supported forms:
    - ``file:/abs/or/relative/path.txt``
    - plain existing file path (best-effort convenience)
    """
    raw = (split_selector or "").strip()
    if not raw:
        return None

    if raw.lower().startswith("file:"):
        target = raw[5:].strip()
        if not target:
            raise ValueError("Empty file selector. Use file:/path/to/test.txt")
        resolved = _resolve_existing_path(target)
        if resolved is None:
            raise FileNotFoundError(f"Query split file not found: {target}")
        return resolved

    return _resolve_existing_path(raw)


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
    selector_file = resolve_query_selector_file(split_selector)
    if selector_file is not None:
        split = f"file:{selector_file}"
        requested_names = _read_query_name_file(selector_file)
        allow_random_fallback = False
    else:
        split = normalize_query_split(split_selector, default_split=default_split)
        requested_names = get_query_names(split)
        allow_random_fallback = True

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

    if not allow_random_fallback:
        return QuerySplitSelection(
            split=split,
            requested_names=requested_names,
            found_names=[],
            missing_names=missing_names,
            test_indices=[],
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
