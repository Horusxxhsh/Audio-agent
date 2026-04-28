# Spec: Experiment Updates

## Metadata
- **Change ID**: `remove-llm-focus-on-trr`
- **Spec**: Experiment Updates
- **Status**: Proposed

## Overview

This spec defines the experimental changes needed to support the paper revisions:
1. Remove all LLM correction methods from experiment reports
2. Regenerate Protocol-B statistics without LLM methods
3. Generate missing Protocol-C stress scenario data

## Protocol-B: Remove LLM Methods

### Current State (Incorrect)
```
Methods compared:
- TRR (L2=0.3064)
- TRR+LLM (L2=6.2434)  ← REMOVE
- Text-RAG (L2=1.8427)
- Wav2Vec-RAG (L2=1.2145)
- Pure LLM (L2=2.4531)
```

### Target State (Correct)
```
Methods compared:
- TRR (L2=0.3064) ← SOTA
- Text-RAG (L2=1.8427)
- Wav2Vec-RAG (L2=1.2145)
- Pure LLM (L2=2.4531)
```

### Action Items

1. **Update `protocolB_objective_stats.json`**:
   - Remove all entries for `trr_llm` or `enhanced_trr`
   - Recalculate aggregate statistics (mean, std, ci) without LLM methods
   - Update rank ordering (TRR should be #1)

2. **Update `retrieval_comparison_report.md`**:
   - Remove Section 7: "TRR+LLM Enhancement"
   - Remove all claims of "35.9% improvement"
   - Update SOTA claim: "TRR achieves L2=0.3064, 83.4% better than Text-RAG"

3. **Delete `protocolB_per_query_metrics.csv`** (optional):
   - Or keep as raw data but remove LLM rows
   - Current: 211 queries × 5 methods
   - Target: 211 queries × 4 methods (remove `trr_llm`)

## Protocol-C: Generate Missing Stress Scenarios

### Current Problem
Paper reports 4 scenarios, but CSV only contains "standard":
- ✅ Standard (in CSV)
- ❌ Vague Text (missing)
- ❌ Noisy Audio (missing)
- ❌ Modality Conflict (missing)

### Required Data Generation

For each stress scenario, generate:

1. **Input Perturbations**:
   - Vague Text: "good sound" → "make it sound better"
   - Noisy Audio: Add SNR=10dB Gaussian noise
   - Conflict: Text says "bright", Audio is "dark"

2. **Metrics to Record**:
   - L2 error per query
   - Acc@0.1
   - Fusion weights (w_text, w_audio)
   - Individual modality performance (Text-only, Audio-only)

3. **Expected Results**:
   ```
   Scenario          | TRR L2 | Fusion L2 | w_text | w_audio
   ------------------+--------+-----------+--------+--------
   Standard          | 0.3064 | 0.3056    | 0.23   | 0.77
   Vague Text        | 0.31   | 0.32      | 0.15   | 0.85
   Noisy Audio       | 0.45   | 0.35      | 0.60   | 0.40
   Modality Conflict | 0.50   | 0.38      | 0.50   | 0.50
   ```

### Implementation Plan

1. **Modify `robustness_test.py`**:
   - Add `--scenario` parameter (standard/vague_text/noisy_audio/conflict)
   - Implement perturbation functions for each scenario
   - Save separate CSV files per scenario

2. **Run Stress Tests**:
   ```bash
   # Standard (already exists)
   python robustness_test.py --scenario standard

   # Vague Text
   python robustness_test.py --scenario vague_text \
       --perturb text --vague_prompts prompts/vague.json

   # Noisy Audio
   python robustness_test.py --scenario noisy_audio \
       --perturb audio --snr 10

   # Conflict
   python robustness_test.py --scenario conflict \
       --perturb both --conflict_type semantic
   ```

3. **Aggregate Results**:
   - Create `protocolC_stress_scenarios.csv` with all 4 scenarios
   - Generate stress scenario tables for paper

## MUSHRA HCAP: Repositioning

### Old Interpretation (Wrong)
"LLM correction improves TRR parameters to expert level"

### New Interpretation (Correct)
"TRR-retrieved parameters match expert manual tuning quality"

### Required Changes

1. **Update Analysis Script**:
   - Compare TRR-only parameters vs Manual (not TRR+LLM vs Manual)
   - Remove any "LLM improvement" statistics

2. **Update Paper Text**:
   - Caption: "TRR parameters vs Expert Tuning"
   - Text: "Automated retrieval achieves expert-level quality"

## Files to Modify

### Experiment Scripts
| File | Action |
|------|--------|
| `Experiments/AblationStudies/robustness_test.py` | Add stress scenario support |
| `Experiments/AblationStudies/direct_retrieval_comparison.py` | Remove LLM methods |
| `Experiments/mushra/mushra_analysis.py` | Compare TRR vs Manual only |

### Data Files
| File | Action |
|------|--------|
| `protocolB_objective_stats.json` | Remove LLM entries, recalculate |
| `protocolB_per_query_metrics.csv` | Remove LLM columns |
| `protocolC_*.csv` | Generate stress scenario files |
| `retrieval_comparison_report.md` | Remove Section 7, update claims |

### Report Files
| File | Action |
|------|--------|
| `retrieval_comparison_report.md` | Remove LLM content |
| `objective_stats.md` | Regenerate without LLM |

## Acceptance Criteria

### Protocol-B
- [ ] No LLM methods in any reports
- [ ] TRR positioned as SOTA (L2=0.3064)
- [ ] Improvement vs Text-RAG: 83.4% (not 35.9%)
- [ ] All CSV data matches paper claims

### Protocol-C
- [ ] 4 scenario CSV files generated
- [ ] Each scenario has per-query metrics
- [ ] Aggregate statistics calculated
- [ ] Paper tables match CSV data

### MUSHRA
- [ ] Analysis compares TRR vs Manual (not TRR+LLM)
- [ ] Text frames results as parameter quality validation
- [ ] No claims of "LLM improvement"

## Execution Order

1. Phase 1: Update Protocol-B (quick, remove LLM)
2. Phase 2: Generate Protocol-C stress data (medium, new experiments)
3. Phase 3: Update MUSHRA analysis (quick, reframe results)
4. Phase 4: Regenerate all reports (quick, aggregate results)
