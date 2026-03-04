# Response to Reviewers (IEEE TMM)

**Manuscript ID**: #8159
**Title**: Audio-Agent: Bridging the Semantic Gap in Neural Audio Effects via Multi-Modal Retrieval-Augmented Generation
**Authors**: Anonymous Authors

---

Dear Dr. [Editor Name] and the Review Team,

Thank you for the opportunity to revise our manuscript titled "Audio-Agent: Bridging the Semantic Gap in Neural Audio Effects via Multi-Modal Retrieval-Augmented Generation" (Manuscript ID: #8159). We appreciate the constructive and detailed feedback provided by the reviewers, which has significantly improved the technical depth and empirical grounding of our work.

We have carefully addressed all reviewer comments in this revision. The most significant changes include:

1. **Substantial Dataset Expansion**: We have expanded the evaluation test set from the initial $N=30$ queries to a more statistically robust pool of $N=211$ held-out queries. This represents a 703% increase in sample size, providing much stronger empirical support for our comparative results.
2. **Rigorous Statistical Evaluation**: We now report 95% bootstrap confidence intervals (CIs) and paired permutation tests for all primary objective metrics. This addressing the reviewers' concerns regarding the statistical significance of our findings.
3. **Narrative Convergence**: We have streamlined the paper's narrative to focus on the Texture Resonance Retrieval (TRR) evidence chain as the primary contribution, while moving auxiliary fusion results to a secondary role to maintain a clear and reproducible "single source of truth."
4. **Mechanical Interpretability of TRR**: We have added a comprehensive layer-sweep analysis across all 12 layers of the Wav2Vec2 backbone, confirming that layer 10 provides the optimal balance for audio texture retrieval.
5. **Refinement of Experimental Setup**: We have cleaned the manuscript of all internal engineering script names and temporary implementation details, ensuring the methodology is described in professional academic terms.

Below we provide point-by-point responses to each reviewer comment. Changes in the manuscript are highlighted in blue in the revised version.

---

## Reviewer 1 (General Feedback)

### Comment 1.1: Technical Correctness and Terminology
> **Quote**: "Observation 3 (Section 4.2) is stated as a 'Theorem' but is actually a basic property of Gram matrices. Suggest changing to 'Property' or 'Remark'."

**Response**: We agree with the reviewer's observation. The formal properties of the Gram matrix, while foundational to our TRR encoding, do not constitute a new mathematical theorem in the context of linear algebra. We have accordingly relabeled this section as "Property 1" and clarified its role as a conceptual justification for the translation invariance of texture descriptors in the audio domain.

**Changes in manuscript**: Section 4.2 has been updated; "Theorem 1" is now "Property 1: Translation Invariance of Texture Priors."

---

## Reviewer 2 (Experimental Design and Scale)

### Comment 2.1: Sample size and Statistical Power
> **Quote**: "The current evaluation with N=30 is insufficient for parameter space evaluation. A larger test set is required to draw reliable conclusions."

**Response**: We appreciate the reviewer's concern regarding the statistical power of our initial evaluation. To address this, we have substantially expanded our evaluation protocol (Protocol-A). The knowledge base has been increased to 1,056 items, and the held-out test set has been expanded to $N=211$ queries. This larger scale allows for more reliable performance estimates and ensures that our reported improvements are not due to sampling noise.

**Changes in manuscript**: Table 4 (tab:main_results) now reports results for $N=211$ queries. Corresponding text in Section 5.1 has been updated to reflect this larger evaluation scale.

### Comment 2.2: Statistical Significance
> **Quote**: "The paper lacks reporting of confidence intervals or p-values. Statistical significance testing is required."

**Response**: We agree that statistical reporting is critical for a journal of TMM's caliber. In this revision, we have included 95% bootstrap confidence intervals for all mean metric values (L2, Acc@0.1, Recall, Cosine, and Module consistency). Furthermore, we performed paired permutation tests (5,000 samples) to compare TRR against baseline methods (Text-RAG, Wav2Vec-RAG, and FeatureNN-RAG), reporting Holm-corrected $p$-values to control for multiple comparisons.

**Changes in manuscript**: Table S2 and Table S3 have been added to the Supplementary Material to provide full statistical transparency. Summary significance statements have been integrated into the Results section (Section 5.2).

---

## Reviewer 3 (Writing and Presentation)

### Comment 3.1: Abstract Length and Content
> **Quote**: "The abstract is too long (approx. 280 words) and contains too many specific numbers. Suggest condensing it to 150-250 words."

**Response**: We have revised the abstract to meet the IEEE TMM length requirements while maintaining focus on the core contributions. We removed exhaustive numerical lists, instead highlighting the most significant relative improvements (e.g., the 97.8% reduction in L2 error compared to pure LLM generation) to emphasize the necessity of the RAG framework.

**Changes in manuscript**: The abstract has been condensed to approximately 210 words.

### Comment 3.2: Numerical Discrepancy (Reviewer Tables 3/4, current Tables 4/5)
> **Quote**: "Table 3 and Table 4 report L2 values that differ by orders of magnitude (e.g., 0.08 vs 13.3). This requires explanation."

**Response**: We thank the reviewer for pointing out this potential source of confusion. The discrepancy arises from the use of different query subsets and candidate pools. Current Table 4 (tab:main_results) evaluates the full benchmark ($N=211$) using the primary knowledge base. In contrast, current Table 5 (tab:trr_texture_baselines) is a diagnostic comparison against classical texture baselines (MFCC, Modulation Spectrogram) conducted on a small, audio-available subset ($N=5$) where the absolute parameter scale and candidate pool density are different, naturally leading to a higher baseline L2 magnitude. We have added a clarifying note to the Table 5 caption to explicitly state that absolute magnitudes are not comparable across these two separate protocols.

**Changes in manuscript**: A clarifying statement was added to the caption of Table 5 in Section 5.3.

---

## Reviewer 4 (Reproducibility and Formatting)

### Comment 4.1: Implementation Details and Reproducibility
> **Quote**: "The paper should clarify key hyperparameters and provide a commitment to reproducibility (e.g., code and dataset availability)."

**Response**: We are committed to open science and reproducibility. We have now specified the exact Wav2Vec2 layer used for TRR encoding (Layer 10) in the main text and provided a complete layer-sweep analysis in the Supplementary Material. Upon acceptance, we will release a curated version of our dataset and an anonymized repository containing the full inference pipeline and evaluation scripts.

**Changes in manuscript**: Section 4.4 and Section 6 (Reproducibility) have been updated with these commitments and hyperparameter details.

---

We hope that these extensive revisions fully address the reviewers' concerns and that the manuscript is now suitable for publication in IEEE Transactions on Multimedia.

Sincerely,

The Authors
