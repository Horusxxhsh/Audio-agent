from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import ntpath
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/vector_prep"
DEFAULT_METHODS = {"TRR": "TRR", "Wav2Vec": "Wav2Vec", "FeatureNN": "FeatureNN", "CLAP": "CLAP", "PaSST": "PaSST", "PANNs": "PANNs"}
REQUIRED_OPTIONAL_DEPS = {
    "soundfile": "soundfile",
    "torchaudio": "torchaudio",
    "hear21passt": "hear21passt",
    "panns_inference": "panns_inference",
}
MANUAL_AUDIO_ALIASES = {
    "Math Rock Crystal Cleans": "Math Rock Crystal.wav",
    "Vintage Tweed Breakup": "Tweed Breakup.wav",
    "Dry Funk Rhythm": "Dry Funk.wav",
    "Saturated Drive Rhythm": "Saturated Rhythm.wav",
    "Reverse Psychedelic Delay": "Reverse Psychedelic.wav",
    "80s Hair Metal Arena": "80s Hair Metal.wav",
    "Acoustic Sim Natural": "Acoustic Sim.wav",
    "Auto-Wah Funk Rhythm": "Auto-Wah Funk.wav",
    "Brian May Queen Tone": "Brian May Style.wav",
    "Brown Sound Modern": "Brown Sound.wav",
    "Plexi Classic Hot": "Classic Plexi.wav",
    "Dreamy Shoegaze Ethereal": "Dreamy Shoegaze.wav",
    "Hard Rock Crunch": "Hard Crunch Rock.wav",
    "Jazz Hollowbody Warm": "Hollow Body Jazz.wav",
    "Lo-Fi Hip Hop Chill": "Lo-Fi Hip Hop.wav",
    "Punk Rock Raw Energy": "Punk Rock Raw.wav",
    "Rotary Speaker Fast": "Rotary Speaker.wav",
    "Texas Blues Warm": "Texas Blues.wav",
    "Touch Sensitive Lead Smooth": "Touch Sensitive Lead.wav",
}


def _ascii_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"dataset must be a JSON array: {path}")
    return data


def _has_vector(item: Mapping[str, object], key: str) -> bool:
    vectors = item.get("Vectors", {})
    if not isinstance(vectors, Mapping):
        return False
    vec = vectors.get(key)
    return isinstance(vec, list) and len(vec) > 0


def build_audio_basename_index(directories: Sequence[Path] | None = None) -> dict[str, Path]:
    """Index audio files by basename, including Windows-style dataset paths."""
    roots = list(directories or [REPO_ROOT / "Data" / "Audio_Synthetic", REPO_ROOT / "musiccaps_guitar_solo", REPO_ROOT / "Sounds", REPO_ROOT / "Assets"])
    index: dict[str, Path] = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                index.setdefault(path.name.lower(), path.resolve())
                index.setdefault(_ascii_key(path.name), path.resolve())
    return index


def _path_basename(path: str) -> str:
    return ntpath.basename(path) or Path(path).name


def resolve_audio_path_for_item(item: Mapping[str, object], basename_index: Mapping[str, Path]) -> Path | None:
    original = str(item.get("AudioPath", ""))
    if original:
        direct = Path(original)
        if direct.exists():
            return direct.resolve()
        for basename in (_path_basename(original).lower(), _ascii_key(_path_basename(original))):
            if basename in basename_index:
                return Path(basename_index[basename]).resolve()
    song_name = str(item.get("SongName", ""))
    alias = MANUAL_AUDIO_ALIASES.get(song_name)
    if alias:
        for key in (alias.lower(), _ascii_key(alias)):
            if key in basename_index:
                return Path(basename_index[key]).resolve()
    if song_name:
        for suffix in (".wav", ".mp3", ".flac", ".ogg"):
            for candidate in (f"{song_name}{suffix}".lower(), _ascii_key(f"{song_name}{suffix}")):
                if candidate in basename_index:
                    return Path(basename_index[candidate]).resolve()
    return None


def audio_coverage_report(dataset: Sequence[Mapping[str, object]], basename_index: Mapping[str, Path]) -> dict[str, object]:
    missing = []
    for idx, item in enumerate(dataset):
        resolved = resolve_audio_path_for_item(item, basename_index)
        if resolved is None:
            missing.append({"idx": int(idx), "song_name": str(item.get("SongName", "")), "audio_path": str(item.get("AudioPath", ""))})
    return {
        "total": len(dataset),
        "resolved": len(dataset) - len(missing),
        "missing": len(missing),
        "missing_items": missing,
        "ready": len(missing) == 0,
    }


def dependency_status(modules: Sequence[str] | None = None) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for module in modules or list(REQUIRED_OPTIONAL_DEPS):
        spec = importlib.util.find_spec(module)
        if spec is None:
            result[module] = {"available": False, "error": "ModuleNotFoundError"}
            continue
        if module == "panns_inference":
            # Importing panns_inference has runtime side effects: it expects
            # AudioSet label files under ~/panns_data and may shell out to wget.
            # Treat package discovery as dependency availability; actual encoder
            # resource checks are recorded separately by the vector-fill step.
            result[module] = {"available": True, "version": "installed"}
            continue
        try:
            imported = importlib.import_module(module)
        except Exception as exc:  # dependency probes must not crash the evidence run
            result[module] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
            continue
        result[module] = {"available": True, "version": str(getattr(imported, "__version__", ""))}
    return result


def _query_index_set(query_indices: Sequence[int]) -> set[int]:
    return {int(idx) for idx in query_indices}


def coverage_report(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    methods: Mapping[str, str] | None = None,
) -> dict[str, object]:
    methods = methods or DEFAULT_METHODS
    qset = _query_index_set(query_indices)
    kb_indices = [idx for idx in range(len(dataset)) if idx not in qset]
    report: dict[str, object] = {
        "query_count": len(qset),
        "kb_count": len(kb_indices),
        "methods": {},
        "ready": True,
    }
    method_report = {}
    for method, vector_key in methods.items():
        query_ok = sum(1 for idx in qset if 0 <= idx < len(dataset) and _has_vector(dataset[idx], vector_key))
        kb_ok = sum(1 for idx in kb_indices if _has_vector(dataset[idx], vector_key))
        ready = query_ok == len(qset) and kb_ok == len(kb_indices)
        method_report[method] = {
            "vector_key": vector_key,
            "query_ok": int(query_ok),
            "query_total": int(len(qset)),
            "kb_ok": int(kb_ok),
            "kb_total": int(len(kb_indices)),
            "ready": bool(ready),
        }
        report["ready"] = bool(report["ready"] and ready)
    report["methods"] = method_report
    return report


def write_blocker_report(output_dir: Path, dep_status: Mapping[str, Mapping[str, object]], context: Mapping[str, object] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    missing = sorted(name for name, status in dep_status.items() if not bool(status.get("available")))
    payload = {
        "status": "blocked",
        "reason": "missing_optional_sota_vector_dependencies",
        "missing_dependencies": missing,
        "dependencies": dep_status,
        "context": dict(context or {}),
    }
    path = output_dir / "sota_vector_blocker.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_dataset_with_manifest(dataset_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "dataset_full_vectors_1267_augmented.json"
    shutil.copy2(dataset_path, out_path)
    manifest = {
        "source_dataset": str(dataset_path),
        "augmented_dataset": str(out_path),
        "sha256": _sha256(out_path),
        "note": "This file is a derived copy. PaSST/PANNs vectors are added only by a successful optional encoder run.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare derived SOTA-vector dataset for TMM major revision.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split-file", default="Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt")
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--coverage-only", action="store_true", help="Refresh audio/vector coverage reports without dependency checks or dataset copying.")
    parser.add_argument("--check-deps-only", action="store_true")
    args = parser.parse_args()

    from Experiments.E7_HardSplit.run_hard_split_retrieval import load_requested_query_indices

    output_dir = Path(args.output_dir)
    dataset_path = Path(args.dataset)
    dataset = load_dataset(dataset_path)
    query_indices = load_requested_query_indices(dataset, Path(args.split_file))
    deps = dependency_status()
    coverage = coverage_report(dataset, query_indices)
    audio_index = build_audio_basename_index()
    audio_coverage = audio_coverage_report(dataset, audio_index)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vector_coverage.json").write_text(json.dumps(coverage, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "audio_coverage.json").write_text(json.dumps(audio_coverage, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if args.coverage_only:
        print(f"wrote coverage reports under {output_dir}")
        return 0

    if not all(status.get("available") for status in deps.values()):
        path = write_blocker_report(output_dir, deps, {"dataset": str(dataset_path), "split_file": str(args.split_file)})
        print(f"blocked: wrote {path}")
        return 2
    if args.check_deps_only:
        print("optional SOTA dependencies available")
        return 0

    out_dataset = copy_dataset_with_manifest(dataset_path, output_dir)
    print(f"wrote derived dataset copy: {out_dataset}")
    print("PaSST/PANNs encoder execution is intentionally explicit; run the legacy fill script against this derived copy after dependency setup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
