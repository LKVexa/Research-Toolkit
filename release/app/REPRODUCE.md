# Reproduce and inspect a comparison

Reproduction requires the exact released application, its verified foundation and adapter artifacts, the declared runtime, a registered dataset or native fixture, and an immutable protocol. Preserve all of these identifiers with the result. A report's positive/negative/inconclusive label is a bounded diagnostic comparison, not a paper result.

## Stored evidence

From the application folder, with a short compatible state path:

```powershell
$state = Join-Path $env:LOCALAPPDATA 'RT01'
& './Start-Research.ps1' runs --state $state
& './Start-Research.ps1' inspect --run-id linear-01 --state $state
& './Start-Research.ps1' verify --run-id linear-01 --state $state
```

Verification checks the preserved evidence and its receipts. It does not grant permission to edit raw outputs. Keep dataset labels, per-row losses, and raw predictions in private local evidence. Public export is aggregate JSON/HTML only.

To repeat the same frozen protocol deliberately, create a new run ID. Link a replacement or follow-up attempt to its predecessor with a reason:

```powershell
& './Start-Research.ps1' run --protocol linear-positive--1.0.0 --state $state --run-id linear-02 --supersedes linear-01 --reason 'Explicit reproducibility check under the same frozen protocol.'
& './Start-Research.ps1' compare --left linear-01 --right linear-02 --state $state
```

Comparison must respect the tool's compatibility checks; unrelated datasets or metrics must not be treated as interchangeable. The original run remains immutable, including negative, failed, cancelled, or inconclusive outcomes. Repetition supplies no additional independent samples for these deterministic methods.

## Cancellation and recovery

```powershell
& './Start-Research.ps1' cancel --run-id linear-02 --state $state
& './Start-Research.ps1' resume --run-id linear-02 --state $state
```

Cancellation is checked while bounded child work runs. Resume reuses complete preserved process outputs when recovery is possible, otherwise seals the run as interrupted. It never reexecutes a missing process. To execute again, request a new run with an explicit predecessor and reason. Never remove locks or edit receipts to force recovery.

## Custom numerical data

The application includes a valid starting pair in `examples/custom-dataset.json` and `examples/custom-protocol.json`. The protocol's data hash matches that exact sample after normalization, and its metric is MAE. You can register and freeze these as supplied:

```powershell
& './Start-Research.ps1' dataset --file './examples/custom-dataset.json' --state $state
& './Start-Research.ps1' freeze --file './examples/custom-protocol.json' --state $state
& './Start-Research.ps1' run --protocol custom-linear--1.0.0 --state $state --run-id custom-01
```

For your own study, copy both files outside the application before editing them. Replace the protocol's data hash with the registration result, choose a new protocol ID or version, and set the hypothesis and comparison rules before collecting final results. The `protocol` display command returns a wrapper containing the protocol and its receipt metadata; only the inner `protocol` object is a valid input to `freeze`.

Prepare a dataset matching `ADAPTER-CONTRACT.md`, including license metadata, separate development/final assignments, unique IDs/groups, and bounded numeric values. Register it:

```powershell
& './Start-Research.ps1' dataset --file 'C:\Path\To\dataset.json' --state $state
```

Use the returned dataset SHA-256 in a complete protocol JSON with `experiment_id` chosen from `numeric-ols`, `numeric-zero`, or `numeric-equivalence`. Select MSE or MAE, minimization, an absolute tolerance, one to three deterministic repetitions, an empty seed list, the fixed stopping rule, timeout, and the diagnostic claim scope before looking at final results. See the full field contract in `ADAPTER-CONTRACT.md`.

```powershell
& './Start-Research.ps1' freeze --file 'C:\Path\To\protocol.json' --state $state
```

`freeze` reports a key such as `my-study--1.0.0`. Inspect that exact key with `protocol --id`, then pass it to `run --protocol`. Paths and names in these custom-data examples are placeholders; use your actual files and the returned key.

Do not revise data, metrics, tolerances, methods, or stopping rules after seeing final outcomes while retaining the old identity. Register changed data under its new content hash and freeze a new protocol version. A correction supplies both the prior protocol key in `supersedes` and a nonempty `change_reason`. Keep the earlier protocol and results visible.

The numerical request carries development labels and final features only. This separation does not turn a user-authored synthetic fixture into an externally validated study. Native fixture labels are embedded in trusted source and are not claimed to be secret. Keep those limits with any exported conclusion.
