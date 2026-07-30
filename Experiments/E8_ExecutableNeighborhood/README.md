# E8 Executable Neighborhood Retrieval

## Purpose

This experiment supports the manuscript reframing from top-1 audio-similarity retrieval to parameter-transferability-aware executable neighborhood retrieval. The evidence package is intentionally scoped: it uses the existing Protocol-A query list and cached vectors, produces auditable JSON/CSV/Markdown artifacts, and does not introduce new datasets or unverified method claims.

## Inputs

- `outputs/topk/topk_retrieval_metrics.json`: Top-K parameter-neighborhood recall and top-1 parameter metrics.
- `outputs/epr/epr_projection_results.json`: exemplar-preserving soft-blended parameter projection metrics and provenance.
- `outputs/module_rerank/module_aware_rerank_results.json`: oracle-free active-module consensus reranking diagnostics.
- `../E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json`: MLP direct-regression boundary, using `projected_metrics`.

## Commands

```bash
python3 Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --split-file Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt \
  --k 5 \
  --threshold 0.10 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/topk

python3 Experiments/E8_ExecutableNeighborhood/epr_projection.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --method TRR \
  --ks 3 5 \
  --temperature 0.05 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/epr

python3 Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --method TRR \
  --module-weight 0.15 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/module_rerank

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

## Final Verification

Last verified on 2026-05-03 with:

```bash
python3 -m pytest Experiments/common/tests/test_parameter_space.py Experiments/E8_ExecutableNeighborhood -v
(cd Paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error main.tex)
(cd Paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error supplementary.tex)
```

Results:

- `49 passed` for the E8 and shared parameter-space tests.
- `Paper/main.pdf` rebuilt successfully as a 13-page PDF.
- `Paper/supplementary.pdf` rebuilt successfully as a 9-page PDF.
- Required artifact gate passed for the Top-K, EPR, module-rerank, summary Markdown, and main PDF outputs.
- LaTeX logs contain no undefined-reference, undefined-citation, or multiply-defined-label diagnostics.

## Supported Claims

- Retrieval can be evaluated as executable neighborhood discovery using PNR@K.
- EPR can be compared against direct regression while retaining exemplar provenance metrics.
- MLP+RangeProjection is retained as the non-executable direct-regression boundary row; in the current E8 outputs, EPR-K5 is the primary hybrid result on Norm.L2 and Acc@0.1.
- Module-aware reranking is diagnostic in this run and must not be written as a gain.

## Unsupported Claims

- PC-TRR training gains are not validated in this run.
- Temporal Pyramid TRR is not validated in this run.
- Log-Covariance/Riemannian TRR is not validated in this run.
- Analysis-by-synthesis reranking is not validated in this run.
- Protocol-C adaptive fusion is diagnostic and cannot be used as a main superiority claim.
