"""
MLP Regressor Baseline for Protocol-A.

Uses Wav2Vec2 mean-pooled embeddings as input to an MLP
that directly regresses flattened DSP parameters.
Trained on KB items only (no query leakage).

Usage:
    python mlp_regressor_baseline.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
from evaluate import Evaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROTOCOL_A_TEST_SIZE = 204
PROTOCOL_A_SEED = 42


def flatten_params(params: Dict, prefix: str = "") -> Dict[str, float]:
    """Recursively flatten nested parameter dict to float dict."""
    flat: Dict[str, float] = {}
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            flat.update(flatten_params(v, key))
        elif isinstance(v, (int, float)):
            flat[key] = float(v)
        elif isinstance(v, str):
            try:
                flat[key] = float(v)
            except ValueError:
                pass
    return flat


def prepare_data(
    dataset: List[Dict],
    test_size: int = PROTOCOL_A_TEST_SIZE,
    seed: int = PROTOCOL_A_SEED,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Prepare train/test data from dataset.

    Args:
        dataset: Full dataset list.

    Returns:
        (X_train, y_train, X_test, y_test, param_keys) tuple.
    """
    # Collect all parameter keys from the full dataset
    all_keys: set = set()
    for item in dataset:
        flat = flatten_params(item.get("Parameters", {}))
        all_keys.update(flat.keys())
    param_keys = sorted(all_keys)

    X_list = []
    y_list = []
    vector_dims: Dict[int, int] = {}
    for item in dataset:
        vec = item.get("Vectors", {}).get("Wav2Vec")
        if not isinstance(vec, list) or not vec:
            X_list.append(None)
            y_list.append(None)
            continue
        arr = np.array(vec, dtype=np.float32)
        vector_dims[int(arr.shape[0])] = vector_dims.get(int(arr.shape[0]), 0) + 1
        X_list.append(arr)
        flat = flatten_params(item.get("Parameters", {}))
        y_vec = np.array([flat.get(k, 0.0) for k in param_keys], dtype=np.float32)
        y_list.append(y_vec)

    # Split Protocol-A using the same deterministic hash split as P0 E2.
    indexed = []
    for idx, item in enumerate(dataset):
        name = str(item.get("SongName", ""))
        h = hashlib.sha1(f"{int(seed)}:{name}".encode("utf-8")).hexdigest()
        indexed.append((h, idx))
    indexed.sort(key=lambda x: x[0])
    n = len(indexed)
    ts = min(max(1, int(test_size)), max(1, n // 3), n - 1) if n > 1 else 1
    test_indices = [idx for _, idx in indexed[:ts]]
    train_indices = [idx for _, idx in indexed[ts:]]

    if not vector_dims:
        raise ValueError("No non-empty Wav2Vec vectors found.")
    dominant_dim = max(vector_dims.items(), key=lambda kv: kv[1])[0]

    def usable(i: int) -> bool:
        return (
            X_list[i] is not None
            and y_list[i] is not None
            and int(X_list[i].shape[0]) == int(dominant_dim)
        )

    train_usable = [i for i in train_indices if usable(i)]
    test_usable = [i for i in test_indices if usable(i)]
    X_train = np.stack([X_list[i] for i in train_usable])
    y_train = np.stack([y_list[i] for i in train_usable])
    X_test = np.stack([X_list[i] for i in test_usable])
    y_test = np.stack([y_list[i] for i in test_usable])

    logger.info(f"Train: {X_train.shape}, Test: {X_test.shape}")
    logger.info(f"Dominant Wav2Vec dim: {dominant_dim}; vector dim counts: {vector_dims}")
    logger.info(f"Parameter dimension: {len(param_keys)}")

    return X_train, y_train, X_test, y_test, param_keys


class SimpleMLPRegressor:
    """Minimal 2-layer MLP regressor using numpy (no PyTorch dependency).

    For a production version, use sklearn.neural_network.MLPRegressor
    or a PyTorch module.
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, lr: float = 0.001):
        self.lr = lr
        # Xavier initialization
        scale1 = np.sqrt(2.0 / input_dim)
        self.W1 = np.random.randn(input_dim, hidden_dim).astype(np.float32) * scale1
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        scale2 = np.sqrt(2.0 / hidden_dim)
        self.W2 = np.random.randn(hidden_dim, output_dim).astype(np.float32) * scale2
        self.b2 = np.zeros(output_dim, dtype=np.float32)

    def forward(self, X: np.ndarray) -> np.ndarray:
        """Forward pass with ReLU activation."""
        self.z1 = X @ self.W1 + self.b1
        self.a1 = np.maximum(0, self.z1)  # ReLU
        self.z2 = self.a1 @ self.W2 + self.b2
        return self.z2

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, batch_size: int = 32):
        """Train with mini-batch SGD."""
        n = X.shape[0]
        for epoch in range(epochs):
            indices = np.random.permutation(n)
            epoch_loss = 0.0
            n_batches = 0
            for start in range(0, n, batch_size):
                batch_idx = indices[start:start + batch_size]
                X_b = X[batch_idx]
                y_b = y[batch_idx]

                # Forward
                pred = self.forward(X_b)
                loss = np.mean((pred - y_b) ** 2)
                epoch_loss += loss
                n_batches += 1

                # Backward
                bs = X_b.shape[0]
                d_z2 = 2.0 * (pred - y_b) / bs
                d_W2 = self.a1.T @ d_z2
                d_b2 = d_z2.sum(axis=0)
                d_a1 = d_z2 @ self.W2.T
                d_z1 = d_a1 * (self.z1 > 0).astype(np.float32)
                d_W1 = X_b.T @ d_z1
                d_b1 = d_z1.sum(axis=0)

                # Update
                self.W2 -= self.lr * d_W2
                self.b2 -= self.lr * d_b2
                self.W1 -= self.lr * d_W1
                self.b1 -= self.lr * d_b1

            if (epoch + 1) % 20 == 0:
                logger.info(f"  Epoch {epoch + 1}/{epochs}, MSE: {epoch_loss / n_batches:.6f}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict parameters for input embeddings."""
        return self.forward(X)


def unflatten_params(values: np.ndarray, keys: List[str]) -> Dict:
    """Convert flat parameter array back to nested dict."""
    result: Dict = {}
    for key, val in zip(keys, values):
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = float(val)
    return result


def run_mlp_baseline(dataset_path: str, output_dir: str, test_size: int, seed: int) -> Dict:
    """Run MLP regressor baseline experiment.

    Args:
        dataset_path: Path to dataset JSON.
        output_dir: Output directory for results.

    Returns:
        Results dict with metrics.
    """
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    np.random.seed(int(seed))
    X_train, y_train, X_test, y_test, param_keys = prepare_data(dataset, test_size=test_size, seed=seed)
    x_mean = X_train.mean(axis=0, keepdims=True)
    x_std = X_train.std(axis=0, keepdims=True) + 1e-6
    y_mean = y_train.mean(axis=0, keepdims=True)
    y_std = y_train.std(axis=0, keepdims=True) + 1e-6
    X_train_s = (X_train - x_mean) / x_std
    X_test_s = (X_test - x_mean) / x_std
    y_train_s = (y_train - y_mean) / y_std

    # Train MLP
    input_dim = X_train_s.shape[1]
    output_dim = y_train.shape[1]
    hidden_dim = 256

    logger.info(f"Training MLP: {input_dim} -> {hidden_dim} -> {output_dim}")
    mlp = SimpleMLPRegressor(input_dim, hidden_dim, output_dim, lr=0.0005)
    mlp.train(X_train_s, y_train_s, epochs=200, batch_size=32)

    # Evaluate direct predictions and a minimal validity-projected variant.
    # The projection clamps each numeric parameter to the train-set observed range.
    y_pred_s = mlp.predict(X_test_s)
    y_pred = y_pred_s * y_std + y_mean
    y_min = y_train.min(axis=0, keepdims=True)
    y_max = y_train.max(axis=0, keepdims=True)
    y_pred_projected = np.clip(y_pred, y_min, y_max)

    evaluator_raw = Evaluator(normalize=False)
    evaluator_norm = Evaluator(normalize=True)

    def evaluate_array(pred_array: np.ndarray) -> Dict[str, List[float]]:
        metrics = {"l2_raw": [], "l2_norm": [], "acc_at_01": [], "cosine": [], "recall": [], "module": []}

        for i in range(len(pred_array)):
            pred_dict = unflatten_params(pred_array[i], param_keys)
            gt_dict = unflatten_params(y_test[i], param_keys)

            metrics["l2_raw"].append(evaluator_raw.compute_parameter_distance(pred_dict, gt_dict))
            metrics["l2_norm"].append(evaluator_norm.compute_parameter_distance(pred_dict, gt_dict))
            metrics["acc_at_01"].append(evaluator_norm.compute_accuracy_tolerance(pred_dict, gt_dict))
            metrics["cosine"].append(evaluator_raw.compute_cosine_similarity(pred_dict, gt_dict))
            metrics["recall"].append(evaluator_raw.compute_parameter_recall(pred_dict, gt_dict))
            metrics["module"].append(evaluator_raw.compute_module_consistency(pred_dict, gt_dict))
        return metrics

    metrics = evaluate_array(y_pred)
    projected_metrics = evaluate_array(y_pred_projected)

    avg_metrics = {k: float(np.mean(v)) for k, v in metrics.items()}
    std_metrics = {f"{k}_std": float(np.std(v)) for k, v in metrics.items()}
    projected_avg_metrics = {k: float(np.mean(v)) for k, v in projected_metrics.items()}
    projected_std_metrics = {f"{k}_std": float(np.std(v)) for k, v in projected_metrics.items()}

    results = {
        "method": "MLP-Regressor",
        "description": "Wav2Vec2 mean-pooled -> 2-layer MLP -> direct parameter regression",
        "train_size": int(X_train.shape[0]),
        "test_size": int(X_test.shape[0]),
        "hidden_dim": hidden_dim,
        "seed": int(seed),
        "split": {"test_size_requested": int(test_size), "protocol": "P0 deterministic hash split"},
        "metrics": {**avg_metrics, **std_metrics},
        "projected_method": "MLP-Regressor+RangeProjection",
        "projection": "Per-parameter clipping to the train-set observed numeric range.",
        "projected_metrics": {**projected_avg_metrics, **projected_std_metrics},
    }

    # Save
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "mlp_regressor_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"MLP-Regressor results: {avg_metrics}")
    logger.info(f"MLP-Regressor+RangeProjection results: {projected_avg_metrics}")
    return results


def main() -> None:
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="MLP Regressor Baseline")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent / "results"))
    parser.add_argument("--test-size", type=int, default=PROTOCOL_A_TEST_SIZE)
    parser.add_argument("--seed", type=int, default=PROTOCOL_A_SEED)
    args = parser.parse_args()

    run_mlp_baseline(args.dataset, args.output_dir, test_size=args.test_size, seed=args.seed)


if __name__ == "__main__":
    main()
