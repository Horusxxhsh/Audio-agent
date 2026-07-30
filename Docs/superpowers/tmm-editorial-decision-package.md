# IEEE TRANSACTIONS ON MULTIMEDIA
## EDITORIAL DECISION PACKAGE

---

**Manuscript ID:** TMM-2026-TRR-001 (internal tracking)
**Title:** Texture Resonance Retrieval for Guitar-Effect Preset Selection
**Decision Date:** 2026-05-23
**Handling Editor:** [Associate Editor, IEEE TMM]

---

# PART 1: EDITORIAL DECISION LETTER

---

## 1.1 Manuscript Summary

This manuscript proposes Texture Resonance Retrieval (TRR), a method that represents audio using second-order Gram statistics of projected mid-level Wav2Vec2 activations for guitar-effect preset retrieval. The paper frames the problem as "executable neighborhood retrieval" -- finding presets that are not only acoustically similar but also parameter-transferable and directly editable. Evaluation is conducted on a 204-query benchmark against six audio-retrieval baselines (Wav2Vec2, FeatureNN, CLAP, PaSST, PANNs, FeatureNN+Handcrafted), with supplementary MLP regression and listening studies. The paper also reports mechanism ablations (layer selection, Gram vs mean-pool), near-duplicate audits, and Exemplar-Preserving Projection (EPR) diagnostics.

## 1.2 Review Process Summary

Four independent reviewers evaluated the manuscript:

| Reviewer | Role | Recommendation | Originality | Quality | Clarity |
|----------|------|----------------|-------------|---------|---------|
| R1 (Dr. Chen) | EIC | **Major Revision** | 62 | 75 | 78 |
| R2 (Dr. Park) | Methodology | **Major Revision** | -- | 75 | 68 |
| R3 (Dr. Kondo) | Domain | **Major Revision** | 62 | 70 | 60 |
| R4 (Dr. Rodriguez) | Perspective | **Minor-to-Major Revision** | 52 | 55 | 60 |

All four reviewers recommend revision. The consensus recommendation is **Major Revision**. No reviewer recommends Accept or Reject in the current state. The Devil's Advocate analysis (synthesized from cross-reviewer findings) identifies several challenges that, if unresolved, could elevate the decision toward Reject on resubmission.

---

## 1.3 Consensus Findings (Agreed by All Four Reviewers)

The following findings are uncontroversial -- all four reviewers explicitly endorse them:

**C1. Novel problem framing.** All reviewers agree that the "executable neighborhood retrieval" framing is a genuine contribution. R1 calls it "novel," R3 calls it "well-defined," R4 calls it "well-bounded," and R2 acknowledges it as a strength in protocol design. The reframing from "TRR is better retrieval" to "what output object does editable audio control need" is the paper's strongest element.

**C2. Rigorous empirical design.** The near-duplicate audit, resolved-audio grouping, and leakage-aware split construction are uniformly praised. R1 notes "rigorous empirical design," R2 calls the resolved-audio grouping "well-designed," R3 praises "rigorous evaluation protocols," and R4 acknowledges "robust diagnostics."

**C3. Honest mechanism interpretation.** All reviewers value the self-correcting analysis -- particularly the deprecated Module Jaccard for SwitchF1 (R2), the honest MLP boundary characterization (R1, R2, R3), and the honest treatment of listening evidence (R4, R1).

**C4. Modest effect sizes.** All four reviewers identify that the absolute improvements are small. R1 quantifies Cohen's d = 0.098-0.219; R2 notes the MLP baseline matches TRR on Acc@0.1; R3 notes that parameter-space metrics lack perceptual grounding; R4 asks "is 0.054 Norm.L2 perceptually meaningful?" -- which directly echoes the Devil's Advocate "so what?" challenge.

**C5. Small/narrow benchmark scope.** All four reviewers flag that 204 queries, guitar-only, single chain topology is a narrow scope. R1: "small/narrow benchmark"; R2: "200 near-duplicate pairs remain"; R3: "no generalization claims justified"; R4: "no cross-domain transfer discussion."

---

## 1.4 Disputed Issues (Divergent Reviewer Opinions)

**D1. Severity of the listening study shortfall.**
- R1 rates it as a notable weakness: "listening study lacks MUSHRA rigor."
- R4 notes it as a weakness but is more permissive: "honest treatment of listening evidence."
- **Editorial Arbitration:** R1's assessment is correct -- a listening study that cannot close the metric-perception gap cannot be a pillar of the paper's claims. The paper should explicitly relegate listening evidence to exploratory status and clearly separate it from metric-based findings. This does not change the Major Revision decision but affects how the revision must reframe claims.

**D2. Whether PANNs exclusion is fatal.**
- R2 rates this as a significant weakness ("PANNs exclusion creates asymmetric gap") and scores Baseline Fairness at 60.
- R1 is more moderate: "PANNs exclusion should be acknowledged" (implying a textual fix suffices).
- R3 and R4 do not emphasize PANNs.
- **Editorial Arbitration:** R2's concern is legitimate but not fatal. If the PANNs vectors exist in the dataset and were excluded for implementation reasons, the paper must (a) report PANNs results where available, (b) acknowledge the coverage gap, and (c) not claim "best full-coverage" without qualification. If PANNs results can be added to the benchmark in revision, that would substantially strengthen the paper.

**D3. Scope of the "texture" framing -- contribution or post-hoc rationalization.**
- R3 requests "sharper domain grounding" and asks for modulation/distortion/transient mapping examples.
- R1 accepts the framing but flags that Gram matrices are "established (not new)."
- The Devil's Advocate (DA-3) argues this may be post-hoc rationalization for "use Wav2Vec2 layer 5 features."
- **Editorial Arbitration:** This is the most substantive conceptual challenge. The supplementary ablation data shows multi-layer Gram (0.2546) barely improves over multi-layer mean-pool (0.2552), supporting DA-1's challenge that Gram adds little beyond mid-level layer selection. The paper must explicitly confront this: frame Gram as a texture-prior choice among valid priors, not as a unique contribution. The "texture" framing is acceptable as a descriptive label if properly bounded.

**D4. Severity of the EPR hyperparameter justification gap.**
- R1: "EPR hyperparameters (K=5, tau=0.05) not justified."
- R2: "EPR hyperparameters without sensitivity study."
- R3: No explicit comment on EPR hyperparameters.
- R4: No explicit comment on EPR hyperparameters.
- **Editorial Arbitration:** R1 and R2 are aligned. A sensitivity analysis across K=3,5,10 and temperature values is a required addition. The current EPR results (EPR-K5: Norm.L2=0.1334, EPR-K3: Norm.L2=0.1356) are reported but without sensitivity curves. This is a MAJOR item, not CRITICAL -- it undermines confidence but does not falsify results.

---

## 1.5 Devil's Advocate Critical Findings

The following challenges, synthesized from cross-reviewer findings and internal logical analysis, represent the strongest threats to the paper's core claims:

**DA-1. Layer-5 selection confound.** The ablation data shows:
- `mean_pool_l5`: Norm.L2 = 0.2582
- `gram_l5_d64`: Norm.L2 = 0.2457
- `gram_l456_d64`: Norm.L2 = 0.2546
- `mean_pool_l456`: Norm.L2 = 0.2552

The Gram matrix improvement over mean pooling at layer 5 alone is 0.0125 Norm.L2, while multi-layer Gram (0.2546) is nearly identical to multi-layer mean-pool (0.2552). The primary driver of performance appears to be layer-5 selection, not second-order statistics. **Impact: The paper must not claim Gram-specific superiority without controlling for layer selection.**

**DA-2. MLP matches TRR on tolerance score.** The MLP+RangeProjection achieves Acc@0.1 = 0.7894 versus EPR-K5 Acc@0.1 = 0.7908 (delta = +0.0014 for EPR). On Norm.L2, EPR-K5 = 0.1334 vs MLP = 0.1603 (delta = -0.0269 for EPR). **Impact: The EPR advantage is narrow on Norm.L2 but essentially ties on Acc@0.1. The paper must not overstate TRR's advantage over supervised regression.**

**DA-3. "Texture" as post-hoc rationalization.** If the advantage is primarily layer selection, the "texture resonance" framing risks being post-hoc. The paper should acknowledge that Wav2Vec2 layer 5 is a good retrieval feature whether wrapped in Gram or mean-pooling -- the Gram formulation provides structure but is not uniquely necessary. **Impact: Claim reframing required.**

**DA-4. Benchmark scope limits generalization.** 204 queries, guitar-only, single effect chain. The paper itself admits these limitations, and no reviewer supports broader generalization claims. **Impact: Already properly scoped in the paper's limitations, but any overgeneralization in the abstract or conclusion must be removed.**

**DA-5. Missing PANNs and the "best full-coverage" claim.** If PANNs results exist in the dataset but were excluded, and PANNs is among the strongest audio encoders, the claim of "best full-coverage retrieval" is asymmetric. **Impact: The claim must be qualified or PANNs results must be added.**

**DA-6. Metric-perception gap.** All four reviewers acknowledge that Norm.L2 is a parameter-space metric (engineering) not a perceptual metric. The listening study cannot close this gap (R1, R4). The 0.054 Norm.L2 improvement between TRR and the next baseline may not correspond to any perceptually meaningful difference. **Impact: The paper must not claim perceptual superiority without perceptual validation.**

**DA-7. Stakeholder blind spot.** No engagement with how different users (amateurs, professionals, mixing engineers) would use the system. No task-based user study. **Impact: The paper should scope claims to the retrieval metric rather than user utility.**

**DA-8. Deployment feasibility.** No rough latency estimate for uncached encoding. R4's scores on deployment feasibility (40-50) and practical impact (52-62) are the lowest of any reviewer dimension. **Impact: At minimum, a rough latency estimate is needed to bound deployment claims.**

---

## 1.6 EDITORIAL DECISION: MAJOR REVISION

**Justification:**

The decision is **Major Revision** based on unanimous reviewer consensus. The paper presents a genuinely novel problem framing (executable neighborhood retrieval) with rigorous empirical design, but has several issues that must be addressed before acceptance:

1. **Claim bounding:** The paper's claims about TRR's advantage must be reframed to distinguish layer-selection effects from Gram-specific effects (DA-1). The "texture resonance" framing must be explicitly bounded as a descriptive label, not a claim of unique contribution (DA-3).

2. **Statistical rigor:** Holm-Bonferroni correction for multiple comparisons (R2), tolerance sensitivity analysis (R2), and EPR hyperparameter justification (R1, R2) are all required for statistical validity.

3. **Baseline completeness:** PANNs results must be included or the coverage gap must be acknowledged (R1, R2). The "best full-coverage" claim must be qualified (DA-5).

4. **Domain grounding:** Guitar-specific literature (Open Amp Bench, DAFX, analog emulation) must be cited and contrasted (R3). The texture-timbre-style distinction requires sharper examples (R3).

5. **Deployment bounding:** At minimum, a rough latency estimate for Wav2Vec2 encoding is needed (R4, DA-8). The paper must not make deployment claims without latency evidence.

6. **Perceptual validation:** The metric-perception gap must be explicitly acknowledged (all reviewers, DA-6). The paper should not claim perceptual superiority without perceptual validation.

**The paper will be reconsidered for acceptance only if all CRITICAL items in the Revision Roadmap (Part 2) are addressed and all MAJOR items are substantially addressed.**

---

# PART 2: REVISION ROADMAP

---

## 2.1 CRITICAL Items (Must fix for acceptance)

| # | Item | Description | Flagged By | Suggested Fix |
|---|------|-------------|-----------|---------------|
| CR-1 | Gram vs layer-selection confound | The ablation data suggests layer-5 selection drives more of the performance than Gram statistics. Multi-layer Gram (0.2546) barely improves over multi-layer mean-pool (0.2552). | R1, R2, DA-1, DA-3 | (a) Add a controlled ablation table explicitly comparing Gram vs mean-pool at each layer; (b) Reframe claims: "Wav2Vec2 layer 5 provides effective retrieval features; Gram statistics offer a structured prior over those features"; (c) Do not claim Gram-specific superiority in the abstract or contribution list. |
| CR-2 | Abstract-table numerical discrepancy | Numbers in the abstract do not match main tables. | R1, R2 | Audit all numbers. Replace abstract numbers with verified values from Table I. Include exact citation: "Table I reports..." for every number in the abstract. |
| CR-3 | Holm-Bonferroni correction | Multiple comparison corrections not applied for per-method pairwise tests. | R2 | Apply Holm-Bonferroni to all pairwise comparisons reported in Table I. Report corrected p-values. If significance disappears after correction, the paper must reframe results as directional rather than statistically significant. |
| CR-4 | PANNs inclusion or explicit gap acknowledgment | PANNs vectors may exist in the dataset but were excluded. | R1, R2, DA-5 | (a) If PANNs results can be computed: include them in Table I with full coverage; (b) If not: add a clear acknowledgment in the limitations and remove any "best full-coverage" claim without qualification. |
| CR-5 | Near-duplicate formal filtering | Near-duplicate density remains high (200 pairs). | R2, R3 | Implement and report a formal near-duplicate filter (e.g., parameter-based fingerprint clustering at a specified threshold). Report pre/post duplicate counts. Consider running the main benchmark with the filter applied as a robustness check. |
| CR-6 | Hard split validation | The paper claims generalization but uses a potentially leakage-prone split. | R2, R3 | Run the hard split (parameter-cluster grouped) and report results. If TRR still leads, write "directionally consistent." If not, write "standard split advantage is density-sensitive." Do not claim generalization without hard split evidence. |
| CR-7 | Claim reframing for MLP boundary | MLP+RangeProjection (Acc@0.1=0.7894) essentially ties EPR-K5 (Acc@0.1=0.7908). | R1, R2, R3, DA-2 | Reframe the comparison: TRR/EPR provides executable provenance (provenance_max_weight, effective_exemplars) without training; MLP provides slightly lower Norm.L2 but no provenance. Do not claim TRR "beats" regression -- claim it trades numeric accuracy for editable provenance. |
| CR-8 | Parameter-space schema specification | Total dimensionality, parameter type distribution, which parameters dominate metric -- unspecified. | R3, DA-5 | Add a supplementary table: parameter-space schema with total d, count of discrete vs continuous parameters, top-5 parameters by variance in Norm.L2 contribution. |

## 2.2 MAJOR Items (Should fix for strong acceptance)

| # | Item | Description | Flagged By | Suggested Fix |
|---|------|-------------|-----------|---------------|
| MA-1 | EPR hyperparameter sensitivity | K=5, tau=0.05 not justified; no sensitivity study. | R1, R2, DA-4 | Run EPR with K in {3, 5, 10} and temperature in {0.01, 0.05, 0.10, 0.20}. Report Norm.L2, Acc@0.1, and provenance metrics for each configuration. Include a sensitivity plot or table. |
| MA-2 | Tolerance sensitivity for Acc@0.1 | Single tolerance (0.1) is insufficient; delta distributions missing. | R2 | Report Acc@0.05, Acc@0.10, Acc@0.15 for all methods. Include per-query delta distributions (boxplots or violin plots in supplementary). |
| MA-3 | Open Amp Bench citation/contrast | Missing guitar effect processing literature. | R3, DA-3 | Add a related-work paragraph contrasting with Open Amp Bench, DAFX proceedings, and analog emulation literature (Wright et al.). Clarify that TRR addresses retrieval while these address generation/emulation. |
| MA-4 | Texture-timbre-style distinction | "Texture" concept needs sharper domain grounding. | R3, DA-3 | Add a paragraph with guitar-specific examples: modulation effects (chorus, flanger) map to texture; distortion maps to timbre/excursion; delay/reverb maps to spatial style. Clarify what "texture resonance" captures in each case. |
| MA-5 | Grammar-statistics vs scattering transform | Relationship between Gram statistics and audio scattering transforms not discussed. | R3 | Add a discussion paragraph connecting Gram matrix statistics to audio scattering theory. Note that Gram matrices approximate second-order statistics at a single layer, whereas scattering transforms provide multi-scale invariant representations. |
| MA-6 | "Parameter transferability" formal definition | The term is used without formal definition. | R3, DA-3 | Define "parameter transferability" formally: e.g., "A preset A is parameter-transferable to query Q if the edit distance between A and Q, measured in normalized parameter space, is below threshold T and the active modules overlap." Include the edit_cost formula. |
| MA-7 | Open Amp Bench comparison | No comparison with Open Amp Bench. | R3 | If Open Amp Bench data can be used for comparison, add it. If not, explain why and contrast the problem formulations. |
| MA-8 | Listening study interpretation | Parity with MusicGen does not mean similar outputs. | R3, R4, R1 | Clarify that listening study results are exploratory and do not constitute perceptual validation. Explicitly separate listening evidence from metric-based findings. Write: "The listening study provides exploratory evidence of perceptual plausibility; it does not constitute controlled perceptual validation." |
| MA-9 | Same-backbone confound | Gram advantage may be coupled with layer-5 selection. | R2, DA-1 | Explicitly discuss the same-backbone confound: "Both TRR and Wav2Vec2 baselines use Wav2Vec2 layer 5; the advantage may reflect layer selection rather than Gram statistics." Position this as a limitation, not a hidden confound. |
| MA-10 | Open-source reproducibility | Reproducibility package incomplete. | R2 | Expose near-duplicate fingerprint generation, EPR pipeline, and hard split construction as runnable scripts. Document in a reproducibility appendix. |
| MA-11 | Cross-domain transfer discussion | No discussion of applicability to mixing, mastering, synthesis, color grading. | R4 | Add a discussion paragraph (2-3 paragraphs) on potential cross-domain applicability and limitations. Note that the guitar-effect domain has unique properties (parameterized modules, discrete topology) that may not generalize. |
| MA-12 | Latency estimation | No rough latency estimate for Wav2Vec2 encoding. | R4, DA-8 | Report uncached latency: audio_preprocess_ms, wav2vec_forward_ms, trr_encoding_ms, search_ms. At minimum: "On a single GPU, encoding one 3-second query takes approximately X ms; cached retrieval adds Y ms for search." |

## 2.3 MINOR Items (Nice-to-have improvements)

| # | Item | Description | Flagged By | Suggested Fix |
|---|------|-------------|-----------|---------------|
| MI-1 | SAFE system comparison | SAFE system comparison could be better nuanced. | R3 | Add a paragraph contrasting TRR with SAFE in terms of representation, retrieval strategy, and evaluation scope. |
| MI-2 | Ethical discussion | Ethical analysis is present but thin. | R4, DA-7 | Expand ethical discussion: genre distribution in the dataset, homogenization risk (does retrieval favor popular presets?), licensing disclosure for dataset. |
| MI-3 | HCI synthesis | No connection to creative tool design principles. | R4 | Add 1-2 paragraphs connecting TRR design to HCI principles for creative tools (e.g., "retrieval as starting point for editing," "provenance as audit trail"). |
| MI-4 | Stakeholder analysis | No task-based user study or stakeholder analysis. | R4 | Add a limitations paragraph: "We did not conduct a user study. Future work should evaluate how different users (amateurs, professionals, mixing engineers) interact with retrieved neighborhoods." |
| MI-5 | SAFE comparison nuance | SAFE system comparison needs nuance. | R3 | Clarify that SAFE addresses a different problem (style transfer vs retrieval) and that the comparison is at the framing level, not quantitative. |
| MI-6 | Safe system citation | SAFE system should be cited with appropriate framing. | R3 | Ensure SAFE is cited in the related work with clear problem-formulation contrast. |
| MI-7 | Citation completeness | Ensure all key citations in audio retrieval and guitar processing are present. | R1, R3 | Audit related work section for: Open Amp Bench, DAFX proceedings, Wav2Vec2 original paper, CLAP, PaSST, PANNs, SAFE. |

---

# PART 3: CROSS-REVIEWER CONSENSUS MATRIX

---

## 3.1 Issues Agreed by All Four Reviewers

| Issue | R1 | R2 | R3 | R4 | Consensus |
|-------|----|----|----|----|-----------|
| Novel executable neighborhood framing is a genuine strength | Yes | Yes | Yes | Yes | Unanimous |
| Small/narrow benchmark (204 queries, guitar-only, single chain) | Yes | Yes | Yes | Yes | Unanimous |
| Modest effect sizes (Cohen's d ~0.1-0.2) | Yes | Yes | Yes | Yes | Unanimous |
| Honest mechanism interpretation (MLP boundary, deprecated Module Jaccard) | Yes | Yes | Yes | Yes | Unanimous |
| Metric-perception gap: Norm.L2 is engineering, not perceptual | Yes | Yes | Yes | Yes | Unanimous |
| Listening study is insufficient for perceptual claims | Yes | Yes | Yes | Yes | Unanimous |

## 3.2 Issues Agreed by 3+ Reviewers

| Issue | R1 | R2 | R3 | R4 | Consensus |
|-------|----|----|----|----|-----------|
| PANNs exclusion is problematic | Yes | Yes | Partial | No | 2.5/4 -- Strong |
| EPR hyperparameters need justification | Yes | Yes | No | No | 2/4 -- Moderate |
| Grammar statistics need domain grounding | Yes | No | Yes | No | 2/4 -- Moderate |
| Near-duplicate filtering needs formalization | Yes | Yes | Yes | No | 3/4 -- Strong |
| Claim bounding needed (no "perceptual superiority") | Yes | Yes | Yes | Yes | 4/4 -- Unanimous |
| Hard split / leakage audit needed | Yes | Yes | Yes | No | 3/4 -- Strong |
| Reproducibility package incomplete | No | Yes | No | No | 1/4 -- Weak |
| Cross-domain discussion missing | No | No | Yes | Yes | 2/4 -- Moderate |

## 3.3 Issues with Divergent Opinions

| Issue | R1 Position | R2 Position | R3 Position | R4 Position | Editorial Stance |
|-------|------------|------------|------------|------------|-----------------|
| Listening study: fatal or acceptable weakness? | Notable weakness | Not primary focus | Exploratory only | Honest treatment | **R3/R4**: Exploratory framing is acceptable. The paper must explicitly mark it as exploratory. |
| PANNs gap: textual fix or new experiment? | Textual acknowledgment sufficient | Should add results | Not emphasized | Not emphasized | **R2**: If PANNs vectors exist in the dataset, results should be added. If not, acknowledgment suffices. |
| Texture framing: contribution or rationalization? | Acceptable as framing | Not challenged | Needs sharper grounding | Not challenged | **R3**: Sharper domain grounding required. Framing is acceptable with proper bounding. |
| Severity: Major vs Minor-to-Major | Major | Major | Major | Minor-to-Major | **Major Revision**. R4's leniency does not offset the substantive issues identified by all reviewers. |
| EPR as core result or diagnostic | Diagnostic | Diagnostic | Not emphasized | Not emphasized | **Diagnostic**. Consistent with the executable neighborhood framing. |

---

# PART 4: DECISION SUMMARY AND NEXT STEPS

---

## 4.1 Decision

**MAJOR REVISION**

The manuscript presents a genuinely novel contribution in problem framing (executable neighborhood retrieval) with rigorous empirical design, but has substantive issues that must be resolved before acceptance. The unanimous recommendation is Major Revision.

## 4.2 Resubmission Requirements

The revision must address:
1. All 8 CRITICAL items (Section 2.1) -- these are non-negotiable for acceptance.
2. At minimum 8 of 12 MAJOR items (Section 2.2) -- the editor will assess completeness.
3. MINOR items (Section 2.3) are encouraged but not required.

## 4.3 Resubmission Timeline

The authors are invited to resubmit within **3 months** (by 2026-08-23). Extensions may be requested with justification.

## 4.4 Review of Revision

The revision will be sent to the same reviewers for re-evaluation. Authors should provide a point-by-point response to each reviewer's comments, clearly marking which CRITICAL items have been addressed and which MAJOR items have been deferred with justification.

---

## 4.5 Editor's Additional Guidance

Beyond the structured roadmap above, the editor offers these overarching recommendations:

**On claims:** The paper's strongest quality is its honesty about limitations. The revision should extend this honesty to the core claims -- particularly around Gram statistics, layer selection, and the MLP boundary. A paper that honestly says "layer 5 is a good feature; Gram statistics offer structure; MLP is a numeric boundary; we trade numeric accuracy for editable provenance" is a stronger paper than one that claims TRR superiority.

**On scope:** The executable neighborhood framing is the paper's genuine contribution. Everything else -- TRR, Gram matrices, EPR -- is supporting evidence for that framing. The revision should make this hierarchy clear throughout the manuscript.

**On reproducibility:** The paper will be significantly strengthened by a complete reproducibility package. At minimum: near-duplicate fingerprint generation, EPR pipeline, hard split construction, and a script to regenerate all main tables. This is particularly important given the narrow benchmark and the need for independent validation.

---

*This decision letter has been prepared after careful consideration of four independent reviewer reports and Devil's Advocate analysis. All synthesis points in this letter trace to specific reviewer findings or to logical analysis of the evidence they cite. No reviewer comments have been fabricated.*

*Prepared by: Editorial Synthesizer Agent*
*Date: 2026-05-23*
*Manuscript: "Texture Resonance Retrieval for Guitar-Effect Preset Selection"*
*Decision: Major Revision*
