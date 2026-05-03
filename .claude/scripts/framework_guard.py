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

# Shared parser — see _manifest_lib.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _manifest_lib import parse_manifest  # noqa: E402


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


def is_framework_write_in_command(cmd, project_dir, framework):
    """Detect Bash commands that write to framework-classified paths.

    Returns (True, matched_path, matched_pattern) when a write operation
    targeting a framework path is detected, (False, None, None) otherwise.

    Closes the Bash coverage gap acknowledged when framework-guard.sh
    shipped (corrections.md 2026-05-03): the original hook only intercepted
    Write|Edit|MultiEdit. An agent using `cp`, `cat >`, `echo >`, `tee`,
    `sed -i`, etc. via Bash to a framework path bypassed the guard. This
    function closes that gap.

    Heuristic-based (not a full shell parser). False positives are bypassable
    via upstream.json `active: false`. False negatives are the more dangerous
    direction, so the patterns lean conservative.
    """
    import re

    # Normalize for matching
    cmd_norm = cmd.strip()

    # ALLOWLIST 1: legitimate upgrade.sh invocation — this IS the framework-update mechanism
    if re.match(r"^\s*bash\s+(?:[./\w-]*\.claude/scripts/)?upgrade\.sh", cmd_norm):
        return False, None, None

    # ALLOWLIST 2: git operations that don't write framework files via shell
    # (git checkout/reset CAN restore framework files, but that's git-state restoration,
    # not agent-driven framework editing — different failure mode, not what this guards)
    git_safe_subcmds = (
        "status",
        "diff",
        "log",
        "show",
        "add",
        "commit",
        "push",
        "pull",
        "fetch",
        "branch",
        "checkout",
        "restore",
        "stash",
        "reset",
        "rev-parse",
        "remote",
        "config",
        "tag",
        "merge",
        "rebase",
        "blame",
        "shortlog",
    )
    if re.match(rf"^\s*git\s+({'|'.join(git_safe_subcmds)})\b", cmd_norm):
        return False, None, None

    # Read-only prefix detection lives in the per-segment scan below — a
    # standalone allowlist here is unsafe (compound statements like
    # `cat foo && echo bar > framework_path` have a read prefix but write
    # downstream). The per-segment scan catches both correctly.

    # Build framework path patterns from manifest
    framework_paths = set()
    framework_paths.update(framework["top_level"])
    framework_paths.update(p.rstrip("/") + "/" for p in framework["directories"])
    framework_paths.update(framework["single_files"])
    framework_paths.update(framework["harness_framework"])
    framework_paths.update(framework["preserved_dir_readmes"])
    framework_paths.update(framework["metrics_adapters_framework"])
    for evals_path in framework["evals_replace"]:
        framework_paths.add(evals_path.rstrip("/") + "/")

    # Split command on common compound-command separators to analyze each segment
    # individually. Conservative: also split on subshells, command substitution.
    segments = re.split(r"(?:&&|\|\||;|\|(?!\|))", cmd_norm)

    write_op_patterns = [
        # Direct file-write commands followed by a destination path
        (r"\b(cp|mv|install|ln)\s+", "copy/move/install/link"),
        # Heredoc / redirect: command > path or command >> path
        (r">{1,2}(?!&)\s*", "redirect"),
        # tee writes
        (r"\btee\s+(-a\s+)?", "tee"),
        # sed in-place
        (r"\bsed\s+(?:-[^\s]*i[^\s]*|-i)\s+", "sed -i"),
        # python -c with file open(..., 'w'/'a') — common shell-from-python pattern
        (r"\bopen\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][wa]", "python file write"),
        # rm against framework
        (r"\brm\s+(-[a-z]+\s+)*", "rm"),
        # touch (creates files)
        (r"\btouch\s+", "touch"),
        # chmod (modifies framework files' permissions)
        (r"\bchmod\s+(\S+\s+)+", "chmod"),
    ]

    for segment in segments:
        seg = segment.strip()
        if not seg:
            continue

        # Check each framework path against each write pattern
        for fp in framework_paths:
            # Skip if the framework path doesn't appear in this segment at all
            if fp not in seg:
                continue

            # Check if a write operation precedes/surrounds the framework path in this segment
            for op_re, op_name in write_op_patterns:
                if re.search(op_re + r"[^|;&]*" + re.escape(fp), seg):
                    return True, fp, op_name
                # Also check redirect pattern: <command> > <fp>
                if op_name == "redirect" and re.search(
                    r">{1,2}\s*['\"]?" + re.escape(fp), seg
                ):
                    return True, fp, op_name

    return False, None, None


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
    tool_input = input_data.get("tool_input", {})

    manifest_path = Path(project_dir) / ".claude" / "manifest.yml"
    framework = parse_manifest(manifest_path)

    # Branch on tool — Edit/Write/MultiEdit use file_path; Bash uses command
    if tool_name in ("Write", "Edit", "MultiEdit"):
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)

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

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if not cmd:
            sys.exit(0)

        matched, fp, op = is_framework_write_in_command(cmd, project_dir, framework)
        if matched:
            deny(
                f"Mycelium framework-guard: this Bash command writes to {fp} "
                f"({op}), which is classified as FRAMEWORK per .claude/manifest.yml. "
                f"This project is in dogfood mode (.claude/state/upstream.json points "
                f"to '{upstream_repo}'). Framework changes must flow upstream first: "
                f"edit in '{upstream_repo}', commit + push, then run "
                f".claude/scripts/upgrade.sh here.\n\n"
                f"Closes the Bash coverage gap acknowledged when the file-edit guard "
                f"shipped (corrections.md 2026-05-03). Legitimate sync IS allowed: "
                f"`bash .claude/scripts/upgrade.sh` is allowlisted; git operations "
                f"(checkout/restore/stash/reset) are allowlisted.\n\n"
                f"To bypass for an emergency: set 'active': false in "
                f".claude/state/upstream.json. Use sparingly — every bypass should be "
                f"paired with an escape-hatch entry per .claude/orchestration/"
                f"escape-hatch.md."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
