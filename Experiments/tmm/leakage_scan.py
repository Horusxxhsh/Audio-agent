import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.io import wavfile
from scipy.signal import stft


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_dataset(dataset_json: Path) -> List[Dict]:
    with dataset_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list.")
    return data


def _audio_fingerprint(path: Path, target_sr: int = 16000) -> np.ndarray:
    """Cheap fingerprint for near-duplicate scan using log-STFT pooling."""
    sr, x = wavfile.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x.astype(np.float32)
    # normalize
    x = x - x.mean()
    denom = np.sqrt((x * x).mean() + 1e-8)
    x = x / denom
    # naive resample by stride if needed (fast, not audiophile)
    if sr != target_sr and sr > 0:
        ratio = sr / target_sr
        idx = (np.arange(0, len(x)) / ratio).astype(np.int64)
        idx = idx[idx < len(x)]
        x = x[idx]
        sr = target_sr

    f, t, Z = stft(x, fs=sr, nperseg=512, noverlap=256, padded=False, boundary=None)
    mag = np.abs(Z).astype(np.float32)
    feat = np.log1p(mag)
    # pool over time into fixed vector
    v = feat.mean(axis=1)
    v = v / (np.linalg.norm(v) + 1e-8)
    return v


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) + 1e-8) * (np.linalg.norm(b) + 1e-8)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_json", type=str, required=True)
    ap.add_argument("--out", type=str, default="Experiments/tmm/leakage_report.json")
    ap.add_argument("--near_dup_threshold", type=float, default=0.995)
    ap.add_argument("--max_pairs", type=int, default=200)
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    out_path = (repo_root / args.out).resolve()

    data = _load_dataset(dataset_json)

    items: List[Tuple[str, Path]] = []
    for x in data:
        name = str(x.get("SongName", ""))
        apath = x.get("AudioPath")
        if not name or not apath:
            continue
        p = Path(str(apath))
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        if p.exists():
            items.append((name, p))

    hashes: Dict[str, List[str]] = {}
    for name, p in items:
        h = _sha256_file(p)
        hashes.setdefault(h, []).append(name)

    exact_dups = [names for names in hashes.values() if len(names) > 1]

    # Near-duplicates via cheap fingerprint
    feats: List[np.ndarray] = []
    for _, p in items:
        feats.append(_audio_fingerprint(p))

    near_pairs: List[Dict] = []
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            c = _cos(feats[i], feats[j])
            if c >= args.near_dup_threshold:
                near_pairs.append(
                    {
                        "a": items[i][0],
                        "b": items[j][0],
                        "cos": c,
                    }
                )
                if len(near_pairs) >= args.max_pairs:
                    break
        if len(near_pairs) >= args.max_pairs:
            break

    report = {
        "dataset_json": str(dataset_json),
        "n_items_with_audio": len(items),
        "exact_duplicate_groups": exact_dups,
        "n_exact_duplicate_groups": len(exact_dups),
        "near_duplicate_threshold": args.near_dup_threshold,
        "near_duplicate_pairs": near_pairs,
        "n_near_duplicate_pairs": len(near_pairs),
        "note": "Near-duplicate scan uses a cheap log-STFT fingerprint; upgrade to TRR/CLAP-based scan for stricter auditing.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote leakage report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

