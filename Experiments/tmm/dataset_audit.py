import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.io import wavfile


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_audio_path(repo_root: Path, p: Optional[str]) -> Optional[Path]:
    if not p:
        return None
    path = Path(str(p))
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def resolve_audio_path_for_item(repo_root: Path, item: Dict) -> Optional[Path]:
    song_name = str(item.get("SongName", "")).strip()
    cur = item.get("AudioPath")
    base_audio_dir = repo_root / "Data" / "Audio_Synthetic"

    candidates: List[Path] = []
    resolved_raw = _resolve_audio_path(repo_root, cur)
    if resolved_raw is not None:
        candidates.append(resolved_raw)

    if isinstance(cur, str) and cur:
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


@dataclass(frozen=True)
class AudioInfo:
    sr: int
    n_samples: int
    seconds: float
    peak_dbfs: float
    rms_dbfs: float


def _read_audio_info(path: Path) -> Optional[AudioInfo]:
    try:
        sr, x = wavfile.read(str(path))
        if hasattr(x, "ndim") and x.ndim > 1:
            x = x.mean(axis=1)
        x = np.asarray(x)
        if np.issubdtype(x.dtype, np.integer):
            maxv = float(np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / (maxv if maxv > 0 else 1.0)
        else:
            x = x.astype(np.float32)
        n = int(x.shape[0]) if hasattr(x, "shape") else 0
        sec = float(n / sr) if sr and n else 0.0
        peak = float(np.max(np.abs(x))) if n else 0.0
        rms = float(np.sqrt(np.mean(x * x))) if n else 0.0
        peak_dbfs = 20.0 * float(np.log10(peak + 1e-12))
        rms_dbfs = 20.0 * float(np.log10(rms + 1e-12))
        return AudioInfo(
            sr=int(sr),
            n_samples=n,
            seconds=sec,
            peak_dbfs=peak_dbfs,
            rms_dbfs=rms_dbfs,
        )
    except Exception:
        return None


def _summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"count": 0}
    a = np.array(values, dtype=np.float64)
    return {
        "count": int(a.size),
        "min": float(np.min(a)),
        "p10": float(np.quantile(a, 0.10)),
        "median": float(np.quantile(a, 0.50)),
        "mean": float(np.mean(a)),
        "p90": float(np.quantile(a, 0.90)),
        "max": float(np.max(a)),
    }


def _read_split(path: Path) -> List[str]:
    if not path.exists():
        return []
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    return [x for x in lines if x]


def _check_disjoint(a: List[str], b: List[str]) -> List[str]:
    sa = set(a)
    sb = set(b)
    return sorted(list(sa.intersection(sb)))


def audit_dataset(dataset_json: Path, split_root: Optional[Path]) -> Dict:
    repo_root = Path(__file__).resolve().parents[2]
    data = _load_json(dataset_json)
    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list.")

    required_fields = ["SongName", "Parameters", "Style", "Feature"]
    n_total = len(data)
    missing_fields: Dict[str, int] = {k: 0 for k in required_fields}

    names: List[str] = []
    audio_paths: List[Tuple[str, Path]] = []

    for item in data:
        if not isinstance(item, dict):
            continue
        for k in required_fields:
            if k not in item:
                missing_fields[k] += 1
        name = str(item.get("SongName", ""))
        if name:
            names.append(name)
        apath = resolve_audio_path_for_item(repo_root, item)
        if name and apath and apath.exists():
            audio_paths.append((name, apath))

    unique_names = len(set(names))
    dup_names = n_total - unique_names

    seconds: List[float] = []
    sample_rates: List[int] = []
    peaks_dbfs: List[float] = []
    rms_dbfs: List[float] = []
    missing_audio: List[str] = []
    unreadable_audio: List[str] = []
    silent_audio: List[str] = []
    clipped_audio: List[str] = []

    for name, apath in audio_paths:
        info = _read_audio_info(apath)
        if info is None:
            unreadable_audio.append(name)
            continue
        seconds.append(info.seconds)
        sample_rates.append(info.sr)
        peaks_dbfs.append(info.peak_dbfs)
        rms_dbfs.append(info.rms_dbfs)
        # Heuristics: flag very low energy (likely silence) and near-full-scale peaks (likely clipping).
        if info.rms_dbfs < -80.0:
            silent_audio.append(name)
        if info.peak_dbfs > -0.1:
            clipped_audio.append(name)

    # items with missing audio path or missing file
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("SongName", ""))
        apath = resolve_audio_path_for_item(repo_root, item)
        if not name:
            continue
        if apath is None or not apath.exists():
            missing_audio.append(name)

    report: Dict = {
        "dataset_json": str(dataset_json),
        "n_total_items": n_total,
        "n_unique_song_names": unique_names,
        "n_duplicate_song_names": dup_names,
        "missing_field_counts": missing_fields,
        "n_items_with_existing_audio": len(audio_paths),
        "n_items_missing_audio": len(missing_audio),
        "n_unreadable_audio": len(unreadable_audio),
        "audio_seconds_summary": _summarize(seconds),
        "audio_sample_rate_summary": _summarize([float(x) for x in sample_rates]),
        "audio_peak_dbfs_summary": _summarize(peaks_dbfs),
        "audio_rms_dbfs_summary": _summarize(rms_dbfs),
        "n_silent_audio": len(silent_audio),
        "silent_audio_examples": silent_audio[:20],
        "n_clipped_audio": len(clipped_audio),
        "clipped_audio_examples": clipped_audio[:20],
        "audio_missing_examples": missing_audio[:20],
        "audio_unreadable_examples": unreadable_audio[:20],
    }

    if split_root is not None and split_root.exists():
        split_report = {}
        dataset_set: Set[str] = set(names)
        for seed_dir in sorted([p for p in split_root.iterdir() if p.is_dir()]):
            train = _read_split(seed_dir / "train.txt")
            val = _read_split(seed_dir / "val.txt")
            test = _read_split(seed_dir / "test.txt")

            overlap_tv = _check_disjoint(train, val)
            overlap_tt = _check_disjoint(train, test)
            overlap_vt = _check_disjoint(val, test)

            unknown = sorted(list((set(train) | set(val) | set(test)) - dataset_set))

            split_report[seed_dir.name] = {
                "n_train": len(train),
                "n_val": len(val),
                "n_test": len(test),
                "overlap_train_val": overlap_tv[:20],
                "overlap_train_test": overlap_tt[:20],
                "overlap_val_test": overlap_vt[:20],
                "n_unknown_names": len(unknown),
                "unknown_name_examples": unknown[:20],
            }
        report["splits"] = split_report

    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_json", type=str, required=True)
    ap.add_argument("--split_root", type=str, default="")
    ap.add_argument("--out", type=str, default="Experiments/tmm/dataset_audit_report.json")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    split_root = (repo_root / args.split_root).resolve() if args.split_root else None
    out_path = (repo_root / args.out).resolve()

    report = audit_dataset(dataset_json, split_root=split_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote audit report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
