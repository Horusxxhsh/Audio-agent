import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.tmm.leakage_scan import _resolve_audio_path


def _load_dataset(dataset_json: Path) -> List[Dict]:
    with dataset_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list.")
    return data


def group_key_for_name(song_name: str) -> str:
    name = str(song_name or "").strip()
    if " - " in name:
        return name.split(" - ", 1)[0].strip()
    return name


def group_key_for_item(item: Dict, *, group_mode: str, repo_root: Path) -> str:
    song_name = str(item.get("SongName") or "").strip()
    if group_mode == "base_name":
        return group_key_for_name(song_name)
    if group_mode == "resolved_audio":
        resolved = _resolve_audio_path(repo_root, item)
        if resolved is not None:
            return str(resolved)
        return f"missing_audio::{song_name}"
    raise ValueError(f"Unsupported group_mode: {group_mode}")


def build_grouped_split(
    dataset: List[Dict],
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    group_mode: str = "base_name",
) -> Dict[str, List[str]]:
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must sum to 1.0")

    song_names = [str(x["SongName"]) for x in dataset if "SongName" in x and str(x["SongName"]).strip()]
    if not song_names:
        raise RuntimeError("No SongName in dataset.")

    rng = random.Random(seed)

    if group_mode == "none":
        names = song_names[:]
        rng.shuffle(names)
        n = len(names)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        return {
            "train": names[:n_train],
            "val": names[n_train : n_train + n_val],
            "test": names[n_train + n_val :],
        }

    if group_mode not in {"base_name", "resolved_audio"}:
        raise ValueError(f"Unsupported group_mode: {group_mode}")

    grouped: Dict[str, List[str]] = defaultdict(list)
    repo_root = Path(__file__).resolve().parents[2]
    for item in dataset:
        name = str(item.get("SongName") or "").strip()
        if not name:
            continue
        grouped[group_key_for_item(item, group_mode=group_mode, repo_root=repo_root)].append(name)

    group_keys = list(grouped.keys())
    rng.shuffle(group_keys)

    n_total = len(song_names)
    target_train = int(n_total * train_ratio)
    target_val = int(n_total * val_ratio)

    train_names: List[str] = []
    val_names: List[str] = []
    test_names: List[str] = []

    for key in group_keys:
        bucket = grouped[key]
        if len(train_names) < target_train:
            train_names.extend(bucket)
        elif len(val_names) < target_val:
            val_names.extend(bucket)
        else:
            test_names.extend(bucket)

    return {"train": train_names, "val": val_names, "test": test_names}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_json", type=str, required=True)
    ap.add_argument("--name", type=str, required=True, help="Split namespace name (folder name)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--train", type=float, default=0.80)
    ap.add_argument("--val", type=float, default=0.10)
    ap.add_argument("--test", type=float, default=0.10)
    ap.add_argument(
        "--group_mode",
        type=str,
        default="base_name",
        choices=["base_name", "resolved_audio", "none"],
        help="Grouping strategy for split generation. 'base_name' keeps '<Base> - <Suffix>' variants together; "
        "'resolved_audio' keeps items that resolve to the same local audio file together.",
    )
    args = ap.parse_args()

    if abs((args.train + args.val + args.test) - 1.0) > 1e-6:
        raise ValueError("train+val+test must sum to 1.0")

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    dataset = _load_dataset(dataset_json)

    out_root = repo_root / "Experiments" / "tmm" / "splits" / args.name
    out_root.mkdir(parents=True, exist_ok=True)
    n = len([x for x in dataset if "SongName" in x and str(x["SongName"]).strip()])

    for seed in args.seeds:
        split = build_grouped_split(
            dataset,
            seed=seed,
            train_ratio=args.train,
            val_ratio=args.val,
            test_ratio=args.test,
            group_mode=args.group_mode,
        )
        train_names = split["train"]
        val_names = split["val"]
        test_names = split["test"]

        seed_dir = out_root / f"seed{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        (seed_dir / "train.txt").write_text("\n".join(train_names) + "\n", encoding="utf-8")
        (seed_dir / "val.txt").write_text("\n".join(val_names) + "\n", encoding="utf-8")
        (seed_dir / "test.txt").write_text("\n".join(test_names) + "\n", encoding="utf-8")

        summary = {
            "seed": seed,
            "n_total": n,
            "n_train": len(train_names),
            "n_val": len(val_names),
            "n_test": len(test_names),
            "dataset_json": str(dataset_json),
            "group_mode": args.group_mode,
        }
        (seed_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print(f"Wrote splits: {seed_dir} (train/val/test = {len(train_names)}/{len(val_names)}/{len(test_names)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
