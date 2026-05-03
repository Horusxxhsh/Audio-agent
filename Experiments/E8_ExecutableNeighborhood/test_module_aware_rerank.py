import csv

import pytest

from Experiments.E8_ExecutableNeighborhood.module_aware_rerank import (
    candidate_module_consensus,
    rerank_by_module_consensus,
    rerank_topk_rows,
    write_outputs,
)


def test_candidate_module_consensus_weights_active_modules():
    candidates = [
        {"Parameters": {"DriverOn": {}, "DelayOff": {}}},
        {"Parameters": {"DriverOn": {}, "ReverbOn": {}}},
    ]

    assert candidate_module_consensus(candidates, [0.75, 0.25]) == {"Driver": 1.0, "Reverb": 0.25}


def test_candidate_module_consensus_rejects_negative_weights():
    candidates = [{"Parameters": {"DriverOn": {}}}]

    with pytest.raises(ValueError, match="non-negative"):
        candidate_module_consensus(candidates, [-0.1])


def test_rerank_by_module_consensus_uses_similarity_and_consensus():
    candidates = [
        {"SongName": "A", "Parameters": {"DelayOn": {}}},
        {"SongName": "B", "Parameters": {"DriverOn": {}, "ReverbOn": {}}},
        {"SongName": "C", "Parameters": {"DriverOn": {}}},
        {"SongName": "D", "Parameters": {"ReverbOn": {}}},
    ]

    ranked = rerank_by_module_consensus(candidates, [0.9, 0.85, 0.8, 0.84], module_weight=0.5)

    assert ranked[0]["SongName"] == "B"
    assert ranked[0]["rerank_score"] > ranked[1]["rerank_score"]


def test_rerank_uses_full_precision_before_rounding():
    candidates = [
        {"SongName": "A", "Parameters": {}},
        {"SongName": "B", "Parameters": {"DriverOn": {}}},
    ]
    ranked = rerank_by_module_consensus(
        candidates,
        [1.000000000001, 1.0],
        module_weight=0.0,
    )

    assert ranked[0]["SongName"] == "A"
    assert ranked[0]["rerank_score"] == ranked[1]["rerank_score"]


def test_rerank_does_not_require_query_parameters():
    candidates = [{"SongName": "A", "Parameters": {"DriverOn": {}}}]

    assert rerank_by_module_consensus(candidates, [1.0], module_weight=0.5)[0]["SongName"] == "A"


def test_rerank_topk_rows_rejects_missing_candidate_score():
    dataset = [{"SongName": "Q", "Parameters": {"DriverOn": {"Distortion": 0.8}}}]
    rows = [
        {
            "method": "TRR",
            "query_idx": 0,
            "query_name": "Q",
            "status": "ok",
            "topk_candidates": [{"name": "A", "parameters": {"DriverOn": {"Distortion": 0.8}}}],
        }
    ]

    with pytest.raises(ValueError, match="query_idx=0"):
        rerank_topk_rows(dataset, rows, method="TRR", module_weight=0.5)


def test_rerank_topk_rows_filters_ok_method_and_evaluates_after_sorting():
    dataset = [
        {"SongName": "Q", "Parameters": {"DriverOn": {"Distortion": 0.8}}},
    ]
    rows = [
        {
            "method": "TRR",
            "query_idx": 0,
            "query_name": "Q",
            "status": "ok",
            "topk_candidates": [
                {"name": "A", "score": 0.9, "parameters": {"DelayOn": {"Mix": 0.2}}},
                {"name": "B", "score": 0.85, "parameters": {"DriverOn": {"Distortion": 0.8}, "ReverbOn": {"Mix": 0.1}}},
                {"name": "C", "score": 0.8, "parameters": {"DriverOn": {"Distortion": 0.7}}},
                {"name": "D", "score": 0.84, "parameters": {"ReverbOn": {"Mix": 0.2}}},
            ],
        },
        {
            "method": "TRR",
            "query_idx": 0,
            "query_name": "Q",
            "status": "skipped",
            "topk_candidates": [],
        },
        {
            "method": "CLAP",
            "query_idx": 0,
            "query_name": "Q",
            "status": "ok",
            "topk_candidates": [
                {"name": "Other", "score": 1.0, "parameters": {"DriverOn": {"Distortion": 0.8}}},
            ],
        },
    ]

    records = rerank_topk_rows(dataset, rows, method="TRR", module_weight=0.5)

    assert len(records) == 1
    assert records[0]["original_top1_name"] == "A"
    assert records[0]["reranked_top1_name"] == "B"
    assert records[0]["changed"] is True
    assert records[0]["original_module"] == 0.0
    assert records[0]["reranked_module"] > records[0]["original_module"]


def test_write_outputs_omits_full_parameters_from_csv(tmp_path):
    write_outputs(
        tmp_path,
        [
            {
                "method": "TRR",
                "query_idx": 0,
                "query_name": "Q",
                "original_top1_name": "A",
                "reranked_top1_name": "B",
                "changed": True,
                "original_norm_l2": 1.0,
                "reranked_norm_l2": 0.5,
                "original_module": 0.0,
                "reranked_module": 1.0,
                "module_consensus_score": 0.65,
                "rerank_score": 1.175,
                "reranked_parameters": {"DriverOn": {"Distortion": 0.8}},
            }
        ],
    )

    with (tmp_path / "module_aware_rerank_results.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "reranked_parameters" not in reader.fieldnames
