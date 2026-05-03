from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.evaluate import Evaluator
from Experiments.common.parameter_space import (
    blend_parameter_dicts,
    edit_cost,
    exemplar_provenance_score,
    flatten_numeric_params,
)


DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_TOPK_JSON = "Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json"
DEFAULT_OUT = "Experiments/E8_ExecutableNeighborhood/outputs/epr"
METRIC_IMPL = "epr_rcpp_softmax_topk_observed_kb_range"
OUTPUT_FIELDS = [
    "method",
    "source_method",
    "query_idx",
    "query_name",
    "k",
    "effective_k",
    "temperature",
    "status",
    "skip_reason",
    "norm_l2",
    "acc_at_0_1",
    "recall",
    "cosine",
    "module",
    "edit_cost",
    "provenance_max_weight",
    "provenance_entropy_norm",
    "provenance_effective_exemplars",
    "topk_names",
    "topk_scores",
    "weights",
    "metric_impl",
]


def softmax_weights(scores: Sequence[float], temperature: float) -> List[float]:
    if not math.isfinite(float(temperature)) or temperature <= 0:
        raise ValueError("temperature must be positive and finite")
    if not scores:
        return []
    arr = np.asarray(scores, dtype=np.float64) / float(temperature)
    if not np.all(np.isfinite(arr)):
        raise ValueError("scores must be finite")
    arr = arr - float(np.max(arr))
    exp = np.exp(arr)
    total = float(exp.sum())
    if total <= 0 or not math.isfinite(total):
        raise ValueError("softmax weights are undefined for these scores")
    return [float(x) for x in exp / total]


def observed_numeric_ranges(items: Sequence[Mapping[str, object]]) -> Dict[str, Tuple[float, float]]:
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}
    for item in items:
        params = item.get("Parameters", item)
        if not isinstance(params, Mapping):
            continue
        for key, value in flatten_numeric_params(params).items():
            mins[key] = value if key not in mins else min(mins[key], value)
            maxs[key] = value if key not in maxs else max(maxs[key], value)
    return {key: (mins[key], maxs[key]) for key in sorted(mins)}


def _assign_dotted(out: Dict[str, object], dotted: str, value: float) -> None:
    cur = out
    parts = dotted.split(".")
    for part in parts[:-1]:
        next_value = cur.setdefault(part, {})
        if not isinstance(next_value, dict):
            raise ValueError(f"cannot assign nested parameter under scalar key {part}")
        cur = next_value
    cur[parts[-1]] = round(float(value), 10)


def project_to_observed_ranges(
    params: Mapping[str, object],
    ranges: Mapping[str, Tuple[float, float]],
) -> Dict[str, object]:
    projected: Dict[str, object] = {}
    for key, value in flatten_numeric_params(params).items():
        clipped = value
        if key in ranges:
            lo, hi = ranges[key]
            lo_f = float(lo)
            hi_f = float(hi)
            if not math.isfinite(lo_f) or not math.isfinite(hi_f):
                raise ValueError(f"non-finite observed range for {key}")
            if lo_f > hi_f:
                raise ValueError(f"invalid observed range for {key}: {(lo_f, hi_f)}")
            clipped = min(max(value, lo_f), hi_f)
        _assign_dotted(projected, key, clipped)
    return projected


def weighted_projection(
    candidates: Sequence[Mapping[str, object]],
    weights: Sequence[float],
    ranges: Mapping[str, Tuple[float, float]],
) -> Tuple[Dict[str, object], Dict[str, float]]:
    blended = blend_parameter_dicts(candidates, weights)
    projected = project_to_observed_ranges(blended, ranges)
    projected = enforce_mutually_exclusive_module_states(projected, candidates, weights)
    return projected, exemplar_provenance_score(weights)


def _module_state(key: str) -> Optional[Tuple[str, str]]:
    if key.endswith("On"):
        return key[:-2], "On"
    if key.endswith("Off"):
        return key[:-3], "Off"
    return None


def _preferred_state(
    root: str,
    candidates: Sequence[Mapping[str, object]],
    weights: Sequence[float],
    votes: Mapping[str, Mapping[str, float]],
) -> str:
    root_votes = votes.get(root, {})
    on_vote = float(root_votes.get("On", 0.0))
    off_vote = float(root_votes.get("Off", 0.0))
    if on_vote > off_vote:
        return "On"
    if off_vote > on_vote:
        return "Off"
    best_weight = -1.0
    best_state = "On"
    for candidate, weight in zip(candidates, weights):
        params = candidate.get("Parameters", candidate) if isinstance(candidate, Mapping) else {}
        if not isinstance(params, Mapping):
            continue
        for state in ("On", "Off"):
            if f"{root}{state}" in params and float(weight) > best_weight:
                best_weight = float(weight)
                best_state = state
    return best_state


def enforce_mutually_exclusive_module_states(
    params: Mapping[str, object],
    candidates: Sequence[Mapping[str, object]],
    weights: Sequence[float],
) -> Dict[str, object]:
    votes: Dict[str, Dict[str, float]] = {}
    for candidate, weight in zip(candidates, weights):
        candidate_params = candidate.get("Parameters", candidate) if isinstance(candidate, Mapping) else {}
        if not isinstance(candidate_params, Mapping):
            continue
        for key in candidate_params.keys():
            state = _module_state(str(key))
            if state is None:
                continue
            root, on_off = state
            votes.setdefault(root, {"On": 0.0, "Off": 0.0})[on_off] += float(weight)

    resolved: Dict[str, object] = {}
    present_roots = {
        state[0]
        for key in params.keys()
        for state in [_module_state(str(key))]
        if state is not None
    }
    preferred = {root: _preferred_state(root, candidates, weights, votes) for root in present_roots}
    for key, value in params.items():
        state = _module_state(str(key))
        if state is None:
            resolved[key] = value
            continue
        root, on_off = state
        if preferred[root] == on_off:
            resolved[key] = value
    return resolved


def load_dataset(dataset_path: Path) -> List[Dict[str, object]]:
    with dataset_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"dataset must be a JSON array: {dataset_path}")
    return data


def load_topk_rows(topk_path: Path) -> List[Dict[str, object]]:
    with topk_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"top-k metrics must be a JSON array, not JSONL: {topk_path}")
    rows = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"top-k row {idx} is not an object")
        rows.append(row)
    return rows


def kb_items_from_topk_rows(
    dataset: Sequence[Dict[str, object]],
    topk_rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    query_indices = set()
    for row in topk_rows:
        if "query_idx" not in row:
            continue
        try:
            query_indices.add(int(row["query_idx"]))
        except (TypeError, ValueError):
            continue
    if not query_indices:
        return list(dataset)
    return [item for idx, item in enumerate(dataset) if idx not in query_indices]


def _candidate_params(candidate: Mapping[str, object]) -> Mapping[str, object]:
    params = candidate.get("parameters", candidate.get("Parameters", {}))
    return params if isinstance(params, Mapping) else {}


def _candidate_name(candidate: Mapping[str, object]) -> str:
    return str(candidate.get("name", candidate.get("SongName", "")))


def _candidate_score(candidate: Mapping[str, object]) -> float:
    score = candidate.get("score", 0.0)
    numeric = float(score)
    if not math.isfinite(numeric):
        raise ValueError(f"candidate score must be finite: {score}")
    return numeric


def _evaluate_projection(
    pred_params: Mapping[str, object],
    gt_params: Mapping[str, object],
) -> Dict[str, float]:
    norm_eval = Evaluator(normalize=True)
    raw_eval = Evaluator(normalize=False)
    return {
        "norm_l2": norm_eval.compute_parameter_distance(pred_params, gt_params),
        "acc_at_0_1": norm_eval.compute_accuracy_tolerance(pred_params, gt_params, tolerance=0.1),
        "recall": norm_eval.compute_parameter_recall(pred_params, gt_params, threshold=0.1),
        "cosine": norm_eval.compute_cosine_similarity(pred_params, gt_params),
        "module": raw_eval.compute_module_consistency(pred_params, gt_params),
        "edit_cost": edit_cost(pred_params, gt_params, normalize=True),
    }


def projection_record(
    row: Mapping[str, object],
    dataset: Sequence[Dict[str, object]],
    ranges: Mapping[str, Tuple[float, float]],
    k: int,
    temperature: float,
) -> Dict[str, object]:
    query_idx = int(row["query_idx"])
    query_item = dataset[query_idx]
    gt_params = query_item.get("Parameters", {})
    candidates = row.get("topk_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    selected = [candidate for candidate in candidates[:k] if isinstance(candidate, Mapping)]
    if not selected:
        return {
            "method": f"EPR-K{k}",
            "source_method": str(row.get("method", "")),
            "query_idx": query_idx,
            "query_name": str(row.get("query_name", query_item.get("SongName", ""))),
            "k": int(k),
            "effective_k": 0,
            "temperature": float(temperature),
            "status": "skipped",
            "skip_reason": "no_topk_candidates",
            "metric_impl": METRIC_IMPL,
        }

    scores = [_candidate_score(candidate) for candidate in selected]
    weights = softmax_weights(scores, temperature=temperature)
    candidate_params = [_candidate_params(candidate) for candidate in selected]
    pred_params, provenance = weighted_projection(candidate_params, weights, ranges)
    metrics = _evaluate_projection(pred_params, gt_params if isinstance(gt_params, Mapping) else {})

    return {
        "method": f"EPR-K{k}",
        "source_method": str(row.get("method", "")),
        "query_idx": query_idx,
        "query_name": str(row.get("query_name", query_item.get("SongName", ""))),
        "k": int(k),
        "effective_k": len(selected),
        "temperature": float(temperature),
        "status": "ok",
        "skip_reason": "",
        **metrics,
        "provenance_max_weight": provenance["max_weight"],
        "provenance_entropy_norm": provenance["entropy_norm"],
        "provenance_effective_exemplars": provenance["effective_exemplars"],
        "topk_names": [_candidate_name(candidate) for candidate in selected],
        "topk_scores": scores,
        "weights": weights,
        "prediction_parameters": pred_params,
        "metric_impl": METRIC_IMPL,
    }


def run_epr_projection(
    dataset_path: Path,
    topk_json_path: Path,
    method: str,
    ks: Sequence[int],
    temperature: float,
    output_dir: Path,
) -> List[Dict[str, object]]:
    if not ks:
        raise ValueError("at least one k must be provided")
    if any(k <= 0 for k in ks):
        raise ValueError("all k values must be positive")
    dataset = load_dataset(dataset_path)
    topk_rows = load_topk_rows(topk_json_path)
    kb_items = kb_items_from_topk_rows(dataset, topk_rows)
    ranges = observed_numeric_ranges(kb_items)
    source_rows = [
        row
        for row in topk_rows
        if row.get("status") == "ok" and str(row.get("method", "")) == method
    ]

    rows: List[Dict[str, object]] = []
    for source_row in source_rows:
        for k in ks:
            rows.append(projection_record(source_row, dataset, ranges, k=int(k), temperature=temperature))
    write_outputs(output_dir, rows)
    return rows


def _csv_value(value: object) -> object:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_outputs(output_dir: Path, rows: Sequence[Dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "epr_projection_results.json"
    csv_path = output_dir / "epr_projection_results.csv"

    json_path.write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = list(OUTPUT_FIELDS)
    extra = sorted({key for row in rows for key in row.keys()} - set(fields))
    extra = [key for key in extra if key != "prediction_parameters"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + extra)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields + extra})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exemplar-preserving parameter projection over top-k retrieval rows.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset JSON array path.")
    parser.add_argument("--topk-json", default=DEFAULT_TOPK_JSON, help="Task 2 top-k retrieval JSON array.")
    parser.add_argument("--method", default="TRR", help="Source retrieval method to consume.")
    parser.add_argument("--ks", type=int, nargs="+", default=[3, 5], help="Top-k values to blend.")
    parser.add_argument("--temperature", type=float, default=0.05, help="Softmax temperature over retrieval scores.")
    parser.add_argument("--output-dir", default=DEFAULT_OUT, help="Output directory for CSV/JSON.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    run_epr_projection(
        dataset_path=Path(args.dataset),
        topk_json_path=Path(args.topk_json),
        method=args.method,
        ks=args.ks,
        temperature=args.temperature,
        output_dir=output_dir,
    )
    print(f"wrote {output_dir / 'epr_projection_results.csv'}")
    print(f"wrote {output_dir / 'epr_projection_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
