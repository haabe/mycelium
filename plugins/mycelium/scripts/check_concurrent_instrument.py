#!/usr/bin/env python3
"""An instrument frozen for a diamond while another instrument on that diamond is still in flight.

WHAT THIS CATCHES. Writing an assumption-test instrument (`.claude/evals/assumption-tests/*.md`)
for diamond X while a human task in `human-tasks.yml` carries `diamond_ref: X` and is still in
flight (`in_progress` or `waiting`: started, not scored). Said at the write, which is the moment the
instrument is designed. Advisory: it never blocks.

WHY (founder ruling 2026-11-12 on every-hook-is-a-script-so-nothing-in-the-loop-can-check-sense,
"Scripts for two cases"). A retrodiction over the corrections the founder caught by hand, scored
blind by two readers, found two that a deterministic script reading existing files could have
caught. This is the first. Dogfood 2026-08-21: a session ran a sweep for `l1-strategy` while an
assumption test for the same diamond was in flight (five replies sent, `diamond_ref:
l1-strategy`, horizon 2026-08-30), and that test existed because the sweep's design had already
failed. The fork offered was built from the diamond's blockers; `human-tasks.yml` was never
opened, so the in-flight instrument was invisible to the design step. Both fields existed and
nothing read them together.

HOW THE INSTRUMENT NAMES ITS DIAMOND. `diamond_ref:` in the instrument's header
(`/mycelium:assumption-test` Step 5b), or a `diamonds/active.yml#<id>` anchor anywhere in the file
(the `[target -> <file>#<anchor>]` tags Step 2 asks for). An instrument that names neither is not
checked: nothing says which diamond it serves.

WHEN IT STAYS SILENT. The instrument is scored, void or not an instrument; or it names the
in-flight task's id, which means it is that task's own instrument, or the reason for running both
is written down where the next reader will find it. Naming the task is the way out the note offers.

Reads the PostToolUse payload on stdin; prints one line, or nothing. Fails open: any error prints
nothing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

INSTRUMENT_DIR = "/.claude/evals/assumption-tests/"
#: Started and not scored. `pending` has not started; `watching` owes nothing.
IN_FLIGHT = {"in_progress", "waiting"}
#: Instrument statuses that are not a live design.
NOT_LIVE = {"scored", "void", "not-an-instrument"}
_ANCHOR = re.compile(r"diamonds/active\.yml#([A-Za-z0-9][\w-]*)")


def _clean(value) -> str:
    """A header value without its inline comment or quotes."""
    return str(value or "").split(" #", 1)[0].strip().strip("\"'")


def _header(text: str) -> dict:
    try:
        import check_instrument_contract as cic  # noqa: PLC0415 -- sibling, loaded on use
    except ImportError:
        return {}
    return cic._frontmatter(text) or {}  # noqa: SLF001 -- the one parser for this header; a copy would drift


def instrument_diamonds(text: str) -> tuple[set[str], str]:
    """(diamond ids the instrument names, its status)."""
    head = _header(text)
    ids = {x.strip() for x in _clean(head.get("diamond_ref")).split(",") if x.strip()}
    ids |= set(_ANCHOR.findall(text))
    return ids, _clean(head.get("status")).lower()


def in_flight_tasks(tasks_doc, diamonds: set[str]) -> list[dict]:
    """Open human tasks that are started, not scored, and carry one of these diamond refs."""
    tasks = tasks_doc.get("pending_tasks") if isinstance(tasks_doc, dict) else None
    return [t for t in tasks or [] if isinstance(t, dict)
            and str(t.get("status") or "") in IN_FLIGHT
            and str(t.get("diamond_ref") or "").strip() in diamonds]


def findings(project_dir: Path, text: str) -> list[str]:
    diamonds, status = instrument_diamonds(text)
    if not diamonds or status in NOT_LIVE:
        return []
    tasks_path = project_dir / ".claude" / "canvas" / "human-tasks.yml"
    if not tasks_path.is_file():
        return []
    import yaml  # noqa: PLC0415 -- only once an instrument names a diamond
    doc = yaml.safe_load(tasks_path.read_text()) or {}
    out = []
    for t in in_flight_tasks(doc, diamonds):
        tid = str(t.get("id") or "")
        if tid and re.search(rf"(?<![\w-]){re.escape(tid)}(?![\w-])", text):
            continue
        horizon = f", horizon {t['horizon']}" if t.get("horizon") else ""
        objective = " ".join(str(t.get("objective") or "").split())[:140]
        out.append(f"{tid or '(no id)'} ({t.get('status')}{horizon}, diamond_ref "
                   f"{t.get('diamond_ref')}): {objective}")
    return out


def instrument_path(path: str) -> Path | None:
    """The instrument a write touched, absolute, or None when the write is not to one."""
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / p
    return p if INSTRUMENT_DIR in p.as_posix() and p.suffix == ".md" else None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        target = instrument_path(str((payload.get("tool_input") or {}).get("file_path") or ""))
        if target is None:
            return 0
        project = Path(target.as_posix().split(INSTRUMENT_DIR, 1)[0] or "/")
        rows = findings(project, target.read_text())
    except Exception:  # noqa: BLE001 -- an advisory hook helper fails open, silently
        return 0
    if rows:
        print(f"INSTRUMENT ALREADY IN FLIGHT ON THIS DIAMOND: {target.name} is frozen for a "
              "diamond that an unscored human task already tests: " + "; ".join(rows) + ". Read "
              "that task before running this one. If it answers the same question, wait for its "
              "horizon. If this one runs anyway, write the reason in this instrument and name the "
              "task id there, so the next reader sees why both ran.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
