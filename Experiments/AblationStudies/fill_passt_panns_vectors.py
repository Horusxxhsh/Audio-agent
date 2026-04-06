import argparse
import json
import math
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import requests
import soundfile as sf
import torch
import torchaudio


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATASET = os.path.join("Experiments", "dataset_full_vectors.json")
MANUAL_AUDIO_PATHS = {
    "Prism Clean Math Rock Crystal": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Base_TRR_Advantage_for_Math_Rock_Crystal.wav"),
    "Vintage Tweed Breakup": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Base_TRR_Advantage_for_Tweed_Breakup.wav"),
    "Pocketline Dry Funk": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Base_TRR_Advantage_for_Dry_Funk.wav"),
    "Saturated Drive Rhythm": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Base_TRR_Advantage_for_Saturated_Rhythm.wav"),
    "Echo Trail Reverse Psychedelic": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Base_TRR_Advantage_for_Reverse_Psychedelic.wav"),
    "Stadium Fire 80s Hair Metal 2": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "80s Hair Metal.wav"),
    "Organic Bloom Acoustic Sim": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Acoustic Sim.wav"),
    "Pocketline Auto-Wah Funk 2": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Auto-Wah Funk.wav"),
    "Brian May Queen Tone": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Brian May Style.wav"),
    "Current Heat Brown Sound": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Brown Sound.wav"),
    "Plexi Classic Hot": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Classic Plexi.wav"),
    "Aether Glow Dreamy Shoegaze": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Dreamy Shoegaze.wav"),
    "Redux Hard Rock Crunch": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Hard Rock Crunch.wav"),
    "Jazz Hollowbody Warm": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Hollow Body Jazz.wav"),
    "Late Night Ease Lo-Fi Hip Hop": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Lo-Fi Hip Hop.wav"),
    "Livewire Punk Rock Raw": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Punk Rock Raw.wav"),
    "Rotor Rush Rotary Speaker": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Rotary Speaker.wav"),
    "Amber Glow Texas Blues": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Texas Blues.wav"),
    "Silk Glide Touch Sensitive Lead": os.path.join(ROOT_DIR, "Data", "Audio_Synthetic", "Touch Sensitive Lead.wav"),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fill PaSST and PANNs vectors into dataset_full_vectors.json.")
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--methods", nargs="+", default=["PaSST", "PANNs"], choices=["PaSST", "PANNs"])
    p.add_argument("--limit", type=int, default=0, help="Only process the first N resolvable items. 0 means all.")
    p.add_argument("--force", action="store_true", help="Recompute vectors even if already present.")
    p.add_argument("--backup", action="store_true", help="Create a backup before writing.")
    p.add_argument(
        "--cache-dir",
        default=os.path.join("Experiments", "AblationStudies", "model_cache"),
        help="Local cache directory for downloaded weights and labels.",
    )
    p.add_argument(
        "--save-every",
        type=int,
        default=25,
        help="Persist dataset every N updated items to avoid losing long-running progress.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Number of audio files to encode together per forward pass.",
    )
    return p.parse_args()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def backup_file(path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_before_passt_panns_{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return vec.astype(np.float32)
    return (vec / norm).astype(np.float32)


def load_audio_mono_32k(audio_path: str) -> np.ndarray:
    audio, sr = sf.read(audio_path)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if sr != 32000:
        wav = torch.from_numpy(audio).unsqueeze(0)
        audio = torchaudio.functional.resample(wav, sr, 32000).squeeze(0).cpu().numpy().astype(np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        audio = audio / peak
    return audio


def load_audio_batch(audio_paths: Iterable[str]) -> np.ndarray:
    audios = [load_audio_mono_32k(path) for path in audio_paths]
    max_len = max(len(audio) for audio in audios)
    batch = np.stack([np.pad(audio, (0, max_len - len(audio))) for audio in audios]).astype(np.float32)
    return batch


def candidate_dirs() -> List[str]:
    return [
        os.path.join(ROOT_DIR, "Data", "Audio_Synthetic"),
        os.path.join(ROOT_DIR, "musiccaps_guitar_solo"),
        os.path.join(ROOT_DIR, "Sounds"),
        os.path.join(ROOT_DIR, "Assets"),
    ]


def build_basename_index() -> Dict[str, str]:
    index: Dict[str, str] = {}
    for base_dir in candidate_dirs():
        if not os.path.isdir(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for name in files:
                index.setdefault(name.lower(), os.path.join(root, name))
    return index


def resolve_audio_path(original_path: str, basename_index: Dict[str, str]) -> Optional[str]:
    if original_path and os.path.exists(original_path):
        return os.path.abspath(original_path)
    if not original_path:
        return None
    basename = os.path.basename(original_path).lower()
    return basename_index.get(basename)


def resolve_audio_path_for_item(item: Dict[str, Any], basename_index: Dict[str, str]) -> Optional[str]:
    manual = MANUAL_AUDIO_PATHS.get(str(item.get("SongName", "")))
    if manual and os.path.exists(manual):
        return manual
    return resolve_audio_path(str(item.get("AudioPath", "")), basename_index)


def configure_model_env(cache_dir: str) -> Dict[str, str]:
    abs_cache = os.path.abspath(cache_dir)
    ensure_dir(abs_cache)
    home_dir = os.path.join(abs_cache, "home")
    torch_home = os.path.join(abs_cache, "torch")
    tmp_dir = os.path.join(abs_cache, "tmp")
    numba_cache_dir = os.path.join(abs_cache, "numba_cache")
    ensure_dir(home_dir)
    ensure_dir(torch_home)
    ensure_dir(tmp_dir)
    ensure_dir(numba_cache_dir)
    os.environ["HOME"] = home_dir
    os.environ["USERPROFILE"] = home_dir
    os.environ["TORCH_HOME"] = torch_home
    os.environ["TMP"] = tmp_dir
    os.environ["TEMP"] = tmp_dir
    os.environ["NUMBA_CACHE_DIR"] = numba_cache_dir
    os.environ["NUMBA_DISABLE_JIT"] = "1"
    return {
        "home_dir": home_dir,
        "torch_home": torch_home,
        "tmp_dir": tmp_dir,
        "numba_cache_dir": numba_cache_dir,
    }


def download_file(url: str, dst: str) -> None:
    ensure_dir(os.path.dirname(dst))
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


class PasstEncoder:
    def __init__(self) -> None:
        from hear21passt.api import get_scene_embeddings, load_model

        self._get_scene_embeddings = get_scene_embeddings
        self.model = load_model()

    def encode(self, audio_path: str) -> np.ndarray:
        return self.encode_many([audio_path])[0]

    def encode_many(self, audio_paths: List[str]) -> List[np.ndarray]:
        batch = load_audio_batch(audio_paths)
        tensor = torch.from_numpy(batch)
        embeddings = self._get_scene_embeddings(tensor, self.model).detach().cpu().numpy()
        return [l2_normalize(np.asarray(emb, dtype=np.float32)) for emb in embeddings]

class PannsEncoder:
    LABELS_URL = "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"
    CHECKPOINT_URL = "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1"

    def __init__(self, home_dir: str) -> None:
        panns_dir = os.path.join(home_dir, "panns_data")
        labels_path = os.path.join(panns_dir, "class_labels_indices.csv")
        checkpoint_path = os.path.join(panns_dir, "Cnn14_mAP=0.431.pth")
        download_file(self.LABELS_URL, labels_path)
        download_file(self.CHECKPOINT_URL, checkpoint_path)

        from panns_inference import AudioTagging

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AudioTagging(checkpoint_path=checkpoint_path, device=device)

    def encode(self, audio_path: str) -> np.ndarray:
        return self.encode_many([audio_path])[0]

    def encode_many(self, audio_paths: List[str]) -> List[np.ndarray]:
        batch = load_audio_batch(audio_paths)
        _, embeddings = self.model.inference(batch)
        return [l2_normalize(np.asarray(emb, dtype=np.float32)) for emb in embeddings]


def should_update(item: Dict[str, Any], method: str, force: bool) -> bool:
    if force:
        return True
    vec = item.get("Vectors", {}).get(method)
    return not (isinstance(vec, list) and len(vec) > 0)


def flush_batch(
    pending: List[Dict[str, Any]],
    encoders: Dict[str, Any],
    dataset_path: str,
    data: List[Dict[str, Any]],
    updated_methods: Dict[str, int],
    updated_items: int,
    save_every: int,
) -> int:
    if not pending:
        return updated_items

    for method, encoder in encoders.items():
        subset = [entry for entry in pending if method in entry["methods_needed"]]
        if not subset:
            continue
        vectors = encoder.encode_many([entry["audio_path"] for entry in subset])
        for entry, vec in zip(subset, vectors):
            entry["item"]["Vectors"][method] = vec.tolist()
            updated_methods[method] += 1

    updated_items += len(pending)
    if updated_items % max(1, save_every) < len(pending) or updated_items == len(pending):
        save_dataset(dataset_path, data)
        print(
            f"[checkpoint] updated_items={updated_items} "
            f"PaSST={updated_methods.get('PaSST', 0)} "
            f"PANNs={updated_methods.get('PANNs', 0)}",
            flush=True,
        )
    return updated_items


def main() -> None:
    args = parse_args()
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    dataset_path = os.path.abspath(args.dataset)
    data = load_dataset(dataset_path)
    basename_index = build_basename_index()
    env_info = configure_model_env(args.cache_dir)

    backup_path = None
    if args.backup:
        backup_path = backup_file(dataset_path)

    encoders: Dict[str, Any] = {}
    if "PaSST" in args.methods:
        encoders["PaSST"] = PasstEncoder()
    if "PANNs" in args.methods:
        encoders["PANNs"] = PannsEncoder(env_info["home_dir"])

    updated_items = 0
    processed = 0
    unresolved = 0
    updated_methods = {m: 0 for m in args.methods}
    pending: List[Dict[str, Any]] = []

    for item in data:
        original_audio_path = str(item.get("AudioPath", ""))
        resolved_audio_path = resolve_audio_path_for_item(item, basename_index)
        if not resolved_audio_path:
            unresolved += 1
            continue

        item["AudioPath"] = resolved_audio_path
        item.setdefault("Vectors", {})
        need_any = any(should_update(item, method, args.force) for method in args.methods)
        if not need_any:
            continue

        processed += 1
        if args.limit and processed > args.limit:
            break

        pending.append(
            {
                "item": item,
                "audio_path": resolved_audio_path,
                "methods_needed": [method for method in args.methods if should_update(item, method, args.force)],
            }
        )
        if len(pending) >= max(1, args.batch_size):
            updated_items = flush_batch(
                pending,
                encoders,
                dataset_path,
                data,
                updated_methods,
                updated_items,
                args.save_every,
            )
            pending = []

    updated_items = flush_batch(
        pending,
        encoders,
        dataset_path,
        data,
        updated_methods,
        updated_items,
        args.save_every,
    )

    save_dataset(dataset_path, data)
    print("Done.", flush=True)
    print(f"dataset: {dataset_path}", flush=True)
    if backup_path:
        print(f"backup: {backup_path}", flush=True)
    print(f"processed_items: {processed}", flush=True)
    print(f"updated_items: {updated_items}", flush=True)
    print(f"unresolved_audio_paths: {unresolved}", flush=True)
    for method in args.methods:
        print(f"{method}_updated: {updated_methods[method]}", flush=True)


if __name__ == "__main__":
    main()
