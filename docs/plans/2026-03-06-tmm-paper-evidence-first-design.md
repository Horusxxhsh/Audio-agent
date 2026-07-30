# TMM Paper Evidence-First Design

## Goal

Revise the paper so that the submission-quality claim chain is strictly bounded by artifacts that already exist in the repository or can be directly regenerated from the current codebase, while aligning structure and presentation with IEEE journal expectations.

## Why This Design

The current manuscript is not failing because of prose alone. It mixes three layers that must be separated for a safe TMM resubmission:

1. Verified evidence already backed by code and result artifacts.
2. Planned or partially scaffolded experiments that are described as if completed.
3. Reviewer-response narrative that is stronger than the executable evidence chain.

An evidence-first revision reduces rejection risk by collapsing the paper onto the strongest reproducible contribution: TRR-based retrieval for executable parameter control. This keeps the manuscript defensible even if some adaptive-memory, fusion, robustness, or latency claims remain incomplete.

## Constraints

- Do not rely on experiments that are only present as proposal text or half-implemented scripts.
- Prefer claims that can be traced to local result tables, CSVs, figures, or reproducible scripts.
- Preserve anonymity and TMM-style journal tone.
- Fix LaTeX hygiene issues that currently block clean submission review.

## External Alignment

- IEEE Author Center guidance emphasizes standard journal article structure, concise abstracts, and clean figure/table/citation presentation.
- IEEE TMM scope centers on multimedia signal processing, systems, and applications, so the paper must foreground the multimedia/audio-method contribution rather than tool-building rhetoric.
- Related-work positioning should privilege concrete prior work in semantic audio control, audio effect parameter inference, retrieval, and audio representation learning over broad agent rhetoric.

## Recommended Paper Positioning

Primary contribution:

"Texture Resonance Retrieval (TRR) improves retrieval-based executable parameter control on a held-out guitar-effects benchmark."

Secondary contributions that may remain only if fully supported after audit:

- Retrieval is materially stronger than direct LLM parameter generation.
- A listening study provides complementary perceptual evidence for workflow relevance.

Claims to demote unless fully verified during audit:

- AEM as a core validated contribution.
- Protocol-C robustness under realistic noise.
- Real end-to-end deployment latency beyond the currently verified measurement setup.
- Strong "state-of-the-art" language against modern external baselines unless those baselines are actually run and reported from this repository.

## Revision Strategy

### 1. Submission Hygiene

- Fix figure path inconsistencies and compile blockers.
- Normalize captions, labels, and anonymous reproducibility statements.
- Check citation integrity, undefined references, and bibliography consistency.

### 2. Claim Audit

- Build a claim-to-evidence map from the manuscript to local artifacts.
- Mark each statement as `verified`, `weakly supported`, or `unsupported`.
- Rewrite abstract, introduction, methods framing, experiments, discussion, and limitations accordingly.

### 3. Research Verification

- Verify that cited prior work is real, relevant, and properly positioned.
- Remove or soften comparisons that imply unrun SOTA baselines.
- Strengthen the "why TMM cares" framing: editable control, retrieval-grounded executability, perceptual alignment, and DAW workflow utility.

### 4. Output Standard

The revised paper should satisfy four conditions:

- It compiles cleanly.
- Every major numeric claim maps to a local artifact.
- Every major contribution sentence is narrower than or equal to the evidence.
- The paper reads like a focused journal manuscript, not a running revision memo.

