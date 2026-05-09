#!/usr/bin/env python3
"""Print a list from .claude/manifest.yml for shell consumption.

Usage:
  python3 parse_manifest.py <key>

Keys (matching manifest.yml structure):
  top_level                     -> framework.top_level
  directories                   -> framework.directories
  single_files                  -> framework.single_files
  harness_framework             -> harness_framework
  preserved_dir_readmes         -> preserved_dir_readmes
  evals_replace                 -> evals.replace
  metrics_adapters_framework    -> metrics_adapters.framework
  project_state                 -> project_state

Output: space-separated values on stdout, one shell-iterable list.
Returns exit 0 even on empty list (so shell loops handle it cleanly).
Returns exit 1 only on misuse (unknown key, missing manifest).

Designed for upgrade.sh:
  TOP_LEVEL=$(python3 .claude/scripts/parse_manifest.py top_level)
  for file in $TOP_LEVEL; do ...; done

Why this exists: corrections.md 2026-04-28 (harness/ hardcoded drift) +
2026-05-03 (top_level hardcoded drift, missed AGENTS.md). Same root cause
recurring. Shifts upgrade.sh from hardcoded lists to manifest-driven —
single source of truth, no drift possible.

Parser is shared with framework_guard.py via _manifest_lib.py (D2 of the
2026-05-03 cleanup cycle — closes the duplicated-parse_manifest DRY
violation logged at end-of-day audit). Parser is intentionally minimal
(stdlib only, no PyYAML) and matches the specific structure of
manifest.yml. If manifest grows new sub-structures, _manifest_lib needs
updating (and a corresponding test).
"""
import sys
from pathlib import Path

# Shared parser — see _manifest_lib.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _manifest_lib import parse_manifest

MIN_ARGV_LEN = 2   # script_name + key
MAX_ARGV_LEN = 3   # script_name + key + optional --manifest=<path>


def main():
    if not (MIN_ARGV_LEN <= len(sys.argv) <= MAX_ARGV_LEN):
        print("Usage: parse_manifest.py <key> [--manifest=<path>]", file=sys.stderr)
        print(
            "Keys: top_level directories single_files version_source harness_framework",
            file=sys.stderr,
        )
        print(
            "      preserved_dir_readmes evals_replace metrics_adapters_framework",
            file=sys.stderr,
        )
        print("      project_state", file=sys.stderr)
        print(
            "Default manifest: .claude/manifest.yml (relative to this script).",
            file=sys.stderr,
        )
        print(
            "--manifest=<path>: override the manifest path (used by upgrade.sh "
            "to read the upstream/temp-dir manifest before local replacement, "
            "closing the recurring stale-read pattern from corrections.md 2026-05-04).",
            file=sys.stderr,
        )
        sys.exit(1)

    key = sys.argv[1]
    valid_keys = {
        "top_level",
        "directories",
        "single_files",
        "version_source",
        "harness_framework",
        "preserved_dir_readmes",
        "evals_replace",
        "metrics_adapters_framework",
        "project_state",
    }
    if key not in valid_keys:
        print(f"Unknown key: {key}", file=sys.stderr)
        print(f"Valid: {' '.join(sorted(valid_keys))}", file=sys.stderr)
        sys.exit(1)

    # Resolve manifest path — default is local, but --manifest=<path> overrides.
    # The override exists so upgrade.sh can read the freshly-pulled upstream
    # manifest before replacing the local one. Without this, new directory
    # entries (or any new manifest field) require a 2nd upgrade run to take
    # effect — corrections.md 2026-05-04 "manifest-driven script reads stale
    # local manifest" (4th instance of the recurring stale-read pattern).
    manifest_path = None
    for arg in sys.argv[2:]:
        if arg.startswith("--manifest="):
            manifest_path = Path(arg.split("=", 1)[1])
        else:
            print(f"Unknown argument: {arg!r}", file=sys.stderr)
            print(
                "Only --manifest=<path> is accepted as an extra argument.",
                file=sys.stderr,
            )
            sys.exit(1)

    if manifest_path is None:
        script_dir = Path(__file__).resolve().parent
        manifest_path = script_dir.parent / "manifest.yml"

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    framework = parse_manifest(manifest_path)
    values = framework.get(key, [])

    # Space-separated for shell iteration
    print(" ".join(values))


if __name__ == "__main__":
    main()
