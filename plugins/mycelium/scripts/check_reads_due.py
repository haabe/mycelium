#!/usr/bin/env python3
"""check_reads_due.py — pre-registered reads on open human tasks whose date has passed unrecorded.

WHY THIS EXISTS (dogfood, 2026-09-10). Two observation tasks registered a 48-hour read for that
day in `read_dates`. Five sessions ran, thirteen releases shipped, one decision-log entry cited
"the 48-hour reads are on 2026-09-10" as a reason not to build something else, and nothing read
them. `read_dates` was free text that no script consumed: the closing-path controller watched
`horizon`, the staleness label watched activity, and a read that is due looks like any other day.

ONE IMPLEMENTATION. The read states (DUE / recorded / upcoming) are computed by
`derive_closing_path.reads_for`; this script only walks every open task and prints the due ones
as one advisory line, the shape `check_reply_owed.py` uses, so session-start and the advisory
ledger pick it up without a second rule to diverge.

Output: "READ DUE on N task(s): ht-113 (read dated 2026-09-10: 48 h ...); ..." when any read is
due; "OK: no read due across N open task(s)." otherwise. Exit 0 in both cases and on a missing
file; an unreadable file is said out loud, never read as "nothing due".
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml
from derive_closing_path import TERMINAL_TASK, reads_for


def due_reads(tasks_doc, today: str) -> tuple[list[tuple[str, dict]], int]:
    """(due reads as (task id, read row), count of open tasks walked)."""
    due, n_open = [], 0
    if not isinstance(tasks_doc, dict):
        return due, n_open
    for key, lst in tasks_doc.items():
        if not isinstance(lst, list) or key == "completed_tasks":
            continue
        for t in lst:
            if not isinstance(t, dict) or str(t.get("status", "")).lower() in TERMINAL_TASK:
                continue
            n_open += 1
            due.extend((str(t.get("id")), r) for r in reads_for(t, today) if r["state"] == "DUE")
    return due, n_open


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    args = ap.parse_args(argv)
    path = Path(args.project_dir) / ".claude" / "canvas" / "human-tasks.yml"
    if not path.exists():
        print("OK: no human-tasks.yml; no read due.")
        return 0
    # yaml.safe_load directly, not derive_closing_path.load_yaml: that helper prints and
    # returns {} on a parse error, and {} here would read as "nothing due" (the fail-open
    # shape the tests below refuse).
    try:
        doc = yaml.safe_load(path.read_text())
    except Exception as exc:  # noqa: BLE001 - say it, do not read it as nothing due
        print(f"UNREADABLE: {path}: {exc}. Whether a read is due is UNKNOWN.")
        return 0
    due, n_open = due_reads(doc, args.today)
    if not due:
        print(f"OK: no read due across {n_open} open task(s).")
        return 0
    parts = "; ".join(
        f"{tid} (read dated {r['date']}: {r['what'] or 'no description'})" for tid, r in due
    )
    print(
        f"READ DUE on {len(due)} task(s): {parts}. A pre-registered read whose date has passed "
        "with nothing recorded on the task since. Run it now, record it on the task (a dated "
        "field or touch entry on or after the read date clears this), or say why it is void."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
