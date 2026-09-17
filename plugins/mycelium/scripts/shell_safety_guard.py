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

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

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


def _blank_quoted(command: str) -> str:
    """Return `command` with quoted-string BODIES replaced by spaces.

    A `|` inside '...' or "..." is an argument, not a pipeline: `grep "a\\|b"`,
    `jq '.x[] | select(.y)'`, `echo "a|b"`. Offsets are preserved so positional
    comparisons against the original string stay valid.

    Measured on 12,260 real Bash commands from dogfood session transcripts
    (2026-08-30): quoted pipes were the single largest source of rule-1 false
    positives, and stripping heredoc bodies alone removed only 13% of fires.
    """
    out, i, n = list(command), 0, len(command)
    while i < n:
        ch = command[i]
        if ch in "'\"":
            j = i + 1
            while j < n and command[j] != ch:
                if command[j] == "\\":
                    j += 1
                j += 1
            for k in range(i + 1, min(j, n)):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


_PIPE = re.compile(r"(?<!\|)\|(?!\|)")          # a real pipe, not ||
_DOLLAR_STATUS = re.compile(r"\$\?")
#: Case-INSENSITIVE: bash spells it PIPESTATUS, zsh spells it pipestatus.
#: A case-sensitive test warned people who had already applied the remedy,
#: in the shell this project actually runs.
_PIPESTATUS = re.compile(r"pipestatus", re.IGNORECASE)
_GREP_AND = re.compile(r"\b(grep|pgrep|rg)\b[^\n;]*?&&")
#: Rule 4 (v0.208.0). A step that writes a durable project file, followed later in the same
#: command by `git commit` or `git push`, with a newline or `;` between them: a failed write
#: does not stop the commit. Twice on 2026-09-09 a canvas-writing python heredoc exited 1 and
#: the decision-log append, the commit and the push after it still ran, so origin received a
#: log entry describing writes that had not happened; on the second occasion `set -e` at the
#: top of the command did not stop the chain under the agent's Bash tool.
_DURABLE_PATH = re.compile(r"\.claude/(?:canvas|diamonds|harness|memory)/")
_WRITE_SHAPE = re.compile(
    r"(?:>>?|\bsed\s+-i|\btee\b|\bpython3?\s+-(?:\s|$|c\b)|<<-?\s*['\"]?\w+|safe_replace|"
    r"\.write_text\(|open\([^)]*['\"][wa]['\"]\))"
)
_GIT_LANDS = re.compile(r"\bgit\s+(?:commit|push)\b")

# Rule 5: a scripted multi-file text edit that can half-apply.
_PY_REPLACE = re.compile(r"\.replace\(")
_EDIT_HELPER = re.compile(r"safe_replace|apply_edits|write_checked")
_PY_OPEN_WRITE = re.compile(r"open\(\s*([A-Za-z_][\w.]*|['\"][^'\"]+['\"])\s*,\s*['\"][wa]['\"]")
_PY_WRITE_TEXT = re.compile(r"([A-Za-z_][\w.]*|Path\([^)]*\))\.write_text\(")
_PY_ANCHOR_CHECK = re.compile(r"\bassert\b|\.count\(")


def _half_applying_edit(command: str) -> bool:
    """Replaces text, writes two or more DISTINCT files, skips the helper, and either checks
    an anchor after the first write or checks none.

    NARROWED BEFORE IT SHIPPED, 2026-09-17, over 14,419 real Bash commands from dogfood
    transcripts. The contract's HARD RULE names safe_replace.py for any scripted edit of
    more than one file or anchor; 1,960 commands were replace-and-write scripts and 123
    used the helper. A rule warning on the other 1,626 would fire on 11% of all commands,
    which is a nag, and most of them are one file with every anchor asserted before the
    write: the rule's substance, kept by hand. What the rule exists to prevent is a tree
    left half-edited, and that needs two files and a check that can fail after the first
    one is written. That shape: 299 commands, 2.1%.
    """
    if not _PY_REPLACE.search(command) or _EDIT_HELPER.search(command):
        return False
    writes = list(_PY_OPEN_WRITE.finditer(command)) + list(_PY_WRITE_TEXT.finditer(command))
    if len({m.group(1) for m in writes}) < 2:  # noqa: PLR2004 -- two files is the rule's own threshold
        return False
    first_write = min(m.start() for m in writes)
    checks = [m.start() for m in _PY_ANCHOR_CHECK.finditer(command)]
    return not checks or max(checks) > first_write


def _raw_steps(command: str) -> list[str]:
    """Split a command into steps at `;` and newlines OUTSIDE quotes and quoted-heredoc bodies.

    Each step keeps its own heredoc body, so a path written from inside a python heredoc
    belongs to the step that opened the heredoc. Steps joined by `&&` or `||` are one step:
    that join is the gating the rule asks for.
    """
    steps, start, i, n = [], 0, 0, len(command)
    while i < n:
        ch = command[i]
        if ch in "'\"":
            j = i + 1
            while j < n and command[j] != ch:
                j += 2 if command[j] == "\\" else 1
            i = j + 1
            continue
        m = _QUOTED_HEREDOC_START.match(command, i)
        if m:
            body_start = command.find("\n", m.end())
            if body_start == -1:
                break
            end = re.compile(r"^\s*" + re.escape(m.group(2)) + r"\s*$", re.MULTILINE).search(
                command, body_start + 1)
            i = end.end() if end else n
            continue
        if ch in ";\n":
            steps.append(command[start:i])
            start = i + 1
        i += 1
    steps.append(command[start:])
    return [s for s in steps if s.strip()]


def _ungated_commit(command: str) -> bool:
    """True when a durable write precedes a commit or push in a LATER step."""
    write_seen = False
    for step in _raw_steps(command):
        if write_seen and _GIT_LANDS.search(_blank_quoted(step)):
            return True
        if _DURABLE_PATH.search(step) and _WRITE_SHAPE.search(step):
            write_seen = True
    return False


def _status_reads_a_pipeline(base: str, scan: str) -> bool:
    """True when a `$?` in `base` actually reports a pipeline's exit status.

    `base` is the command with quoted-heredoc bodies stripped; `scan` is `base`
    with quoted-string bodies blanked. They are the same length, so offsets in
    one index the other — `$?` is read from `base` (where it is still visible)
    while pipes and command separators are read from `scan` (where a quoted `|`
    or `;` cannot masquerade as shell syntax).

    The test is adjacency: `$?` reports the previous SIMPLE COMMAND, so it names
    a pipeline only when the immediately preceding segment contained one.
    `a | b; echo $?` warns. `a > log; echo $?` does not, even where some earlier
    line piped — that `$?` is reporting the redirect, correctly.
    """
    if len(base) != len(scan):  # defensive: offsets must index both
        return False
    bounds = [0] + [m.start() for m in re.finditer(r"[;\n]", scan)] + [len(base)]
    prev_piped = False
    for lo, hi in pairwise(bounds):
        if _DOLLAR_STATUS.search(base[lo:hi]) and prev_piped:
            return True
        if base[lo:hi].strip():
            prev_piped = bool(_PIPE.search(scan[lo:hi]))
    return False


def findings(command: str) -> list[str]:
    """Return a warning per trap present. Empty list means nothing to say."""
    out: list[str] = []

    # 1. $? after a pipeline, without PIPESTATUS.
    #
    # NARROWED 2026-08-30. This rule used to ask only "is there a `$?` somewhere
    # after some `|`?", over the RAW command. Measured over 12,260 real Bash
    # commands from dogfood session transcripts, that fired 223 times with an
    # effective-false-positive rate of 53-60% — five to six times outside
    # Tricorder's <10% bar for an advisory check (ICSE 2015; "effective false
    # positive" = any report the user declines to act on). Two things were wrong:
    #   * the `|` was often inside a quoted string or a quoted heredoc, so no
    #     pipeline existed at all — `grep "a\|b"`, `jq '.a | .b'`;
    #   * the `$?` usually belonged to a DIFFERENT command, typically one using
    #     a redirect: `cmd > log 2>&1; echo "rc=$?"` is correct and was warned.
    # So the pipe is now looked for only outside quotes and quoted heredocs, and
    # the `$?` must sit in the segment IMMEDIATELY following the piped one —
    # which is the only shape where `$?` actually reports a pipeline.
    # Removes 135 of 223 fires (61%) and keeps all 88 true positives.
    if _DOLLAR_STATUS.search(command) and not _PIPESTATUS.search(command):
        base = _strip_quoted_heredoc_bodies(command)
        if _status_reads_a_pipeline(base, _blank_quoted(base)):
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

    # 4. A durable write, then a commit or push, with nothing gating the commit on the write.
    if _GIT_LANDS.search(command) and _DURABLE_PATH.search(command) and _ungated_commit(command):
        out.append(
            "A write to a canvas, diamond, harness or memory file precedes `git commit` "
            "or `git push` in this command with a newline or `;` between them: an "
            "ungated commit. If the write fails, the commit and push still run, and "
            "origin receives a record of a change that did not happen (twice on "
            "2026-09-09; `set -e` did not stop the chain under this tool). Chain every "
            "step from the first write to the push with `&&`, or commit in a separate "
            "command after reading the write's output."
        )

    # 5. A multi-file scripted edit that can half-apply. See _half_applying_edit for the
    # measurement that set its scope.
    if _half_applying_edit(command):
        out.append(
            "This script replaces text and writes two or more files without "
            "`safe_replace.py`, and an anchor check runs after the first write or not at "
            "all. If a later anchor fails, the earlier files are already written and the "
            "tree is in a state nobody described (agent-operating-contract, scripted "
            "multi-file edits, HARD RULE). Pass the edits to "
            '`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/safe_replace.py" --spec edits.json` '
            "(try `--dry-run` first), or import `apply_edits`: every anchor is validated "
            "before any file is touched."
        )

    return out



# Opt-in trigger recording (v0.224.0). OFF unless MYCELIUM_LEDGER_TRIGGER=on.
_TRIGGER_CHARS = 200
_SECRET_SHAPES = (
    # provider-shaped tokens
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}"
               r"|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,})"),
    # Authorization headers
    re.compile(r"(?i)\b((?:bearer|basic|token)\s+)[A-Za-z0-9._~+/=-]{8,}"),
    # NAME=value where the name says it is a secret
    re.compile(r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|CREDENTIALS?)[A-Z0-9_]*=)\S+"),
    # --password x / --token=x style flags
    re.compile(r"(?i)(--?(?:password|passwd|token|secret|api-?key)[= ])\S+"),
    # credentials inside a URL
    re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@"),
)


def _masked_trigger(command: str) -> str:
    """First _TRIGGER_CHARS of the command with obvious secret shapes replaced.

    Masking is BEST EFFORT and says so: it knows token prefixes, auth headers, secret-named
    assignments and flags, and URL credentials. A secret in none of those shapes is recorded
    as typed. That is why this is opt-in and off by default; it is for a maintainer scoring
    their own guard. The ledger lives under .claude/state/, which setup does not git-ignore.
    """
    text = command
    for pat in _SECRET_SHAPES:
        text = pat.sub(lambda m: (m.group(1) if m.lastindex else "") + "<masked>", text)
    return " ".join(text.split())[:_TRIGGER_CHARS]


def _log(hook: str, fires: int, first_match: str, signature: str, command: str = "") -> None:
    """Append one line per fire so the action rate and the OVERRIDE rate are computable.

    Two rules make this part of the ship rather than a nice-to-have.
    `opportunities.yml#sol-048a`: a guard whose ACTION RATE stays near zero is narrowed
    or retired, not left running — unenforceable without an instrument. And a session on
    2026-08-22 measured the other half: this guard fired correctly, repeatedly, was read
    past every time, and the error it described happened anyway. **That override was only
    visible in a transcript, and transcripts die.**

    `signature` is what makes overrides countable without anyone self-reporting: the same
    signature firing again in the same session is an agent that was warned and carried on.
    A corrected agent does not re-trigger the same rule.

    Records WHAT fired, never the full input — enough to compute a rate, not enough to be
    a transcript. Silent on every failure: an instrument that breaks a session is worse
    than an instrument with a gap.

    OPT-IN EXCEPTION (v0.224.0): with MYCELIUM_LEDGER_TRIGGER=on the row also carries
    `trigger`, the first 200 characters of the command with obvious secrets masked. A rate
    says how often a rule fires; it cannot say whether a fire was right, and both times
    this guard was narrowed (2026-08-30, 2026-09-17) the false-positive numbers had to be
    rebuilt from session transcripts, which rotate away. Default stays a rate: commands
    can carry tokens and names, and the default is what other people's projects get.
    """
    try:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "state"
        root.mkdir(parents=True, exist_ok=True)
        row = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "hook": hook,
            "fires": fires,
            "signature": signature,
            "first_match": first_match[:120],
        }
        if command and os.environ.get("MYCELIUM_LEDGER_TRIGGER", "").lower() == "on":
            row["trigger"] = _masked_trigger(command)
        with (root / f"{hook}-log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001, S110 — never break a tool call over telemetry
        pass


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
    signature = hashlib.sha256("|".join(sorted(warnings)).encode()).hexdigest()[:10]
    _log("shell-safety-guard", len(warnings), warnings[0], signature, command)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": body,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
