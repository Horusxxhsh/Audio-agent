# Response to Reviewers (IEEE TMM) -- Audio-Agent

Manuscript: ``Audio-Agent: Bridging the Semantic Gap in Neural Audio Effects via Multi-Modal Retrieval-Augmented Generation''

This document is a point-by-point response template. Replace bracketed placeholders and add page/line numbers after final PDF pagination.

## Summary of Major Changes in This Revision

- Abstract shortened and numeric clutter reduced.
- Related work expanded and positioning clarified (audio texture lineage, semantic audio retrieval and RAG context, and recent audio-language models).
- Notation and theory clarifications:
  - Element-wise inequality for $\preceq$ in the feasible set definition.
  - ``Observation 3'' renamed to ``Property 3''.
  - Clarified that the preference-distribution softmax uses unit temperature and that $\beta$ controls entropy-to-weight sensitivity.
- Figure/table readability improvements:
  - Architecture figure moved to a two-column layout.
  - Key tables avoid `\resizebox` where feasible; captions clarify protocol-scoped interpretation.
- Reproducibility strengthened:
  - Added a resources paragraph describing code/data/prompt release plan and split specifications.
  - Specified the Wav2Vec2 layer used for TRR feature extraction.

## Constraints for This Revision (Declared Up Front)

- No new experiments are added in this revision.
  - We do not expand the objective benchmark size.
  - We do not add new representation baselines (e.g., CLAP/PaSST) or additional audio-level metrics.
  - Instead, we clarify statistical scope and protocol limitations, strengthen limitations/future work, and improve reproducibility artifacts.

## High-Priority Comments

### C1. Experimental scale and statistical significance

**Comment.** [Paste the reviewer comment.]

**Response.** We agree that the current objective benchmark is a pilot. In this revision, we explicitly scope our claims to descriptive comparisons and avoid statistical-significance language for the objective metrics. We clarify protocol details and add a reproducibility package plan (split specifications and scripts) so the community can verify and extend the evaluation. We treat large-scale evaluation and full statistical reporting as future work.

**Changes in manuscript.**
- Section ``Experiments / Experimental Setup'': scope + comparability notes; clarified dataset split and KB size.
- Section ``Limitations'': expanded discussion of statistical power and dataset coverage.

### C2. Missing strong baselines (CLAP/PaSST) and audio-level metrics

**Comment.** [Paste the reviewer comment.]

**Response.** We agree these are important comparisons. Under the ``no new experiments'' constraint for this revision, we cannot add these results. We therefore (i) sharpen the limitations statement, (ii) clarify why Wav2Vec2 frame-level features are required for Gram-based TRR, and (iii) outline concrete future-work baselines and metric families (CLAP/PaSST/PANNs; audio-space metrics such as FAD or multi-resolution STFT losses).

**Changes in manuscript.**
- Section ``Limitations / Baseline Strength'': explicit baseline gap and planned comparisons.
- Section ``Metrics'': clarified that parameter-space metrics are operational proxies; audio-space metrics are future work.

### C3. Abstract length and readability

**Comment.** [Paste the reviewer comment.]

**Response.** We shortened the abstract to meet the typical journal length guidance and removed most numeric details, keeping only high-level experimental scope.

**Changes in manuscript.**
- Abstract rewritten and condensed.

### C4. Related work completeness (Gram-matrix audio lineage; audio language models; RAG in MIR)

**Comment.** [Paste the reviewer comment.]

**Response.** We expanded the related work section to (i) acknowledge prior Gram-matrix/audio-texture uses and clarify how TRR differs (retrieval embedding for executable parameter inference), (ii) better situate our work in semantic audio retrieval and audio RAG, and (iii) mention recent instruction-following audio language models and why executable parameter control remains distinct.

**Changes in manuscript.**
- Related Work: added/expanded paragraphs in ``Audio Texture and Semantic Audio Retrieval'' and ``Perceptual similarity vs. parameter transferability''.

### C5. Notation/clarity issues (Observation 3; softmax vs. beta)

**Comment.** [Paste the reviewer comment.]

**Response.** We adjusted the presentation to avoid over-stating a basic property, and clarified the roles of the softmax used to construct the preference distribution and the $\beta$ hyperparameter used to map entropy into fusion weights.

**Changes in manuscript.**
- Methodology: ``Observation 3'' renamed to ``Property 3''.
- Fusion subsection: clarified unit-temperature softmax and interpretation of $\beta$.

### C6. Figure/table readability and metric magnitude interpretation

**Comment.** [Paste the reviewer comment.]

**Response.** We improved figure/table readability and clarified that comparisons should be interpreted within the stated protocol (within-table), since absolute magnitudes of parameter-space metrics can depend on encoding and the operational setting.

**Changes in manuscript.**
- Architecture figure moved to a two-column layout.
- Key tables adjusted to reduce over-aggressive resizing.
- Experimental setup/captions updated with protocol-scoped interpretation notes.

### C7. Reproducibility (code/data availability; hyperparameters)

**Comment.** [Paste the reviewer comment.]

**Response.** We added a dedicated resources paragraph describing the planned anonymized release of code, scripts, prompts, and split specifications, and we specified the TRR layer choice for Wav2Vec2.

**Changes in manuscript.**
- Experimental Setup: added ``Resources and reproducibility'' paragraph (with a placeholder link).
- TRR/Experiments: specified $\ell=10$ for Wav2Vec2 layer selection.

