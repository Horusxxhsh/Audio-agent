# Revision Summary: fix-tmm-major-revision-gaps

## Overview of Changes

This revision has successfully synchronized the manuscript's experimental narrative with the reproducible evidence grounded in the current repository. The evidence chain has been substantially strengthened by expanding the test scale from $N=30$ to $N=211$ and introducing rigorous statistical verification.

### Completed Actions
- **Evidence Realignment**: All objective tables (Table 4, 5 and Supplementary Table S1-S4) now match the latest Protocol-A outputs exactly.
- **Narrative Convergence**: Removed `fusion` as a primary evidence source, focusing on the `TRR` (Texture Resonance Retrieval) main evidence chain to improve reproducibility and clarity.
- **Statistical Grounding**: Integrated 95% bootstrap confidence intervals and paired permutation significance tests (Holm-corrected) across all objective comparisons.
- **Methodological Cleanup**: Purged engineering-level details (script filenames, temporary implementation names) from the manuscript setup to meet journal-quality standards.
- **Transparency**: Added a comprehensive layer-sweep analysis for the TRR encoder and detailed latency profiling.
- **Response Package**: Generated a point-by-point response to reviewers addressing all major revision concerns raised by the TMM review team.

## Outstanding Items (Post-Audit Actions)

While the current manuscript is now self-consistent and grounded, the following items remain as high-priority commitments for the final resubmission:

1. **Cross-Domain Evaluation (P1-A)**:
   - Need to run evaluation on at least one non-guitar dataset (e.g., Vocal FX or Synthesis Timbre).
   - Deliverable: A new results table showing cross-domain generalization performance.

2. **Advanced Baselines (P1-B)**:
   - Implement and compare against CLAP-based and PaSST-based retrieval baselines.
   - Investigate at least one learned regressor or re-ranker as a stronger baseline than direct retrieval.

3. **Subjective Protocol Upgrade (P1-C)**:
   - Collect and report participant expertise metadata.
   - Standardize loudness matching and time budget documentation for the supplementary appendix.

4. **Acoustic Probing (P1-D)**:
   - Perform deeper analysis into the TRR layer-10 behavior (e.g., sensitivity to transient vs. modulation features).

5. **Algorithm Documentation (P1-E)**:
   - Formulate the deterministic validity-repair/projection algorithm in pseudo-code for the methods section.

## Verification Status

- [x] LaTeX compilation check (Pass)
- [x] Numerical alignment check (Pass)
- [x] Figure/Table numbering check (Pass)
- [x] Terminology consistency check (Pass)

**Recommendation**: The workspace is now ready for archival of this specific evidence-alignment change. Further feature work (cross-domain/baselines) should be initiated as separate follow-up changes.
