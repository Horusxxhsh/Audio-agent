# TMM Major Revision Checklist (Executable)

This document serves as the authoritative tracking log for the IEEE Transactions on Multimedia (TMM) major revision of the Audio-Agent manuscript. The primary objective of this revision cycle is to strengthen the empirical evidence chain by expanding the evaluation scale, introducing rigorous statistical testing, and ensuring absolute consistency between the reported values in the manuscript and the reproducible experimental artifacts in the repository.

## P0: Must-Hold Consistency (Current Draft)

| ID | Item | Target Section/File | Acceptance Criterion | Status |
|---|---|---|---|---|
| P0-1 | Objective main table aligned with report values | `Paper/content.tex` Table `tab:main_results`; `Experiments/AblationStudies/retrieval_comparison_report.md` | Five methods and all five metrics are numerically identical | Done |
| P0-2 | Single-protocol statement for objective comparison | `Paper/content.tex` Experimental Setup + RQ1 text | Main objective comparison explicitly states Protocol-A retrieval-only | Done |
| P0-3 | Remove fusion-centered claims/tables from core narrative | `Paper/content.tex`, `Paper/supplementary.tex` | No fusion result table is used as main evidence | Done |
| P0-4 | Restore non-fusion experimental figures and text | `Paper/content.tex` (TRR layer figure + listening figures/tables) | Historical valid figures are present with matching descriptions | Done |
| P0-5 | No setup script filename in experiment setup | `Paper/content.tex` | Setup paragraph contains no `profile.py` or report filename reference | Done |

## P1: Reviewer Major-Revision Actions (Need to Complete Before Resubmission)

| ID | Reviewer Concern | Required Action | Target Section/File | Deliverable | Status |
|---|---|---|---|---|---|
| P1-A | Generalization beyond guitar benchmark | Add at least one non-guitar dataset/domain and cross-domain evaluation | `Paper/content.tex` Experiments + Discussion | New table with per-domain metrics and split details | Planned |
| P1-B | Stronger baselines | Add CLAP/PaSST retrieval baselines and at least one learned regressor/reranker | `Paper/content.tex` RQ1 + Supplementary | Expanded baseline table and significance test | Planned |
| P1-C | Subjective protocol standardization | Add participant expertise metadata, loudness matching, time budget, and explicit production-utility score | `Paper/content.tex` Listening subsection + Supplementary protocol appendix | Protocol checklist + updated subjective results | Planned |
| P1-D | TRR layer-10 mechanism depth | Add acoustic probing analysis for layer behavior (transient/modulation sensitivity) | `Paper/content.tex` TRR subsection + appendix | Probe figure/table + explanatory paragraph | In Progress |
| P1-E | Deterministic repair detail | Add explicit repair/projection pseudo-code and one discrete-constraint repair case | `Paper/content.tex` Method + appendix | Algorithm block + worked example | Planned |

## P2: Format and Submission Hygiene

| ID | Item | Target | Acceptance Criterion | Status |
|---|---|---|---|---|
| P2-1 | Acronym completeness | `Paper/content.tex` + figures | All abbreviations are defined at first appearance | In progress |
| P2-2 | Final language/typography sweep | Full manuscript | No inconsistent capitalization/punctuation in technical terms | In progress |
| P2-3 | Reproducibility package link finalization | Reproducibility paragraph | Public anonymized repo URL + scripts + splits + environment spec | Planned |

## Verified Numeric Match Snapshot (Current)

The following rows in `Paper/content.tex` and `Paper/supplementary.tex` have been audited and are currently identical to the canonical experimental outputs (Protocol-A, $N=211$):

- **TRR**: `0.3064 / 0.7253 / 0.6990 / 0.8376 / 0.9574`
- **Wav2Vec-RAG**: `0.3625 / 0.6434 / 0.5748 / 0.7364 / 0.9116`
- **Text-RAG**: `0.4573 / 0.7034 / 0.6407 / 0.7404 / 0.8625`
- **FeatureNN-RAG**: `1.1729 / 0.6765 / 0.6485 / 0.7757 / 0.9602`
- **Pure LLM**: `13.6520 / 0.4361 / 0.2127 / 0.3779 / 0.7053`

## Operational Notes

The `retrieval_comparison_report.md` file is currently utilized as a legacy bridge for consistency checking. Prior to final resubmission, all objective claims must be cross-verified against the canonical protocol outputs, specifically `protocolA_objective_stats.md` and the raw per-query metrics CSV, to eliminate any potential source-of-truth ambiguity. All statistical significance markers (confidence intervals and $p$-values) must follow the bootstrap-corrected results reported in the Supplementary Material.
