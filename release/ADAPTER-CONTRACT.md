# Adapter and evaluation contract

Adapters are fixed local implementations selected by a pinned registry. The initial release does not accept user-written code, arbitrary commands, custom imports, package installations, network endpoints, or model requests. Data and protocol text are inputs, never executable instructions.

## Qualified native fixture paths

| Experiment family | Foundation component | Fixed alternatives | Interpretation |
| --- | --- | --- | --- |
| Token counter | `D0001/C0081-03` | Baseline and deliberately faulty negative control | Authored role-counting and rejection fixture behavior |
| Repair diagnostic | `D0007/C0322-01` | Initial, correct, and regression variants | Authored C# regression fixture behavior |

Only qualification-approved extraction of the pinned raw artifacts is allowed. Execution success is insufficient by itself: component/case identity, raw artifact integrity, fixture scope, and oracle agreement must also be checked. The native fixtures are not trained methods; expected labels are embedded in their trusted source. An inherited `final-evaluation` name does not establish a new secret holdout.

`D0007/C0322-02` uses the same source observations and is not another independent study. PC-Winter is not qualified and remains blocked. Historical negative findings remain provenance.

## Numerical dataset

The dataset object contains exactly `schema_version: "1.0.0"`, `dataset_id`, `license`, and `rows`. Every row contains exactly `id`, `group`, `split`, `x`, and `y`. Splits are `development` and `final`; at least eight development rows and four final rows are required, with at most 256 total. Row IDs are unique. This initial profile also requires one row per unique group, excluding within-split duplicates and cross-split group overlap.

IDs/groups are simple identifiers with a maximum length of 64 characters. Numeric inputs must be finite, with absolute value no greater than one million; booleans are rejected. License is bounded single-line metadata. Unknown fields and duplicate JSON keys are rejected. The validated normalized dataset is registered by content hash. Metadata does not enter adapter prompts or command arguments.

The numerical request has exactly this structure:

```text
{schema_version, method, dev: [{id, x, y}], final: [{id, x}]}
```

Final labels are kept in local evaluator state. The adapter rejects any final row containing `y` or another extra field. Its response contains a schema version, method name, `predictions: [{id, value}]`, and fixed fit details. All prediction IDs must match the final-label IDs exactly.

Methods are `ordinary-least-squares`, `mean-baseline`, `zero-predictor`, and `same-baseline`. They have no selected hyperparameters and no random seeds. OLS fits only development rows; constant development x values use a documented slope-zero tie-break. The mean baseline predicts the development y mean. Same-baseline intentionally repeats that rule. Derived coefficients and predictions must be finite with magnitude at most 10^12; invalid derived values fail rather than being clipped or silently changing the method.

The fixed numerical adapter reads a bounded UTF-8 JSON request. The host starts it with an argument list, not a shell, and enforces the frozen timeout plus output/process/memory limits. See the shipped numerical contract for exact numerical bounds and algorithms.

## Frozen protocol and comparison

Protocol fields are `schema_version`, `protocol_id`, `version`, `experiment_id`, `hypothesis`, `dataset_sha256`, `metric`, `direction`, `absolute_tolerance`, `repetitions`, `seeds`, `stopping_rule`, `timeout_seconds`, `claim_scope`, `supersedes`, and `change_reason`. Extra fields are rejected. The protocol key is `protocol_id--version`.

Native protocols use `dataset_sha256: "embedded"`, accuracy, and maximization. Numerical protocols refer to registered data, use MSE or MAE, and minimize. Repetitions are one to three; `seeds` must be empty. The stopping rule is `fixed-repetitions-stop-on-execution-error`. The scope is `fixture-or-authored-diagnostic; no-paper-replication`.

For minimization, each paired improvement is baseline loss minus candidate loss; maximization reverses the sign. A mean improvement strictly greater than the preset absolute tolerance is positive, strictly less than its negative is negative, otherwise inconclusive. Equality at a threshold is inconclusive. Report count, mean, population standard deviation, minimum, and maximum as descriptive summaries only. There are no p-values, confidence intervals, or independence claims.

A protocol correction uses a new version/key with both `supersedes` and `change_reason`. A run correction uses a new run ID with `--supersedes` and `--reason`. Case-insensitive reservations prevent capitalization aliases. Neither correction rewrites old evidence.
