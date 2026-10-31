# Rollback and removal

Rollback means returning to a complete known-good application version with its matching evidence. Keep application files, state, original deliveries, and sibling products in separate directories so an application can be retired without disturbing data.

1. Request cancellation of active toolkit runs and inspect their resulting state. If a process was interrupted, use `resume` to recover from complete preserved outputs or seal the interruption.
2. Preserve the full private state folder and any public exports. Do not remove receipt or lock files to change a recorded outcome.
3. Close processes using the application. Rename the specific application directory to a clearly marked retired name, or keep it beside the previous version. Verify the resolved source and destination paths before moving anything.
4. Start the intact known-good version and verify only evidence compatible with that version. Use a new state/run identity for a fresh experiment rather than modifying old records.

An uninstall does not require deleting state, registered datasets, original deliveries, the shared foundation release, workbench, or coding-agent platform. Retiring an application directory is a reversible first step. Delete only a deliberately selected retired copy after confirming it is no longer needed; no recursive removal of a computed parent directory is part of the workflow.

Release acceptance should demonstrate this separation using a disposable application copy and preserved test state. This guide does not assert that such a check has already passed.
