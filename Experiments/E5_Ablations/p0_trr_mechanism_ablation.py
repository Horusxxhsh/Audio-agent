"""
P0 TRR mechanism ablation.

This script is intentionally separate from the older E5 ablation prototypes.
It recomputes Wav2Vec2 hidden states once per audio item, then evaluates
controlled aggregation variants on the same deterministic P0 split used by E2.

The ablation is designed to answer the reviewer-facing mechanism question:
whether the gain comes from the Wav2Vec2 backbone alone or from the TRR
second-order aggregation design.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import torch
import torchaudio
from transformers import Wav2Vec2Model

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.dataset_loader import _resolve_local_audio_paths  # noqa: E402
from Experiments.common.evaluate import Evaluator  # noqa: E402


@dataclass(frozen=True)
class Variant:
    name: str
    family: str
    layers: Tuple[int, ...]
    project_dim: int
    l2_normalize: bool = True
    similarity: str = "cosine"


VARIANTS: Tuple[Variant, ...] = (
    Variant("mean_pool_l5", "mean_pool", (5,), 0, True, "cosine"),
    Variant("gram_no_projection_l5", "gram_full", (5,), 768, True, "cosine"),
    Variant("gram_l4_d64", "gram_projected", (4,), 64, True, "cosine"),
    Variant("gram_l5_d64", "gram_projected", (5,), 64, True, "cosine"),
    Variant("gram_l6_d64", "gram_projected", (6,), 64, True, "cosine"),
    Variant("gram_l456_d16", "gram_projected", (4, 5, 6), 16, True, "cosine"),
    Variant("gram_l456_d32", "gram_projected", (4, 5, 6), 32, True, "cosine"),
    Variant("gram_l456_d64", "gram_projected", (4, 5, 6), 64, True, "cosine"),
    Variant("gram_l456_d128", "gram_projected", (4, 5, 6), 128, True, "cosine"),
    Variant("gram_l456_d64_no_l2", "gram_projected", (4, 5, 6), 64, False, "dot"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P0 TRR mechanism ablation")
    parser.add_argument("--dataset", default=str(REPO_ROOT / "Experiments" / "dataset_full_vectors.json"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "Experiments" / "E5_Ablations" / "outputs" / "p0_trr_mechanism"))
    parser.add_argument("--test-size", type=int, default=204)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--skip-full-gram", action="store_true", help="Skip the expensive 768x768 unprojected Gram variant.")
    return parser.parse_args()


def deterministic_split_indices(data: Sequence[Dict[str, Any]], test_size: int, seed: int) -> Tuple[List[int], List[int]]:
    indexed: List[Tuple[str, int]] = []
    for idx, item in enumerate(data):
        name = str(item.get("SongName", ""))
        h = hashlib.sha1(f"{seed}:{name}".encode("utf-8")).hexdigest()
        indexed.append((h, idx))
    indexed.sort(key=lambda x: x[0])
    n = len(indexed)
    ts = min(max(1, test_size), max(1, n // 3), n - 1) if n > 1 else 1
    test = [x[1] for x in indexed[:ts]]
    kb = [x[1] for x in indexed[ts:]]
    return test, kb


def flatten_numeric(params: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten_numeric(v, key))
        elif isinstance(v, (int, float)):
            out[key] = float(v)
        elif isinstance(v, str):
            try:
                out[key] = float(v)
            except ValueError:
                pass
    return out


def build_param_ranges(items: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}
    for item in items:
        for key, val in flatten_numeric(item.get("Parameters", {})).items():
            mins[key] = min(mins.get(key, val), val)
            maxs[key] = max(maxs.get(key, val), val)
    return {k: (mins[k], maxs[k]) for k in mins}


def normalized_l2(pred: Dict[str, Any], gt: Dict[str, Any], ranges: Dict[str, Tuple[float, float]]) -> float:
    fp = flatten_numeric(pred)
    fg = flatten_numeric(gt)
    keys = set(fp) | set(fg)
    if not keys:
        return 0.0
    total = 0.0
    for k in keys:
        lo, hi = ranges.get(k, (0.0, 1.0))
        span = hi - lo if abs(hi - lo) > 1e-12 else 1.0
        diff = (fp.get(k, 0.0) - fg.get(k, 0.0)) / span
        total += diff * diff
    return math.sqrt(total / len(keys))


def make_projection_matrices(device: torch.device, seed: int) -> Dict[int, torch.Tensor]:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    mats: Dict[int, torch.Tensor] = {}
    for dim in (16, 32, 64, 128):
        mat = torch.randn(768, dim, generator=generator, dtype=torch.float32) / math.sqrt(float(dim))
        mats[dim] = mat.to(device)
    return mats


def load_waveform(audio_path: str, device: torch.device) -> torch.Tensor | None:
    try:
        import soundfile as sf

        data, sr = sf.read(audio_path)
        waveform = torch.from_numpy(np.asarray(data)).float()
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        else:
            waveform = waveform.t()
    except Exception:
        try:
            waveform, sr = torchaudio.load(audio_path)
        except Exception:
            return None

    if int(sr) != 16000:
        resampler = torchaudio.transforms.Resample(int(sr), 16000).to(waveform.device)
        waveform = resampler(waveform)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    waveform = (waveform - waveform.mean()) / torch.sqrt(waveform.var() + 1e-7)
    return waveform.to(device)


def l2_norm(x: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.normalize(x, p=2, dim=0)


def variant_embedding(
    variant: Variant,
    hidden: Dict[int, torch.Tensor],
    projections: Dict[int, torch.Tensor],
) -> torch.Tensor:
    if variant.family == "mean_pool":
        emb = hidden[variant.layers[0]].mean(dim=0)
        return l2_norm(emb) if variant.l2_normalize else emb

    grams: List[torch.Tensor] = []
    for layer in variant.layers:
        feat = hidden[layer]
        if variant.family == "gram_full":
            projected = feat
        else:
            projected = feat @ projections[variant.project_dim]
        gram = projected.T @ projected / float(projected.shape[0])
        grams.append(gram)
    emb = torch.stack(grams).mean(dim=0).flatten()
    return l2_norm(emb) if variant.l2_normalize else emb


def compute_embeddings(
    data: Sequence[Dict[str, Any]],
    variants: Sequence[Variant],
    device: torch.device,
    seed: int,
) -> Dict[str, List[np.ndarray | None]]:
    model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base").to(device)
    model.eval()
    projections = make_projection_matrices(device, seed)
    outputs: Dict[str, List[np.ndarray | None]] = {v.name: [] for v in variants}

    t0 = time.time()
    for idx, item in enumerate(data):
        audio_path = item.get("AudioPath")
        if not audio_path or not os.path.exists(str(audio_path)):
            for v in variants:
                outputs[v.name].append(None)
            continue

        waveform = load_waveform(str(audio_path), device)
        if waveform is None:
            for v in variants:
                outputs[v.name].append(None)
            continue

        with torch.no_grad():
            model_out = model(waveform, output_hidden_states=True)
            hidden = {
                layer: model_out.hidden_states[layer].squeeze(0).float()
                for layer in (4, 5, 6)
            }
            for variant in variants:
                emb = variant_embedding(variant, hidden, projections)
                if variant.family == "gram_full":
                    arr = emb.detach().cpu().numpy().astype(np.float16)
                else:
                    arr = emb.detach().cpu().numpy().astype(np.float32)
                outputs[variant.name].append(arr)

        if (idx + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"encoded {idx + 1}/{len(data)} items in {elapsed:.1f}s", flush=True)

    return outputs


def similarity_matrix(q: np.ndarray, kb: np.ndarray, mode: str, device: torch.device) -> np.ndarray:
    q_t = torch.from_numpy(q).to(device)
    kb_t = torch.from_numpy(kb).to(device)
    if mode == "cosine":
        q_t = torch.nn.functional.normalize(q_t.float(), p=2, dim=1)
        kb_t = torch.nn.functional.normalize(kb_t.float(), p=2, dim=1)
    else:
        q_t = q_t.float()
        kb_t = kb_t.float()
    sims = q_t @ kb_t.T
    return sims.detach().cpu().numpy()


def evaluate_variant(
    variant: Variant,
    embeddings: List[np.ndarray | None],
    data: Sequence[Dict[str, Any]],
    test_indices: Sequence[int],
    kb_indices: Sequence[int],
    ranges: Dict[str, Tuple[float, float]],
    device: torch.device,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    evaluator = Evaluator()
    valid_test = [idx for idx in test_indices if embeddings[idx] is not None]
    valid_kb = [idx for idx in kb_indices if embeddings[idx] is not None]
    if not valid_test or not valid_kb:
        return {"variant": variant.name, "error": "no valid embeddings"}, []

    q_mat = np.stack([np.asarray(embeddings[i]) for i in valid_test])
    kb_mat = np.stack([np.asarray(embeddings[i]) for i in valid_kb])
    sims = similarity_matrix(q_mat, kb_mat, variant.similarity, device)

    per_query: List[Dict[str, Any]] = []
    metrics: Dict[str, List[float]] = {
        "l2": [],
        "norm_l2": [],
        "acc": [],
        "recall": [],
        "cosine": [],
        "module": [],
        "top3_oracle_norm_l2": [],
        "top5_oracle_norm_l2": [],
    }
    for row_pos, q_idx in enumerate(valid_test):
        order = np.argsort(sims[row_pos])[::-1]
        top1_idx = valid_kb[int(order[0])]
        gt = data[q_idx].get("Parameters", {})
        pred = data[top1_idx].get("Parameters", {})

        top3 = [valid_kb[int(i)] for i in order[:3]]
        top5 = [valid_kb[int(i)] for i in order[:5]]
        top3_best = min(normalized_l2(data[i].get("Parameters", {}), gt, ranges) for i in top3)
        top5_best = min(normalized_l2(data[i].get("Parameters", {}), gt, ranges) for i in top5)

        row = {
            "variant": variant.name,
            "query_song": data[q_idx].get("SongName", ""),
            "retrieved_song": data[top1_idx].get("SongName", ""),
            "l2": evaluator.compute_parameter_distance(pred, gt),
            "norm_l2": normalized_l2(pred, gt, ranges),
            "acc@0.1": evaluator.compute_accuracy_tolerance(pred, gt, tolerance=0.1),
            "recall": evaluator.compute_parameter_recall(pred, gt, threshold=0.1),
            "cosine": evaluator.compute_cosine_similarity(pred, gt),
            "module": evaluator.compute_module_consistency(pred, gt, active_threshold=0.1),
            "top3_oracle_norm_l2": top3_best,
            "top5_oracle_norm_l2": top5_best,
        }
        per_query.append(row)
        metrics["l2"].append(float(row["l2"]))
        metrics["norm_l2"].append(float(row["norm_l2"]))
        metrics["acc"].append(float(row["acc@0.1"]))
        metrics["recall"].append(float(row["recall"]))
        metrics["cosine"].append(float(row["cosine"]))
        metrics["module"].append(float(row["module"]))
        metrics["top3_oracle_norm_l2"].append(float(top3_best))
        metrics["top5_oracle_norm_l2"].append(float(top5_best))

    summary = {
        "variant": variant.name,
        "family": variant.family,
        "layers": "+".join(str(x) for x in variant.layers),
        "project_dim": variant.project_dim,
        "embedding_dim": int(np.asarray(embeddings[valid_test[0]]).shape[0]),
        "l2_normalize": bool(variant.l2_normalize),
        "similarity": variant.similarity,
        "n": len(per_query),
        "l2_mean": float(np.mean(metrics["l2"])),
        "norm_l2_mean": float(np.mean(metrics["norm_l2"])),
        "acc_mean": float(np.mean(metrics["acc"])),
        "recall_mean": float(np.mean(metrics["recall"])),
        "cosine_mean": float(np.mean(metrics["cosine"])),
        "module_mean": float(np.mean(metrics["module"])),
        "top3_oracle_norm_l2_mean": float(np.mean(metrics["top3_oracle_norm_l2"])),
        "top5_oracle_norm_l2_mean": float(np.mean(metrics["top5_oracle_norm_l2"])),
    }
    return summary, per_query


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.dataset, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = _resolve_local_audio_paths(data)

    variants = [v for v in VARIANTS if not (args.skip_full_gram and v.family == "gram_full")]
    test_indices, kb_indices = deterministic_split_indices(data, args.test_size, args.seed)
    valid_test = [i for i in test_indices if data[i].get("AudioPath") and os.path.exists(str(data[i].get("AudioPath")))]
    ranges = build_param_ranges([data[i] for i in list(test_indices) + list(kb_indices)])
    device = torch.device(args.device)

    print(
        f"P0 TRR mechanism ablation: items={len(data)} test={len(test_indices)} "
        f"valid_test_audio={len(valid_test)} kb={len(kb_indices)} device={device}"
    )
    embeddings = compute_embeddings(data, variants, device=device, seed=args.seed)

    summary_rows: List[Dict[str, Any]] = []
    per_query_rows: List[Dict[str, Any]] = []
    for variant in variants:
        print(f"evaluating {variant.name}", flush=True)
        summary, per_query = evaluate_variant(
            variant=variant,
            embeddings=embeddings[variant.name],
            data=data,
            test_indices=test_indices,
            kb_indices=kb_indices,
            ranges=ranges,
            device=device,
        )
        summary_rows.append(summary)
        per_query_rows.extend(per_query)

    write_csv(out_dir / "p0_trr_mechanism_summary.csv", summary_rows)
    write_csv(out_dir / "p0_trr_mechanism_per_query.csv", per_query_rows)
    with (out_dir / "p0_trr_mechanism_meta.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "dataset": args.dataset,
                "seed": args.seed,
                "test_size_requested": args.test_size,
                "test_size_actual": len(test_indices),
                "valid_test_audio": len(valid_test),
                "kb_size_actual": len(kb_indices),
                "variants": [v.__dict__ for v in variants],
            },
            f,
            indent=2,
        )

    print("\nSummary:")
    print("variant,n,norm_l2,acc,recall,cosine,module,top5_oracle_norm_l2")
    for row in summary_rows:
        print(
            f"{row['variant']},{row.get('n', 0)},"
            f"{row.get('norm_l2_mean', 0):.4f},{row.get('acc_mean', 0):.4f},"
            f"{row.get('recall_mean', 0):.4f},{row.get('cosine_mean', 0):.4f},"
            f"{row.get('module_mean', 0):.4f},{row.get('top5_oracle_norm_l2_mean', 0):.4f}"
        )


if __name__ == "__main__":
    main()
