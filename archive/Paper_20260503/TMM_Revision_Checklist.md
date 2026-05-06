# TMM Revision Checklist (Evidence-Hardening)

This checklist tracks the submission-facing fixes needed to keep the paper package aligned with the repository's verified evidence chain.

## P0: Canonical Evidence Sources

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P0-1 | Main objective evidence anchored to audited Protocol-A | `Paper/content.tex` and `Paper/supplementary.tex` cite the split audit plus `protocolA_audio_grouped_objective_stats.*` and `protocolA_audio_grouped_per_query_metrics.csv` for the main objective comparison | Done |
| P0-2 | P0 real-degradation Protocol-C incorporated | Submission-facing documents distinguish the older synthetic diagnostic from the P0 raw-audio degradation experiment | Done |
| P0-3 | Listening study anchored to canonical report | Submission-facing docs use `Experiments/mushura/results_report.md` for participants, ratings, and nonparametric tests | Done |
| P0-4 | Deprecated / legacy artifacts removed from main evidence chain | No submission-facing document uses `retrieval_comparison_report.md` or `protocolB_objective_stats.*` as formal evidence | Done |
| P0-5 | P0 E2/E3 accepted as verified experimental data | User double-checked P0 raw outputs for authenticity, completeness, and correctness; submission-facing docs use these values as formal results | Done |

## P1: Derived Protocol-A Diagnostics

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P1-1 | Per-query diagnostics generated from canonical CSV | `Experiments/AblationStudies/protocolA_audio_grouped_derived_analysis.md` and `.json` exist and are reproducible from `protocolA_audio_grouped_per_query_metrics.csv` | Done |
| P1-2 | Win/loss/tie summary added to supplementary | Supplementary reports per-baseline TRR diagnostics beyond mean-only tables | Done |
| P1-3 | Representative success/failure cases added | Supplementary includes case-level evidence derived from the canonical per-query CSV | Done |
| P1-4 | Bookkeeping note added for query pairing | Supplementary explains the `204` paired rows vs `203` unique `query_name` labels and clarifies that pairing uses `query_idx` | Done |
| P1-5 | Near-duplicate sensitivity placeholder removed | `Experiments/E5_Ablations/outputs/p0_near_dup/p0_near_dup_sensitivity.csv` exists and `Paper/supplementary.tex` reports the resulting table without placeholder values | Done |
| P1-6 | TRR mechanism ablation added | `Experiments/E5_Ablations/outputs/p0_trr_mechanism/p0_trr_mechanism_summary.csv` reports mean pooling, unprojected Gram, single-layer Gram, projection-dim, and L2-normalization variants; supplement reports the controlled table | Done |

## P2: Listening and Protocol-C Reporting

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P2-1 | P0 Protocol-C real-degradation table added | Supplementary reports overall adaptive-vs-fixed fusion results under real audio degradations | Done |
| P2-2 | P0 Protocol-C per-condition table added | Supplementary summarizes which fusion setting wins under AWGN, MP3, reverb, and truncation | Done |
| P2-2a | Local Protocol-C execution path checked | Current workspace can execute the raw-audio degradation script with local dependencies and produce per-query, per-condition, overall, delta, and meta artifacts; canonical manuscript numbers remain the user-verified P0 server record | Done |
| P2-2b | Protocol-C boundary rows reported | Supplementary reports current-code audio-only, pure-text, and parameter-oracle upper-bound rows and explicitly labels them as an execution-path audit, not as a replacement for canonical P0 values | Done |
| P2-3 | Listening-study repeated-measures stats added | Supplementary includes Friedman and Wilcoxon/Holm tables with `rbc` | Done |
| P2-4 | Non-standard MUSHRA wording avoided | Submission-facing docs consistently describe the study as multiple-stimulus with hidden reference and no explicit anchor | Done |
| P2-5 | Listening-study caveats surfaced in support docs | Submission-facing docs state that `HCAP` is only a raw-log label and that manual-baseline provenance/time-budget metadata are incomplete | Done |

## P3: Scope Hygiene

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P3-1 | Architecture figure matches verified pipeline | Main paper figure no longer shows AEM, episodic memory, or unsupported system modules | Done |
| P3-2 | AEM / personalization downgraded to exploratory | No submission-facing document treats memory/personalization as a verified main contribution | Done |
| P3-3 | Only verified strong-baseline claims remain | Submission-facing docs include CLAP, PaSST, and PANNs from P0 E2; the direct MLP regressor is reported only as a diagnostic non-executable boundary baseline, and learned reranking is not claimed as complete | Done |
| P3-4 | Metric redesign claims removed unless verified | No submission-facing document claims normalized metrics or categorical-metric reform has been completed | Done |

## Final Verification Targets

- Main paper compiles cleanly with the revised architecture figure and updated result text.
- Submission-facing docs are numerically consistent on:
  - `N_total=1267`
  - legacy split audit: `N_test=211`, `N_kb=1056`, `16` shared resolved audio paths
  - P0 Protocol-A: `N_test=204`, `N_kb=1063`
  - TRR on P0 Protocol-A: `8.7287 / 0.1881 / 0.5766 / 0.5404 / 0.8415 / 0.8297`
  - P0 E2 baselines: `Wav2Vec`, `FeatureNN`, `CLAP`, `PaSST`, `PANNs`
  - P0 Protocol-C adaptive fusion: `alpha=0.5980`, `L2=20.1491`, `Acc@0.1=0.6121`, `MRR=0.5654`, `NDCG@5=0.5566`
  - Local Protocol-C reproducibility check: `Experiments/AblationStudies/outputs/p0_e3_boundary_local_204/` records a current-code 204-query run with audio-only and pure-text boundaries; this is an execution-path audit artifact, not a replacement for the verified P0 server values above.
  - TRR mechanism ablation: `Experiments/E5_Ablations/outputs/p0_trr_mechanism/p0_trr_mechanism_summary.csv` records `mean_pool_l5`, `gram_no_projection_l5`, single-layer Gram rows, projection dimensions `16/32/64/128`, and `gram_l456_d64_no_l2`.
  - Listening study `26 participants / 910 ratings`
- Repository-backed response docs no longer contain stale claims about missing PaSST/PANNs baselines, missing real-audio Protocol-C, normalized metrics, or AEM learning curves.
- Supplementary material no longer contains placeholder values for near-duplicate sensitivity or Trials 2--5 per-trial breakdowns.
- Diagnostic MLP direct-regression result is reported with the explicit boundary that dense continuous outputs are not executable retrieved presets.

## Reviewer-Claim Traceability Audit

This audit is intended to prevent a response-letter/manuscript mismatch in the next submission package.

| Reviewer item | Response-letter claim | Manuscript or artifact evidence |
| --- | --- | --- |
| m1 projection dimension | Algorithm 1 and prose use frozen random projection `R^768 -> R^32` | `Paper/content.tex:159` states `P:\mathbb{R}^{768}\rightarrow\mathbb{R}^{32}`; `Paper/content.tex:174` states 32 dimensions, `32x32`, and 1024-dimensional flattening |
| m3 personalization deletion | Preliminary personalization section removed | `rg "Preliminary Personalization" Paper/content.tex` returns no manuscript hit; validated section list has no personalization subsection |
| m7 Figure 1 caption | Nine-module topology is listed | `Paper/content.tex:139` lists Compressor -> Driver -> Screamer -> Equaliser -> Chorus -> Flanger -> Phaser -> Delay -> Reverb |
| m8 fusion formula | Explicit score-level fusion formula added | `Paper/content.tex:235` defines `s_fused(z_i)=alpha s_text(z_i)+(1-alpha)s_audio(z_i)` |
| M2 raw L2 inconsistency | Near-duplicate table avoids invalid raw-L2 cross-script comparison | `Paper/content.tex:329` explains why the sensitivity table reports normalized/directional metrics only |
| M3 supervised boundary | MLP is acknowledged as stronger on normalized numeric error | `Paper/content.tex:353` states that if normalized numeric error is the sole objective, the supervised regressor is stronger |
| M4 listening interpretation | Listening test is exploratory, not objective-metric validation | `Paper/content.tex:487` and `Paper/content.tex:524` explicitly state this boundary |
| Local vLLM experiment | Local qwen3.5-9b vLLM diagnostic added as negative control | `Paper/content.tex:490`; outputs under `Experiments/E4_MetricCorrelation/outputs/local_llm_alignment/` |
| M5 scale/generalizability | Guitar-only, single-topology scope is framed as limited | `Paper/content.tex:521` requires larger multi-instrument and multi-effect benchmarks before general claims |
| Figure quality | Listening boxplots use vector PDFs | `Paper/content.tex:431`, `Paper/content.tex:456`, and `Paper/content.tex:481` include `system_boxplot_Trial_*.pdf` |
| Bibliography hygiene | High-risk entries corrected without claiming full camera-ready cleanup | `Paper/reference.bib:54` changes LLM2Fx to `@misc` with expanded authors and DOI; response letter states remaining metadata should still be checked |
