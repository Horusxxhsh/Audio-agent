# Audio-Agent Paper Polishing: Consistency Checklist (IEEE Tone)

This checklist records the global consistency decisions and reviewer-risk fixes applied in the latest polishing pass. It does **not** change any experimental results or numbers.

## Terminology and Style

- **Primary term**: use *parameter synthesis* (instead of mixing parameter generation/control) for the core task definition.
- **Neuro-symbolic agent claim strength**: avoid absolute causal wording (e.g., “ensure”, “essential”, “catastrophic”); prefer *“under this protocol / in this setting / indicates / suggests”*.
- **No new emphasis formatting**: do not introduce new `\textbf{}` / `\textit{}` beyond what already exists; emphasize through sentence structure instead.

## Equations and References

- **Feasible set equation** is labeled as `\label{eq:feasible_set}`; all references use `Eq.~\ref{eq:feasible_set}` (avoid hard-coded “Eq.~1”).
- **Fusion weights**: the entropy-weighted fusion equation is written in normalized form to make `w_{\text{text}}+w_{\text{audio}}=1` explicit.
- **Projection operator**: `\Pi_{\Theta}` is defined as `clip` followed by deterministic `Repair(·)` to make feasibility enforcement unambiguous.

## Metrics and Protocol Wording

- **Metric definitions live in the main paper** (Section “Metrics”) and are **restated in the supplementary** for completeness.
- **Protocol binding rule**: every quantitative claim should point to a specific table/setting; avoid wording that implies cross-table comparability unless the protocol is explicitly identical.
- **Cross-table magnitude caution**: avoid comparing absolute `Param. Dist.` magnitudes across tables with different settings; interpret improvements **within** each table under its stated protocol.

## Abstract Guardrails

- Do not chain multiple `Param. Dist.` values from different comparisons as if they are directly comparable.
- Keep the abstract’s quantitative claims tied to a specific protocol/table (e.g., “Supplementary Table S1”).

## Related Work Citation Hygiene

- Remove or weaken “hard numbers” that do not have a clear supporting citation (e.g., “up to X%”) rather than leaving an uncited statistic.

## Remaining High-Risk Items to Double-Check (Manual)

- Any numeric claim in prose that is not directly adjacent to the table/figure it comes from.
- Any “same protocol / same metric” wording that could be contradicted by a reader comparing Table III vs. Supplementary Tables.
- Any dataset-size statement (e.g., “1082 paired records”) versus what will be released in the artifact package; if the released package differs, add a clear note in the artifact/availability section.

