# Protocol-A Objective Metrics: Confidence Intervals and Significance

- Input CSV: `Experiments/AblationStudies/protocolA_per_query_metrics.csv`
- Queries: n=211 (paired across methods by `query_idx`)
- Bootstrap resamples: 2000 (seed=42)
- Paired permutation samples: 5000 (seed=42)

## Per-Method 95% CIs (Mean Over Queries)

| Method | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- |
| FeatureNN-RAG | 1.1729, [0.6876, 1.7622] | 0.6765, [0.6448, 0.7068] | 0.6485, [0.6057, 0.6886] | 0.7757, [0.7316, 0.8156] | 0.9602, [0.9373, 0.9793] |
| TRR | 0.3064, [0.2746, 0.3388] | 0.7253, [0.6945, 0.7542] | 0.6990, [0.6630, 0.7350] | 0.8376, [0.8064, 0.8679] | 0.9574, [0.9382, 0.9740] |
| Text-RAG | 0.4573, [0.3734, 0.5596] | 0.7034, [0.6722, 0.7341] | 0.6407, [0.5973, 0.6810] | 0.7404, [0.6969, 0.7808] | 0.8625, [0.8254, 0.8980] |
| Wav2Vec-RAG | 0.3625, [0.3249, 0.4001] | 0.6434, [0.6054, 0.6800] | 0.5748, [0.5245, 0.6188] | 0.7364, [0.6902, 0.7784] | 0.9116, [0.8789, 0.9403] |

## TRR vs Baselines (Signed Improvements)

Signed improvement is defined as:
- For `l2`: `baseline - TRR` (positive means TRR reduces error).
- For other metrics: `TRR - baseline` (positive means TRR increases the score).

| Baseline | Metric | Mean Δ | 95% CI | p (perm, 2-sided) | p (Holm) |
| --- | --- | --- | --- | --- | --- |
| FeatureNN-RAG | l2 | 0.8666 | [0.3738, 1.4565] | 0.0002 | 0.003 |
| FeatureNN-RAG | acc@0.1 | 0.0489 | [0.0315, 0.0682] | 0.0002 | 0.003 |
| FeatureNN-RAG | recall | 0.0505 | [0.0221, 0.0823] | 0.0006 | 0.0042 |
| FeatureNN-RAG | cosine | 0.0620 | [0.0273, 0.0998] | 0.0012 | 0.005 |
| FeatureNN-RAG | module | -0.0028 | [-0.0292, 0.0261] | 0.836 | 0.836 |
| Text-RAG | l2 | 0.1509 | [0.0650, 0.2546] | 0.0006 | 0.0042 |
| Text-RAG | acc@0.1 | 0.0220 | [0.0022, 0.0423] | 0.0344 | 0.0688 |
| Text-RAG | recall | 0.0583 | [0.0254, 0.0924] | 0.001 | 0.005 |
| Text-RAG | cosine | 0.0972 | [0.0603, 0.1369] | 0.0002 | 0.003 |
| Text-RAG | module | 0.0949 | [0.0624, 0.1287] | 0.0002 | 0.003 |
| Wav2Vec-RAG | l2 | 0.0561 | [0.0313, 0.0815] | 0.0002 | 0.003 |
| Wav2Vec-RAG | acc@0.1 | 0.0819 | [0.0561, 0.1080] | 0.0002 | 0.003 |
| Wav2Vec-RAG | recall | 0.1242 | [0.0877, 0.1615] | 0.0002 | 0.003 |
| Wav2Vec-RAG | cosine | 0.1012 | [0.0689, 0.1368] | 0.0002 | 0.003 |
| Wav2Vec-RAG | module | 0.0458 | [0.0104, 0.0826] | 0.011 | 0.033 |
