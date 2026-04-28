# Protocol-A Objective Metrics: Confidence Intervals and Significance

- Input CSV: `Experiments/AblationStudies/protocolA_audio_grouped_per_query_metrics.csv`
- Queries (total in CSV): n=204
- TRR available queries: n=204
- Pairwise tests use the intersection of `query_idx` between TRR and each baseline.
- Bootstrap resamples: 10000 (seed=42)
- Paired permutation samples: 20000 (seed=42)

## Per-Method 95% CIs (Mean Over Queries)

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| CLAP | 201 | 22.3102, [18.6405, 26.1201] | 0.4492, [0.4167, 0.4821] | 0.3971, [0.3615, 0.4329] | 0.5725, [0.5133, 0.6317] | 0.7240, [0.6884, 0.7591] |
| FeatureNN-RAG | 204 | 19.2613, [15.9103, 22.7101] | 0.4198, [0.3896, 0.4514] | 0.3600, [0.3269, 0.3948] | 0.5479, [0.4869, 0.6089] | 0.7134, [0.6773, 0.7497] |
| TRR | 204 | 8.0467, [5.7805, 10.4727] | 0.5169, [0.4860, 0.5495] | 0.4595, [0.4232, 0.4979] | 0.8247, [0.7820, 0.8646] | 0.8051, [0.7681, 0.8419] |
| Text-RAG | 204 | 24.1705, [20.2018, 28.1073] | 0.4717, [0.4371, 0.5073] | 0.3967, [0.3592, 0.4353] | 0.4943, [0.4314, 0.5596] | 0.7456, [0.7108, 0.7809] |
| Wav2Vec-RAG | 204 | 23.8197, [20.1623, 27.5540] | 0.4251, [0.3925, 0.4596] | 0.3505, [0.3130, 0.3893] | 0.5292, [0.4663, 0.5902] | 0.7043, [0.6668, 0.7411] |

## TRR vs Baselines (Signed Improvements)

Signed improvement is defined as:
- For `l2`: `baseline - TRR` (positive means TRR reduces error).
- For other metrics: `TRR - baseline` (positive means TRR increases the score).

| Baseline | Metric | n | Mean Δ | 95% CI | p (perm, 2-sided) | p (Holm) |
| --- | --- | --- | --- | --- | --- | --- |
| CLAP | l2 | 201 | 14.1460 | [10.3041, 18.0624] | 5e-05 | 0.001 |
| CLAP | acc@0.1 | 201 | 0.0640 | [0.0257, 0.1020] | 0.0014 | 0.007 |
| CLAP | recall | 201 | 0.0600 | [0.0189, 0.1007] | 0.00605 | 0.0181 |
| CLAP | cosine | 201 | 0.2503 | [0.1833, 0.3183] | 5e-05 | 0.001 |
| CLAP | module | 201 | 0.0781 | [0.0361, 0.1200] | 0.00025 | 0.0015 |
| FeatureNN-RAG | l2 | 204 | 11.2146 | [7.6011, 14.8710] | 5e-05 | 0.001 |
| FeatureNN-RAG | acc@0.1 | 204 | 0.0971 | [0.0601, 0.1343] | 5e-05 | 0.001 |
| FeatureNN-RAG | recall | 204 | 0.0995 | [0.0572, 0.1423] | 5e-05 | 0.001 |
| FeatureNN-RAG | cosine | 204 | 0.2769 | [0.2087, 0.3435] | 5e-05 | 0.001 |
| FeatureNN-RAG | module | 204 | 0.0917 | [0.0469, 0.1353] | 0.00015 | 0.00105 |
| Text-RAG | l2 | 204 | 16.1238 | [12.3722, 19.8789] | 5e-05 | 0.001 |
| Text-RAG | acc@0.1 | 204 | 0.0453 | [0.0084, 0.0818] | 0.0177 | 0.0227 |
| Text-RAG | recall | 204 | 0.0628 | [0.0224, 0.1032] | 0.0035 | 0.014 |
| Text-RAG | cosine | 204 | 0.3304 | [0.2588, 0.4014] | 5e-05 | 0.001 |
| Text-RAG | module | 204 | 0.0595 | [0.0135, 0.1050] | 0.0113 | 0.0227 |
| Wav2Vec-RAG | l2 | 204 | 15.7730 | [12.2807, 19.3414] | 5e-05 | 0.001 |
| Wav2Vec-RAG | acc@0.1 | 204 | 0.0918 | [0.0582, 0.1259] | 5e-05 | 0.001 |
| Wav2Vec-RAG | recall | 204 | 0.1091 | [0.0664, 0.1528] | 5e-05 | 0.001 |
| Wav2Vec-RAG | cosine | 204 | 0.2956 | [0.2305, 0.3630] | 5e-05 | 0.001 |
| Wav2Vec-RAG | module | 204 | 0.1008 | [0.0576, 0.1440] | 5e-05 | 0.001 |
