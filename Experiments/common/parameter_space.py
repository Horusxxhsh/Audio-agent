from __future__ import annotations

import math
from typing import Dict, Iterable, Mapping, Sequence

from Experiments.common.evaluate import load_param_ranges


def _as_finite_float(value: object, key: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"non-finite numeric value for {key}: {value}")
    return numeric


def _as_non_negative_finite_float(value: object, name: str) -> float:
    numeric = _as_finite_float(value, name)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


def flatten_numeric_params(params: Mapping, prefix: str = "") -> Dict[str, float]:
    flat: Dict[str, float] = {}
    for key, value in params.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flat.update(flatten_numeric_params(value, dotted))
        elif isinstance(value, bool):
            continue
        elif isinstance(value, (int, float)):
            flat[dotted] = _as_finite_float(value, dotted)
        elif isinstance(value, str):
            try:
                numeric = float(value)
            except ValueError:
                continue
            flat[dotted] = _as_finite_float(numeric, dotted)
    return flat


def active_modules(params: Mapping) -> set[str]:
    return {str(key)[:-2] for key in params.keys() if str(key).endswith("On")}


def _canonical_edit_key(key: str) -> str:
    parts = key.split(".")
    if parts and (parts[0].endswith("On") or parts[0].endswith("Off")):
        parts[0] = parts[0][:-2] if parts[0].endswith("On") else parts[0][:-3]
    return ".".join(parts)


def _module_range_candidates(module: str) -> list[str]:
    candidates = [module]
    if module.endswith("On"):
        candidates.append(f"{module[:-2]}Off")
    elif module.endswith("Off"):
        candidates.append(f"{module[:-3]}On")
    return candidates


def _normalize_with_ranges(original_key: str, value: float, ranges: Mapping) -> float:
    if not ranges:
        raise ValueError("normalization ranges are required when normalize=True")
    parts = original_key.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"missing normalization range for {original_key}")
    module, param = parts
    param_info = {}
    for candidate_module in _module_range_candidates(module):
        module_ranges = ranges.get(candidate_module, {})
        if isinstance(module_ranges, Mapping):
            candidate_info = module_ranges.get(param, {})
            if isinstance(candidate_info, Mapping) and "min" in candidate_info and "max" in candidate_info:
                param_info = candidate_info
                break
    if not (isinstance(param_info, Mapping) and "min" in param_info and "max" in param_info):
        raise ValueError(f"missing normalization range for {original_key}")
    lo = _as_finite_float(param_info["min"], f"{original_key}.min")
    hi = _as_finite_float(param_info["max"], f"{original_key}.max")
    if abs(hi - lo) < 1e-12:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _canonical_numeric_params_for_edit(params: Mapping, normalize: bool, ranges: Mapping) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key, value in flatten_numeric_params(params).items():
        edit_value = _normalize_with_ranges(key, value, ranges) if normalize else value
        out[_canonical_edit_key(key)] = edit_value
    return out


def _numeric_params_for_distance(params: Mapping, normalize: bool, ranges: Mapping) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key, value in flatten_numeric_params(params).items():
        out[key] = _normalize_with_ranges(key, value, ranges) if normalize else value
    return out


def _parameter_rmse(pred_params: Mapping, gt_params: Mapping, normalize: bool) -> float:
    ranges = load_param_ranges() if normalize else {}
    pred = _numeric_params_for_distance(pred_params, normalize, ranges)
    gt = _numeric_params_for_distance(gt_params, normalize, ranges)
    keys = sorted(set(pred) | set(gt))
    if not keys:
        return 0.0
    error_sum = sum((pred.get(key, 0.0) - gt.get(key, 0.0)) ** 2 for key in keys)
    return math.sqrt(error_sum / len(keys))


def topk_parameter_neighborhood_recall(
    topk_params: Sequence[Mapping],
    gt_params: Mapping,
    threshold: float,
    normalize: bool = True,
) -> int:
    return int(any(_parameter_rmse(candidate, gt_params, normalize) <= float(threshold) for candidate in topk_params))


def edit_cost(
    pred_params: Mapping,
    gt_params: Mapping,
    switch_weight: float = 1.0,
    continuous_weight: float = 1.0,
    normalize: bool = True,
) -> float:
    switch_weight = _as_non_negative_finite_float(switch_weight, "switch_weight")
    continuous_weight = _as_non_negative_finite_float(continuous_weight, "continuous_weight")
    pred_modules = active_modules(pred_params)
    gt_modules = active_modules(gt_params)
    switch_changes = len(pred_modules.symmetric_difference(gt_modules))
    ranges = load_param_ranges() if normalize else {}
    pred = _canonical_numeric_params_for_edit(pred_params, normalize, ranges)
    gt = _canonical_numeric_params_for_edit(gt_params, normalize, ranges)
    keys = sorted(set(pred) | set(gt))
    continuous_l1 = 0.0
    for key in keys:
        pv = pred.get(key, 0.0)
        gv = gt.get(key, 0.0)
        continuous_l1 += abs(pv - gv)
    return round(switch_weight * switch_changes + continuous_weight * continuous_l1, 10)


def exemplar_provenance_score(weights: Iterable[float]) -> Dict[str, float]:
    ws = []
    for weight in weights:
        numeric_weight = float(weight)
        if not math.isfinite(numeric_weight) or numeric_weight < 0:
            raise ValueError("weights must be finite and non-negative")
        ws.append(numeric_weight)
    total = sum(ws)
    if total <= 0:
        return {"max_weight": 0.0, "entropy_norm": 0.0, "effective_exemplars": 0.0}
    probs = [w / total for w in ws]
    max_weight = max(probs)
    entropy = -sum(p * math.log(p) for p in probs if p > 0)
    entropy_norm = entropy / math.log(len(probs)) if len(probs) > 1 else 0.0
    effective = 1.0 / sum(p * p for p in probs if p > 0)
    return {
        "max_weight": round(max_weight, 10),
        "entropy_norm": round(entropy_norm, 10),
        "effective_exemplars": round(effective, 10),
    }


def blend_parameter_dicts(candidates: Sequence[Mapping], weights: Sequence[float]) -> Dict:
    if len(candidates) != len(weights):
        raise ValueError("candidates and weights must have the same length")
    if not candidates:
        return {}
    checked_weights = []
    for weight in weights:
        numeric_weight = _as_non_negative_finite_float(weight, "weight")
        checked_weights.append(numeric_weight)
    total = float(sum(checked_weights))
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    norm_weights = [w / total for w in checked_weights]
    flat_acc: Dict[str, float] = {}
    for candidate, weight in zip(candidates, norm_weights):
        for key, value in flatten_numeric_params(candidate).items():
            flat_acc[key] = flat_acc.get(key, 0.0) + weight * value
    out: Dict = {}
    for dotted, value in flat_acc.items():
        cur = out
        parts = dotted.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = round(float(value), 10)
    return out
