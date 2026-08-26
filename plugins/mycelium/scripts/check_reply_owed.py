#!/usr/bin/env python3
"""check_reply_owed.py — the SINGLE implementation of "they wrote, you have not answered".

WHY THIS FILE EXISTS, AND IT IS NOT THAT THE RULE WAS WRONG.

The rule was implemented TWICE: as prose in `skills/canvas-health/SKILL.md` step
8c(e), and as code inside a `python3 -c` block in `hooks/session-start.sh`. Both
described the same check. Only one got fixed.

    2026-08-05  A dogfood run found the same-day defect: an inbound and its reply
                on the SAME DATE scored as unanswered, because day-granular dates
                cannot order two contacts and the tie broke toward the inbound.
                TWO false positives out of two flags -- ht-060 and ht-003.
    v0.90.0     The fix was written into the SKILL PROSE as a documented tie-break.
    2026-08-07  `session-start.sh` flagged ht-060 and ht-003. The same two tasks,
                the same cause, two days later. Fixed again as v0.103.1, by an
                agent who did not know the diagnosis already existed.

**The defect class is not "a bug recurred". It is that a rule with two
implementations was repaired in the one that cannot execute.** Prose cannot be
run, so nothing compared it to the code; the code kept its bug while the
documentation described the fix. That is the
documented-rule-diverges-from-enforcement cluster with the arrow reversed --
usually the prose is right and unenforced, here the prose was right and the
enforcement rotted beside it.

Patching both copies would leave two copies. So there is now one, and both
surfaces call it: `session-start.sh` for the session banner, and canvas-health
step 8c(e) instead of describing an algorithm it cannot run.

THE RULE, stated once:

  Walk `touch_log[]`. Consider only entries whose `direction` is a CONTACT value
  (outbound / inbound / bidirectional) -- an `internal` note is not contact, and
  letting one sit on top of an inbound is how an owed reply disappears. Take the
  newest by DATE, breaking ties by LOG POSITION (later entry wins), because dates
  are day-granular and carry no ordering within a day. If that newest contact is
  `inbound` and >= threshold days old, a reply is owed. An explicit `reply_owed:`
  field forces the flag regardless of dates.

  The tiebreak is POSITION, not direction. Preferring outbound on a tie would
  silence the honest case where the reply went out and they answered it again the
  same day -- which is a real owed reply.

Exit 0 always (advisory). Findings to stdout, or JSON with --json.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import yaml

CONTACT_DIRECTIONS = ("outbound", "inbound", "bidirectional")
TERMINAL_STATUSES = ("completed", "abandoned", "stalled", "cancelled")
DEFAULT_THRESHOLD_DAYS = 3


def _status(task: dict) -> str:
    """Status token only. YAML comments ride along on these fields in real canvases."""
    return str(task.get("status", "")).split("#")[0].strip().lower()


def is_terminal(task: dict) -> bool:
    return _status(task) in TERMINAL_STATUSES


def last_contact(task: dict) -> tuple[datetime.date, str, int] | None:
    """Newest CONTACT entry as (date, direction, index), ties broken by log position.

    Position is consulted ONLY when dates are equal. Different dates still order by
    date, so the out-of-order-log guardpost is unaffected.
    """
    best: tuple[datetime.date, str, int] | None = None
    for i, entry in enumerate(task.get("touch_log") or []):
        if not isinstance(entry, dict):
            continue
        direction = entry.get("direction")
        if direction not in CONTACT_DIRECTIONS:
            continue
        raw = entry.get("date")
        if not isinstance(raw, str):
            continue
        try:
            when = datetime.date.fromisoformat(raw[:10])
        except ValueError:
            continue
        if best is None or (when, i) > (best[0], best[2]):
            best = (when, direction, i)
    return best


def owed(tasks: list, today: datetime.date,
         threshold: int = DEFAULT_THRESHOLD_DAYS) -> list[dict]:
    """Tasks where the other person is waiting on an answer."""
    out: list[dict] = []
    for task in tasks:
        if not isinstance(task, dict) or is_terminal(task):
            continue
        tid = task.get("id", "?")
        if task.get("reply_owed"):
            out.append({"id": tid, "age_days": None, "reason": "explicit reply_owed field"})
            continue
        contact = last_contact(task)
        if not contact:
            continue
        when, direction, _ = contact
        if direction != "inbound":
            continue
        age = (today - when).days
        if age >= threshold:
            out.append({"id": tid, "age_days": age,
                        "reason": f"last contact was inbound {age}d ago"})
    return out


def load_tasks(path: Path) -> list | None:
    """Pending tasks, or None if the file could not be read.

    NONE AND [] ARE DIFFERENT ANSWERS AND USED NOT TO BE. This returned [] on any
    read or parse failure, and main() then printed "OK: no reply owed across 0
    task(s)" with status "ok" — a green produced by not being able to look. The
    branch immediately above it in main() already got this right for a MISSING
    file ("No task file is not a clean pass; it is nothing to check. Say which."),
    so the file contained both the failure and its own remedy.

    The old handler also listed `(OSError, UnicodeDecodeError, Exception)`, where
    the third member makes the first two decorative.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data.get("pending_tasks") or [] if isinstance(data, dict) else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_DAYS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today", default=None, help="ISO date; for tests")
    args = ap.parse_args(argv)

    # datetime.now(tz).date() rather than date.today(): DTZ011 — an untimezoned
    # 'today' silently uses the runner's locale, and a reply-owed age is a real number.
    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.datetime.now(datetime.UTC).date())
    path = Path(args.project_dir) / ".claude" / "canvas" / "human-tasks.yml"

    if not path.exists():
        # No task file is not a clean pass; it is nothing to check. Say which.
        if args.json:
            print(json.dumps({"status": "no_task_file", "violations": []}))
        return 0

    tasks = load_tasks(path)
    if tasks is None:
        msg = (f"UNREADABLE: {path} could not be read or parsed, so whether a reply is "
               f"owed is UNKNOWN. This is not 'no replies owed'.")
        if args.json:
            print(json.dumps({"status": "unreadable", "violations": [],
                              "detail": msg}))
        else:
            print(msg, file=sys.stderr)
        return 2

    flagged = owed(tasks, today, args.threshold)

    if args.json:
        print(json.dumps({
            "status": "violations" if flagged else "ok",
            "tasks_scanned": len(tasks),
            "violations": flagged,
        }))
        return 0

    if not flagged:
        print(f"OK: no reply owed across {len(tasks)} task(s).")
        return 0

    parts = ", ".join(f"{f['id']}" + (f" ({f['age_days']}d)" if f["age_days"] is not None else "")
                      for f in flagged)
    print(f"REPLY OWED on {len(flagged)} task(s): {parts}. "
          "The last CONTACT on these was inbound — they wrote, you have not answered. "
          "This is invisible to the staleness check, which counts their reply as activity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
