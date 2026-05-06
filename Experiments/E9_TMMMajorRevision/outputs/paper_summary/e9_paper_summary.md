# E9 TMM Major Revision Evidence Summary

## SOTA Vector Preparation

PaSST coverage gate: query=204/204, KB=1063/1063, ready=True.

## Unified Protocol-A Top-1

- CLAP: n=173, Norm.L2=0.1896, SwitchF1=0.8125
- FeatureNN: n=204, Norm.L2=0.2002, SwitchF1=0.7898
- PaSST: n=204, Norm.L2=0.1960, SwitchF1=0.7970
- TRR: n=204, Norm.L2=0.1454, SwitchF1=0.8630
- Wav2Vec: n=204, Norm.L2=0.1997, SwitchF1=0.7692

## Protocol-B EPR

- CLAP EPR-K5: n=173, Norm.L2=0.1642, Neff=4.4888
- FeatureNN EPR-K5: n=204, Norm.L2=0.1878, Neff=4.8828
- PaSST EPR-K5: n=204, Norm.L2=0.1808, Neff=4.9983
- TRR EPR-K5: n=204, Norm.L2=0.1334, Neff=4.2129
- Wav2Vec EPR-K5: n=204, Norm.L2=0.1838, Neff=4.6642

## Unified Near-Duplicate Canonical Row

Threshold 0.000 KB=1063 TRR Norm.L2=0.1454; this row must match the Table III Protocol-A TRR row.

## Protocol-B Validity

- CLAP: validity=1.0000, repair=0.9306
- FeatureNN: validity=1.0000, repair=0.9363
- PaSST: validity=1.0000, repair=0.9510
- TRR: validity=1.0000, repair=0.7843
- Wav2Vec: validity=1.0000, repair=0.8627

## EPR Sensitivity

TRR K/temperature/weighting sensitivity was exported; use the K=5, tau=0.05, softmax row as the primary manuscript setting.

## Claim Boundary

- Use Protocol-B EPR claims only for methods with complete source-method rows.
- Claim PaSST only when the PaSST coverage gate is ready; do not claim PANNs fairness while its runtime path is blocked.
- Do not use internal labels such as E8 current-code in the manuscript.
