from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/paper_summary"


def _load_optional(path: Path) -> object:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: object, digits: int = 4) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "--"


def build_summary(
    unified: Mapping[str, object] | None,
    epr: Mapping[str, object] | None,
    blocker: Mapping[str, object] | None,
    coverage: Mapping[str, object] | None,
    near_duplicate: Mapping[str, object] | None,
    validity: Mapping[str, object] | None,
    sensitivity: object | None,
) -> str:
    lines = ["# E9 TMM Major Revision Evidence Summary", ""]
    if coverage:
        coverage_by_method = coverage.get("method_coverage") or coverage.get("methods") or coverage.get("coverage") or {}
        passt = coverage_by_method.get("PaSST", {}) if isinstance(coverage_by_method, Mapping) else {}
        if isinstance(passt, Mapping):
            ready = passt.get("ready")
            if ready is None:
                ready = passt.get("query_ok") == passt.get("query_total") and passt.get("kb_ok") == passt.get("kb_total")
            lines.extend([
                "## SOTA Vector Preparation",
                "",
                f"PaSST coverage gate: query={passt.get('query_ok')}/{passt.get('query_total')}, KB={passt.get('kb_ok')}/{passt.get('kb_total')}, ready={ready}.",
                "",
            ])
    if blocker:
        lines.extend([
            "## SOTA Vector Preparation",
            "",
            "Status: blocked. Fair Protocol-B claims for the blocked method must not be made until the runtime/vector-generation blockers recorded in the vector-preparation audit are resolved.",
            "",
        ])
    if unified:
        lines.extend(["## Unified Protocol-A Top-1", ""])
        for method, row in sorted(unified.items()):
            if isinstance(row, Mapping):
                lines.append(f"- {method}: n={row.get('n')}, Norm.L2={_fmt(row.get('norm_l2'))}, SwitchF1={_fmt(row.get('switch_f1') or row.get('top1_switch_f1'))}")
        lines.append("")
    if epr:
        lines.extend(["## Protocol-B EPR", ""])
        for method, row in sorted(epr.items()):
            if isinstance(row, Mapping):
                lines.append(f"- {method} EPR-K5: n={row.get('n')}, Norm.L2={_fmt(row.get('norm_l2'))}, Neff={_fmt(row.get('provenance_effective_exemplars'))}")
        lines.append("")
    if near_duplicate:
        rows = near_duplicate.get("near_duplicate_rows", []) if isinstance(near_duplicate, Mapping) else []
        canonical = rows[0] if isinstance(rows, list) and rows else None
        if canonical is None and isinstance(near_duplicate, Mapping):
            canonical = near_duplicate.get("0.000")
        if isinstance(canonical, Mapping):
            kb_size = canonical.get("kb_size")
            trr = canonical.get("TRR")
            if isinstance(trr, Mapping):
                kb_size = trr.get("kb_size")
                trr = trr.get("norm_l2")
            lines.extend([
                "## Unified Near-Duplicate Canonical Row",
                "",
                f"Threshold 0.000 KB={kb_size} TRR Norm.L2={_fmt(trr)}; this row must match the Table III Protocol-A TRR row.",
                "",
            ])
    if validity:
        lines.extend(["## Protocol-B Validity", ""])
        for method, row in sorted(validity.items()):
            if isinstance(row, Mapping):
                lines.append(f"- {method}: validity={_fmt(row.get('validity_rate'))}, repair={_fmt(row.get('repair_rate'))}")
        lines.append("")
    if sensitivity:
        lines.extend([
            "## EPR Sensitivity",
            "",
            "TRR K/temperature/weighting sensitivity was exported; use the K=5, tau=0.05, softmax row as the primary manuscript setting.",
            "",
        ])
    lines.extend([
        "## Claim Boundary",
        "",
        "- Use Protocol-B EPR claims only for methods with complete source-method rows.",
        "- Claim PaSST only when the PaSST coverage gate is ready; do not claim PANNs fairness while its runtime path is blocked.",
        "- Do not use internal labels such as E8 current-code in the manuscript.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paper-facing E9 evidence summary.")
    parser.add_argument("--unified-summary", default="Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_summary.json")
    parser.add_argument("--epr-summary", default="Experiments/E9_TMMMajorRevision/outputs/protocol_b_epr/protocol_b_epr_summary.json")
    parser.add_argument("--blocker", default="Experiments/E9_TMMMajorRevision/outputs/passt_vectors/sota_vector_blocker.json")
    parser.add_argument("--coverage-report", default="Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_audit.json")
    parser.add_argument("--near-duplicate-summary", default="Experiments/E9_TMMMajorRevision/outputs/robustness/near_duplicate_unified/near_duplicate_summary.json")
    parser.add_argument("--validity-summary", default="Experiments/E9_TMMMajorRevision/outputs/validity_audit/validity_summary.json")
    parser.add_argument("--sensitivity-summary", default="Experiments/E9_TMMMajorRevision/outputs/epr_sensitivity/epr_sensitivity_summary.json")
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    args = parser.parse_args()
    unified = _load_optional(Path(args.unified_summary))
    epr = _load_optional(Path(args.epr_summary))
    blocker = _load_optional(Path(args.blocker))
    coverage = _load_optional(Path(args.coverage_report))
    near_duplicate = _load_optional(Path(args.near_duplicate_summary))
    validity = _load_optional(Path(args.validity_summary))
    sensitivity = _load_optional(Path(args.sensitivity_summary))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md = build_summary(
        unified if isinstance(unified, Mapping) else None,
        epr if isinstance(epr, Mapping) else None,
        blocker if isinstance(blocker, Mapping) else None,
        coverage if isinstance(coverage, Mapping) else None,
        near_duplicate if isinstance(near_duplicate, Mapping) else None,
        validity if isinstance(validity, Mapping) else None,
        sensitivity,
    )
    (output_dir / "e9_paper_summary.md").write_text(md, encoding="utf-8")
    (output_dir / "e9_paper_summary.json").write_text(json.dumps({
        "has_blocker": bool(blocker),
        "coverage": coverage,
        "epr": epr,
        "near_duplicate": near_duplicate,
        "sensitivity": sensitivity,
        "unified": unified,
        "validity": validity,
    }, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output_dir / 'e9_paper_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
