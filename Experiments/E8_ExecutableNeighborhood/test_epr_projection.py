import csv

import pytest

from Experiments.E8_ExecutableNeighborhood.epr_projection import (
    enforce_mutually_exclusive_module_states,
    observed_numeric_ranges,
    project_to_observed_ranges,
    write_outputs,
    softmax_weights,
    weighted_projection,
)


def test_softmax_weights_prefers_higher_similarity():
    weights = softmax_weights([2.0, 1.0], temperature=1.0)

    assert weights[0] > weights[1]
    assert round(sum(weights), 10) == 1.0


def test_softmax_weights_rejects_nonfinite_temperature_and_scores():
    with pytest.raises(ValueError, match="positive and finite"):
        softmax_weights([1.0, 2.0], temperature=float("inf"))
    with pytest.raises(ValueError, match="scores must be finite"):
        softmax_weights([1.0, float("nan")], temperature=1.0)


def test_softmax_weights_is_stable_for_large_scores():
    weights = softmax_weights([10000.0, 9999.0], temperature=1.0)

    assert weights[0] > weights[1]
    assert round(sum(weights), 10) == 1.0


def test_observed_numeric_ranges_collects_min_max_from_kb_items():
    items = [
        {"Parameters": {"DriverOn": {"Distortion": 0.1}}},
        {"Parameters": {"DriverOn": {"Distortion": 0.9}}},
    ]

    assert observed_numeric_ranges(items) == {"DriverOn.Distortion": (0.1, 0.9)}


def test_project_to_observed_ranges_clips_values():
    params = {"DriverOn": {"Distortion": 1.5}}
    ranges = {"DriverOn.Distortion": (0.1, 0.9)}

    assert project_to_observed_ranges(params, ranges) == {"DriverOn": {"Distortion": 0.9}}


def test_weighted_projection_blends_then_projects():
    candidates = [
        {"DriverOn": {"Distortion": 0.0}},
        {"DriverOn": {"Distortion": 1.0}},
    ]

    projected, provenance = weighted_projection(
        candidates,
        [0.25, 0.75],
        {"DriverOn.Distortion": (0.2, 0.7)},
    )

    assert projected == {"DriverOn": {"Distortion": 0.7}}
    assert provenance["max_weight"] == 0.75


def test_weighted_projection_enforces_on_off_exclusivity():
    candidates = [
        {"FlangerOff": {"Delay": "0.0", "Depth": "0.0"}},
        {"FlangerOn": {"Delay": "0.8", "Depth": "0.6"}},
    ]

    projected, _ = weighted_projection(
        candidates,
        [0.25, 0.75],
        {
            "FlangerOff.Delay": (0.0, 0.0),
            "FlangerOff.Depth": (0.0, 0.0),
            "FlangerOn.Delay": (0.0, 1.0),
            "FlangerOn.Depth": (0.0, 1.0),
        },
    )

    assert "FlangerOn" in projected
    assert "FlangerOff" not in projected


def test_enforce_mutually_exclusive_module_states_uses_weighted_vote():
    params = {
        "FlangerOff": {"Delay": 0.0},
        "FlangerOn": {"Delay": 0.9},
        "ReverbOn": {"Mix": 0.2},
    }
    candidates = [
        {"FlangerOff": {"Delay": 0.0}, "ReverbOn": {"Mix": 0.2}},
        {"FlangerOn": {"Delay": 0.9}, "ReverbOn": {"Mix": 0.4}},
    ]

    resolved = enforce_mutually_exclusive_module_states(params, candidates, [0.7, 0.3])

    assert "FlangerOff" in resolved
    assert "FlangerOn" not in resolved
    assert "ReverbOn" in resolved


def test_write_outputs_omits_prediction_parameters_from_csv(tmp_path):
    write_outputs(
        tmp_path,
        [
            {
                "method": "EPR-K3",
                "source_method": "TRR",
                "query_idx": 1,
                "query_name": "Q",
                "k": 3,
                "effective_k": 1,
                "temperature": 0.05,
                "status": "ok",
                "skip_reason": "",
                "prediction_parameters": {"DriverOn": {"Distortion": 0.5}},
            }
        ],
    )

    with (tmp_path / "epr_projection_results.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "prediction_parameters" not in reader.fieldnames


def test_projection_range_is_derived_from_kb_not_query_ground_truth():
    query_gt = {"DriverOn": {"Distortion": 999.0}}
    kb_items = [
        {"Parameters": {"DriverOn": {"Distortion": 0.2}}},
        {"Parameters": {"DriverOn": {"Distortion": 0.8}}},
    ]

    ranges = observed_numeric_ranges(kb_items)

    assert "999" not in str(ranges)
    assert project_to_observed_ranges(query_gt, ranges) == {"DriverOn": {"Distortion": 0.8}}
