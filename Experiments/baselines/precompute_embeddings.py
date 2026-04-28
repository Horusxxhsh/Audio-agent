#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.audio_io import SegmentConfig, load_audio_mono


DEFAULT_AUDIO_DIR = str(REPO_ROOT / "Data" / "Audio_Synthetic")
DEFAULT_TARGET_SR = 32000
DEFAULT_SEG_SECONDS = 10.0


@dataclass
class CoverageReport:
    model: str
    audio_dir: str
    target_sr: int
    segment_seconds: float
    overwrite: bool
    resume: bool
    report_only: bool
    total_wavs: int
    cache_ok: int
    cache_missing: int
    cache_corrupt: int
    computed: int
    skipped_existing: int
    failed: int
    embedding_dim: Optional[int]
    failures: List[str]
    missing_files: List[str]
    corrupt_files: List[str]
    started_at: str
    finished_at: str


def _list_wavs(audio_dir: str) -> List[str]:
    p = Path(audio_dir)
    if not p.exists():
        raise FileNotFoundError(audio_dir)
    return sorted(str(x) for x in p.glob("*.wav"))


def _safe_load_npy(path: str) -> Optional[np.ndarray]:
    try:
        arr = np.load(path)
        if arr is None:
            return None
        arr = np.asarray(arr)
        if arr.ndim != 1 or arr.size == 0:
            return None
        return arr
    except Exception:
        return None


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    n = float(np.linalg.norm(x))
    if n <= 0:
        return x
    return (x / n).astype(np.float32, copy=False)


class _PasstEmbedder:
    def __init__(self, arch: str, device: str):
        try:
            import torch  # noqa: F401
            from hear21passt.base import get_basic_model  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "PaSST requires optional deps. Install with:\n"
                "  python -m pip install -r Experiments/requirements_sota.txt\n"
                f"Import error: {e}"
            ) from e

        import torch

        self.torch = torch
        self.model = get_basic_model(arch=arch)
        self.model.eval()
        if device == "cuda" and torch.cuda.is_available():
            self.model.cuda()
            self.device = "cuda"
        else:
            self.device = "cpu"

    def embed(self, wav_32k_mono: np.ndarray) -> np.ndarray:
        x = np.asarray(wav_32k_mono, dtype=np.float32)
        x_t = self.torch.tensor(x).float().unsqueeze(0)
        if self.device == "cuda":
            x_t = x_t.cuda()
        with self.torch.no_grad():
            emb = self.model.get_scene_embeddings(x_t)
        if hasattr(emb, "detach"):
            emb = emb.detach()
        if getattr(emb, "device", None) is not None and str(emb.device) != "cpu":
            emb = emb.cpu()
        arr = np.asarray(emb.numpy()[0], dtype=np.float32)
        return _l2_normalize(arr)


class _PannsEmbedder:
    def __init__(self, checkpoint_path: Optional[str], device: str):
        try:
            from panns_inference import AudioTagging  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "PANNs requires optional deps. Install with:\n"
                "  python -m pip install -r Experiments/requirements_sota.txt\n"
                f"Import error: {e}"
            ) from e

        # panns-inference uses its own checkpoint download logic (Zenodo) if missing.
        self.tagger = AudioTagging(checkpoint_path=checkpoint_path, device=device)

    def embed(self, wav_32k_mono: np.ndarray) -> np.ndarray:
        x = np.asarray(wav_32k_mono, dtype=np.float32)[None, :]
        _clipwise, emb = self.tagger.inference(x)
        arr = np.asarray(emb[0], dtype=np.float32)
        return _l2_normalize(arr)


def _get_cache_path(wav_path: str, model: str) -> str:
    if model == "passt":
        return wav_path + ".passt.npy"
    if model == "panns":
        return wav_path + ".panns.npy"
    raise ValueError(model)


def _scan_cache(wavs: List[str], model: str) -> Tuple[int, List[str], List[str], Optional[int]]:
    ok = 0
    missing: List[str] = []
    corrupt: List[str] = []
    emb_dim: Optional[int] = None
    for wav_path in wavs:
        cache_path = _get_cache_path(wav_path, model)
        if not os.path.exists(cache_path):
            missing.append(wav_path)
            continue
        arr = _safe_load_npy(cache_path)
        if arr is None:
            corrupt.append(wav_path)
            continue
        if emb_dim is None:
            emb_dim = int(arr.shape[0])
        ok += 1
    return ok, missing, corrupt, emb_dim


def main() -> int:
    ap = argparse.ArgumentParser(description="Precompute PaSST/PANNs embeddings for Retrieval baselines.")
    ap.add_argument("--model", choices=["passt", "panns"], required=True, help="Embedding model to precompute.")
    ap.add_argument("--audio_dir", default=DEFAULT_AUDIO_DIR, help=f"Directory containing .wav files (default: {DEFAULT_AUDIO_DIR}).")
    ap.add_argument("--target_sr", type=int, default=DEFAULT_TARGET_SR, help="Target sample rate for embedding extraction (default: 32000).")
    ap.add_argument("--segment_seconds", type=float, default=DEFAULT_SEG_SECONDS, help="Clip length in seconds (default: 10.0).")
    ap.add_argument("--resume", action="store_true", help="Skip existing readable cache files (default behavior).")
    ap.add_argument("--overwrite", action="store_true", help="Recompute and overwrite existing cache files.")
    ap.add_argument("--report_out", default="", help="Optional path to write a JSON coverage report.")
    ap.add_argument("--report_only", action="store_true", help="Only scan cache coverage; do not import model deps or compute embeddings.")
    ap.add_argument("--missing_out", default="", help="Optional path to write newline-separated wav paths missing cache.")
    ap.add_argument("--corrupt_out", default="", help="Optional path to write newline-separated wav paths with unreadable cache.")

    # Model-specific knobs
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda"], help="Device for embedding extraction (default: cuda if available).")
    ap.add_argument("--passt_arch", default="passt_s_swa_p16_128_ap476", help="PaSST arch name (hear21passt).")
    ap.add_argument("--panns_ckpt", default="", help="Optional PANNs checkpoint path (if empty, panns-inference will download/cache).")

    args = ap.parse_args()

    started = datetime.utcnow().isoformat() + "Z"

    wavs = _list_wavs(args.audio_dir)
    failures: List[str] = []
    computed = 0
    skipped = 0
    failed = 0
    emb_dim_from_compute: Optional[int] = None

    # Default behavior: skip existing cache (resume) unless --overwrite is provided.
    resume = bool(args.resume) or not bool(args.overwrite)
    overwrite = bool(args.overwrite)

    if not args.report_only:
        if args.model == "passt":
            embedder = _PasstEmbedder(arch=args.passt_arch, device=args.device)
        else:
            ckpt = args.panns_ckpt.strip() or None
            embedder = _PannsEmbedder(checkpoint_path=ckpt, device=args.device)

        seg_cfg = SegmentConfig(segment_seconds=float(args.segment_seconds), hop_seconds=None, pad_last=True)

        for wav_path in wavs:
            cache_path = _get_cache_path(wav_path, args.model)

            if os.path.exists(cache_path) and not overwrite:
                if resume:
                    arr = _safe_load_npy(cache_path)
                    if arr is not None:
                        emb_dim_from_compute = int(arr.shape[0])
                        skipped += 1
                        continue

            try:
                wav, _sr = load_audio_mono(wav_path, target_sr=int(args.target_sr), segment_cfg=seg_cfg)
                emb = embedder.embed(wav)
                emb = np.asarray(emb, dtype=np.float32).reshape(-1)
                if emb_dim_from_compute is None:
                    emb_dim_from_compute = int(emb.shape[0])
                np.save(cache_path, emb)
                computed += 1
            except Exception as e:
                failed += 1
                failures.append(wav_path)
                print(f"[FAIL] {wav_path}: {e}")

    cache_ok, missing_files, corrupt_files, emb_dim_from_scan = _scan_cache(wavs, args.model)

    finished = datetime.utcnow().isoformat() + "Z"
    report = CoverageReport(
        model=str(args.model),
        audio_dir=str(args.audio_dir),
        target_sr=int(args.target_sr),
        segment_seconds=float(args.segment_seconds),
        overwrite=overwrite,
        resume=resume,
        report_only=bool(args.report_only),
        total_wavs=len(wavs),
        cache_ok=int(cache_ok),
        cache_missing=int(len(missing_files)),
        cache_corrupt=int(len(corrupt_files)),
        computed=computed,
        skipped_existing=skipped,
        failed=failed,
        embedding_dim=emb_dim_from_scan or emb_dim_from_compute,
        failures=failures,
        missing_files=missing_files,
        corrupt_files=corrupt_files,
        started_at=started,
        finished_at=finished,
    )

    print(
        f"[Done] model={report.model} total_wavs={report.total_wavs} "
        f"cache_ok={report.cache_ok} cache_missing={report.cache_missing} cache_corrupt={report.cache_corrupt} "
        f"computed={report.computed} skipped={report.skipped_existing} failed={report.failed} dim={report.embedding_dim}"
    )

    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        print(f"[Report] Wrote: {out_path}")

    if args.missing_out:
        out_path = Path(args.missing_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(report.missing_files) + ("\n" if report.missing_files else ""), encoding="utf-8")
        print(f"[Missing] Wrote: {out_path}")

    if args.corrupt_out:
        out_path = Path(args.corrupt_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(report.corrupt_files) + ("\n" if report.corrupt_files else ""), encoding="utf-8")
        print(f"[Corrupt] Wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
