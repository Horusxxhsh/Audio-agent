# TMM Experiment Plan (Algorithm Track): TRR + Fusion + Constraint Repair

中文版本请见：`Research/tmm_experiment_plan_zh.md`

## 0. Meta
- Target venue: IEEE Transactions on Multimedia (TMM)
- Paper positioning: algorithm-first (representation + fusion + constraint repair), system as application
- Current status: existing results are pilot-scale (e.g., `archive/legacy_reports/2025-01-09_retrieval_comparison_report.md` uses N=5) and must be upgraded to TMM-level evidence

## 1. AE Concerns -> Experiment Requirements (Acceptance Targets)
- R1 Scale: main objective benchmark must be >= 200 test samples, with learning-curve evidence across multiple dataset sizes.
- R2 Perceptual linkage: show how parameter-space metrics relate to perceived audio quality (correlation + failure modes).
- R3 Strong baselines: compare TRR against modern audio embeddings (CLAP/PaSST/AST/HuBERT/Wav2Vec2 pooling, etc.) under a fairness protocol.
- R4 Efficiency: report latency/throughput/memory and show TRR complexity trade-offs (Pareto plot).
- R5 Fusion credibility: rule out leakage/bugs/outliers via per-query analysis + sanity checks + ablations.
- R6 Subjective rigor: avoid mixed-task MUSHRA; provide a pre-defined analysis plan, QC gates, and corrected statistics.
- R7 Reproducibility: one-command runs, fixed splits/seeds, artifact manifests (checksum), and a claim-to-evidence ledger.

## 2. Research Questions (RQs) and Hypotheses (Hs)
- RQ1: Does TRR improve retrieval/parameter inference over strong audio embeddings for effect-preset matching, especially on texture-sensitive cases?
- RQ2: Does uncertainty-aware fusion provide consistent gains over best single-modality methods, beyond a few cherry-picked samples?
- RQ3: Do improvements in parameter-space metrics translate to perceptual improvements (objective audio distances + human ratings)?
- RQ4: What is the latency-cost trade-off of TRR/fusion/repair, and is it compatible with DAW-style workflows?

## 3. Assets We Already Have (Pilot Evidence, To Be Reframed)
- Pilot retrieval report: `archive/legacy_reports/2025-01-09_retrieval_comparison_report.md` (N=5 test samples, KB=51) is only a pilot and should not be used for TMM-level claims.
- Existing scripts: `Experiments/TextureResonance/*`, `Experiments/Fusion/*`, `Experiments/mushura/*`.
- Existing MUSHRA raw: `Experiments/mushura/mushra.csv` contains duplicate header rows; analysis must start from a cleaned dataset and report cleaning rules.
- Existing dataset skeleton: `Data/Audio_Synthetic/` (50 WAV; some `.trr.npy` cache exists).

## 4. Data Plan

### 4.1 Dataset Schema (per sample)
- `dry.wav`: dry input (fixed for evaluation; optionally multiple dry inputs for robustness)
- `target.wav`: processed reference audio for the preset
- `style_text.txt`: textual style description (if available)
- `params.json`: ground-truth parameter vector + module ON/OFF
- `meta.json`: tags (instrument/effect family/style), source, license, unique IDs

### 4.2 Dataset Size Tiers (for learning curves)
- Tier S (pilot): N=50 (existing)
- Tier M (TMM-min): N>=200
- Tier L (TMM-strong): N>=500 (if data/rights allow)

### 4.3 Splits and Leakage Control (must)
- Publish split files: `splits/{tier}/{seed}/train.txt`, `val.txt`, `test.txt`.
- Split principle: source/artist/preset-group based splitting (avoid near-duplicates across train/test).
- Leakage scan: hash-based exact duplicate removal + near-duplicate audio scan (embedding cosine threshold) before splitting.
- Report distribution table: instrument/effect/style coverage per split.

### 4.4 Versioning and Licensing (reproducibility baseline)
- Create `dataset_manifest.csv` with SHA256 per file, plus `license`/`source` fields.
- Any non-redistributable content must be excluded from public release; still keep manifest for internal reproduction.

## 5. Evaluation Tracks (separate what each module contributes)

### 5.1 Track A: Retrieval-only (Representation Quality)
Goal: evaluate embeddings/fusion without LLM/repair confounds.
- Inputs: text-only, audio-only, text+audio.
- Output: retrieved neighbor(s) and copied parameter vector (no post-processing).
- Primary metrics: retrieval quality (R@k / mAP if labels exist), plus parameter metrics on copied parameters.
- Artifacts: `tables/trackA_main.csv`, per-query logs, and failure-case list.

### 5.2 Track B: End-to-end (Agent Output)
Goal: evaluate full pipeline with controlled variants.
- Variants: no-LLM vs LLM-on; no-repair vs repair-on; fusion strategies.
- Metrics: parameter metrics + audio metrics (objective) + subjective ratings (separate study).
- Artifacts: rendered audio folders, metrics tables, and per-sample diffs.

## 6. Methods and Baselines (Fairness Protocol Required)

### 6.1 Our Methods (ablation-ready)
- TRR: Gram-based second-order statistics on learned features.
- Fusion: uncertainty-aware weighting or gating (must include fixed-weight and random-weight controls).
- Constraint repair: hard projection / post-hoc repair (must include "no repair" baseline).

### 6.2 Strong Baselines (audio embeddings)
Minimum set (for Track A and B, where applicable):
- CLAP embedding retrieval
- AST (Audio Spectrogram Transformer) embedding retrieval
- PaSST embedding retrieval
- HuBERT pooling baseline (mean pooling + optional PCA)
- Wav2Vec2 pooling baseline (layer sweep or selected layers)
- PANNs/VGGish-style embeddings (if feasible)
Keep existing weak baselines as historical but not central:
- MFCC temporal
- Modulation spectrogram

### 6.3 Text baselines
- BM25 / keyword overlap (current "RAGRetriever" style) as a lower baseline
- Sentence embedding retrieval (e.g., SBERT-style) if feasible

### 6.4 Fusion baselines
- Fixed weights: 0.0/0.5/1.0
- Temperature sweep / beta sweep (pre-registered ranges)
- Learned gating baseline (simple linear/logistic gate trained on train split only)

## 7. Metrics Plan

### 7.1 Parameter-space metrics (keep, but downgrade as proxies)
- L2 distance (normalized) on full parameter vector
- Acc@0.1
- Recall (active-parameter)
- Cosine similarity
- Module consistency (Jaccard over activated modules)
- Constraint violation rate (must define constraints and measure before/after repair)

### 7.2 Audio-space objective metrics (required for TMM)
Computed on rendered audio from predicted parameters:
- FAD (choose one reference implementation and lock it; report configuration)
- Additional spectral distances: multi-resolution STFT distance / log-spectral distance (as supportive, not primary)
- Loudness/level controls: integrated LUFS and true peak (to ensure fairness)

### 7.3 Correlation / predictability analysis (parameter -> perceptual)
Goal: quantify the link and its limits.
- Spearman correlation between parameter metrics and (FAD, subjective scores).
- Mixed-effects regression: subjective score ~ metric + (1|listener) + (1|excerpt).
- Leave-one-excerpt-out validation to test generalization of correlations.

### 7.4 Identifiability stress test (parameter non-uniqueness)
Goal: directly demonstrate when parameter distance is not perceptual distance.
- For a subset of presets, create multiple parameter variants (e.g., random small changes within module constraints, or alternative parameter sets from different retrieval neighbors).
- Render audio for each variant and measure audio-space distances and subjective confusion where feasible.
- Output: a "many-to-one" analysis table and a short failure taxonomy (cases where audio is similar but parameters differ).

## 8. Subjective Evaluation Plan (MUSHRA + ABX, separated)

### 8.1 Task separation (hard rule)
- Study S1 (MUSHRA): audio quality / target similarity for a single well-defined endpoint.
- Study S2 (ABX): discriminability between systems (optional, if needed).
Do not mix "style matching", "solo comparison", "similarity to reference" in one combined analysis.

### 8.2 MUSHRA design (S1)
- Each page: Reference + Hidden reference + 1-2 anchors + <= 6 systems (use BIBD if more systems).
- Excerpt length: 6-12s, aligned and loudness-matched across systems.
- QC gates: hidden reference median >= 90; anchor median <= 30; exclude participants failing gates (pre-registered).
- Target N: 24-32 valid listeners (adjust after a small pilot).

### 8.3 ABX design (S2, optional)
- Binary forced choice, X balanced 50/50, include catch trials.
- Plan by total valid trials per comparison (e.g., >= 200) instead of raw participant count only.

### 8.4 Subjective analysis plan (pre-registered)
- Primary endpoint: delta between our best method and the strongest baseline; define SMID (e.g., 5 or 10 points).
- Model: LMM score ~ system + (1|listener) + (1|excerpt).
- Multiple comparisons: Holm for primary family; BH-FDR for exploratory.
- Report: effect sizes + 95% CI, not only p-values.

## 9. Experiment List (Actionable, With Deliverables)

### E0: Data + split + leakage audit
- Output: `tables/dataset_stats.csv`, split files, `tables/leakage_scan.csv`.
- Accept: test split >= 200 (Tier M), 0 exact duplicates across splits, near-duplicate scan documented.

### E1: Learning curve (scale vs performance)
- Output: `Figure-LearningCurve` + `tables/learning_curve.csv` for Tier S/M/(L).
- Accept: monotonic or explainable trend; no "small tier beats large tier" without documented cause.

### E2: Strong embedding baseline comparison (Track A)
- Output: `Table-TrackA_Main` with mean±CI (bootstrap over excerpts).
- Accept: at least 5 strong baselines included; all configs and versions logged.

### E3: TRR necessity ablation
- Output: `Table-A_TRR` (TRR on/off + design knobs) + `Figure-TRRDepth`.
- Accept: TRR gains replicate across >=2 splits/seeds; report latency deltas.

### E4: Fusion credibility + ablation + sanity
- Output: per-query improvement distribution (`Figure-DeltaCDF`), `Table-Sanity`.
- Accept: shuffle/static/noise tests drop to chance; no single outlier dominates mean gains (report median and trimmed mean).

### E5: Constraint repair ablation
- Output: `Table-A_Repair` (violation rate before/after + performance impact).
- Accept: violation rate reduced by >=10x and meets a pre-set threshold; any performance drop quantified.

### E6: Efficiency/latency benchmark
- Output: `Table-Efficiency` + `Figure-LatencyCDF` (p50/p95) + raw logs.
- Accept: one script reproduces all numbers; report device + batch + audio length; provide Pareto plot.

### E7: Parameter metrics vs perceptual quality linkage
- Output: `Table-Corr` (correlation + CI) + `Figure-Scatter` + error cases list.
- Accept: report both where correlation holds and where it breaks; do not over-claim equivalence.

### E8: Subjective study (MUSHRA, S1)
- Output: `Table-Subjective` (EMM + CI + effect size) + QC summary + anonymized ratings (where allowed).
- Accept: analysis plan frozen before running; QC and exclusion rules applied as written; corrected statistics reported.

### E9: Identifiability and invariance stress tests
- Output: `Table-Identifiability` (param-distance vs audio-distance vs subjective confusion), plus a small curated audio set for supplementary.
- Accept: report both positive and negative evidence; explicitly delimit what parameter metrics can and cannot support.

## 10. Reproducibility and Artifacts (Path A: manifest-based minimum)
- One-command entrypoints: `scripts/run_experiment.py --exp E2 --tier M --seed 0` (or equivalent)
- Every run writes to: `runs/{exp_id}/{timestamp}/` with:
  - `config.yaml`, `command.txt`, `git_rev.txt`, `env_pip_freeze.txt`, `hardware.json`
  - raw outputs (CSVs, figures, audio paths), plus `checksums.sha256`
- Dataset manifest: `dataset_manifest.csv` (sha256 + source + license)
- Claim-to-evidence ledger: `Research/evidence_ledger.md` updated per result

## 11. Timeline (suggested)
- Week 1: E0 + E1 + Track A baselines (E2) + latency harness (E6 scaffold)
- Week 2: TRR/fusion/repair ablations (E3/E4/E5) + sanity (E4)
- Week 3: Audio-space metrics + correlation (E7) + subjective pilot
- Week 4: Full subjective (E8) + paper rewrite and supplementary packaging

## 12. Go/No-Go Criteria for TMM Submission
- Objective: Tier M test >= 200 with >=2 splits/seeds; main table reports CI + effect sizes.
- Baselines: includes >=5 strong audio embeddings; no "weak-baseline-only" comparisons.
- Perceptual: includes at least one audio-space metric + one subjective study with pre-defined analysis plan.
- Efficiency: includes latency CDF and Pareto trade-offs.
- Sanity: includes shuffle/noise/leakage scans with documented outcomes.
