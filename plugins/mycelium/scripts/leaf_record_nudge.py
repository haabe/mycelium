#!/usr/bin/env python3
"""The record a leaf owes, said at the write that creates the gap (v0.287.0).

Two validator warnings on the dogfood canvas (2026-09-29) had one source: solution leaves written
straight into opportunities.yml by an agent, outside the skills that ask for the record. 23
leaves reached a terminal status (15 of them `shipped`) with no cycle-history row, and 7 new
solutions carried no purpose_stance; the validator named each days or weeks later, when the
context that could fill it was gone. This runs on the write itself, for the leaves that write
touched, and names what each one still owes. Advisory: it never blocks.

Reads the PostToolUse payload on stdin; prints one line, or nothing.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_SOL = re.compile(r"\bsol-[0-9]+[a-z0-9-]*\b")


def written_text(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    parts = [ti.get("content"), ti.get("new_string")]
    parts += [e.get("new_string") for e in ti.get("edits") or [] if isinstance(e, dict)]
    return "\n".join(str(p) for p in parts if p)


def owed(canvas: Path, ids: set[str]) -> list[str]:
    """What each touched leaf still owes: a cycle row, a purpose stance."""
    out = []
    try:
        import check_cycle_recording as ccr  # noqa: PLC0415 — sibling script, loaded on use
        for f in ccr.terminal_leaf_without_cycle_findings(canvas):
            m = re.match(r"opportunities\.yml#(\S+): status `([^`]*)`", f)
            if m and m.group(1) in ids:
                out.append(f"{m.group(1)} is `{m.group(2)}` with no cycle-history.yml row: write "
                           "it now, while the dates and the outcome are in front of you "
                           "(engine/cycle-learning.md)")
    except Exception as exc:  # noqa: BLE001 — SPEAKS: an advisory that cannot look says so
        out.append(f"(cycle-record check could not run: {type(exc).__name__})")
    try:
        import check_purpose_stance as cps  # noqa: PLC0415 — sibling script, loaded on use
        for f in cps.purpose_stance_findings(canvas, None):
            sid = f.split(" ", 1)[0]
            if sid in ids and "no purpose_stance" in f:
                out.append(f"{sid} has no purpose_stance against the binding purpose properties: "
                           "write it now (written_by: agent, confirmed_by: null)")
    except Exception as exc:  # noqa: BLE001 — SPEAKS: an advisory that cannot look says so
        out.append(f"(purpose-stance check could not run: {type(exc).__name__})")
    return out


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0  # not a hook payload: nothing was written, so nothing is owed
    path = str((payload.get("tool_input") or {}).get("file_path") or "")
    if not path.endswith(".claude/canvas/opportunities.yml"):
        return 0
    ids = set(_SOL.findall(written_text(payload)))
    if not ids:
        return 0
    canvas = Path(path).parent
    lines = owed(canvas, ids)
    if lines:
        print("LEAF RECORDS OWED BY THIS WRITE: " + "; ".join(lines) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
