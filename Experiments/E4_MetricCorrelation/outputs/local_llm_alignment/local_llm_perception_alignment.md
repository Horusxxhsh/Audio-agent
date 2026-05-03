# Local LLM Perception Alignment Diagnostic

Trial-1 style-label diagnostic with explicit alias matching; not a primary query-level validation.

- Local model: `qwen3.5-9b` at `http://127.0.0.1:8000`
- Stimuli: 7
- Stimuli with Protocol-A TRR matches: 4

## Correlations

| Pair | n | Spearman r | Spearman p | Pearson r | Pearson p |
| --- | ---: | ---: | ---: | ---: | ---: |
| human_vs_trr_l2 | 4 | 0.4000 | 0.6 | -0.4033 | 0.5967 |
| human_vs_trr_acc | 4 | 0.0000 | 1 | -0.0686 | 0.9314 |
| human_vs_trr_cosine | 4 | 0.0000 | 1 | -0.1905 | 0.8095 |
| human_vs_llm_score | 7 | -0.1793 | 0.7005 | -0.2006 | 0.6662 |
| llm_vs_trr_l2 | 4 | 0.7746 | 0.2254 | 0.3423 | 0.6577 |
| llm_vs_trr_acc | 4 | 0.2582 | 0.7418 | 0.0717 | 0.9283 |

## Per-Stimulus Rows

| stimulus       |   human_mean |   human_median |   human_std |   human_n |   matched_queries |   matched_rows |   trr_l2_mean |   trr_acc_mean |   trr_recall_mean |   trr_cosine_mean |   trr_module_mean |   llm_score |
|:---------------|-------------:|---------------:|------------:|----------:|------------------:|---------------:|--------------:|---------------:|------------------:|------------------:|------------------:|------------:|
| Ambient Guitar |      72.3462 |           73.5 |     18.4476 |        26 |                 1 |              1 |       1.86358 |       0.884615 |          0.869565 |         0.999999  |          1        |          90 |
| Blues Solo     |      72.9615 |           69.5 |     21.1934 |        26 |                 0 |              0 |     nan       |     nan        |        nan        |       nan         |        nan        |          90 |
| Chorus         |      64.9231 |           66.5 |     23.1152 |        26 |                 0 |              0 |     nan       |     nan        |        nan        |       nan         |        nan        |          95 |
| Flanger        |      69.1154 |           74   |     23.0796 |        26 |                 0 |              0 |     nan       |     nan        |        nan        |       nan         |        nan        |          98 |
| Jazz Clean     |      76.1923 |           81   |     20.7962 |        26 |                25 |             25 |       1.63415 |       0.618333 |          0.628594 |         0.892141  |          0.983333 |          95 |
| Modern Metal   |      65.5769 |           70   |     30.2181 |        26 |                10 |             10 |       2.56638 |       0.52893  |          0.446335 |         0.695713  |          0.700794 |          90 |
| Phase          |      75.3846 |           80.5 |     20.8788 |        26 |                 1 |              1 |      59.1761  |       0.344828 |          0.269231 |         0.0672504 |          0.333333 |          90 |