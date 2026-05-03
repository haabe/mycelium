#!/usr/bin/env python3
"""Framework-guard helper for the PreToolUse framework-guard hook.

Classifies the target file path against .claude/manifest.yml's framework
sections. If the file is framework-classified AND the project is in dogfood
mode (.claude/state/upstream.json present and active), denies the edit with
a clear message routing the agent to the upstream repo.

Usage (called by .claude/hooks/framework-guard.sh):
  echo $TOOL_INPUT_JSON | python3 framework_guard.py <state_file> <project_dir>

Returns:
  - exit 0, empty stdout → allow
  - exit 0 + JSON deny on stdout → block with UI message

Design: stdlib only (json, os, sys, pathlib). No PyYAML dependency.
The manifest YAML is parsed with a minimal indent-based scanner that
handles the specific shape of .claude/manifest.yml — not a general parser.
If manifest.yml grows more complex sub-structures, this scanner needs an
update (and a corresponding test).
"""
import json
import os
import sys
from pathlib import Path


def parse_manifest(manifest_path):
    """Extract framework file/directory lists from manifest.yml.

    Returns a dict with keys matching the manifest sections:
      top_level, directories, single_files, harness_framework,
      preserved_dir_readmes, evals_replace, metrics_adapters_framework
    """
    framework = {
        "top_level": [],
        "directories": [],
        "single_files": [],
        "harness_framework": [],
        "preserved_dir_readmes": [],
        "evals_replace": [],
        "metrics_adapters_framework": [],
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

            # List item: "- value  # optional comment"
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

    return framework


def is_framework(file_path, project_dir, framework):
    """Return (True, matched_rule) if file_path is framework-classified."""
    abs_path = os.path.abspath(file_path)
    project_dir = os.path.abspath(project_dir)

    # Outside project → not classifiable here
    rel_path = os.path.relpath(abs_path, project_dir)
    if rel_path.startswith(".."):
        return False, None

    # Exact-match lists
    if rel_path in framework["top_level"]:
        return True, f"framework.top_level: {rel_path}"
    if rel_path in framework["single_files"]:
        return True, f"framework.single_files: {rel_path}"
    if rel_path in framework["harness_framework"]:
        return True, f"harness_framework: {rel_path}"
    if rel_path in framework["preserved_dir_readmes"]:
        return True, f"preserved_dir_readmes: {rel_path}"
    if rel_path in framework["metrics_adapters_framework"]:
        return True, f"metrics_adapters.framework: {rel_path}"

    # Prefix-match lists (directories)
    for prefix in framework["evals_replace"]:
        if rel_path.startswith(prefix):
            return True, f"evals.replace: {prefix}"
    for dir_path in framework["directories"]:
        if rel_path.startswith(dir_path):
            return True, f"framework.directories: {dir_path}"

    return False, None


def deny(reason):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def main():
    if len(sys.argv) != 3:
        sys.exit(0)  # Misconfigured → fail open

    state_file = sys.argv[1]
    project_dir = sys.argv[2]

    # Read upstream config
    try:
        with open(state_file) as f:
            state = json.load(f)
    except Exception:
        sys.exit(0)  # Malformed state → fail open

    if not state.get("active", True):
        sys.exit(0)  # Explicitly disabled

    upstream_repo = state.get("upstream_repo", "the upstream framework repo")

    # Read tool input
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Classify
    manifest_path = Path(project_dir) / ".claude" / "manifest.yml"
    framework = parse_manifest(manifest_path)
    matched, rule = is_framework(file_path, project_dir, framework)

    if matched:
        rel_path = os.path.relpath(os.path.abspath(file_path), project_dir)
        deny(
            f"Mycelium framework-guard: {rel_path} is classified as FRAMEWORK "
            f"({rule}) per .claude/manifest.yml. This project is in dogfood "
            f"mode (.claude/state/upstream.json points to '{upstream_repo}'). "
            f"Framework changes must flow upstream first: edit in '{upstream_repo}', "
            f"commit + push, then run .claude/scripts/upgrade.sh here. "
            f"\n\nRecurring failure logged in corrections.md 2026-05-03 "
            f"'Framework changes made directly in roadmap'. To bypass this gate "
            f"in an emergency, set 'active': false in .claude/state/upstream.json. "
            f"Use the bypass sparingly — every bypass should be paired with an "
            f"escape-hatch entry per .claude/orchestration/escape-hatch.md."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
