# Protocol-C: Robustness + Modality-Conflict (Objective Metrics)

- Protocol: **Protocol-C**
- Per-query CSV: `Experiments/AblationStudies/protocolC_per_query_metrics.csv`
- Dataset: N_total=1267, N_test=211, N_kb=1056
- Test source: `built-in held-out pool (Protocol-A)`
- Fusion beta=2.0 quality_weight=1.0 quality_threshold=0.0 audio_bias=0.5 top_k=5
- Vague text: `warm guitar tone`
- Audio noise_level: 5.0
- Bootstrap: n_boot=10000 (seed=42)
- Paired permutation: n_perm=20000 (seed=42)

## Scenario Summaries (Mean Over Queries, 95% CI)

### standard
- Standard inputs (original text + original audio).
- Weight stats (Fusion): w_text mean=0.4716 std=0.4968 p25/p50/p75=0.0000/0.0000/1.0000 min/max=0.0000/1.0000
- Weight stats (Fusion): w_audio mean=0.5284 std=0.4968 p25/p50/p75=0.0000/1.0000/1.0000 min/max=0.0000/1.0000

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| Text-only | 211 | 1.5148, [0.5929, 2.7216] | 0.7145, [0.6823, 0.7462] | 0.6733, [0.6327, 0.7135] | 0.7851, [0.7444, 0.8254] | 0.9053, [0.8743, 0.9344] |
| TRR-only | 211 | 0.2970, [0.2637, 0.3307] | 0.7330, [0.7018, 0.7627] | 0.7061, [0.6685, 0.7432] | 0.8420, [0.8111, 0.8732] | 0.9574, [0.9391, 0.9740] |
| Fusion | 211 | 0.3056, [0.2722, 0.3390] | 0.7293, [0.6982, 0.7596] | 0.6986, [0.6602, 0.7368] | 0.8226, [0.7880, 0.8563] | 0.9404, [0.9164, 0.9617] |

### vague_text
- Vague text: replace text with `warm guitar tone` (audio unchanged).
- Weight stats (Fusion): w_text mean=0.0000 std=0.0000 p25/p50/p75=0.0000/0.0000/0.0000 min/max=0.0000/0.0000
- Weight stats (Fusion): w_audio mean=1.0000 std=0.0000 p25/p50/p75=1.0000/1.0000/1.0000 min/max=1.0000/1.0000

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| Text-only | 211 | 12.6517, [9.3530, 16.1122] | 0.5959, [0.5689, 0.6233] | 0.3384, [0.2917, 0.3854] | 0.3709, [0.3173, 0.4255] | 0.5066, [0.4610, 0.5525] |
| TRR-only | 211 | 0.2970, [0.2637, 0.3307] | 0.7330, [0.7018, 0.7627] | 0.7061, [0.6685, 0.7432] | 0.8420, [0.8111, 0.8732] | 0.9574, [0.9391, 0.9740] |
| Fusion | 211 | 0.2970, [0.2637, 0.3307] | 0.7330, [0.7018, 0.7627] | 0.7061, [0.6685, 0.7432] | 0.8420, [0.8111, 0.8732] | 0.9574, [0.9391, 0.9740] |

### noisy_audio
- Noisy audio: add embedding-space Gaussian noise (noise_level=5.0).
- Weight stats (Fusion): w_text mean=1.0000 std=0.0000 p25/p50/p75=1.0000/1.0000/1.0000 min/max=1.0000/1.0000
- Weight stats (Fusion): w_audio mean=0.0000 std=0.0000 p25/p50/p75=0.0000/0.0000/0.0000 min/max=0.0000/0.0000

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| Text-only | 211 | 1.5148, [0.5929, 2.7216] | 0.7145, [0.6823, 0.7462] | 0.6733, [0.6327, 0.7135] | 0.7851, [0.7444, 0.8254] | 0.9053, [0.8743, 0.9344] |
| TRR-only | 211 | 33.8549, [29.7971, 37.9178] | 0.3080, [0.2904, 0.3263] | 0.1949, [0.1724, 0.2172] | 0.1783, [0.1391, 0.2189] | 0.4493, [0.4120, 0.4865] |
| Fusion | 211 | 1.5148, [0.5929, 2.7216] | 0.7145, [0.6823, 0.7462] | 0.6733, [0.6327, 0.7135] | 0.7851, [0.7444, 0.8254] | 0.9053, [0.8743, 0.9344] |

### conflict
- Modality conflict: contradictory text (audio unchanged).
- Weight stats (Fusion): w_text mean=0.4123 std=0.4934 p25/p50/p75=0.0000/0.0000/1.0000 min/max=0.0000/1.0000
- Weight stats (Fusion): w_audio mean=0.5877 std=0.4934 p25/p50/p75=0.0000/1.0000/1.0000 min/max=0.0000/1.0000

| Method | n | l2 (mean, 95% CI) | acc@0.1 (mean, 95% CI) | recall (mean, 95% CI) | cosine (mean, 95% CI) | module (mean, 95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| Text-only | 211 | 12.8572, [9.5718, 16.3074] | 0.4623, [0.4455, 0.4793] | 0.3537, [0.3144, 0.3931] | 0.3315, [0.2846, 0.3787] | 0.5192, [0.4865, 0.5514] |
| TRR-only | 211 | 0.2970, [0.2637, 0.3307] | 0.7330, [0.7018, 0.7627] | 0.7061, [0.6685, 0.7432] | 0.8420, [0.8111, 0.8732] | 0.9574, [0.9391, 0.9740] |
| Fusion | 211 | 4.5259, [2.5100, 6.6140] | 0.5741, [0.5443, 0.6038] | 0.4687, [0.4257, 0.5113] | 0.5715, [0.5184, 0.6241] | 0.7309, [0.6895, 0.7719] |

## Paired Tests (Fusion vs Baselines, Holm-Corrected)

| Scenario | Baseline | Metric | n | MeanΔ (signed) | 95% CI | p | p(Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| standard | Text-only | l2 | 211 | 1.2092 | [0.2936, 2.4213] | 0.0009 | 0.0153 |
| standard | Text-only | acc@0.1 | 211 | 0.0148 | [0.0057, 0.0254] | 0.0019 | 0.0304 |
| standard | Text-only | recall | 211 | 0.0254 | [0.0101, 0.0431] | 0.00085 | 0.0153 |
| standard | Text-only | cosine | 211 | 0.0375 | [0.0175, 0.0614] | 0.00015 | 0.003 |
| standard | Text-only | module | 211 | 0.0350 | [0.0167, 0.0564] | 0.0003 | 0.0057 |
| standard | TRR-only | l2 | 211 | -0.0085 | [-0.0176, -0.0012] | 0.06085 | 0.9127 |
| standard | TRR-only | acc@0.1 | 211 | -0.0037 | [-0.0101, 0.0003] | 0.2459 | 1 |
| standard | TRR-only | recall | 211 | -0.0074 | [-0.0190, -0.0007] | 0.1233 | 1 |
| standard | TRR-only | cosine | 211 | -0.0195 | [-0.0384, -0.0036] | 0.06085 | 0.9127 |
| standard | TRR-only | module | 211 | -0.0171 | [-0.0335, -0.0032] | 0.06085 | 0.9127 |
| vague_text | Text-only | l2 | 211 | 12.3546 | [9.0728, 15.8110] | 5e-05 | 0.002 |
| vague_text | Text-only | acc@0.1 | 211 | 0.1371 | [0.0957, 0.1780] | 5e-05 | 0.002 |
| vague_text | Text-only | recall | 211 | 0.3676 | [0.3054, 0.4292] | 5e-05 | 0.002 |
| vague_text | Text-only | cosine | 211 | 0.4712 | [0.4102, 0.5311] | 5e-05 | 0.002 |
| vague_text | Text-only | module | 211 | 0.4508 | [0.4020, 0.4990] | 5e-05 | 0.002 |
| vague_text | TRR-only | l2 | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| vague_text | TRR-only | acc@0.1 | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| vague_text | TRR-only | recall | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| vague_text | TRR-only | cosine | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| vague_text | TRR-only | module | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | Text-only | l2 | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | Text-only | acc@0.1 | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | Text-only | recall | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | Text-only | cosine | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | Text-only | module | 211 | 0.0000 | [0.0000, 0.0000] | 1 | 1 |
| noisy_audio | TRR-only | l2 | 211 | 32.3401 | [27.9508, 36.7472] | 5e-05 | 0.002 |
| noisy_audio | TRR-only | acc@0.1 | 211 | 0.4065 | [0.3694, 0.4446] | 5e-05 | 0.002 |
| noisy_audio | TRR-only | recall | 211 | 0.4783 | [0.4303, 0.5265] | 5e-05 | 0.002 |
| noisy_audio | TRR-only | cosine | 211 | 0.6068 | [0.5477, 0.6641] | 5e-05 | 0.002 |
| noisy_audio | TRR-only | module | 211 | 0.4560 | [0.4078, 0.5037] | 5e-05 | 0.002 |
| conflict | Text-only | l2 | 211 | 8.3313 | [5.6384, 11.2942] | 5e-05 | 0.002 |
| conflict | Text-only | acc@0.1 | 211 | 0.1118 | [0.0836, 0.1417] | 5e-05 | 0.002 |
| conflict | Text-only | recall | 211 | 0.1150 | [0.0755, 0.1559] | 5e-05 | 0.002 |
| conflict | Text-only | cosine | 211 | 0.2400 | [0.1910, 0.2923] | 5e-05 | 0.002 |
| conflict | Text-only | module | 211 | 0.2117 | [0.1762, 0.2483] | 5e-05 | 0.002 |
| conflict | TRR-only | l2 | 211 | -4.2289 | [-6.3159, -2.2150] | 5e-05 | 0.002 |
| conflict | TRR-only | acc@0.1 | 211 | -0.1589 | [-0.1913, -0.1282] | 5e-05 | 0.002 |
| conflict | TRR-only | recall | 211 | -0.2374 | [-0.2863, -0.1908] | 5e-05 | 0.002 |
| conflict | TRR-only | cosine | 211 | -0.2706 | [-0.3244, -0.2199] | 5e-05 | 0.002 |
| conflict | TRR-only | module | 211 | -0.2265 | [-0.2682, -0.1869] | 5e-05 | 0.002 |

## Modality-Conflict Degradation (Fusion: conflict - standard)

- n=211 paired queries

| Metric | MeanΔ | 95% CI (Δ) |
| --- | --- | --- |
| l2 | 4.2204 | [2.2068, 6.3062] |
| acc@0.1 | -0.1552 | [-0.1873, -0.1248] |
| recall | -0.2299 | [-0.2783, -0.1838] |
| cosine | -0.2511 | [-0.3066, -0.1982] |
| module | -0.2095 | [-0.2526, -0.1675] |

## Representative Modality-Conflict Failures (Largest ΔL2 vs Standard Fusion)

1. query_idx=26 name=`Saturated Rhythm` ΔL2=63.0896 (standard=0.6068, conflict=63.6964), w_text=1.000, w_audio=0.000, retrieved=`Dry Funk Rhythm`
   conflict_text: `clean dry jazz guitar tone, low gain, no distortion`
2. query_idx=1091 name=`Saturated Rhythm - Alt Take` ΔL2=63.0896 (standard=0.6068, conflict=63.6964), w_text=1.000, w_audio=0.000, retrieved=`Dry Funk Rhythm`
   conflict_text: `clean dry jazz guitar tone, low gain, no distortion`
3. query_idx=1121 name=`Saturated Rhythm - Studio Mix` ΔL2=63.0896 (standard=0.6068, conflict=63.6964), w_text=1.000, w_audio=0.000, retrieved=`Dry Funk Rhythm`
   conflict_text: `clean dry jazz guitar tone, low gain, no distortion`
