import argparse
import json
import random
from pathlib import Path
from typing import Dict, List


def _load_dataset(dataset_json: Path) -> List[Dict]:
    with dataset_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list.")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_json", type=str, required=True)
    ap.add_argument("--name", type=str, required=True, help="Split namespace name (folder name)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--train", type=float, default=0.80)
    ap.add_argument("--val", type=float, default=0.10)
    ap.add_argument("--test", type=float, default=0.10)
    args = ap.parse_args()

    if abs((args.train + args.val + args.test) - 1.0) > 1e-6:
        raise ValueError("train+val+test must sum to 1.0")

    repo_root = Path(__file__).resolve().parents[2]
    dataset_json = (repo_root / args.dataset_json).resolve()
    dataset = _load_dataset(dataset_json)

    song_names = [str(x["SongName"]) for x in dataset if "SongName" in x]
    if not song_names:
        raise RuntimeError("No SongName in dataset.")

    out_root = repo_root / "Experiments" / "tmm" / "splits" / args.name
    out_root.mkdir(parents=True, exist_ok=True)

    n = len(song_names)
    n_train = int(n * args.train)
    n_val = int(n * args.val)
    n_test = n - n_train - n_val

    for seed in args.seeds:
        rng = random.Random(seed)
        names = song_names[:]
        rng.shuffle(names)

        train_names = names[:n_train]
        val_names = names[n_train : n_train + n_val]
        test_names = names[n_train + n_val :]

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
        }
        (seed_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print(f"Wrote splits: {seed_dir} (train/val/test = {len(train_names)}/{len(val_names)}/{len(test_names)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

