import argparse
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATASET = os.path.join("Experiments", "dataset_full_vectors.json")
MANUAL_CLAP_SOURCES = {
    "Prism Clean Math Rock Crystal": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Math Rock Crystal.wav.clap.npy"),
    "Vintage Tweed Breakup": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Tweed Breakup.wav.clap.npy"),
    "Pocketline Dry Funk": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Dry Funk.wav.clap.npy"),
    "Saturated Drive Rhythm": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Saturated Rhythm.wav.clap.npy"),
    "Echo Trail Reverse Psychedelic": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Reverse Psychedelic.wav.clap.npy"),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fill missing CLAP vectors from existing .clap.npy caches.")
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--force", action="store_true", help="Overwrite existing CLAP vectors.")
    p.add_argument("--backup", action="store_true", help="Create a backup before writing.")
    return p.parse_args()


def backup_file(path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_before_clap_fill_{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def should_fill(item: Dict[str, Any], force: bool) -> bool:
    if force:
        return True
    vec = item.get("Vectors", {}).get("CLAP")
    return not (isinstance(vec, list) and len(vec) > 0)


def resolve_clap_npy(item: Dict[str, Any]) -> Optional[str]:
    manual = MANUAL_CLAP_SOURCES.get(str(item.get("SongName", "")))
    if manual and os.path.exists(manual):
        return manual
    audio_path = str(item.get("AudioPath", ""))
    if not audio_path:
        return None
    npy_path = audio_path + ".clap.npy"
    if os.path.exists(npy_path):
        return npy_path
    return None


def main() -> None:
    args = parse_args()
    dataset_path = os.path.abspath(args.dataset)
    data = load_dataset(dataset_path)

    backup_path = backup_file(dataset_path) if args.backup else None
    updated = 0
    unresolved: List[str] = []

    for item in data:
        item.setdefault("Vectors", {})
        if not should_fill(item, args.force):
            continue

        npy_path = resolve_clap_npy(item)
        if not npy_path:
            unresolved.append(str(item.get("SongName", "")))
            continue

        vec = np.load(npy_path)
        item["Vectors"]["CLAP"] = np.asarray(vec, dtype=np.float32).tolist()
        updated += 1

    save_dataset(dataset_path, data)
    print("Done.")
    print(f"dataset: {dataset_path}")
    if backup_path:
        print(f"backup: {backup_path}")
    print(f"updated_clap: {updated}")
    print(f"unresolved: {len(unresolved)}")
    for name in unresolved:
        print(name)


if __name__ == "__main__":
    main()
