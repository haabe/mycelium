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

Parser is intentionally minimal (stdlib only, no PyYAML) and matches the
specific structure of manifest.yml. If manifest grows new sub-structures,
this scanner needs updating (and a corresponding test).
"""
import sys
from pathlib import Path


def parse_manifest(manifest_path):
    framework = {
        "top_level": [],
        "directories": [],
        "single_files": [],
        "harness_framework": [],
        "preserved_dir_readmes": [],
        "evals_replace": [],
        "metrics_adapters_framework": [],
        "project_state": [],
    }

    if not manifest_path.exists():
        return framework

    section = None
    subsection = None
    with open(manifest_path) as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(stripped)

            # Top-level section: e.g., "framework:" at column 0
            if indent == 0 and stripped.endswith(":"):
                section = stripped[:-1]
                subsection = None
                continue

            # Sub-section: e.g., "  top_level:" at column 2
            if indent == 2 and stripped.endswith(":"):
                subsection = stripped[:-1]
                continue

            # List item
            if stripped.startswith("- "):
                value = stripped[2:].split("#")[0].strip().strip('"').strip("'")
                if not value:
                    continue

                if section == "framework":
                    if subsection in ("top_level", "directories", "single_files"):
                        framework[subsection].append(value)
                elif section == "harness_framework":
                    framework["harness_framework"].append(value)
                elif section == "preserved_dir_readmes":
                    framework["preserved_dir_readmes"].append(value)
                elif section == "evals" and subsection == "replace":
                    framework["evals_replace"].append(value)
                elif section == "metrics_adapters" and subsection == "framework":
                    framework["metrics_adapters_framework"].append(value)
                elif section == "project_state":
                    framework["project_state"].append(value)

    return framework


def main():
    if len(sys.argv) != 2:
        print("Usage: parse_manifest.py <key>", file=sys.stderr)
        print("Keys: top_level directories single_files harness_framework", file=sys.stderr)
        print("      preserved_dir_readmes evals_replace metrics_adapters_framework", file=sys.stderr)
        print("      project_state", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]
    valid_keys = {
        "top_level",
        "directories",
        "single_files",
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

    # Find manifest.yml — script lives at .claude/scripts/parse_manifest.py
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
