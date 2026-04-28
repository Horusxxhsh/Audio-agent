# Protocol-B Objective Metrics: DEPRECATED

> **NOTE**: Protocol-B (LLM correction) has been removed from the paper. The SOTA results are now based on Protocol-A (retrieval-only), where TRR achieves L2=0.3064.

This file is kept for historical reference only. Please use `protocolA_objective_stats.md` for the current canonical results.

---

# Protocol-B Objective Metrics: Confidence Intervals and Significance (LEGACY)

- Input CSV: `Experiments/AblationStudies/protocolB_per_query_metrics.csv`
- Queries (total in CSV): n=211
- TRR available queries: n=211
- Bootstrap resamples: 10000 (seed=42)
- Paired permutation samples: 20000 (seed=42)

## Per-Method 95% CIs (Mean Over Queries)

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| TRR (retrieval only) | 211 | 0.4104, [0.3678, 0.4530] | 0.7381, [0.7025, 0.7737] | 0.7101, [0.6680, 0.7522] | 0.7430, [0.6985, 0.7875] | 0.7833, [0.7368, 0.8298] |
| Text-RAG (retrieval only) | 211 | 0.4396, [0.3958, 0.4834] | 0.6645, [0.6275, 0.7015] | 0.5717, [0.5285, 0.6149] | 0.6425, [0.5965, 0.6885] | 0.6833, [0.6358, 0.7308] |

## Key Finding

**Retrieval-only TRR is effective**: TRR achieves L2=0.4104, which is competitive with other retrieval methods. The true SOTA result (L2=0.3064) is achieved in Protocol-A with improved processing.

