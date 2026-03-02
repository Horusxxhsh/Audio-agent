import argparse
import csv
import os
import shutil
import tempfile
from dataclasses import dataclass

from frechet_audio_distance import CLAPScore, FrechetAudioDistance


@dataclass(frozen=True)
class FadConfig:
    model_name: str
    sample_rate: int
    channels: int
    label: str


def _compute_rms(data) -> float:
    import numpy as np

    x = np.asarray(data, dtype=np.float64)
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x * x)))


def _convert_biquad_48k_to_sr(
    a1_48k: float,
    a2_48k: float,
    b0_48k: float,
    b1_48k: float,
    b2_48k: float,
    new_sample_rate: int,
    old_sample_rate: int = 48000,
) -> tuple[float, float, float, float, float]:
    import numpy as np

    if new_sample_rate == old_sample_rate:
        return a1_48k, a2_48k, b0_48k, b1_48k, b2_48k

    k_over_q = (2.0 - (2.0 * a2_48k)) / (a2_48k - a1_48k + 1.0)
    k = float(np.sqrt((a1_48k + a2_48k + 1.0) / (a2_48k - a1_48k + 1.0)))
    q = k / k_over_q
    vb = (b0_48k - b2_48k) / (1.0 - a2_48k)
    vh = (b0_48k - b1_48k + b2_48k) / (a2_48k - a1_48k + 1.0)
    vl = (b0_48k + b1_48k + b2_48k) / (a1_48k + a2_48k + 1.0)

    k = float(np.tan(np.arctan(k) * old_sample_rate / float(new_sample_rate)))
    k_sq = k * k
    common = 1.0 / (1.0 + (k / q) + k_sq)

    a1 = 2.0 * (k_sq - 1.0) * common
    a2 = (1.0 - (k / q) + k_sq) * common
    b0 = (vh + (vb * k / q) + (vl * k_sq)) * common
    b1 = 2.0 * ((vl * k_sq) - vh) * common
    b2 = (vh - (vb * k / q) + (vl * k_sq)) * common
    return float(a1), float(a2), float(b0), float(b1), float(b2)


def _k_weighted_audio(data, sr: int):
    import numpy as np
    from scipy.signal import lfilter

    x = np.asarray(data, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]

    x = x - np.mean(x, axis=0, keepdims=True)

    shelf_a1, shelf_a2, shelf_b0, shelf_b1, shelf_b2 = _convert_biquad_48k_to_sr(
        a1_48k=-1.69065929318241,
        a2_48k=0.73248077421585,
        b0_48k=1.53512485958697,
        b1_48k=-2.69169618940638,
        b2_48k=1.19839281085285,
        new_sample_rate=sr,
    )
    hp_a1, hp_a2, hp_b0, hp_b1, hp_b2 = _convert_biquad_48k_to_sr(
        a1_48k=-1.99004745483398,
        a2_48k=0.99007225036621,
        b0_48k=1.0,
        b1_48k=-2.0,
        b2_48k=1.0,
        new_sample_rate=sr,
    )

    y = lfilter([shelf_b0, shelf_b1, shelf_b2], [1.0, shelf_a1, shelf_a2], x, axis=0)
    y = lfilter([hp_b0, hp_b1, hp_b2], [1.0, hp_a1, hp_a2], y, axis=0)

    return y


def _integrated_lufs(data, sr: int) -> float:
    import numpy as np

    x = _k_weighted_audio(data, sr)
    x = np.mean(x, axis=1)
    if x.size == 0:
        return float("-inf")

    block_len = max(1, int(round(0.4 * sr)))
    hop = max(1, int(round(0.1 * sr)))

    ms_blocks = []
    for start in range(0, max(1, x.shape[0] - block_len + 1), hop):
        block = x[start:start + block_len]
        if block.shape[0] < block_len:
            break
        ms = float(np.mean(block * block))
        ms_blocks.append(ms)

    if not ms_blocks:
        ms = float(np.mean(x * x))
        return float(-0.691 + 10.0 * np.log10(ms + 1e-18))

    ms_blocks = np.asarray(ms_blocks, dtype=np.float64)
    ms_ungated = float(np.mean(ms_blocks))
    lufs_ungated = float(-0.691 + 10.0 * np.log10(ms_ungated + 1e-18))

    abs_gate = -70.0
    rel_gate = lufs_ungated - 10.0
    gate = max(abs_gate, rel_gate)
    mask = (-0.691 + 10.0 * np.log10(ms_blocks + 1e-18)) >= gate
    if not np.any(mask):
        return lufs_ungated

    ms_gated = float(np.mean(ms_blocks[mask]))
    return float(-0.691 + 10.0 * np.log10(ms_gated + 1e-18))



def _read_audio(path: str):
    import soundfile as sf
    import numpy as np

    data, sr = sf.read(path, always_2d=True)
    if data.size == 0 or sr <= 0:
        raise RuntimeError(f"Empty audio or invalid sample rate: {path}")
    return data.astype(np.float32), int(sr)


def _write_segments_from_array(
    data,
    sr: int,
    output_dir: str,
    base_name: str,
    segment_seconds: float,
    hop_seconds: float,
) -> None:
    import soundfile as sf
    import numpy as np

    if segment_seconds <= 0:
        out_path = os.path.join(output_dir, base_name)
        sf.write(out_path, np.asarray(data, dtype=np.float32), sr, subtype="PCM_16")
        return

    seg_len = int(round(segment_seconds * sr))
    hop_len = int(round((hop_seconds if hop_seconds > 0 else segment_seconds) * sr))
    seg_len = max(seg_len, 1)
    hop_len = max(hop_len, 1)

    total = data.shape[0]
    if total <= seg_len:
        out_path = os.path.join(output_dir, f"seg_00000_{base_name}")
        sf.write(out_path, data.astype(np.float32), sr, subtype="PCM_16")
        return

    idx = 0
    for start in range(0, total - seg_len + 1, hop_len):
        seg = data[start:start + seg_len]
        out_path = os.path.join(output_dir, f"seg_{idx:05d}_{base_name}")
        sf.write(out_path, seg.astype(np.float32), sr, subtype="PCM_16")
        idx += 1

    if idx == 0:
        out_path = os.path.join(output_dir, f"seg_00000_{base_name}")
        sf.write(out_path, data.astype(np.float32), sr, subtype="PCM_16")


def _write_rms_matched_wav(
    ref_wav: str,
    eval_wav: str,
    output_path: str,
    match_duration: bool,
    no_boost: bool,
    max_gain: float,
    min_gain: float,
) -> None:
    import soundfile as sf
    import numpy as np

    ref_data, ref_sr = _read_audio(ref_wav)
    eval_data, eval_sr = _read_audio(eval_wav)

    if match_duration:
        ref_dur = ref_data.shape[0] / float(ref_sr)
        eval_dur = eval_data.shape[0] / float(eval_sr)
        target_dur = min(ref_dur, eval_dur)
        ref_n = max(1, int(target_dur * ref_sr))
        eval_n = max(1, int(target_dur * eval_sr))
        ref_data = ref_data[:ref_n]
        eval_data = eval_data[:eval_n]

    ref_rms = _compute_rms(ref_data)
    eval_rms = _compute_rms(eval_data)
    if ref_rms > 0.0 and eval_rms > 0.0:
        gain = ref_rms / eval_rms
        if no_boost and gain > 1.0:
            gain = 1.0
        gain = max(min_gain, min(max_gain, gain))
        eval_data = eval_data * float(gain)

    sf.write(output_path, np.asarray(eval_data, dtype=np.float32), eval_sr, subtype="FLOAT")


def write_wav_segments(input_wav: str, output_dir: str, segment_seconds: float, hop_seconds: float) -> None:
    data, sr = _read_audio(input_wav)
    _write_segments_from_array(data, sr, output_dir, os.path.basename(input_wav), segment_seconds, hop_seconds)


def find_reference_wav_path(csv_path: str, audio_id: str) -> str:
    encodings_to_try = ["utf-8", "utf-8-sig", "cp936", "gbk", "latin-1"]
    last_error: Exception | None = None

    for enc in encodings_to_try:
        try:
            with open(csv_path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    if row[0] == audio_id:
                        if len(row) < 2:
                            raise RuntimeError(f"CSV row for {audio_id} has no wav path column: {row}")
                        return row[1]
        except UnicodeDecodeError as e:
            last_error = e
            continue

    if last_error is not None:
        raise last_error
    raise FileNotFoundError(f"Audio id not found in CSV: {audio_id}")


def find_reference_metadata(csv_path: str, audio_id: str) -> tuple[str, str]:
    encodings_to_try = ["utf-8", "utf-8-sig", "cp936", "gbk", "latin-1"]
    last_error: Exception | None = None

    for enc in encodings_to_try:
        try:
            with open(csv_path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    if row[0] == audio_id:
                        wav_path = row[1] if len(row) > 1 else ""
                        caption = row[2] if len(row) > 2 else ""
                        return wav_path, caption
        except UnicodeDecodeError as e:
            last_error = e
            continue

    if last_error is not None:
        raise last_error
    raise FileNotFoundError(f"Audio id not found in CSV: {audio_id}")


def _resolve_repo_audio_path(raw_path: str) -> str:
    """
    Best-effort path resolver for CSVs authored on other machines (e.g., Windows).

    We keep the CSV as-is for provenance, but make local evaluation runnable by
    mapping the audio filename to known local folders when the original path
    does not exist.
    """
    if not raw_path:
        return raw_path
    if os.path.exists(raw_path):
        return raw_path

    normalized = raw_path.replace("\\", "/")
    basename = os.path.basename(normalized)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(repo_root, "musiccaps_guitar_solo", basename),
        os.path.join(repo_root, "Data", "Audio_Synthetic", basename),
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return cand

    return raw_path


def compute_fad_between_files(
    config: FadConfig,
    ref_wav: str,
    eval_wav: str,
    segment_seconds: float,
    hop_seconds: float,
    match_ref_rms: bool,
    match_duration: bool,
    match_ref_lufs: bool,
    no_boost: bool,
    max_gain: float,
    min_gain: float,
) -> float:
    import math

    fad = FrechetAudioDistance(
        model_name=config.model_name,
        sample_rate=config.sample_rate,
        channels=config.channels,
        verbose=False,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        background_dir = os.path.join(tmpdir, "background")
        eval_dir = os.path.join(tmpdir, "eval")
        os.makedirs(background_dir, exist_ok=True)
        os.makedirs(eval_dir, exist_ok=True)

        ref_data, ref_sr = _read_audio(ref_wav)
        eval_data, eval_sr = _read_audio(eval_wav)

        if match_duration:
            ref_dur = ref_data.shape[0] / float(ref_sr)
            eval_dur = eval_data.shape[0] / float(eval_sr)
            target_dur = min(ref_dur, eval_dur)
            ref_n = max(1, int(target_dur * ref_sr))
            eval_n = max(1, int(target_dur * eval_sr))
            ref_data = ref_data[:ref_n]
            eval_data = eval_data[:eval_n]

        if match_ref_lufs:
            ref_lufs = _integrated_lufs(ref_data, ref_sr)
            eval_lufs = _integrated_lufs(eval_data, eval_sr)
            if math.isfinite(ref_lufs) and math.isfinite(eval_lufs):
                gain_db = ref_lufs - eval_lufs
                gain = 10.0 ** (gain_db / 20.0)
                if no_boost and gain > 1.0:
                    gain = 1.0
                gain = max(min_gain, min(max_gain, gain))
                eval_data = eval_data * float(gain)
        elif match_ref_rms:
            ref_rms = _compute_rms(ref_data)
            eval_rms = _compute_rms(eval_data)
            if ref_rms > 0.0 and eval_rms > 0.0:
                gain = ref_rms / eval_rms
                if no_boost and gain > 1.0:
                    gain = 1.0
                gain = max(min_gain, min(max_gain, gain))
                eval_data = eval_data * float(gain)

        _write_segments_from_array(ref_data, ref_sr, background_dir, os.path.basename(ref_wav), segment_seconds, hop_seconds)
        _write_segments_from_array(eval_data, eval_sr, eval_dir, os.path.basename(eval_wav), segment_seconds, hop_seconds)

        return float(fad.score(background_dir=background_dir, eval_dir=eval_dir))


def kl_divergence(p, q, eps: float = 1e-8) -> float:
    import numpy as np

    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    p = np.clip(p, eps, None)
    q = np.clip(q, eps, None)
    p = p / (p.sum() + eps)
    q = q / (q.sum() + eps)
    return float(np.sum(p * np.log(p / q)))


class PannTagger:
    def __init__(self):
        self._fad = FrechetAudioDistance(model_name="pann", sample_rate=32000, channels=1, verbose=False)
        self._device = self._fad.device

    def predict_clipwise(self, audio_32k_mono):
        import torch

        with torch.no_grad():
            x = torch.tensor(audio_32k_mono).float().unsqueeze(0).to(self._device)
            out = self._fad.model(x, None)
            clipwise = out["clipwise_output"][0]
            if clipwise.device.type != "cpu":
                clipwise = clipwise.cpu()
            return clipwise.detach().numpy()


def compute_pann_label_distribution(wav_path: str, segment_seconds: float, hop_seconds: float, tagger: PannTagger):
    import numpy as np
    from frechet_audio_distance.utils import load_audio_task

    with tempfile.TemporaryDirectory() as tmpdir:
        seg_dir = os.path.join(tmpdir, "segs")
        os.makedirs(seg_dir, exist_ok=True)
        write_wav_segments(wav_path, seg_dir, segment_seconds, hop_seconds)

        seg_files = [os.path.join(seg_dir, f) for f in sorted(os.listdir(seg_dir))]
        if not seg_files:
            raise RuntimeError(f"No audio segments produced from: {wav_path}")

        preds = []
        for fp in seg_files:
            audio = load_audio_task(fp, sample_rate=32000, channels=1, dtype="float32")
            preds.append(tagger.predict_clipwise(audio))

        mean_pred = np.mean(np.stack(preds, axis=0), axis=0)
        mean_pred = np.maximum(mean_pred, 0.0)
        mean_pred = mean_pred / (float(np.sum(mean_pred)) + 1e-8)
        return mean_pred


def make_caption_csv(csv_path: str, caption: str, n_rows: int) -> None:
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["caption"])
        for _ in range(max(1, n_rows)):
            writer.writerow([caption])


def compute_clap_score(caption: str, wav_path: str, segment_seconds: float, hop_seconds: float, submodel_name: str) -> tuple[float, float]:
    import torch

    def get_download_name() -> str:
        if submodel_name == "630k-audioset":
            return "630k-audioset-best.pt"
        if submodel_name == "630k":
            return "630k-best.pt"
        if submodel_name == "music_audioset":
            return "music_audioset_epoch_15_esc_90.14.pt"
        if submodel_name == "music_speech":
            return "music_speech_epoch_15_esc_89.25.pt"
        if submodel_name == "music_speech_audioset":
            return "music_speech_audioset_epoch_15_esc_89.98.pt"
        return "630k-audioset-best.pt"

    def is_corrupt_ckpt_error(e: Exception) -> bool:
        msg = str(e)
        return "PytorchStreamReader failed reading zip archive" in msg or "failed finding central directory" in msg

    def delete_cached_ckpt():
        ckpt_dir = torch.hub.get_dir()
        model_path = os.path.join(ckpt_dir, get_download_name())
        if os.path.exists(model_path):
            try:
                os.remove(model_path)
            except OSError:
                pass

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_dir = os.path.join(tmpdir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        write_wav_segments(wav_path, audio_dir, segment_seconds, hop_seconds)
        audio_files = [f for f in os.listdir(audio_dir) if f.lower().endswith(".wav")]
        caption_csv = os.path.join(tmpdir, "captions.csv")
        make_caption_csv(caption_csv, caption, len(audio_files))

        try:
            clap = CLAPScore(submodel_name=submodel_name, verbose=False, enable_fusion=False)
            mean, std = clap.score(text_path=caption_csv, audio_dir=audio_dir, text_column="caption")
            return float(mean), float(std)
        except Exception as e:
            if not is_corrupt_ckpt_error(e):
                raise
            delete_cached_ckpt()
            clap = CLAPScore(submodel_name=submodel_name, verbose=False, enable_fusion=False)
            mean, std = clap.score(text_path=caption_csv, audio_dir=audio_dir, text_column="caption")
            return float(mean), float(std)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", dest="csv_path", default="guitar_solo_evaluation_metadata.csv")
    parser.add_argument("--id", dest="audio_id", default="XQB27QPic3k")
    parser.add_argument(
        "--generated",
        dest="generated_wav",
        default="generated_input.wav",
    )
    parser.add_argument(
        "--final",
        dest="final_wav",
        default="final_output.wav",
    )
    parser.add_argument("--caption", dest="caption", default="")
    parser.add_argument("--segment-seconds", dest="segment_seconds", type=float, default=0.0)
    parser.add_argument("--hop-seconds", dest="hop_seconds", type=float, default=0.0)
    parser.add_argument("--match-ref-rms", dest="match_ref_rms", action="store_true")
    parser.add_argument("--match-ref-rms-final", dest="match_ref_rms_final", action="store_true")
    parser.add_argument("--match-ref-lufs", dest="match_ref_lufs", action="store_true")
    parser.add_argument("--match-duration", dest="match_duration", action="store_true")
    parser.add_argument("--no-boost", dest="no_boost", action="store_true")
    parser.add_argument("--max-gain", dest="max_gain", type=float, default=4.0)
    parser.add_argument("--min-gain", dest="min_gain", type=float, default=0.25)
    parser.add_argument("--kl", dest="with_kl", action="store_true")
    parser.add_argument("--clap", dest="with_clap", action="store_true")
    parser.add_argument("--clap-submodel", dest="clap_submodel", default="630k-audioset")
    parser.add_argument(
        "--extra",
        dest="extra_models",
        action="append",
        choices=["pann_32k", "clap_48k", "encodec_24k"],
        default=[],
    )
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv_path)
    ref_wav, csv_caption = find_reference_metadata(csv_path, args.audio_id)
    ref_wav = _resolve_repo_audio_path(ref_wav)
    caption = args.caption or csv_caption

    print(f"CSV: {csv_path}")
    print(f"Reference ({args.audio_id}): {ref_wav}")
    print(f"Generated: {args.generated_wav}")
    print(f"Final: {args.final_wav}")
    if caption:
        print(f"Caption: {caption}")
    if args.segment_seconds > 0:
        print(f"Segmentation: segment_seconds={args.segment_seconds}, hop_seconds={args.hop_seconds if args.hop_seconds > 0 else args.segment_seconds}")
    if args.match_ref_rms:
        print("Preprocess: match_ref_rms=on")
    if args.match_ref_rms_final:
        print("Preprocess: match_ref_rms_final=on")
    if args.match_ref_lufs:
        print("Preprocess: match_ref_lufs=on")
    if args.match_duration:
        print("Preprocess: match_duration=on")
    if args.no_boost:
        print("Preprocess: no_boost=on")

    missing = [p for p in [csv_path, ref_wav, args.generated_wav, args.final_wav] if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError("Missing files:\n" + "\n".join(missing))

    temp_holder = None
    final_eval_wav = args.final_wav
    if args.match_ref_rms_final:
        temp_holder = tempfile.TemporaryDirectory()
        final_eval_wav = os.path.join(temp_holder.name, "final_output_rms_matched.wav")
        _write_rms_matched_wav(
            ref_wav=ref_wav,
            eval_wav=args.final_wav,
            output_path=final_eval_wav,
            match_duration=args.match_duration,
            no_boost=args.no_boost,
            max_gain=args.max_gain,
            min_gain=args.min_gain,
        )

    configs = [FadConfig(model_name="vggish", sample_rate=16000, channels=1, label="FAD_vgg")]
    if "pann_32k" in args.extra_models:
        configs.append(FadConfig(model_name="pann", sample_rate=32000, channels=1, label="FAD_pann_32k"))
    if "clap_48k" in args.extra_models:
        configs.append(FadConfig(model_name="clap", sample_rate=48000, channels=1, label="FAD_clap_48k"))
    if "encodec_24k" in args.extra_models:
        configs.append(FadConfig(model_name="encodec", sample_rate=24000, channels=1, label="FAD_encodec_24k"))

    for cfg in configs:
        try:
            s1 = compute_fad_between_files(
                cfg,
                ref_wav,
                args.generated_wav,
                args.segment_seconds,
                args.hop_seconds,
                args.match_ref_rms,
                args.match_duration,
                args.match_ref_lufs,
                args.no_boost,
                args.max_gain,
                args.min_gain,
            )
            s2 = compute_fad_between_files(
                cfg,
                ref_wav,
                final_eval_wav,
                args.segment_seconds,
                args.hop_seconds,
                False if args.match_ref_rms_final else args.match_ref_rms,
                args.match_duration,
                args.match_ref_lufs,
                args.no_boost,
                args.max_gain,
                args.min_gain,
            )
        except Exception as e:
            print(f"{cfg.label} ERROR: {e}")
            continue

        print(f"{cfg.label}: ref vs generated_input.wav = {s1:.6f}")
        print(f"{cfg.label}: ref vs final_output.wav    = {s2:.6f}")

    if args.with_kl:
        try:
            tagger = PannTagger()
            pref = compute_pann_label_distribution(ref_wav, args.segment_seconds, args.hop_seconds, tagger)
            pgen = compute_pann_label_distribution(args.generated_wav, args.segment_seconds, args.hop_seconds, tagger)
            pfin = compute_pann_label_distribution(final_eval_wav, args.segment_seconds, args.hop_seconds, tagger)
            print(f"KL_pann: ref || generated_input.wav = {kl_divergence(pref, pgen):.6f}")
            print(f"KL_pann: ref || final_output.wav    = {kl_divergence(pref, pfin):.6f}")
        except Exception as e:
            print(f"KL_pann ERROR: {e}")

    if args.with_clap:
        if not caption:
            print("CLAP_scr ERROR: no caption available (use --caption or ensure CSV has a description column).")
        else:
            try:
                mean_g, std_g = compute_clap_score(caption, args.generated_wav, args.segment_seconds, args.hop_seconds, args.clap_submodel)
                mean_f, std_f = compute_clap_score(caption, final_eval_wav, args.segment_seconds, args.hop_seconds, args.clap_submodel)
                print(f"CLAP_scr: generated_input.wav mean={mean_g:.6f} std={std_g:.6f}")
                print(f"CLAP_scr: final_output.wav    mean={mean_f:.6f} std={std_f:.6f}")
            except Exception as e:
                print(f"CLAP_scr ERROR: {e}")

    print("Note: TRILL-based FAD is not available in this environment (no TensorFlow/TF-Hub).")
    print("If you must compute FAD_trill, install tensorflow + tensorflow_hub and use a TRILL embedding pipeline.")
    if temp_holder is not None:
        temp_holder.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
