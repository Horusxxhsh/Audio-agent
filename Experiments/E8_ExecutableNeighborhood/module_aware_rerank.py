from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.evaluate import Evaluator
from Experiments.common.parameter_space import active_modules


DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_TOPK_JSON = "Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json"
DEFAULT_OUT = "Experiments/E8_ExecutableNeighborhood/outputs/module_rerank"
METRIC_IMPL = "oracle_free_active_module_consensus"
OUTPUT_FIELDS = [
    "method",
    "query_idx",
    "query_name",
    "status",
    "skip_reason",
    "module_weight",
    "original_top1_name",
    "reranked_top1_name",
    "changed",
    "original_norm_l2",
    "reranked_norm_l2",
    "original_acc_at_0_1",
    "reranked_acc_at_0_1",
    "original_recall",
    "reranked_recall",
    "original_cosine",
    "reranked_cosine",
    "original_module",
    "reranked_module",
    "module_consensus_score",
    "rerank_score",
    "original_similarity",
    "reranked_similarity",
    "topk_names",
    "topk_scores",
    "metric_impl",
]
CSV_EXCLUDED_FIELDS = {
    "original_parameters",
    "reranked_parameters",
    "ranked_candidates",
    "module_consensus",
}


def _finite_float(value: object, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric


def _candidate_params(candidate: Mapping[str, object]) -> Mapping[str, object]:
    params = candidate.get("parameters", candidate.get("Parameters", {}))
    return params if isinstance(params, Mapping) else {}


def _candidate_name(candidate: Mapping[str, object]) -> str:
    return str(candidate.get("name", candidate.get("SongName", "")))


def _candidate_similarity(candidate: Mapping[str, object], context: Optional[str] = None) -> float:
    if "score" in candidate:
        raw = candidate["score"]
    elif "similarity" in candidate:
        raw = candidate["similarity"]
    else:
        label = context or _candidate_name(candidate) or "candidate"
        raise ValueError(f"missing candidate similarity for {label}")
    return _finite_float(raw, f"candidate score for {context or _candidate_name(candidate)}")


def _round(value: float) -> float:
    return round(float(value), 10)


def candidate_module_consensus(
    candidates: Sequence[Mapping[str, object]],
    weights: Sequence[float],
) -> Dict[str, float]:
    if len(candidates) != len(weights):
        raise ValueError("candidates and weights must have the same length")
    consensus: Dict[str, float] = {}
    for candidate, weight in zip(candidates, weights):
        numeric_weight = _finite_float(weight, "weight")
        if numeric_weight < 0:
            raise ValueError("weight must be non-negative")
        params = _candidate_params(candidate)
        for module in active_modules(params):
            consensus[module] = consensus.get(module, 0.0) + numeric_weight
    return {module: _round(consensus[module]) for module in sorted(consensus)}


def _consensus_weights_from_similarities(similarities: Sequence[float]) -> List[float]:
    non_negative = [max(0.0, _finite_float(score, "similarity")) for score in similarities]
    total = sum(non_negative)
    if total > 0:
        return [score / total for score in non_negative]
    if not non_negative:
        return []
    return [1.0 / len(non_negative)] * len(non_negative)


def _average_consensus_score(params: Mapping[str, object], consensus: Mapping[str, float]) -> float:
    modules = sorted(active_modules(params))
    if not modules:
        return 0.0
    return sum(float(consensus.get(module, 0.0)) for module in modules) / len(modules)


def rerank_by_module_consensus(
    candidates: Sequence[Mapping[str, object]],
    similarities: Sequence[float],
    module_weight: float,
) -> List[Dict[str, object]]:
    if len(candidates) != len(similarities):
        raise ValueError("candidates and similarities must have the same length")
    module_weight = _finite_float(module_weight, "module_weight")
    if module_weight < 0:
        raise ValueError("module_weight must be non-negative")

    similarities = [_finite_float(score, "similarity") for score in similarities]
    consensus_weights = _consensus_weights_from_similarities(similarities)
    consensus = candidate_module_consensus(candidates, consensus_weights)
    ranked: List[Dict[str, object]] = []
    for index, (candidate, similarity) in enumerate(zip(candidates, similarities)):
        params = _candidate_params(candidate)
        module_score = _average_consensus_score(params, consensus)
        rerank_score = similarity + module_weight * module_score
        enriched = dict(candidate)
        enriched.update(
            {
                "name": _candidate_name(candidate),
                "parameters": params,
                "similarity": similarity,
                "module_consensus_score": _round(module_score),
                "rerank_score": _round(rerank_score),
                "_rerank_score_raw": rerank_score,
                "active_modules": sorted(active_modules(params)),
                "_original_rank": index,
            }
        )
        ranked.append(enriched)
    ranked.sort(
        key=lambda item: (
            -float(item["_rerank_score_raw"]),
            -float(item["similarity"]),
            int(item["_original_rank"]),
        )
    )
    for rank, item in enumerate(ranked, start=1):
        item["reranked_rank"] = rank
        item.pop("_original_rank", None)
        item.pop("_rerank_score_raw", None)
    return ranked


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
    rows: List[Dict[str, object]] = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"top-k row {idx} is not an object")
        rows.append(row)
    return rows


def _evaluate_candidate(pred_params: Mapping[str, object], gt_params: Mapping[str, object]) -> Dict[str, float]:
    norm_eval = Evaluator(normalize=True)
    raw_eval = Evaluator(normalize=False)
    return {
        "norm_l2": norm_eval.compute_parameter_distance(pred_params, gt_params),
        "acc_at_0_1": norm_eval.compute_accuracy_tolerance(pred_params, gt_params, tolerance=0.1),
        "recall": norm_eval.compute_parameter_recall(pred_params, gt_params, threshold=0.1),
        "cosine": norm_eval.compute_cosine_similarity(pred_params, gt_params),
        "module": raw_eval.compute_module_consistency(pred_params, gt_params),
    }


def _topk_candidates(row: Mapping[str, object]) -> List[Mapping[str, object]]:
    candidates = row.get("topk_candidates", [])
    if not isinstance(candidates, list):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def rerank_record(
    row: Mapping[str, object],
    dataset: Sequence[Mapping[str, object]],
    module_weight: float,
) -> Dict[str, object]:
    query_idx = int(row["query_idx"])
    query_item = dataset[query_idx]
    gt_params = query_item.get("Parameters", {})
    gt_params = gt_params if isinstance(gt_params, Mapping) else {}
    candidates = _topk_candidates(row)
    if not candidates:
        return {
            "method": str(row.get("method", "")),
            "query_idx": query_idx,
            "query_name": str(row.get("query_name", query_item.get("SongName", ""))),
            "status": "skipped",
            "skip_reason": "no_topk_candidates",
            "module_weight": float(module_weight),
            "metric_impl": METRIC_IMPL,
        }

    similarities = [
        _candidate_similarity(candidate, context=f"query_idx={query_idx}, candidate={_candidate_name(candidate)}")
        for candidate in candidates
    ]
    ranked = rerank_by_module_consensus(candidates, similarities, module_weight=module_weight)
    original = candidates[0]
    reranked = ranked[0]
    original_params = _candidate_params(original)
    reranked_params = _candidate_params(reranked)
    original_metrics = _evaluate_candidate(original_params, gt_params)
    reranked_metrics = _evaluate_candidate(reranked_params, gt_params)
    original_name = _candidate_name(original)
    reranked_name = _candidate_name(reranked)
    consensus_weights = _consensus_weights_from_similarities(similarities)

    return {
        "method": str(row.get("method", "")),
        "query_idx": query_idx,
        "query_name": str(row.get("query_name", query_item.get("SongName", ""))),
        "status": "ok",
        "skip_reason": "",
        "module_weight": float(module_weight),
        "original_top1_name": original_name,
        "reranked_top1_name": reranked_name,
        "changed": original_name != reranked_name,
        "original_norm_l2": original_metrics["norm_l2"],
        "reranked_norm_l2": reranked_metrics["norm_l2"],
        "original_acc_at_0_1": original_metrics["acc_at_0_1"],
        "reranked_acc_at_0_1": reranked_metrics["acc_at_0_1"],
        "original_recall": original_metrics["recall"],
        "reranked_recall": reranked_metrics["recall"],
        "original_cosine": original_metrics["cosine"],
        "reranked_cosine": reranked_metrics["cosine"],
        "original_module": original_metrics["module"],
        "reranked_module": reranked_metrics["module"],
        "module_consensus_score": reranked["module_consensus_score"],
        "rerank_score": reranked["rerank_score"],
        "original_similarity": _candidate_similarity(
            original,
            context=f"query_idx={query_idx}, candidate={_candidate_name(original)}",
        ),
        "reranked_similarity": float(reranked["similarity"]),
        "topk_names": [_candidate_name(candidate) for candidate in candidates],
        "topk_scores": similarities,
        "module_consensus": candidate_module_consensus(candidates, consensus_weights),
        "ranked_candidates": [
            {
                "name": _candidate_name(candidate),
                "similarity": float(candidate["similarity"]),
                "module_consensus_score": float(candidate["module_consensus_score"]),
                "rerank_score": float(candidate["rerank_score"]),
                "active_modules": list(candidate["active_modules"]),
                "reranked_rank": int(candidate["reranked_rank"]),
            }
            for candidate in ranked
        ],
        "original_parameters": original_params,
        "reranked_parameters": reranked_params,
        "metric_impl": METRIC_IMPL,
    }


def rerank_topk_rows(
    dataset: Sequence[Mapping[str, object]],
    topk_rows: Sequence[Mapping[str, object]],
    method: str,
    module_weight: float,
) -> List[Dict[str, object]]:
    source_rows = [
        row
        for row in topk_rows
        if row.get("status") == "ok" and str(row.get("method", "")) == method
    ]
    return [rerank_record(row, dataset, module_weight=module_weight) for row in source_rows]


def run_module_aware_rerank(
    dataset_path: Path,
    topk_json_path: Path,
    method: str,
    module_weight: float,
    output_dir: Path,
) -> List[Dict[str, object]]:
    dataset = load_dataset(dataset_path)
    topk_rows = load_topk_rows(topk_json_path)
    rows = rerank_topk_rows(dataset, topk_rows, method=method, module_weight=module_weight)
    write_outputs(output_dir, rows)
    return rows


def _csv_value(value: object) -> object:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_outputs(output_dir: Path, rows: Sequence[Dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "module_aware_rerank_results.json"
    csv_path = output_dir / "module_aware_rerank_results.csv"

    json_path.write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = list(OUTPUT_FIELDS)
    extra = sorted({key for row in rows for key in row.keys()} - set(fields))
    extra = [key for key in extra if key not in CSV_EXCLUDED_FIELDS]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + extra)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields + extra})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run oracle-free active-module consensus reranking over Task 2 top-k rows.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset JSON array path.")
    parser.add_argument("--topk-json", default=DEFAULT_TOPK_JSON, help="Task 2 top-k retrieval JSON array.")
    parser.add_argument("--method", default="TRR", help="Source retrieval method to consume.")
    parser.add_argument("--module-weight", type=float, default=0.15, help="Weight for active-module consensus score.")
    parser.add_argument("--output-dir", default=DEFAULT_OUT, help="Output directory for CSV/JSON.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    run_module_aware_rerank(
        dataset_path=Path(args.dataset),
        topk_json_path=Path(args.topk_json),
        method=args.method,
        module_weight=args.module_weight,
        output_dir=output_dir,
    )
    print(f"wrote {output_dir / 'module_aware_rerank_results.csv'}")
    print(f"wrote {output_dir / 'module_aware_rerank_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
