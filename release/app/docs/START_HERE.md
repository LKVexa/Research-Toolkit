# Start here

The Research Replication Toolkit freezes and checks bounded local diagnostic comparisons. This first release supports qualified source fixtures and authored numerical controls. It does not claim to reproduce a paper or establish broad benchmark superiority.

Open PowerShell in the application's folder, where `Start-Research.ps1` is located. View available source and experiment information:

```powershell
& './Start-Research.ps1' doctor
& './Start-Research.ps1' catalog
& './Start-Research.ps1' catalog --query 'token'
```

Use a short new state path outside all applications and original deliveries. These commands prepare one fixed numerical comparison and run it:

```powershell
$state = Join-Path $env:LOCALAPPDATA 'RT01'
& './Start-Research.ps1' prepare --preset linear-positive --state $state
& './Start-Research.ps1' protocol --id linear-positive--1.0.0 --state $state
& './Start-Research.ps1' run --protocol linear-positive--1.0.0 --state $state --run-id linear-01
& './Start-Research.ps1' inspect --run-id linear-01 --state $state
& './Start-Research.ps1' verify --run-id linear-01 --state $state
```

`prepare` reports the frozen protocol key. Read the returned result before continuing. Choose a new state name if `RT01` is already used for unrelated work, and a new run ID when the example run already exists. Protocol and run identifiers use lowercase names, preventing capitalization aliases. Row/group identifiers are case-sensitive data values.

Export a public aggregate report to a new folder. Its parent must already exist:

```powershell
$exportParent = Join-Path $env:LOCALAPPDATA 'RTReports'
New-Item -ItemType Directory -Path $exportParent -Force | Out-Null
$report = Join-Path $exportParent 'linear-01'
& './Start-Research.ps1' export --run-id linear-01 --state $state --destination $report
```

Export creates aggregate JSON and HTML. It excludes dataset labels, per-row outcomes, and raw predictions. Full local evidence remains private in the state folder. Existing export destinations are rejected; choose a new name rather than replacing a prior report.

Available presets:

| Preset | Declared comparison |
| --- | --- |
| `token-equivalence` | Native token baseline against itself |
| `token-negative` | Faulty native token control against its baseline |
| `repair-positive` | Native correct repair fixture against initial |
| `repair-negative` | Native regression fixture against initial |
| `repair-equivalence` | Native initial fixture against itself |
| `linear-positive` | OLS versus mean on an authored positive-slope relation |
| `negative-slope-positive` | OLS versus mean on an authored negative-slope relation |
| `distribution-shift-negative` | OLS versus mean after an authored final-distribution shift |
| `zero-negative` | Zero predictor versus mean on the positive-slope dataset |
| `numeric-equivalence` | Identical mean-baseline methods |

Preset names describe intended controls, not completed acceptance results. Execution, implementation checks, comparison, and source claim are reported separately. A negative or inconclusive comparison remains a valid outcome to preserve and review.

Use `runs --state $state` to list local runs. `cancel` requests termination of a running fixed adapter. `resume` uses complete preserved outputs or records an interrupted run; it does not restart a missing process. See `REPRODUCE.md` for explicit fresh attempts and custom datasets, and `INSTALL.md` for the pinned environment and Windows path advice.
