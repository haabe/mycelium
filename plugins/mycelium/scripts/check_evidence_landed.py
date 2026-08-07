#!/usr/bin/env python3
"""check_evidence_landed.py — a task that closed with findings must have put them somewhere.

THE EMPTY QUADRANT.

`canvas-health` already covers two thirds of the routing problem:

    8c(b)  task still OPEN while its evidence exists        -> flagged
    8c(d)  evidence exists with NO task covering it         -> flagged
    ????   task CLOSED and its evidence never landed        -> nothing

The third case had no check, and `canvas_refs` — the field where a task DECLARES
which canvases its findings belong in — was read by NOTHING. Grep across
`plugins/mycelium/scripts/` returned zero matches before this file existed. It was
documentation of an intention, with no mechanism behind it.

FOUND IN DOGFOOD 2026-08-08, and the timing is the argument. That morning's
`/bvssh-check` rated Measurement AMBER for a named, recurring failure:
"measurements generated and never landing where they are read." Three hours later
ht-055 was scored, closed, and its findings written ONLY into `human-tasks.yml` —
while ht-055's own `canvas_refs` declared it routed to
`purpose.yml#positioning_evidence`. The task said where its evidence belonged, the
evidence did not go there, and nothing noticed. It surfaced because a human asked
"all logged and verified?", which is not a mechanism.

WHY THIS IS THE EXPENSIVE DIRECTION. An open task with stranded evidence is still
visible: it sits in the pending list and something will trip over it. A CLOSED task
is gone from every open-work surface, so its findings are not merely unrouted —
they are unreachable. The next session reads the canvas, sees no entry, and
concludes the question was never asked.

THE RULE:

  For each task in a TERMINAL state that declares `canvas_refs`, check whether the
  referenced canvas files actually mention the task's id. If none do, its findings
  did not land where the task itself said they belonged.

WHAT COUNTS AS LANDED is deliberately cheap: the target file mentions the task id
anywhere. Not a semantic check on whether the finding is faithfully represented —
no script can do that — but it separates "routed" from "never written", which is
the failure that actually occurs. A task with a legitimate null result records it
with `no_evidence_produced:` and is exempt, because "we asked and learned nothing"
is a finding that belongs in the task, not in the opportunity tree.

ADVISORY. Exit 0 when it ran, 2 when there was nothing to scan.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

TERMINAL_STATUSES = ("completed", "abandoned", "stalled", "cancelled")
# `abandoned` and `cancelled` are terminal but are NOT expected to produce landed
# evidence — the point of abandoning is that nothing came of it. Only a task that
# COMPLETED made a claim to have finished something.
EXPECTED_TO_LAND = ("completed",)

_REF_RE = re.compile(r"^([A-Za-z0-9_.-]+\.yml)")


def _status(task: dict) -> str:
    return str(task.get("status", "")).split("#")[0].strip().lower()


def refs_of(task: dict) -> list[str]:
    """Canvas files this task declared its findings belong in."""
    out: list[str] = []
    for ref in task.get("canvas_refs") or []:
        if not isinstance(ref, str):
            continue
        m = _REF_RE.match(ref.strip())
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def _reader(canvas_dir: Path):
    """Cached file reader. A missing canvas returns empty — it cannot have received
    anything, which is a finding rather than an error."""
    cache: dict[str, str] = {}

    def body(name: str) -> str:
        if name not in cache:
            try:
                cache[name] = (canvas_dir / name).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                cache[name] = ""
        return cache[name]
    return body


def _expects_landing(task: dict) -> bool:
    """Whether this task claimed to have finished something that belongs elsewhere."""
    if _status(task) not in EXPECTED_TO_LAND:
        return False
    # An explicit null result is a finding recorded in the right place.
    return not task.get("no_evidence_produced")


def stranded(tasks: list, canvas_dir: Path) -> list[dict]:
    """Completed tasks whose declared canvases never mention them."""
    body = _reader(canvas_dir)
    out: list[dict] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if not _expects_landing(task):
            continue
        tid = task.get("id")
        if not tid:
            continue
        targets = refs_of(task)
        if not targets:
            # No declared destination is a different (and much weaker) concern:
            # the task never claimed its findings belonged anywhere.
            continue
        landed = [t for t in targets if tid in body(t)]
        if not landed:
            out.append({
                "id": tid,
                "declared": targets,
                "reason": (f"{tid} closed declaring canvas_refs {targets}, and none of those "
                           f"files mention {tid}. Its findings are unreachable from the canvas."),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet-when-clean", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_dir)
    tasks_file = root / ".claude" / "canvas" / "human-tasks.yml"
    canvas_dir = root / ".claude" / "canvas"

    if not tasks_file.exists():
        msg = (f"PRECONDITION NOT MET: no {tasks_file}. Nothing was verified. "
               "This is not a clean result.")
        if args.json:
            print(json.dumps({"status": "precondition_not_met", "violations": [], "reason": msg}))
        else:
            print(msg, file=sys.stderr)
        return 2

    try:
        data = yaml.safe_load(tasks_file.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        # Fail open on a broken file; a hook must not block a session.
        if args.json:
            print(json.dumps({"status": "unparseable", "violations": []}))
        return 0

    tasks = data.get("pending_tasks") or [] if isinstance(data, dict) else []
    findings = stranded(tasks, canvas_dir)
    completed = sum(1 for t in tasks if isinstance(t, dict) and _status(t) in EXPECTED_TO_LAND)

    if args.json:
        print(json.dumps({
            "status": "violations" if findings else "ok",
            "completed_tasks_checked": completed,
            "violations": findings,
        }))
        return 0

    if not findings:
        if not args.quiet_when_clean:
            print(f"OK: every completed task with canvas_refs is cited by at least one of them "
                  f"({completed} completed task(s) checked).")
        return 0

    print(f"ADVISORY: {len(findings)} completed task(s) whose findings never reached the canvas "
          "they were routed to.")
    for f in findings:
        print(f"  {f['id']}: declared {f['declared']} — none of them mention {f['id']}")
    print("\nA CLOSED task is gone from every open-work surface, so stranded findings are not")
    print("merely unrouted, they are unreachable. The next session reads the canvas, sees")
    print("nothing, and concludes the question was never asked.")
    print("Fix by writing the finding into one of the declared files, or record")
    print("`no_evidence_produced:` with the reason if nothing came of it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
