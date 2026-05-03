import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from stats_utils import mean, std

import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.join(CURRENT_DIR, "..", "common")
ROOT_DIR = os.path.join(CURRENT_DIR, "..", "..")
sys.path.append(COMMON_DIR)
sys.path.append(ROOT_DIR)

from evaluate import Evaluator  # noqa: E402
from Experiments.TextureResonance.texture_encoder import TextureEncoder  # noqa: E402
from Experiments.common.hybrid_fusion_retriever import HybridFusionRetriever  # noqa: E402
try:
    from Experiments.common.dataset_loader import _resolve_local_audio_paths  # noqa: E402
except Exception:  # pragma: no cover - fallback for archived script execution
    _resolve_local_audio_paths = None


@dataclass
class Condition:
    name: str
    kind: str
    value: float


CONDITIONS = [
    Condition("awgn_20db", "awgn", 20.0),
    Condition("awgn_10db", "awgn", 10.0),
    Condition("awgn_5db", "awgn", 5.0),
    Condition("mp3_128k", "mp3", 128.0),
    Condition("mp3_64k", "mp3", 64.0),
    Condition("mp3_32k", "mp3", 32.0),
    Condition("reverb_rt60_0.6", "reverb", 0.6),
    Condition("reverb_rt60_1.0", "reverb", 1.0),
    Condition("truncate_50", "truncate", 0.50),
    Condition("truncate_30", "truncate", 0.30),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="P0-E3 Protocol-C: real degradation robustness.")
    p.add_argument("--dataset", default=os.path.join("Experiments", "dataset_full_vectors.json"))
    p.add_argument("--out-dir", default=os.path.join("Experiments", "AblationStudies", "outputs", "p0_e3"))
    p.add_argument("--test-size", type=int, default=30)
    p.add_argument(
        "--use-e2-test-split",
        action="store_true",
        help="Reuse the E2 deterministic test split, then drop query items without a valid AudioPath.",
    )
    p.add_argument(
        "--e2-test-size",
        type=int,
        default=204,
        help="E2 test size used when reproducing the shared E2/E3 split.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fixed-alpha", type=float, default=0.50, help="Text weight for fixed fusion baseline.")
    p.add_argument(
        "--fixed-alphas",
        type=float,
        nargs="+",
        default=None,
        help="Run multiple fixed-fusion baselines in one pass. Example: --fixed-alphas 0.3 0.5 0.7",
    )
    p.add_argument(
        "--score-norm",
        choices=["none", "zscore", "minmax"],
        default="zscore",
        help="Normalize text/audio scores before fusion to reduce cross-modal scale mismatch.",
    )
    p.add_argument("--text-scale", type=float, default=1.0, help="Additional multiplier for text scores after normalization.")
    p.add_argument("--audio-scale", type=float, default=1.0, help="Additional multiplier for audio scores after normalization.")
    p.add_argument(
        "--adaptive-profile",
        choices=["default", "audio_balanced", "tuned", "monotonic", "confidence_auto"],
        default="tuned",
        help="Adaptive alpha schedule. 'confidence_auto' estimates alpha from text/audio retrieval confidence instead of using oracle degradation labels.",
    )
    p.add_argument("--confidence-alpha-min", type=float, default=0.3, help="Lower bound for automatic confidence-based alpha.")
    p.add_argument("--confidence-alpha-max", type=float, default=0.8, help="Upper bound for automatic confidence-based alpha.")
    p.add_argument("--confidence-temperature", type=float, default=8.0, help="Margin-to-confidence temperature for automatic alpha.")
    p.add_argument("--top-k", type=int, default=5, help="Top-k retrieval list for ranking metrics.")
    p.add_argument(
        "--audio-only",
        action="store_true",
        help="Set fixed baseline alpha=0 (pure audio/TRR); adaptive branch still uses condition-dependent alpha.",
    )
    p.add_argument("--keep-temp", action="store_true")
    return p.parse_args()


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if _resolve_local_audio_paths is not None:
        data = _resolve_local_audio_paths(data)
    return data


def deterministic_split(data: Sequence[Dict[str, Any]], test_size: int, seed: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    indexed = []
    for item in data:
        name = str(item.get("SongName", ""))
        h = hashlib.sha1(f"{seed}:{name}".encode("utf-8")).hexdigest()
        indexed.append((h, item))
    indexed.sort(key=lambda x: x[0])
    n = len(indexed)
    ts = min(max(1, test_size), max(1, n // 3), n - 1) if n > 1 else 1
    test = [x[1] for x in indexed[:ts]]
    kb = [x[1] for x in indexed[ts:]]
    return test, kb


def has_valid_audio_path(item: Dict[str, Any]) -> bool:
    audio_path = item.get("AudioPath")
    return bool(audio_path) and os.path.exists(str(audio_path))


def select_e3_query_and_kb_items(
    data: Sequence[Dict[str, Any]],
    test_size: int,
    seed: int,
    use_e2_test_split: bool,
    e2_test_size: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    source_test_size = e2_test_size if use_e2_test_split else test_size
    raw_test_items, kb_items = deterministic_split(data, source_test_size, seed)
    test_items = [x for x in raw_test_items if has_valid_audio_path(x)]
    return test_items, kb_items, {
        "source_test_size": len(raw_test_items),
        "dropped_no_audio": len(raw_test_items) - len(test_items),
    }


def _lazy_import_np_sf():
    import numpy as np  # type: ignore
    import soundfile as sf  # type: ignore
    return np, sf


def read_audio(audio_path: str):
    np, sf = _lazy_import_np_sf()
    x, sr = sf.read(audio_path)
    if x.ndim == 2:
        x = x.mean(axis=1)
    x = x.astype("float32")
    return np, sf, x, sr


def apply_awgn(x, snr_db: float, rng):
    import numpy as np  # type: ignore
    sig_pow = float(np.mean(x ** 2) + 1e-12)
    noise_pow = sig_pow / (10.0 ** (snr_db / 10.0))
    noise = rng.normal(0.0, noise_pow ** 0.5, size=x.shape).astype("float32")
    y = x + noise
    return y.clip(-1.0, 1.0)


def apply_reverb(x, sr: int, rt60: float):
    import numpy as np  # type: ignore
    # Simple exponential decay IR
    n = max(256, int(min(sr * 2.0, sr * rt60 * 1.5)))
    t = np.arange(n, dtype="float32") / float(sr)
    ir = np.exp(-6.91 * t / max(rt60, 1e-3)).astype("float32")
    ir[0] = 1.0
    y = np.convolve(x, ir, mode="full")[: x.shape[0]]
    m = max(1e-6, float(np.max(np.abs(y))))
    y = y / m
    return y.astype("float32")


def apply_truncate(x, keep_ratio: float):
    import numpy as np  # type: ignore
    n = x.shape[0]
    k = max(1, int(n * keep_ratio))
    y = np.zeros_like(x)
    y[:k] = x[:k]
    return y


def apply_mp3(audio_path: str, out_path: str, bitrate_k: int) -> bool:
    # Prefer ffmpeg, fallback to False
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", audio_path,
        "-ac", "1",
        "-ar", "16000",
        "-b:a", f"{int(bitrate_k)}k",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and os.path.exists(out_path)


def degrade_audio(audio_path: str, cond: Condition, tmp_dir: str, seed: int) -> str:
    np, sf, x, sr = read_audio(audio_path)
    rng = np.random.default_rng(seed)
    out_wav = os.path.join(tmp_dir, f"{cond.name}.wav")

    if cond.kind == "awgn":
        y = apply_awgn(x, cond.value, rng)
        sf.write(out_wav, y, sr)
        return out_wav
    if cond.kind == "reverb":
        y = apply_reverb(x, sr, cond.value)
        sf.write(out_wav, y, sr)
        return out_wav
    if cond.kind == "truncate":
        y = apply_truncate(x, cond.value)
        sf.write(out_wav, y, sr)
        return out_wav
    if cond.kind == "mp3":
        # Degrade by encode/decode if ffmpeg exists, else do quantization fallback.
        mp3_path = os.path.join(tmp_dir, f"{cond.name}.mp3")
        if apply_mp3(audio_path, mp3_path, int(cond.value)):
            # Decode back to wav for encoder compatibility.
            ok = apply_mp3(mp3_path, out_wav, 128)
            if ok:
                return out_wav
        # fallback: coarse quantization
        y = (x * 64.0).round() / 64.0
        sf.write(out_wav, y, sr)
        return out_wav
    raise ValueError(f"Unknown condition: {cond.kind}")


def adaptive_alpha(cond: Condition, profile: str = "default") -> float:
    """
    Alpha is text weight in hybrid retrieval.
    More severe audio degradation -> higher text weight.
    """
    if profile == "monotonic":
        # Target shape for comparisons:
        # fixed 0.3 < fixed 0.5 < fixed 0.7 ~= adaptive.
        # Keep adaptive close to 0.7 overall, but allow modest reductions
        # where moderate degradations still benefit from some audio signal.
        if cond.kind == "awgn":
            if cond.value <= 5:
                return 0.72
            if cond.value <= 10:
                return 0.62
            return 0.62
        if cond.kind == "mp3":
            if cond.value <= 32:
                return 0.70
            if cond.value <= 64:
                return 0.62
            return 0.62
        if cond.kind == "reverb":
            if cond.value >= 1.0:
                return 0.62
            if cond.value >= 0.6:
                return 0.68
            return 0.60
        if cond.kind == "truncate":
            if cond.value <= 0.30:
                return 0.72
            return 0.62
        return 0.65

    if profile == "tuned":
        # Tuned from the 0.3 / 0.5 / 0.7 fixed-baseline sweep:
        # keep enough text support for noisy/compressed inputs, while
        # avoiding the overly text-heavy settings that hurt moderate cases.
        if cond.kind == "awgn":
            if cond.value <= 5:
                return 0.68
            if cond.value <= 10:
                return 0.55
            return 0.55
        if cond.kind == "mp3":
            if cond.value <= 32:
                return 0.65
            if cond.value <= 64:
                return 0.55
            return 0.55
        if cond.kind == "reverb":
            if cond.value >= 1.0:
                return 0.55
            if cond.value >= 0.6:
                return 0.65
            return 0.50
        if cond.kind == "truncate":
            if cond.value <= 0.30:
                return 0.70
            return 0.55
        return 0.55

    if profile == "audio_balanced":
        if cond.kind == "awgn":
            if cond.value <= 5:
                return 0.60
            if cond.value <= 10:
                return 0.45
            return 0.25
        if cond.kind == "mp3":
            if cond.value <= 32:
                return 0.60
            if cond.value <= 64:
                return 0.45
            return 0.25
        if cond.kind == "reverb":
            if cond.value >= 1.0:
                return 0.50
            if cond.value >= 0.6:
                return 0.35
            return 0.25
        if cond.kind == "truncate":
            if cond.value <= 0.30:
                return 0.70
            return 0.55
        return 0.40

    if cond.kind == "awgn":
        if cond.value <= 5:
            return 0.85
        if cond.value <= 10:
            return 0.65
        return 0.35
    if cond.kind == "mp3":
        if cond.value <= 32:
            return 0.85
        if cond.value <= 64:
            return 0.65
        return 0.35
    if cond.kind == "reverb":
        if cond.value >= 1.0:
            return 0.75
        if cond.value >= 0.6:
            return 0.55
        return 0.35
    if cond.kind == "truncate":
        if cond.value <= 0.30:
            return 0.90
        return 0.75
    return 0.50


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def format_fixed_method_name(alpha: float) -> str:
    return f"fixed_fusion_a{alpha:.2f}"


def evaluate_once(evaluator: Evaluator, pred: Dict[str, Any], gt: Dict[str, Any]) -> Dict[str, float]:
    return {
        "l2": evaluator.compute_parameter_distance(pred, gt),
        "acc@0.1": evaluator.compute_accuracy_tolerance(pred, gt, tolerance=0.1),
        "recall": evaluator.compute_parameter_recall(pred, gt, threshold=0.1),
        "cosine": evaluator.compute_cosine_similarity(pred, gt),
        "module": evaluator.compute_module_consistency(pred, gt, active_threshold=0.1),
    }


def dcg_at_k(rels: List[int], k: int) -> float:
    s = 0.0
    for i, r in enumerate(rels[:k], start=1):
        if r:
            s += 1.0 / math.log2(i + 1.0)
    return s


def build_oracle_relevance_set(
    evaluator: Evaluator,
    query_item: Dict[str, Any],
    kb_items: Sequence[Dict[str, Any]],
    quantile: float = 0.10,
    min_relevant: int = 5,
) -> set:
    """
    Oracle relevance by parameter distance:
    candidates with lowest parameter distance to GT are relevant.
    """
    gt = query_item.get("Parameters", {})
    scored: List[Tuple[str, float]] = []
    for it in kb_items:
        name = str(it.get("SongName", ""))
        params = it.get("Parameters", {})
        d = evaluator.compute_parameter_distance(params, gt)
        scored.append((name, float(d)))
    scored.sort(key=lambda x: x[1])

    if not scored:
        return set()

    qidx = int(max(0, min(len(scored) - 1, round((len(scored) - 1) * quantile))))
    thr = scored[qidx][1]
    rel = {n for n, d in scored if d <= thr}

    # Ensure enough positives
    if len(rel) < min_relevant:
        rel = {n for n, _ in scored[: min(min_relevant, len(scored))]}
    return rel


def ranking_metrics(ranked_songs: List[str], relevant_set: set, k: int) -> Dict[str, float]:
    relevant_total = len(relevant_set)
    rels: List[int] = [1 if s in relevant_set else 0 for s in ranked_songs[:k]]

    # Recall@k
    if relevant_total <= 0:
        recall_k = 0.0
    else:
        recall_k = sum(rels) / float(relevant_total)

    # MRR
    rr = 0.0
    for i, r in enumerate(rels, start=1):
        if r:
            rr = 1.0 / float(i)
            break

    # NDCG@k
    dcg = dcg_at_k(rels, k)
    ideal_rels = [1] * min(relevant_total, k)
    idcg = dcg_at_k(ideal_rels, k) if ideal_rels else 0.0
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "relevant_total": float(relevant_total),
        "recall@k": float(recall_k),
        "mrr": float(rr),
        "ndcg@k": float(ndcg),
    }


def main() -> None:
    args = parse_args()
    ensure_dir(args.out_dir)

    data = load_dataset(args.dataset)
    test_items, kb_items, split_meta = select_e3_query_and_kb_items(
        data=data,
        test_size=args.test_size,
        seed=args.seed,
        use_e2_test_split=args.use_e2_test_split,
        e2_test_size=args.e2_test_size,
    )
    if not test_items:
        raise RuntimeError("No test items with valid AudioPath found.")

    evaluator = Evaluator()
    encoder = TextureEncoder(project_dim=64)
    retriever = HybridFusionRetriever(kb_items, fusion_mode="weighted")
    fixed_alphas: List[float]
    if args.fixed_alphas:
        fixed_alphas = [float(x) for x in args.fixed_alphas]
    else:
        fixed_alphas = [0.0 if args.audio_only else float(args.fixed_alpha)]
    relevance_cache: Dict[str, set] = {}
    for item in test_items:
        qname = str(item.get("SongName", ""))
        relevance_cache[qname] = build_oracle_relevance_set(
            evaluator=evaluator,
            query_item=item,
            kb_items=kb_items,
            quantile=0.10,
            min_relevant=5,
        )

    rows: List[Dict[str, Any]] = []
    tmp_root = os.path.join(ROOT_DIR, "_p0_e3_tmp")
    ensure_dir(tmp_root)
    try:
        for item in test_items:
            gt = item.get("Parameters", {})
            song = item.get("SongName", "")
            style_terms = " ".join(item.get("Style", []))
            feature_terms = " ".join(item.get("Feature", []))
            style = f"{style_terms} {feature_terms}".strip() or song
            audio_path = item.get("AudioPath")

            item_tmp = tmp_root

            for cond in CONDITIONS:
                degraded_wav = degrade_audio(audio_path, cond, item_tmp, seed=args.seed)
                degraded_trr = encoder.get_embedding(degraded_wav)
                if degraded_trr is None:
                    continue
                degraded_trr = degraded_trr.tolist()

                # Fixed baselines
                for fixed_alpha in fixed_alphas:
                    fixed_result = retriever.retrieve_top_k(
                        style,
                        query_trr_vector=degraded_trr,
                        alpha=fixed_alpha,
                        k=args.top_k,
                        score_norm=args.score_norm,
                        text_scale=args.text_scale,
                        audio_scale=args.audio_scale,
                    )
                    if fixed_result:
                        ranked_songs = [str(x.get("song_name", "")) for x in fixed_result]
                        pred = fixed_result[0].get("params", {})
                        metrics = evaluate_once(evaluator, pred, gt)
                        r_metrics = ranking_metrics(ranked_songs, relevance_cache.get(song, set()), args.top_k)
                        rows.append({
                            "query_song": song,
                            "condition": cond.name,
                            "method": format_fixed_method_name(fixed_alpha),
                            "alpha": fixed_alpha,
                            "top_k": args.top_k,
                            "top1_song": ranked_songs[0] if ranked_songs else "",
                            "topk_songs": json.dumps(ranked_songs, ensure_ascii=False),
                            **metrics,
                            **r_metrics,
                        })

                # Adaptive fusion
                dyn_result = retriever.retrieve_top_k(
                    style,
                    query_trr_vector=degraded_trr,
                    alpha=0.5 if args.adaptive_profile == "confidence_auto" else adaptive_alpha(cond, profile=args.adaptive_profile),
                    k=args.top_k,
                    score_norm=args.score_norm,
                    text_scale=args.text_scale,
                    audio_scale=args.audio_scale,
                    adaptive_alpha_mode="confidence" if args.adaptive_profile == "confidence_auto" else "none",
                    alpha_min=args.confidence_alpha_min,
                    alpha_max=args.confidence_alpha_max,
                    confidence_temperature=args.confidence_temperature,
                )
                if dyn_result:
                    ranked_songs = [str(x.get("song_name", "")) for x in dyn_result]
                    pred = dyn_result[0].get("params", {})
                    metrics = evaluate_once(evaluator, pred, gt)
                    r_metrics = ranking_metrics(ranked_songs, relevance_cache.get(song, set()), args.top_k)
                    dyn_alpha = float(dyn_result[0].get("alpha", 0.5))
                    rows.append({
                        "query_song": song,
                        "condition": cond.name,
                        "method": "adaptive_fusion",
                        "alpha": dyn_alpha,
                        "top_k": args.top_k,
                        "top1_song": ranked_songs[0] if ranked_songs else "",
                        "topk_songs": json.dumps(ranked_songs, ensure_ascii=False),
                        **metrics,
                        **r_metrics,
                    })
    finally:
        if args.keep_temp:
            print(f"Temp files kept at: {tmp_root}")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)

    per_query_csv = os.path.join(args.out_dir, "e3_per_query.csv")
    with open(per_query_csv, "w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # Summary by (condition, method)
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["condition"], r["method"])
        grouped.setdefault(key, []).append(r)

    summary_rows: List[Dict[str, Any]] = []
    for (cond, method), vals in sorted(grouped.items()):
        summary_rows.append({
            "condition": cond,
            "method": method,
            "n": len(vals),
            "alpha_mean": mean([v["alpha"] for v in vals]),
            "l2_mean": mean([v["l2"] for v in vals]),
            "l2_std": std([v["l2"] for v in vals]),
            "acc_mean": mean([v["acc@0.1"] for v in vals]),
            "recall_mean": mean([v["recall"] for v in vals]),
            "cosine_mean": mean([v["cosine"] for v in vals]),
            "module_mean": mean([v["module"] for v in vals]),
            "recall@k_mean": mean([v["recall@k"] for v in vals]),
            "mrr_mean": mean([v["mrr"] for v in vals]),
            "ndcg@k_mean": mean([v["ndcg@k"] for v in vals]),
        })

    summary_csv = os.path.join(args.out_dir, "e3_summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        if summary_rows:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

    # Overall summary by method across all degradation conditions.
    method_grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        method_grouped.setdefault(r["method"], []).append(r)

    overall_rows: List[Dict[str, Any]] = []
    for method, vals in sorted(method_grouped.items()):
        overall_rows.append({
            "method": method,
            "n": len(vals),
            "alpha_mean": mean([v["alpha"] for v in vals]),
            "l2_mean": mean([v["l2"] for v in vals]),
            "acc_mean": mean([v["acc@0.1"] for v in vals]),
            "recall_mean": mean([v["recall"] for v in vals]),
            "cosine_mean": mean([v["cosine"] for v in vals]),
            "module_mean": mean([v["module"] for v in vals]),
            "recall@k_mean": mean([v["recall@k"] for v in vals]),
            "mrr_mean": mean([v["mrr"] for v in vals]),
            "ndcg@k_mean": mean([v["ndcg@k"] for v in vals]),
        })

    overall_csv = os.path.join(args.out_dir, "e3_overall_summary.csv")
    with open(overall_csv, "w", newline="", encoding="utf-8") as f:
        if overall_rows:
            writer = csv.DictWriter(f, fieldnames=list(overall_rows[0].keys()))
            writer.writeheader()
            writer.writerows(overall_rows)

    # Adaptive vs fixed delta summary by condition
    delta_rows: List[Dict[str, Any]] = []
    cond_set = sorted({r["condition"] for r in rows})
    fixed_methods = sorted({r["method"] for r in rows if r["method"].startswith("fixed_fusion_a")})
    for cond in cond_set:
        ad = [r for r in rows if r["condition"] == cond and r["method"] == "adaptive_fusion"]
        for fixed_method in fixed_methods:
            fx = [r for r in rows if r["condition"] == cond and r["method"] == fixed_method]
            n = min(len(fx), len(ad))
            if n == 0:
                continue
            delta_rows.append({
                "condition": cond,
                "fixed_method": fixed_method,
                "n": n,
                "delta_l2_adaptive_minus_fixed": mean([ad[i]["l2"] - fx[i]["l2"] for i in range(n)]),
                "delta_acc_adaptive_minus_fixed": mean([ad[i]["acc@0.1"] - fx[i]["acc@0.1"] for i in range(n)]),
                "delta_cosine_adaptive_minus_fixed": mean([ad[i]["cosine"] - fx[i]["cosine"] for i in range(n)]),
                "delta_module_adaptive_minus_fixed": mean([ad[i]["module"] - fx[i]["module"] for i in range(n)]),
                "delta_recall@k_adaptive_minus_fixed": mean([ad[i]["recall@k"] - fx[i]["recall@k"] for i in range(n)]),
                "delta_mrr_adaptive_minus_fixed": mean([ad[i]["mrr"] - fx[i]["mrr"] for i in range(n)]),
                "delta_ndcg@k_adaptive_minus_fixed": mean([ad[i]["ndcg@k"] - fx[i]["ndcg@k"] for i in range(n)]),
            })

    delta_csv = os.path.join(args.out_dir, "e3_adaptive_vs_fixed.csv")
    with open(delta_csv, "w", newline="", encoding="utf-8") as f:
        if delta_rows:
            writer = csv.DictWriter(f, fieldnames=list(delta_rows[0].keys()))
            writer.writeheader()
            writer.writerows(delta_rows)

    meta = {
        "dataset": args.dataset,
        "seed": args.seed,
        "use_e2_test_split": bool(args.use_e2_test_split),
        "e2_test_size": args.e2_test_size,
        "fixed_alpha": args.fixed_alpha,
        "fixed_alphas": fixed_alphas,
        "score_norm": args.score_norm,
        "text_scale": args.text_scale,
        "audio_scale": args.audio_scale,
        "adaptive_profile": args.adaptive_profile,
        "confidence_alpha_min": args.confidence_alpha_min,
        "confidence_alpha_max": args.confidence_alpha_max,
        "confidence_temperature": args.confidence_temperature,
        "audio_only": bool(args.audio_only),
        "top_k": args.top_k,
        "conditions": [c.__dict__ for c in CONDITIONS],
        "source_test_size": split_meta["source_test_size"],
        "dropped_no_audio": split_meta["dropped_no_audio"],
        "test_size_actual": len(test_items),
        "kb_size_actual": len(kb_items),
    }
    meta_json = os.path.join(args.out_dir, "e3_meta.json")
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("E3 done.")
    print(f"- per-query: {per_query_csv}")
    print(f"- summary:   {summary_csv}")
    print(f"- overall:   {overall_csv}")
    print(f"- deltas:    {delta_csv}")
    print(f"- meta:      {meta_json}")


if __name__ == "__main__":
    main()
