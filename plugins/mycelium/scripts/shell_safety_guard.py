#!/usr/bin/env python3
"""Warn on shell constructs whose exit status or quoting silently misleads.

WHY THIS IS A HOOK AND NOT A NOTE (dogfood 2026-08-03). Three of these traps
have their own memory files in this project, written after earlier incidents.
All three were walked into anyway, in a single session, **eight times**, and one
produced a WRONG ANSWER TO THE OPERATOR: `which opencode | head -1; echo $?`
reported `head`'s status, so the agent stated a tool was not installed when the
binary was merely absent from PATH. Per the Lopopolo reframe this project runs
on — "every interaction is a failure of the harness to provide enough context;
fix one layer up" — a correction that recurs against an existing note needs a
mechanism, not a better note. A note is read once at session start and decays. A
PreToolUse hook fires on the exact command, every time.

IT WARNS, IT DOES NOT BLOCK. Every pattern here has legitimate uses, and a guard
that blocks real work gets disabled — which is how a guard dies. `additionalContext`
puts the warning in front of the agent at the moment of use and lets it proceed.

WHAT IT CHECKS, each anchored to a documented contract rather than a preference:

  1. `$?` after a pipeline. POSIX and bash define `$?` as the exit status of the
     LAST command in a pipeline, so `cmd | head; echo $?` reports head. The
     documented remedy is `${PIPESTATUS[0]}` in bash and `${pipestatus[1]}` in
     zsh (lowercase, 1-indexed) — suppressed when either is present, since
     then the author knows. Naming only the bash form was the shipped bug:
     this project's shell is zsh, where `${PIPESTATUS[0]}` expands to the
     empty string, so the advice silently did not work in the environment it
     was written for. Advice that fails quietly is worse than none, because
     it reads as handled.
     ShellCheck SC2181 covers the adjacent "check exit code directly" case.

  2. Backticks. ShellCheck SC2006: "Use $(...) notation instead of legacy
     backticks". Beyond style, backticks inside a DOUBLE-QUOTED string are
     command substitution, so a markdown code span in a commit message becomes
     an execution attempt — which is exactly how instance seven happened:
     `git commit -m "... `| head` ..."` died with `parse error near '|'`.

  3. `grep` / `pgrep` gating an `&&` chain. grep(1): "Exit status is 0 if any
     line is selected, 1 if no lines were selected". Zero matches is frequently
     the DESIRED answer, so `grep -c X f && echo done` silently skips the echo.

WHAT IT DELIBERATELY DOES NOT CHECK, stated because a guard that overstates its
reach is worse than none. **cwd persistence** — a `cd` in one Bash call leaking
into the next — is the fourth trap in this family and bit twice the same session.
It is invisible here: a PreToolUse hook sees ONE command and cannot know what the
next call assumes. Catching it needs cross-invocation state, which is a different
mechanism and is not pretended at.

Contract: exit 0 silent = nothing to say. exit 0 + JSON additionalContext = warn.
Never denies. Fails open on unparseable input — a guard that breaks the Bash tool
is worse than the traps it catches.
"""

from __future__ import annotations

import json
import re
import sys

#: (id, compiled test, message). Each returns True when the trap is PRESENT.
_BACKTICK = re.compile(r"`")
#: A QUOTED heredoc (<<'EOF' / <<"EOF") disables expansion, so backticks inside
#: one are inert text — and a quoted heredoc is exactly what the backtick message
#: below tells the author to use. Warning on it is the same defect already fixed
#: for PIPESTATUS above: telling people who have applied the remedy to apply it.
#: An UNQUOTED heredoc (<<EOF) still expands, so it is deliberately not stripped.
_QUOTED_HEREDOC_START = re.compile(r"<<-?\s*(['\"])([A-Za-z_][A-Za-z0-9_]*)\1")


def _strip_quoted_heredoc_bodies(command: str) -> str:
    """Return `command` with the bodies of quoted heredocs removed.

    Only the BODY is removed; the redirection operator itself stays, so a trap
    written on the same line as the heredoc opener is still seen.
    """
    out, pos = [], 0
    for m in _QUOTED_HEREDOC_START.finditer(command):
        if m.start() < pos:
            continue
        delim = m.group(2)
        body_start = command.find("\n", m.end())
        if body_start == -1:
            continue
        end = re.compile(r"^\s*" + re.escape(delim) + r"\s*$", re.MULTILINE).search(
            command, body_start + 1
        )
        stop = end.start() if end else len(command)
        out.append(command[pos:body_start])
        pos = stop
    out.append(command[pos:])
    return "".join(out)
_PIPE = re.compile(r"(?<!\|)\|(?!\|)")          # a real pipe, not ||
_DOLLAR_STATUS = re.compile(r"\$\?")
#: Case-INSENSITIVE: bash spells it PIPESTATUS, zsh spells it pipestatus.
#: A case-sensitive test warned people who had already applied the remedy,
#: in the shell this project actually runs.
_PIPESTATUS = re.compile(r"pipestatus", re.IGNORECASE)
_GREP_AND = re.compile(r"\b(grep|pgrep|rg)\b[^\n;]*?&&")


def findings(command: str) -> list[str]:
    """Return a warning per trap present. Empty list means nothing to say."""
    out: list[str] = []

    # 1. $? after a pipeline, without PIPESTATUS.
    if _DOLLAR_STATUS.search(command) and _PIPE.search(command) \
            and not _PIPESTATUS.search(command):
        pipe_at = _PIPE.search(command).start()
        status_at = _DOLLAR_STATUS.search(command).start()
        if status_at > pipe_at:
            out.append(
                "`$?` appears after a pipeline. POSIX defines it as the exit "
                "status of the LAST command in the pipeline, so it reports the "
                "tail (often `head`/`tail`/`grep`), not the command you care "
                "about. In bash use `${PIPESTATUS[0]}`; in ZSH that array is "
                "`$pipestatus` and it is 1-INDEXED, so the same slot is "
                "`${pipestatus[1]}`. Or drop the pipe."
            )

    # 2. Backticks — outside quoted heredocs, whose contents do not expand.
    if _BACKTICK.search(_strip_quoted_heredoc_bodies(command)):
        out.append(
            "Backticks present. ShellCheck SC2006 says use `$(...)`; more "
            "importantly, backticks inside a DOUBLE-QUOTED string are command "
            "substitution, so a markdown code span in a commit message or "
            "heredoc-less string gets executed. For text containing backticks, "
            "`$`, or pipes, use a QUOTED heredoc (<<'EOF') rather than -m \"...\" "
            'or -c "...".'
        )

    # 3. grep gating an && chain.
    if _GREP_AND.search(command):
        out.append(
            "`grep` gates an `&&` chain. grep(1) exits 1 when NOTHING matched, "
            "and zero matches is often the desired answer, so the right-hand "
            "side is skipped silently. Test the output rather than the status, "
            "or append `|| true`."
        )

    return out


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:                      # noqa: BLE001 — must never break Bash
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    warnings = findings(command)
    if not warnings:
        return 0

    body = "MYCELIUM SHELL-SAFETY WARNING (the command still runs):\n" + "\n".join(
        f"  - {w}" for w in warnings
    ) + (
        "\n  These are warnings, not blocks. Each of these traps has produced a "
        "wrong answer in this project before — see corrections.md, "
        "verification-hygiene class."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": body,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
