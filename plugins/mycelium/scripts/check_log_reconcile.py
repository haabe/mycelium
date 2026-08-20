#!/usr/bin/env python3
"""A dated event in the decision log whose canvas row was never written.

THIS SHIPS GREEN, AND THAT IS STATED FIRST because a check introduced with no
failing instance is the kind that quietly becomes noise. It is a REGRESSION GUARD
against two documented failures, not a discovery tool, and it found nothing on the
corpus that motivated it. Measured 2026-08-20 on the dogfood repo: BVSSH 8 dated
log events against 14 canvas rows, DORA 3 against 9, zero log-only in either, and
zero dangling canvas IDs across 253 cited. If it stays green for a long window,
narrow or retire it — that is this project's own rule for a guard with a near-zero
action rate (opp-048), and it applies to this file too.

THE FAILURE IT GUARDS, twice recorded.

  1. A BVSSH assessment was ORPHANED to the decision log and never reached
     `bvssh-health.yml#assessment_history`. `check_bvssh_reconcile.py` exists
     because of it.
  2. DORA, 2026-08-09: the measurement WAS taken and written into the metric
     fields, and `measurement_history` never gained the row. One file then carried
     THREE dates for one measurement — 2026-08-08 in the fields, 2026-08-02 in the
     top-level stamp, 2026-07-17 in the history — so every instrument asking "when
     was this measured" got a different answer depending on which it read.

Both are the same shape: **real work landing somewhere no instrument reads.** The
decision log is where it lands, which is why the only script that reads this file
for content reads it to detect exactly this.

DIRECTION MATTERS, and the asymmetry is inherited from check_bvssh_reconcile
rather than invented here. Log-without-canvas is the ORPHAN and fails. Canvas
-without-log is the HARMLESS direction and is reported as INFO: the canvas is the
source of truth, and failing on it would train people to stop writing the canvas.

WHY A REGISTRY RATHER THAN A THIRD BESPOKE CHECK. Two instances of one shape is
where a pattern earns a mechanism. Adding a class is one row. BVSSH is listed and
DEACTIVATED rather than omitted, because `check_bvssh_reconcile.py` already covers
it with special-case absent-input logic and is wired into `session-start.sh` — the
row documents the boundary instead of leaving a reader to wonder why the
motivating case is missing.

WHAT IT CANNOT DO. It matches DATES, not content. An entry can announce a
measurement and the canvas row can record a different number; nothing here would
notice. It also cannot tell a decision that legitimately belongs only in the log
(a rejected alternative, of which this corpus holds 159) from one that should have
been routed — so it only looks at classes explicitly registered below, never at
entries in general.

Exit codes:
    0  every registered class reconciles, or nothing to reconcile
    1  at least one dated log event has no canvas row
    2  the check itself could not run

Python stdlib only, so it runs in any consumer regardless of environment.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: (name, log-heading pattern capturing a date, canvas file, history key, active)
#:
#: `active=False` means another check already owns the class. The row stays so the
#: boundary is visible — an omitted class reads as an oversight, a deactivated one
#: reads as a decision.
RECONCILIATIONS = [
    (
        "DORA measurements",
        r"^###[^\n]*\bDORA\b[^\n]*?(\d{4}-\d{2}-\d{2})\s*$",
        "dora-metrics.yml",
        "measurement_history",
        True,
    ),
    (
        "BVSSH assessments",
        r"^###\s*BVSSH Assessment[^\n]*?(\d{4}-\d{2}-\d{2})\s*$",
        "bvssh-health.yml",
        "assessment_history",
        False,  # owned by check_bvssh_reconcile.py, wired into session-start.sh
    ),
]

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _history_dates(canvas: Path, key: str) -> set[str] | None:
    """Dates inside the `key:` block of a canvas file, or None if unreadable.

    Deliberately not a YAML parse: stdlib-only so this runs in any consumer. Takes
    the block from `key:` to the next line indented at or below it, then collects
    every ISO date in it — the same block-boundary technique the rest of this
    script family uses.
    """
    if not canvas.is_file():
        return None
    lines = canvas.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            indent = len(line) - len(line.lstrip())
            block = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt)
            return set(_DATE.findall("\n".join(block)))
    return None


def analyse(root: Path) -> dict:
    log = root / ".claude" / "harness" / "decision-log.md"
    if not log.is_file():
        return {"error": f"no decision log at {log}"}
    text = log.read_text(encoding="utf-8", errors="replace")

    res: dict = {"orphans": [], "info": [], "skipped": [], "checked": 0}
    for name, pattern, fname, key, active in RECONCILIATIONS:
        if not active:
            res["skipped"].append((name, "owned by check_bvssh_reconcile.py"))
            continue
        log_dates = set(re.findall(pattern, text, re.MULTILINE))
        canvas_dates = _history_dates(root / ".claude" / "canvas" / fname, key)
        if canvas_dates is None:
            if log_dates:
                # Log events exist and the canvas history does not. That IS the orphan.
                res["orphans"].append((name, f"{fname}#{key} unreadable", sorted(log_dates)))
            else:
                res["skipped"].append((name, f"{fname}#{key} not present, and no log events"))
            continue
        res["checked"] += 1
        only_log = sorted(log_dates - canvas_dates)
        if only_log:
            res["orphans"].append((name, f"{fname}#{key}", only_log))
        only_canvas = sorted(canvas_dates - log_dates)
        if only_canvas:
            res["info"].append((name, len(only_canvas)))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile dated decision-log events with canvas history rows.")
    ap.add_argument("--root", default=".", help="project root containing .claude/")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    res = analyse(root)
    if "error" in res:
        # UNKNOWN, never clean. A check that cannot run must not report a pass.
        print(f"UNKNOWN: {res['error']}", file=sys.stderr)
        return 2

    for name, where, dates in res["orphans"]:
        print(f"\nORPHANED — {name}: dated in the decision log, absent from {where}")
        for d in dates:
            print(f"  {d}")
        print("  The work was done and the recording of it was not. Route it to the canvas;")
        print("  logging a finding is not the same as filing it.")

    for name, n in res["info"]:
        print(f"INFO — {name}: {n} canvas row(s) with no log entry. Not a failure.")
        print("  The canvas is the source of truth, and failing this direction would")
        print("  train people to stop writing it.")

    for name, why in res["skipped"]:
        print(f"skip: {name} — {why}")

    if not res["orphans"]:
        print(f"\nLog reconcile: OK — {res['checked']} registered class(es), "
              "no orphaned events.")
        print("This is a REGRESSION GUARD and it ships green: it found nothing on")
        print("the corpus that motivated it. If it stays green over a long window,")
        print("narrow or retire it rather than leaving it running — a guard with a")
        print("near-zero action rate trains its reader to skim.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
