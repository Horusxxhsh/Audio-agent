import json

from Experiments.E8_ExecutableNeighborhood.summarize_e8 import (
    build_summary,
    mean_by_method,
    recommendation_from_metrics,
    render_markdown,
)


def test_mean_by_method_groups_numeric_fields():
    rows = [
        {"method": "TRR", "pnr_at_5": 1, "top1_norm_l2": 0.2},
        {"method": "TRR", "pnr_at_5": 0, "top1_norm_l2": 0.4},
    ]
    assert mean_by_method(rows, ["pnr_at_5", "top1_norm_l2"]) == {
        "TRR": {
            "n": 2,
            "pnr_at_5_n": 2,
            "pnr_at_5": 0.5,
            "top1_norm_l2_n": 2,
            "top1_norm_l2": 0.3,
        }
    }


def test_mean_by_method_skips_skipped_rows_and_reports_field_counts():
    rows = [
        {"method": "TRR", "status": "ok", "pnr_at_5": 1, "top1_norm_l2": 0.2},
        {"method": "TRR", "status": "ok", "pnr_at_5": None, "top1_norm_l2": 0.4},
        {"method": "TRR", "status": "skipped", "pnr_at_5": 0, "top1_norm_l2": 9.9},
    ]

    assert mean_by_method(rows, ["pnr_at_5", "top1_norm_l2"]) == {
        "TRR": {
            "n": 2,
            "pnr_at_5_n": 1,
            "pnr_at_5": 1.0,
            "top1_norm_l2_n": 2,
            "top1_norm_l2": 0.3,
        }
    }


def test_recommendation_keeps_mlp_as_boundary_when_numeric_wins():
    text = recommendation_from_metrics(
        trr_norm_l2=0.1881,
        epr_norm_l2=0.1700,
        mlp_norm_l2=0.1603,
        epr_provenance=0.72,
    )
    assert "boundary" in text
    assert "provenance" in text


def test_recommendation_promotes_epr_when_it_beats_mlp():
    text = recommendation_from_metrics(
        trr_norm_l2=0.1881,
        epr_norm_l2=0.1500,
        mlp_norm_l2=0.1603,
        epr_provenance=0.72,
    )
    assert "primary hybrid result" in text


def test_recommendation_does_not_claim_retrieval_side_gain_unless_epr_beats_trr():
    text = recommendation_from_metrics(
        trr_norm_l2=0.1200,
        epr_norm_l2=0.1500,
        mlp_norm_l2=0.1603,
        epr_provenance=0.72,
    )

    assert "does not improve retrieval-side Norm.L2" in text


def test_build_summary_preserves_claim_boundaries_and_required_markdown_sections():
    topk = [
        {"method": "TRR", "status": "ok", "pnr_at_1": 0, "pnr_at_3": 1, "pnr_at_5": 1, "top1_norm_l2": 0.20},
        {"method": "TRR", "status": "ok", "pnr_at_1": 1, "pnr_at_3": 1, "pnr_at_5": 1, "top1_norm_l2": 0.10},
    ]
    epr = [
        {
            "method": "EPR-K5",
            "status": "ok",
            "norm_l2": 0.12,
            "acc_at_0_1": 0.9,
            "recall": 0.8,
            "cosine": 0.7,
            "module": 1.0,
            "provenance_max_weight": 0.4,
            "provenance_effective_exemplars": 3.0,
        }
    ]
    module = [
        {
            "method": "TRR",
            "status": "ok",
            "changed": False,
            "original_norm_l2": 0.15,
            "reranked_norm_l2": 0.16,
            "original_acc_at_0_1": 0.8,
            "reranked_acc_at_0_1": 0.8,
        }
    ]
    mlp = {
        "projected_method": "MLP-Regressor+RangeProjection",
        "projected_metrics": {
            "l2_norm": 0.11,
            "acc_at_01": 0.91,
            "recall": 0.82,
            "cosine": 0.73,
            "module": 1.0,
        },
    }

    summary = build_summary(topk, epr, module, mlp)
    markdown = render_markdown(summary)

    assert summary["topk"]["by_method"]["TRR"]["pnr_at_5"] == 1.0
    assert summary["mlp"]["projected_metrics"]["norm_l2"] == 0.11
    assert summary["recommendation"]["numeric_winner"] == "MLP+RangeProjection"
    assert summary["module"]["interpretation"] == "diagnostic_negative"
    assert "PC-TRR 训练收益未验证" in summary["claims"]["not_supported"]
    assert "Protocol-C adaptive fusion 不能作为主贡献" in summary["claims"]["not_supported"]
    for section in [
        "# E8 Executable Neighborhood Retrieval Summary",
        "## Scope",
        "## Top-K Parameter Neighborhood Recall",
        "## Exemplar-Preserving Parameter Projection",
        "## Module-Aware Reranking",
        "## MLP Boundary Interpretation",
        "## Claims Supported",
        "## Claims Not Supported",
    ]:
        assert section in markdown


def test_build_summary_marks_epr_as_numeric_winner_when_current_hybrid_beats_mlp():
    summary = build_summary(
        [{"method": "TRR", "status": "ok", "pnr_at_5": 1, "top1_norm_l2": 0.20}],
        [
            {
                "method": "EPR-K5",
                "status": "ok",
                "norm_l2": 0.13,
                "acc_at_0_1": 0.79,
                "recall": 0.71,
                "cosine": 0.92,
                "module": 0.83,
                "provenance_max_weight": 0.34,
                "provenance_effective_exemplars": 4.2,
            }
        ],
        [],
        {
            "projected_metrics": {
                "l2_norm": 0.16,
                "acc_at_01": 0.789,
                "recall": 0.35,
                "cosine": 0.59,
                "module": 1.0,
            }
        },
    )

    assert summary["recommendation"]["numeric_winner"] == "EPR"
    assert "primary hybrid result" in summary["recommendation"]["text"]


def test_cli_writes_machine_readable_json_and_markdown(tmp_path):
    from Experiments.E8_ExecutableNeighborhood.summarize_e8 import main

    topk_path = tmp_path / "topk.json"
    epr_path = tmp_path / "epr.json"
    module_path = tmp_path / "module.json"
    mlp_path = tmp_path / "mlp.json"
    out_dir = tmp_path / "summary"

    topk_path.write_text(json.dumps([{"method": "TRR", "status": "ok", "pnr_at_5": 1, "top1_norm_l2": 0.2}]))
    epr_path.write_text(
        json.dumps(
            [
                {
                    "method": "EPR-K5",
                    "status": "ok",
                    "norm_l2": 0.18,
                    "acc_at_0_1": 0.8,
                    "recall": 0.7,
                    "cosine": 0.6,
                    "module": 1.0,
                    "provenance_max_weight": 0.5,
                    "provenance_effective_exemplars": 2.0,
                }
            ]
        )
    )
    module_path.write_text(
        json.dumps(
            [
                {
                    "method": "TRR",
                    "status": "ok",
                    "changed": True,
                    "original_norm_l2": 0.2,
                    "reranked_norm_l2": 0.21,
                    "original_acc_at_0_1": 0.8,
                    "reranked_acc_at_0_1": 0.79,
                }
            ]
        )
    )
    mlp_path.write_text(
        json.dumps(
            {
                "projected_metrics": {
                    "l2_norm": 0.16,
                    "acc_at_01": 0.82,
                    "recall": 0.75,
                    "cosine": 0.65,
                    "module": 1.0,
                }
            }
        )
    )

    assert main(
        [
            "--topk-json",
            str(topk_path),
            "--epr-json",
            str(epr_path),
            "--module-json",
            str(module_path),
            "--mlp-json",
            str(mlp_path),
            "--output-dir",
            str(out_dir),
        ]
    ) == 0
    assert (out_dir / "e8_summary.json").exists()
    assert (out_dir / "e8_summary.md").exists()
    written = json.loads((out_dir / "e8_summary.json").read_text())
    assert set(written) >= {"topk", "epr", "module", "mlp", "recommendation", "claims"}
