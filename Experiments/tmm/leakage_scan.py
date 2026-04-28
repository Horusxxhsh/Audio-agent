import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def _read_split_names(seed_dir: Path) -> Dict[str, List[str]]:
    def _read(path: Path) -> List[str]:
        if not path.exists():
            return []
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
        return [x for x in lines if x]

    return {
        "train": _read(seed_dir / "train.txt"),
        "val": _read(seed_dir / "val.txt"),
        "test": _read(seed_dir / "test.txt"),
    }


def _resolve_audio_path(repo_root: Path, item: Dict) -> Optional[Path]:
    song_name = str(item.get("SongName", "")).strip()
    cur = item.get("AudioPath")
    base_audio_dir = repo_root / "Data" / "Audio_Synthetic"

    candidates: List[Path] = []
    if isinstance(cur, str) and cur:
        raw_path = Path(cur)
        if raw_path.is_absolute() and raw_path.exists():
            candidates.append(raw_path)
        else:
            candidates.append((repo_root / raw_path).resolve())
            base = cur.replace("\\", "/").split("/")[-1]
            if base.lower().endswith(".wav"):
                candidates.append((base_audio_dir / base).resolve())

    def _sanitize(name: str) -> str:
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in (" ", "-", "_")]).strip()

    if song_name:
        candidates.append((base_audio_dir / f"{_sanitize(song_name)}.wav").resolve())
        candidates.append((base_audio_dir / f"{song_name}.wav").resolve())
        if " - " in song_name:
            base_name = song_name.split(" - ", 1)[0].strip()
            candidates.append((base_audio_dir / f"{_sanitize(base_name)}.wav").resolve())
            candidates.append((base_audio_dir / f"{base_name}.wav").resolve())

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return None


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


def scan_split_leakage(
    *,
    dataset_json: Path,
    split_root: Path,
    near_dup_threshold: float,
    max_pairs: int,
) -> Dict:
    repo_root = Path(__file__).resolve().parents[2]
    data = _load_dataset(dataset_json)

    items: List[Tuple[str, Path]] = []
    for x in data:
        name = str(x.get("SongName", "")).strip()
        if not name:
            continue
        resolved = _resolve_audio_path(repo_root, x)
        if resolved is not None:
            items.append((name, resolved))

    name_to_path = {name: path for name, path in items}
    name_to_hash = {name: _sha256_file(path) for name, path in items}
    name_to_feat = {name: _audio_fingerprint(path) for name, path in items}

    split_reports: Dict[str, Dict] = {}
    for seed_dir in sorted([p for p in split_root.iterdir() if p.is_dir()]):
        split_names = _read_split_names(seed_dir)
        memberships: Dict[str, str] = {}
        for split_name, names in split_names.items():
            for name in names:
                memberships[name] = split_name

        exact_pairs: List[Dict] = []
        near_pairs: List[Dict] = []
        names = [name for name in memberships if name in name_to_path]

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = names[i]
                b = names[j]
                split_a = memberships[a]
                split_b = memberships[b]
                if split_a == split_b:
                    continue

                if name_to_hash[a] == name_to_hash[b]:
                    exact_pairs.append(
                        {"a": a, "b": b, "split_a": split_a, "split_b": split_b}
                    )

                c = _cos(name_to_feat[a], name_to_feat[b])
                if c >= near_dup_threshold:
                    near_pairs.append(
                        {
                            "a": a,
                            "b": b,
                            "split_a": split_a,
                            "split_b": split_b,
                            "cos": c,
                        }
                    )
                if len(near_pairs) >= max_pairs:
                    break
            if len(near_pairs) >= max_pairs:
                break

        split_reports[seed_dir.name] = {
            "n_named_items": len(memberships),
            "n_items_with_audio": len(names),
            "exact_cross_split_pairs": exact_pairs,
            "near_cross_split_pairs": near_pairs,
            "n_exact_cross_split_pairs": len(exact_pairs),
            "n_near_cross_split_pairs": len(near_pairs),
        }

    return {
        "dataset_json": str(dataset_json),
        "split_root": str(split_root),
        "n_items_with_audio": len(items),
        "near_duplicate_threshold": near_dup_threshold,
        "split_reports": split_reports,
        "note": "Near-duplicate scan uses a cheap log-STFT fingerprint; upgrade to TRR/CLAP-based scan for stricter auditing.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_json", type=str, required=True)
    ap.add_argument("--out", type=str, default="Experiments/tmm/leakage_report.json")
    ap.add_argument("--near_dup_threshold", type=float, default=0.995)
    ap.add_argument("--max_pairs", type=int, default=200)
    ap.add_argument("--split_root", type=str, default="", help="Optional split root to report cross-split leakage by seed.")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    out_path = (repo_root / args.out).resolve()

    data = _load_dataset(dataset_json)

    items: List[Tuple[str, Path]] = []
    for x in data:
        name = str(x.get("SongName", ""))
        if not name:
            continue
        p = _resolve_audio_path(repo_root, x)
        if p is not None:
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
    if args.split_root:
        split_root = (repo_root / args.split_root).resolve()
        report.update(
            scan_split_leakage(
                dataset_json=dataset_json,
                split_root=split_root,
                near_dup_threshold=args.near_dup_threshold,
                max_pairs=args.max_pairs,
            )
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote leakage report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
