# Proposal: Remove LLM Correction, Focus on TRR

## Metadata
- **Change ID**: `remove-llm-focus-on-trr`
- **Status**: Proposed
- **Priority**: High
- **Created**: 2025-03-03
- **Author**: Claude (based on user request)

## Problem Statement

### Critical Issues with LLM Correction Approach

1. **Performance Degradation**: TRR+LLM (L2=6.2434) performs **20x worse** than pure TRR (L2=0.3064)
   - Only 15.2% of queries improve with LLM correction
   - 55.5% of queries get worse
   - The "SOTA" claim of 0.2631 is not supported by traceable CSV data

2. **Fundamental Design Flaw**: Adding LLM correction is NOT a valid ablation experiment
   - TRR already uses LLM-generated results (text description → audio retrieval)
   - Adding another LLM step is redundant, not a meaningful comparison
   - This violates experimental design principles

3. **Data Integrity Issues**:
   - Protocol-B: Paper claims L2=0.2631, but CSV shows L2=6.2434 (Critical)
   - Protocol-C: Paper reports 4 scenarios, CSV only contains "standard" (Critical)

## Proposed Solution

**Remove all LLM correction content and focus on TRR as the sole contribution**

### Scope of Changes

#### Remove Entirely:
1. **Section 5.2**: "RQ2: Neuro-Symbolic Correction"
2. **Table 3**: `llm_enhancement` comparison (TRR vs TRR+LLM)
3. **Figure 2**: `dryfunk_case` module correction visualization
4. **Section 3.3**: "Constrained Reasoning and Projection" subsection
5. **Abstract**: References to "repairing LLM drafts"
6. **Key Contribution (iii)**: "Constrained Neuro-Symbolic Execution"
7. **All "35.9% improvement" claims** throughout the paper

#### Restructure:
1. **System Architecture**: 3 components → 2 components
   - Remove: LLM Adaptation, Constraint Projection blocks
   - Keep: Texture Resonance Retrieval, Uncertainty-Aware Fusion

2. **Research Questions**: RQ1, RQ2, RQ3 → RQ1, RQ2
   - Remove: RQ2 (Neuro-Symbolic Correction)
   - Rename: RQ3 (Fusion robustness) → RQ2

3. **Main Results (Table I)**: Compare pure retrieval methods
   - TRR (L2=0.3064) ← **New SOTA**
   - Text-RAG
   - Wav2Vec-RAG
   - Pure LLM (no retrieval)

4. **MUSHRA HCAP**: Reposition as "retrieved parameters vs manual tuning comparison"
   - NOT a validation of LLM correction
   - Shows our TRR-retrieved parameters match expert tuning

## Rationale

### Why This is the Right Choice

1. **Scientific Integrity**: Report what actually works (TRR L2=0.3064 is SOTA)
2. **Experimental Validity**: Remove the flawed "double LLM" ablation design
3. **Paper Focus**: TRR (Gram matrix texture matching) is novel and sufficient contribution
4. **Reviewer Confidence**: Traceable data in CSV files, no discrepancies

### What We Keep (Strong Results)

| Scenario | Metric | TRR Result | Status |
|----------|--------|------------|--------|
| Protocol-A (standard) | L2 | 0.3064 | ✓ SOTA |
| Protocol-C (fusion) | L2 | 0.3056 | ✓ Robust |
| MUSHRA HCAP | Score | ~manual | ✓ Validated |

## Capabilities

No new capabilities added. This is a **content removal** change to align the paper with actual experimental results.

## Impact Assessment

### Positive
- Paper claims now match traceable data
- Remove controversial/discredited LLM correction approach
- Clearer contribution: TRR is novel and sufficient
- Addresses 2 Critical + 2 High issues from TMM review

### Neutral/Negative
- Reduced paper length (~2 pages removed)
- Remove one research question (was flawed anyway)
- MUSHRA needs repositioning (still valid as parameter comparison)

## Dependencies

None - this is a paper content change only.

## Success Criteria

1. [ ] All LLM correction content removed from paper
2. [ ] TRR positioned as sole contribution with SOTA results (L2=0.3064)
3. [ ] MUSHRA repositioned as parameter quality validation
4. [ ] No discrepancies between paper claims and CSV data
5. [ ] Research questions reduced to 2 (Texture Priors, Fusion)

## Timeline

- Phase 1: Remove LLM sections (Tables 3, Figures 2, Section 5.2)
- Phase 2: Update abstract, introduction, methodology
- Phase 3: Reposition MUSHRA and update main results table
- Phase 4: Regenerate experiment reports without LLM methods
