#!/usr/bin/env python3

"""
Latency profiling for Audio-Agent (IEEE TMM Major Revision).

This script measures per-query latency breakdown (median / p95) for:
- Retrieval (Text-only / TRR-only / Fusion)
- Optional LLM step (cache-first; network only with an explicit flag)
- Deterministic projection

Design goals:
- Reproducible by default: no network calls.
- Produces audit artifacts: JSON + Markdown summary tables.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.dataset_loader import load_and_merge_data

# Split definition must stay consistent with Protocol-A/B/C.
from Experiments.AblationStudies.direct_retrieval_comparison import is_test_sample_name as is_test_sample  # noqa: E402

# Reuse Protocol-B utilities for projection + (optional) LLM-cache/network call.
from Experiments.AblationStudies.llm_retrieval_comparison import (  # noqa: E402
    compute_param_ranges,
    copy_params_with_onoff,
    predict_onoff_with_llm_cached,
    project_params,
)


PROTOCOL = "Latency"
MS = 1000.0


def _utc_now() -> str:
    # Use timezone-aware UTC timestamps (avoids deprecated utcnow()).
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _try_cmd(cmd: List[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace").strip()
        return out
    except Exception:
        return ""


def _git_sha() -> str:
    sha = _try_cmd(["git", "rev-parse", "HEAD"])
    return sha or "unknown"


def _env_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
    }

    # Optional GPU info (best-effort)
    try:
        import torch  # type: ignore

        info["torch"] = getattr(torch, "__version__", "unknown")
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
        else:
            info["cuda_available"] = False
    except Exception:
        pass

    return info


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
    v = item.get("Vectors")
    if isinstance(v, dict) and v.get("TRR"):
        try:
            arr = np.asarray(v["TRR"], dtype=np.float64).reshape(-1)
            if arr.size > 0:
                return arr
        except Exception:
            pass
    audio_path = item.get("AudioPath")
    if audio_path:
        cache_path = str(audio_path) + ".trr.npy"
        if os.path.exists(cache_path):
            try:
                return np.load(cache_path).astype(np.float64).reshape(-1)
            except Exception:
                pass
    return None


def _minmax(x: np.ndarray) -> np.ndarray:
    lo = float(np.min(x))
    hi = float(np.max(x))
    if hi - lo < 1e-12:
        return np.zeros_like(x, dtype=np.float64)
    return (x - lo) / (hi - lo)


def _entropy_from_topk(scores: np.ndarray) -> float:
    s = scores.astype(np.float64)
    s = s - np.max(s)
    p = np.exp(s)
    p = p / (np.sum(p) + 1e-12)
    return float(-np.sum(p * np.log(p + 1e-12)))


def _entropy_weights(text_topk: np.ndarray, audio_topk: np.ndarray, *, beta: float) -> Dict[str, float]:
    top_k = int(text_topk.shape[0])
    if top_k <= 1:
        return {"w_text": 0.5, "w_audio": 0.5, "u_text_norm": 0.0, "u_audio_norm": 0.0}
    u_text = _entropy_from_topk(text_topk)
    u_audio = _entropy_from_topk(audio_topk)
    u_max = float(np.log(top_k))
    u_text_norm = float(u_text / (u_max + 1e-12))
    u_audio_norm = float(u_audio / (u_max + 1e-12))
    w_text = float(np.exp(-float(beta) * u_text_norm))
    w_audio = float(np.exp(-float(beta) * u_audio_norm))
    z = w_text + w_audio
    w_text = w_text / (z + 1e-12)
    w_audio = w_audio / (z + 1e-12)
    return {"w_text": w_text, "w_audio": w_audio, "u_text_norm": u_text_norm, "u_audio_norm": u_audio_norm}


@dataclass(frozen=True)
class PerQueryLatency:
    protocol: str
    method: str
    llm_mode: str
    allow_network_llm: bool
    query_idx: int
    query_name: str
    n_kb: int
    trr_dim: int
    llm_cache_hit: bool
    llm_network_attempted: bool
    llm_success: bool

    # Timings (ms)
    t_text_score_ms: float
    t_audio_score_ms: float
    t_fusion_ms: float
    t_retrieve_ms: float
    t_llm_cache_ms: float
    t_llm_network_ms: float
    t_llm_total_ms: float
    t_projection_ms: float
    t_end_to_end_ms: float


def _pct(x: np.ndarray, q: float) -> float:
    return float(np.quantile(x, q)) if x.size else float("nan")


def _summarize_ms(xs: Sequence[float]) -> Dict[str, float]:
    arr = np.asarray(list(xs), dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"n": 0.0, "median_ms": float("nan"), "p95_ms": float("nan")}
    return {"n": float(arr.size), "median_ms": float(np.median(arr)), "p95_ms": _pct(arr, 0.95)}


def _as_md_table(rows: List[Tuple[str, Dict[str, float]]]) -> str:
    lines = []
    lines.append("| Component | n | median (ms) | p95 (ms) |")
    lines.append("| --- | ---: | ---: | ---: |")
    for name, s in rows:
        n = int(s.get("n", 0.0))
        med = s.get("median_ms", float("nan"))
        p95 = s.get("p95_ms", float("nan"))
        lines.append(f"| {name} | {n} | {med:.3f} | {p95:.3f} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile per-query latency (median/p95) for Audio-Agent experiments.")
    ap.add_argument("--method", choices=["text", "trr", "fusion"], default="fusion", help="Retrieval method to profile.")
    ap.add_argument("--top_k", type=int, default=5, help="Top-K used for entropy computation (fusion only).")
    ap.add_argument("--beta", type=float, default=2.0, help="Entropy-conditioning beta (fusion only).")
    ap.add_argument("--max_queries", type=int, default=211, help="Maximum number of held-out queries to profile.")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for selecting queries.")
    ap.add_argument("--warmup", type=int, default=5, help="Warmup iterations (not recorded).")
    ap.add_argument("--repeats", type=int, default=1, help="Repeats per query (recorded).")

    ap.add_argument(
        "--llm_mode",
        choices=["none", "cache", "network"],
        default="none",
        help="LLM timing mode. 'cache' is offline (no network). 'network' requires explicit allow flag + API key.",
    )
    ap.add_argument(
        "--llm_cache_dir",
        type=str,
        default=str(Path("Experiments") / "llm_cache" / "protocolB_onoff"),
        help="LLM cache directory (JSON). Used in llm_mode=cache/network.",
    )
    ap.add_argument("--allow_network_llm", action="store_true", help="Allow live LLM calls on cache miss (disabled by default).")
    ap.add_argument("--with_fewshot", action="store_true", help="Use few-shot prompt when calling LLM (default: off).")

    ap.add_argument("--out_json", type=str, default=str(Path("Experiments") / "latency" / "latency_report.json"))
    ap.add_argument("--out_md", type=str, default=str(Path("Experiments") / "latency" / "latency_report.md"))

    args = ap.parse_args()

    started = _utc_now()
    rng = np.random.default_rng(int(args.seed))

    dataset = load_and_merge_data()
    test_indices = [i for i, it in enumerate(dataset) if is_test_sample(str(it.get("SongName") or ""))]
    kb_indices = [i for i in range(len(dataset)) if i not in set(test_indices)]
    test_items = [dataset[i] for i in test_indices]
    kb_items = [dataset[i] for i in kb_indices]

    n_total = int(len(dataset))
    n_test = int(len(test_items))
    n_kb = int(len(kb_items))

    # Precompute structures (not included in per-query timing).
    kb_doc_tokens, idf = _build_text_index(kb_items)

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
    kb_trr_unit = kb_trr_arr / (np.linalg.norm(kb_trr_arr, axis=1, keepdims=True) + 1e-12)

    # Projection ranges: from KB only (deterministic).
    ranges = compute_param_ranges(kb_items)

    # Query selection.
    max_q = int(min(max(1, int(args.max_queries)), n_test))
    q_indices = rng.choice(np.arange(n_test), size=max_q, replace=False)
    selected = [test_items[int(i)] for i in q_indices]

    # Warmup (single representative query).
    if selected and int(args.warmup) > 0:
        q0 = selected[0]
        q_text = _build_text(q0)
        q_trr = _load_trr_vector(q0)
        if q_trr is None:
            q_trr = np.zeros(int(trr_dim), dtype=np.float64)
        q_trr = q_trr.astype(np.float64).reshape(-1)
        q_trr = q_trr / (np.linalg.norm(q_trr) + 1e-12)
        for _ in range(int(args.warmup)):
            _ = np.asarray([_score_text_query(q_text, doc, idf) for doc in kb_doc_tokens], dtype=np.float64)
            _ = kb_trr_unit @ q_trr

    llm_cache_dir = Path(args.llm_cache_dir)

    rows: List[PerQueryLatency] = []
    allow_network_llm = bool(args.allow_network_llm) if str(args.llm_mode) == "network" else False

    for q_pos, q_item in enumerate(selected, 1):
        q_name = str(q_item.get("SongName") or f"query#{q_pos}")
        q_text = _build_text(q_item)
        q_style = " ".join(q_item.get("Style", []) or [])
        q_trr = _load_trr_vector(q_item)
        if q_trr is None or int(q_trr.shape[0]) != int(trr_dim):
            q_trr = np.zeros(int(trr_dim), dtype=np.float64)
        q_trr = q_trr.astype(np.float64).reshape(-1)
        q_trr = q_trr / (np.linalg.norm(q_trr) + 1e-12)

        for rep in range(int(max(1, int(args.repeats)))):
            t_start = time.perf_counter()

            t0 = time.perf_counter()
            text_scores = np.asarray([_score_text_query(q_text, doc, idf) for doc in kb_doc_tokens], dtype=np.float64)
            t1 = time.perf_counter()

            audio_scores = (kb_trr_unit @ q_trr) if kb_trr_unit.size else np.zeros(n_kb, dtype=np.float64)
            t2 = time.perf_counter()

            # Select retrieved item.
            if str(args.method) == "text":
                best_pos = int(np.argmax(text_scores)) if text_scores.size else 0
                t3 = time.perf_counter()
                t_fusion = 0.0
            elif str(args.method) == "trr":
                best_pos = int(np.argmax(audio_scores)) if audio_scores.size else 0
                t3 = time.perf_counter()
                t_fusion = 0.0
            else:
                k_eff = int(min(int(args.top_k), n_kb))
                text_topk = np.sort(text_scores)[-k_eff:] if k_eff > 0 else np.zeros(1)
                audio_topk = np.sort(audio_scores)[-k_eff:] if k_eff > 0 else np.zeros(1)
                w = _entropy_weights(text_topk, audio_topk, beta=float(args.beta))
                fused = w["w_text"] * _minmax(text_scores) + w["w_audio"] * _minmax(audio_scores)
                best_pos = int(np.argmax(fused)) if fused.size else 0
                t3 = time.perf_counter()
                t_fusion = (t3 - t2) * MS

            retrieved_item = kb_items[int(best_pos)]
            retrieved_params = retrieved_item.get("Parameters") or {}

            # Optional LLM step (cache-first).
            llm_cache_hit = False
            llm_network_attempted = False
            llm_success = False
            onoff = None

            t_llm_cache_ms = 0.0
            t_llm_network_ms = 0.0
            if str(args.llm_mode) != "none":
                # 1) Cache-only attempt (always, offline).
                t0_cache = time.perf_counter()
                cache_onoff = predict_onoff_with_llm_cached(
                    q_style,
                    q_name,
                    cache_dir=llm_cache_dir,
                    allow_network=False,
                    with_fewshot=bool(args.with_fewshot),
                )
                t_llm_cache_ms = (time.perf_counter() - t0_cache) * MS
                llm_cache_hit = cache_onoff is not None
                onoff = cache_onoff

                if onoff is None and str(args.llm_mode) == "network":
                    llm_network_attempted = bool(allow_network_llm)
                    if llm_network_attempted:
                        t0_net = time.perf_counter()
                        onoff = predict_onoff_with_llm_cached(
                            q_style,
                            q_name,
                            cache_dir=llm_cache_dir,
                            allow_network=True,
                            with_fewshot=bool(args.with_fewshot),
                        )
                        t_llm_network_ms = (time.perf_counter() - t0_net) * MS

                llm_success = onoff is not None

            pred_params = retrieved_params
            if isinstance(onoff, dict) and onoff:
                try:
                    pred_params = copy_params_with_onoff(retrieved_params, onoff)
                except Exception:
                    pred_params = retrieved_params

            # Deterministic projection.
            t_proj0 = time.perf_counter()
            try:
                _ = project_params(pred_params, ranges)
            except Exception:
                pass
            t_proj1 = time.perf_counter()

            t_end = time.perf_counter()

            row = PerQueryLatency(
                protocol=PROTOCOL,
                method=str(args.method),
                llm_mode=str(args.llm_mode),
                allow_network_llm=bool(allow_network_llm),
                query_idx=int(test_indices[int(q_indices[q_pos - 1])]),
                query_name=str(q_name),
                n_kb=int(n_kb),
                trr_dim=int(trr_dim),
                llm_cache_hit=bool(llm_cache_hit),
                llm_network_attempted=bool(llm_network_attempted),
                llm_success=bool(llm_success),
                t_text_score_ms=(t1 - t0) * MS,
                t_audio_score_ms=(t2 - t1) * MS,
                t_fusion_ms=float(t_fusion),
                t_retrieve_ms=(t3 - t0) * MS,
                t_llm_cache_ms=float(t_llm_cache_ms),
                t_llm_network_ms=float(t_llm_network_ms),
                t_llm_total_ms=float(t_llm_cache_ms + t_llm_network_ms),
                t_projection_ms=(t_proj1 - t_proj0) * MS,
                t_end_to_end_ms=(t_end - t_start) * MS,
            )
            rows.append(row)

        if q_pos % 50 == 0 or q_pos == len(selected):
            print(f"[Latency] processed {q_pos}/{len(selected)} queries (repeats={int(args.repeats)})")

    finished = _utc_now()

    # Summaries
    t_text = [r.t_text_score_ms for r in rows]
    t_audio = [r.t_audio_score_ms for r in rows]
    t_fusion = [r.t_fusion_ms for r in rows if str(args.method) == "fusion"]
    t_retrieve = [r.t_retrieve_ms for r in rows]
    t_proj = [r.t_projection_ms for r in rows]
    t_llm = [r.t_llm_total_ms for r in rows if str(args.llm_mode) != "none"]
    t_e2e = [r.t_end_to_end_ms for r in rows]

    summary = {
        "meta": {
            "protocol": PROTOCOL,
            "git_sha": _git_sha(),
            "started_at": started,
            "finished_at": finished,
            "env": _env_info(),
            "args": vars(args),
        },
        "dataset": {"n_total": n_total, "n_test": n_test, "n_kb": n_kb, "trr_dim": int(trr_dim)},
        "summary_ms": {
            "text_score": _summarize_ms(t_text),
            "audio_score": _summarize_ms(t_audio),
            "fusion": _summarize_ms(t_fusion) if str(args.method) == "fusion" else {"n": 0.0, "median_ms": float("nan"), "p95_ms": float("nan")},
            "retrieve_total": _summarize_ms(t_retrieve),
            "llm": _summarize_ms(t_llm) if str(args.llm_mode) != "none" else {"n": 0.0, "median_ms": float("nan"), "p95_ms": float("nan")},
            "projection": _summarize_ms(t_proj),
            "end_to_end": _summarize_ms(t_e2e),
        },
        "per_query": [asdict(r) for r in rows],
    }

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines: List[str] = []
    md_lines.append("# Latency Profiling Report")
    md_lines.append("")
    md_lines.append(f"- Git SHA: `{summary['meta']['git_sha']}`")
    md_lines.append(f"- Started: `{started}`")
    md_lines.append(f"- Finished: `{finished}`")
    md_lines.append(f"- Dataset: N_total={n_total}, N_test={n_test}, N_kb={n_kb}")
    md_lines.append(f"- Retrieval method: `{args.method}`")
    md_lines.append(f"- LLM mode: `{args.llm_mode}` (allow_network_llm={bool(allow_network_llm)})")
    md_lines.append("")
    md_lines.append("## Latency Summary (per-query, ms)")
    md_lines.append("")
    md_lines.append(
        _as_md_table(
            [
                ("Text scoring", summary["summary_ms"]["text_score"]),
                ("Audio scoring (TRR)", summary["summary_ms"]["audio_score"]),
                ("Fusion (weights+argmax)", summary["summary_ms"]["fusion"]),
                ("Retrieval total", summary["summary_ms"]["retrieve_total"]),
                ("LLM step", summary["summary_ms"]["llm"]),
                ("Projection", summary["summary_ms"]["projection"]),
                ("End-to-end", summary["summary_ms"]["end_to_end"]),
            ]
        )
    )
    md_lines.append("")
    md_lines.append("## Notes")
    md_lines.append("")
    md_lines.append("- By default, this script is offline and will not perform network LLM calls.")
    md_lines.append("- For measuring live API latency, run with `--llm_mode network --allow_network_llm` and configure API keys.")
    md_lines.append("- For cache-only LLM latency, first populate the cache once (network enabled), then rerun with `--llm_mode cache`.")

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"[Latency] wrote JSON: {out_json}")
    print(f"[Latency] wrote MD:   {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
