# Response to Reviewers (IEEE TMM)

**Manuscript ID**: #8159  
**Title**: Texture Resonance Retrieval for Retrieval-Grounded Editable Audio Effect Preset Selection  
**Authors**: Anonymous Authors

Dear Editor and Reviewers,

Thank you for the detailed feedback. We used the revision to narrow the manuscript to the claims that are directly supported by reproducible artifacts and the P0 experiment package. The revised evidence chain now relies on an audited split definition plus the P0 E2/E3 record:

- `Experiments/tmm/protocolA_split_audit.md`
- `Experiments/tmm/protocolA_audio_grouped_leakage_report.json`
- `Experiments/AblationStudies/protocolA_audio_grouped_objective_stats.md`
- `Experiments/AblationStudies/protocolA_audio_grouped_per_query_metrics.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_stats.json`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_overall_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_summary.csv`
- `Experiments/E5_Ablations/outputs/p0_near_dup/p0_near_dup_sensitivity.csv`
- `Experiments/E5_Ablations/outputs/p0_trr_mechanism/p0_trr_mechanism_summary.csv`
- `Experiments/E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json`
- `Experiments/AblationStudies/outputs/p0_e3_boundary_local_204/e3_overall_summary.csv`
- `Experiments/mushura/results_report.md`

We no longer treat the legacy retrieval comparison report, the deprecated Protocol-B outputs, or the repository's exploratory personalization/memory code as primary evidence.

## Summary of Implemented Changes

1. **Scope narrowed to retrieval-grounded editable control.**  
   The manuscript now centers on TRR as a retrieval representation for executable preset control. Personalization, AEM memory, and other exploratory system extensions are explicitly excluded from the paper's primary validated claims.

2. **Objective evidence upgraded to the P0 Protocol-A baseline matrix.**
   A post-hoc audit of the legacy song-name-based Protocol-A list found `16` cross-split shared resolved audio paths. We retain this audit for split transparency and now use the P0 204-query Protocol-A package as the main baseline matrix. The revised comparison includes TRR, Wav2Vec, FeatureNN, CLAP, PaSST, and PANNs on the shared `N_test=204`, `N_kb=1063` setup.

3. **Per-query diagnostics added for Protocol-A.**  
   We added a repository-backed derived analysis from `protocolA_audio_grouped_per_query_metrics.csv` to show where the gains come from. This includes win/loss/tie counts, signed-delta summaries, and representative success/failure cases. These diagnostics are now referenced in the supplementary material so that the main results are not supported by mean values alone.

4. **TRR mechanism ablations added.**
   We added a controlled same-backbone ablation on the P0 split comparing Wav2Vec2 mean pooling, full unprojected Gram, single-layer projected Gram, projection dimensions, and with/without L2 normalization. The ablation supports a bounded mechanism claim: second-order Gram aggregation improves over same-backbone mean pooling, and L2 normalization is important. It also shows that layer and projection choices matter, so we avoid claiming that the current TRR configuration is globally optimal.

5. **Stronger baselines and boundary baselines added.**
   We now include CLAP, PaSST, and PANNs in the P0 Protocol-A evidence chain. TRR remains strongest on normalized L2, Acc@0.1, Recall, Cosine, and Module among retrieval methods. We also add a diagnostic direct-regression boundary baseline (mean-pooled Wav2Vec2 $\rightarrow$ MLP) trained on the P0 knowledge base. Because that regressor predicts dense continuous parameter leaves rather than retrieved executable presets, we report it as a boundary condition rather than as a replacement for the retrieval leaderboard. Learned reranking remains future work.

6. **Protocol-C downgraded to a diagnostic robustness analysis and boundary rows added.**
   The older Protocol-C diagnostic used synthetic embedding-space degradation and remains only a boundary-condition artifact. The P0 Protocol-C result now applies AWGN, MP3, reverb, and truncation to raw audio before TRR re-encoding, reuses the same 204-query split as E2, and compares fixed fusion against adaptive fusion. We additionally report current-code audio-only, pure-text, and parameter-oracle upper-bound rows as an execution-path audit. The revised claim is not that adaptive fusion is a standalone main contribution or that it improves over a text-only upper boundary; it is that degradation robustness is highly sensitive to modality weighting.

7. **Listening study terminology and statistics corrected.**
   We consistently describe the study as a multiple-stimulus listening test with a hidden reference and no explicit low-quality anchor, rather than as standard MUSHRA. We now report the canonical nonparametric statistics from the listening-study report, including Friedman omnibus tests, Holm-corrected Wilcoxon signed-rank post-hoc tests, and rank-biserial effect sizes.

8. **Submission package synchronized.**
   The paper, supplementary material, response documents, and revision checklist were revised to remove stale claims about missing PaSST/PANNs baselines, missing real-audio Protocol-C, unresolved near-duplicate placeholders, and unsupported AEM learning curves.

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

We now include **CLAP, PaSST, and PANNs** as stronger retrieval baselines in the P0 Protocol-A package. The revised manuscript therefore frames the current result as:

> TRR is the strongest among the currently evaluated retrieval baselines on the shared P0 Protocol-A benchmark, including Wav2Vec, FeatureNN, CLAP, PaSST, and PANNs.

This remains narrower than a best-in-class claim. The Norm.L2 effect sizes are small. We now include a diagnostic direct-regression MLP boundary baseline, but we still do **not** claim to have completed an executable direct-parameter controller or learned reranking baseline.

### 3a. TRR mechanism evidence

We agree that the previous version did not sufficiently isolate why TRR works. We therefore added a controlled same-backbone mechanism ablation. The new supplementary table compares:

- Wav2Vec2 mean pooling;
- full unprojected Gram aggregation;
- single-layer Gram variants for layers 4, 5, and 6;
- multi-layer projected Gram variants with projection dimensions 16, 32, 64, and 128;
- the same multi-layer setting without L2 normalization.

The result supports a narrower but more defensible mechanism claim: second-order Gram aggregation improves over same-backbone mean pooling, and normalization is necessary for stable retrieval. It also shows that the exact layer/projection choice matters. We therefore present TRR as an effective texture-aware retrieval prior, not as a fully optimized universal representation.

### 4. Metric limitations

We did **not** replace the metric system with a new normalized suite in this revision. Instead, we clarified the exact operational definitions and their limitations:

- flattened numeric leaves only;
- missing numeric keys treated as zero;
- no per-parameter normalization;
- within-protocol interpretation only.

This limitation is now stated explicitly in both the main paper and the supplementary material.

### 5. Protocol-C realism

We agree with the reviewers that synthetic embedding-space degradation is not equivalent to real audio corruption. The earlier Protocol-C diagnostic remains limited for that reason. The P0 Protocol-C package addresses this gap by applying real degradations to raw audio before re-encoding:

- AWGN at `20 / 10 / 5 dB`;
- MP3 at `128 / 64 / 32 kbps`;
- Reverb with `RT60 = 0.6 / 1.0`;
- Truncation to `50% / 30%`.

The retained result is not a claim that adaptive fusion dominates every condition or improves over a pure-text boundary. We added a boundary audit with audio-only, pure-text, and parameter-oracle upper-bound rows and revised the manuscript to treat Protocol-C as a diagnostic robustness analysis. The supported claim is narrower: audio-heavy fusion is fragile under realistic degradation, and retrieval stability depends strongly on modality weighting.

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
