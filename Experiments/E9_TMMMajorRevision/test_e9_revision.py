import json
from pathlib import Path

import pytest

from Experiments.E9_TMMMajorRevision.prepare_sota_vectors import (
    coverage_report,
    dependency_status,
    build_audio_basename_index,
    resolve_audio_path_for_item,
    write_blocker_report,
)
from Experiments.E9_TMMMajorRevision.protocol_b_epr_projection import (
    epr_rows_for_methods,
)
from Experiments.E9_TMMMajorRevision.robustness_export import (
    bootstrap_mean_ci,
    near_duplicate_sensitivity,
    shared_subset_indices,
)
from Experiments.E9_TMMMajorRevision.validity_audit import (
    epr_validity_record,
    switch_metrics,
)
from Experiments.E9_TMMMajorRevision.epr_sensitivity import (
    epr_sensitivity_rows,
)
from Experiments.E9_TMMMajorRevision.unified_protocol_export import (
    aggregate_topk_rows,
    dump_unified_topk,
    vector_coverage,
)


def _item(name, vectors, gain, module_on=1.0):
    return {
        "SongName": name,
        "Vectors": vectors,
        "Parameters": {"DriverOn": {"Distortion": gain}, "DelayOn": {"Mix": module_on}},
    }


def test_vector_coverage_counts_query_and_kb_availability():
    data = [
        _item("q", {"TRR": [1.0, 0.0], "CLAP": [1.0, 0.0]}, 0.1),
        _item("kb1", {"TRR": [0.9, 0.1]}, 0.2),
        _item("kb2", {"TRR": [0.1, 0.9], "CLAP": [0.1, 0.9]}, 0.8),
    ]
    report = vector_coverage(data, query_indices=[0], methods={"TRR": "TRR", "CLAP": "CLAP"})
    assert report["TRR"] == {"query_ok": 1, "query_total": 1, "kb_ok": 2, "kb_total": 2}
    assert report["CLAP"] == {"query_ok": 1, "query_total": 1, "kb_ok": 1, "kb_total": 2}


def test_aggregate_topk_rows_reports_pnr_at_configured_thresholds():
    rows = [
        {
            "method": "TRR",
            "status": "ok",
            "top1_norm_l2": 0.2,
            "top1_acc_at_0_1": 0.5,
            "top1_recall": 0.4,
            "top1_cosine": 0.7,
            "top1_module": 1.0,
            "pnr_at_1_t0_05": 0,
            "pnr_at_5_t0_05": 1,
            "pnr_at_10_t0_05": 1,
            "pnr_at_1_t0_10": 1,
            "pnr_at_5_t0_10": 1,
            "pnr_at_10_t0_10": 1,
        }
    ]
    summary = aggregate_topk_rows(rows, pnr_thresholds=[0.05, 0.10])
    trr = summary["TRR"]
    assert trr["n"] == 1
    assert trr["pnr_at_5_t0_05"] == 1.0
    assert trr["pnr_at_1_t0_10"] == 1.0


def test_epr_rows_for_methods_projects_each_source_method():
    topk_rows = [
        {
            "method": "TRR",
            "status": "ok",
            "query_idx": 0,
            "query_name": "q",
            "topk_candidates": [
                {"name": "kb1", "score": 0.9, "parameters": {"DriverOn": {"Distortion": 0.2}}},
                {"name": "kb2", "score": 0.8, "parameters": {"DriverOn": {"Distortion": 0.8}}},
            ],
        },
        {
            "method": "Wav2Vec",
            "status": "ok",
            "query_idx": 0,
            "query_name": "q",
            "topk_candidates": [
                {"name": "kb2", "score": 0.7, "parameters": {"DriverOn": {"Distortion": 0.8}}},
            ],
        },
    ]
    dataset = [_item("q", {}, 0.25), _item("kb1", {}, 0.2), _item("kb2", {}, 0.8)]
    rows = epr_rows_for_methods(topk_rows, dataset, source_methods=["TRR", "Wav2Vec"], k=2, temperature=0.05)
    assert {(row["source_method"], row["method"]) for row in rows} == {
        ("TRR", "EPR-K2"),
        ("Wav2Vec", "EPR-K2"),
    }
    assert all(row["status"] == "ok" for row in rows)
    assert all(row["provenance_effective_exemplars"] >= 1.0 for row in rows)


def test_shared_subset_indices_requires_all_methods_on_query_and_kb():
    data = [
        _item("q0", {"TRR": [1], "CLAP": [1]}, 0.1),
        _item("q1", {"TRR": [1]}, 0.2),
        _item("kb_bad", {"TRR": [1]}, 0.3),
        _item("kb_ok", {"TRR": [1], "CLAP": [1]}, 0.4),
    ]
    query_subset, kb_subset = shared_subset_indices(
        data,
        query_indices=[0, 1],
        methods={"TRR": "TRR", "CLAP": "CLAP"},
        return_kb=True,
    )
    assert query_subset == [0]
    assert kb_subset == [3]


def test_dump_unified_topk_accepts_explicit_kb_indices():
    data = [
        _item("q", {"TRR": [1.0, 0.0]}, 0.1),
        _item("near", {"TRR": [0.99, 0.01]}, 0.12),
        _item("far", {"TRR": [0.0, 1.0]}, 0.9),
    ]
    rows = dump_unified_topk(
        data,
        query_indices=[0],
        kb_indices=[2],
        methods={"TRR": "TRR"},
        k=1,
        pnr_thresholds=[0.10],
    )
    assert rows[0]["status"] == "ok"
    assert rows[0]["top1_name"] == "far"


def test_near_duplicate_threshold_zero_matches_canonical_top1_summary():
    data = [
        _item("q", {"TRR": [1.0, 0.0]}, 0.1),
        _item("near", {"TRR": [0.99, 0.01]}, 0.1),
        _item("far", {"TRR": [0.0, 1.0]}, 0.9),
    ]
    canonical = aggregate_topk_rows(
        dump_unified_topk(data, [0], methods={"TRR": "TRR"}, k=10, pnr_thresholds=[0.10]),
        pnr_thresholds=[0.10],
    )
    sensitivity = near_duplicate_sensitivity(
        data,
        query_indices=[0],
        methods={"TRR": "TRR"},
        thresholds=[0.0, 0.05],
        k=10,
    )
    assert sensitivity["0.000"]["TRR"]["norm_l2"] == canonical["TRR"]["norm_l2"]
    assert sensitivity["0.050"]["TRR"]["kb_size"] == 1


def test_epr_sensitivity_handles_softmax_and_uniform_deterministically():
    topk_rows = [
        {
            "method": "TRR",
            "status": "ok",
            "query_idx": 0,
            "query_name": "q",
            "topk_candidates": [
                {"name": "kb1", "score": 0.9, "parameters": {"DriverOn": {"Distortion": 0.2}}},
                {"name": "kb2", "score": 0.8, "parameters": {"DriverOn": {"Distortion": 0.8}}},
            ],
        }
    ]
    dataset = [_item("q", {}, 0.25), _item("kb1", {}, 0.2), _item("kb2", {}, 0.8)]
    rows1 = epr_sensitivity_rows(topk_rows, dataset, source_method="TRR", ks=[1, 2], temperatures=[0.05], weighting_modes=["softmax", "uniform"])
    rows2 = epr_sensitivity_rows(topk_rows, dataset, source_method="TRR", ks=[1, 2], temperatures=[0.05], weighting_modes=["softmax", "uniform"])
    assert rows1 == rows2
    assert {(row["k"], row["weighting"]) for row in rows1} == {(1, "softmax"), (2, "softmax"), (1, "uniform"), (2, "uniform")}
    assert all("switch_f1" in row for row in rows1)


def test_validity_audit_detects_range_repair_and_switch_collision():
    ranges = {"DriverOn.Distortion": (0.0, 1.0), "DriverOff.Distortion": (0.0, 1.0)}
    pre = {"DriverOn": {"Distortion": 1.5}, "DriverOff": {"Distortion": 0.3}}
    post = {"DriverOn": {"Distortion": 1.0}}
    record = epr_validity_record(pre, post, ranges)
    assert record["pre_valid"] is False
    assert record["post_valid"] is True
    assert record["range_repaired"] is True
    assert record["switch_repaired"] is True


def test_switch_metrics_uses_values_not_key_presence():
    gt = {"DriverOn": {"Distortion": 0.5}, "DelayOff": {"Mix": 0.0}}
    pred = {"DriverOff": {"Distortion": 0.5}, "DelayOff": {"Mix": 0.0}, "DriverOn": {"Distortion": 0.0}}
    metrics = switch_metrics(pred, gt)
    assert metrics["legacy_module_jaccard"] == 1.0
    assert metrics["switch_f1"] < 1.0
    assert metrics["switch_accuracy"] < 1.0


def test_passt_path_resolver_handles_windows_audio_paths(tmp_path):
    audio = tmp_path / "Studio Clean.wav"
    audio.write_bytes(b"riff")
    index = build_audio_basename_index([tmp_path])
    item = {"AudioPath": r"C:\Users\80753\Documents\Github\Audio-agent\Data\Audio_Synthetic\Studio Clean.wav"}
    assert resolve_audio_path_for_item(item, index) == audio


def test_bootstrap_mean_ci_is_deterministic_and_ordered():
    low1, high1 = bootstrap_mean_ci([1.0, 2.0, 3.0], n_boot=200, seed=7)
    low2, high2 = bootstrap_mean_ci([1.0, 2.0, 3.0], n_boot=200, seed=7)
    assert (low1, high1) == (low2, high2)
    assert low1 <= 2.0 <= high1


def test_prepare_sota_vectors_writes_blocker_for_missing_dependency(tmp_path):
    status = dependency_status(["definitely_missing_audio_dep"])
    assert status["definitely_missing_audio_dep"]["available"] is False
    path = write_blocker_report(tmp_path, status, context={"phase": "unit"})
    payload = json.loads(Path(path).read_text())
    assert payload["status"] == "blocked"
    assert payload["missing_dependencies"] == ["definitely_missing_audio_dep"]


def test_coverage_report_marks_missing_methods():
    data = [_item("q", {"TRR": [1]}, 0.1), _item("kb", {"TRR": [1]}, 0.2)]
    report = coverage_report(data, query_indices=[0], methods={"TRR": "TRR", "PaSST": "PaSST"})
    assert report["methods"]["TRR"]["ready"] is True
    assert report["methods"]["PaSST"]["ready"] is False
    assert report["ready"] is False
