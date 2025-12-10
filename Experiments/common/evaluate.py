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

if __name__ == "__main__":
    ev = Evaluator()
    p1 = {"a": 10, "b": {"c": 5}}
    p2 = {"a": 12, "b": {"c": 5}}
    print("Distance:", ev.compute_parameter_distance(p1, p2)) # sqrt((4+0)/2) = 1.414
    print("Recall:", ev.evaluate_retrieval(p1, p2))
