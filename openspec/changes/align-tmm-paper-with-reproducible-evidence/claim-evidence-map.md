# Claim -> Evidence Baseline (No-Fabrication)

## Canonical Dataset/Split Facts

- Total paired records loadable from current repository: **50**
  - Evidence: `Experiments/common/dataset_loader.py` + `music_info.db` + `audio_info.db`
- Available synthetic audio files in `Data/Audio_Synthetic/`: **50** `.wav`
- Primary objective benchmark used in paper tables: **5-query held-out subset**
  - Corresponding retrieval KB under same split: **45**
- Layer-sweep diagnostic file `Experiments/TextureResonance/layer_selection_results.csv`: **n_samples=31**
  - This diagnostic must not be conflated with the 5-query held-out benchmark.

## Metric Naming Convention (Global)

- `Param. Dist.`: operational RMSE over flattened numeric parameter leaves (missing keys as zero).
- `Acc@0.1`: fraction within ±0.1 tolerance under the same flattened representation.
- `Recall`: recall over active/non-zero parameters under the same representation.
- `Cosine`: cosine similarity on flattened parameter vectors.
- `Module`: Jaccard over active DSP modules.

Rule: Do not mix different definitions/scales under one metric name (especially `L2`).

## Claim Mapping

| Claim (paper) | Evidence Source | Status | Action |
|---|---|---|---|
| TRR/Text/FeatureNN/Wav2Vec table with 0.0980/0.1512/etc | `retrieval_comparison_report.md` (depends on a missing legacy full-vector artifact) | Unsupported | Remove quantitative claim or downgrade to qualitative statement |
| LLM enhancement table with 0.0852 and stress tests 28.94/29.30 | `retrieval_comparison_report.md` (same missing dependency) | Unsupported | Remove quantitative claim; keep only non-quantitative rationale/future work |
| TRR vs MFCC vs ModSpec (13.57/24.95/32.02, N=5) | `Experiments/TextureResonance/texture_representation_comparison.csv` | Supported | Keep |
| Fusion ablation + weight stats + beta sweep | `Experiments/Fusion/fusion_beta_sensitivity.csv` | Supported | Keep |
| MUSHRA 26 participants / 910 ratings and grouped stats | `Experiments/mushura/mushra.csv` (after cleaning) + `Experiments/mushura/results_report.md` | Supported | Keep with explicit cleaning rule |
| Layer sweep summary | `Experiments/TextureResonance/layer_selection_results.csv` | Supported | Keep but align main text and supplementary to n=31 file |

## Reproducibility Boundary

- Allowed quantitative claims: only those directly traceable to the supported sources above.
- Disallowed quantitative claims: any number requiring absent artifacts or incompatible metric scales.
- If a useful statement cannot be supported quantitatively, rewrite as qualitative observation and/or future work.

## Implementation Back-Write

- `Paper/content.tex` now removes unsupported quantitative claims tied to missing artifacts.
- `Paper/content.tex` now uses a single parameter-distance naming convention (`Param. Dist.`) for retained objective tables.
- `Paper/supplementary.tex` now aligns layer-sweep sample count and values with `layer_selection_results.csv` (`n_samples=31`).
