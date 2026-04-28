# TMM Revision Checklist (Evidence-Hardening)

This checklist tracks the submission-facing fixes needed to keep the paper package aligned with the repository's verified evidence chain.

## P0: Canonical Evidence Sources

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P0-1 | Main objective evidence anchored to audited Protocol-A | `Paper/content.tex` and `Paper/supplementary.tex` cite the split audit plus `protocolA_audio_grouped_objective_stats.*` and `protocolA_audio_grouped_per_query_metrics.csv` for the main objective comparison | Done |
| P0-2 | Protocol-C positioned as diagnostic only | No submission-facing document describes Protocol-C as a real-audio robustness benchmark | Done |
| P0-3 | Listening study anchored to canonical report | Submission-facing docs use `Experiments/mushura/results_report.md` for participants, ratings, and nonparametric tests | Done |
| P0-4 | Deprecated / legacy artifacts removed from main evidence chain | No submission-facing document uses `retrieval_comparison_report.md` or `protocolB_objective_stats.*` as formal evidence | Done |

## P1: Derived Protocol-A Diagnostics

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P1-1 | Per-query diagnostics generated from canonical CSV | `Experiments/AblationStudies/protocolA_audio_grouped_derived_analysis.md` and `.json` exist and are reproducible from `protocolA_audio_grouped_per_query_metrics.csv` | Done |
| P1-2 | Win/loss/tie summary added to supplementary | Supplementary reports per-baseline TRR diagnostics beyond mean-only tables | Done |
| P1-3 | Representative success/failure cases added | Supplementary includes case-level evidence derived from the canonical per-query CSV | Done |
| P1-4 | Bookkeeping note added for query pairing | Supplementary explains the `204` paired rows vs `203` unique `query_name` labels and clarifies that pairing uses `query_idx` | Done |

## P2: Listening and Protocol-C Reporting

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P2-1 | Protocol-C boundary-condition table added | Supplementary reports scenario-level fallback behavior and conflict degradation | Done |
| P2-2 | Protocol-C paired L2 tests added | Supplementary includes Holm-corrected L2 comparisons for the diagnostic scenarios | Done |
| P2-3 | Listening-study repeated-measures stats added | Supplementary includes Friedman and Wilcoxon/Holm tables with `rbc` | Done |
| P2-4 | Non-standard MUSHRA wording avoided | Submission-facing docs consistently describe the study as multiple-stimulus with hidden reference and no explicit anchor | Done |
| P2-5 | Listening-study caveats surfaced in support docs | Submission-facing docs state that `HCAP` is only a raw-log label and that manual-baseline provenance/time-budget metadata are incomplete | Done |

## P3: Scope Hygiene

| ID | Item | Acceptance Criterion | Status |
| --- | --- | --- | --- |
| P3-1 | Architecture figure matches verified pipeline | Main paper figure no longer shows AEM, episodic memory, or unsupported system modules | Done |
| P3-2 | AEM / personalization downgraded to exploratory | No submission-facing document treats memory/personalization as a verified main contribution | Done |
| P3-3 | Only verified strong-baseline claims remain | Submission-facing docs include CLAP only where backed by canonical artifacts, and do not claim PaSST / PANNs / direct regressors are completed | Done |
| P3-4 | Metric redesign claims removed unless verified | No submission-facing document claims normalized metrics or categorical-metric reform has been completed | Done |

## Final Verification Targets

- Main paper compiles cleanly with the revised architecture figure and updated result text.
- Submission-facing docs are numerically consistent on:
  - `N_total=1267`
  - legacy split audit: `N_test=211`, `N_kb=1056`, `16` shared resolved audio paths
  - stricter Protocol-A: `N_test=204`, `N_kb=1063`
  - TRR on stricter Protocol-A: `8.0467 / 0.5169 / 0.4595 / 0.8247 / 0.8051`
  - CLAP coverage on stricter Protocol-A: `201` queries
  - Listening study `26 participants / 910 ratings`
- Repository-backed response docs no longer contain stale claims about larger datasets, stronger baselines, real-audio Protocol-C, normalized metrics, or AEM learning curves.
