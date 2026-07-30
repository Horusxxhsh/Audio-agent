"""
Dimensionality-matched control baseline for Devil's Advocate challenge.

Generates a new retrieval baseline by projecting the existing 768-D Wav2Vec
mean-pooled vector to 4096-D via a fixed random Gaussian projection, then
L2-normalizing. This tests whether the TRR advantage is merely due to higher
dimensionality (4096-D vs 768-D) rather than second-order structure.

Usage:
    python dimensionality_control_baseline.py
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E7_HardSplit.run_hard_split_retrieval import load_dataset, load_requested_query_indices
from Experiments.E8_ExecutableNeighborhood.topk_retrieval_dump import cosine_topk
from Experiments.common.evaluate import Evaluator
from Experiments.E9_TMMMajorRevision.validity_audit import switch_metrics

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_SPLIT = "Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/dimensionality_control"
PROJECTION_SEED = 42
INPUT_DIM = 768
OUTPUT_DIM = 4096


def build_projection_matrix(in_dim: int = INPUT_DIM, out_dim: int = OUTPUT_DIM, seed: int = PROJECTION_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # Scaled random Gaussian so that output energy matches input energy in expectation
    R = rng.standard_normal((in_dim, out_dim), dtype=np.float64) / np.sqrt(float(in_dim))
    return R


def project_vector(vec: np.ndarray, R: np.ndarray) -> np.ndarray | None:
    if vec is None or vec.size == 0:
        return None
    projected = vec.astype(np.float64) @ R
    norm = float(np.linalg.norm(projected))
    if norm <= 0.0:
        return None
    return (projected / norm).astype(np.float32)


def dump_baseline_topk(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    R: np.ndarray,
    k: int = 10,
) -> list[dict[str, object]]:
    qset = {int(idx) for idx in query_indices}
    kb_source_indices = [idx for idx in range(len(dataset)) if int(idx) not in qset]
    kb_items = [dataset[int(idx)] for idx in kb_source_indices]

    # Build KB matrix for projected vectors
    kb_vectors = []
    kb_meta = []
    for item in kb_items:
        vec_raw = item.get("Vectors", {}).get("Wav2Vec")
        if vec_raw is None:
            continue
        vec = np.asarray(vec_raw, dtype=float).reshape(-1)
        if vec.shape[0] != INPUT_DIM:
            continue
        proj = project_vector(vec, R)
        if proj is None:
            continue
        kb_vectors.append(proj)
        kb_meta.append(item)
    kb_matrix = np.asarray(kb_vectors, dtype=float)

    norm_eval = Evaluator(normalize=True)
    rows: list[dict[str, object]] = []
    for query_idx in query_indices:
        query = dataset[int(query_idx)]
        qvec_raw = query.get("Vectors", {}).get("Wav2Vec")
        if qvec_raw is None:
            rows.append({
                "method": "Wav2Vec_RP4096",
                "query_idx": int(query_idx),
                "query_name": str(query.get("SongName", "")),
                "status": "skipped",
                "skip_reason": "missing_or_invalid_query_vector",
            })
            continue
        qvec = np.asarray(qvec_raw, dtype=float).reshape(-1)
        if qvec.shape[0] != INPUT_DIM:
            rows.append({
                "method": "Wav2Vec_RP4096",
                "query_idx": int(query_idx),
                "query_name": str(query.get("SongName", "")),
                "status": "skipped",
                "skip_reason": "dim_mismatch_query_vector",
            })
            continue
        qproj = project_vector(qvec, R)
        if qproj is None:
            rows.append({
                "method": "Wav2Vec_RP4096",
                "query_idx": int(query_idx),
                "query_name": str(query.get("SongName", "")),
                "status": "skipped",
                "skip_reason": "zero_norm_after_projection",
            })
            continue

        topk = cosine_topk(qproj, kb_matrix, k=k)
        candidates = [(kb_meta[idx], float(score)) for idx, score in topk]
        top1 = candidates[0][0] if candidates else {}
        top1_params = top1.get("Parameters", {}) if isinstance(top1, Mapping) else {}
        gt = query.get("Parameters", {})
        row: dict[str, object] = {
            "method": "Wav2Vec_RP4096",
            "query_idx": int(query_idx),
            "query_name": str(query.get("SongName", "")),
            "status": "ok",
            "top1_name": str(top1.get("SongName", "")) if isinstance(top1, Mapping) else "",
            "top1_norm_l2": norm_eval.compute_parameter_distance(top1_params, gt),
            "top1_acc_at_0_1": norm_eval.compute_accuracy_tolerance(top1_params, gt, tolerance=0.1),
            "top1_recall": norm_eval.compute_parameter_recall(top1_params, gt, threshold=0.1),
            "top1_cosine": norm_eval.compute_cosine_similarity(top1_params, gt),
            "top1_module": norm_eval.compute_module_consistency(top1_params, gt),
        }
        row.update({f"top1_{key}": value for key, value in switch_metrics(top1_params, gt).items()})
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    n = len(ok_rows)
    if n == 0:
        return {"n": 0}
    metrics = ["top1_norm_l2", "top1_acc_at_0_1", "top1_recall", "top1_cosine", "top1_switch_f1"]
    out: dict[str, object] = {"n": n, "coverage": n / len(rows)}
    for m in metrics:
        vals = [float(r[m]) for r in ok_rows if m in r]
        if vals:
            out[m] = float(np.mean(vals))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split-file", default=DEFAULT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    query_indices = load_requested_query_indices(dataset, Path(args.split_file))
    R = build_projection_matrix()

    rows = dump_baseline_topk(dataset, query_indices, R, k=args.k)
    summary = aggregate(rows)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rows.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    fields = sorted({key for row in rows for key in row.keys()})
    with (out_dir / "rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field) for field in fields})

    print(f"Wrote {out_dir / 'summary.json'}")
    print(f"Coverage: {summary['coverage']:.3f}, n={summary['n']}")
    for m in ["top1_norm_l2", "top1_acc_at_0_1", "top1_recall", "top1_cosine", "top1_switch_f1"]:
        if m in summary:
            print(f"  {m}: {summary[m]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
