#!/usr/bin/env python3
"""Framework-guard helper for the PreToolUse framework-guard hook.

Classifies the target of a tool call against .claude/manifest.yml's
framework sections. If the target is framework-classified AND the project
is in dogfood mode (.claude/state/upstream.json present and active),
denies the tool call with a clear message routing the agent to the upstream.

Two tool surfaces handled:
  - Edit / Write / MultiEdit: classify file_path directly via is_framework()
  - Bash: scan the command string for write-ops to framework paths via
    is_framework_write_in_command()

Refactored 2026-05-03 (D3 of L4 cleanup cycle): the Bash analyzer was
previously a 147-line monolith. Now split into per-concern helpers
(allowlist check, segment scan, write-pattern matching). Same behavior,
KISS-compliant, testable.

Usage (called by .claude/hooks/framework-guard.sh):
  echo $TOOL_INPUT_JSON | python3 framework_guard.py <state_file> <project_dir>

Returns:
  - exit 0, empty stdout → allow
  - exit 0 + JSON deny on stdout → block with UI message

Design: stdlib only (json, os, re, sys, pathlib). No PyYAML dependency.
"""
import json
import os
import re
import sys
from pathlib import Path

# Shared parser — see _manifest_lib.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _manifest_lib import parse_manifest

# ============================================================
# Module-level constants (compiled once, reused per invocation)
# ============================================================

# git subcommands that are safe to allow without further analysis.
# Restorative operations (checkout/restore/stash/reset) CAN modify
# framework files, but that's git-state restoration — a different failure
# mode than agent-driven framework editing, and not what this guard targets.
_GIT_SAFE_SUBCMDS = (
    "status", "diff", "log", "show", "add", "commit", "push", "pull",
    "fetch", "branch", "checkout", "restore", "stash", "reset", "rev-parse",
    "remote", "config", "tag", "merge", "rebase", "blame", "shortlog",
    # git rm/mv are git-state (index/tree) operations, not agent-driven
    # framework editing. Surfaced 2026-05-03 D4 follow-up: `git rm --cached`
    # was incorrectly flagged because of the bare `rm` in the command.
    "rm", "mv",
)

# Subset of git "global options" (https://git-scm.com/docs/git#_options) that
# may appear BEFORE the subcommand (e.g., `git -C /path/to/repo rm file`).
# We strip these to find the actual subcommand for allowlist matching.
_GIT_GLOBAL_OPTS_REGEX = re.compile(
    r"^\s*git\s+"
    r"(?:(?:-C|-c)\s+\S+\s+|"
    r"--git-dir=\S+\s+|"
    r"--work-tree=\S+\s+|"
    r"--no-pager\s+|"
    r"-P\s+)*"
)

# Allowlist patterns — compiled once at module load.
_ALLOWLIST_UPGRADE = re.compile(r"^\s*bash\s+(?:[./\w-]*\.claude/scripts/)?upgrade\.sh")
# Match `git <subcmd>` OR `git <global-opts> <subcmd>`. The optional
# global-opts segment (handled by _GIT_GLOBAL_OPTS_REGEX, which we
# substitute away first) lets us recognize `git -C /path rm foo` as
# a git rm command.
_ALLOWLIST_GIT = re.compile(rf"^\s*git\s+({'|'.join(_GIT_SAFE_SUBCMDS)})\b")

# Compound-command separator: && / || / ; / | (single pipe, not ||).
_SEGMENT_SPLIT = re.compile(r"(?:&&|\|\||;|\|(?!\|))")

# Write-operation patterns. Each tuple is (regex_for_op_prefix, human_name).
# These are matched per-segment, then the framework path must follow.
_WRITE_OP_PATTERNS = [
    (re.compile(r"\b(cp|mv|install|ln)\s+"), "copy/move/install/link"),
    (re.compile(r">{1,2}(?!&)\s*"), "redirect"),
    (re.compile(r"\btee\s+(-a\s+)?"), "tee"),
    (re.compile(r"\bsed\s+(?:-[^\s]*i[^\s]*|-i)\s+"), "sed -i"),
    (
        re.compile(r"\bopen\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][wa]"),
        "python file write",
    ),
    (re.compile(r"\brm\s+(-[a-z]+\s+)*"), "rm"),
    (re.compile(r"\btouch\s+"), "touch"),
    (re.compile(r"\bchmod\s+(\S+\s+)+"), "chmod"),
]

# Path-boundary characters that may legitimately precede a framework path
# in a shell command. Used to prevent substring false positives where a
# framework path appears as part of a longer non-framework path
# (e.g., "/tmp/myc-d2/.claude/manifest.yml" should not match ".claude/manifest.yml").
_PATH_BOUNDARY_PRECEDES = (" ", "\t", "\n", '"', "'", "=", "(", ">", "<", "|", "&", ";")


# ============================================================
# is_framework — file-path classification (Edit/Write/MultiEdit path)
# ============================================================

def is_framework(file_path, project_dir, framework):
    """Return (True, matched_rule) if file_path is framework-classified."""
    abs_path = os.path.abspath(file_path)
    project_dir = os.path.abspath(project_dir)

    rel_path = os.path.relpath(abs_path, project_dir)
    if rel_path.startswith(".."):
        return False, None  # outside project

    # Exact-match buckets
    exact_buckets = (
        ("top_level",                    "framework.top_level"),
        ("single_files",                 "framework.single_files"),
        ("harness_framework",            "harness_framework"),
        ("preserved_dir_readmes",        "preserved_dir_readmes"),
        ("metrics_adapters_framework",   "metrics_adapters.framework"),
    )
    for key, label in exact_buckets:
        if rel_path in framework[key]:
            return True, f"{label}: {rel_path}"

    # Prefix-match buckets
    prefix_buckets = (
        ("evals_replace",  "evals.replace"),
        ("directories",    "framework.directories"),
    )
    for key, label in prefix_buckets:
        for prefix in framework[key]:
            if rel_path.startswith(prefix):
                return True, f"{label}: {prefix}"

    return False, None


# ============================================================
# is_framework_write_in_command — Bash command analysis
# ============================================================

def _extract_framework_paths(framework):
    """Build the set of framework path tokens to search for in commands."""
    paths = set()
    paths.update(framework["top_level"])
    paths.update(p.rstrip("/") + "/" for p in framework["directories"])
    paths.update(framework["single_files"])
    paths.update(framework["harness_framework"])
    paths.update(framework["preserved_dir_readmes"])
    paths.update(framework["metrics_adapters_framework"])
    paths.update(p.rstrip("/") + "/" for p in framework["evals_replace"])
    return paths


def _is_segment_allowlisted(seg):
    """Return True for shell segments that are inherently safe.

    Allowlist (per-segment, so compound commands like
    `cd /path && git rm framework_file` correctly allow the git rm segment):
      1. `bash .claude/scripts/upgrade.sh` — the legitimate framework-update mechanism.
      2. `git [global-opts] <safe-subcommand>` — git state operations
         (see _GIT_SAFE_SUBCMDS). Strips global options like -C, -c,
         --git-dir before matching the subcommand.
    """
    seg_stripped = seg.lstrip()
    if _ALLOWLIST_UPGRADE.match(seg_stripped):
        return True
    # Strip any git global options to expose the subcommand
    normalized = _GIT_GLOBAL_OPTS_REGEX.sub("git ", seg_stripped, count=1)
    return bool(_ALLOWLIST_GIT.match(normalized))


def _is_command_allowlisted(cmd_norm):
    """Backwards-compatible whole-command allowlist (delegates to per-segment).

    Kept for callers that pass the whole command. Internal callers should
    prefer _is_segment_allowlisted, which is per-segment-aware.
    """
    return _is_segment_allowlisted(cmd_norm)


def _path_appears_at_boundary(seg, fp):
    """Return True if `fp` appears in `seg` at a shell-token boundary.

    Prevents substring false positives: ".claude/manifest.yml" should NOT
    match a destination like "/tmp/myc-d2/.claude/manifest.yml" because the
    framework path is preceded by "/myc-d2" (no boundary character).

    A boundary is one of: start-of-string, whitespace, quote, =, (, redirect-op.
    """
    start = 0
    while True:
        idx = seg.find(fp, start)
        if idx == -1:
            return False
        if idx == 0 or seg[idx - 1] in _PATH_BOUNDARY_PRECEDES:
            return True
        start = idx + 1


def _scan_segment_for_write(seg, framework_paths):
    """Scan one shell-segment for write-ops targeting any framework path.

    Returns (True, matched_path, op_name) on first match, (False, None, None)
    if no write to framework path is found in this segment.
    """
    for fp in framework_paths:
        if not _path_appears_at_boundary(seg, fp):
            continue

        fp_re = re.escape(fp)
        for op_pattern, op_name in _WRITE_OP_PATTERNS:
            # Match the op prefix, then any non-control chars, then the framework path
            combined = op_pattern.pattern + r"[^|;&]*" + fp_re
            if re.search(combined, seg):
                return True, fp, op_name
            # Special-case redirect: `command > path` — also match the strict
            # pattern `>{1,2} <fp>` to catch heredoc-mixed cases like
            # `cat > AGENTS.md << EOF`.
            if op_name == "redirect" and re.search(
                r">{1,2}\s*['\"]?" + fp_re, seg
            ):
                return True, fp, op_name

    return False, None, None


def is_framework_write_in_command(cmd, project_dir, framework):  # noqa: ARG001
    """Detect Bash commands that write to framework-classified paths.

    Returns (True, matched_path, matched_pattern) on detected write,
    (False, None, None) otherwise.

    project_dir is currently unused — kept in signature for symmetry with
    is_framework() and to enable future abspath-based destination resolution.

    Heuristic-based (not a full shell parser). False positives are bypassable
    via upstream.json `active: false`. False negatives are the more dangerous
    direction — patterns lean conservative.

    KNOWN LIMITATIONS (documented for future refactor; current behavior is
    intentional within the time-bounded scope of the 2026-05-03 cleanup cycle):
      1. cp/mv/install/ln source/destination ambiguity: when a framework path
         appears as the SOURCE arg (e.g., `cp .claude/manifest.yml /tmp/x.yml`),
         the heuristic flags it as a write because it can't distinguish
         positional arg roles. Fix would require shell-arg parsing. Workaround:
         the active:false bypass is the right tool for legitimate cp-from-
         framework operations.
      2. Embedded test data containing framework paths: when a Bash command
         constructs test inputs that mention framework paths as DATA (e.g.,
         a Python heredoc generating test cases for this very function), the
         hook flags the command. There's no way to distinguish "string
         containing path" from "operation on path" without shell semantics.
         Workaround: write tests as files, invoke with `python3 path/to/test.py`
         where the bash command itself contains no framework paths.
    """
    cmd_norm = cmd.strip()

    framework_paths = _extract_framework_paths(framework)
    segments = _SEGMENT_SPLIT.split(cmd_norm)

    for segment in segments:
        seg = segment.strip()
        if not seg:
            continue
        # Per-segment allowlist: a single segment that is a git op or
        # the upgrade.sh invocation is safe regardless of what other
        # segments in the compound command look like.
        if _is_segment_allowlisted(seg):
            continue
        matched, fp, op = _scan_segment_for_write(seg, framework_paths)
        if matched:
            return True, fp, op

    return False, None, None


# ============================================================
# Hook output + main dispatch
# ============================================================

def deny(reason):
    """Emit the deny JSON expected by the PreToolUse hook protocol."""
    print(
        json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        })
    )
    sys.exit(0)


def _deny_file_edit(rel_path, rule, upstream_repo):
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


def _deny_bash_write(fp, op, upstream_repo):
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


def _handle_file_edit(tool_input, project_dir, framework, upstream_repo):
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return  # no path → can't classify → fail open
    matched, rule = is_framework(file_path, project_dir, framework)
    if matched:
        rel_path = os.path.relpath(os.path.abspath(file_path), project_dir)
        _deny_file_edit(rel_path, rule, upstream_repo)


def _handle_bash(tool_input, project_dir, framework, upstream_repo):
    cmd = tool_input.get("command", "")
    if not cmd:
        return  # no command → fail open
    matched, fp, op = is_framework_write_in_command(cmd, project_dir, framework)
    if matched:
        _deny_bash_write(fp, op, upstream_repo)


def _handle_mcp_filesystem_path(tool_input, project_dir, framework, upstream_repo):
    """MCP filesystem write/edit on a single `path` field.

    Added 2026-05-09 (team-topologies dogfood F6 follow-up): the
    Edit/Write/MultiEdit guard was bypassable via mcp__filesystem__write_file
    and mcp__filesystem__edit_file because the matcher only covered the
    Anthropic-built tools. This handler closes the gap for the filesystem MCP.
    Other MCP servers with write capability (mcp__github__create_or_update_file,
    mcp__filesystem__create_directory) remain uncovered — extend handlers and
    the hooks.json matcher together when they become a real bypass risk.
    """
    file_path = tool_input.get("path", "")
    if not file_path:
        return  # no path → fail open
    matched, rule = is_framework(file_path, project_dir, framework)
    if matched:
        rel_path = os.path.relpath(os.path.abspath(file_path), project_dir)
        _deny_file_edit(rel_path, rule, upstream_repo)


def _handle_mcp_filesystem_move(tool_input, project_dir, framework, upstream_repo):
    """MCP filesystem move with `source` + `destination`.

    Move into framework path = framework write; move out of framework path =
    framework deletion. Both classify as framework-modifying.
    """
    for field in ("source", "destination"):
        path = tool_input.get(field, "")
        if not path:
            continue
        matched, rule = is_framework(path, project_dir, framework)
        if matched:
            rel_path = os.path.relpath(os.path.abspath(path), project_dir)
            _deny_file_edit(rel_path, rule, upstream_repo)


def _load_state(state_file):
    """Read the upstream-config state file. Returns dict or None on error/disabled."""
    try:
        with open(state_file) as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not state.get("active", True):
        return None
    return state


def _load_input():
    """Read tool input JSON from stdin. Returns dict or None on parse error."""
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return None


EXPECTED_ARGV_LEN = 3  # script_name + state_file + project_dir


def main():
    if len(sys.argv) != EXPECTED_ARGV_LEN:
        sys.exit(0)  # misconfigured → fail open

    state_file = sys.argv[1]
    project_dir = sys.argv[2]

    state = _load_state(state_file)
    if state is None:
        sys.exit(0)  # missing/malformed/disabled → fail open
    upstream_repo = state.get("upstream_repo", "the upstream framework repo")

    input_data = _load_input()
    if input_data is None:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    manifest_path = Path(project_dir) / ".claude" / "manifest.yml"
    framework = parse_manifest(manifest_path)

    handlers = {
        "Write":                          _handle_file_edit,
        "Edit":                           _handle_file_edit,
        "MultiEdit":                      _handle_file_edit,
        "Bash":                           _handle_bash,
        "mcp__filesystem__write_file":    _handle_mcp_filesystem_path,
        "mcp__filesystem__edit_file":     _handle_mcp_filesystem_path,
        "mcp__filesystem__move_file":     _handle_mcp_filesystem_move,
    }
    handler = handlers.get(tool_name)
    if handler is not None:
        handler(tool_input, project_dir, framework, upstream_repo)

    sys.exit(0)


if __name__ == "__main__":
    main()
