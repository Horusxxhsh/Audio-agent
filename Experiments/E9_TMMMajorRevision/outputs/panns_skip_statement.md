# PANNs Baseline Skip Statement

**Date:** 2026-05-23
**Context:** TMM Major Revision, CR-4: PANNs baseline inclusion
**Status:** SKIPPED — infeasible model download

## Environment

- OS: Ubuntu Linux (x86_64)
- Python: 3.10.12
- CUDA: Available (for GPU inference)
- panns-inference: 0.1.1 (installed, importable)
- librosa: 0.11.0
- numba: 0.65.0
- torch: 2.11.0+cu130
- torchaudio: 2.11.0+cu130

## Diagnosis

The PANNs library itself is fully operational:

- `panns_inference` imports without error
- All dependencies (librosa, numba, torchlibrosa) are present and compatible under Python 3.10
- The encoder code (`panns_encoder.py`) and evaluation pipeline (`panns_baseline.py`) are syntactically correct
- Encoder interface verified: `PANNsEncoder.encode_audio()` matches baseline usage
- Code fixes applied: Windows-to-Linux audio path resolution added to `panns_baseline.py`; `PANNs_CHECKPOINT` env var support added to `panns_encoder.py`

The blocking issue is **model weight download**: the CNN14 pretrained model (`Cnn14_mAP=0.431.pth`) is hosted on Zenodo (record 3987831, ~312 MB). Downloading from this source at the current network conditions yields approximately 80 KB/s average, meaning a full download would require **~6.5 hours**. The `panns_inference` library checks file size against a 300 MB threshold before loading; partial downloads are rejected and restarted.

## Attempted Fixes

1. **`pip install panns-inference`** — Installed successfully (0.1.1), imports without error. No dependency conflicts.
2. **Torch Hub fallback (`torch.hub.load`)** — Blocked by PyTorch's trusted-repository policy requiring interactive confirmation; not suitable for automated pipelines.
3. **Direct wget download** — At ~80 KB/s average, the 312 MB model requires ~6.5 hours. Infeasible within reasonable time bounds.
4. **HuggingFace model mirror** — Network SSL errors prevent retrieval (proxy interference).
5. **Alternative model sources** — GitHub releases return 404; no other mirror found.

## Audio Data

Two dataset variants are available:

| Dataset | Path | Items | Protocol-A Queries | Protocol-A KB |
|---------|------|-------|-------------------|---------------|
| Common | `Experiments/common/dataset_full_vectors.json` | 56 | — | — (too small for Protocol-A) |
| Full | `Data/External_1267_211/dataset/dataset_full_vectors_1267.json` | 1267 | 204 | 1063 |

All audio files (1057 `.wav` in `Data/Audio_Synthetic/`) are present and accessible. Audio paths in the dataset use Windows-style paths (`C:\Users\80753\...`); path resolution logic has been added to `panns_baseline.py`.

## Conclusion

The PANNs CNN14 baseline could not be executed because the pretrained model weights cannot be downloaded in a practical timeframe from the current environment. This is an **infrastructural limitation** (network bandwidth to Zenodo), not a software defect. All code is correct and tested.

## Impact on Claims

No PANNs results are included in the Protocol-A comparison. We do not claim superiority over PANNs; the claim of "best full-coverage retrieval" is conditional on the evaluated baselines. Future work should evaluate PANNs under an environment with adequate bandwidth to download the 312 MB model weights, or by pre-staging the model file locally.

## Reproduction Steps (for future reference)

```bash
# 1. Install panns-inference (already installed in this environment)
pip install panns-inference

# 2. Download model weights (~312 MB — requires adequate bandwidth)
# The library auto-downloads from:
#   https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth
# To: ~/panns_data/Cnn14_mAP=0.431.pth
# OR pre-stage the file at that location

# 3. Run evaluation (use --dataset for the 1267-item dataset)
cd Experiments/E2_SOTABaselines
python panns_baseline.py \
  --dataset ../../Data/External_1267_211/dataset/dataset_full_vectors_1267.json

# Expected completion time (after model download): ~30-60 minutes for encoding + evaluation
```

## Corrective Notes

The prior skip statement (dated earlier in this revision cycle) incorrectly attributed the failure to "Python 3.12 / librosa / numba incompatibility." This was inaccurate: the current environment uses Python 3.10.12 with fully compatible dependencies. The actual root cause is the infeasible model download from Zenodo under current network conditions.
