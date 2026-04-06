import argparse
import os
import tempfile

import numpy as np

from p0_e3_protocol_c import Condition, adaptive_alpha, degrade_audio, load_dataset

import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(CURRENT_DIR, "..", "..")
sys.path.append(ROOT_DIR)

from Experiments.common.hybrid_fusion_retriever import HybridFusionRetriever  # noqa: E402
from Experiments.TextureResonance.texture_encoder import TextureEncoder  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Print original vs degraded TRR embeddings using the same E3 audio degradation pipeline."
    )
    p.add_argument("--audio", required=True, help="Path to the source audio file.")
    p.add_argument(
        "--dataset",
        default=os.path.join("Experiments", "dataset_full_vectors.json"),
        help="Dataset JSON used to build the retrieval database.",
    )
    p.add_argument(
        "--kind",
        default="awgn",
        choices=["awgn", "mp3", "reverb", "truncate"],
        help="Degradation type.",
    )
    p.add_argument(
        "--value",
        type=float,
        default=10.0,
        help="Degradation value. Examples: awgn=10, mp3=64, reverb=0.6, truncate=0.5",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed for stochastic degradation.")
    p.add_argument(
        "--project-dim",
        type=int,
        default=64,
        help="TRR projection dimension. Use 64 to match current E3 setup.",
    )
    p.add_argument(
        "--print-dims",
        type=int,
        default=16,
        help="How many leading embedding dimensions to print.",
    )
    p.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Text weight used by the weighted hybrid retriever.",
    )
    p.add_argument(
        "--use-adaptive-alpha",
        action="store_true",
        help="Use the same adaptive alpha schedule as E3 instead of a fixed alpha.",
    )
    p.add_argument(
        "--adaptive-profile",
        choices=["default", "audio_balanced", "tuned", "monotonic", "confidence_auto"],
        default="audio_balanced",
        help="Adaptive alpha schedule profile.",
    )
    p.add_argument(
        "--score-norm",
        choices=["none", "zscore", "minmax"],
        default="zscore",
        help="Normalize text/audio scores before fusion.",
    )
    p.add_argument("--text-scale", type=float, default=1.0, help="Multiplier for normalized text scores.")
    p.add_argument("--audio-scale", type=float, default=1.0, help="Multiplier for normalized audio scores.")
    p.add_argument("--confidence-alpha-min", type=float, default=0.3, help="Lower bound for automatic confidence-based alpha.")
    p.add_argument("--confidence-alpha-max", type=float, default=0.8, help="Upper bound for automatic confidence-based alpha.")
    p.add_argument("--confidence-temperature", type=float, default=8.0, help="Margin-to-confidence temperature for automatic alpha.")
    return p.parse_args()


def format_vector(vec: np.ndarray, n: int) -> str:
    clipped = vec[:n]
    return np.array2string(clipped, precision=6, suppress_small=False, separator=", ")


def normalize_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def find_query_item(dataset, audio_path: str):
    target = normalize_path(audio_path)
    for item in dataset:
        item_audio = item.get("AudioPath")
        if item_audio and normalize_path(item_audio) == target:
            return item
    return None


def main() -> None:
    args = parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")
    dataset_path = os.path.abspath(args.dataset)
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    condition_name = f"{args.kind}_{str(args.value).replace('.', '_')}"
    cond = Condition(condition_name, args.kind, float(args.value))
    alpha = adaptive_alpha(cond, profile=args.adaptive_profile) if (args.use_adaptive_alpha and args.adaptive_profile != "confidence_auto") else float(args.alpha)
    adaptive_alpha_mode = "confidence" if (args.use_adaptive_alpha and args.adaptive_profile == "confidence_auto") else "none"

    dataset = load_dataset(dataset_path)
    query_item = find_query_item(dataset, audio_path)
    query_song = (
        str(query_item.get("SongName", ""))
        if query_item is not None
        else os.path.splitext(os.path.basename(audio_path))[0]
    )
    if query_item:
        style_terms = " ".join(query_item.get("Style", []))
        feature_terms = " ".join(query_item.get("Feature", []))
        query_text = f"{style_terms} {feature_terms}".strip() or query_song
    else:
        query_text = query_song

    encoder = TextureEncoder(project_dim=args.project_dim)
    retriever = HybridFusionRetriever(dataset, fusion_mode="weighted")

    with tempfile.TemporaryDirectory(prefix="inspect_e3_emb_") as tmp_dir:
        degraded_path = degrade_audio(audio_path, cond, tmp_dir, args.seed)

        original_vec = encoder.get_embedding(audio_path)
        degraded_vec = encoder.get_embedding(degraded_path)

        if original_vec is None:
            raise RuntimeError("Failed to encode original audio.")
        if degraded_vec is None:
            raise RuntimeError("Failed to encode degraded audio.")

        cosine = float(np.dot(original_vec, degraded_vec))
        l2 = float(np.linalg.norm(original_vec - degraded_vec))
        abs_delta = np.abs(original_vec - degraded_vec)
        original_result = retriever.retrieve_top_k(
            query_text,
            query_trr_vector=original_vec.tolist(),
            alpha=alpha,
            k=1,
            score_norm=args.score_norm,
            text_scale=args.text_scale,
            audio_scale=args.audio_scale,
            adaptive_alpha_mode=adaptive_alpha_mode,
            alpha_min=args.confidence_alpha_min,
            alpha_max=args.confidence_alpha_max,
            confidence_temperature=args.confidence_temperature,
        )
        degraded_result = retriever.retrieve_top_k(
            query_text,
            query_trr_vector=degraded_vec.tolist(),
            alpha=alpha,
            k=1,
            score_norm=args.score_norm,
            text_scale=args.text_scale,
            audio_scale=args.audio_scale,
            adaptive_alpha_mode=adaptive_alpha_mode,
            alpha_min=args.confidence_alpha_min,
            alpha_max=args.confidence_alpha_max,
            confidence_temperature=args.confidence_temperature,
        )
        original_top1 = original_result[0].get("song_name", "") if original_result else ""
        degraded_top1 = degraded_result[0].get("song_name", "") if degraded_result else ""
        original_final_score = float(original_result[0].get("score", 0.0)) if original_result else 0.0
        original_text_score = float(original_result[0].get("text_score", 0.0)) if original_result else 0.0
        original_audio_score = float(original_result[0].get("audio_score", 0.0)) if original_result else 0.0
        original_text_score_scaled = float(original_result[0].get("text_score_scaled", 0.0)) if original_result else 0.0
        original_audio_score_scaled = float(original_result[0].get("audio_score_scaled", 0.0)) if original_result else 0.0
        original_alpha = float(original_result[0].get("alpha", alpha)) if original_result else float(alpha)
        original_alpha_source = str(original_result[0].get("alpha_source", "fixed")) if original_result else "fixed"
        original_text_margin = float(original_result[0].get("text_margin", 0.0)) if original_result else 0.0
        original_audio_margin = float(original_result[0].get("audio_margin", 0.0)) if original_result else 0.0
        original_text_peak = float(original_result[0].get("text_peak", 0.0)) if original_result else 0.0
        original_audio_peak = float(original_result[0].get("audio_peak", 0.0)) if original_result else 0.0
        original_peak_gap_bias = float(original_result[0].get("peak_gap_bias", 0.0)) if original_result else 0.0
        original_weak_audio_bias = float(original_result[0].get("weak_audio_bias", 0.0)) if original_result else 0.0
        original_low_audio_peak_bias = float(original_result[0].get("low_audio_peak_bias", 0.0)) if original_result else 0.0
        original_low_audio_margin_bias = float(original_result[0].get("low_audio_margin_bias", 0.0)) if original_result else 0.0
        original_text_conf = float(original_result[0].get("text_confidence", 0.0)) if original_result else 0.0
        original_audio_conf = float(original_result[0].get("audio_confidence", 0.0)) if original_result else 0.0
        degraded_final_score = float(degraded_result[0].get("score", 0.0)) if degraded_result else 0.0
        degraded_text_score = float(degraded_result[0].get("text_score", 0.0)) if degraded_result else 0.0
        degraded_audio_score = float(degraded_result[0].get("audio_score", 0.0)) if degraded_result else 0.0
        degraded_text_score_scaled = float(degraded_result[0].get("text_score_scaled", 0.0)) if degraded_result else 0.0
        degraded_audio_score_scaled = float(degraded_result[0].get("audio_score_scaled", 0.0)) if degraded_result else 0.0
        degraded_alpha = float(degraded_result[0].get("alpha", alpha)) if degraded_result else float(alpha)
        degraded_alpha_source = str(degraded_result[0].get("alpha_source", "fixed")) if degraded_result else "fixed"
        degraded_text_margin = float(degraded_result[0].get("text_margin", 0.0)) if degraded_result else 0.0
        degraded_audio_margin = float(degraded_result[0].get("audio_margin", 0.0)) if degraded_result else 0.0
        degraded_text_peak = float(degraded_result[0].get("text_peak", 0.0)) if degraded_result else 0.0
        degraded_audio_peak = float(degraded_result[0].get("audio_peak", 0.0)) if degraded_result else 0.0
        degraded_peak_gap_bias = float(degraded_result[0].get("peak_gap_bias", 0.0)) if degraded_result else 0.0
        degraded_weak_audio_bias = float(degraded_result[0].get("weak_audio_bias", 0.0)) if degraded_result else 0.0
        degraded_low_audio_peak_bias = float(degraded_result[0].get("low_audio_peak_bias", 0.0)) if degraded_result else 0.0
        degraded_low_audio_margin_bias = float(degraded_result[0].get("low_audio_margin_bias", 0.0)) if degraded_result else 0.0
        degraded_text_conf = float(degraded_result[0].get("text_confidence", 0.0)) if degraded_result else 0.0
        degraded_audio_conf = float(degraded_result[0].get("audio_confidence", 0.0)) if degraded_result else 0.0

        print("=== E3 Embedding Inspection ===")
        print(f"query_song:      {query_song}")
        print(f"audio:          {audio_path}")
        print(f"degraded_audio: {degraded_path}")
        print(f"dataset:        {dataset_path}")
        print(f"condition:      {args.kind} ({args.value})")
        print(f"seed:           {args.seed}")
        print(f"alpha:          {alpha}")
        print(f"alpha_mode:     {adaptive_alpha_mode or 'fixed'}")
        print(f"score_norm:     {args.score_norm}")
        print(f"text_scale:     {args.text_scale}")
        print(f"audio_scale:    {args.audio_scale}")
        print(f"embedding_dim:  {original_vec.shape[0]}")
        print(f"top1_original:  {original_top1}")
        print(f"  alpha_used:   {original_alpha:.6f} ({original_alpha_source})")
        print(f"  text_margin:  {original_text_margin:.6f}")
        print(f"  audio_margin: {original_audio_margin:.6f}")
        print(f"  text_peak:    {original_text_peak:.6f}")
        print(f"  audio_peak:   {original_audio_peak:.6f}")
        print(f"  peak_bias:    {original_peak_gap_bias:.6f}")
        print(f"  weak_bias:    {original_weak_audio_bias:.6f}")
        print(f"  low_peak_b:   {original_low_audio_peak_bias:.6f}")
        print(f"  low_marg_b:   {original_low_audio_margin_bias:.6f}")
        print(f"  text_conf:    {original_text_conf:.6f}")
        print(f"  audio_conf:   {original_audio_conf:.6f}")
        print(f"  text_score:   {original_text_score:.6f}")
        print(f"  audio_score:  {original_audio_score:.6f}")
        print(f"  text_scaled:  {original_text_score_scaled:.6f}")
        print(f"  audio_scaled: {original_audio_score_scaled:.6f}")
        print(f"  final_score:  {original_final_score:.6f}")
        print(f"top1_degraded:  {degraded_top1}")
        print(f"  alpha_used:   {degraded_alpha:.6f} ({degraded_alpha_source})")
        print(f"  text_margin:  {degraded_text_margin:.6f}")
        print(f"  audio_margin: {degraded_audio_margin:.6f}")
        print(f"  text_peak:    {degraded_text_peak:.6f}")
        print(f"  audio_peak:   {degraded_audio_peak:.6f}")
        print(f"  peak_bias:    {degraded_peak_gap_bias:.6f}")
        print(f"  weak_bias:    {degraded_weak_audio_bias:.6f}")
        print(f"  low_peak_b:   {degraded_low_audio_peak_bias:.6f}")
        print(f"  low_marg_b:   {degraded_low_audio_margin_bias:.6f}")
        print(f"  text_conf:    {degraded_text_conf:.6f}")
        print(f"  audio_conf:   {degraded_audio_conf:.6f}")
        print(f"  text_score:   {degraded_text_score:.6f}")
        print(f"  audio_score:  {degraded_audio_score:.6f}")
        print(f"  text_scaled:  {degraded_text_score_scaled:.6f}")
        print(f"  audio_scaled: {degraded_audio_score_scaled:.6f}")
        print(f"  final_score:  {degraded_final_score:.6f}")
        print()
        print("Original embedding:")
        print(format_vector(original_vec, args.print_dims))
        print()
        print("Degraded embedding:")
        print(format_vector(degraded_vec, args.print_dims))
        print()
        print("Absolute delta (leading dims):")
        print(format_vector(abs_delta, args.print_dims))
        print()
        print(f"cosine_similarity: {cosine:.6f}")
        print(f"l2_distance:       {l2:.6f}")
        print(f"max_abs_delta:     {float(abs_delta.max()):.6f}")
        print(f"mean_abs_delta:    {float(abs_delta.mean()):.6f}")


if __name__ == "__main__":
    main()
