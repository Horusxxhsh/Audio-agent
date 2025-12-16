import json
import math

class Evaluator:
    def __init__(self):
        pass

    def compute_parameter_distance(self, pred_params, gt_params):
        """
        Compute normalized Euclidean distance between parameter sets.
        We flatten the JSON objects to numerical vectors.
        """
        # Flatten
        v1 = self._flatten_params(pred_params)
        v2 = self._flatten_params(gt_params)
        
        # Get union of keys
        all_keys = set(v1.keys()) | set(v2.keys())
        
        error_sum = 0
        count = 0
        
        for k in all_keys:
            val1 = v1.get(k, 0.0) # Assume 0 if missing (not ideal but consistent)
            val2 = v2.get(k, 0.0)
            
            # Simple difference, normalized??
            # Since we don't know the range of each param, we just take raw diff
            # In a real system, we'd use metadata to normalize to [0,1]
            diff = val1 - val2
            error_sum += diff * diff
            count += 1
            
        if count == 0:
            return 0.0
            
        return math.sqrt(error_sum / count) # RMSE

    def _flatten_params(self, params, prefix=''):
        """
        Recursively flatten json to float dict.
        Non-numeric leaves are ignored.
        """
        flat = {}
        for k, v in params.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flat.update(self._flatten_params(v, key))
            elif isinstance(v, (int, float)):
                flat[key] = float(v)
            # Ignore strings/bools for distance metric for now
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
        """
        Compute Cosine Similarity between parameter vectors.
        1.0 = Perfect direction match (relative ratios are correct).
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())
        keys = sorted(list(all_keys)) # Ensure order
        
        vec1 = [v1_dict.get(k, 0.0) for k in keys]
        vec2 = [v2_dict.get(k, 0.0) for k in keys]
        
        dot_product = sum(a*b for a,b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a*a for a in vec1))
        norm2 = math.sqrt(sum(a*a for a in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)

    def compute_accuracy_tolerance(self, pred_params, gt_params, tolerance=0.1):
        """
        Percentage of parameters that are within 'tolerance' (e.g. 0.1) of GT.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())
        
        hit_count = 0
        total_count = 0
        
        for k in all_keys:
            val1 = v1_dict.get(k, 0.0)
            val2 = v2_dict.get(k, 0.0)
            if abs(val1 - val2) <= tolerance:
                hit_count += 1
            total_count += 1
            
        if total_count == 0: return 0.0
        return hit_count / total_count

    def compute_max_error(self, pred_params, gt_params):
        """
        The largest single parameter error (Chebyshev distance / L-infinity).
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())
        
        max_err = 0.0
        for k in all_keys:
            val1 = v1_dict.get(k, 0.0)
            val2 = v2_dict.get(k, 0.0)
            err = abs(val1 - val2)
            if err > max_err:
                max_err = err
        return max_err

    def compute_parameter_recall(self, pred_params, gt_params, threshold=0.1):
        """
        Recall of *Active* (Non-zero) Parameters.
        Measures: Of the effects that SHOULD be active, how many did we activate correctly?
        
        TP: GT is active (abs>0), Pred is active AND close to GT.
        FN: GT is active, Pred is inactive OR far from GT.
        """
        v1_dict = self._flatten_params(pred_params)
        v2_dict = self._flatten_params(gt_params)
        all_keys = set(v1_dict.keys()) | set(v2_dict.keys())
        
        tp = 0
        fn = 0
        
        active_threshold = 0.05 # What counts as "Active" in GT?
        match_tolerance = threshold # How close must Pred be to count as a Hit?
        
        for k in all_keys:
            gt_val = v2_dict.get(k, 0.0)
            pred_val = v1_dict.get(k, 0.0)
            
            if abs(gt_val) > active_threshold:
                # This parameter matters (it's active in GT)
                if abs(pred_val - gt_val) <= match_tolerance:
                    tp += 1
                else:
                    fn += 1
        
        if (tp + fn) == 0:
            return 1.0 # No active parameters to recall, perfect score trivially
            
        return tp / (tp + fn)

if __name__ == "__main__":
    ev = Evaluator()
    p1 = {"a": 10, "b": {"c": 5}}
    p2 = {"a": 12, "b": {"c": 5}}
    print("Distance:", ev.compute_parameter_distance(p1, p2)) # sqrt((4+0)/2) = 1.414
    print("Recall:", ev.evaluate_retrieval(p1, p2))
