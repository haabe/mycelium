# Scripts — Utility Scripts

Standalone scripts for validation, maintenance, and upgrades.

## What's Here

- **[validate_canvas.py](validate_canvas.py)** — Validates canvas YAML files against schemas. Run in CI to catch structural errors.
- **[scope_check.py](scope_check.py)** — Decides whether a write is inside the folders an open delivery cycle named (`in_scope_paths` on the L4 in `.claude/diamonds/active.yml`), and judges writes that name or change those folders. Called by `scope-gate.sh`; `--notices` is called by `session-start.sh`. Python stdlib plus PyYAML.
- **[upgrade.sh](upgrade.sh)** — Framework upgrade helper for moving between Mycelium versions.
- **[sync_derived.py](sync_derived.py)** — Rewrites mechanically-derived tokens (framework version, skill count) from their single source into the files that quote them. Run before a release; `--check` reports drift without writing. Python stdlib only.

All scripts use Python stdlib only (no pip dependencies) so they work on fresh clones without setup.
