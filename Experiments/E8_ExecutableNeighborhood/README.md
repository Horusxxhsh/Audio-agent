# E8 Executable Neighborhood Retrieval

This workspace aggregates the E8 evidence layer for executable neighborhood retrieval. It does not modify the paper source; it produces a machine-readable JSON summary and a paper-facing Markdown claim boundary.

## Inputs

- `outputs/topk/topk_retrieval_metrics.json`: Top-K parameter-neighborhood recall and top-1 parameter metrics.
- `outputs/epr/epr_projection_results.json`: exemplar-preserving soft-blended parameter projection metrics and provenance.
- `outputs/module_rerank/module_aware_rerank_results.json`: oracle-free active-module consensus reranking diagnostics.
- `../E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json`: MLP direct-regression boundary, using `projected_metrics`.

## Summary Command

```bash
python3 Experiments/E8_ExecutableNeighborhood/summarize_e8.py \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --epr-json Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json \
  --module-json Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json \
  --mlp-json Experiments/E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/summary
```

The command writes:

- `outputs/summary/e8_summary.json`
- `outputs/summary/e8_summary.md`

## Claim Boundary

Supported by current E8 outputs:

- Top-K retrieval can be interpreted as parameter-neighborhood recall.
- EPR is an executable soft-blended projection with retained exemplar provenance.
- MLP+RangeProjection is retained as the direct-regression boundary row; in the current E8 outputs, EPR-K5 is the primary hybrid result on Norm.L2 and Acc@0.1.
- Module-aware reranking is diagnostic in this run and must not be written as a gain.

Not supported by current E8 outputs:

- PC-TRR training gains are not verified.
- Temporal Pyramid TRR is not verified.
- Log-Covariance/Riemannian TRR is not verified.
- Analysis-by-synthesis reranking is not verified.
- Protocol-C adaptive fusion cannot be used as the main contribution.
