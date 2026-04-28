#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.AblationStudies.direct_retrieval_comparison import TEST_SAMPLE_SET
from Experiments.tmm.leakage_scan import _audio_fingerprint, _cos, _resolve_audio_path


DEFAULT_DATASET_JSON = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"


def _load_dataset(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list dataset JSON, got {type(data)!r}")
    return data


def _base_name(song_name: str) -> str:
    name = str(song_name or "").strip()
    if " - " in name:
        return name.split(" - ", 1)[0].strip()
    return name


def _style_size(item: Dict) -> int:
    style = item.get("Style")
    if isinstance(style, list):
        return len(style)
    if style:
        return 1
    return 0


def _feature_size(item: Dict) -> int:
    feat = item.get("Feature")
    if isinstance(feat, list):
        return len(feat)
    if feat:
        return 1
    return 0


def _vector_coverage(item: Dict) -> Dict[str, int]:
    vectors = item.get("Vectors", {}) or {}
    return {
        "TRR": 1 if vectors.get("TRR") else 0,
        "Wav2Vec": 1 if vectors.get("Wav2Vec") else 0,
        "FeatureNN": 1 if vectors.get("FeatureNN") else 0,
        "CLAP": 1 if vectors.get("CLAP") else 0,
    }


def _cache_exists(audio_path: Optional[Path], suffix: str) -> int:
    if audio_path is None:
        return 0
    return 1 if Path(str(audio_path) + suffix).exists() else 0


def build_manifest(dataset: List[Dict], repo_root: Path) -> List[Dict]:
    rows: List[Dict] = []
    for idx, item in enumerate(dataset):
        song_name = str(item.get("SongName") or "").strip()
        split = "test" if song_name in TEST_SAMPLE_SET else "kb"
        resolved_audio = _resolve_audio_path(repo_root, item)
        vec_cov = _vector_coverage(item)
        rows.append(
            {
                "row_idx": idx,
                "song_name": song_name,
                "base_name": _base_name(song_name),
                "split": split,
                "audio_path_raw": str(item.get("AudioPath") or ""),
                "audio_path_resolved": str(resolved_audio) if resolved_audio else "",
                "audio_exists": 1 if resolved_audio else 0,
                "style_count": _style_size(item),
                "feature_count": _feature_size(item),
                "has_trr": vec_cov["TRR"],
                "has_wav2vec": vec_cov["Wav2Vec"],
                "has_featurenn": vec_cov["FeatureNN"],
                "has_clap": vec_cov["CLAP"],
                "has_clap_cache": _cache_exists(resolved_audio, ".clap.npy"),
            }
        )
    return rows


def summarize_manifest(rows: List[Dict], near_dup_threshold: float, max_near_pairs: int) -> Dict:
    by_split: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)

    test_rows = by_split.get("test", [])
    kb_rows = by_split.get("kb", [])
    total_counter = Counter(row["song_name"] for row in rows if row["song_name"])
    test_counter = Counter(row["song_name"] for row in test_rows if row["song_name"])

    test_base_names = {row["base_name"] for row in test_rows if row["base_name"]}
    kb_base_names = {row["base_name"] for row in kb_rows if row["base_name"]}
    shared_base_names = sorted(test_base_names.intersection(kb_base_names))

    def _coverage(split_rows: List[Dict], key: str) -> int:
        return int(sum(int(r[key]) for r in split_rows))

    shared_audio_paths: List[Dict] = []
    audio_to_test = defaultdict(list)
    audio_to_kb = defaultdict(list)
    for row in test_rows:
        if row["audio_path_resolved"]:
            audio_to_test[row["audio_path_resolved"]].append(row["song_name"])
    for row in kb_rows:
        if row["audio_path_resolved"]:
            audio_to_kb[row["audio_path_resolved"]].append(row["song_name"])

    for audio_path in sorted(set(audio_to_test).intersection(audio_to_kb)):
        shared_audio_paths.append(
            {
                "audio_path_resolved": audio_path,
                "test_song_names": sorted(audio_to_test[audio_path]),
                "kb_song_names": sorted(audio_to_kb[audio_path]),
            }
        )

    # Cheap near-duplicate scan across unique resolved audio files.
    unique_test_audio = sorted(set(r["audio_path_resolved"] for r in test_rows if r["audio_path_resolved"]))
    unique_kb_audio = sorted(set(r["audio_path_resolved"] for r in kb_rows if r["audio_path_resolved"]))
    near_pairs: List[Dict] = []
    if unique_test_audio and unique_kb_audio:
        feat_cache: Dict[str, object] = {}
        for audio_path in unique_test_audio + unique_kb_audio:
            if audio_path not in feat_cache:
                feat_cache[audio_path] = _audio_fingerprint(Path(audio_path))

        audio_to_names = defaultdict(list)
        for row in rows:
            if row["audio_path_resolved"]:
                audio_to_names[row["audio_path_resolved"]].append(row["song_name"])

        for test_audio in unique_test_audio:
            test_feat = feat_cache[test_audio]
            for kb_audio in unique_kb_audio:
                if test_audio == kb_audio:
                    continue
                score = _cos(test_feat, feat_cache[kb_audio])
                if score >= near_dup_threshold:
                    near_pairs.append(
                        {
                            "test_audio_path": test_audio,
                            "kb_audio_path": kb_audio,
                            "cosine": float(score),
                            "test_song_names": sorted(audio_to_names[test_audio]),
                            "kb_song_names": sorted(audio_to_names[kb_audio]),
                        }
                    )
                    if len(near_pairs) >= int(max_near_pairs):
                        break
            if len(near_pairs) >= int(max_near_pairs):
                break

    return {
        "n_total": len(rows),
        "n_test": len(test_rows),
        "n_kb": len(kb_rows),
        "n_unique_song_names_total": len(total_counter),
        "n_duplicate_song_names_total": sum(1 for _, c in total_counter.items() if c > 1),
        "n_duplicate_song_names_test": sum(1 for _, c in test_counter.items() if c > 1),
        "n_unique_base_names_test": len(test_base_names),
        "n_unique_base_names_kb": len(kb_base_names),
        "n_shared_base_names_test_kb": len(shared_base_names),
        "shared_base_names_test_kb": shared_base_names,
        "coverage": {
            "test": {
                "audio_exists": _coverage(test_rows, "audio_exists"),
                "has_trr": _coverage(test_rows, "has_trr"),
                "has_wav2vec": _coverage(test_rows, "has_wav2vec"),
                "has_featurenn": _coverage(test_rows, "has_featurenn"),
                "has_clap": _coverage(test_rows, "has_clap"),
                "has_clap_cache": _coverage(test_rows, "has_clap_cache"),
            },
            "kb": {
                "audio_exists": _coverage(kb_rows, "audio_exists"),
                "has_trr": _coverage(kb_rows, "has_trr"),
                "has_wav2vec": _coverage(kb_rows, "has_wav2vec"),
                "has_featurenn": _coverage(kb_rows, "has_featurenn"),
                "has_clap": _coverage(kb_rows, "has_clap"),
                "has_clap_cache": _coverage(kb_rows, "has_clap_cache"),
            },
        },
        "shared_resolved_audio_paths_cross_split": shared_audio_paths,
        "n_shared_resolved_audio_paths_cross_split": len(shared_audio_paths),
        "near_duplicate_threshold": float(near_dup_threshold),
        "near_duplicate_pairs_cross_split": near_pairs,
        "n_near_duplicate_pairs_cross_split": len(near_pairs),
        "selection_rule": "Protocol-A test set is defined exactly as rows whose SongName appears in direct_retrieval_comparison.TEST_SAMPLE_SET; KB is the complement.",
        "text_provenance_note": "The dataset JSON exposes SongName/Style/Feature/Parameters/Vectors but does not include a separate auditable text-source field; Style/Feature are therefore the only explicit text-side provenance fields available in-repo.",
        "parameter_provenance_note": "Ground-truth parameters are taken from the dataset JSON Parameters field as stored in the external 1267 benchmark drop-in.",
    }


def write_manifest_csv(rows: List[Dict], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "row_idx",
        "song_name",
        "base_name",
        "split",
        "audio_path_raw",
        "audio_path_resolved",
        "audio_exists",
        "style_count",
        "feature_count",
        "has_trr",
        "has_wav2vec",
        "has_featurenn",
        "has_clap",
        "has_clap_cache",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(summary: Dict, manifest_csv: Path, dataset_json: Path, out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Protocol-A Split Audit")
    lines.append("")
    lines.append(f"- Dataset JSON: `{dataset_json}`")
    lines.append(f"- Manifest CSV: `{manifest_csv}`")
    lines.append(f"- Selection rule: {summary['selection_rule']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- n_total={summary['n_total']}")
    lines.append(f"- n_test={summary['n_test']}")
    lines.append(f"- n_kb={summary['n_kb']}")
    lines.append(f"- n_duplicate_song_names_total={summary['n_duplicate_song_names_total']}")
    lines.append(f"- n_duplicate_song_names_test={summary['n_duplicate_song_names_test']}")
    lines.append(f"- n_unique_base_names_test={summary['n_unique_base_names_test']}")
    lines.append(f"- n_unique_base_names_kb={summary['n_unique_base_names_kb']}")
    lines.append(f"- n_shared_base_names_test_kb={summary['n_shared_base_names_test_kb']}")
    lines.append(f"- n_shared_resolved_audio_paths_cross_split={summary['n_shared_resolved_audio_paths_cross_split']}")
    lines.append(f"- n_near_duplicate_pairs_cross_split={summary['n_near_duplicate_pairs_cross_split']}")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Split | audio_exists | TRR | Wav2Vec | FeatureNN | CLAP(JSON) | CLAP(cache) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for split in ("test", "kb"):
        cov = summary["coverage"][split]
        lines.append(
            f"| {split} | {cov['audio_exists']} | {cov['has_trr']} | {cov['has_wav2vec']} | {cov['has_featurenn']} | {cov['has_clap']} | {cov['has_clap_cache']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(f"- Text provenance: {summary['text_provenance_note']}")
    lines.append(f"- Parameter provenance: {summary['parameter_provenance_note']}")
    if summary["shared_base_names_test_kb"]:
        preview = ", ".join(summary["shared_base_names_test_kb"][:20])
        lines.append(f"- Shared base names across test/KB (first 20): {preview}")
    if summary["shared_resolved_audio_paths_cross_split"]:
        example = summary["shared_resolved_audio_paths_cross_split"][0]
        lines.append(
            "- Example shared resolved audio path across split: "
            f"`{example['audio_path_resolved']}` with test={example['test_song_names'][:3]} and kb={example['kb_song_names'][:3]}"
        )
    if summary["near_duplicate_pairs_cross_split"]:
        example = summary["near_duplicate_pairs_cross_split"][0]
        lines.append(
            "- Example near-duplicate cross-split pair: "
            f"test={example['test_song_names'][:2]} vs kb={example['kb_song_names'][:2]} (cos={example['cosine']:.4f})"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the real Protocol-A split on the 1267 benchmark.")
    ap.add_argument("--dataset_json", type=str, default=DEFAULT_DATASET_JSON)
    ap.add_argument("--out_manifest_csv", type=str, default="Experiments/tmm/protocolA_split_manifest.csv")
    ap.add_argument("--out_json", type=str, default="Experiments/tmm/protocolA_split_audit.json")
    ap.add_argument("--out_md", type=str, default="Experiments/tmm/protocolA_split_audit.md")
    ap.add_argument("--near_dup_threshold", type=float, default=0.995)
    ap.add_argument("--max_near_pairs", type=int, default=50)
    args = ap.parse_args()

    dataset_json = (REPO_ROOT / args.dataset_json).resolve()
    dataset = _load_dataset(dataset_json)
    rows = build_manifest(dataset, REPO_ROOT)
    summary = summarize_manifest(rows, args.near_dup_threshold, args.max_near_pairs)

    manifest_csv = (REPO_ROOT / args.out_manifest_csv).resolve()
    out_json = (REPO_ROOT / args.out_json).resolve()
    out_md = (REPO_ROOT / args.out_md).resolve()

    write_manifest_csv(rows, manifest_csv)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(summary, manifest_csv, dataset_json, out_md)

    print(f"Wrote manifest CSV: {manifest_csv}")
    print(f"Wrote JSON: {out_json}")
    print(f"Wrote MD: {out_md}")


if __name__ == "__main__":
    main()
