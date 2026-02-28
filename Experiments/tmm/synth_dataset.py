import argparse
import copy
import hashlib
import json
import os
import random
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


FORCE_OFF_MODULES = {
    # Current plugin offline renderer skips/avoids these modules; keep them off for coherence.
    "Compressor",
    "Driver",
    "Screamer",
    "Delay",
    "NoiseGate",
}

AUDIBLE_MODULES = {"Equaliser", "Chorus", "Flanger", "Phaser", "Reverb"}


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _default_documents_dir() -> Path:
    env = os.environ.get("DOCUMENTS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "Documents").resolve()


def _plugin_import_dir(documents_dir: Path) -> Path:
    return documents_dir / "Supertonal" / "Audio-agent"


def _safe_parse_json(s: Any) -> Any:
    if isinstance(s, (dict, list)):
        return s
    if not isinstance(s, str):
        return s
    try:
        return json.loads(s)
    except Exception:
        return s


def _parse_tags(s: Any) -> List[str]:
    if s is None:
        return []
    if isinstance(s, list):
        return [str(x).strip() for x in s if str(x).strip()]
    if isinstance(s, str):
        # common DB format is "a, b, c"
        parts = [p.strip() for p in s.split(",")]
        return [p for p in parts if p]
    return [str(s).strip()]


def _extract_module_root(module_key: str) -> Tuple[str, str]:
    if module_key.endswith("On"):
        return module_key[: -len("On")], "On"
    if module_key.endswith("Off"):
        return module_key[: -len("Off")], "Off"
    return module_key, ""


def _with_state(root: str, state: str) -> str:
    if state not in {"On", "Off"}:
        return root
    return f"{root}{state}"


def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


@dataclass(frozen=True)
class ParamStat:
    min_v: float
    max_v: float
    mean_v: float
    std_v: float


def _collect_param_stats(presets: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str], ParamStat]:
    buckets: Dict[Tuple[str, str], List[float]] = {}
    for preset in presets:
        params = preset.get("Parameters") or {}
        if not isinstance(params, dict):
            continue
        for module_key, module_value in params.items():
            root, _ = _extract_module_root(str(module_key))
            if not isinstance(module_value, dict):
                continue
            for sub_key, sub_value in module_value.items():
                fv = _to_float(sub_value)
                if fv is None:
                    continue
                buckets.setdefault((root, str(sub_key)), []).append(fv)

    stats: Dict[Tuple[str, str], ParamStat] = {}
    for k, values in buckets.items():
        if not values:
            continue
        values_sorted = sorted(values)
        n = len(values_sorted)
        mean_v = sum(values_sorted) / n
        var = sum((x - mean_v) ** 2 for x in values_sorted) / max(1, n - 1)
        std_v = var ** 0.5
        stats[k] = ParamStat(
            min_v=values_sorted[0],
            max_v=values_sorted[-1],
            mean_v=mean_v,
            std_v=std_v,
        )
    return stats


def _jitter_params(
    base_params: Dict[str, Any],
    stats: Dict[Tuple[str, str], ParamStat],
    rng: random.Random,
    p_flip: float = 0.10,
    noise_scale: float = 0.50,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for module_key, module_value in base_params.items():
        module_key = str(module_key)
        root, state = _extract_module_root(module_key)

        # Force some modules off for coherence with the current offline renderer.
        if root in FORCE_OFF_MODULES:
            new_key = _with_state(root, "Off")
        else:
            flip = rng.random() < p_flip
            new_state = state
            if state in {"On", "Off"} and flip:
                new_state = "Off" if state == "On" else "On"
            new_key = _with_state(root, new_state) if state else module_key

        if not isinstance(module_value, dict):
            out[new_key] = copy.deepcopy(module_value)
            continue

        new_module: Dict[str, Any] = {}
        for sub_key, sub_value in module_value.items():
            sub_key_s = str(sub_key)
            fv = _to_float(sub_value)
            if fv is None:
                new_module[sub_key_s] = copy.deepcopy(sub_value)
                continue

            stat = stats.get((root, sub_key_s))
            if stat and stat.max_v > stat.min_v:
                range_v = stat.max_v - stat.min_v
                sigma = (stat.std_v if stat.std_v > 0 else 0.05 * range_v) * noise_scale
                new_v = fv + rng.gauss(0.0, sigma)
                # clamp
                new_v = max(stat.min_v, min(stat.max_v, new_v))
            else:
                new_v = fv

            new_module[sub_key_s] = float(new_v)

        out[new_key] = new_module

    # Ensure at least one audible module is On, otherwise everything sounds too similar.
    has_audible_on = any(
        (k.endswith("On") and _extract_module_root(k)[0] in AUDIBLE_MODULES) for k in out.keys()
    )
    if not has_audible_on:
        candidates = [m for m in AUDIBLE_MODULES if _with_state(m, "Off") in out]
        if candidates:
            pick = rng.choice(candidates)
            off_key = _with_state(pick, "Off")
            out[_with_state(pick, "On")] = out.pop(off_key)

    return out


def _style_tags(params: Dict[str, Any], dataset_name: str, seed: int) -> List[str]:
    tags = ["synthetic", dataset_name, f"seed{seed}"]
    for module_key in params.keys():
        root, state = _extract_module_root(str(module_key))
        if state == "On" and root in AUDIBLE_MODULES:
            tags.append(f"{root.lower()}_on")
    return tags


def _feature_text(params: Dict[str, Any], parent: str) -> str:
    on = []
    for module_key in params.keys():
        root, state = _extract_module_root(str(module_key))
        if state == "On" and root in AUDIBLE_MODULES:
            on.append(root)
    on_s = ", ".join(sorted(on)) if on else "None"
    return f"Synthetic preset (offline-rendered). Audible modules on: {on_s}. Parent preset: {parent}."


# Mapping copied from the existing `Source/llm.py` auto-import logic.
# Keys are module-style parameters (nested JSON). Values are plugin parameter IDs or switch tuples.
PARAM_MAPPING: Dict[str, Any] = {
    "CompressorOn": ("pre_compressor_on", 1.0),
    "CompressorOff": ("pre_compressor_on", 0.0),
    "ScreamerOn": ("tube_screamer_on", 1.0),
    "ScreamerOff": ("tube_screamer_on", 0.0),
    "DriverOn": ("mouse_drive_on", 1.0),
    "DriverOff": ("mouse_drive_on", 0.0),
    "DelayOn": ("delay_on", 1.0),
    "DelayOff": ("delay_on", 0.0),
    "ReverbOn": ("room_on", 1.0),
    "ReverbOff": ("room_on", 0.0),
    "ChorusOn": ("chorus_on", 1.0),
    "ChorusOff": ("chorus_on", 0.0),
    "FlangerOn": ("flanger_on", 1.0),
    "FlangerOff": ("flanger_on", 0.0),
    "PhaserOn": ("phaser_on", 1.0),
    "PhaserOff": ("phaser_on", 0.0),
    "EqualiserOn": ("pre_eq_on", 1.0),
    "EqualiserOff": ("pre_eq_on", 0.0),
    "NoiseGateOn": ("noise_gate_on", 1.0),
    "NoiseGateOff": ("noise_gate_on", 0.0),
    # Compressor
    "CompressorOn.Threshold": "pre_comp_thresh",
    "CompressorOn.Ratio": "pre_comp_ratio",
    "CompressorOn.Attack": "pre_comp_attack",
    "CompressorOn.Release": "pre_comp_release",
    "CompressorOn.Mix": "pre_comp_blend",
    "CompressorOn.Makeup": "pre_comp_gain",
    "CompressorOff.Threshold": "pre_comp_thresh",
    "CompressorOff.Ratio": "pre_comp_ratio",
    "CompressorOff.Attack": "pre_comp_attack",
    "CompressorOff.Release": "pre_comp_release",
    "CompressorOff.Mix": "pre_comp_blend",
    "CompressorOff.Makeup": "pre_comp_gain",
    # Screamer
    "ScreamerOn.Drive": "tube_screamer_drive",
    "ScreamerOn.Tone": "tube_screamer_tone",
    "ScreamerOn.Level": "tube_screamer_level",
    "ScreamerOff.Drive": "tube_screamer_drive",
    "ScreamerOff.Tone": "tube_screamer_tone",
    "ScreamerOff.Level": "tube_screamer_level",
    # Driver
    "DriverOn.Distortion": "mouse_drive_distortion",
    "DriverOn.Volume": "mouse_drive_volume",
    "DriverOff.Distortion": "mouse_drive_distortion",
    "DriverOff.Volume": "mouse_drive_volume",
    # Delay
    "DelayOn.Feedback": "delay_feedback",
    "DelayOn.Delay": "delay_left_millisecond",
    "DelayOn.Mix": "delay_mix",
    "DelayOff.Feedback": "delay_feedback",
    "DelayOff.Delay": "delay_left_millisecond",
    "DelayOff.Mix": "delay_mix",
    # Reverb
    "ReverbOn.Size": "room_size",
    "ReverbOn.Damping": "room_damping",
    "ReverbOn.Width": "room_width",
    "ReverbOn.Mix": "room_mix",
    "ReverbOff.Size": "room_size",
    "ReverbOff.Damping": "room_damping",
    "ReverbOff.Width": "room_width",
    "ReverbOff.Mix": "room_mix",
    # Chorus
    "ChorusOn.Delay": "chorus_delay",
    "ChorusOn.Depth": "chorus_depth",
    "ChorusOn.Frequency": "chorus_frequency",
    "ChorusOn.Width": "chorus_width",
    "ChorusOff.Delay": "chorus_delay",
    "ChorusOff.Depth": "chorus_depth",
    "ChorusOff.Frequency": "chorus_frequency",
    "ChorusOff.Width": "chorus_width",
    # Flanger
    "FlangerOn.Delay": "flanger_delay",
    "FlangerOn.Depth": "flanger_depth",
    "FlangerOn.Feedback": "flanger_feedback",
    "FlangerOn.Frequency": "flanger_frequency",
    "FlangerOn.Width": "flanger_width",
    "FlangerOff.Delay": "flanger_delay",
    "FlangerOff.Depth": "flanger_depth",
    "FlangerOff.Feedback": "flanger_feedback",
    "FlangerOff.Frequency": "flanger_frequency",
    "FlangerOff.Width": "flanger_width",
    # Phaser
    "PhaserOn.Depth": "phaser_depth",
    "PhaserOn.Feedback": "phaser_feedback",
    "PhaserOn.Frequency": "phaser_frequency",
    "PhaserOn.Width": "phaser_width",
    "PhaserOff.Depth": "phaser_depth",
    "PhaserOff.Feedback": "phaser_feedback",
    "PhaserOff.Frequency": "phaser_frequency",
    "PhaserOff.Width": "phaser_width",
    # Equaliser (pre EQ)
    "EqualiserOn.100hz": "pre_eq_100_gain",
    "EqualiserOn.200hz": "pre_eq_200_gain",
    "EqualiserOn.400hz": "pre_eq_400_gain",
    "EqualiserOn.800hz": "pre_eq_800_gain",
    "EqualiserOn.1600hz": "pre_eq_1600_gain",
    "EqualiserOn.3200hz": "pre_eq_3200_gain",
    "EqualiserOn.6400hz": "pre_eq_6400_gain",
    "EqualiserOn.Level": "pre_eq_level_gain",
    "EqualiserOff.100hz": "pre_eq_100_gain",
    "EqualiserOff.200hz": "pre_eq_200_gain",
    "EqualiserOff.400hz": "pre_eq_400_gain",
    "EqualiserOff.800hz": "pre_eq_800_gain",
    "EqualiserOff.1600hz": "pre_eq_1600_gain",
    "EqualiserOff.3200hz": "pre_eq_3200_gain",
    "EqualiserOff.6400hz": "pre_eq_6400_gain",
    "EqualiserOff.Level": "pre_eq_level_gain",
}


def _map_to_import_params(nested_params: Dict[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    for module_key, module_value in nested_params.items():
        if module_key in PARAM_MAPPING and isinstance(PARAM_MAPPING[module_key], tuple):
            pid, pval = PARAM_MAPPING[module_key]
            mapped[pid] = pval
        if isinstance(module_value, dict):
            for sub_key, sub_value in module_value.items():
                full_key = f"{module_key}.{sub_key}"
                pid = PARAM_MAPPING.get(full_key)
                if isinstance(pid, str):
                    fv = _to_float(sub_value)
                    mapped[pid] = fv if fv is not None else sub_value
    return mapped


def _render_with_plugin(
    import_dir: Path,
    import_params: Dict[str, Any],
    dry_wav: Path,
    out_wav: Path,
    timeout_sec: float,
    poll_sec: float,
) -> bool:
    import_dir.mkdir(parents=True, exist_ok=True)
    params_path = import_dir / "import_params.json"
    input_path = import_dir / "generated_input.wav"
    output_path = import_dir / "final_output.wav"

    t0 = time.time()

    # Best-effort remove stale output so "mtime changed" always corresponds to the current trigger.
    # (Some shell environments block `rm`; do it in-process and ignore failures.)
    try:
        output_path.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 1) Write params first (so the next timer tick applies them).
    with params_path.open("w", encoding="utf-8") as f:
        json.dump(import_params, f, ensure_ascii=False, indent=2)

    # Let the plugin timer pick up parameters.
    time.sleep(0.60)

    # 2) Overwrite input audio to trigger a render.
    shutil.copyfile(dry_wav, input_path)
    os.utime(input_path, None)
    try:
        trigger_mtime = float(input_path.stat().st_mtime)
    except Exception:
        trigger_mtime = t0

    # 3) Wait for output to update.
    deadline = t0 + timeout_sec
    last_mtime = 0.0
    if output_path.exists():
        try:
            last_mtime = output_path.stat().st_mtime
        except Exception:
            last_mtime = 0.0

    while time.time() < deadline:
        if output_path.exists():
            try:
                st = output_path.stat()
                if (
                    st.st_size > 0
                    and st.st_mtime > last_mtime + 1e-6
                    and st.st_mtime >= trigger_mtime - 1e-3
                ):
                    # Guard: wait briefly for file size to stabilize to avoid copying mid-write.
                    size1 = int(st.st_size)
                    time.sleep(0.15)
                    try:
                        size2 = int(output_path.stat().st_size)
                    except Exception:
                        size2 = -1
                    if size2 == size1 and size2 > 0:
                        shutil.copyfile(output_path, out_wav)
                        return True
            except Exception:
                pass
        time.sleep(poll_sec)

    return False


def _load_base_presets(music_db: Path) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(music_db))
    try:
        cur = conn.cursor()
        cur.execute("SELECT SongName, Parameters, Style, Feature FROM music_responses ORDER BY rowid")
        rows = cur.fetchall()
    finally:
        conn.close()

    presets: List[Dict[str, Any]] = []
    for song_name, params_str, style_str, feature_str in rows:
        params_obj = _safe_parse_json(params_str)
        if not isinstance(params_obj, dict):
            continue
        presets.append(
            {
                "SongName": str(song_name),
                "Parameters": params_obj,
                "Style": _parse_tags(style_str),
                "Feature": _parse_tags(feature_str),
            }
        )
    return presets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=220, help="Number of synthetic presets to generate")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--music_db", type=str, default="music_info.db")
    ap.add_argument("--dry_wav", type=str, default="Sounds/guitar_tone_test_2.wav")
    ap.add_argument("--out", type=str, default="Data/TMM_Synth_v1")
    ap.add_argument("--dataset_name", type=str, default="tmm_synth_v1")
    ap.add_argument("--dataset_json", type=str, default="Experiments/dataset_full_vectors.json")
    ap.add_argument("--timeout_sec", type=float, default=60.0)
    ap.add_argument("--poll_sec", type=float, default=0.25)
    ap.add_argument("--no_render", action="store_true", help="Only sample parameters; do not call the plugin renderer")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    music_db = (repo_root / args.music_db).resolve()
    dry_wav = (repo_root / args.dry_wav).resolve()
    out_dir = (repo_root / args.out).resolve()
    dataset_json = (repo_root / args.dataset_json).resolve()

    if not music_db.exists():
        raise FileNotFoundError(f"Missing music_db: {music_db}")
    if not dry_wav.exists():
        raise FileNotFoundError(f"Missing dry_wav: {dry_wav}")

    base_presets = _load_base_presets(music_db)
    if not base_presets:
        raise RuntimeError("No base presets loaded from music_responses.")

    stats = _collect_param_stats(base_presets)
    rng = random.Random(args.seed)

    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    documents_dir = _default_documents_dir()
    import_dir = _plugin_import_dir(documents_dir)

    dataset: List[Dict[str, Any]] = []
    manifest_rows: List[Dict[str, Any]] = []

    def _to_repo_rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except Exception:
            return str(p)

    def _checkpoint() -> None:
        dataset_json.parent.mkdir(parents=True, exist_ok=True)
        with dataset_json.open("w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        manifest_path = out_dir / "dataset_manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(manifest_rows, f, ensure_ascii=False, indent=2)

    checkpoint_every = 20

    for i in range(args.n):
        parent = rng.choice(base_presets)
        parent_name = parent["SongName"]
        base_params = parent["Parameters"]

        synth_params = _jitter_params(base_params, stats, rng)
        song_name = f"TMM_Synth_{i:05d}"
        out_wav = audio_dir / f"{song_name}.wav"

        if not args.no_render:
            # Resume-friendly: if the target wav already exists, reuse it.
            if not out_wav.exists():
                import_params = _map_to_import_params(synth_params)
                ok = _render_with_plugin(
                    import_dir=import_dir,
                    import_params=import_params,
                    dry_wav=dry_wav,
                    out_wav=out_wav,
                    timeout_sec=args.timeout_sec,
                    poll_sec=args.poll_sec,
                )
                if not ok:
                    print("")
                    print("ERROR: Plugin render timeout.")
                    print("Checklist:")
                    print(f"- Is the plugin running with Auto Import enabled?")
                    print(f"- Is this directory correct? {import_dir}")
                    print("- Did it create/update final_output.wav there?")
                    print("")
                    print("Writing partial dataset checkpoint for resuming...")
                    _checkpoint()
                    return 2

        audio_path_value = _to_repo_rel(out_wav) if out_wav.exists() else None
        style = _style_tags(synth_params, args.dataset_name, args.seed)
        feature = [_feature_text(synth_params, parent=parent_name)]

        item = {
            "SongName": song_name,
            "Parameters": synth_params,
            "Style": style,
            "Feature": feature,
            "Vector": None,
            "AudioPath": audio_path_value,
            "Meta": {
                "dataset": args.dataset_name,
                "seed": args.seed,
                "parent_preset": parent_name,
            },
        }
        dataset.append(item)

        if out_wav.exists():
            manifest_rows.append(
                {
                    "song_name": song_name,
                    "audio_path": _to_repo_rel(out_wav),
                    "sha256": _sha256_file(out_wav),
                    "dataset": args.dataset_name,
                    "seed": args.seed,
                    "parent_preset": parent_name,
                }
            )

        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{args.n}] generated: {song_name}")
        if (i + 1) % checkpoint_every == 0:
            _checkpoint()

    _checkpoint()

    print("")
    print(f"Wrote dataset JSON: {dataset_json}")
    print(f"Wrote manifest JSON: {out_dir / 'dataset_manifest.json'}")
    print(f"Audio dir: {audio_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
