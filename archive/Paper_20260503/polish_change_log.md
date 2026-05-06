# Audio-Agent Paper Polishing: Change Log (IEEE Tone)

This log summarizes the main polishing edits applied to the LaTeX sources. It is intended as a review aid for quickly scanning what changed and why.

## `Paper/content.tex`

- **Abstract**: removed “necessity/essential” framing; reduced cross-comparison chaining of `Param. Dist.` values by switching one comparison to percentage improvements and explicitly tying the no-retrieval LLM comparison to Supplementary Table S1.
- **Introduction**: softened “ensure” phrasing to avoid absolute causal claims while keeping the editability motivation.
- **Related Work**:
  - Removed the uncited “up to 35\%” hallucination/violation statistic; replaced with a conservative, citation-safe statement.
  - Standardized the task term to *parameter synthesis* and tightened the positioning paragraph.
  - Minor flow edits for a more journal/IEEE tone (less promotional, more audit-oriented).
- **Problem Formulation**:
  - Tightened the opening paragraph (more direct statement of constraints and goal).
  - Added `\label{eq:feasible_set}` and replaced hard-coded `Eq.~1` references with `Eq.~\ref{eq:feasible_set}` for robustness.
- **Methodology**:
  - Architecture paragraph now explicitly maps the narrative to Figure~\ref{fig:architecture}.
  - Fusion weighting equation is written in normalized form so `w_{\text{text}}+w_{\text{audio}}=1` is explicit.
  - Projection operator is given a compact formal definition as `Repair(clip(·))` to make feasibility enforcement unambiguous.
- **Experiments**:
  - Rephrased “necessity/catastrophic/fails” language to protocol-scoped statements.
  - Added an explicit note that comparisons are interpreted within each stated protocol and that magnitudes should not be compared across different settings/tables.
- **Metrics**: removed “definitions only in supplementary” implication by stating metrics are restated in supplementary for completeness.

## `Paper/supplementary.tex`

- Added an opening section that restates metric definitions and adds protocol notes on within-table interpretation (avoid cross-table magnitude comparisons).
- Updated the direct retrieval table caption to explicitly state within-protocol comparison intent.

## New files

- `Paper/polish_consistency_checklist.md`: global consistency rules + reviewer-risk checklist for future edits.

