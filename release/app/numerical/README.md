# Authored numerical diagnostics

This module compares four fixed, deterministic methods on a bounded univariate regression dataset. It is an analytical workflow control, not a replication of a research paper or a scientific benchmark. Custom datasets use the same diagnostic contract and do not change that scope.

`data.validate_dataset(value)` accepts exactly `schema_version`, `dataset_id`, `license`, and `rows`. Version is `1.0.0`. Each row has exactly `id`, `group`, `split`, `x`, and `y`. IDs and groups use simple identifiers of 1–64 characters. IDs are globally unique; this initial profile also requires one row per globally unique group, which excludes cross-split group overlap. Splits are `development` and `final`, with at least 8 and 4 rows respectively, at most 256 total. Numeric values must be finite real JSON numbers with magnitude at most one million; booleans are rejected. License is nonempty single-line metadata with a 1,024-byte limit. Extra fields are rejected. Metadata is never interpreted as instructions or code.

`data.make_request(dataset, method)` returns exactly `schema_version`, `method`, `dev:[{id,x,y}]`, and `final:[{id,x}]`. Dataset metadata, group names, and final labels do not enter the adapter. `data.final_labels(dataset)` provides the separate evaluator-only `[{id,y}]` array. The adapter rejects final rows containing `y` or any other extra field.

Run the trusted fixed adapter with `python -I -B numerical/adapter.py --request REQUEST.json`. It reads one UTF-8 JSON file of at most 131,072 bytes and emits one JSON result with `predictions:[{id,value}]` and `fit_details`. It rejects duplicate JSON keys and non-finite constants. It has no network operations, dynamic evaluation, package installation, or imports from dataset-supplied paths. The host owns process limits, integrity checks, cancellation, and evidence storage.

Methods are `ordinary-least-squares`, `mean-baseline`, `zero-predictor`, and `same-baseline`. OLS fits only development rows, using centered/scaled sums to reduce numerical error. Identical development x values use a declared slope-zero tie-break and the development mean. The mean baseline predicts the development y mean. The zero control always predicts zero. Same-baseline intentionally computes exactly the same rule as mean-baseline. There are no selected hyperparameters or random seeds. Coefficients and predictions must remain finite and have magnitude at most 10^12; ill-conditioned requests exceeding that derived-value bound fail explicitly, without clipping or switching methods.

`metrics.compare({candidate:[{id,value}],baseline:[{id,value}]}, final_labels, metric, direction='minimize', tolerance=1e-9)` supports `mse` and `mae`. Prediction IDs must match final label IDs exactly. For minimization, each paired improvement is baseline loss minus candidate loss; maximization reverses that sign. A mean above the prespecified absolute tolerance is `positive`, below its negative is `negative`, otherwise `inconclusive`. An exact boundary is inconclusive. Tolerance is an absolute diagnostic threshold, not a significance level. The result includes both scores, per-row losses, and the paired-difference count, mean, population standard deviation, minimum, and maximum. No confidence interval, p-value, sampling uncertainty, or independence claim is provided. Per-row values belong in private evidence; public summaries can omit them.

The frozen presets are chosen by formulas, without random seeds or selected runs:

| Dataset | Development | Final | Prespecified OLS versus mean |
| --- | --- | --- | --- |
| positive-linear | x = −4,…,3; y = 2x + 3 | x = 4,…,7; same formula | OLS MSE/MAE 0/0; mean 149/12; positive |
| negative-linear | x = −4,…,3; y = −3x + 5 | x = 4,…,7; same formula | OLS 0/0; mean 335.25/18; positive |
| negative-shift | x = −4,…,3; y = 2x + 3 | x = 4,…,7; y = 2 | OLS 149/12; mean 0/0; negative |

On positive-linear, zero-predictor has MSE 201 and MAE 14, worse than mean-baseline's 149 and 12; same-baseline is exactly equivalent to mean-baseline and is inconclusive at the preset tolerance. The shift case is an authored distribution change, not a claim that linear regression universally fails. Negative-linear supplies the requested negative-slope exact relation; equivalence reuses positive-linear and does not need a fourth dataset.

Repeated execution of these deterministic methods is only a reproducibility check. Repeated seeds or repeated identical runs do not supply independent observations and must not be presented as extra samples. `CONTROLS.json` fixes the analytical expectations before benchmark execution. `MANIFEST.json` freezes the adapter, validator, metrics, datasets, controls, documentation, and tests. Root workflow code must pin and verify that manifest before any run.
