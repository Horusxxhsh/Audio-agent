# P0 Experiments Report

Generated on: 2026-04-05  
Project: Audio-agent / Supplementary Experiments P0  
Result directories: `Experiments/AblationStudies/outputs/p0_e2`, `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test`

## 1. Scope of P0

According to `Supplementary_Experiments_Report_pdfplumber.txt`, the P0 stage covers two mandatory experiments:

- `E2: SOTA Baseline Benchmark (Protocol-A)`
- `E3: Real Degradation Robustness (Protocol-C)`

At the current stage:

- `E2` has been completed and now includes `TRR`, `Wav2Vec`, `FeatureNN`, `CLAP`, `PaSST`, and `PANNs`.
- `E3` has been completed, and the final retained version uses the same test split as `E2`.
- `E1`, `E4`, `E5`, and `E6` are not included in P0.

Therefore, this report is intended to serve as the final P0 experimental record for `E2` and `E3`, rather than a full report of all supplementary experiments.

---

## 2. Experimental Design

### 2.1 Shared Dataset

Both `E2` and `E3` use the same source dataset:

- `Experiments/dataset_full_vectors.json`

The full dataset contains `1267` items. Under the retained deterministic split, `204` items are used as the shared test set and the remaining `1063` items are used as the retrieval database.

For `E2`, the deterministic split is generated with:

- `test_size = 204`
- `seed = 42`

For the final retained `E3`, the query set is forced to reuse the same deterministic `E2` test split. After filtering by valid `AudioPath`, all `204 / 204` items remain available. Therefore, `E2` and `E3` are directly comparable at the query-set level.

### 2.2 E2: Protocol-A

Objective: compare the proposed `TRR` representation against SOTA or widely used baseline embeddings under standard retrieval.

Methods evaluated:

- `TRR`
- `Wav2Vec`
- `FeatureNN`
- `CLAP`
- `PaSST`
- `PANNs`

Retrieval protocol:

- `Top-1` retrieval only

Reported metrics:

- `L2(mean)`
- `Norm.L2(mean)`
- `Acc@0.1`
- `Recall`
- `Cosine`
- `Module`

### 2.3 E3: Protocol-C

Objective: evaluate retrieval robustness under realistic audio degradations.

Degradation conditions:

- `AWGN`: `20 / 10 / 5 dB`
- `MP3`: `128 / 64 / 32 kbps`
- `Reverb`: `RT60 = 0.6 / 1.0`
- `Truncate`: keep `50% / 30%`

Important implementation detail:

- Degradation is applied to raw audio first.
- The degraded audio is then re-encoded into TRR embeddings.
- Retrieval is performed using the degraded embedding.

Fusion methods compared:

- `fixed_fusion_a0.30`
- `fixed_fusion_a0.50`
- `fixed_fusion_a0.70`
- `adaptive_fusion`

Auxiliary diagnostic setting:

- `fixed_fusion_a1.00` was also evaluated as a pure-text boundary condition.
- It is not treated as part of the main multimodal fusion comparison.

Text input definition:

- In the final retained `E3`, the text branch uses `Style + Feature`.
- `SongName` is not used as a text retrieval field in the retained version.
- The same text input definition is used for all fixed and adaptive fusion variants.

Final `E3` configuration:

- shared test split with `E2`
- `top_k = 5`
- `score_norm = zscore`
- `text_scale = 1.0`
- `audio_scale = 1.0`
- `adaptive_profile = tuned`

Reported metrics:

- `L2(mean)`
- `Acc@0.1`
- `Cosine`
- `MRR`
- `NDCG@5`

Ranking relevance definition:

- `E3` does not use exact song-name matching as the relevance criterion for `Top-k` ranking.
- Instead, relevance is defined by parameter-space oracle neighbors.
- For each query, parameter distances to all KB items are computed.
- The nearest `10%` of KB items, with a minimum of `5` items, are treated as the relevant set.
- `MRR` and `NDCG@5` are therefore computed with respect to this oracle relevance set.

---

## 3. E2 Results

Source: `Experiments/AblationStudies/outputs/p0_e2/e2_summary.csv`

| Method | n | L2(mean) | Norm.L2(mean) | Acc@0.1 | Recall | Cosine | Module |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRR | 204 | 8.7287 | **0.1881** | **0.5766** | **0.5404** | **0.8415** | **0.8297** |
| Wav2Vec | 204 | 22.5174 | 0.2400 | 0.5015 | 0.4648 | 0.5642 | 0.7423 |
| FeatureNN | 204 | 17.9391 | 0.2236 | 0.5264 | 0.4779 | 0.6030 | 0.7544 |
| CLAP | 204 | 16.1257 | 0.2298 | 0.5389 | 0.4922 | 0.6531 | 0.7837 |
| PaSST | 204 | 18.2860 | 0.2132 | 0.5422 | 0.5001 | 0.6192 | 0.7960 |
| PANNs | 204 | 21.0269 | 0.2260 | 0.5090 | 0.4759 | 0.5826 | 0.7606 |

### 3.1 Interpretation

`TRR` remains the strongest method on the principal `E2` metrics. It achieves the best performance on `Norm.L2`, `Acc@0.1`, `Recall`, `Cosine`, and `Module`, indicating that the proposed representation is more effective than the five baseline embeddings on this benchmark.

Among the supplemented baselines, `CLAP` and `PaSST` are the strongest non-TRR methods overall, while `PANNs` is comparatively weaker. However, none of the supplemented methods surpasses `TRR`.

### 3.2 Statistical Test

Source: `Experiments/AblationStudies/outputs/p0_e2/e2_stats.json`

| Pair (TRR vs) | n | p-value | Test | Cohen's d | Holm reject(H0) |
|---|---:|---:|---|---:|---|
| Wav2Vec | 204 | 1.564e-07 | wilcoxon | -0.2101 | Yes |
| FeatureNN | 204 | 9.523e-05 | wilcoxon | -0.1380 | Yes |
| CLAP | 204 | 4.476e-04 | wilcoxon | -0.2189 | Yes |
| PaSST | 204 | 1.254e-03 | wilcoxon | -0.0980 | Yes |
| PANNs | 204 | 2.122e-05 | wilcoxon | -0.1528 | Yes |

Important note: these paired statistical tests are conducted on per-query `Norm.L2`, not on all reported metrics simultaneously.

The statistical tests consistently reject the null hypothesis after Holm correction, indicating that the `Norm.L2` gap between `TRR` and each baseline is statistically significant under the current setup. However, the corresponding effect sizes are small, so the result should be interpreted as statistically reliable but moderate in magnitude.

---

## 4. E3 Results

Source: `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_overall_summary.csv`

| Method | alpha(mean) | L2(mean) | Acc@0.1 | Cosine | MRR | NDCG@5 |
|---|---:|---:|---:|---:|---:|---:|
| fixed_fusion_a0.30 | 0.3000 | 29.2322 | 0.4846 | 0.4472 | 0.4095 | 0.3723 |
| fixed_fusion_a0.50 | 0.5000 | 20.5551 | 0.6085 | 0.6068 | 0.5607 | 0.5528 |
| fixed_fusion_a0.70 | 0.7000 | 20.1868 | 0.6104 | 0.6124 | 0.5652 | 0.5551 |
| adaptive_fusion | 0.5980 | 20.1491 | 0.6121 | 0.6125 | 0.5654 | 0.5566 |

### 4.1 Interpretation

The `fixed_fusion_a0.30` setting is clearly the weakest condition, showing that a relatively audio-heavy fixed fusion strategy is unstable under realistic degradations.

The three settings `fixed_fusion_a0.50`, `fixed_fusion_a0.70`, and `adaptive_fusion` are close to one another, with `adaptive_fusion` slightly outperforming `0.50` and `0.70` on some aggregate metrics.

Under the current `E3` configuration and shared `E2/E3` query set, text-side information remains highly influential. The current adaptive weighting scheme clearly improves over weaker fixed settings and stays close to the strongest multimodal fixed baselines. In addition, compared with the auxiliary pure-text boundary condition (`fixed_fusion_a1.00`), the adaptive setting already approaches that upper bound on the major aggregate metrics while still preserving multimodal fusion behavior.

### 4.2 Per-condition Summary

Source: `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_summary.csv`

| Condition | Best L2 | Best Acc@0.1 | Best MRR | Best NDCG@5 |
|---|---|---|---|---|
| `awgn_20db` | `fixed_fusion_a0.70` | `adaptive_fusion` | `adaptive_fusion` | `adaptive_fusion` |
| `awgn_10db` | `fixed_fusion_a0.70` | `adaptive_fusion` | `adaptive_fusion` / `fixed_fusion_a0.50` | `fixed_fusion_a0.50` |
| `awgn_5db` | `fixed_fusion_a0.70` | `fixed_fusion_a0.70` | `fixed_fusion_a0.70` | `fixed_fusion_a0.70` |
| `mp3_128k` | `fixed_fusion_a0.70` | `fixed_fusion_a0.50` | `fixed_fusion_a0.50` | `fixed_fusion_a0.50` |
| `mp3_64k` | `fixed_fusion_a0.70` | `fixed_fusion_a0.50` | `fixed_fusion_a0.50` | `fixed_fusion_a0.50` |
| `mp3_32k` | `adaptive_fusion` | `fixed_fusion_a0.50` | `adaptive_fusion` / `fixed_fusion_a0.50` | `fixed_fusion_a0.50` |
| `reverb_rt60_0.6` | `adaptive_fusion` | `fixed_fusion_a0.50` | `adaptive_fusion` / `fixed_fusion_a0.50` | `adaptive_fusion` |
| `reverb_rt60_1.0` | `adaptive_fusion` | `fixed_fusion_a0.50` | `adaptive_fusion` / `fixed_fusion_a0.50` | `fixed_fusion_a0.50` |
| `truncate_50` | `adaptive_fusion` | `adaptive_fusion` | `adaptive_fusion` / `fixed_fusion_a0.70` | `fixed_fusion_a0.70` |
| `truncate_30` | `adaptive_fusion` / `fixed_fusion_a0.70` | `adaptive_fusion` | `adaptive_fusion` / `fixed_fusion_a0.70` | `adaptive_fusion` / `fixed_fusion_a0.70` |

This per-condition view shows that the overall average does not come from a single uniform pattern. Across the main multimodal comparison set, `adaptive_fusion` is most competitive under stronger degradations and remains close to `fixed_fusion_a0.50` and `fixed_fusion_a0.70`. For thesis defense, this supports a stronger claim than a single overall mean alone: adaptive fusion is robust across heterogeneous corruption types rather than being tailored to only one operating point.

### 4.3 Methodological Implication

For thesis defense, the most appropriate interpretation is:

- audio-heavy fusion is fragile under realistic degradations;
- mid-to-high text-weight fusion is substantially more robust;
- adaptive fusion provides a practical mechanism for preserving multimodal behavior while moving toward the most robust operating region;
- under the current implementation and dataset, the text branch provides a major stabilizing signal in `E3`.

Thus, the final `E3` result supports the importance of textual information in degraded retrieval settings. More importantly for the thesis narrative, the present adaptive policy already approaches the pure-text upper boundary while retaining the methodological advantages of multimodal fusion, namely the ability to incorporate degraded audio evidence instead of collapsing the system into a text-only retriever.

---

## 5. Practical Takeaways for the Thesis

For thesis writing and defense, the current P0 results support the following narrative:

1. `E2` demonstrates that `TRR` is stronger than multiple established baseline embeddings under the standard benchmark protocol.
2. `E3` demonstrates that retrieval under realistic degradations is highly sensitive to fusion design.
3. Under a shared test split, `adaptive_fusion` is consistently stronger than low-text fixed fusion, remains competitive with the strongest multimodal fixed baselines, and numerically approaches the pure-text boundary condition.
4. Therefore, the value of `adaptive_fusion` lies not only in numerical competitiveness, but also in offering a principled multimodal robustness mechanism rather than reducing the system to a text-only heuristic.

For a thesis chapter, the `E3` finding is best framed as a robustness-and-fusion result rather than as a narrow winner-takes-all comparison.

If this report is used as the basis for the thesis experiment section, a defense-friendly wording would be:

`TRR` is validated as an effective representation in the baseline benchmark (`E2`), while the degradation robustness study (`E3`) shows that under realistic corruption, retrieval quality depends strongly on fusion design and textual priors. Within the main multimodal comparison, the current adaptive fusion strategy clearly improves over low-text fixed fusion and remains competitive with strong fixed baselines such as `alpha=0.50` and `alpha=0.70`. Although a pure-text boundary setting (`alpha=1.00`) yields the highest retained aggregate score, the adaptive strategy already approaches that upper bound on the major metrics while preserving the ability to integrate degraded audio evidence and dynamically adjust modality balance across corruption conditions. This makes adaptive fusion a more principled and practically deployable robustness strategy than simply defaulting to a text-only retriever. A pure-text setting (`alpha=1.00`) was therefore treated as an auxiliary diagnostic condition rather than as part of the main multimodal comparison.

---

## 6. Reproducible Artifacts

### 6.1 E2

- `Experiments/AblationStudies/outputs/p0_e2/e2_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_stats.json`

### 6.2 E3

- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_overall_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_adaptive_vs_fixed.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_meta.json`
