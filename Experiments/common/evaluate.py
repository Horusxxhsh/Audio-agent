import json
import math
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Default path for parameter ranges config
_PARAM_RANGES_PATH = Path(__file__).parent / "param_ranges.json"


def load_param_ranges(path: Optional[str] = None) -> Dict:
    """Load DSP parameter physical ranges for min-max normalization.

    Args:
        path: Path to param_ranges.json. Uses default if None.

    Returns:
        Nested dict of parameter ranges with min/max values.
    """
    p = Path(path) if path else _PARAM_RANGES_PATH
    if not p.exists():
        logger.warning(f"param_ranges.json not found at {p}, normalization disabled")
        return {}
    with open(p, "r") as f:
        data = json.load(f)
    # Remove _doc key
    data.pop("_doc", None)
    return data


class Evaluator:
    def __init__(self, normalize: bool = False, param_ranges_path: Optional[str] = None):
        """Initialize Evaluator.

        Args:
            normalize: If True, apply min-max normalization using DSP physical ranges
                       before computing metrics. This maps all parameters to [0, 1].
            param_ranges_path: Path to param_ranges.json (optional).
        """
        self.normalize = normalize
        self._param_ranges: Optional[Dict] = None
        self._param_ranges_path = param_ranges_path
        if normalize:
            self._param_ranges = load_param_ranges(param_ranges_path)
            if not self._param_ranges:
                logger.warning("Normalization requested but no ranges loaded; falling back to raw mode")
                self.normalize = False

    def _get_range(self, key: str) -> Tuple[float, float]:
        """Get (min, max) for a flattened parameter key like 'CompressorOn.Threshold'.

        Args:
            key: Dot-separated parameter key.

        Returns:
            (min_val, max_val) tuple. Returns (0.0, 1.0) as fallback.
        """
        if not self._param_ranges:
            return (0.0, 1.0)
        parts = key.split(".", 1)
        if len(parts) == 2:
            module, param = parts
            module_ranges = self._param_ranges.get(module, {})
            if isinstance(module_ranges, dict):
                param_info = module_ranges.get(param, {})
                if isinstance(param_info, dict) and "min" in param_info and "max" in param_info:
                    return (float(param_info["min"]), float(param_info["max"]))
        return (0.0, 1.0)

    def _normalize_value(self, key: str, value: float) -> float:
        """Normalize a single parameter value to [0, 1] using physical ranges.

        Args:
            key: Flattened parameter key.
            value: Raw parameter value.

        Returns:
            Normalized value in [0, 1].
        """
        if not self.normalize:
            return value
        lo, hi = self._get_range(key)
        if abs(hi - lo) < 1e-12:
            return 0.0
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))

    def compute_parameter_distance(self, pred_params, gt_params):
        """Compute RMSE between parameter sets.

        If normalize=True, parameters are min-max normalized to [0,1]
        using DSP physical ranges before computing distance.

        Args:
            pred_params: Predicted parameter dict.
            gt_params: Ground-truth parameter dict.

        Returns:
            RMSE distance (float).
        """
        v1 = self._flatten_params(pred_params)
        v2 = self._flatten_params(gt_params)

        all_keys = set(v1.keys()) | set(v2.keys())

        error_sum = 0
        count = 0

        for k in all_keys:
            val1 = v1.get(k, 0.0)
            val2 = v2.get(k, 0.0)

            if self.normalize:
                val1 = self._normalize_value(k, val1)
                val2 = self._normalize_value(k, val2)

            diff = val1 - val2
            error_sum += diff * diff
            count += 1

        if count == 0:
            return 0.0

        return math.sqrt(error_sum / count)  # RMSE

    def _flatten_params(self, params, prefix=''):
        """Recursively flatten json to float dict.

        Args:
            params: Nested parameter dict.
            prefix: Key prefix for recursion.

        Returns:
            Flat dict mapping dotted keys to float values.
        """
        flat = {}
        for k, v in params.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flat.update(self._flatten_params(v, key))
            elif isinstance(v, (int, float)):
                flat[key] = float(v)
            elif isinstance(v, str):
                try:
                    flat[key] = float(v)
                except ValueError:
                    pass
        return flat

    def evaluate_retrieval(self, retrieved_params, gt_params, k=1):
        """
        Check if retrieved params matches GT exactly (Recall@k).
        In our case, we retrieve 1 item.
        So this returns 1 if match, 0 if not.
        We check equality of the full JSON structure.
        """
        # Normalize for comparison
        s1 = json.dumps(retrieved_params, sort_keys=True)
        s2 = json.dumps(gt_params, sort_keys=True)
        return 1 if s1 == s2 else 0

    def compute_cosine_similarity(self, pred_params, gt_params):
        """Compute Cosine Similarity between parameter vectors.

        1.0 = Perfect direction match. If normalize=True, values are
        min-max normalized before computation.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)

        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())
        keys = sorted(list(all_keys))

        if self.normalize:
            vec1 = [self._normalize_value(k, v1_dict.get(k, 0.0)) for k in keys]
            vec2 = [self._normalize_value(k, v2_dict.get(k, 0.0)) for k in keys]
        else:
            vec1 = [v1_dict.get(k, 0.0) for k in keys]
            vec2 = [v2_dict.get(k, 0.0) for k in keys]

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def compute_accuracy_tolerance(self, pred_params, gt_params, tolerance=0.1):
        """Percentage of parameters within tolerance of GT.

        If normalize=True, comparison is in [0,1] space, so tolerance=0.1
        means 10% of the physical range.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)

        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())

        hit_count = 0
        total_count = 0

        for k in all_keys:
            val1 = v1_dict.get(k, 0.0)
            val2 = v2_dict.get(k, 0.0)

            if self.normalize:
                val1 = self._normalize_value(k, val1)
                val2 = self._normalize_value(k, val2)

            if abs(val1 - val2) <= tolerance:
                hit_count += 1
            total_count += 1

        if total_count == 0:
            return 0.0
        return hit_count / total_count

    def compute_max_error(self, pred_params, gt_params):
        """Largest single parameter error (L-infinity / Chebyshev).

        If normalize=True, error is computed in normalized space.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())

        max_err = 0.0
        for k in all_keys:
            val1 = v1_dict.get(k, 0.0)
            val2 = v2_dict.get(k, 0.0)

            if self.normalize:
                val1 = self._normalize_value(k, val1)
                val2 = self._normalize_value(k, val2)

            err = abs(val1 - val2)
            if err > max_err:
                max_err = err
        return max_err

    def compute_parameter_recall(self, pred_params, gt_params, threshold=0.1):
        """Recall of *Active* (Non-zero) Parameters.

        TP: GT is active (abs>active_threshold), Pred is close to GT.
        FN: GT is active, Pred is inactive or far from GT.
        If normalize=True, comparison is in normalized space.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())

        tp = 0
        fn = 0

        active_threshold = 0.05
        match_tolerance = threshold

        for k in all_keys:
            gt_val = v2_dict.get(k, 0.0)
            pred_val = v1_dict.get(k, 0.0)

            if self.normalize:
                gt_val_n = self._normalize_value(k, gt_val)
                pred_val_n = self._normalize_value(k, pred_val)
            else:
                gt_val_n = gt_val
                pred_val_n = pred_val

            if abs(gt_val_n) > active_threshold:
                if abs(pred_val_n - gt_val_n) <= match_tolerance:
                    tp += 1
                else:
                    fn += 1

        if (tp + fn) == 0:
            return 1.0

        return tp / (tp + fn)

    def compute_constraint_violation(self, pred_params, gt_params):
        """
        Invalid Rate = (Hallucinated Keys + Out-of-bounds Values) / Total Parameters

        参数对比说明：
        - 只比较 Parameters 中的数据
        - Hallucinated Keys: 预测中有但GT中没有的参数键
        - Out-of-bounds Values: 超出[0,1]范围的参数值
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)

        violations = 0
        total = 0

        for k, v in v1_dict.items():
            total += 1
            # 1. Hallucination Check: 预测的键必须在GT中存在
            if k not in v2_dict:
                violations += 1
                continue

            # 2. Bound Check: 参数值应该在[0, 1]范围内（加小容忍度）
            if abs(v) > 1.05:  # tolerance
                violations += 1

        if total == 0: return 0.0
        return violations / total

    def compute_style_consistency(self, pred_tags, gt_tags):
        """
        Jaccard Similarity of style tags.
        Input should be lists of strings locally, but here we simulate it via parameter patterns if tags missing.
        Assumption: If tags are passed directly.
        """
        s1 = set(pred_tags) if pred_tags else set()
        s2 = set(gt_tags) if gt_tags else set()

        if not s1 and not s2: return 1.0 # Both empty = match
        if not s1 or not s2: return 0.0

        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union

    def compute_module_consistency(self, pred_params, gt_params, active_threshold=0.05):
        """
        Module Consistency Score (音色模块一致性).
        衡量哪些效果器模块（如 Compressor, Delay, Reverb）被启用。

        判断逻辑：单纯看参数键名是否以"On"结尾
        - CompressorOn → Compressor开启
        - DriverOff → Driver关闭

        返回 Jaccard 相似度：|A ∩ B| / |A ∪ B|
        其中 A 是预测启用的模块集合，B 是GT启用的模块集合

        值范围：[0, 1]，1.0 表示完全一致
        """
        def get_active_modules(params):
            """获取所有启用的模块名称（只看键名是否以On结尾）"""
            active = set()
            for key in params.keys():
                if key.endswith('On'):
                    # 提取模块名（去掉On后缀）
                    module_name = key[:-2]  # 如 "CompressorOn" → "Compressor"
                    active.add(module_name)
            return active

        pred_modules = get_active_modules(pred_params)
        gt_modules = get_active_modules(gt_params)

        # Jaccard 相似度
        if not pred_modules and not gt_modules:
            return 1.0  # 两者都没有启用模块，认为一致

        intersection = len(pred_modules & gt_modules)
        union = len(pred_modules | gt_modules)

        if union == 0:
            return 1.0

        return intersection / union

if __name__ == "__main__":
    # Raw mode (backward compatible)
    ev = Evaluator()
    p1 = {"a": 10, "b": {"c": 5}}
    p2 = {"a": 12, "b": {"c": 5}}
    print("Distance (raw):", ev.compute_parameter_distance(p1, p2))
    print("Recall:", ev.evaluate_retrieval(p1, p2))

    # Normalized mode
    ev_norm = Evaluator(normalize=True)
    p3 = {"CompressorOn": {"Threshold": -50.0, "Ratio": 4.0}}
    p4 = {"CompressorOn": {"Threshold": -30.0, "Ratio": 6.0}}
    print("Distance (normalized):", ev_norm.compute_parameter_distance(p3, p4))
    print("Acc@0.1 (normalized):", ev_norm.compute_accuracy_tolerance(p3, p4))

