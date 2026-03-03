"""
Protocol-C: Robustness Stress Tests + Modality-Conflict Evaluation (N=211)
============================================================================

This script implements the TMM "Protocol-C" stress-test suite on the paper's
held-out pool (default: N=211) with the KB split aligned to Protocol-A.

What this script produces (audit artifacts):
1) Per-query CSV: each (query × scenario × method) row contains objective metrics
   and fusion weights (w_text / w_audio) derived from entropy-conditioned scoring.
2) Stats reports (JSON + Markdown): 95% bootstrap CIs + paired permutation tests
   with Holm correction for multiple comparisons.

Scenarios:
- standard: original text + original audio
- vague_text: replace text with a generic descriptor (audio unchanged)
- noisy_audio: add strong Gaussian noise in TRR embedding space (text unchanged)
- conflict: contradictory text (audio unchanged)

Methods:
- Text-only: TF-IDF retrieval
- TRR-only: cosine KNN in TRR embedding space
- Fusion: entropy-conditioned score fusion (Algorithm-style), top-1 selection
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

# Ensure common modules are importable when running as a script.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.join(CURRENT_DIR, "..", "common")
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from dataset_loader import load_and_merge_data
from evaluate import Evaluator

# Reuse the Protocol-A held-out pool definition to ensure split consistency.
from direct_retrieval_comparison import is_test_sample_name as is_test_sample


PROTOCOL = "Protocol-C"
METRICS: List[str] = ["l2", "acc@0.1", "recall", "cosine", "module"]
LOWER_IS_BETTER = {"l2"}


def _read_name_list(path: Path) -> List[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _build_text(item: dict) -> str:
    song_name = (item.get("SongName") or "").replace("_", " ")
    style = " ".join(item.get("Style", []) or [])
    return f"{song_name} {style}".strip()


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "guitar",
    "in",
    "is",
    "it",
    "low",
    "no",
    "of",
    "on",
    "or",
    "sound",
    "that",
    "the",
    "this",
    "to",
    "tone",
    "warm",
    "with",
}


def _tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in toks if t not in _STOPWORDS]


def _build_text_index(kb_items: List[dict]) -> Tuple[List[set], Dict[str, float]]:
    """
    Lightweight TF-IDF-like scorer (no sklearn dependency).

    Returns:
    - doc_token_sets: list of token sets per KB item
    - idf: token -> idf weight
    """
    doc_token_sets: List[set] = []
    df: Dict[str, int] = {}
    for it in kb_items:
        toks = set(_tokenize(_build_text(it)))
        doc_token_sets.append(toks)
        for t in toks:
            df[t] = df.get(t, 0) + 1
    n = max(1, len(doc_token_sets))
    idf = {t: float(np.log((n + 1.0) / (c + 1.0)) + 1.0) for t, c in df.items()}
    return doc_token_sets, idf


def _score_text_query(query_text: str, doc_tokens: set, idf: Dict[str, float]) -> float:
    q = set(_tokenize(query_text))
    if not q or not doc_tokens:
        return 0.0
    inter = q.intersection(doc_tokens)
    return float(sum(idf.get(t, 0.0) for t in inter))


def _load_trr_vector(item: dict) -> Optional[np.ndarray]:
    if isinstance(item.get("Vectors"), dict) and item["Vectors"].get("TRR"):
        try:
            return np.asarray(item["Vectors"]["TRR"], dtype=np.float64)
        except Exception:
            pass
    audio_path = item.get("AudioPath")
    if audio_path:
        cache_path = str(audio_path) + ".trr.npy"
        if os.path.exists(cache_path):
            try:
                return np.load(cache_path).astype(np.float64)
            except Exception:
                pass
    return None


def _cosine_scores(query_vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    q = query_vec.astype(np.float64)
    q = q / (np.linalg.norm(q) + 1e-12)
    m = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)
    return m @ q


def _minmax(x: np.ndarray) -> np.ndarray:
    lo = float(np.min(x))
    hi = float(np.max(x))
    if hi - lo < 1e-12:
        return np.zeros_like(x, dtype=np.float64)
    return (x - lo) / (hi - lo)


def _entropy_from_topk(scores: np.ndarray) -> float:
    """
    Shannon entropy computed over a softmax distribution derived from similarity scores.
    """
    s = scores.astype(np.float64)
    s = s - np.max(s)
    p = np.exp(s)
    p = p / (np.sum(p) + 1e-12)
    return float(-np.sum(p * np.log(p + 1e-12)))


def _compute_quality_score(scores: np.ndarray, top_k: int) -> float:
    """
    Compute retrieval quality score from top-K similarity scores.

    The intuition is:
    - "Peaked but wrong": low max score + low variance → low quality
    - "Peaked and correct": high max score + high variance → high quality
    - "Diversely correct": medium max + high variance → medium quality

    Quality = (max_score / (max_possible_score)) × peakedness_factor

    where peakedness_factor captures how much the top result stands out.

    Args:
        scores: Top-K similarity scores (sorted ascending)
        top_k: Number of scores

    Returns:
        Quality score in [0, 1], higher is better
    """
    if top_k <= 1 or len(scores) == 0:
        return 0.5

    # Get the max score (top-1 result)
    max_score = float(scores[-1]) if len(scores) > 0 else 0.0

    # For cosine similarity, max possible is 1.0
    # Normalize by max possible to get absolute strength
    absolute_strength = min(1.0, max_score)

    # Peakedness: ratio of max to second-best (if available)
    # This captures how much the top result stands out
    if len(scores) >= 2:
        second_best = float(scores[-2])
        # Avoid division by zero
        if second_best > 1e-12:
            peakedness = min(2.0, max_score / second_best) / 2.0  # Normalize to [0, 1]
        else:
            peakedness = 1.0
    else:
        peakedness = 1.0

    # Quality = absolute strength × peakedness
    # High absolute strength AND high peakedness → high quality
    # Low absolute strength OR low peakedness → low quality
    quality = absolute_strength * peakedness

    return float(quality)


def _entropy_weights_quality_aware(
    text_topk: np.ndarray,
    audio_topk: np.ndarray,
    *,
    beta: float,
    quality_weight: float = 0.5,
) -> Dict[str, float]:
    """
    Quality-aware entropy fusion weights.

    Formula:
        Q_m = (1 - α) × exp(-β × U_m) + α × quality_m
        w_m = Q_m / (Q_text + Q_audio)

    where:
        U_m = H(p_m) / log(K) - normalized entropy
        quality_m = normalized confidence score

    Args:
        text_topk: Top-K text retrieval scores
        audio_topk: Top-K audio retrieval scores
        beta: Entropy temperature
        quality_weight: Weight of quality factor [0, 1]

    Returns:
        Dictionary with weights and metadata
    """
    top_k = int(text_topk.shape[0])
    if top_k <= 1:
        return {
            "w_text": 0.5,
            "w_audio": 0.5,
            "u_text_norm": 0.0,
            "u_audio_norm": 0.0,
            "q_text": 0.5,
            "q_audio": 0.5,
        }

    # Compute normalized entropy
    u_text = _entropy_from_topk(text_topk)
    u_audio = _entropy_from_topk(audio_topk)
    u_max = float(np.log(top_k))
    u_text_norm = float(u_text / (u_max + 1e-12))
    u_audio_norm = float(u_audio / (u_max + 1e-12))

    # Compute quality scores
    q_text = _compute_quality_score(text_topk, top_k)
    q_audio = _compute_quality_score(audio_topk, top_k)

    # Combine entropy and quality
    # Low entropy + high quality → high weight
    # High entropy + low quality → low weight
    entropy_text = float(np.exp(-float(beta) * u_text_norm))
    entropy_audio = float(np.exp(-float(beta) * u_audio_norm))

    # Weighted combination of entropy confidence and quality score
    w_text_raw = (1.0 - quality_weight) * entropy_text + quality_weight * q_text
    w_audio_raw = (1.0 - quality_weight) * entropy_audio + quality_weight * q_audio

    # Normalize
    z = w_text_raw + w_audio_raw + 1e-12
    w_text = w_text_raw / z
    w_audio = w_audio_raw / z

    return {
        "w_text": w_text,
        "w_audio": w_audio,
        "u_text_norm": u_text_norm,
        "u_audio_norm": u_audio_norm,
        "q_text": q_text,
        "q_audio": q_audio,
    }


def _adaptive_fusion_weights(
    text_topk: np.ndarray,
    audio_topk: np.ndarray,
    *,
    beta: float,
    quality_weight: float = 0.5,
    quality_threshold: float = 0.3,
    audio_bias: float = 0.0,
) -> Dict[str, float]:
    """
    Adaptive fusion weights that can fall back to single-modality retrieval.

    Strategy:
    1. Compute quality scores for both modalities
    2. Apply audio_bias to account for TRR's generally better reliability
    3. If one modality has significantly higher quality (above threshold),
       use it exclusively (winner-takes-all)
    4. Otherwise, use quality-aware weighted fusion

    The audio_bias parameter allows giving TRR a baseline advantage since
    experiments show TRR is generally more reliable than Text.

    Args:
        text_topk: Top-K text retrieval scores
        audio_topk: Top-K audio retrieval scores
        beta: Entropy temperature
        quality_weight: Weight of quality factor [0, 1]
        quality_threshold: Quality difference threshold for exclusive selection
        audio_bias: Baseline advantage for audio [0-1], 0=no bias, 1=audio-only

    Returns:
        Dictionary with weights and metadata
    """
    top_k = int(text_topk.shape[0])
    if top_k <= 1:
        return {
            "w_text": 0.5,
            "w_audio": 0.5,
            "u_text_norm": 0.0,
            "u_audio_norm": 0.0,
            "q_text": 0.5,
            "q_audio": 0.5,
        }

    # Compute normalized entropy
    u_text = _entropy_from_topk(text_topk)
    u_audio = _entropy_from_topk(audio_topk)
    u_max = float(np.log(top_k))
    u_text_norm = float(u_text / (u_max + 1e-12))
    u_audio_norm = float(u_audio / (u_max + 1e-12))

    # Compute quality scores
    q_text = _compute_quality_score(text_topk, top_k)
    q_audio = _compute_quality_score(audio_topk, top_k)

    # Apply audio_bias: boost audio quality by the bias factor
    q_audio_biased = min(1.0, q_audio * (1.0 + float(audio_bias)))

    # Check if one modality is significantly better
    quality_diff = abs(q_audio_biased - q_text)

    if quality_diff > quality_threshold:
        # Winner-takes-all: use the better modality exclusively
        if q_audio_biased > q_text:
            w_text, w_audio = 0.0, 1.0
        else:
            w_text, w_audio = 1.0, 0.0
    else:
        # Use quality-aware weighted fusion with biased audio quality
        entropy_text = float(np.exp(-float(beta) * u_text_norm))
        entropy_audio = float(np.exp(-float(beta) * u_audio_norm))

        w_text_raw = (1.0 - quality_weight) * entropy_text + quality_weight * q_text
        w_audio_raw = (1.0 - quality_weight) * entropy_audio + quality_weight * q_audio_biased

        z = w_text_raw + w_audio_raw + 1e-12
        w_text = w_text_raw / z
        w_audio = w_audio_raw / z

    return {
        "w_text": w_text,
        "w_audio": w_audio,
        "u_text_norm": u_text_norm,
        "u_audio_norm": u_audio_norm,
        "q_text": q_text,
        "q_audio": q_audio,
    }


def _entropy_weights(text_topk: np.ndarray, audio_topk: np.ndarray, *, beta: float) -> Dict[str, float]:
    """Original entropy-only weights (for backward compatibility)."""
    return _entropy_weights_quality_aware(text_topk, audio_topk, beta=beta, quality_weight=0.0)


def _add_noise_unit(vec: np.ndarray, *, noise_level: float, rng: np.random.Generator) -> np.ndarray:
    v = vec.astype(np.float64)
    v = v / (np.linalg.norm(v) + 1e-12)
    eps = rng.normal(loc=0.0, scale=float(noise_level), size=v.shape).astype(np.float64)
    out = v + eps
    out = out / (np.linalg.norm(out) + 1e-12)
    return out


def _generate_conflict_text(item: dict) -> str:
    """
    Heuristic contradictory-text generator for modality-conflict stress tests.

    We flip a coarse "clean-ish" vs "heavy-ish" intent based on SongName/style tokens.
    This is intentionally simple and auditable (no LLM).
    """
    base = _build_text(item).lower()

    heavy_tokens = [
        "metal",
        "djent",
        "high gain",
        "gain",
        "distortion",
        "fuzz",
        "crunch",
        "grunge",
        "doom",
        "stoner",
        "industrial",
        "saturated",
        "breakup",
        "drive",
    ]
    clean_tokens = [
        "clean",
        "acoustic",
        "jazz",
        "neo-soul",
        "crystal",
        "dry",
        "funk",
        "pop",
        "box",
        "jangle",
    ]

    is_heavy = any(t in base for t in heavy_tokens)
    is_clean = any(t in base for t in clean_tokens)

    if is_heavy and not is_clean:
        return "clean dry jazz guitar tone, low gain, no distortion"
    if is_clean and not is_heavy:
        return "aggressive high-gain distorted guitar tone, heavy saturation, modern metal"
    return "aggressive high-gain distorted guitar tone, heavy saturation, modern metal"


@dataclass(frozen=True)
class PerQueryRow:
    protocol: str
    scenario: str
    query_idx: int
    query_name: str
    query_text: str
    method: str
    retrieved_name: str
    w_text: float
    w_audio: float
    u_text_norm: float
    u_audio_norm: float
    l2: float
    acc_at_0_1: float
    recall: float
    cosine: float
    module: float


def _bootstrap_ci_mean(x: np.ndarray, *, n_boot: int, seed: int, alpha: float) -> Tuple[float, float]:
    rng = np.random.default_rng(int(seed))
    n = int(x.shape[0])
    idx = rng.integers(0, n, size=(int(n_boot), n))
    samples = x[idx].mean(axis=1)
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _bootstrap_ci_mean_diff(d: np.ndarray, *, n_boot: int, seed: int, alpha: float) -> Tuple[float, float]:
    rng = np.random.default_rng(int(seed))
    n = int(d.shape[0])
    idx = rng.integers(0, n, size=(int(n_boot), n))
    samples = d[idx].mean(axis=1)
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _paired_permutation_pvalue(d: np.ndarray, *, n_perm: int, seed: int) -> float:
    """
    Two-sided paired permutation test via random sign-flipping.
    """
    rng = np.random.default_rng(int(seed))
    n = int(d.shape[0])
    obs = float(d.mean())
    signs = rng.choice(np.array([-1.0, 1.0], dtype=float), size=(int(n_perm), n), replace=True)
    perm_means = (signs * d).mean(axis=1)
    p = (float(np.sum(np.abs(perm_means) >= abs(obs))) + 1.0) / (float(n_perm) + 1.0)
    return float(p)


def _holm_bonferroni(pvals: List[float]) -> List[float]:
    """
    Holm-Bonferroni adjusted p-values (step-down), preserving original order.
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        p_adj = (m - rank) * pvals[i]
        p_adj = min(1.0, max(p_adj, prev))
        adj[i] = p_adj
        prev = p_adj
    return adj


def _scenario_specs(args: argparse.Namespace) -> List[Tuple[str, str]]:
    all_specs = [
        ("standard", "Standard inputs (original text + original audio)."),
        ("vague_text", f"Vague text: replace text with `{args.vague_text}` (audio unchanged)."),
        ("noisy_audio", f"Noisy audio: add embedding-space Gaussian noise (noise_level={args.noise_level})."),
        ("conflict", "Modality conflict: contradictory text (audio unchanged)."),
    ]
    keep = set([s.strip() for s in (args.scenarios or "").split(",") if s.strip()])
    if not keep:
        return all_specs
    return [(k, d) for (k, d) in all_specs if k in keep]


def _select_split(dataset: List[dict], test_list: str) -> Tuple[List[int], List[int], str]:
    test_source = "built-in held-out pool (Protocol-A)"
    test_name_set: Optional[set] = None
    if test_list:
        p = Path(test_list)
        test_name_set = set(_read_name_list(p))
        test_source = str(p)

    def is_test(name: str) -> bool:
        if test_name_set is not None:
            return name in test_name_set
        return is_test_sample(name)

    test_indices = [i for i, it in enumerate(dataset) if is_test(it.get("SongName") or "")]
    kb_indices = [i for i in range(len(dataset)) if i not in set(test_indices)]
    return test_indices, kb_indices, test_source


def _eval_metrics(evaluator: Evaluator, pred_params: dict, gt_params: dict) -> Tuple[float, float, float, float, float]:
    l2 = float(evaluator.compute_parameter_distance(pred_params, gt_params))
    acc = float(evaluator.compute_accuracy_tolerance(pred_params, gt_params, tolerance=0.1))
    rec = float(evaluator.compute_parameter_recall(pred_params, gt_params))
    cos = float(evaluator.compute_cosine_similarity(pred_params, gt_params))
    mod = float(evaluator.compute_module_consistency(pred_params, gt_params, active_threshold=0.1))
    return l2, acc, rec, cos, mod


def _run_one_scenario(
    *,
    dataset: List[dict],
    test_indices: List[int],
    kb_items: List[dict],
    kb_doc_tokens: List[set],
    idf: Dict[str, float],
    kb_trr_arr: np.ndarray,
    trr_dim: int,
    evaluator: Evaluator,
    scenario_key: str,
    beta: float,
    quality_weight: float,
    quality_threshold: float,
    audio_bias: float,
    top_k: int,
    vague_text: str,
    noise_level: float,
    seed: int,
) -> Tuple[List[PerQueryRow], Dict[int, float]]:
    rows: List[PerQueryRow] = []
    fusion_l2_by_q: Dict[int, float] = {}

    for q_pos, q_idx in enumerate(test_indices, 1):
        q_item = dataset[int(q_idx)]
        q_name = q_item.get("SongName") or f"idx={q_idx}"

        q_text_std = _build_text(q_item)
        if scenario_key == "standard":
            q_text = q_text_std
        elif scenario_key == "vague_text":
            q_text = str(vague_text)
        elif scenario_key == "noisy_audio":
            q_text = q_text_std
        elif scenario_key == "conflict":
            q_text = _generate_conflict_text(q_item)
        else:
            raise ValueError(f"Unknown scenario: {scenario_key}")

        q_trr = _load_trr_vector(q_item)
        if q_trr is None or int(q_trr.shape[0]) != int(trr_dim):
            q_trr = np.zeros(int(trr_dim), dtype=np.float64)

        if scenario_key == "noisy_audio":
            rng = np.random.default_rng(int(seed) + int(q_idx))
            q_trr = _add_noise_unit(q_trr, noise_level=float(noise_level), rng=rng)

        # Text scores: lightweight TF-IDF-like overlap using precomputed IDF weights.
        text_scores_full = np.asarray(
            [_score_text_query(q_text, doc, idf) for doc in kb_doc_tokens], dtype=np.float64
        )

        audio_scores_full = _cosine_scores(q_trr, kb_trr_arr) if kb_trr_arr.size else np.zeros(len(kb_items))

        k_eff = int(min(int(top_k), len(kb_items)))
        text_topk = np.sort(text_scores_full)[-k_eff:] if k_eff > 0 else np.zeros(1)
        audio_topk = np.sort(audio_scores_full)[-k_eff:] if k_eff > 0 else np.zeros(1)

        # Use adaptive fusion if threshold > 0 or bias > 0, otherwise use quality-aware fusion
        if float(quality_threshold) > 0 or float(audio_bias) > 0:
            w = _adaptive_fusion_weights(
                text_topk,
                audio_topk,
                beta=float(beta),
                quality_weight=float(quality_weight),
                quality_threshold=float(quality_threshold),
                audio_bias=float(audio_bias),
            )
        else:
            w = _entropy_weights_quality_aware(
                text_topk, audio_topk, beta=float(beta), quality_weight=float(quality_weight)
            )

        text_best_pos = int(np.argmax(text_scores_full)) if len(text_scores_full) else 0
        trr_best_pos = int(np.argmax(audio_scores_full)) if len(audio_scores_full) else 0
        fused_scores = w["w_text"] * _minmax(text_scores_full) + w["w_audio"] * _minmax(audio_scores_full)
        fused_best_pos = int(np.argmax(fused_scores)) if len(fused_scores) else 0

        gt_params = q_item.get("Parameters") or {}

        def one(method: str, best_pos: int) -> PerQueryRow:
            retrieved_item = kb_items[int(best_pos)]
            retrieved_name = retrieved_item.get("SongName") or "Unknown"
            pred_params = retrieved_item.get("Parameters") or {}
            l2, acc, rec, cos, mod = _eval_metrics(evaluator, pred_params, gt_params)
            return PerQueryRow(
                protocol=PROTOCOL,
                scenario=scenario_key,
                query_idx=int(q_idx),
                query_name=str(q_name),
                query_text=str(q_text),
                method=str(method),
                retrieved_name=str(retrieved_name),
                w_text=float(w["w_text"]),
                w_audio=float(w["w_audio"]),
                u_text_norm=float(w["u_text_norm"]),
                u_audio_norm=float(w["u_audio_norm"]),
                l2=float(l2),
                acc_at_0_1=float(acc),
                recall=float(rec),
                cosine=float(cos),
                module=float(mod),
            )

        for method, pos in [
            ("Text-only", text_best_pos),
            ("TRR-only", trr_best_pos),
            ("Fusion", fused_best_pos),
        ]:
            r = one(method, pos)
            rows.append(r)
            if method == "Fusion":
                fusion_l2_by_q[int(q_idx)] = float(r.l2)

        if q_pos % 50 == 0 or q_pos == len(test_indices):
            print(f"  processed {q_pos}/{len(test_indices)} queries...")

    return rows, fusion_l2_by_q


def main() -> None:
    ap = argparse.ArgumentParser(description="Protocol-C stress tests + modality conflict evaluation (N=211).")
    ap.add_argument(
        "--test_list",
        type=str,
        default="",
        help="Optional newline-separated SongName list for held-out queries (overrides built-in held-out pool).",
    )
    ap.add_argument(
        "--dump_csv",
        type=str,
        default="Experiments/AblationStudies/protocolC_per_query_metrics.csv",
        help="Output per-query CSV path.",
    )
    ap.add_argument("--stats_out_json", type=str, default="Experiments/AblationStudies/protocolC_objective_stats.json")
    ap.add_argument("--stats_out_md", type=str, default="Experiments/AblationStudies/protocolC_objective_stats.md")
    ap.add_argument("--beta", type=float, default=2.0, help="Fusion temperature beta (default: 2.0).")
    ap.add_argument(
        "--quality_weight",
        type=float,
        default=0.5,
        help="Quality-aware fusion weight [0-1], 0=entropy-only, 1=quality-only (default: 0.5).",
    )
    ap.add_argument(
        "--quality_threshold",
        type=float,
        default=0.0,
        help="Adaptive fusion threshold [0-1], >0 enables winner-takes-all when quality diff > threshold (default: 0.0=disabled).",
    )
    ap.add_argument(
        "--audio_bias",
        type=float,
        default=0.0,
        help="Baseline advantage for audio/TRR [0-1], 0=no bias, 0.5=moderate, 1.0=strong (default: 0.0).",
    )
    ap.add_argument("--top_k", type=int, default=5, help="Top-K for entropy computation (default: 5).")
    ap.add_argument("--vague_text", type=str, default="warm guitar tone", help="Generic descriptor for vague-text stress.")
    ap.add_argument("--noise_level", type=float, default=5.0, help="Audio embedding noise level (default: 5.0).")
    ap.add_argument(
        "--scenarios",
        type=str,
        default="standard,vague_text,noisy_audio,conflict",
        help="Comma-separated scenario keys to run.",
    )
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    ap.add_argument("--stats_n_boot", type=int, default=10000, help="Bootstrap resamples (default: 10000).")
    ap.add_argument("--stats_n_perm", type=int, default=20000, help="Permutation samples (default: 20000).")
    ap.add_argument(
        "--beta_sweep_out",
        type=str,
        default="",
        help="Optional CSV output path. If set, runs a beta sweep over {0.5,1,2,4} in STANDARD scenario.",
    )
    args = ap.parse_args()

    dataset = load_and_merge_data()
    n_total = int(len(dataset))

    test_indices, kb_indices, test_source = _select_split(dataset, args.test_list)
    n_test = int(len(test_indices))
    n_kb = int(len(kb_indices))

    print("=" * 88)
    print("Protocol-C: Robustness Stress Tests + Modality Conflict")
    print("=" * 88)
    print(f"- Protocol label: {PROTOCOL}")
    print(f"- Dataset size: N_total={n_total}")
    print(f"- Held-out queries: N_test={n_test} (source: {test_source})")
    print(f"- Knowledge base: N_kb={n_kb}")
    print(f"- Fusion beta={float(args.beta)} top_k={int(args.top_k)}")

    if n_test == 0:
        raise SystemExit("No held-out queries found. Check your dataset JSON and/or --test_list.")

    kb_items = [dataset[i] for i in kb_indices]
    kb_doc_tokens, idf = _build_text_index(kb_items)

    # Candidate TRR vectors
    trr_dim = None
    kb_trr: List[np.ndarray] = []
    for it in kb_items:
        v = _load_trr_vector(it)
        if v is not None and trr_dim is None:
            trr_dim = int(v.shape[0])
        kb_trr.append(v if v is not None else np.zeros(1, dtype=np.float64))
    trr_dim = trr_dim or 4096
    kb_trr_arr = np.stack(
        [
            (v if (v is not None and int(v.shape[0]) == trr_dim) else np.zeros(trr_dim, dtype=np.float64))
            for v in kb_trr
        ],
        axis=0,
    ).astype(np.float64)

    evaluator = Evaluator()

    scenario_specs = _scenario_specs(args)
    all_rows: List[PerQueryRow] = []
    fusion_l2_standard: Dict[int, float] = {}

    for scenario_key, scenario_desc in scenario_specs:
        print(f"\n[Scenario: {scenario_key}] {scenario_desc}")
        rows, fusion_l2_by_q = _run_one_scenario(
            dataset=dataset,
            test_indices=test_indices,
            kb_items=kb_items,
            kb_doc_tokens=kb_doc_tokens,
            idf=idf,
            kb_trr_arr=kb_trr_arr,
            trr_dim=int(trr_dim),
            evaluator=evaluator,
            scenario_key=scenario_key,
            beta=float(args.beta),
            quality_weight=float(args.quality_weight),
            quality_threshold=float(args.quality_threshold),
            audio_bias=float(args.audio_bias),
            top_k=int(args.top_k),
            vague_text=str(args.vague_text),
            noise_level=float(args.noise_level),
            seed=int(args.seed),
        )
        all_rows.extend(rows)
        if scenario_key == "standard":
            fusion_l2_standard = fusion_l2_by_q

    # Per-query CSV
    out_csv = Path(args.dump_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "protocol",
                "scenario",
                "query_idx",
                "query_name",
                "query_text",
                "method",
                "retrieved_name",
                "w_text",
                "w_audio",
                "u_text_norm",
                "u_audio_norm",
                "l2",
                "acc@0.1",
                "recall",
                "cosine",
                "module",
            ]
        )
        for r in all_rows:
            writer.writerow(
                [
                    r.protocol,
                    r.scenario,
                    r.query_idx,
                    r.query_name,
                    r.query_text,
                    r.method,
                    r.retrieved_name,
                    f"{r.w_text:.8f}",
                    f"{r.w_audio:.8f}",
                    f"{r.u_text_norm:.8f}",
                    f"{r.u_audio_norm:.8f}",
                    f"{r.l2:.8f}",
                    f"{r.acc_at_0_1:.8f}",
                    f"{r.recall:.8f}",
                    f"{r.cosine:.8f}",
                    f"{r.module:.8f}",
                ]
            )
    print(f"\nWrote per-query CSV: {out_csv}")

    # Stats
    by_scenario: Dict[str, Dict[str, List[PerQueryRow]]] = {}
    for r in all_rows:
        by_scenario.setdefault(r.scenario, {}).setdefault(r.method, []).append(r)

    def series(rows_: List[PerQueryRow], metric: str) -> np.ndarray:
        if metric == "l2":
            return np.asarray([r.l2 for r in rows_], dtype=np.float64)
        if metric == "acc@0.1":
            return np.asarray([r.acc_at_0_1 for r in rows_], dtype=np.float64)
        if metric == "recall":
            return np.asarray([r.recall for r in rows_], dtype=np.float64)
        if metric == "cosine":
            return np.asarray([r.cosine for r in rows_], dtype=np.float64)
        if metric == "module":
            return np.asarray([r.module for r in rows_], dtype=np.float64)
        raise ValueError(metric)

    stats = {
        "protocol": PROTOCOL,
        "input_dataset": "dataset_loader.load_and_merge_data()",
        "n_total": int(n_total),
        "n_test": int(n_test),
        "n_kb": int(n_kb),
        "test_source": test_source,
        "beta": float(args.beta),
        "quality_weight": float(args.quality_weight),
        "quality_threshold": float(args.quality_threshold),
        "audio_bias": float(args.audio_bias),
        "top_k": int(args.top_k),
        "noise_level": float(args.noise_level),
        "vague_text": str(args.vague_text),
        "env": {
            "python": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "scenarios": {},
        "comparisons": [],
        "comparisons_note": "Signed diffs are defined so that positive means Fusion is better.",
    }

    raw_pvals: List[float] = []

    for scenario_key, _ in scenario_specs:
        methods = by_scenario.get(scenario_key, {})
        if not methods:
            continue

        # Weight distribution is read from Fusion rows (same weights per query in this scenario).
        w_rows = methods.get("Fusion", [])
        w_text_arr = np.asarray([r.w_text for r in w_rows], dtype=np.float64)
        w_audio_arr = np.asarray([r.w_audio for r in w_rows], dtype=np.float64)

        stats["scenarios"][scenario_key] = {
            "n": int(len(w_rows)),
            "weights": {
                "w_text": {
                    "mean": float(w_text_arr.mean()) if len(w_text_arr) else float("nan"),
                    "std": float(w_text_arr.std(ddof=1)) if len(w_text_arr) > 1 else 0.0,
                    "p25": float(np.quantile(w_text_arr, 0.25)) if len(w_text_arr) else float("nan"),
                    "p50": float(np.quantile(w_text_arr, 0.50)) if len(w_text_arr) else float("nan"),
                    "p75": float(np.quantile(w_text_arr, 0.75)) if len(w_text_arr) else float("nan"),
                    "min": float(w_text_arr.min()) if len(w_text_arr) else float("nan"),
                    "max": float(w_text_arr.max()) if len(w_text_arr) else float("nan"),
                },
                "w_audio": {
                    "mean": float(w_audio_arr.mean()) if len(w_audio_arr) else float("nan"),
                    "std": float(w_audio_arr.std(ddof=1)) if len(w_audio_arr) > 1 else 0.0,
                    "p25": float(np.quantile(w_audio_arr, 0.25)) if len(w_audio_arr) else float("nan"),
                    "p50": float(np.quantile(w_audio_arr, 0.50)) if len(w_audio_arr) else float("nan"),
                    "p75": float(np.quantile(w_audio_arr, 0.75)) if len(w_audio_arr) else float("nan"),
                    "min": float(w_audio_arr.min()) if len(w_audio_arr) else float("nan"),
                    "max": float(w_audio_arr.max()) if len(w_audio_arr) else float("nan"),
                },
            },
            "methods": {},
        }

        for method_name, method_rows in methods.items():
            stats["scenarios"][scenario_key]["methods"][method_name] = {"n": int(len(method_rows)), "metrics": {}}
            for metric in METRICS:
                x = series(method_rows, metric)
                lo, hi = _bootstrap_ci_mean(
                    x, n_boot=int(args.stats_n_boot), seed=int(args.seed), alpha=0.05
                )
                stats["scenarios"][scenario_key]["methods"][method_name]["metrics"][metric] = {
                    "mean": float(x.mean()),
                    "std": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
                    "ci95": [float(lo), float(hi)],
                }

        fusion_rows = methods.get("Fusion", [])
        if not fusion_rows:
            continue

        fusion_by_q = {int(r.query_idx): r for r in fusion_rows}
        for baseline in ["Text-only", "TRR-only"]:
            base_rows = methods.get(baseline, [])
            if not base_rows:
                continue
            base_by_q = {int(r.query_idx): r for r in base_rows}
            shared_q = sorted(set(fusion_by_q.keys()).intersection(base_by_q.keys()))
            if not shared_q:
                continue
            for metric in METRICS:
                a = np.asarray([series([fusion_by_q[q]], metric)[0] for q in shared_q], dtype=np.float64)
                b = np.asarray([series([base_by_q[q]], metric)[0] for q in shared_q], dtype=np.float64)
                if metric in LOWER_IS_BETTER:
                    d = b - a  # positive means Fusion better
                else:
                    d = a - b
                lo, hi = _bootstrap_ci_mean_diff(
                    d, n_boot=int(args.stats_n_boot), seed=int(args.seed), alpha=0.05
                )
                p = _paired_permutation_pvalue(d, n_perm=int(args.stats_n_perm), seed=int(args.seed))
                stats["comparisons"].append(
                    {
                        "scenario": scenario_key,
                        "baseline": baseline,
                        "metric": metric,
                        "n": int(len(shared_q)),
                        "mean_diff_signed": float(d.mean()),
                        "ci95_signed": [float(lo), float(hi)],
                        "p_perm_two_sided": float(p),
                    }
                )
                raw_pvals.append(float(p))

    if raw_pvals:
        adj = _holm_bonferroni(raw_pvals)
        for rec, p_adj in zip(stats["comparisons"], adj):
            rec["p_holm"] = float(p_adj)

    # Modality-conflict degradation + representative failures (largest Fusion ΔL2).
    if (
        "standard" in by_scenario
        and "Fusion" in by_scenario["standard"]
        and "conflict" in by_scenario
        and "Fusion" in by_scenario["conflict"]
    ):
        standard_fusion_rows = by_scenario["standard"]["Fusion"]
        conflict_fusion_rows = by_scenario["conflict"]["Fusion"]

        std_by_q = {int(r.query_idx): r for r in standard_fusion_rows}
        conflict_by_q = {int(r.query_idx): r for r in conflict_fusion_rows}
        shared_q = sorted(set(std_by_q.keys()).intersection(conflict_by_q.keys()))

        if shared_q:
            # Degradation statistics for Fusion under conflict vs standard.
            degradation = {"n": int(len(shared_q)), "metrics": {}}
            for metric in METRICS:
                std_vals = np.asarray([series([std_by_q[q]], metric)[0] for q in shared_q], dtype=np.float64)
                conflict_vals = np.asarray([series([conflict_by_q[q]], metric)[0] for q in shared_q], dtype=np.float64)
                d = conflict_vals - std_vals  # positive means worse for LOWER_IS_BETTER metrics
                lo, hi = _bootstrap_ci_mean_diff(
                    d, n_boot=int(args.stats_n_boot), seed=int(args.seed), alpha=0.05
                )
                degradation["metrics"][metric] = {
                    "mean_delta": float(d.mean()),
                    "ci95_delta": [float(lo), float(hi)],
                }
            stats["conflict_degradation_vs_standard_fusion"] = degradation

            # Representative worst failures by ΔL2.
            worst = []
            for q in shared_q:
                r = conflict_by_q[q]
                base = std_by_q[q].l2
                worst.append((float(r.l2 - base), r, float(base)))
            worst.sort(key=lambda t: t[0], reverse=True)
            top = worst[:3]
            stats["conflict_failure_cases"] = [
                {
                    "query_idx": int(r.query_idx),
                    "query_name": r.query_name,
                    "standard_fusion_l2": float(base_l2),
                    "conflict_fusion_l2": float(r.l2),
                    "delta_l2": float(delta),
                    "conflict_text": r.query_text,
                    "w_text": float(r.w_text),
                    "w_audio": float(r.w_audio),
                    "u_text_norm": float(r.u_text_norm),
                    "u_audio_norm": float(r.u_audio_norm),
                    "retrieved_name": r.retrieved_name,
                }
                for (delta, r, base_l2) in top
            ]

    out_json = Path(args.stats_out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote stats JSON: {out_json}")

    # Markdown report
    out_md = Path(args.stats_out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    def fmt_ci(ci: Iterable[float]) -> str:
        a, b = list(ci)
        return f"[{a:.4f}, {b:.4f}]"

    lines: List[str] = []
    lines.append("# Protocol-C: Robustness + Modality-Conflict (Objective Metrics)")
    lines.append("")
    lines.append(f"- Protocol: **{PROTOCOL}**")
    lines.append(f"- Per-query CSV: `{out_csv}`")
    lines.append(f"- Dataset: N_total={n_total}, N_test={n_test}, N_kb={n_kb}")
    lines.append(f"- Test source: `{test_source}`")
    lines.append(f"- Fusion beta={float(args.beta)} quality_weight={float(args.quality_weight)} quality_threshold={float(args.quality_threshold)} audio_bias={float(args.audio_bias)} top_k={int(args.top_k)}")
    lines.append(f"- Vague text: `{args.vague_text}`")
    lines.append(f"- Audio noise_level: {float(args.noise_level)}")
    lines.append(f"- Bootstrap: n_boot={int(args.stats_n_boot)} (seed={int(args.seed)})")
    lines.append(f"- Paired permutation: n_perm={int(args.stats_n_perm)} (seed={int(args.seed)})")
    lines.append("")

    lines.append("## Scenario Summaries (Mean Over Queries, 95% CI)")
    for scenario_key, desc in scenario_specs:
        if scenario_key not in stats["scenarios"]:
            continue
        srec = stats["scenarios"][scenario_key]
        lines.append("")
        lines.append(f"### {scenario_key}")
        lines.append(f"- {desc}")
        wtxt = srec["weights"]["w_text"]
        waud = srec["weights"]["w_audio"]
        lines.append(
            f"- Weight stats (Fusion): "
            f"w_text mean={wtxt['mean']:.4f} std={wtxt['std']:.4f} "
            f"p25/p50/p75={wtxt['p25']:.4f}/{wtxt['p50']:.4f}/{wtxt['p75']:.4f} "
            f"min/max={wtxt['min']:.4f}/{wtxt['max']:.4f}"
        )
        lines.append(
            f"- Weight stats (Fusion): "
            f"w_audio mean={waud['mean']:.4f} std={waud['std']:.4f} "
            f"p25/p50/p75={waud['p25']:.4f}/{waud['p50']:.4f}/{waud['p75']:.4f} "
            f"min/max={waud['min']:.4f}/{waud['max']:.4f}"
        )
        lines.append("")
        header = ["Method", "n"] + [f"{m} (mean, 95% CI)" for m in METRICS]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for method_name in ["Text-only", "TRR-only", "Fusion"]:
            mrec = srec["methods"].get(method_name)
            if not mrec:
                continue
            row = [method_name, str(int(mrec["n"]))]
            for metric in METRICS:
                mm = mrec["metrics"][metric]
                row.append(f"{mm['mean']:.4f}, {fmt_ci(mm['ci95'])}")
            lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Paired Tests (Fusion vs Baselines, Holm-Corrected)")
    lines.append("")
    if not stats["comparisons"]:
        lines.append("_No comparisons were generated._")
    else:
        header = ["Scenario", "Baseline", "Metric", "n", "MeanΔ (signed)", "95% CI", "p", "p(Holm)"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for rec in stats["comparisons"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        rec["scenario"],
                        rec["baseline"],
                        rec["metric"],
                        str(int(rec["n"])),
                        f"{float(rec['mean_diff_signed']):.4f}",
                        fmt_ci(rec["ci95_signed"]),
                        f"{float(rec['p_perm_two_sided']):.4g}",
                        f"{float(rec.get('p_holm', float('nan'))):.4g}",
                    ]
                )
                + " |"
            )

    if stats.get("conflict_failure_cases"):
        if stats.get("conflict_degradation_vs_standard_fusion"):
            lines.append("")
            lines.append("## Modality-Conflict Degradation (Fusion: conflict - standard)")
            lines.append("")
            drec = stats["conflict_degradation_vs_standard_fusion"]
            lines.append(f"- n={int(drec['n'])} paired queries")
            lines.append("")
            header = ["Metric", "MeanΔ", "95% CI (Δ)"]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join(["---"] * len(header)) + " |")
            for metric in METRICS:
                mm = drec["metrics"][metric]
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            metric,
                            f"{float(mm['mean_delta']):.4f}",
                            fmt_ci(mm["ci95_delta"]),
                        ]
                    )
                    + " |"
                )

        lines.append("")
        lines.append("## Representative Modality-Conflict Failures (Largest ΔL2 vs Standard Fusion)")
        lines.append("")
        for i, ex in enumerate(stats["conflict_failure_cases"], 1):
            lines.append(
                f"{i}. query_idx={ex['query_idx']} name=`{ex['query_name']}` "
                f"ΔL2={ex['delta_l2']:.4f} (standard={ex['standard_fusion_l2']:.4f}, conflict={ex['conflict_fusion_l2']:.4f}), "
                f"w_text={ex['w_text']:.3f}, w_audio={ex['w_audio']:.3f}, retrieved=`{ex['retrieved_name']}`"
            )
            lines.append(f"   conflict_text: `{ex['conflict_text']}`")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote stats Markdown: {out_md}")

    # Optional beta sweep in STANDARD scenario (for paper table).
    if args.beta_sweep_out:
        betas = [0.5, 1.0, 2.0, 4.0]
        print("\n[Beta sweep] Running STANDARD scenario for beta in {0.5,1,2,4} ...")
        rows_by_beta = []
        for b in betas:
            sweep_rows, _ = _run_one_scenario(
                dataset=dataset,
                test_indices=test_indices,
                kb_items=kb_items,
                kb_doc_tokens=kb_doc_tokens,
                idf=idf,
                kb_trr_arr=kb_trr_arr,
                trr_dim=int(trr_dim),
                evaluator=evaluator,
                scenario_key="standard",
                beta=float(b),
                quality_weight=float(args.quality_weight),
                quality_threshold=float(args.quality_threshold),
                audio_bias=float(args.audio_bias),
                top_k=int(args.top_k),
                vague_text=str(args.vague_text),
                noise_level=float(args.noise_level),
                seed=int(args.seed),
            )
            fusion_rows = [r for r in sweep_rows if r.method == "Fusion"]
            w_text_arr = np.asarray([r.w_text for r in fusion_rows], dtype=np.float64)
            l2_arr = np.asarray([r.l2 for r in fusion_rows], dtype=np.float64)
            rows_by_beta.append(
                {
                    "beta": float(b),
                    "w_text_mean": float(w_text_arr.mean()),
                    "w_text_std": float(w_text_arr.std(ddof=1)) if len(w_text_arr) > 1 else 0.0,
                    "w_text_min": float(w_text_arr.min()),
                    "w_text_max": float(w_text_arr.max()),
                    "l2_fusion_mean": float(l2_arr.mean()),
                }
            )
        out = Path(args.beta_sweep_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=["beta", "w_text_mean", "w_text_std", "w_text_min", "w_text_max", "l2_fusion_mean"]
            )
            w.writeheader()
            for r in rows_by_beta:
                w.writerow(r)
        print(f"Wrote beta sweep CSV: {out}")


if __name__ == "__main__":
    main()
