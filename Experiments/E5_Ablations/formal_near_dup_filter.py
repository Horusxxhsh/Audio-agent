"""Formal near-duplicate filter (CR-5).

Parameter-space near-duplicate detection using normalized L2 distance,
KB filtering at three thresholds, and re-evaluation of all methods.

Outputs:
  - Filter stats JSON (NearDupFilterStats)
  - Filtered results CSV (FilteredResult)

Usage:
    python formal_near_dup_filter.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E7_HardSplit.run_hard_split_retrieval import (
    evaluate_method,
    load_dataset,
    load_requested_query_indices,
)
from Experiments.common.evaluate import Evaluator

# ---------------------------------------------------------------------------
# Data classes (interface contract)
# ---------------------------------------------------------------------------
@dataclass
class NearDupFilterStats:
    threshold: float
    original_queries: int   # 204
    retained_queries: int
    original_kb: int       # 1063
    retained_kb: int
    filtered_pairs: int
    filter_rate: float


@dataclass
class FilteredResult:
    method: str
    threshold: float
    norm_l2: float
    coverage: float
    n_queries: int


# ---------------------------------------------------------------------------
# Parameter-space distance
# ---------------------------------------------------------------------------
def flatten_numeric_params(params: Dict, prefix: str = "") -> Dict[str, float]:
    """Recursively flatten a nested parameter dict to {dotted_key: float}."""
    flat: Dict[str, float] = {}
    for key, value in (params or {}).items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_numeric_params(value, dotted))
        elif isinstance(value, (int, float)):
            flat[dotted] = float(value)
        elif isinstance(value, str):
            try:
                flat[dotted] = float(value)
            except ValueError:
                pass
    return flat


def load_param_ranges(path: Path | None = None) -> Dict:
    """Load DSP parameter physical ranges for min-max normalization."""
    if path is None:
        path = REPO_ROOT / "Experiments" / "common" / "param_ranges.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_doc", None)
    return data


def _normalize_value(key: str, value: float, ranges: Dict) -> float:
    parts = key.split(".", 1)
    if len(parts) != 2:
        return value
    module, param = parts
    module_ranges = ranges.get(module, {})
    if not isinstance(module_ranges, dict):
        return value
    param_info = module_ranges.get(param, {})
    if not isinstance(param_info, dict) or "min" not in param_info or "max" not in param_info:
        return value
    lo = float(param_info["min"])
    hi = float(param_info["max"])
    if abs(hi - lo) < 1e-12:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def normalized_param_l2(a: Dict, b: Dict, ranges: Dict) -> float:
    """Compute the normalized L2 distance between two parameter dicts."""
    fa = flatten_numeric_params(a)
    fb = flatten_numeric_params(b)
    keys = set(fa) | set(fb)
    if not keys:
        return 0.0
    sq_sum = 0.0
    for k in keys:
        va = _normalize_value(k, fa.get(k, 0.0), ranges)
        vb = _normalize_value(k, fb.get(k, 0.0), ranges)
        sq_sum += (va - vb) ** 2
    return math.sqrt(sq_sum / len(keys))


# ---------------------------------------------------------------------------
# Near-duplicate detection & filtering
# ---------------------------------------------------------------------------
def find_near_duplicate_indices(
    items: Sequence[Dict], threshold: float, ranges: Dict
) -> Tuple[Set[int], int]:
    """Find near-duplicate pairs within KB items using normalized parameter L2.

    Returns:
        (indices_to_remove, n_pairs) where indices_to_remove contains the
        second member of each near-duplicate pair.
    """
    flats = [flatten_numeric_params(item.get("Parameters", {})) for item in items]
    remove: Set[int] = set()
    n_pairs = 0
    n = len(flats)
    for i in range(n):
        if i in remove:
            continue
        for j in range(i + 1, n):
            if j in remove:
                continue
            dist = normalized_param_l2(
                {k: v for k, v in flats[i].items()},
                {k: v for k, v in flats[j].items()},
                ranges,
            )
            if dist <= threshold:
                n_pairs += 1
                remove.add(j)
    return remove, n_pairs


def filter_by_indices(items: Sequence[Dict], remove: Iterable[int]) -> List[Dict]:
    """Return items with indices in *remove* excluded."""
    remove_set = set(remove)
    return [item for idx, item in enumerate(items) if idx not in remove_set]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_formal_filter(
    dataset: Sequence[Dict],
    query_indices: Sequence[int],
    thresholds: Sequence[float],
    ranges: Dict | None = None,
) -> Tuple[List[NearDupFilterStats], List[FilteredResult]]:
    """Execute the full formal near-duplicate filter pipeline.

    Returns:
        (stats_list, results_list)
    """
    if ranges is None:
        ranges = load_param_ranges()

    qset = {int(idx) for idx in query_indices}
    test_items = [dataset[idx] for idx in query_indices]
    kb_items = [dataset[idx] for idx in range(len(dataset)) if idx not in qset]

    original_queries = len(test_items)
    original_kb = len(kb_items)

    stats_list: List[NearDupFilterStats] = []
    results_list: List[FilteredResult] = []

    for threshold in thresholds:
        remove_idx, n_pairs = find_near_duplicate_indices(kb_items, threshold, ranges)
        filtered_kb = filter_by_indices(kb_items, remove_idx)

        retained_kb = len(filtered_kb)
        filter_rate = 1.0 - (retained_kb / original_kb) if original_kb > 0 else 0.0

        stats_list.append(NearDupFilterStats(
            threshold=threshold,
            original_queries=original_queries,
            retained_queries=original_queries,
            original_kb=original_kb,
            retained_kb=retained_kb,
            filtered_pairs=n_pairs,
            filter_rate=filter_rate,
        ))

        # Re-evaluate all methods on filtered KB
        for method, vector_key in [
            ("TRR", "TRR"),
            ("Wav2Vec", "Wav2Vec"),
            ("FeatureNN", "FeatureNN"),
            ("CLAP", "CLAP"),
            ("PaSST", "PaSST"),
            ("PANNs", "PANNs"),
        ]:
            result = evaluate_method(method, vector_key, test_items, filtered_kb)
            results_list.append(FilteredResult(
                method=method,
                threshold=threshold,
                norm_l2=result.get("norm_l2") or float("nan"),
                coverage=result.get("coverage") or 0.0,
                n_queries=result.get("n") or 0,
            ))

    return stats_list, results_list


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_stats_json(path: Path, stats: List[NearDupFilterStats]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(s) for s in stats]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_results_csv(path: Path, results: List[FilteredResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["method", "threshold", "norm_l2", "coverage", "n_queries"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def write_full_outputs(
    output_dir: Path,
    stats: List[NearDupFilterStats],
    results: List[FilteredResult],
) -> None:
    write_stats_json(output_dir / "filter_stats.json", stats)
    write_results_csv(output_dir / "filtered_results.csv", results)

    # Also write a machine-readable combined JSON
    combined = {
        "stats": [asdict(s) for s in stats],
        "results": [asdict(r) for r in results],
    }
    (output_dir / "formal_near_dup_filter.json").write_text(
        json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
DEFAULT_DATASET = str(REPO_ROOT / "Data" / "External_1267_211" / "dataset" / "dataset_full_vectors_1267.json")
DEFAULT_SPLIT = str(REPO_ROOT / "Experiments" / "tmm" / "splits" / "tmm_external1267_audio_grouped" / "seed0" / "test.txt")
DEFAULT_OUT = str(REPO_ROOT / "Experiments" / "E5_Ablations" / "outputs" / "p0_formal_near_dup_filter")
DEFAULT_THRESHOLDS = [0.02, 0.05, 0.10]


def main() -> int:
    parser = argparse.ArgumentParser(description="Formal near-duplicate filter (CR-5)")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split-file", default=DEFAULT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--param-ranges", default=str(REPO_ROOT / "Experiments" / "common" / "param_ranges.json"))
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    query_indices = load_requested_query_indices(dataset, Path(args.split_file))
    ranges = load_param_ranges(Path(args.param_ranges) if args.param_ranges else None)

    stats, results = run_formal_filter(
        dataset, query_indices, args.thresholds, ranges,
    )

    output_dir = Path(args.output_dir)
    write_full_outputs(output_dir, stats, results)

    # Summary to stdout
    print(f"Formal near-duplicate filter completed:")
    print(f"  Dataset: {len(dataset)} items")
    print(f"  Queries: {query_indices[0] if query_indices else 'N/A'}")
    print(f"  Thresholds: {args.thresholds}")
    for s in stats:
        print(f"  t={s.threshold}: KB {s.original_kb} -> {s.retained_kb} "
              f"({s.filtered_pairs} pairs, rate={s.filter_rate:.3f})")
    print(f"  Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
