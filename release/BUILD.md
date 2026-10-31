# Build and reproduce boundaries

The application ships Python source, the frozen native measurement module/oracles, fixed numerical adapter/data, and the exact embedded foundation. No compilation or dependency installation is needed on the declared existing runtime. `Start-Research.ps1 doctor` checks the runtime and package; the ten named presets exercise native Python, native C# and authored numerical paths.

Changes require a new reviewed candidate and manifest. The manifest is a sorted file-to-SHA-256 mapping serialized as canonical UTF-8 JSON, excluding only PRODUCT-MANIFEST.json itself. Do not edit an installed release or merely regenerate a manifest to suppress a defect. Revalidate qualification, protocol semantics, controls, independent arithmetic and applicable operational/package checks before publishing another version.

The numerical dependency manifest and source qualification retain method/data/oracle hashes. Development test sources are preserved under validation/test-sources with their original setup paths for audit; they are not an automatically installed test harness. The supported consumer reproduction workflow is documented in REPRODUCE.md. Saved diagnostic state in evidence/state permits read-only metric verification under the exact originating package and Python executable identity. A different compatible runtime can run fresh protocols in new state; it cannot silently substitute for the recorded runtime when verifying old evidence.

This first release has no earlier migration target. Clean removal or renaming of a disposable installation was tested while separate state remained intact. Preserve the whole application version alongside its protocols and runs.
