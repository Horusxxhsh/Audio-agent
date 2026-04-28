# Tasks: Remove LLM Correction, Focus on TRR

## Metadata
- **Change ID**: `remove-llm-focus-on-trr`
- **Status**: Proposed
- **Total Tasks**: 15

## Phase 1: Paper Content Removal (Priority: High)

### Task 1.1: Update Abstract
- [ ] Remove "repairs LLM draft parameters" phrase
- [ ] Remove "neuro-symbolic" terminology
- [ ] Emphasize TRR as core contribution
- [ ] Update SOTA claim to TRR-only (L2=0.3064)
**File**: `Paper/content.tex` (Abstract section)
**Estimated**: 15 minutes

### Task 1.2: Update Introduction Key Contributions
- [ ] Remove contribution (iii): "Constrained Neuro-Symbolic Execution"
- [ ] Promote TRR from (ii) to (i)
- [ ] Promote Fusion from (iv) to (ii)
- [ ] Remove "Neuro-Symbolic Architecture" contribution
**File**: `Paper/content.tex` (Introduction section)
**Estimated**: 15 minutes

### Task 1.3: Delete Section 3.3 (Constrained Reasoning)
- [ ] Delete entire `\subsection{Constrained Reasoning and Projection}`
- [ ] Remove all constraint projection equations
- [ ] Remove LLM adaptation block descriptions
- [ ] Update section numbering (3.4 → 3.3, etc.)
**File**: `Paper/content.tex` (Section 3)
**Estimated**: 30 minutes

### Task 1.4: Delete Section 5.2 (RQ2: Neuro-Symbolic Correction)
- [ ] Delete entire RQ2 section
- [ ] Remove all LLM correction results
- [ ] Renumber remaining sections (5.3 → 5.2, 5.4 → 5.3)
**File**: `Paper/content.tex` (Section 5)
**Estimated**: 20 minutes

### Task 1.5: Remove Table 3 (LLM Enhancement)
- [ ] Delete `tab:llm_enhancement` entirely
- [ ] Remove all table references from text
- [ ] Check for orphaned `\ref{tab:llm_enhancement}`
**File**: `Paper/content.tex`
**Estimated**: 10 minutes

### Task 1.6: Remove Figure 2 (DryFuNK Case Study)
- [ ] Delete `fig:dryfunk_case` entirely
- [ ] Remove module correction visualization
- [ ] Check for orphaned `\ref{fig:dryfunk_case}`
**File**: `Paper/content.tex`
**Estimated**: 10 minutes

### Task 1.7: Update Table I (Main Results)
- [ ] Remove TRR+LLM row from results table
- [ ] Highlight TRR as SOTA (L2=0.3064)
- [ ] Recalculate improvement percentages
**File**: `Paper/content.tex` (Table I)
**Estimated**: 15 minutes

### Task 1.8: Remove All "35.9% Improvement" Claims
- [ ] Search entire `.tex` for "35.9%"
- [ ] Search for "LLM correction improves"
- [ ] Search for "neuro-symbolic execution"
- [ ] Replace or delete all instances
**File**: `Paper/content.tex`, `Paper/supplementary.tex`
**Estimated**: 20 minutes

### Task 1.9: Update MUSHRA HCAP Positioning
- [ ] Rewrite caption to emphasize TRR vs Manual comparison
- [ ] Update text to frame as "parameter quality validation"
- [ ] Remove any LLM correction claims
**File**: `Paper/content.tex` (Section 5.3/5.6)
**Estimated**: 15 minutes

## Phase 2: Experiment Updates (Priority: High)

### Task 2.1: Update Protocol-B Statistics
- [ ] Remove `trr_llm` entries from `protocolB_objective_stats.json`
- [ ] Recalculate aggregate stats (mean, std, ci)
- [ ] Update rank ordering
**File**: `Experiments/AblationStudies/protocolB_objective_stats.json`
**Estimated**: 30 minutes

### Task 2.2: Update Retrieval Comparison Report
- [ ] Remove Section 7: "TRR+LLM Enhancement"
- [ ] Update SOTA claim: "TRR achieves 83.4% improvement over Text-RAG"
- [ ] Remove all LLM correction references
**File**: `Experiments/AblationStudies/retrieval_comparison_report.md`
**Estimated**: 20 minutes

### Task 2.3: Generate Protocol-C Stress Scenario Data
- [ ] Add stress scenario support to `robustness_test.py`
- [ ] Run tests for: vague_text, noisy_audio, conflict
- [ ] Generate CSV files for each scenario
**File**: `Experiments/AblationStudies/robustness_test.py`
**Estimated**: 2 hours

### Task 2.4: Update MUSHRA Analysis
- [ ] Modify analysis to compare TRR vs Manual (not TRR+LLM)
- [ ] Remove "LLM improvement" statistics
- [ ] Reframe as "parameter quality validation"
**File**: `Experiments/mushra/mushra_analysis.py`
**Estimated**: 30 minutes

## Phase 3: Verification (Priority: Medium)

### Task 3.1: LaTeX Compilation Check
- [ ] Run `latexmk` to verify compilation
- [ ] Check for undefined references
- [ ] Check for duplicate labels
- [ ] Verify PDF generation
**Command**: `cd Paper && latexmk -pdf`
**Estimated**: 10 minutes

### Task 3.2: Content Consistency Check
- [ ] Verify all paper claims match CSV data
- [ ] Verify no orphaned figure/table references
- [ ] Verify section numbering is consistent
- [ ] Verify no remaining LLM references
**Estimated**: 30 minutes

### Task 3.3: TMM Review Response Verification
- [ ] Confirm Critical Issue #1 addressed (LLM removed)
- [ ] Confirm High Issue #1 addressed (double LLM flaw removed)
- [ ] Verify all changes address reviewer concerns
**Estimated**: 15 minutes

## Phase 4: Final Polish (Priority: Low)

### Task 4.1: Update Supplementary Material
- [ ] Remove LLM content from supplementary
- [ ] Update any remaining LLM references
- [ ] Ensure consistency with main paper
**File**: `Paper/supplementary.tex`
**Estimated**: 20 minutes

### Task 4.2: Update GitHub/Documentation
- [ ] Update README to reflect TRR-only focus
- [ ] Update any documentation mentioning LLM correction
- [ ] Update experiment scripts documentation
**Estimated**: 30 minutes

## Task Summary

| Phase | Tasks | Estimated Time | Priority |
|-------|-------|----------------|----------|
| 1. Paper Content Removal | 9 | ~2.5 hours | High |
| 2. Experiment Updates | 4 | ~3 hours | High |
| 3. Verification | 3 | ~1 hour | Medium |
| 4. Final Polish | 2 | ~1 hour | Low |
| **Total** | **18** | **~7.5 hours** | - |

## Execution Order

1. Start with Phase 1 (Tasks 1.1-1.9) - Critical path
2. Parallel Phase 2 (Tasks 2.1-2.4) - Can run alongside Phase 1
3. Phase 3 (Tasks 3.1-3.3) - After Phase 1 and 2 complete
4. Phase 4 (Tasks 4.1-4.2) - Optional polish

## Quick Start Commands

```bash
# Phase 1: Edit paper
cd /Users/xyh/Code/Audio-agent/Paper
vim content.tex  # Complete Tasks 1.1-1.9

# Phase 2: Update experiments
cd /Users/xyh/Code/Audio-agent/Experiments
# Complete Tasks 2.1-2.4

# Phase 3: Verify
cd /Users/xyh/Code/Audio-agent/Paper
latexmk -pdf  # Task 3.1
grep -n "LLM\|neuro.symbolic\|constraint" content.tex  # Task 3.2

# Phase 4: Polish
# Complete Tasks 4.1-4.2
```
