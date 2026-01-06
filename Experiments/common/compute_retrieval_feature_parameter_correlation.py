import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from dataset_loader import load_and_merge_data
from evaluate import Evaluator


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def dot_similarity(a: np.ndarray, b: np.ndarray) -> float:
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    return float(np.dot(a[:min_len], b[:min_len]))


def sanitize_song_name(song_name: str) -> str:
    return "".join([c for c in song_name if c.isalpha() or c.isdigit() or c in (" ", "-", "_")]).strip()


def try_load_trr_embedding(repo_root: str, item: Dict[str, Any]) -> Optional[np.ndarray]:
    audio_path = item.get("AudioPath")
    if isinstance(audio_path, str) and audio_path:
        candidate = audio_path + ".trr.npy"
        if os.path.exists(candidate):
            return np.load(candidate)

    base_audio_dir = os.path.join(repo_root, "Data", "Audio_Synthetic")
    song_name = str(item.get("SongName", ""))
    safe_name = sanitize_song_name(song_name)

    candidates = [
        os.path.join(base_audio_dir, f"{song_name}.wav.trr.npy"),
        os.path.join(base_audio_dir, f"{safe_name}.wav.trr.npy"),
    ]

    for c in candidates:
        if os.path.exists(c):
            return np.load(c)

    return None


def parse_vector(v: Any) -> Optional[np.ndarray]:
    if v is None:
        return None
    if isinstance(v, list) and v:
        try:
            return np.asarray([float(x) for x in v], dtype=np.float32)
        except Exception:
            return None
    if isinstance(v, str) and v.strip():
        try:
            return np.asarray([float(x) for x in v.split(",")], dtype=np.float32)
        except Exception:
            return None
    return None


def rankdata(values: List[float]) -> List[float]:
    indexed = sorted(enumerate(values), key=lambda t: t[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def pearsonr(x: List[float], y: List[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return float("nan")

    mx = sum(x) / len(x)
    my = sum(y) / len(y)

    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denx = math.sqrt(sum((a - mx) ** 2 for a in x))
    deny = math.sqrt(sum((b - my) ** 2 for b in y))
    den = denx * deny
    if den == 0.0:
        return float("nan")
    return num / den


def spearmanr(x: List[float], y: List[float]) -> float:
    rx = rankdata(x)
    ry = rankdata(y)
    return pearsonr(rx, ry)


def is_non_stationary(item: Dict[str, Any]) -> bool:
    style = " ".join([str(x) for x in item.get("Style", [])])
    feature = " ".join([str(x) for x in item.get("Feature", [])])
    name = str(item.get("SongName", ""))
    text = f"{style} {feature} {name}".lower()

    keywords = [
        # Non-linear / saturation
        "distortion",
        "fuzz",
        "overdrive",
        "drive",
        "saturation",
        "clipping",
        "bitcrush",
        "bitcrushed",
        # Time-varying modulation
        "chorus",
        "flanger",
        "phaser",
        "wah",
        "auto-wah",
        "tremolo",
        "vibrato",
        "modulation",
    ]
    return any(k in text for k in keywords)


def compute_feature_parameter_alignment(repo_root: str) -> Dict[str, Any]:
    dataset = load_and_merge_data()
    evaluator = Evaluator()

    items: List[Dict[str, Any]] = []
    for item in dataset:
        vec = parse_vector(item.get("Vector"))
        trr = try_load_trr_embedding(repo_root, item)
        items.append({
            "raw": item,
            "vector": vec,
            "trr": trr,
            "non_stationary": is_non_stationary(item),
        })

    vec_feature_sims_all: List[float] = []
    vec_param_sims_all: List[float] = []
    vec_feature_sims_ns: List[float] = []
    vec_param_sims_ns: List[float] = []

    trr_feature_sims_all: List[float] = []
    trr_param_sims_all: List[float] = []
    trr_feature_sims_ns: List[float] = []
    trr_param_sims_ns: List[float] = []

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i]
            b = items[j]

            pa = a["raw"].get("Parameters", {})
            pb = b["raw"].get("Parameters", {})
            param_sim = float(evaluator.compute_cosine_similarity(pa, pb))

            a_vec = a["vector"]
            b_vec = b["vector"]
            if a_vec is not None and b_vec is not None:
                min_len = min(len(a_vec), len(b_vec))
                if min_len > 0:
                    vec_sim = cosine_similarity(a_vec[:min_len], b_vec[:min_len])
                    vec_feature_sims_all.append(float(vec_sim))
                    vec_param_sims_all.append(param_sim)

                    if a["non_stationary"] and b["non_stationary"]:
                        vec_feature_sims_ns.append(float(vec_sim))
                        vec_param_sims_ns.append(param_sim)

            a_trr = a["trr"]
            b_trr = b["trr"]
            if a_trr is not None and b_trr is not None:
                min_len = min(len(a_trr), len(b_trr))
                if min_len > 0:
                    trr_sim = dot_similarity(a_trr[:min_len], b_trr[:min_len])
                    trr_feature_sims_all.append(float(trr_sim))
                    trr_param_sims_all.append(param_sim)

                    if a["non_stationary"] and b["non_stationary"]:
                        trr_feature_sims_ns.append(float(trr_sim))
                        trr_param_sims_ns.append(param_sim)

    def summarize(feature_sims: List[float], param_sims: List[float]) -> Dict[str, Any]:
        if len(feature_sims) != len(param_sims):
            return {"n": 0, "spearman": float("nan"), "pearson": float("nan")}
        n = len(feature_sims)
        if n < 2:
            return {"n": n, "spearman": float("nan"), "pearson": float("nan")}
        return {
            "n": n,
            "spearman": spearmanr(feature_sims, param_sims),
            "pearson": pearsonr(feature_sims, param_sims),
            "mean_feature_similarity": sum(feature_sims) / n,
            "mean_parameter_similarity": sum(param_sims) / n,
        }

    return {
        "vector": {
            "all": summarize(vec_feature_sims_all, vec_param_sims_all),
            "non_stationary_pairs": summarize(vec_feature_sims_ns, vec_param_sims_ns),
        },
        "trr": {
            "all": summarize(trr_feature_sims_all, trr_param_sims_all),
            "non_stationary_pairs": summarize(trr_feature_sims_ns, trr_param_sims_ns),
        },
    }


def main() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out = compute_feature_parameter_alignment(repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
