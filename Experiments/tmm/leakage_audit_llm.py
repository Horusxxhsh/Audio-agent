#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.dataset_loader import load_and_merge_data


def _normalize_text(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _load_test_name_set(test_list: str) -> Set[str]:
    if test_list:
        p = Path(test_list)
        if not p.exists():
            raise FileNotFoundError(f"--test_list not found: {p}")
        out: List[str] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            out.append(s)
        return set(out)

    # Default: reuse Protocol-A/B held-out list from direct_retrieval_comparison.py.
    try:
        from Experiments.AblationStudies.direct_retrieval_comparison import TEST_SAMPLE_SET  # type: ignore

        return set(TEST_SAMPLE_SET)
    except Exception:
        # Conservative fallback: empty => audit cannot be trusted.
        return set()


@dataclass(frozen=True)
class LeakageAuditReport:
    n_total_records: int
    n_test_records: int
    n_test_unique_song_names: int
    fewshot_texts: List[str]
    n_fewshot_texts: int
    overlap_song_names: List[str]
    overlap_audio_paths: List[str]
    overlap_texts: List[str]


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit prompt/few-shot leakage against held-out queries (Protocol-B).")
    ap.add_argument("--test_list", type=str, default="", help="Optional held-out SongName list (newline-separated).")
    ap.add_argument("--out_json", type=str, default="", help="Optional output JSON path.")
    ap.add_argument("--out_md", type=str, default="", help="Optional output Markdown path.")
    args = ap.parse_args()

    test_name_set = _load_test_name_set(args.test_list)
    if not test_name_set:
        raise RuntimeError(
            "Held-out query list is empty. Provide --test_list, or ensure "
            "Experiments/AblationStudies/direct_retrieval_comparison.py is importable."
        )

    data = load_and_merge_data()
    test_items = [d for d in data if d.get("SongName") in test_name_set]

    # Few-shot examples: keep consistent with llm_retrieval_comparison.py (handcrafted).
    fewshot_texts = [
        "clean_funk dry_funk groove",
        "blues tweed_breakup vintage_drive",
        "fx_reverse reverse_psychedelic tape_echo",
        "clean_comp math_rock_crystal shimmer",
        "rock_high saturated_rhythm heavy",
    ]

    heldout_song_names = {str(d.get("SongName", "")) for d in test_items if d.get("SongName")}
    heldout_audio_paths = {str(d.get("AudioPath", "")) for d in test_items if d.get("AudioPath")}
    heldout_texts = {
        _normalize_text(" ".join(d.get("Style", []) or []) if (d.get("Style") or []) else str(d.get("SongName", "")))
        for d in test_items
    }

    fewshot_song_names: Set[str] = set()  # handcrafted; no dataset IDs
    fewshot_audio_paths: Set[str] = set()  # no audio examples in prompt
    fewshot_text_set = {_normalize_text(s) for s in fewshot_texts}

    overlap_song = sorted(heldout_song_names.intersection(fewshot_song_names))
    overlap_audio = sorted(heldout_audio_paths.intersection(fewshot_audio_paths))
    overlap_text = sorted(heldout_texts.intersection(fewshot_text_set))

    report = LeakageAuditReport(
        n_total_records=int(len(data)),
        n_test_records=int(len(test_items)),
        n_test_unique_song_names=int(len({d.get("SongName") for d in test_items})),
        fewshot_texts=list(fewshot_texts),
        n_fewshot_texts=int(len(fewshot_texts)),
        overlap_song_names=overlap_song,
        overlap_audio_paths=overlap_audio,
        overlap_texts=overlap_text,
    )

    if args.out_json:
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Audit] Wrote JSON: {out_path}")

    if args.out_md:
        out_path = Path(args.out_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        lines.append("# Few-shot / Held-out Leakage Audit (Protocol-B)")
        lines.append("")
        lines.append(f"- Total records: {report.n_total_records}")
        lines.append(f"- Held-out test records: {report.n_test_records} (unique SongName: {report.n_test_unique_song_names})")
        lines.append(f"- Few-shot texts: {report.n_fewshot_texts}")
        lines.append("")
        lines.append("## Overlaps (Should Be Empty)")
        lines.append("")
        lines.append(f"- SongName overlap: {len(report.overlap_song_names)}")
        if report.overlap_song_names:
            lines.append("  - " + ", ".join(report.overlap_song_names[:20]))
        lines.append(f"- AudioPath overlap: {len(report.overlap_audio_paths)}")
        if report.overlap_audio_paths:
            lines.append("  - " + ", ".join(report.overlap_audio_paths[:5]))
        lines.append(f"- Text overlap: {len(report.overlap_texts)}")
        if report.overlap_texts:
            lines.append("  - " + ", ".join(report.overlap_texts[:20]))
        lines.append("")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[Audit] Wrote MD: {out_path}")

    has_overlap = bool(overlap_song or overlap_audio or overlap_text)
    if has_overlap:
        print("[Audit] FAIL: leakage overlap detected.")
        return 2

    print("[Audit] PASS: overlap=0 (SongName/AudioPath/text)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

