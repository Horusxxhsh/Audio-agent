# E8 Executable Neighborhood Retrieval Summary

## Scope

This summary aggregates E8 executable-neighborhood evidence from Top-K retrieval, EPR soft blending, module-aware reranking, and the existing E2 MLP boundary. It is a paper-facing evidence boundary document only; it does not modify manuscript text.

## Top-K Parameter Neighborhood Recall

| Method | n | pnr_at_1 | pnr_at_3 | pnr_at_5 | top1_norm_l2 | top1_acc_at_0_1 | top1_recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CLAP | 173 | 0.3526 | 0.6763 | 0.7803 | 0.1896 | 0.7204 | 0.6361 |
| FeatureNN | 204 | 0.2451 | 0.4559 | 0.5686 | 0.2002 | 0.7055 | 0.6208 |
| TRR | 204 | 0.4608 | 0.6520 | 0.7500 | 0.1454 | 0.7863 | 0.7045 |
| Wav2Vec | 204 | 0.2941 | 0.5098 | 0.5931 | 0.1997 | 0.7085 | 0.6228 |

Best PNR@5 method: `CLAP`. These numbers support retrieval as an executable neighborhood surface, not as proof that every downstream parameter value is numerically superior to direct regression.

## Exemplar-Preserving Parameter Projection

| Method | n | norm_l2 | acc_at_0_1 | recall | cosine | module | provenance_effective_exemplars | provenance_max_weight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EPR-K3 | 204 | 0.1356 | 0.7872 | 0.7060 | 0.9177 | 0.8187 | 2.6857 | 0.4664 |
| EPR-K5 | 204 | 0.1334 | 0.7908 | 0.7146 | 0.9207 | 0.8315 | 4.2129 | 0.3438 |

Best EPR method by Norm.L2: `EPR-K5`. EPR is executable soft-blended projection over retrieved exemplars and retains provenance through effective-exemplar and max-weight statistics.

## Module-Aware Reranking

| Method | n | norm_l2_delta | acc_at_0_1_delta | recall_delta | cosine_delta | module_delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TRR | 204 | 0.0024 | 0.0007 | -0.0089 | -0.0052 | -0.0188 |

Module-aware reranking is treated as a diagnostic negative result in this run. It must not be described as a gain unless future outputs show lower Norm.L2 and non-degraded alignment scores under the same oracle-free constraint.

## MLP Boundary Interpretation

| Method | Norm.L2 | Acc@0.1 | Recall | Cosine | Module |
| --- | ---: | ---: | ---: | ---: | ---: |
| MLP-Regressor(raw) | 0.1607 | 0.7884 | 0.3209 | 0.4964 | 1.0000 |
| MLP-Regressor+RangeProjection | 0.1603 | 0.7894 | 0.3468 | 0.5941 | 1.0000 |

Range projection is the relevant MLP boundary row; its deltas relative to raw MLP are preserved in `e8_summary.json`.

EPR should be reported as the primary hybrid result: it improves the retrieval-side Norm.L2 while preserving executable exemplar provenance (effective exemplars 4.2129).

## Claims Supported

- Top-K retrieval can be evaluated as parameter-neighborhood recall on the current Protocol-A E8 outputs.
- EPR is an executable soft-blended projection with retained exemplar provenance over retrieved candidates.
- MLP+RangeProjection remains the direct-regression boundary row, but current E8 outputs must compare it against EPR rather than assuming it is numerically stronger.
- Module-aware reranking is diagnostic on these outputs and must not be described as a gain unless Norm.L2 delta is negative and alignment-score deltas are non-negative in future runs.

## Claims Not Supported

- PC-TRR 训练收益未验证
- Temporal Pyramid TRR 未验证
- Log-Covariance/Riemannian TRR 未验证
- Analysis-by-synthesis reranking 未验证
- Protocol-C adaptive fusion 不能作为主贡献
