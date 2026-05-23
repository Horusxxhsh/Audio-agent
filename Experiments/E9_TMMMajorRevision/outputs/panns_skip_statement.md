# PANNs Baseline Skip Statement

**Date:** 2026-05-23
**Context:** TMM Major Revision, CR-4: PANNs baseline inclusion

## Attempt

We attempted to run the PANNs CNN14 baseline under the same Protocol-A evaluation pipeline as the other methods. The PANNs inference package (`panns-inference`) requires a compatible version of `librosa` and `numba`, which are blocked under the current Python 3.12 environment.

## Environment

- OS: Ubuntu Linux (x86_64)
- Python: 3.12
- CUDA: Available (for GPU inference)

## Error

The PANNs CNN14 model could not be loaded due to a dependency conflict: `panns-inference` requires a specific version of `librosa` that depends on `numba`, which in turn has a compatibility issue with Python 3.12. The exact import failure occurs when attempting to load the PANNs model weights or run inference.

## Attempted Fixes

1. `pip install panns-inference` — failed due to librosa/numba dependency chain
2. Attempted to upgrade numba and librosa to compatible versions — did not resolve the issue
3. Attempted to isolate in a conda environment — the subagent was BLOCKED before completing environment setup

## Conclusion

The PANNs baseline could not be evaluated under the current environment. We report results only for encoders that pass the vector coverage gate in the current artifact. We do not claim exclusion of PANNs as evidence of superiority. The claim of "best full-coverage retrieval" is conditional on the evaluated baselines and does not preclude PANNs performance if evaluated under a compatible environment.

## Impact on Claims

This exclusion creates an asymmetric baseline gap. Future work should evaluate PANNs under a compatible environment (e.g., Python 3.10) and re-run the Protocol-A comparison.
