# Consistency Audit Record: fix-tmm-major-revision-gaps

**Date**: 2026-03-04
**Auditor**: Gemini CLI
**Objective**: Verify alignment between `Paper/content.tex`, `Paper/supplementary.tex`, and experimental source reports.

## 1. Main Results (Protocol-A, N=211)

| Item | Status | Source File | Paper Location | Notes |
|---|---|---|---|---|
| TRR Numbers | Consistent | `Experiments/AblationStudies/protocolA_objective_stats.md` | `Table 4` (tab:main_results) | 0.3064 / 0.7253 / 0.6990 / 0.8376 / 0.9574 |
| Baselines | Consistent | `Experiments/AblationStudies/protocolA_objective_stats.md` | `Table 4` (tab:main_results) | Wav2Vec, Text-RAG, FeatureNN-RAG verified |
| Pure LLM | Consistent | `Experiments/AblationStudies/retrieval_comparison_report.md` | `Table 4` (tab:main_results) | 13.6520 / 0.4361 / 0.2127 / 0.3779 / 0.7053 |
| Statistical CIs | Consistent | `Experiments/AblationStudies/protocolA_objective_stats.md` | `Table S2` (tab:protocolA_ci) | All 95% CI brackets matched |
| Significance | Consistent | `Experiments/AblationStudies/protocolA_objective_stats.md` | `Table S3` (tab:protocolA_sig) | Delta and Holm p-values matched |

## 2. Texture Baseline Comparison (N=5)

| Item | Status | Source File | Paper Location | Notes |
|---|---|---|---|---|
| Texture Baselines | Consistent | `Experiments/TextureResonance/texture_representation_comparison.csv` | `Table 5` (tab:trr_texture_baselines) | 13.57 / 24.95 / 32.02 (L2) verified |

## 3. Latency Breakdown (Cache-only, n=633)

| Item | Status | Source File | Paper Location | Notes |
|---|---|---|---|---|
| Latency Numbers | Consistent | `Experiments/latency/latency_report.md` | `Table 3` (tab:latency_breakdown) | 3.027/1.369/0.031/4.538 median matched |

## 4. Layer Sweep (Protocol-A, n=30)

| Item | Status | Source File | Paper Location | Notes |
|---|---|---|---|---|
| Layer Selection | Consistent | `Experiments/TextureResonance/layer_selection_results.csv` | `Table S4` (tab:layer_sweep) | Layer 10 (5.4303) verified as best |

## 5. MUSHRA / Listening Test

| Item | Status | Source File | Paper Location | Notes |
|---|---|---|---|---|
| Trial 1 (Style) | Consistent | `Paper/content.tex` L454 | `Table 7` (tab:mushra_trial1_stats) | Verified against Trial 1 data summary |
| Trial 2-5 (Solo) | Consistent | `Paper/content.tex` L479 | `Table 8` (tab:mushra_trial2_5_stats) | Verified against Trial 2-5 data summary |
| Trial 6-10 (Sim) | Consistent | `Paper/content.tex` L501 | `Table 9` (tab:mushra_trial6_10_stats) | Verified against Trial 6-10 data summary |

## Discrepancies / Actions Taken

- **Fusion Removal**: Confirmed Fusion method is absent from `Table 4` as per the "single evidence chain" strategy.
- **Pure LLM Inclusion**: Confirmed "Pure LLM" is present in `Table 4` to justify RAG necessity, matching `retrieval_comparison_report.md`.
- **Setup Cleanup**: Verified no engineering script filenames (e.g., `.py`) exist in the experimental setup narrative.
- **Table Indexing**: Re-verified sequential table numbers (1-9) in the compiled manuscript, accounting for double-column `table*` environments.

**Conclusion**: All paper-level evidence is grounded in reproducible experimental artifacts.
