#!/usr/bin/env python3
"""One line per reflexion firing, without the command or its output (v0.318.0).

WHY. reflexion-gate.sh logged every project-relevant command failure to
.claude/state/reflexion-log.jsonl with the first 160 characters of the command and 200 of its
error output, unmasked, in every project the plugin ran in. A password typed into a command
that failed ended up in a plain file, and nothing kept that file out of a commit where setup
never ran. Found by Anthropic's plugin directory review of v0.317.4 (2026-10-09); PRIVACY.md
said commands are kept only when the user opts in.

WHAT A ROW HOLDS NOW. `ts`, `tool`, `exit_code`, `program` (the command's first word, when it is a
plain program name: `grep`, `git`, `./build.sh`), and `suppressed` (why a documented non-failure
such as grep exit 1 is not a learning). That is everything reconcile_reflexions.py counts with.
With MYCELIUM_LEDGER_TRIGGER=on, the same opt-in the shell-safety ledger uses, a row also keeps
`command_head` and `stderr_head`, masked by _secret_mask.py, and `masked: true`.

SCRUB. `scrub` removes `command_head` and `stderr_head` from every row that does not carry
`masked: true`, i.e. every row an earlier version wrote. session-start.sh runs it, so a project
upgraded from an earlier version stops holding the old text at its next session.

Usage (the hook passes its PostToolUseFailure payload on stdin, never the command as an
argument, which `ps` would show):
  reflexion_record.py record --state-dir DIR [--suppressed REASON] < payload.json
  reflexion_record.py scrub --state-dir DIR
Exit 0 always: telemetry never breaks a tool call.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _secret_mask
import _state_dir

LOG_NAME = "reflexion-log.jsonl"
TEXT_FIELDS = ("command_head", "stderr_head")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PLAIN = re.compile(r"^[A-Za-z0-9_./+-]{1,40}$")


def program_of(command: str) -> str | None:
    """The first word of the command, skipping VAR=value assignments, if it is a plain name.

    `PGPASSWORD=x psql ...` gives `psql`; a first word with quotes, `$`, `=` or other
    punctuation gives None, so nothing typed after the program name is ever kept.
    """
    for word in (command or "").split():
        if _ASSIGNMENT.match(word):
            continue
        if not _PLAIN.match(word):
            return None
        return word.rsplit("/", 1)[-1] or None
    return None


def build_row(payload: dict, suppressed: str = "", environ=os.environ) -> dict:
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    exit_code = response.get("exit_code") if isinstance(response, dict) else None
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": "Bash",
        "exit_code": exit_code,
        "program": program_of(command),
    }
    if suppressed:
        # A suppressed row stays in the log WITH its reason, so the classifier stays auditable.
        row["suppressed"] = suppressed
    if _secret_mask.opted_in(environ):
        stderr = (response.get("stderr") or "") if isinstance(response, dict) else ""
        row["command_head"] = _secret_mask.mask(command, 160)
        row["stderr_head"] = _secret_mask.mask(stderr, 200) or None
        row["masked"] = True
    return row


def record(state_dir: Path, payload: dict, suppressed: str = "", environ=os.environ) -> dict:
    row = build_row(payload, suppressed, environ)
    try:
        _state_dir.ensure(state_dir)
        with (state_dir / LOG_NAME).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return row


def scrub(state_dir: Path) -> int:
    """Drop the text fields from rows not written masked; return how many rows changed."""
    path = state_dir / LOG_NAME
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return 0
    changed, out = 0, []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            out.append(line)  # a torn line is kept as found; the reader already skips it
            continue
        if isinstance(row, dict) and not row.get("masked") and any(k in row for k in TEXT_FIELDS):
            for k in TEXT_FIELDS:
                row.pop(k, None)
            changed += 1
            out.append(json.dumps(row) + "\n")
        else:
            out.append(line)
    if changed:
        fd, tmp = tempfile.mkstemp(dir=state_dir, prefix=".reflexion-log.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(out)
        os.replace(tmp, path)
    return changed


def main(argv: list[str] | None = None, stdin=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("mode", choices=("record", "scrub"))
    ap.add_argument("--state-dir", required=True, type=Path)
    ap.add_argument("--suppressed", default="")
    args = ap.parse_args(argv)
    try:
        if args.mode == "scrub":
            scrub(args.state_dir)
            return 0
        try:
            payload = json.loads((stdin or sys.stdin).read() or "{}")
        except ValueError:
            payload = {}
        record(args.state_dir, payload if isinstance(payload, dict) else {}, args.suppressed)
    except Exception:  # noqa: BLE001, S110 — never break a tool call over telemetry
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
