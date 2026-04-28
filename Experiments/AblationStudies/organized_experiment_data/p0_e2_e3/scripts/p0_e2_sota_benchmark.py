import argparse
import csv
import hashlib
import json
import math
import os
from typing import Any, Dict, List, Sequence, Tuple

from stats_utils import cohens_d_paired, holm_bonferroni, mean, paired_test, std, win_tie_loss

# Local experiment shared evaluator
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.join(CURRENT_DIR, "..", "common")
sys.path.append(COMMON_DIR)
from evaluate import Evaluator  # noqa: E402


VECTOR_METHODS = {
    "TRR": "TRR",
    "Wav2Vec": "Wav2Vec",
    "FeatureNN": "FeatureNN",
    "CLAP": "CLAP",
    "PaSST": "PaSST",
    "PANNs": "PANNs",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="P0-E2 SOTA baseline benchmark (Protocol-A).")
    p.add_argument("--dataset", default=os.path.join("Experiments", "dataset_full_vectors.json"))
    p.add_argument("--out-dir", default=os.path.join("Experiments", "AblationStudies", "outputs", "p0_e2"))
    p.add_argument("--test-size", type=int, default=204)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--top-k", type=int, default=1)
    return p.parse_args()


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        fx = float(x)
        fy = float(y)
        dot += fx * fy
        na += fx * fx
        nb += fy * fy
    if na <= 0 or nb <= 0:
        return -1.0
    return dot / math.sqrt(na * nb)


def flatten_numeric(params: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten_numeric(v, key))
        elif isinstance(v, (int, float)):
            out[key] = float(v)
    return out


def build_param_ranges(all_items: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}
    for item in all_items:
        flat = flatten_numeric(item.get("Parameters", {}))
        for k, v in flat.items():
            if k not in mins or v < mins[k]:
                mins[k] = v
            if k not in maxs or v > maxs[k]:
                maxs[k] = v
    return {k: (mins[k], maxs[k]) for k in mins.keys()}


def normalized_l2(pred: Dict[str, Any], gt: Dict[str, Any], ranges: Dict[str, Tuple[float, float]]) -> float:
    fp = flatten_numeric(pred)
    fg = flatten_numeric(gt)
    keys = set(fp.keys()) | set(fg.keys())
    if not keys:
        return 0.0
    acc = 0.0
    cnt = 0
    for k in keys:
        p = fp.get(k, 0.0)
        g = fg.get(k, 0.0)
        lo, hi = ranges.get(k, (0.0, 1.0))
        span = hi - lo
        if abs(span) < 1e-12:
            span = 1.0
        d = (p - g) / span
        acc += d * d
        cnt += 1
    return math.sqrt(acc / cnt)


def has_vector(item: Dict[str, Any], key: str) -> bool:
    vec = item.get("Vectors", {}).get(key)
    return isinstance(vec, list) and len(vec) > 0


def retrieve_top1(query: Dict[str, Any], kb: Sequence[Dict[str, Any]], vector_key: str) -> Dict[str, Any]:
    qv = query.get("Vectors", {}).get(vector_key, [])
    if not isinstance(qv, list) or not qv:
        return {}
    best_score = -2.0
    best_item: Dict[str, Any] = {}
    for item in kb:
        iv = item.get("Vectors", {}).get(vector_key, [])
        if not isinstance(iv, list) or not iv:
            continue
        if len(iv) != len(qv):
            continue
        s = cosine(qv, iv)
        if s > best_score:
            best_score = s
            best_item = item
    return best_item


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    args = parse_args()
    ensure_dir(args.out_dir)

    data = load_dataset(args.dataset)
    test_items, kb_items = deterministic_split(data, args.test_size, args.seed)
    evaluator = Evaluator()
    ranges = build_param_ranges(test_items + kb_items)

    available_methods: List[str] = []
    for method_name, vector_key in VECTOR_METHODS.items():
        q_ok = any(has_vector(x, vector_key) for x in test_items)
        k_ok = any(has_vector(x, vector_key) for x in kb_items)
        if q_ok and k_ok:
            available_methods.append(method_name)

    if not available_methods:
        raise RuntimeError("No usable vector methods found in dataset.")

    rows: List[Dict[str, Any]] = []
    by_method: Dict[str, Dict[str, List[float]]] = {}
    for m in available_methods:
        by_method[m] = {
            "l2": [],
            "norm_l2": [],
            "acc": [],
            "recall": [],
            "cosine": [],
            "module": [],
        }

    for q in test_items:
        qname = q.get("SongName", "")
        gt = q.get("Parameters", {})
        for method_name in available_methods:
            vkey = VECTOR_METHODS[method_name]
            top1 = retrieve_top1(q, kb_items, vkey)
            if not top1:
                continue
            pred = top1.get("Parameters", {})
            l2 = evaluator.compute_parameter_distance(pred, gt)
            nl2 = normalized_l2(pred, gt, ranges)
            acc = evaluator.compute_accuracy_tolerance(pred, gt, tolerance=0.1)
            rec = evaluator.compute_parameter_recall(pred, gt, threshold=0.1)
            cos = evaluator.compute_cosine_similarity(pred, gt)
            mod = evaluator.compute_module_consistency(pred, gt, active_threshold=0.1)

            by_method[method_name]["l2"].append(l2)
            by_method[method_name]["norm_l2"].append(nl2)
            by_method[method_name]["acc"].append(acc)
            by_method[method_name]["recall"].append(rec)
            by_method[method_name]["cosine"].append(cos)
            by_method[method_name]["module"].append(mod)

            rows.append({
                "query_song": qname,
                "method": method_name,
                "retrieved_song": top1.get("SongName", ""),
                "l2": l2,
                "norm_l2": nl2,
                "acc@0.1": acc,
                "recall": rec,
                "cosine": cos,
                "module": mod,
            })

    per_query_csv = os.path.join(args.out_dir, "e2_per_query.csv")
    with open(per_query_csv, "w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    summary_rows: List[Dict[str, Any]] = []
    for m in available_methods:
        d = by_method[m]
        summary_rows.append({
            "method": m,
            "n": len(d["l2"]),
            "l2_mean": mean(d["l2"]),
            "l2_std": std(d["l2"]),
            "norm_l2_mean": mean(d["norm_l2"]),
            "norm_l2_std": std(d["norm_l2"]),
            "acc_mean": mean(d["acc"]),
            "recall_mean": mean(d["recall"]),
            "cosine_mean": mean(d["cosine"]),
            "module_mean": mean(d["module"]),
        })
    summary_csv = os.path.join(args.out_dir, "e2_summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        if summary_rows:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

    stats: Dict[str, Any] = {
        "config": {
            "dataset": args.dataset,
            "test_size_requested": args.test_size,
            "seed": args.seed,
            "top_k": args.top_k,
            "test_size_actual": len(test_items),
            "kb_size_actual": len(kb_items),
            "methods": available_methods,
        },
        "pairwise_vs_trr": {},
    }

    if "TRR" in available_methods:
        trr_l2 = by_method["TRR"]["norm_l2"]
        pvals: Dict[str, float] = {}
        pairs: Dict[str, Any] = {}
        for m in available_methods:
            if m == "TRR":
                continue
            baseline = by_method[m]["norm_l2"]
            n = min(len(trr_l2), len(baseline))
            if n == 0:
                continue
            a = trr_l2[:n]
            b = baseline[:n]
            pinfo = paired_test(a, b, lower_better_for_a=True)
            pvals[m] = pinfo["p_value"]
            w, t, l = win_tie_loss(a, b, lower_better=True)
            pairs[m] = {
                "n": n,
                "p_value": pinfo["p_value"],
                "test": pinfo["test"],
                "cohens_d": cohens_d_paired(a, b),
                "trr_win_tie_loss_vs_baseline": {"win": w, "tie": t, "loss": l},
            }
        if pvals:
            holm = holm_bonferroni(pvals, alpha=0.05)
            for m, h in holm.items():
                pairs[m]["holm_threshold"] = h["holm_threshold"]
                pairs[m]["reject_h0"] = bool(h["reject_h0"])
        stats["pairwise_vs_trr"] = pairs

    stats_json = os.path.join(args.out_dir, "e2_stats.json")
    with open(stats_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("E2 done.")
    print(f"- per-query: {per_query_csv}")
    print(f"- summary:   {summary_csv}")
    print(f"- stats:     {stats_json}")


if __name__ == "__main__":
    main()

