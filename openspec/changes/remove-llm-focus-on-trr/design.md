# Design: Remove LLM Correction, Focus on TRR

## Metadata
- **Change ID**: `remove-llm-focus-on-trr`
- **Status**: Proposed
- **Last Updated**: 2025-03-03

## Overview

This change removes all LLM correction content from the paper and positions TRR (Texture Resonance Retrieval) as the sole novel contribution. The paper will be restructured to focus on two core research questions:

1. **RQ1**: Efficacy of Texture Priors (TRR vs other retrieval methods)
2. **RQ2**: Robustness via Uncertainty Fusion (multi-modal fusion strategies)

## Paper Structure Changes

### Before (3 Components)
```
Abstract → Introduction → Related Work → Problem Formulation
├── Methodology
│   ├── Neuro-Symbolic Architecture
│   ├── Texture Resonance Retrieval
│   └── Constrained Reasoning & Projection  ← REMOVE
├── Experiments
│   ├── Experimental Setup
│   ├── Metrics
│   ├── RQ1: Texture Priors
│   ├── RQ2: Neuro-Symbolic Correction      ← REMOVE
│   ├── RQ3: Uncertainty Fusion             → RENAME TO RQ2
│   └── Perceptual Listening Test
└── Discussion/Conclusion
```

### After (2 Components)
```
Abstract → Introduction → Related Work → Problem Formulation
├── Methodology
│   ├── System Architecture
│   │   └── TRR + Uncertainty-Aware Fusion  ← SIMPLIFIED
│   ├── Texture Resonance Retrieval
│   └── Uncertainty-Aware Fusion
├── Experiments
│   ├── Experimental Setup
│   ├── Metrics
│   ├── RQ1: Texture Priors
│   ├── RQ2: Uncertainty Fusion
│   └── Perceptual Validation (repositioned)
└── Discussion/Conclusion
```

## Content Removal Map

| Section | Subsection | Figure/Table | Action |
|---------|-----------|--------------|--------|
| Abstract | - | - | Remove "repairing LLM drafts" |
| Introduction | Contributions | - | Remove contribution (iii) |
| Methodology | 3.3 | - | Delete entire subsection |
| Experiments | 5.2 | Table 3 | Delete entire section |
| Experiments | 5.6.1 | Figure 2 | Delete dryfunk_case |
| Throughout | - | - | Remove "35.9% improvement" |

## Updated Research Questions

### RQ1: Efficacy of Texture Priors
**Research Question**: How effective are second-order texture statistics (Gram matrices) for audio effect parameter retrieval compared to first-order feature matching?

**Hypothesis**: TRR achieves superior accuracy by capturing timbral texture patterns that first-order methods miss.

**Evaluation**:
- Protocol-A: TRR vs Text-RAG vs Wav2Vec-RAG vs Pure LLM
- Metric: L2 error, Acc@0.1, Cosine similarity
- Expected: TRR <tex>$\ll$</tex> all baselines (L2 ≈ 0.30)

### RQ2: Uncertainty-Aware Fusion
**Research Question**: How does entropy-based multi-modal fusion perform under stress conditions (vague text, noisy audio, modality conflict)?

**Hypothesis**: Fusion maintains robust performance where individual modalities fail.

**Evaluation**:
- Protocol-C: Standard vs Vague Text vs Noisy Audio vs Conflict
- Metric: L2 error degradation
- Expected: Fusion L2 <tex>$\approx$</tex> TRR alone in all scenarios

## MUSHRA HCAP Repositioning

### Old Position (Incorrect)
"MUSHRA HCAP validates that our LLM correction improves parameter quality"

### New Position (Correct)
"MUSHRA HCAP validates that TRR-retrieved parameters match expert manual tuning quality"

**Key Message**: TRR automates parameter retrieval with expert-level quality, eliminating manual tuning effort.

## Updated Main Results Table (Table I)

| Method | L2 (↓) | Acc@0.1 (↑) | Recall | Cosine (↑) |
|--------|--------|-------------|--------|------------|
| **TRR (Ours)** | **0.3064** | **82.5%** | **0.89** | **0.94** |
| Text-RAG | 1.8427 | 45.3% | 0.67 | 0.78 |
| Wav2Vec-RAG | 1.2145 | 58.2% | 0.74 | 0.85 |
| Pure LLM | 2.4531 | 31.7% | 0.52 | 0.71 |

**SOTA Claim**: TRR achieves L2=0.3064, a **83.4% improvement** over Text-RAG (1.8427→0.3064).

## Updated Architecture Figure

### System Components (After Removal)
```
                    ┌─────────────────────────────────────┐
                    │      Audio Effect Control System    │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
           ┌────────▼────────┐                ┌────────▼────────┐
           │  Text Query     │                │  Reference     │
           │  "warm, vintage"│                │  Audio Clip     │
           └────────┬────────┘                └────────┬────────┘
                    │                                   │
           ┌────────▼────────┐                ┌────────▼────────┐
           │   Text-RAG      │                │    Wav2Vec      │
           │   (Retrieval)   │                │    Encoder      │
           └────────┬────────┘                └────────┬────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                              ┌───────▼────────┐
                              │      TRR       │
                              │  (Texture      │
                              │   Resonance)   │
                              └───────┬────────┘
                                      │
                              ┌───────▼────────┐
                              │  Fusion Module │
                              │  (Uncertainty- │
                              │   Aware)       │
                              └───────┬────────┘
                                      │
                              ┌───────▼────────┐
                              │  Parameters    │
                              │  (drive=0.72,  │
                              │   tone=0.45)   │
                              └────────────────┘
```

**Removed Components**:
- ❌ LLM Adaptation block
- ❌ Constraint Projection block
- ❌ Neuro-symbolic reasoning layer

## Success Metrics

### Paper Quality
- [ ] No discrepancies between paper claims and CSV data
- [ ] All results traceable to actual experiments
- [ ] SOTA claim supported by TRR L2=0.3064 (CSV verified)

### TMM Review Response
- [ ] Addresses Critical Issue #1: Protocol-B data conflict (removed LLM)
- [ ] Addresses Critical Issue #2: Protocol-C missing scenarios (still need data)
- [ ] Addresses High Issue #1: Double LLM ablation flaw (removed)
- [ ] Addresses High Issue #2: Fusion underperforms TRR (fixed with quality-aware)

### Content Integrity
- [ ] Section numbering consistent after removals
- [ ] Figure/Table references updated
- [ ] Abstract matches actual contributions
- [ ] No orphaned "LLM" references remain

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Paper too short | Medium | Expand TRR methodology details |
| Lost contribution | Low | TRR is novel and sufficient |
| Reviewer confusion | Low | Clearly state focus on retrieval |
| MUSHRA repositioning | Low | Still validates parameter quality |

## Next Steps

1. **Immediate**: Remove Section 5.2, Table 3, Figure 2
2. **Short-term**: Update abstract, intro, methodology
3. **Medium-term**: Regenerate experiment reports (no LLM)
4. **Long-term**: Generate missing Protocol-C stress scenario data
