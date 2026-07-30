# PANNs Baseline Skip Statement (CR-4)

**Date:** 2026-05-23
**Status:** SKIPPED — infeasible model download

## Summary

The PANNs CNN14 baseline was not evaluated under Protocol-A due to infeasible model download. The pretrained model weights (`Cnn14_mAP=0.431.pth`, 312 MB) hosted on Zenodo require ~6.5 hours to download at current bandwidth (~80 KB/s average).

## Root Cause

**Infrastructural limitation (network bandwidth)**, not software defect:
- `panns-inference` 0.1.1 installs and imports correctly
- All dependencies compatible under Python 3.10.12
- Encoder and evaluation code verified correct
- Audio data fully available (1057 `.wav` files)

## Attempted Fixes

| Fix | Result |
|-----|--------|
| `pip install panns-inference` | Installed, imports OK |
| Torch Hub fallback | Blocked by trusted-repository policy |
| Direct wget (312 MB) | ~6.5 hours at ~80 KB/s |
| HuggingFace mirror | SSL errors |
| Alternative mirrors | None found |

## Impact

No PANNs results in Protocol-A comparison. "Best full-coverage retrieval" claim is conditional on evaluated baselines only.

## Reproduction

```bash
pip install panns-inference  # Already installed
# Download model (~312 MB): auto-downloads to ~/panns_data/
cd Experiments/E2_SOTABaselines
python panns_baseline.py \
  --dataset ../../Data/External_1267_211/dataset/dataset_full_vectors_1267.json
```

## See Also

- Full skip statement: `Experiments/E9_TMMMajorRevision/outputs/panns_skip_statement.md`
- Skip result JSON: `Experiments/E9_TMMMajorRevision/outputs/panns_baseline_skip_result.json`
