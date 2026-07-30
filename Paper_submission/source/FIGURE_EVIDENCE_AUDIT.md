# Figure and Data Evidence Audit

Date: 2026-05-23

Scope: `Paper/content.tex`, `Paper/supplementary.tex`, `Paper/figures/`, and the local experiment artifacts used by the paper-facing figures.

## Verdict

The core quantitative claim is currently evidence-backed: TRR is the best full-coverage Protocol-A retrieval method on normalized L2, Recall, Cosine, and SwitchF1, and TRR EPR-K5 further improves normalized L2 while retaining retrieved-neighborhood provenance. The manuscript should keep this claim bounded to the current 204-query guitar-effect benchmark.

The figures are now separated into three evidence classes:

| Class | Figures / Tables | Audit status | Claim role |
| --- | --- | --- | --- |
| Primary quantitative evidence | Main Protocol-A/B table, robustness curves, EPR sensitivity curve | PASS, values match E9 CSV/JSON exports | Supports the main performance claim |
| Diagnostic evidence | TRR Gram/t-SNE, mechanism/layer plot, per-parameter error plot, fusion plots, listening boxplots | PASS after script repair, but diagnostic only | Explains mechanism, boundary, and perceptual context |
| Non-result illustrations | Supplementary pipeline and adaptive-agent example | PASS as illustrations only | Must not be used as performance evidence |

## Key Checks

1. Protocol-A/B values in the main table match local E9 artifacts:
   - `TRR top-1 Norm.L2 = 0.14544972956836597`, rounded to `0.1454`.
   - `TRR EPR-K5 Norm.L2 = 0.1333506615946094`, rounded to `0.1334`.
   - `TRR PNR@5 threshold 0.10 = 0.75`.
   - `TRR EPR-K5 effective exemplars = 4.212860291080392`, max weight `0.34381110934019615`.

2. Robustness curves match exported E9 artifacts:
   - Near-duplicate thresholds `0.010` and `0.020` match `0.1968` and `0.2510`.
   - Hard-split thresholds `0.010`, `0.020`, and `0.050` match `0.2065`, `0.2424`, and `0.2668`.
   - Boundary: CLAP can be lower on partial-coverage hard-split subsets at `0.010` and `0.020`; the paper must only claim TRR as the best full-coverage method there.

3. Listening-study figures are backed by `Experiments/mushura/mushra.csv`:
   - 26 participants, 910 valid ratings.
   - Trials 2--5 support TRR-based system over manual baseline in this dataset.
   - Trials 6--10 support parity-style interpretation against MusicGen, not superiority.
   - The study lacks a low-quality anchor and device/provenance metadata, so it is not a standard MUSHRA validation.

4. Fusion figures are diagnostic only:
   - `fusion_weight_distribution.pdf` and `fusion_failure_analysis.png` derive from `Experiments/Fusion/fusion_weight_analysis.csv` and related generation code.
   - They do not establish the main performance claim and should remain boundary/robustness diagnostics.

## Repairs Made During Audit

- Repaired `Experiments/TextureResonance/gram_matrix_heatmap.py` to read cached `Vectors["TRR"]` instead of using `Vectors["Wav2Vec"]` as a proxy.
- Repaired `Experiments/TextureResonance/trr_tsne_visualization.py` to compare real `TRR` vectors against real `Wav2Vec` vectors over the same valid item set.
- Repaired `Experiments/E5_Ablations/per_param_analysis.py` to use the current TMM 204-query split and the `TRR` vector key.
- Added `Experiments/E5_Ablations/plot_p0_mechanism_figures.py` to regenerate the mechanism/layer diagnostic from `p0_trr_mechanism_summary.csv`.
- Added `Experiments/E9_TMMMajorRevision/plot_paper_figures.py` to regenerate robustness and EPR paper figures from exported CSV/JSON artifacts.
- Updated the manuscript TRR dimensionality from `D=32 / 1024` to `D=64 / 4096`, matching the cached TRR vectors and local retrieval adapter.
- Added a paper-facing artifact provenance table to prevent framework/illustration figures from being interpreted as result evidence.

## Remaining Evidence Caveat

`Experiments/E9_TMMMajorRevision/outputs/passt_vectors/dataset_full_vectors_1267_augmented.json` is currently a Git LFS pointer, and `git lfs` is not installed in this environment. Therefore the existing E9 PaSST-inclusive summary files are internally consistent and table values match them, but a clean checkout cannot fully regenerate the PaSST-inclusive E9 exports until the LFS object is restored or vendored as a normal artifact.

This is a reproducibility packaging blocker, not evidence that the current CSV/JSON summaries are fabricated. It should be fixed before final archival submission.
