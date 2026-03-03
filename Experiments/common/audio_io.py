from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import numpy as np


def _to_float32(waveform: np.ndarray) -> np.ndarray:
    """
    Convert PCM or float waveform to float32 in approximately [-1, 1].
    """
    x = np.asarray(waveform)
    if x.dtype.kind in ("i", "u"):
        # Integer PCM
        info = np.iinfo(x.dtype)
        denom = float(max(abs(info.min), info.max))
        x = x.astype(np.float32) / denom
    else:
        x = x.astype(np.float32, copy=False)
        # Some loaders may return floats outside [-1, 1]; normalize defensively.
        mx = float(np.max(np.abs(x))) if x.size else 0.0
        if mx > 1.5:
            x = x / (mx + 1e-9)
    return x


def read_audio(path: str) -> Tuple[np.ndarray, int]:
    """
    Read audio from a local file.

    Returns:
      waveform: np.ndarray, shape (n,) for mono or (n, c) for multi-channel, float32
      sr: int
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # Prefer soundfile when available (handles more formats robustly).
    try:
        import soundfile as sf  # type: ignore

        data, sr = sf.read(path, always_2d=False)
        return _to_float32(data), int(sr)
    except Exception:
        pass

    # Fallback: scipy wavfile (WAV-only).
    try:
        from scipy.io import wavfile  # type: ignore

        sr, data = wavfile.read(path)
        return _to_float32(data), int(sr)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Failed to read audio. Install `soundfile` (recommended) or `scipy`.\n"
            f"Path: {path}\n"
            f"Error: {e}"
        ) from e


def to_mono(waveform: np.ndarray) -> np.ndarray:
    x = np.asarray(waveform, dtype=np.float32)
    if x.ndim == 1:
        return x
    if x.ndim == 2:
        return np.mean(x, axis=1).astype(np.float32, copy=False)
    raise ValueError(f"Unsupported waveform shape: {x.shape}")


def resample(waveform: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if int(orig_sr) == int(target_sr):
        return np.asarray(waveform, dtype=np.float32)

    x = np.asarray(waveform, dtype=np.float32)

    # Polyphase resampling (preferred).
    try:
        from scipy.signal import resample_poly  # type: ignore

        return resample_poly(x, target_sr, orig_sr).astype(np.float32, copy=False)
    except Exception:
        # Fallback: linear interpolation (lower quality but dependency-free).
        n_in = x.shape[0]
        if n_in == 0:
            return x
        dur = n_in / float(orig_sr)
        n_out = max(1, int(round(dur * float(target_sr))))
        t_in = np.linspace(0.0, dur, num=n_in, endpoint=False, dtype=np.float64)
        t_out = np.linspace(0.0, dur, num=n_out, endpoint=False, dtype=np.float64)
        y = np.interp(t_out, t_in, x.astype(np.float64)).astype(np.float32)
        return y


def pad_or_trim(waveform: np.ndarray, target_len: int) -> np.ndarray:
    x = np.asarray(waveform, dtype=np.float32)
    if target_len <= 0:
        return x[:0]
    if x.shape[0] == target_len:
        return x
    if x.shape[0] > target_len:
        return x[:target_len]
    pad = target_len - x.shape[0]
    return np.pad(x, (0, pad), mode="constant")


@dataclass(frozen=True)
class SegmentConfig:
    segment_seconds: float
    hop_seconds: Optional[float] = None
    pad_last: bool = True


def iter_segments(waveform: np.ndarray, sr: int, cfg: SegmentConfig) -> Iterable[np.ndarray]:
    """
    Iterate fixed-length segments of a 1D waveform.
    """
    x = np.asarray(waveform, dtype=np.float32)
    if x.ndim != 1:
        raise ValueError("iter_segments expects mono waveform (1D). Call to_mono() first.")

    seg_len = int(round(float(cfg.segment_seconds) * float(sr)))
    if seg_len <= 0:
        yield x
        return

    hop = cfg.hop_seconds if cfg.hop_seconds is not None else cfg.segment_seconds
    hop_len = int(round(float(hop) * float(sr)))
    hop_len = max(1, hop_len)

    n = x.shape[0]
    start = 0
    while start < n:
        end = start + seg_len
        seg = x[start:end]
        if seg.shape[0] < seg_len:
            if cfg.pad_last and seg.shape[0] > 0:
                seg = pad_or_trim(seg, seg_len)
                yield seg
            break
        yield seg
        start += hop_len


def load_audio_mono(
    path: str,
    target_sr: int,
    segment_cfg: Optional[SegmentConfig] = None,
) -> Tuple[np.ndarray, int]:
    """
    Load audio, convert to mono, resample to target_sr. If segment_cfg is provided,
    returns the first segment (sufficient for embedding extraction baselines that
    expect fixed-length clips).
    """
    wav, sr = read_audio(path)
    wav = to_mono(wav)
    wav = resample(wav, orig_sr=sr, target_sr=target_sr)
    if segment_cfg is None:
        return wav, int(target_sr)
    segs = list(iter_segments(wav, int(target_sr), segment_cfg))
    return (segs[0] if segs else wav), int(target_sr)

