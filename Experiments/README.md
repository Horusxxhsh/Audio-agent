# TMM Revision Experiments

This directory contains the supplementary experiments for the IEEE TMM major revision.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# 3. Run experiments
python E1_AEM/memory_learning_curve.py
python E6_Latency/latency_profiler.py
```

## Experiments Overview

| Experiment | Purpose | Runtime | Priority |
|------------|---------|---------|----------|
| **E1** | AEM Learning Curve | 2-4 hours | P0 |
| **E2** | SOTA Baselines (CLAP/PaSST/PANNs) | 8-12 hours | P0 |
| **E3** | Real Noise Protocol-C | 4-6 hours | P0 |
| **E4** | Metric-Perception Correlation | < 1 hour | P1 |
| **E5** | Retrieval Ablation | 2-3 hours | P1 |
| **E6** | Latency Profiling | 1-2 hours | P2 |

## Detailed Instructions

### E1: AEM Learning Curve

**Purpose**: Validate that memory improves performance over interactions.

**Run**:
```bash
cd E1_AEM
python memory_learning_curve.py
```

**Output**:
- `results/aem_results_memory_size_*.csv` - Raw results per condition
- `results/aem_analysis.json` - Statistical analysis
- `results/aem_learning_curves.png` - Visualization

**Expected Results**:
- Memory size=0 (baseline) should have flat learning curve
- Memory sizes > 0 should show decreasing error over turns
- 50 memory entries should reduce L2 error by 20-30%

---

### E6: Latency Profiling

**Purpose**: Measure end-to-end pipeline latency.

**Run**:
```bash
cd E6_Latency
python latency_profiler.py
```

**Output**:
- `results/latency_results.csv` - Raw timing data
- `results/latency_analysis.png` - Visualizations

**Expected Results**:
- Wav2Vec2 encoding: ~50-100ms
- Gram matrix: < 1ms
- KNN retrieval: < 5ms
- LLM generation: ~100-500ms (API dependent)

---

### E3: Protocol-C with Real Noise

**Purpose**: Test robustness under realistic audio degradations.

**Prerequisites**:
```bash
pip install soundfile scipy pydub
brew install ffmpeg  # macOS
# apt-get install ffmpeg  # Linux
```

**Run**:
```bash
cd E3_ProtocolC
python protocol_c_experiment.py
```

**Degradations Tested**:
- AWGN: SNR 20dB, 10dB, 5dB
- MP3: 128k, 64k, 32k bitrate
- Reverberation: small (RT60=0.3s), medium (0.6s), large (1.0s)
- Truncation: 50%, 30% of audio

---

### E4: Metric-Perception Correlation

**Purpose**: Correlate parameter-space metrics with listening test scores.

**Prerequisites**: MUSHRA listening test raw data.

**Run**:
```bash
cd E4_MetricCorrelation
python correlation_analysis.py --mushra-data path/to/mushra_raw.csv
```

---

### E5: Retrieval Ablation

**Purpose**: Compare retrieval-only vs retrieval+projection vs +constraint repair.

**Run**:
```bash
cd E5_Ablations
python retrieval_ablation.py
```

---

### E2: SOTA Baselines

**Purpose**: Compare TRR against CLAP, PaSST, PANNs.

**⚠️ Warning**: This is the most complex experiment. See E2_SOTABaselines/README.md

## Results Directory Structure

```
results/
├── E1_AEM/
│   ├── aem_results_memory_size_*.csv
│   ├── aem_analysis.json
│   └── aem_learning_curves.png
├── E2_SOTABaselines/
│   └── ...
├── E3_ProtocolC/
│   └── ...
├── E4_MetricCorrelation/
│   └── ...
├── E5_Ablations/
│   └── ...
└── E6_Latency/
    ├── latency_results.csv
    └── latency_analysis.png
```

## Troubleshooting

### API Rate Limiting
If you hit rate limits:
- Add `time.sleep(0.5)` between calls
- Reduce `n_queries` in config
- Use batching where possible

### GPU Out of Memory
For E2:
- Reduce batch size
- Use mixed precision (fp16)
- Process embeddings incrementally

### Missing Dependencies
```bash
# Audio processing
pip install librosa soundfile pydub

# Statistics
pip install scipy statsmodels pingouin

# Visualization
pip install matplotlib seaborn
```

## Paper Integration

After running experiments:

1. **Copy results to paper**:
   ```bash
   cp results/*/*.png ../Paper/figures/
   ```

2. **Generate LaTeX tables**:
   ```bash
   python generate_latex_tables.py
   ```

3. **Update Response Letter** with actual numbers

## Contact

For issues, check:
- Source code: `/Source/rag_system.py`
- Experiment plan: `/Research/TMM_Supplementary_Experiment_Plan.md`
