#!/usr/bin/env python3
"""Outreach started without opening the channel map.

WHAT THIS CATCHES. A write to `.claude/canvas/human-tasks.yml` that starts an `outreach` task
(an open task of that type whose id the write contains) while `.claude/canvas/go-to-market.yml`
exists and has not been opened in this session, by the read log
(`.claude/state/read-log.jsonl`, written by hooks/read-log.sh; a Bash read logged as inferred
counts). Said at the write, which is the moment the outreach starts. Advisory: it never blocks.

WHY (founder ruling 2026-11-12 on every-hook-is-a-script-so-nothing-in-the-loop-can-check-sense,
"Scripts for two cases"). A retrodiction over the corrections the founder caught by hand, scored
blind by two readers, found two that a deterministic script reading existing files could have
caught. This is the second. Dogfood 2026-08-25: a whole session went into user acquisition (1:1
lists, artifact sweeps, other forges, issue trackers) without once opening go-to-market.yml,
whose channel ledger already held 18 of 24 standard channels with decisions attached. The rule
existed as prose (`/mycelium:handoff` step 1b: read the channel map before naming a channel);
nothing checked it at the moment it applied.

WHAT IT CANNOT SEE. Acquisition work that never writes an outreach task, an edit that changes an
existing task's status without its id in the new text, and a read made outside the hooks (no
read-log row). A read is not understanding: opening the file satisfies this check, and stating
what the ledger shows worked is still step 1b's job. With no session id in the payload it cannot
tell this session's reads from earlier ones, so it stays silent.

Reads the PostToolUse payload on stdin; prints one line, or nothing. Fails open: any error prints
nothing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TASKS = "/.claude/canvas/human-tasks.yml"
CHANNEL_MAP = "/.claude/canvas/go-to-market.yml"
#: An outreach task in one of these has not been sent yet: the write is its start.
STARTING = {"pending", "in_progress"}


def written_text(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    parts = [ti.get("content"), ti.get("new_string")]
    parts += [e.get("new_string") for e in ti.get("edits") or [] if isinstance(e, dict)]
    return "\n".join(str(p) for p in parts if p)


def channel_map_read(project: Path, session_id: str) -> bool:
    """Whether this session's read log shows go-to-market.yml opened."""
    log = project / ".claude" / "state" / "read-log.jsonl"
    if not log.is_file():
        return False
    with log.open(errors="replace") as fh:
        for line in fh:
            if "go-to-market.yml" not in line or session_id not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            path = str(row.get("file_path") or "")
            if row.get("session_id") == session_id and (
                    path.endswith(CHANNEL_MAP) or path == CHANNEL_MAP.lstrip("/")):
                return True
    return False


def starting_outreach(tasks_doc, written: str) -> list[str]:
    """Ids of open outreach tasks, not yet sent, that this write contains."""
    tasks = tasks_doc.get("pending_tasks") if isinstance(tasks_doc, dict) else None
    out = []
    for t in tasks or []:
        if not isinstance(t, dict) or t.get("type") != "outreach":
            continue
        tid = str(t.get("id") or "")
        if (tid and str(t.get("status") or "") in STARTING
                and re.search(rf"(?<![\w-]){re.escape(tid)}(?![\w-])", written)):
            out.append(tid)
    return out


def findings(project: Path, session_id: str, written: str) -> list[str]:
    if "outreach" not in written or not session_id:
        return []
    if not (project / CHANNEL_MAP.lstrip("/")).is_file() or channel_map_read(project, session_id):
        return []
    import yaml  # noqa: PLC0415 -- only once every cheaper test has passed
    doc = yaml.safe_load((project / TASKS.lstrip("/")).read_text()) or {}
    return starting_outreach(doc, written)


def tasks_path(path: str) -> Path | None:
    """The human-tasks file a write touched, absolute, or None when the write is not to it."""
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / p
    return p if p.as_posix().endswith(TASKS) else None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        target = tasks_path(str((payload.get("tool_input") or {}).get("file_path") or ""))
        if target is None:
            return 0
        project = Path(target.as_posix()[: -len(TASKS)] or "/")
        ids = findings(project, str(payload.get("session_id") or ""), written_text(payload))
    except Exception:  # noqa: BLE001 -- an advisory hook helper fails open, silently
        return 0
    if ids:
        print("CHANNEL MAP NOT READ THIS SESSION: this write starts outreach "
              f"{', '.join(ids)}, and .claude/canvas/go-to-market.yml has not been opened in "
              "this session. Before naming a channel, read its channel_intelligence and say what "
              "the record shows worked and what was ruled out, with the entry's date; posture "
              "rulings recorded there bind the outreach (/mycelium:handoff step 1b).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
