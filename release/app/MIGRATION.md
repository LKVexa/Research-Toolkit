# Migration and version changes

Version 0.1.0-rc.1 is the first separate research-toolkit product. There is no automatic migration of workbench or coding-agent state. Do not point this application at another product's state folder, rewrite its marker, or copy its run receipts into research state.

Install the full versioned application beside existing products. Use a new short research state root outside all protected source and application trees. Original deliveries and their notes remain provenance; they are not moved into a mutable research workspace.

For a later toolkit release, preserve the complete old application and its state. Verify old runs with their originating package. Do not edit version fields or hashes to make old evidence appear to originate from the new package. A new package can require fresh compatibility checks or a new state root; use only a documented migration if one is supplied by that release.

Dataset changes create new content hashes. Protocol changes require a new versioned key and an explicit predecessor/reason when correcting an earlier protocol. A new run ID records a deliberate rerun or correction, using `--supersedes` and `--reason` as appropriate. Case changes do not create a new identity.

Public reports can be copied for distribution, but they are not a replacement for the private dataset and raw evidence needed to verify a local run. Retain the originating application, protocol, registered data, and complete evidence separately.
