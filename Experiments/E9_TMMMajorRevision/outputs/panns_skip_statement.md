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
- torch: 2.11.0
- torchaudio: 2.11.0

## Diagnosis

The PANNs library itself is fully operational:

- `panns_inference` imports without error
- All dependencies (librosa, numba, torchlibrosa) are present and compatible under Python 3.10
- The encoder code (`panns_encoder.py`) and evaluation pipeline (`panns_baseline.py`) are syntactically correct and have been tested with synthetic audio

The blocking issue is **model weight download**: the CNN14 pretrained model (`Cnn14_mAP=0.431.pth`) is hosted on Zenodo (~312 MB). Downloading from this source at the current network conditions yields approximately 30--50 KB/s, meaning a full download would require **10--17 hours**. The partial download was repeatedly restarted because the `panns_inference` library checks file size against a 300 MB threshold before loading.

## Attempted Fixes

1. **`pip install panns-inference`** — Package installs and imports correctly. No dependency conflicts under Python 3.10.
2. **Torch Hub fallback (`torch.hub.load`)** — Blocked by PyTorch's trusted-repository policy requiring interactive confirmation; not suitable for automated pipelines.
3. **Direct wget download** — Download at ~30--50 KB/s for a 312 MB file; projected completion time 10+ hours. Infeasible within reasonable time bounds.
4. **Model mirror search** — No alternative mirror found (GitHub releases 404).
5. **Previous skip statement** — Previously attributed the failure to Python 3.12 / librosa / numba incompatibility. This was incorrect: the actual environment is Python 3.10 with fully compatible dependencies. The skip was caused by infrastructural download constraints, not software incompatibility.

## Audio Data

- Dataset: 1267 items in `dataset_full_vectors.json` (204 queries + 1063 KB)
- Audio files: 1057 `.wav` files present in `Data/Audio_Synthetic/`
- Audio paths in dataset use Windows-style paths (`C:\Users\80753\...`); these resolve to local files when used from within the repository.

## Conclusion

The PANNs CNN14 baseline could not be executed because the pretrained model weights cannot be downloaded in a practical timeframe from the current environment. This is an infrastructural limitation (network bandwidth to Zenodo), not a software defect.

## Impact on Claims

No PANNs results are included in the Protocol-A comparison. We do not claim superiority over PANNs; the claim of "best full-coverage retrieval" is conditional on the evaluated baselines. Future work should evaluate PANNs under an environment with adequate bandwidth to download the 312 MB model weights, or by pre-staging the model file locally.

## Reproduction Steps (for future reference)

```bash
# 1. Install panns-inference (already installed in this environment)
pip install panns-inference

# 2. Download model weights (requires ~312 MB bandwidth)
# The library auto-downloads from:
#   https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth
# To: ~/.panns_data/Cnn14_mAP=0.431.pth

# 3. Run evaluation
cd Experiments/E2_SOTABaselines
python panns_baseline.py --dataset ../../Experiments/dataset_full_vectors.json
```

If the model file is pre-staged at `~/.panns_data/Cnn14_mAP=0.431.pth`, steps 1--2 can be skipped and step 3 will complete in ~30--60 minutes (encoding + retrieval evaluation).
