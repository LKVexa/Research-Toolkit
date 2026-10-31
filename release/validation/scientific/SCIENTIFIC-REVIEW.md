# Independent scientific review — numerical module

The direct-module review passed 34 checks with zero failures. It concerns the new product's authored analytical controls only. It does not establish a paper replication, broad benchmark result, complete runner validation or R03 acceptance.

Expected values were derived from raw dataset rows using exact rational arithmetic. The independent OLS oracle solves the normal equations using `nΣxy − ΣxΣy` divided by `nΣx² − (Σx)²`, then obtains the intercept from the means. The production implementation uses centered/scaled floating-point sums. Production adapter and metric functions supply observed outputs only; their outputs are not the oracle.

| Data and candidate versus development mean | Candidate MSE / MAE | Baseline MSE / MAE | Exact direction |
| --- | --- | --- | --- |
| Positive linear, OLS | 0 / 0 | 149 / 12 | Positive |
| Negative slope, OLS | 0 / 0 | 1341/4 / 18 | Positive |
| Authored distribution shift, OLS | 149 / 12 | 0 / 0 | Negative |
| Positive linear, zero predictor | 201 / 14 | 149 / 12 | Negative |
| Positive linear, same baseline | 149 / 12 | 149 / 12 | Inconclusive |

These exact results agree with both preset control declarations and observed MSE/MAE comparisons. The review independently checked paired means and population variance, not only the outcome labels. All comparisons use four unique final rows. Three deterministic repeats retain four samples per result and are not additional independent observations. No confidence interval, p-value or independence claim is supported.

Translation/scaling checks and row permutation preserve the expected predictions and loss relationships. Fixed zero prediction is intentionally excluded from response-translation equivariance because it is anchored to zero. Replacing every final label leaves method requests and predictions unchanged; explicitly injecting a final label into the adapter request is rejected.

Cross-split and within-development group duplication, duplicate row identity, wrong splits, insufficient partition sizes, nonfinite labels and missing predictions are rejected. An infeasible derived coefficient produces an explicit error without a scientific score. Constant development x follows the declared slope-zero/development-mean tie-break. Equality at the comparison tolerance is inconclusive rather than positive.

The low-level comparison helper supports either direction, so reversing direction reverses the conclusion. Source review confirms that qualified numeric protocols require minimization and native accuracy requires maximization. Runtime protocol-rejection checks and the runner's repetition aggregation remain pending until the assembled product is available.

`SCIENTIFIC-REVIEW.json` contains the 34 results, exact rational control values, observed records, input hashes and explicit limits. `review_numerical.py` is the independent test implementation. Reviewed input hashes were unchanged across this run. This focused review does not prove floating-point accuracy for every possible admissible custom dataset or protect against an operator inspecting the local final labels before choosing a protocol.
