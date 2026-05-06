from __future__ import annotations

import math
from typing import Mapping

from Experiments.common.evaluate import Evaluator
from Experiments.common.parameter_space import flatten_numeric_params


def _module_root(key: str) -> tuple[str, str] | None:
    if key.endswith("On"):
        return key[:-2], "On"
    if key.endswith("Off"):
        return key[:-3], "Off"
    return None


def _branch_energy(value: object) -> float:
    if isinstance(value, Mapping):
        return float(sum(abs(v) for v in flatten_numeric_params(value).values()))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return abs(float(value))
    return 0.0


def switch_state_map(params: Mapping[str, object]) -> dict[str, str]:
    votes: dict[str, dict[str, float]] = {}
    for key, value in params.items():
        root_state = _module_root(str(key))
        if root_state is None:
            continue
        root, state = root_state
        votes.setdefault(root, {"On": 0.0, "Off": 0.0})[state] += _branch_energy(value)
    states: dict[str, str] = {}
    for root, state_votes in votes.items():
        on_vote = float(state_votes.get("On", 0.0))
        off_vote = float(state_votes.get("Off", 0.0))
        if on_vote > off_vote:
            states[root] = "On"
        elif off_vote > on_vote:
            states[root] = "Off"
        else:
            states[root] = "On" if f"{root}On" in params else "Off"
    return states


def switch_metrics(pred_params: Mapping[str, object], gt_params: Mapping[str, object]) -> dict[str, float]:
    pred_states = switch_state_map(pred_params)
    gt_states = switch_state_map(gt_params)
    roots = sorted(set(pred_states) | set(gt_states))
    pred_active = {root for root, state in pred_states.items() if state == "On"}
    gt_active = {root for root, state in gt_states.items() if state == "On"}
    tp = len(pred_active & gt_active)
    fp = len(pred_active - gt_active)
    fn = len(gt_active - pred_active)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not gt_active else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (
        sum(1 for root in roots if pred_states.get(root) == gt_states.get(root)) / len(roots)
        if roots
        else 1.0
    )
    return {
        "switch_precision": float(precision),
        "switch_recall": float(recall),
        "switch_f1": float(f1),
        "switch_accuracy": float(accuracy),
        "legacy_module_jaccard": float(Evaluator(normalize=False).compute_module_consistency(pred_params, gt_params)),
    }


def _range_violations(params: Mapping[str, object], ranges: Mapping[str, tuple[float, float]]) -> list[str]:
    violations = []
    for key, value in flatten_numeric_params(params).items():
        numeric = float(value)
        if not math.isfinite(numeric):
            violations.append(key)
            continue
        if key in ranges:
            lo, hi = ranges[key]
            if numeric < float(lo) - 1e-9 or numeric > float(hi) + 1e-9:
                violations.append(key)
    return violations


def _switch_collisions(params: Mapping[str, object]) -> list[str]:
    roots: dict[str, set[str]] = {}
    for key in params.keys():
        root_state = _module_root(str(key))
        if root_state is None:
            continue
        root, state = root_state
        roots.setdefault(root, set()).add(state)
    return sorted(root for root, states in roots.items() if "On" in states and "Off" in states)


def _valid(params: Mapping[str, object], ranges: Mapping[str, tuple[float, float]]) -> bool:
    return not _range_violations(params, ranges) and not _switch_collisions(params)


def epr_validity_record(
    pre_projection: Mapping[str, object],
    post_projection: Mapping[str, object],
    ranges: Mapping[str, tuple[float, float]],
) -> dict[str, object]:
    pre_range = _range_violations(pre_projection, ranges)
    post_range = _range_violations(post_projection, ranges)
    pre_switch = _switch_collisions(pre_projection)
    post_switch = _switch_collisions(post_projection)
    return {
        "pre_valid": _valid(pre_projection, ranges),
        "post_valid": _valid(post_projection, ranges),
        "range_repaired": bool(pre_range and not post_range),
        "switch_repaired": bool(pre_switch and not post_switch),
        "pre_range_violations": pre_range,
        "post_range_violations": post_range,
        "pre_switch_collisions": pre_switch,
        "post_switch_collisions": post_switch,
    }
