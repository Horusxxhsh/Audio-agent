# Protocol-A Objective Metrics: Confidence Intervals and Significance

- Input CSV: `/Users/xyh/Code/Audio-agent/Experiments/AblationStudies/protocolA_per_query_metrics_with_strong_baselines.csv`
- Queries (total in CSV): n=211
- TRR available queries: n=211
- Pairwise tests use the intersection of `query_idx` between TRR and each baseline.
- Bootstrap resamples: 10000 (seed=42)
- Paired permutation samples: 20000 (seed=42)

## Per-Method 95% CIs (Mean Over Queries)

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| CLAP | 211 | 11.6489, [8.4105, 15.1112] | 0.5839, [0.5465, 0.6211] | 0.4844, [0.4381, 0.5313] | 0.5933, [0.5376, 0.6487] | 0.8009, [0.7594, 0.8406] |
| FeatureNN-RAG | 211 | 1.1729, [0.6856, 1.7586] | 0.6765, [0.6456, 0.7072] | 0.6485, [0.6064, 0.6890] | 0.7757, [0.7311, 0.8172] | 0.9602, [0.9385, 0.9795] |
| TRR | 211 | 0.3064, [0.2739, 0.3388] | 0.7253, [0.6953, 0.7542] | 0.6990, [0.6622, 0.7350] | 0.8376, [0.8068, 0.8683] | 0.9574, [0.9391, 0.9740] |
| Text-RAG | 211 | 0.4573, [0.3719, 0.5579] | 0.7034, [0.6717, 0.7342] | 0.6407, [0.5967, 0.6825] | 0.7404, [0.6960, 0.7827] | 0.8625, [0.8256, 0.8979] |
| Wav2Vec-RAG | 211 | 0.3625, [0.3258, 0.3992] | 0.6434, [0.6069, 0.6798] | 0.5748, [0.5271, 0.6214] | 0.7364, [0.6905, 0.7800] | 0.9116, [0.8806, 0.9403] |

## TRR vs Baselines (Signed Improvements)

Signed improvement is defined as:
- For `l2`: `baseline - TRR` (positive means TRR reduces error).
- For other metrics: `TRR - baseline` (positive means TRR increases the score).

| Baseline | Metric | n | Mean Δ | 95% CI | p (perm, 2-sided) | p (Holm) |
| --- | --- | --- | --- | --- | --- | --- |
| CLAP | l2 | 211 | 11.3426 | [8.1041, 14.8009] | 5e-05 | 0.001 |
| CLAP | acc@0.1 | 211 | 0.1415 | [0.1126, 0.1702] | 5e-05 | 0.001 |
| CLAP | recall | 211 | 0.2145 | [0.1710, 0.2574] | 5e-05 | 0.001 |
| CLAP | cosine | 211 | 0.2443 | [0.1947, 0.2947] | 5e-05 | 0.001 |
| CLAP | module | 211 | 0.1565 | [0.1219, 0.1921] | 5e-05 | 0.001 |
| FeatureNN-RAG | l2 | 211 | 0.8666 | [0.3759, 1.4615] | 5e-05 | 0.001 |
| FeatureNN-RAG | acc@0.1 | 211 | 0.0489 | [0.0314, 0.0679] | 5e-05 | 0.001 |
| FeatureNN-RAG | recall | 211 | 0.0505 | [0.0224, 0.0810] | 0.0004 | 0.00245 |
| FeatureNN-RAG | cosine | 211 | 0.0620 | [0.0278, 0.0993] | 0.00055 | 0.00275 |
| FeatureNN-RAG | module | 211 | -0.0028 | [-0.0296, 0.0249] | 0.839 | 0.839 |
| Text-RAG | l2 | 211 | 0.1509 | [0.0658, 0.2527] | 0.00035 | 0.00245 |
| Text-RAG | acc@0.1 | 211 | 0.0220 | [0.0023, 0.0422] | 0.0347 | 0.0695 |
| Text-RAG | recall | 211 | 0.0583 | [0.0259, 0.0925] | 0.00085 | 0.0034 |
| Text-RAG | cosine | 211 | 0.0972 | [0.0610, 0.1361] | 5e-05 | 0.001 |
| Text-RAG | module | 211 | 0.0949 | [0.0633, 0.1290] | 5e-05 | 0.001 |
| Wav2Vec-RAG | l2 | 211 | 0.0561 | [0.0318, 0.0812] | 5e-05 | 0.001 |
| Wav2Vec-RAG | acc@0.1 | 211 | 0.0819 | [0.0563, 0.1082] | 5e-05 | 0.001 |
| Wav2Vec-RAG | recall | 211 | 0.1242 | [0.0884, 0.1613] | 5e-05 | 0.001 |
| Wav2Vec-RAG | cosine | 211 | 0.1012 | [0.0691, 0.1356] | 5e-05 | 0.001 |
| Wav2Vec-RAG | module | 211 | 0.0458 | [0.0118, 0.0815] | 0.0107 | 0.0322 |
