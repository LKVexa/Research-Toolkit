# Known limitations

- The release supports bounded fixture replay and authored univariate analytical diagnostics. Source-paper replication, scientific validity, general coding performance, and benchmark superiority remain unverified.
- PC-Winter remains blocked. `D0007/C0322-02` duplicates the observations represented by `C0322-01` and cannot increase sample count or replication count.
- Native diagnostic expected values are embedded in their trusted source. Inherited development/final labels do not establish a new blind holdout. The numerical adapter's final-label separation is a distinct interface control.
- Numerical data are small, finite, bounded, and univariate. This initial profile requires one row per unique group. Multivariate models, grouped repeated observations, classification, missing values, categorical inputs, and arbitrary adapters are unsupported.
- OLS is a fixed development-only fit. Degenerate development x values use a declared slope-zero tie-break. Ill-conditioned fits that exceed derived-value bounds fail explicitly. Distribution shift can make OLS worse than the mean baseline, as an authored negative control demonstrates.
- Metrics and tolerances are prespecified. Positive/negative/inconclusive refer to a directional mean difference relative to an absolute threshold. The release provides descriptive population dispersion, without p-values, confidence intervals, or independence claims.
- One to three deterministic repetitions test reproducibility only. No seed variation, adaptive search, hyperparameter tuning, or final-outcome-driven selection is supported.
- The package and existing runtime are trusted local code. Fixed process limits are not a service for executing arbitrary untrusted programs. The application uses no network or model calls during normal workflows; it does not install dependencies.
- Python 3.12.14, Windows, NumPy 2.3.5 for the native Python fixture, and the foundation's .NET requirements are part of the environment contract. Other versions are not implicitly accepted.
- Windows paths can become long inside nested native-fixture evidence. Use short state roots and keep state separate from the application and protected sources. A relocated application does not justify modifying stored evidence paths or receipts.
- Local state contains private datasets and detailed results. Only aggregate export is intended for sharing. Review the actual exported artifacts and the release evidence before distribution.
- Resume never reruns missing child processes. Some interrupted runs can only be sealed as interrupted and followed by a new explicit superseding attempt. Failed and cancelled evidence is retained.
- Hashes and receipts detect divergence relative to recorded artifacts; they are not third-party signatures or proof against an attacker able to replace an entire application and all of its trust records.

Acceptance records describe what was checked for the exact release. This document does not assert that release gates or particular experiment runs have passed.
