# Scripts — Utility Scripts

Standalone scripts for validation, maintenance, and upgrades.

## What's Here

- **[validate_canvas.py](validate_canvas.py)** — Validates canvas YAML files against schemas. Run in CI to catch structural errors.
- **[scope_check.py](scope_check.py)** — Checks if a file path is within the declared scope of an active execution. Called by `scope-gate.sh` hook. Python stdlib only.
- **[upgrade.sh](upgrade.sh)** — Framework upgrade helper for moving between Mycelium versions.

All scripts use Python stdlib only (no pip dependencies) so they work on fresh clones without setup.
