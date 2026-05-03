from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


TOPK_FIELDS = [
    "coverage",
    "pnr_at_1",
    "pnr_at_3",
    "pnr_at_5",
    "pnr_at_k",
    "top1_norm_l2",
    "top1_acc_at_0_1",
    "top1_recall",
    "top1_cosine",
    "top1_module",
]

EPR_FIELDS = [
    "norm_l2",
    "acc_at_0_1",
    "recall",
    "cosine",
    "module",
    "edit_cost",
    "provenance_max_weight",
    "provenance_entropy_norm",
    "provenance_effective_exemplars",
]

MODULE_FIELDS = [
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
]

UNSUPPORTED_CLAIMS = [
    "PC-TRR 训练收益未验证",
    "Temporal Pyramid TRR 未验证",
    "Log-Covariance/Riemannian TRR 未验证",
    "Analysis-by-synthesis reranking 未验证",
    "Protocol-C adaptive fusion 不能作为主贡献",
]


def _round(value: float) -> float:
    return round(float(value), 10)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _ok_rows(rows: Iterable[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [row for row in rows if row.get("status", "ok") == "ok"]


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required input JSON does not exist: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def mean_by_method(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("status", "ok") != "ok":
            continue
        method = row.get("method")
        if method:
            grouped[str(method)].append(row)

    out: Dict[str, Dict[str, float]] = {}
    for method in sorted(grouped):
        method_rows = grouped[method]
        stats: Dict[str, float] = {"n": len(method_rows)}
        for field in fields:
            values = [float(row[field]) for row in method_rows if _is_number(row.get(field))]
            stats[f"{field}_n"] = len(values)
            if values:
                stats[field] = _round(sum(values) / len(values))
        out[method] = stats
    return out


def recommendation_from_metrics(
    trr_norm_l2: float,
    epr_norm_l2: float,
    mlp_norm_l2: float,
    epr_provenance: float,
) -> str:
    if epr_norm_l2 < mlp_norm_l2:
        if epr_norm_l2 < trr_norm_l2:
            numeric_clause = "it improves the retrieval-side Norm.L2"
        else:
            numeric_clause = "it beats the direct-regression boundary but does not improve retrieval-side Norm.L2"
        return (
            "EPR should be reported as the primary hybrid result: "
            f"{numeric_clause} while preserving executable exemplar provenance "
            f"(effective exemplars {epr_provenance:.4f})."
        )
    return (
        "MLP+RangeProjection remains the direct-regression numeric boundary on "
        "Norm.L2. EPR should be framed as an executable soft-blended projection "
        "with provenance rather than as a superior direct regressor "
        f"(effective exemplars {epr_provenance:.4f})."
    )


def _best_method(stats: Mapping[str, Mapping[str, float]], field: str, *, lower_is_better: bool) -> str:
    candidates = [(method, values[field]) for method, values in stats.items() if field in values]
    if not candidates:
        return ""
    return sorted(candidates, key=lambda item: item[1], reverse=not lower_is_better)[0][0]


def _delta_stats(stats: Mapping[str, Mapping[str, float]]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for method, values in stats.items():
        method_delta: Dict[str, float] = {}
        pairs = [
            ("norm_l2_delta", "reranked_norm_l2", "original_norm_l2"),
            ("acc_at_0_1_delta", "reranked_acc_at_0_1", "original_acc_at_0_1"),
            ("recall_delta", "reranked_recall", "original_recall"),
            ("cosine_delta", "reranked_cosine", "original_cosine"),
            ("module_delta", "reranked_module", "original_module"),
        ]
        for name, after, before in pairs:
            if after in values and before in values:
                method_delta[name] = _round(values[after] - values[before])
        out[method] = method_delta
    return out


def _change_rate_by_method(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        method = row.get("method")
        if method:
            grouped[str(method)].append(row)
    return {
        method: _round(sum(1 for row in method_rows if row.get("changed")) / len(method_rows))
        for method, method_rows in sorted(grouped.items())
        if method_rows
    }


def _projected_mlp_metrics(mlp: Mapping[str, Any]) -> Dict[str, float]:
    projected = mlp.get("projected_metrics")
    if not isinstance(projected, Mapping):
        raise ValueError("MLP JSON must contain projected_metrics")
    required = ["l2_norm", "acc_at_01", "recall", "cosine", "module"]
    missing = [field for field in required if field not in projected]
    if missing:
        raise ValueError(f"MLP projected_metrics missing required fields: {', '.join(missing)}")
    return {
        "norm_l2": _round(float(projected["l2_norm"])),
        "acc_at_0_1": _round(float(projected["acc_at_01"])),
        "recall": _round(float(projected["recall"])),
        "cosine": _round(float(projected["cosine"])),
        "module": _round(float(projected["module"])),
    }


def _raw_mlp_metrics(mlp: Mapping[str, Any]) -> Dict[str, float]:
    raw = mlp.get("metrics")
    if not isinstance(raw, Mapping):
        return {}
    aliases = {
        "l2_norm": "norm_l2",
        "acc_at_01": "acc_at_0_1",
        "recall": "recall",
        "cosine": "cosine",
        "module": "module",
    }
    return {
        out_key: _round(float(raw[in_key]))
        for in_key, out_key in aliases.items()
        if _is_number(raw.get(in_key))
    }


def _projection_delta(raw: Mapping[str, float], projected: Mapping[str, float]) -> Dict[str, float]:
    return {
        field: _round(projected[field] - raw[field])
        for field in ["norm_l2", "acc_at_0_1", "recall", "cosine", "module"]
        if field in raw and field in projected
    }


def build_summary(
    topk_rows: Sequence[Mapping[str, Any]],
    epr_rows: Sequence[Mapping[str, Any]],
    module_rows: Sequence[Mapping[str, Any]],
    mlp_result: Mapping[str, Any],
) -> Dict[str, Any]:
    topk_ok = _ok_rows(topk_rows)
    epr_ok = _ok_rows(epr_rows)
    module_ok = _ok_rows(module_rows)

    topk_by_method = mean_by_method(topk_ok, TOPK_FIELDS)
    epr_by_method = mean_by_method(epr_ok, EPR_FIELDS)
    module_by_method = mean_by_method(module_ok, MODULE_FIELDS)
    module_delta = _delta_stats(module_by_method)
    for method, values in module_delta.items():
        if method in module_by_method and "n" in module_by_method[method]:
            values["n"] = module_by_method[method]["n"]
    mlp_raw = _raw_mlp_metrics(mlp_result)
    mlp_projected = _projected_mlp_metrics(mlp_result)

    best_topk_method = _best_method(topk_by_method, "pnr_at_5", lower_is_better=False)
    best_epr_method = _best_method(epr_by_method, "norm_l2", lower_is_better=True)
    trr_norm_l2 = topk_by_method.get("TRR", {}).get("top1_norm_l2")
    if trr_norm_l2 is None and topk_by_method:
        trr_norm_l2 = next(iter(topk_by_method.values())).get("top1_norm_l2", 0.0)
    epr_norm_l2 = epr_by_method.get(best_epr_method, {}).get("norm_l2", 0.0)
    epr_provenance = epr_by_method.get(best_epr_method, {}).get("provenance_effective_exemplars", 0.0)

    recommendation_text = recommendation_from_metrics(
        trr_norm_l2=float(trr_norm_l2 or 0.0),
        epr_norm_l2=float(epr_norm_l2),
        mlp_norm_l2=float(mlp_projected["norm_l2"]),
        epr_provenance=float(epr_provenance),
    )
    numeric_winner = "EPR" if epr_norm_l2 < mlp_projected["norm_l2"] else "MLP+RangeProjection"

    supported_claims = [
        "Top-K retrieval can be evaluated as parameter-neighborhood recall on the current Protocol-A E8 outputs.",
        "EPR is an executable soft-blended projection with retained exemplar provenance over retrieved candidates.",
        "MLP+RangeProjection remains the direct-regression boundary row, but current E8 outputs must compare it against EPR rather than assuming it is numerically stronger.",
        "Module-aware reranking is diagnostic on these outputs and must not be described as a gain unless Norm.L2 delta is negative and alignment-score deltas are non-negative in future runs.",
    ]

    return {
        "topk": {
            "n_rows": len(topk_ok),
            "by_method": topk_by_method,
            "best_pnr_at_5_method": best_topk_method,
            "interpretation": "parameter_neighborhood_recall",
        },
        "epr": {
            "n_rows": len(epr_ok),
            "by_method": epr_by_method,
            "best_norm_l2_method": best_epr_method,
            "interpretation": "executable_soft_blended_projection_with_provenance",
        },
        "module": {
            "n_rows": len(module_ok),
            "by_method": module_by_method,
            "delta_by_method": module_delta,
            "change_rate_by_method": _change_rate_by_method(module_ok),
            "interpretation": "diagnostic_negative",
        },
        "mlp": {
            "method": str(mlp_result.get("projected_method", "MLP-Regressor+RangeProjection")),
            "raw_metrics": mlp_raw,
            "projected_metrics": mlp_projected,
            "projection_delta": _projection_delta(mlp_raw, mlp_projected),
            "interpretation": "direct_regression_numeric_boundary",
        },
        "recommendation": {
            "numeric_winner": numeric_winner,
            "text": recommendation_text,
        },
        "claims": {
            "supported": supported_claims,
            "not_supported": UNSUPPORTED_CLAIMS,
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metrics_table(stats: Mapping[str, Mapping[str, float]], fields: Sequence[str]) -> str:
    if not stats:
        return "No valid rows were available.\n"
    lines = ["| Method | n | " + " | ".join(fields) + " |"]
    lines.append("| --- | ---: | " + " | ".join(["---:"] * len(fields)) + " |")
    for method, values in stats.items():
        row = [method, _fmt(values.get("n"))]
        row.extend(_fmt(values.get(field)) for field in fields)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def render_markdown(summary: Mapping[str, Any]) -> str:
    topk = summary["topk"]
    epr = summary["epr"]
    module = summary["module"]
    mlp = summary["mlp"]
    recommendation = summary["recommendation"]
    claims = summary["claims"]

    topk_fields = ["pnr_at_1", "pnr_at_3", "pnr_at_5", "top1_norm_l2", "top1_acc_at_0_1", "top1_recall"]
    epr_fields = [
        "norm_l2",
        "acc_at_0_1",
        "recall",
        "cosine",
        "module",
        "provenance_effective_exemplars",
        "provenance_max_weight",
    ]
    module_fields = ["norm_l2_delta", "acc_at_0_1_delta", "recall_delta", "cosine_delta", "module_delta"]

    lines = [
        "# E8 Executable Neighborhood Retrieval Summary",
        "",
        "## Scope",
        "",
        "This summary aggregates E8 executable-neighborhood evidence from Top-K retrieval, EPR soft blending, module-aware reranking, and the existing E2 MLP boundary. It is a paper-facing evidence boundary document only; it does not modify manuscript text.",
        "",
        "## Top-K Parameter Neighborhood Recall",
        "",
        _metrics_table(topk["by_method"], topk_fields).rstrip(),
        "",
        f"Best PNR@5 method: `{topk.get('best_pnr_at_5_method') or 'n/a'}`. These numbers support retrieval as an executable neighborhood surface, not as proof that every downstream parameter value is numerically superior to direct regression.",
        "",
        "## Exemplar-Preserving Parameter Projection",
        "",
        _metrics_table(epr["by_method"], epr_fields).rstrip(),
        "",
        f"Best EPR method by Norm.L2: `{epr.get('best_norm_l2_method') or 'n/a'}`. EPR is executable soft-blended projection over retrieved exemplars and retains provenance through effective-exemplar and max-weight statistics.",
        "",
        "## Module-Aware Reranking",
        "",
        _metrics_table(module["delta_by_method"], module_fields).rstrip(),
        "",
        "Module-aware reranking is treated as a diagnostic negative result in this run. It must not be described as a gain unless future outputs show lower Norm.L2 and non-degraded alignment scores under the same oracle-free constraint.",
        "",
        "## MLP Boundary Interpretation",
        "",
        "| Method | Norm.L2 | Acc@0.1 | Recall | Cosine | Module |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    if mlp.get("raw_metrics"):
        lines.append(
            f"| MLP-Regressor(raw) | {_fmt(mlp['raw_metrics'].get('norm_l2'))} | "
            f"{_fmt(mlp['raw_metrics'].get('acc_at_0_1'))} | "
            f"{_fmt(mlp['raw_metrics'].get('recall'))} | "
            f"{_fmt(mlp['raw_metrics'].get('cosine'))} | "
            f"{_fmt(mlp['raw_metrics'].get('module'))} |"
        )
    lines.extend(
        [
        (
            f"| {mlp['method']} | {_fmt(mlp['projected_metrics']['norm_l2'])} | "
            f"{_fmt(mlp['projected_metrics']['acc_at_0_1'])} | "
            f"{_fmt(mlp['projected_metrics']['recall'])} | "
            f"{_fmt(mlp['projected_metrics']['cosine'])} | "
            f"{_fmt(mlp['projected_metrics']['module'])} |"
        ),
        "",
        "Range projection is the relevant MLP boundary row; its deltas relative to raw MLP are preserved in `e8_summary.json`.",
        "",
        recommendation["text"],
        "",
        "## Claims Supported",
        "",
        ]
    )
    lines.extend(f"- {claim}" for claim in claims["supported"])
    lines.extend(["", "## Claims Not Supported", ""])
    lines.extend(f"- {claim}" for claim in claims["not_supported"])
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize E8 executable neighborhood retrieval outputs.")
    parser.add_argument("--topk-json", required=True, type=Path)
    parser.add_argument("--epr-json", required=True, type=Path)
    parser.add_argument("--module-json", required=True, type=Path)
    parser.add_argument("--mlp-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_summary(
        _load_json(args.topk_json),
        _load_json(args.epr_json),
        _load_json(args.module_json),
        _load_json(args.mlp_json),
    )
    json_path = args.output_dir / "e8_summary.json"
    md_path = args.output_dir / "e8_summary.md"
    _write_json(json_path, summary)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
