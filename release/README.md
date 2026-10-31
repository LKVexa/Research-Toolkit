# Research Replication Toolkit 0.1.0-rc.1

The third product is built and locally verified, independently of the workbench and coding-agent platform. It provides catalog discovery, data validation, frozen protocols, bounded method/baseline execution, comparison, evidence verification and aggregate report export.

Start with [the application guide](app/START_HERE.md). Use `app/Start-Research.ps1` or `app/Research-Toolkit.cmd` on the declared Windows/Python runtime. Extract archives to a short path, such as `C:\Tools`, and keep run state outside the application.

Ten sample protocols were verified: three positive, four negative and three inconclusive comparisons. These are qualified source fixtures and authored analytical controls. Paper-scale replication remains unverified, and PC-Winter remains unavailable. [Acceptance report](ACCEPTANCE-REPORT.md) · [Example reports](examples/reports/index.html) · [Known limits](KNOWN-LIMITATIONS.md).

Saved local fixture evidence can be checked without new execution. From the app directory:

```powershell
& './Start-Research.ps1' verify --state '../evidence/state' --run-id distribution-shift-negative
```

All 9,364 original files and the existing foundation/workbench/coding-agent releases were preserved. The three products retain separate roots, state, manifests, versions and release evidence.
