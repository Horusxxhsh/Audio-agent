from Experiments.common.parameter_space import (
    active_modules,
    blend_parameter_dicts,
    edit_cost,
    exemplar_provenance_score,
    flatten_numeric_params,
    topk_parameter_neighborhood_recall,
)


def test_flatten_numeric_params_parses_nested_numeric_strings():
    params = {"DriverOn": {"Distortion": "0.50", "Mode": "tube"}, "DelayOff": {"Mix": 0}}
    assert flatten_numeric_params(params) == {
        "DriverOn.Distortion": 0.5,
        "DelayOff.Mix": 0.0,
    }


def test_flatten_numeric_params_excludes_bool_leaves():
    params = {"DriverOn": {"Enabled": True, "Distortion": 0.25}, "Bypass": False}
    assert flatten_numeric_params(params) == {"DriverOn.Distortion": 0.25}


def test_active_modules_uses_on_suffix_only():
    assert active_modules({"DriverOn": {}, "DelayOff": {}, "ReverbOn": {}}) == {"Driver", "Reverb"}


def test_topk_parameter_neighborhood_recall_detects_any_close_candidate():
    gt = {"DriverOn": {"Distortion": 0.50}}
    topk = [{"DriverOn": {"Distortion": 0.90}}, {"DriverOn": {"Distortion": 0.53}}]
    assert topk_parameter_neighborhood_recall(topk, gt, threshold=0.05, normalize=False) == 1


def test_topk_parameter_neighborhood_recall_ignores_bool_leaves():
    gt = {"DriverOn": {"Distortion": 0.50, "Enabled": False}}
    topk = [{"DriverOn": {"Distortion": 0.50, "Enabled": True}}]
    assert topk_parameter_neighborhood_recall(topk, gt, threshold=0.0, normalize=False) == 1


def test_edit_cost_penalizes_switch_and_continuous_differences():
    pred = {"DriverOn": {"Distortion": 0.70}, "DelayOff": {"Mix": 0.0}}
    gt = {"DriverOff": {"Distortion": 0.40}, "DelayOff": {"Mix": 0.0}}
    assert edit_cost(pred, gt, switch_weight=2.0, continuous_weight=1.0, normalize=False) == 2.3


def test_edit_cost_normalizes_with_original_on_off_ranges_before_canonical_alignment():
    pred = {"DriverOn": {"Volume": -32.0}}
    gt = {"DriverOff": {"Volume": 64.0}}
    assert edit_cost(pred, gt, switch_weight=0.0, continuous_weight=1.0) == 0.5


def test_edit_cost_normalizes_off_module_with_on_sibling_range():
    pred = {"CompressorOff": {"Threshold": -50.0}}
    gt = {"CompressorOff": {"Threshold": 0.0}}
    assert edit_cost(pred, gt, switch_weight=0.0, continuous_weight=1.0) == 0.5


def test_edit_cost_normalize_raises_when_range_is_missing():
    try:
        edit_cost({"UnknownOn": {"Amount": 0.2}}, {"UnknownOn": {"Amount": 0.1}})
    except ValueError:
        pass
    else:
        raise AssertionError("missing normalization range should be rejected")


def test_edit_cost_rejects_negative_or_nonfinite_weights():
    params = {"DriverOn": {"Distortion": 0.5}}
    for kwargs in (
        {"switch_weight": -1.0},
        {"switch_weight": float("nan")},
        {"switch_weight": float("inf")},
        {"continuous_weight": -1.0},
        {"continuous_weight": float("nan")},
        {"continuous_weight": float("inf")},
    ):
        try:
            edit_cost(params, params, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"edit_cost weight should be rejected: {kwargs}")


def test_exemplar_provenance_score_reports_concentrated_weights():
    score = exemplar_provenance_score([0.8, 0.2])
    assert score["max_weight"] == 0.8
    assert round(score["effective_exemplars"], 4) == 1.4706


def test_exemplar_provenance_score_rejects_negative_or_nonfinite_weights():
    for weights in ([-0.1, 1.1], [float("nan")], [float("inf")]):
        try:
            exemplar_provenance_score(weights)
        except ValueError:
            pass
        else:
            raise AssertionError(f"weights should be rejected: {weights}")


def test_blend_parameter_dicts_averages_shared_numeric_leaves():
    a = {"DriverOn": {"Distortion": 0.0, "Volume": -10.0}}
    b = {"DriverOn": {"Distortion": 1.0, "Volume": -20.0}}
    assert blend_parameter_dicts([a, b], [0.25, 0.75]) == {
        "DriverOn": {"Distortion": 0.75, "Volume": -17.5}
    }


def test_blend_parameter_dicts_empty_input_is_deterministic():
    assert blend_parameter_dicts([], []) == {}


def test_blend_parameter_dicts_rejects_negative_or_nonfinite_weights():
    a = {"DriverOn": {"Distortion": 0.0}}
    for weights in ([-1.0], [float("nan")], [float("inf")]):
        try:
            blend_parameter_dicts([a], weights)
        except ValueError:
            pass
        else:
            raise AssertionError(f"weights should be rejected: {weights}")


def test_blend_parameter_dicts_rejects_nonfinite_numeric_leaf():
    a = {"DriverOn": {"Distortion": float("nan")}}
    try:
        blend_parameter_dicts([a], [1.0])
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite numeric leaf should be rejected")
