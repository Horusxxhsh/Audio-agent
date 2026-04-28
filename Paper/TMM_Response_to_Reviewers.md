# Response to Reviewers (IEEE TMM)

**Manuscript ID**: #8159  
**Title**: Texture Resonance Retrieval for Retrieval-Grounded Editable Audio Effect Preset Selection  
**Authors**: Anonymous Authors

Dear Editor and Reviewers,

Thank you for the detailed feedback. We used the revision to narrow the manuscript to the claims that are directly supported by reproducible repository artifacts. The revised evidence chain now relies on an audited split definition plus six canonical sources:

- `Experiments/tmm/protocolA_split_audit.md`
- `Experiments/tmm/protocolA_audio_grouped_leakage_report.json`
- `Experiments/AblationStudies/protocolA_audio_grouped_objective_stats.md`
- `Experiments/AblationStudies/protocolA_audio_grouped_per_query_metrics.csv`
- `Experiments/AblationStudies/protocolC_objective_stats.md`
- `Experiments/mushura/results_report.md`

We no longer treat the legacy retrieval comparison report, the deprecated Protocol-B outputs, or the repository's exploratory personalization/memory code as primary evidence.

## Summary of Implemented Changes

1. **Scope narrowed to retrieval-grounded editable control.**  
   The manuscript now centers on TRR as a retrieval representation for executable preset control. Personalization, AEM memory, and other exploratory system extensions are explicitly excluded from the paper's primary validated claims.

2. **Objective evidence re-anchored to an audited Protocol-A split.**  
   A post-hoc audit of the legacy song-name-based Protocol-A list found `16` cross-split shared resolved audio paths. We therefore moved the main comparison to a stricter resolved-audio-grouped split (`N_total=1267`, `N_test=204`, `N_kb=1063`) with zero exact shared audio paths under the current audit. We report mean metrics, 95% bootstrap confidence intervals, and Holm-corrected paired permutation tests from the canonical Protocol-A artifacts for this stricter split.

3. **Per-query diagnostics added for Protocol-A.**  
   We added a repository-backed derived analysis from `protocolA_audio_grouped_per_query_metrics.csv` to show where the gains come from. This includes win/loss/tie counts, signed-delta summaries, and representative success/failure cases. These diagnostics are now referenced in the supplementary material so that the main results are not supported by mean values alone.

4. **CLAP added as a verified stronger baseline.**  
   We now include a CLAP retrieval baseline in the verified evidence chain on the stricter Protocol-A split. TRR remains stronger than CLAP on the 201 shared queries with cached CLAP embeddings. We do **not** claim that PaSST, PANNs, or direct parameter regressors have been completed.

5. **Protocol-C repositioned as boundary-condition analysis.**  
   We removed any claim that the current Protocol-C is a realistic robustness benchmark. The revised paper explicitly states that the audio branch still uses synthetic embedding-space degradation. The reported result is therefore limited to diagnosing the current fusion heuristic: successful fallback under single-modality degradation and a clear failure mode under modality conflict.

6. **Listening study terminology and statistics corrected.**  
   We consistently describe the study as a multiple-stimulus listening test with a hidden reference and no explicit low-quality anchor, rather than as standard MUSHRA. We now report the canonical nonparametric statistics from the listening-study report, including Friedman omnibus tests, Holm-corrected Wilcoxon signed-rank post-hoc tests, and rank-biserial effect sizes.

7. **Submission package synchronized.**  
   The paper, supplementary material, response documents, and revision checklist were revised to remove stale claims about larger datasets, stronger baselines, real-audio Protocol-C, normalized metrics, and AEM learning curves that are not part of the current verified evidence chain.

## Point-by-Point Alignment With the Main Reviewer Concerns

### 1. Novelty and scope

We agree that the strongest supported contribution is not a full personalized agent system, but a retrieval-grounded parameter-control formulation centered on TRR. The manuscript now presents TRR as the core method and avoids claims that would require additional evidence beyond the current benchmark.

### 2. Benchmark scale, split transparency, and statistical reporting

We now anchor the objective results to the stricter resolved-audio-grouped Protocol-A benchmark with `N_test=204` and `N_kb=1063`. The revised manuscript and supplementary material report:

- the legacy split audit (`16` shared resolved audio paths across split);
- the stricter anti-leakage split with zero exact shared resolved audio paths under the current audit;
- method means with 95% bootstrap confidence intervals;
- paired permutation tests for TRR versus each retrieval baseline;
- Holm-corrected `p` values;
- per-query derived diagnostics from the canonical CSV.

### 3. Stronger baselines

We now include **CLAP** as a verified stronger retrieval baseline on the stricter Protocol-A split. The revised manuscript therefore frames the current result as:

> TRR is the strongest among the currently evaluated retrieval baselines on the audited Protocol-A benchmark, including CLAP on the 201 shared queries with cached CLAP embeddings.

This remains narrower than a best-in-class claim. We still do **not** claim to have completed PaSST, PANNs, or direct parameter-regression baselines.

### 4. Metric limitations

We did **not** replace the metric system with a new normalized suite in this revision. Instead, we clarified the exact operational definitions and their limitations:

- flattened numeric leaves only;
- missing numeric keys treated as zero;
- no per-parameter normalization;
- within-protocol interpretation only.

This limitation is now stated explicitly in both the main paper and the supplementary material.

### 5. Protocol-C realism

We agree with the reviewers that synthetic embedding-space degradation is not equivalent to real audio corruption. Accordingly, Protocol-C is no longer framed as a realistic robustness benchmark. The revision uses it only to characterize the current fusion heuristic:

- `vague_text`: fusion falls back to audio;
- `noisy_audio`: fusion falls back to text;
- `conflict`: fusion becomes substantially worse than TRR-only.

### 6. Listening test rigor

The revised paper now exposes the canonical statistics already present in the repository:

- `26` participants and `910` ratings;
- Friedman omnibus tests for Trials 2--5 and Trials 6--10;
- Holm-corrected Wilcoxon signed-rank post-hoc tests;
- rank-biserial correlation (`rbc`);
- explicit statement that the HCAP label in the raw logs corresponds to the TRR-based system discussed in the paper.
- explicit limitation that the logs do not preserve device metadata, participant expertise, or the provenance/time budget of the manual baseline.

We also make clear that the TRR-based system and MusicGen are statistically indistinguishable in Trials 6--10 under the reported post-hoc test.

### 7. Scope mismatch between paper and repository

This concern was valid in earlier drafts. The revision addresses it by making the repository's exploratory modules non-central:

- AEM / personalization is described as exploratory only;
- deprecated Protocol-B results are removed from the primary evidence path;
- legacy reports are no longer used as formal evidence;
- the main architecture figure now depicts only the verified retrieval-grounded pipeline.

## Closing Statement

We appreciate the reviewers' insistence on a tighter evidence chain. The revised package is intentionally more conservative than earlier drafts: it makes fewer claims, but each retained claim is now tied to a canonical repository artifact and presented with clearer statistical support and clearer scope boundaries.

Sincerely,  
The Authors
