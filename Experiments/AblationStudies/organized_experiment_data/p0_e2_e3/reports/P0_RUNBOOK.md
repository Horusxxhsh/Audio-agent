# P0 Experiment Runbook

This runbook implements the two mandatory P0 experiments from `Supplementary_Experiments_Report(1).pdf`.

## 1) E2: SOTA Baseline Benchmark (Protocol-A)

Script: `Experiments/AblationStudies/p0_e2_sota_benchmark.py`

Run:

```bash
python Experiments/AblationStudies/p0_e2_sota_benchmark.py \
  --dataset Experiments/dataset_full_vectors.json \
  --out-dir Experiments/AblationStudies/outputs/p0_e2 \
  --test-size 204 \
  --seed 42
```

Outputs:

- `e2_per_query.csv`: per-query/per-method metrics
- `e2_summary.csv`: aggregate metrics
- `e2_stats.json`: pairwise stats (TRR vs baselines), Holm correction, Cohen's d, win/tie/loss

Notes:

- If `CLAP/PaSST/PANNs` vectors are not present in dataset `Vectors`, those methods are skipped automatically.
- `Norm.L2` is implemented by parameter-range normalization estimated from dataset values.

## 2) E3: Real Degradation Robustness (Protocol-C)

Script: `Experiments/AblationStudies/p0_e3_protocol_c.py`

Run:

```bash
python Experiments/AblationStudies/p0_e3_protocol_c.py \
  --dataset Experiments/dataset_full_vectors.json \
  --out-dir Experiments/AblationStudies/outputs/p0_e3 \
  --test-size 30 \
  --seed 42 \
  --fixed-alpha 0.50
```

Outputs:

- `e3_per_query.csv`: per-query/per-condition results
- `e3_summary.csv`: aggregate metrics by condition and method
- `e3_adaptive_vs_fixed.csv`: adaptive-minus-fixed deltas
- `e3_meta.json`: experiment configuration

Protocol-C conditions implemented:

- AWGN: SNR 20/10/5 dB
- MP3 compression: 128/64/32 kbps (ffmpeg path preferred; quantization fallback if ffmpeg missing)
- Reverb: RT60 0.3/0.6/1.0 s
- Truncation: keep 50% / 30%

Key requirement satisfied:

- Degradation is applied to **raw audio first**, then TRR is re-encoded from degraded audio.

