import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def _run(cmd: List[str], repo_root: Path, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write("+ " + " ".join(cmd) + "\n\n")
        f.flush()
        p = subprocess.run(cmd, cwd=str(repo_root), stdout=f, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run E0 end-to-end (synth -> render -> manifest -> splits -> audit -> leakage).")
    ap.add_argument("--n", type=int, default=220)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dataset_name", type=str, default="tmm_synth_v1")
    ap.add_argument("--out", type=str, default="Data/TMM_Synth_v1")
    ap.add_argument("--dataset_json", type=str, default="Experiments/dataset_full_vectors.json")
    ap.add_argument("--timeout_sec", type=float, default=60.0)
    ap.add_argument("--poll_sec", type=float, default=0.25)
    ap.add_argument("--split_seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--near_dup_threshold", type=float, default=0.995)
    ap.add_argument("--group_mode", type=str, default="base_name")
    ap.add_argument("--skip_preflight", action="store_true")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    out_dir = (repo_root / args.out).resolve()

    ts = time.strftime("%Y%m%d_%H%M%S")
    run_root = repo_root / "Experiments" / "tmm" / "runlogs" / f"E0_audio_{ts}"

    meta: Dict[str, Any] = {
        "timestamp": ts,
        "platform": platform.platform(),
        "python": sys.version,
        "args": vars(args),
        "repo_root": str(repo_root),
        "out_dir": str(out_dir),
        "dataset_json": str(dataset_json),
    }
    _write_json(run_root / "meta.json", meta)

    # 0) Preflight: render 1 sample to confirm the plugin Auto Import pipeline is active.
    if not args.skip_preflight:
        _run(
            [
                sys.executable,
                "Experiments/tmm/synth_dataset.py",
                "--n",
                "1",
                "--seed",
                str(args.seed),
                "--dataset_name",
                args.dataset_name,
                "--out",
                "Data/TMM_Synth_preflight",
                "--dataset_json",
                "Experiments/dataset_full_vectors_preflight.json",
                "--timeout_sec",
                str(args.timeout_sec),
                "--poll_sec",
                str(args.poll_sec),
            ],
            repo_root=repo_root,
            log_path=run_root / "00_preflight.log",
        )

    # 1) Full synth + render + manifest.
    _run(
        [
            sys.executable,
            "Experiments/tmm/synth_dataset.py",
            "--n",
            str(args.n),
            "--seed",
            str(args.seed),
            "--dataset_name",
            args.dataset_name,
            "--out",
            str(Path(args.out)),
            "--dataset_json",
            str(Path(args.dataset_json)),
            "--timeout_sec",
            str(args.timeout_sec),
            "--poll_sec",
            str(args.poll_sec),
        ],
        repo_root=repo_root,
        log_path=run_root / "01_synth_render.log",
    )

    # 2) Splits.
    _run(
        [
            sys.executable,
            "Experiments/tmm/make_splits.py",
            "--dataset_json",
            str(Path(args.dataset_json)),
            "--name",
            args.dataset_name,
            "--seeds",
            *[str(x) for x in args.split_seeds],
            "--group_mode",
            args.group_mode,
        ],
        repo_root=repo_root,
        log_path=run_root / "02_splits.log",
    )

    # 3) Audit.
    audit_out = repo_root / "Experiments" / "tmm" / "dataset_audit_report.json"
    _run(
        [
            sys.executable,
            "Experiments/tmm/dataset_audit.py",
            "--dataset_json",
            str(Path(args.dataset_json)),
            "--split_root",
            str(Path("Experiments/tmm/splits") / args.dataset_name),
            "--out",
            str(audit_out.relative_to(repo_root)),
        ],
        repo_root=repo_root,
        log_path=run_root / "03_audit.log",
    )

    # 4) Leakage scan.
    leakage_out = repo_root / "Experiments" / "tmm" / "leakage_report.json"
    _run(
        [
            sys.executable,
            "Experiments/tmm/leakage_scan.py",
            "--dataset_json",
            str(Path(args.dataset_json)),
            "--split_root",
            str(Path("Experiments/tmm/splits") / args.dataset_name),
            "--out",
            str(leakage_out.relative_to(repo_root)),
            "--near_dup_threshold",
            str(args.near_dup_threshold),
        ],
        repo_root=repo_root,
        log_path=run_root / "04_leakage.log",
    )

    # 5) Summarize results (no fabrication; derived from JSON reports).
    audit = _load_json(audit_out)
    leakage = _load_json(leakage_out)

    summary: Dict[str, Any] = {
        "run_root": str(run_root),
        "dataset_json": str(dataset_json),
        "out_dir": str(out_dir),
        "audit_report": str(audit_out),
        "leakage_report": str(leakage_out),
        "audit_key_numbers": {
            "n_total_items": audit.get("n_total_items"),
            "n_items_with_existing_audio": audit.get("n_items_with_existing_audio"),
            "n_items_missing_audio": audit.get("n_items_missing_audio"),
            "n_unreadable_audio": audit.get("n_unreadable_audio"),
            "n_silent_audio": audit.get("n_silent_audio"),
            "n_clipped_audio": audit.get("n_clipped_audio"),
        },
        "leakage_key_numbers": {
            "n_items_with_audio": leakage.get("n_items_with_audio"),
            "n_exact_duplicate_groups": leakage.get("n_exact_duplicate_groups"),
            "n_near_duplicate_pairs": leakage.get("n_near_duplicate_pairs"),
            "near_duplicate_threshold": leakage.get("near_duplicate_threshold"),
        },
        "split_reports": leakage.get("split_reports", {}),
    }
    _write_json(run_root / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
