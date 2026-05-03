"""
P0 near-duplicate sensitivity analysis.

This script reuses the P0 deterministic split (test_size=204, seed=42),
removes near-duplicate items from the knowledge base in parameter space, and
re-evaluates top-1 vector retrieval for all locally available embedding keys.

The analysis is intentionally limited to stored vectors. It does not recompute
PaSST/PANNs/CLAP embeddings when those vectors are absent from the local JSON.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

import numpy as np

COMMON_DIR = Path(__file__).resolve().parents[1] / "common"
sys.path.insert(0, str(COMMON_DIR))

from evaluate import Evaluator  # noqa: E402


VECTOR_METHODS: Dict[str, str] = {
    "TRR": "TRR",
    "Wav2Vec": "Wav2Vec",
    "FeatureNN": "FeatureNN",
    "CLAP": "CLAP",
    "PaSST": "PaSST",
    "PANNs": "PANNs",
}


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected dataset JSON to contain a list of records.")
    return data


def deterministic_split(
    data: Sequence[Dict[str, Any]], *, test_size: int, seed: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    indexed: List[Tuple[str, Dict[str, Any]]] = []
    for item in data:
        name = str(item.get("SongName", ""))
        h = hashlib.sha1(f"{seed}:{name}".encode("utf-8")).hexdigest()
        indexed.append((h, item))
    indexed.sort(key=lambda x: x[0])
    n = len(indexed)
    ts = min(max(1, int(test_size)), max(1, n // 3), n - 1) if n > 1 else 1
    return [x[1] for x in indexed[:ts]], [x[1] for x in indexed[ts:]]


def flatten_numeric(params: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key, value in (params or {}).items():
        flat_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten_numeric(value, flat_key))
        elif isinstance(value, (int, float)):
            out[flat_key] = float(value)
        elif isinstance(value, str):
            try:
                out[flat_key] = float(value)
            except ValueError:
                pass
    return out


def build_param_ranges(items: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}
    for item in items:
        for key, value in flatten_numeric(item.get("Parameters", {})).items():
            mins[key] = value if key not in mins else min(mins[key], value)
            maxs[key] = value if key not in maxs else max(maxs[key], value)
    return {key: (mins[key], maxs[key]) for key in mins}


def normalized_param_rmse(
    a: Dict[str, Any], b: Dict[str, Any], ranges: Dict[str, Tuple[float, float]]
) -> float:
    va = flatten_numeric(a)
    vb = flatten_numeric(b)
    keys = set(va) | set(vb)
    if not keys:
        return 0.0
    total = 0.0
    for key in keys:
        lo, hi = ranges.get(key, (0.0, 1.0))
        span = hi - lo
        if abs(span) < 1e-12:
            span = 1.0
        diff = (va.get(key, 0.0) - vb.get(key, 0.0)) / span
        total += diff * diff
    return math.sqrt(total / float(len(keys)))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    av = np.asarray(a, dtype=np.float64)
    bv = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom <= 0:
        return -1.0
    return float(np.dot(av, bv) / denom)


def has_vector(item: Dict[str, Any], key: str) -> bool:
    vec = item.get("Vectors", {}).get(key)
    return isinstance(vec, list) and len(vec) > 0


def available_methods(test_items: Sequence[Dict[str, Any]], kb_items: Sequence[Dict[str, Any]]) -> List[str]:
    methods: List[str] = []
    for method, key in VECTOR_METHODS.items():
        if any(has_vector(x, key) for x in test_items) and any(has_vector(x, key) for x in kb_items):
            methods.append(method)
    return methods


def retrieve_top1(query: Dict[str, Any], kb: Sequence[Dict[str, Any]], vector_key: str) -> Dict[str, Any]:
    qv = query.get("Vectors", {}).get(vector_key, [])
    if not isinstance(qv, list) or not qv:
        return {}
    best_score = -2.0
    best_item: Dict[str, Any] = {}
    for item in kb:
        iv = item.get("Vectors", {}).get(vector_key, [])
        if not isinstance(iv, list) or not iv or len(iv) != len(qv):
            continue
        score = cosine(qv, iv)
        if score > best_score:
            best_score = score
            best_item = item
    return best_item


def near_duplicate_remove_indices(
    kb_items: Sequence[Dict[str, Any]], threshold: float, ranges: Dict[str, Tuple[float, float]]
) -> Tuple[Set[int], int]:
    flats = [item.get("Parameters", {}) for item in kb_items]
    remove: Set[int] = set()
    pairs = 0
    for i in range(len(flats)):
        if i in remove:
            continue
        for j in range(i + 1, len(flats)):
            if j in remove:
                continue
            dist = normalized_param_rmse(flats[i], flats[j], ranges)
            if dist <= threshold:
                pairs += 1
                remove.add(j)
    return remove, pairs


def filter_by_indices(items: Sequence[Dict[str, Any]], remove: Iterable[int]) -> List[Dict[str, Any]]:
    remove_set = set(remove)
    return [item for idx, item in enumerate(items) if idx not in remove_set]


def evaluate(
    test_items: Sequence[Dict[str, Any]],
    kb_items: Sequence[Dict[str, Any]],
    methods: Sequence[str],
    ranges: Dict[str, Tuple[float, float]],
) -> List[Dict[str, Any]]:
    evaluator = Evaluator()
    rows: List[Dict[str, Any]] = []
    for method in methods:
        key = VECTOR_METHODS[method]
        values: Dict[str, List[float]] = {
            "l2": [],
            "norm_l2": [],
            "acc": [],
            "recall": [],
            "cosine": [],
            "module": [],
        }
        for query in test_items:
            top1 = retrieve_top1(query, kb_items, key)
            if not top1:
                continue
            pred = top1.get("Parameters", {})
            gt = query.get("Parameters", {})
            values["l2"].append(evaluator.compute_parameter_distance(pred, gt))
            values["norm_l2"].append(normalized_param_rmse(pred, gt, ranges))
            values["acc"].append(evaluator.compute_accuracy_tolerance(pred, gt, tolerance=0.1))
            values["recall"].append(evaluator.compute_parameter_recall(pred, gt, threshold=0.1))
            values["cosine"].append(evaluator.compute_cosine_similarity(pred, gt))
            values["module"].append(evaluator.compute_module_consistency(pred, gt, active_threshold=0.1))
        row: Dict[str, Any] = {"method": method, "n": len(values["l2"])}
        for metric, xs in values.items():
            row[f"{metric}_mean"] = float(np.mean(xs)) if xs else float("nan")
        rows.append(row)
    return rows


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        if not rows:
            return
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="P0 near-duplicate sensitivity analysis.")
    parser.add_argument("--dataset", default=str(Path("Experiments") / "dataset_full_vectors.json"))
    parser.add_argument("--out-dir", default=str(Path("Experiments") / "E5_Ablations" / "outputs" / "p0_near_dup"))
    parser.add_argument("--test-size", type=int, default=204)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.0, 0.005, 0.01, 0.02, 0.05])
    args = parser.parse_args()

    data = load_dataset(args.dataset)
    test_items, kb_items = deterministic_split(data, test_size=args.test_size, seed=args.seed)
    ranges = build_param_ranges(test_items + kb_items)
    methods = available_methods(test_items, kb_items)
    if not methods:
        raise SystemExit("No locally available vector methods found.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {
        "dataset": args.dataset,
        "test_size": len(test_items),
        "kb_size_original": len(kb_items),
        "seed": args.seed,
        "thresholds": {},
        "methods": methods,
        "distance": "normalized parameter RMSE over numeric leaves",
    }

    for threshold in args.thresholds:
        if abs(float(threshold)) < 1e-12:
            remove, pairs = set(), 0
        else:
            remove, pairs = near_duplicate_remove_indices(kb_items, float(threshold), ranges)
        kb_filtered = filter_by_indices(kb_items, remove)
        rows = evaluate(test_items, kb_filtered, methods, ranges)
        for row in rows:
            row = dict(row)
            row["threshold"] = float(threshold)
            row["pairs"] = int(pairs)
            row["removed"] = int(len(remove))
            row["kb_size"] = int(len(kb_filtered))
            all_rows.append(row)
        summary["thresholds"][str(threshold)] = {
            "pairs": int(pairs),
            "removed": int(len(remove)),
            "kb_size": int(len(kb_filtered)),
            "metrics": rows,
        }

    csv_path = out_dir / "p0_near_dup_sensitivity.csv"
    json_path = out_dir / "p0_near_dup_sensitivity.json"
    write_csv(csv_path, all_rows)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"P0 near-duplicate sensitivity complete.")
    print(f"- methods: {', '.join(methods)}")
    print(f"- csv: {csv_path}")
    print(f"- json: {json_path}")


if __name__ == "__main__":
    main()
