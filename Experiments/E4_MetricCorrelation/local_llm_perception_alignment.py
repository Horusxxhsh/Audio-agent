"""Diagnostic perception-alignment analysis for the TMM revision.

This script intentionally keeps the analysis narrow. The listening-test labels
do not provide one-to-one Protocol-A query ids, so we only evaluate Trial-1
style labels that can be mapped to Protocol-A query names by an explicit alias
table. A local OpenAI-compatible vLLM server is queried for text-side diagnostic
scores on the same labels. The output is suitable for a supplementary
diagnostic, not for a primary evidence claim.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


STYLE_ALIASES = {
    "Ambient Guitar": ["Ambient Guitar"],
    "Phase": ["Phase", "Phased"],
    "Jazz Clean": ["Jazz", "Clean"],
    "Blues Solo": ["Blues", "Solo"],
    "Flanger": ["Flanger"],
    "Modern Metal": ["Modern Metal", "Metal"],
    "Chorus": ["Chorus"],
}


def call_chat(base_url: str, model: str, stimulus: str, timeout: int = 120) -> dict[str, Any]:
    prompt = (
        "/no_think\n"
        "You are scoring whether a retrieved editable guitar-effect preset label "
        "is likely to be perceptually clear and recognizable to listeners. "
        "Return strict JSON only with keys score and rationale. "
        "score must be a number from 0 to 100. "
        f"Preset label: {stimulus!r}."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 2048,
        "guided_json": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "rationale": {"type": "string"},
            },
            "required": ["score", "rationale"],
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to call local vLLM at {base_url}: {exc}") from exc

    content = body["choices"][0]["message"]["content"]
    parse_content = content.split("</think>")[-1].strip()
    match = re.search(r"\{.*\}", parse_content, flags=re.S)
    if not match:
        score = extract_score(parse_content)
        return {"score": score, "rationale": content.strip(), "raw": content}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"score": np.nan, "rationale": content.strip(), "raw": content}
    return {
        "score": float(parsed.get("score", np.nan)),
        "rationale": str(parsed.get("rationale", "")),
        "raw": content,
    }


def extract_score(text: str) -> float:
    """Extract a fallback scalar score from non-JSON local model output."""
    patterns = [
        r"(?:final decision|final answer|score)\D{0,20}([0-9]{1,3}(?:\.[0-9]+)?)",
        r"\b([0-9]{1,3}(?:\.[0-9]+)?)\b",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.I)
        values = [float(x) for x in matches if 0.0 <= float(x) <= 100.0]
        if values:
            return values[-1]
    return float("nan")


def match_protocol_rows(protocol_df: pd.DataFrame, stimulus: str) -> pd.DataFrame:
    aliases = STYLE_ALIASES[stimulus]
    mask = pd.Series(False, index=protocol_df.index)
    names = protocol_df["query_name"].astype(str)
    for alias in aliases:
        mask = mask | names.str.contains(alias, case=False, regex=False)
    return protocol_df[mask]


def corr(x: list[float], y: list[float]) -> dict[str, float]:
    arr_x = np.asarray(x, dtype=float)
    arr_y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(arr_x) | np.isnan(arr_y))
    arr_x = arr_x[mask]
    arr_y = arr_y[mask]
    if len(arr_x) < 3:
        return {
            "n": int(len(arr_x)),
            "spearman_r": float("nan"),
            "spearman_p": float("nan"),
            "pearson_r": float("nan"),
            "pearson_p": float("nan"),
        }
    sp = stats.spearmanr(arr_x, arr_y)
    pe = stats.pearsonr(arr_x, arr_y)
    return {
        "n": int(len(arr_x)),
        "spearman_r": float(sp.statistic),
        "spearman_p": float(sp.pvalue),
        "pearson_r": float(pe.statistic),
        "pearson_p": float(pe.pvalue),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mushra-csv", default="Experiments/mushura/mushra.csv")
    parser.add_argument(
        "--protocol-csv",
        default="Experiments/AblationStudies/protocolA_audio_grouped_per_query_metrics.csv",
    )
    parser.add_argument("--output-dir", default="Experiments/E4_MetricCorrelation/outputs/local_llm_alignment")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="qwen3.5-9b")
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mushra = pd.read_csv(args.mushra_csv)
    mushra = mushra[mushra["trial_id"].astype(str).eq("trial1")].copy()
    mushra["rating_score"] = pd.to_numeric(mushra["rating_score"], errors="coerce")
    human = (
        mushra[mushra["rating_stimulus"].isin(STYLE_ALIASES)]
        .groupby("rating_stimulus")["rating_score"]
        .agg(["mean", "median", "std", "count"])
        .reset_index()
        .rename(columns={"rating_stimulus": "stimulus", "mean": "human_mean", "median": "human_median"})
    )

    protocol = pd.read_csv(args.protocol_csv)
    trr = protocol[protocol["method"].eq("TRR")].copy()

    rows: list[dict[str, Any]] = []
    for _, hrow in human.iterrows():
        stimulus = str(hrow["stimulus"])
        matches = match_protocol_rows(trr, stimulus)
        llm_result = {"score": np.nan, "rationale": "", "raw": ""}
        if not args.skip_llm:
            llm_result = call_chat(args.base_url, args.model, stimulus)
        rows.append(
            {
                "stimulus": stimulus,
                "human_mean": float(hrow["human_mean"]),
                "human_median": float(hrow["human_median"]),
                "human_std": float(hrow["std"]),
                "human_n": int(hrow["count"]),
                "matched_queries": int(matches["query_name"].nunique()),
                "matched_rows": int(len(matches)),
                "trr_l2_mean": float(matches["l2"].mean()) if len(matches) else np.nan,
                "trr_acc_mean": float(matches["acc@0.1"].mean()) if len(matches) else np.nan,
                "trr_recall_mean": float(matches["recall"].mean()) if len(matches) else np.nan,
                "trr_cosine_mean": float(matches["cosine"].mean()) if len(matches) else np.nan,
                "trr_module_mean": float(matches["module"].mean()) if len(matches) else np.nan,
                "llm_score": float(llm_result["score"]),
                "llm_rationale": llm_result["rationale"],
                "llm_raw": llm_result["raw"],
            }
        )

    result_df = pd.DataFrame(rows)
    result_df.to_csv(out_dir / "local_llm_perception_alignment.csv", index=False)

    correlations = {
        "human_vs_trr_l2": corr(result_df["human_mean"].tolist(), (-result_df["trr_l2_mean"]).tolist()),
        "human_vs_trr_acc": corr(result_df["human_mean"].tolist(), result_df["trr_acc_mean"].tolist()),
        "human_vs_trr_cosine": corr(result_df["human_mean"].tolist(), result_df["trr_cosine_mean"].tolist()),
        "human_vs_llm_score": corr(result_df["human_mean"].tolist(), result_df["llm_score"].tolist()),
        "llm_vs_trr_l2": corr(result_df["llm_score"].tolist(), (-result_df["trr_l2_mean"]).tolist()),
        "llm_vs_trr_acc": corr(result_df["llm_score"].tolist(), result_df["trr_acc_mean"].tolist()),
    }
    summary = {
        "scope": "Trial-1 style-label diagnostic with explicit alias matching; not a primary query-level validation.",
        "mushra_csv": args.mushra_csv,
        "protocol_csv": args.protocol_csv,
        "local_llm": {"base_url": args.base_url, "model": args.model, "skipped": bool(args.skip_llm)},
        "n_stimuli": int(len(result_df)),
        "n_stimuli_with_protocol_match": int(result_df["matched_queries"].gt(0).sum()),
        "correlations": correlations,
    }
    (out_dir / "local_llm_perception_alignment.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Local LLM Perception Alignment Diagnostic",
        "",
        summary["scope"],
        "",
        f"- Local model: `{args.model}` at `{args.base_url}`",
        f"- Stimuli: {summary['n_stimuli']}",
        f"- Stimuli with Protocol-A TRR matches: {summary['n_stimuli_with_protocol_match']}",
        "",
        "## Correlations",
        "",
        "| Pair | n | Spearman r | Spearman p | Pearson r | Pearson p |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, value in correlations.items():
        lines.append(
            f"| {key} | {value['n']} | {value['spearman_r']:.4f} | "
            f"{value['spearman_p']:.4g} | {value['pearson_r']:.4f} | {value['pearson_p']:.4g} |"
        )
    compact_df = result_df.drop(columns=["llm_raw", "llm_rationale"]).copy()
    lines.extend(["", "## Per-Stimulus Rows", "", compact_df.to_markdown(index=False)])
    (out_dir / "local_llm_perception_alignment.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
