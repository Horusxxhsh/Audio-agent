import json

import numpy as np

from Experiments.E8_ExecutableNeighborhood.topk_retrieval_dump import (
    VECTOR_METHODS,
    cosine_topk,
    dump_topk,
    topk_record,
    write_outputs,
)


def test_cosine_topk_sorts_descending():
    query = np.array([1.0, 0.0])
    matrix = np.array([[0.0, 1.0], [1.0, 0.0], [0.8, 0.2]])
    assert cosine_topk(query, matrix, k=2) == [(1, 1.0), (2, 0.9701425001453318)]


def test_cosine_topk_rejects_empty_matrix():
    query = np.array([1.0, 0.0])
    assert cosine_topk(query, np.empty((0, 2)), k=3) == []


def test_topk_record_contains_pnr_and_top1_fields():
    query_item = {"SongName": "Q", "Parameters": {"DriverOn": {"Distortion": 0.5}}}
    candidates = [
        ({"SongName": "A", "Parameters": {"DriverOn": {"Distortion": 0.9}}}, 0.9),
        ({"SongName": "B", "Parameters": {"DriverOn": {"Distortion": 0.52}}}, 0.8),
    ]
    row = topk_record("TRR", 7, query_item, candidates, threshold=0.05)
    assert row["method"] == "TRR"
    assert row["query_idx"] == 7
    assert row["top1_name"] == "A"
    assert row["pnr_at_k"] == 1
    assert row["topk_names"] == ["A", "B"]


def _fake_item(name, vectors=None):
    vectors = vectors or {}
    return {
        "SongName": name,
        "Parameters": {"DriverOn": {"Distortion": 0.5}},
        "Vectors": vectors,
    }


def _all_method_vectors(value):
    return {vector_key: [value, 0.0] for vector_key in VECTOR_METHODS.values()}


def test_write_outputs_json_is_array_loadable(tmp_path):
    rows = [{"method": "TRR", "query_idx": 0}, {"method": "Wav2Vec", "query_idx": 0}]
    audit = {"TRR": {"expected_queries": 1}, "Wav2Vec": {"expected_queries": 1}}

    write_outputs(tmp_path, rows, audit)

    loaded = json.loads((tmp_path / "topk_retrieval_metrics.json").read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert loaded == rows


def test_dump_topk_emits_skipped_row_for_missing_vector(tmp_path):
    dataset = [
        _fake_item("Q", {"TRR": [1.0, 0.0]}),
        _fake_item("KB", _all_method_vectors(1.0)),
    ]
    dataset_path = tmp_path / "dataset.json"
    split_path = tmp_path / "test.txt"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    split_path.write_text("Q\n", encoding="utf-8")

    rows = dump_topk(dataset_path, split_path, tmp_path / "out", k=1, threshold=0.1)

    assert len(rows) == len(VECTOR_METHODS)
    clap = next(row for row in rows if row["method"] == "CLAP")
    assert clap["status"] == "skipped"
    assert clap["coverage"] == 0.0
    assert clap["skip_reason"] == "missing_query_vector"
    assert clap["candidate_count"] == 0


def test_dump_topk_zero_query_vector_is_skipped(tmp_path):
    dataset = [
        _fake_item("Q", dict(_all_method_vectors(1.0), TRR=[0.0, 0.0])),
        _fake_item("KB", _all_method_vectors(1.0)),
    ]
    dataset_path = tmp_path / "dataset.json"
    split_path = tmp_path / "test.txt"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    split_path.write_text("Q\n", encoding="utf-8")

    rows = dump_topk(dataset_path, split_path, tmp_path / "out", k=1, threshold=0.1)

    trr = next(row for row in rows if row["method"] == "TRR")
    assert trr["status"] == "skipped"
    assert trr["skip_reason"] == "zero_norm_query_vector"
    assert trr["topk_names"] == []


def test_dump_topk_preserves_method_query_row_invariant(tmp_path):
    dataset = [
        _fake_item("Q1", _all_method_vectors(1.0)),
        _fake_item("Q2", _all_method_vectors(0.5)),
        _fake_item("KB", _all_method_vectors(1.0)),
    ]
    dataset_path = tmp_path / "dataset.json"
    split_path = tmp_path / "test.txt"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    split_path.write_text("Q1\nQ2\n", encoding="utf-8")

    rows = dump_topk(dataset_path, split_path, tmp_path / "out", k=1, threshold=0.1)

    assert len(rows) == 2 * len(VECTOR_METHODS)
    assert all(row["status"] == "ok" for row in rows)
    assert all(row["candidate_count"] == 1 for row in rows)
