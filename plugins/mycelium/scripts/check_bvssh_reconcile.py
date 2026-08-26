#!/usr/bin/env python3
"""check_bvssh_reconcile.py — catch BVSSH assessments that never landed in the canvas.

THE DEFECT THIS EXISTS FOR (found in dogfood 2026-07-25, twice historically):

    `/bvssh-check` MANDATED only a decision-log append. It never told the agent
    to write `.claude/canvas/bvssh-health.yml` at all.
    Meanwhile `hooks/session-start.sh` computes the "BVSSH is N days overdue"
    reminder by reading `bvssh-health.yml#last_assessed`.

    The skill wrote to A. The detector read B. Nothing connected them.

Consequences for EVERY consumer, not just the dogfood project:
  - `last_assessed` goes stale permanently after the first assessment
  - the SessionStart reminder nags "overdue" forever, even right after a run
  - the canvas source-of-truth never accumulates `assessment_history`, so
    trend questions ("is Happier declining?") are unanswerable from the file
    that is supposed to answer them

Observed twice in the dogfood project before the cause was understood: the
2026-06-20 assessment orphaned to decision-log, was noticed, and a prose rule
("keep BVSSH assessments in the canonical log") was written into a notes field;
the 2026-07-11 assessment then orphaned identically. A prose rule could not fix
it because the skill never had the step — which is why this ships as a check
plus a skill mandate rather than more prose.

WHAT IT CHECKS
    Every `### BVSSH Assessment — <date>` heading in the decision log has a
    matching dated entry in `bvssh-health.yml#assessment_history`.

ABSENT-INPUT DISCIPLINE (anti-pattern #9 — fail loud, but only on real gaps)
    - Neither file present, or no BVSSH entries anywhere → nothing to
      reconcile. Exit 0 with a clear message. A project that has never run
      /bvssh-check is not in violation.
    - Decision-log entries exist but the canvas is missing/empty → FAIL. That
      is exactly the orphan this catches.
    - Canvas entries exist with no decision-log entry → reported as INFO, not
      a failure. Writing the canvas without the log is the harmless direction
      (the canvas is the source of truth); flagging it would train people to
      stop writing the canvas.

Usage:
    check_bvssh_reconcile.py [--project-dir DIR] [--json]

Exit codes:
    0 — reconciled, or nothing to reconcile
    1 — orphaned assessment(s) found
    2 — argument/input error

Python stdlib + PyYAML (already a framework dependency).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# `### BVSSH Assessment — 2026-07-25 (assessment #11; ...)` — the date is the
# first ISO-ish date on the heading line. Accepts em dash, en dash, or hyphen.
HEADING_RE = re.compile(
    r"^#{2,4}\s*BVSSH\s+Assessment\b[^\n]*?(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE | re.MULTILINE,
)


def _date_only(value) -> str | None:
    """Normalize a history entry's date to YYYY-MM-DD.

    Entries are written as ISO timestamps ("2026-07-25T00:00:00Z"), bare dates,
    or already-parsed date/datetime objects (PyYAML resolves unquoted dates).
    """
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    match = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def collect_log_dates(decision_log: Path) -> list[str] | None:
    """Assessment dates in the decision log, or None if it could not be read.

    NONE IS NOT []. A read failure used to return [], which made `orphaned` empty
    and printed "BVSSH reconcile: OK — 0 decision-log assessment(s) all present in
    bvssh-health.yml" — a clean reconcile asserted over a file nobody read.
    """
    if not decision_log.is_file():
        return []
    try:
        text = decision_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # De-duplicate while preserving order; a date assessed twice in one day
    # reconciles against a single canvas entry.
    seen, dates = set(), []
    for match in HEADING_RE.finditer(text):
        date = match.group(1)
        if date not in seen:
            seen.add(date)
            dates.append(date)
    return dates


def collect_canvas_dates(canvas: Path) -> list[str] | None:
    """Assessment dates in bvssh-health.yml, or None if it could not be read.

    The failure here was the mirror image and no better: [] made every log date
    look ORPHANED, so an unparseable canvas was reported as a pile of assessments
    missing from it. Loud, and about the wrong thing.
    """
    if not canvas.is_file():
        return []
    try:
        data = yaml.safe_load(canvas.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return []
    history = data.get("assessment_history") or []
    if not isinstance(history, list):
        return []
    dates = []
    for entry in history:
        if isinstance(entry, dict):
            date = _date_only(entry.get("date"))
            if date:
                dates.append(date)
    return dates


def check(project_dir: Path) -> dict:
    decision_log = project_dir / ".claude" / "harness" / "decision-log.md"
    canvas_override = os.environ.get("MYCELIUM_BVSSH_CANVAS")
    canvas = (
        Path(canvas_override)
        if canvas_override
        else project_dir / ".claude" / "canvas" / "bvssh-health.yml"
    )

    log_dates = collect_log_dates(decision_log)
    canvas_dates = collect_canvas_dates(canvas)

    # UNREADABLE IS ITS OWN STATUS. Two of the three failure combinations used to
    # produce a green: an unreadable log reconciled cleanly against the canvas, and
    # both unreadable reported "nothing to reconcile".
    unreadable = [name for name, v in (("decision-log", log_dates),
                                       ("bvssh-health.yml", canvas_dates)) if v is None]
    if unreadable:
        return {
            "status": "unreadable",
            "unreadable": unreadable,
            "detail": (f"could not read {', '.join(unreadable)}, so whether the assessments "
                       f"reconcile is UNKNOWN — this is not a clean reconcile"),
            "assessments_in_log": [],
            "assessments_in_canvas": [],
            "orphaned": [],
            "canvas_only_info": [],
        }

    orphaned = [d for d in log_dates if d not in set(canvas_dates)]
    log_only_ok = [d for d in canvas_dates if d not in set(log_dates)]

    if not log_dates and not canvas_dates:
        status = "nothing-to-reconcile"
    elif orphaned:
        status = "orphaned"
    else:
        status = "reconciled"

    return {
        "status": status,
        "decision_log": str(decision_log),
        "canvas": str(canvas),
        "assessments_in_log": log_dates,
        "assessments_in_canvas": canvas_dates,
        "orphaned_in_log_only": orphaned,
        "canvas_only_info": log_only_ok,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--project-dir",
        default=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        help="project root containing .claude/ (default: $CLAUDE_PROJECT_DIR or cwd)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir)
    if not project_dir.is_dir():
        print(f"not a directory: {project_dir}", file=sys.stderr)
        return 2

    result = check(project_dir)

    if args.as_json:
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "orphaned" else 0

    if result["status"] == "unreadable":
        print(f"BVSSH reconcile: UNKNOWN — {result['detail']}.", file=sys.stderr)
        return 2

    if result["status"] == "nothing-to-reconcile":
        print("BVSSH reconcile: no assessments recorded anywhere — nothing to reconcile.")
        return 0

    if result["status"] == "reconciled":
        print(
            f"BVSSH reconcile: OK — {len(result['assessments_in_log'])} "
            "decision-log assessment(s) all present in bvssh-health.yml."
        )
        if result["canvas_only_info"]:
            print(
                "  INFO (not a failure): canvas-only assessments "
                f"{result['canvas_only_info']} — the canvas is the source of "
                "truth, so this direction is harmless."
            )
        return 0

    print("BVSSH reconcile: FAIL — assessment(s) written to the decision log but")
    print("never reconciled into the canvas source of truth.")
    print()
    for date in result["orphaned_in_log_only"]:
        print(f"  ORPHANED  {date}  (no assessment_history entry)")
    print()
    print(f"  decision log : {result['decision_log']}")
    print(f"  canvas       : {result['canvas']}")
    print()
    print("Why this matters: hooks/session-start.sh computes the 'BVSSH overdue'")
    print("reminder from bvssh-health.yml#last_assessed. An orphaned assessment")
    print("leaves last_assessed stale, so the reminder reports overdue forever and")
    print("assessment_history never accumulates the trend it exists to hold.")
    print()
    print("Fix: append the assessment to bvssh-health.yml#assessment_history and")
    print("update last_assessed (see skills/bvssh-check/SKILL.md, Canvas step).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
