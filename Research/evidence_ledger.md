# Evidence Ledger (TMM Track)

This file maps each paper claim to concrete, reproducible evidence artifacts.

## Status legend
- planned: experiment not executed yet
- verified: evidence exists and is reproducible from artifacts
- falsified: experiment contradicts the claim (must update paper)

## Claims

| Claim ID | Claim (draft) | Evidence (paths) | Status | Notes |
|---|---|---|---|---|
| C1 | TRR improves retrieval/parameter inference vs strong embeddings on Tier M (>=200). | `runs/E2/*/tables/trackA_main.csv`, `runs/E2/*/figures/*` | planned | Must include >=5 strong baselines. |
| C2 | Uncertainty-aware fusion improves over best single modality consistently (not dominated by outliers). | `runs/E4/*/figures/delta_cdf.png`, `runs/E4/*/tables/fusion_ablation.csv` | planned | Report median + trimmed mean. |
| C3 | Constraint repair reduces violation rate by >=10x with limited performance trade-off. | `runs/E5/*/tables/repair_ablation.csv`, `runs/E5/*/repair_stats.jsonl` | planned | Pre-define violation threshold. |
| C4 | Parameter-space metrics are correlated with perceptual quality, but not equivalent (with failure cases). | `runs/E7/*/tables/corr.csv`, `runs/E7/*/figures/scatter.png`, `runs/E7/*/cases.csv` | planned | Use clustered bootstrap CIs. |
| C5 | Subjective MUSHRA shows significant preference for our method vs strongest baseline under corrected statistics. | `runs/E8/*/tables/subjective_emm.csv`, `runs/E8/*/analysis/*` | planned | Freeze analysis plan before running. |
| C6 | TRR/fusion/repair trade off accuracy vs latency in a documented Pareto frontier. | `runs/E6/*/tables/efficiency.csv`, `runs/E6/*/figures/latency_cdf.png`, `runs/E6/*/figures/pareto.png` | planned | Include p50/p95, device info. |

