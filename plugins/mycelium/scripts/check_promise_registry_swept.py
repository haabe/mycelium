#!/usr/bin/env python3
"""Assert the Promise registry has been swept recently — not that its promises are kept.

WHY THIS EXISTS, AND WHY IT CHECKS THE SWEEP RATHER THAN THE PROMISES.

`engine/consistency-check-spec.md` carries a Promise registry: framework prose claiming a
surface does something nothing implements. It is the right instrument for that class. On
2026-08-23 it held four rows, all closed, all from a single 2026-06-12 analysis — nothing
added in ten weeks, while a rule census that same day found two fresh instances (a fully
specified mutation-log subsystem with no writer, and a BLOCK-tier guardrail unmet for three
of its four named scripts).

The registry did not fail. NOTHING SWEPT IT. Its sweep lives in `/framework-health` step 4f,
which is prose in a skill invoked when someone remembers — so the registry could not
distinguish "nothing to add" from "nobody looked", which are the two states it most needs to
tell apart. That is this project's own recurring shape: the instrument for finding unenforced
rules was itself an unenforced rule.

WHAT THIS DELIBERATELY DOES NOT DO. It does not try to detect unkept promises. Both forms of
that check were built and measured on 2026-08-23 and both were rejected: the broad form
produced 61 hits, nearly all consumer-repo canvas files that correctly do not ship in the
plugin; the narrow form produced 3 flags, all false, AND MISSED the very instance it was
written from. The measurements are recorded in the spec so the attempt is not repeated blind.
A matcher that misses its own founding case is worse than no check.

ADVISORY BY DEFAULT. Exit 0 unless --strict, for the reason every WARN-tier check here gives:
a consumer inherits this file and must not have their build broken by a date they did not set.
A MISSING marker is different from a STALE one and is reported differently — absent means the
contract was never adopted, stale means it was adopted and then not honoured.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

SPEC = pathlib.Path("plugins/mycelium/engine/consistency-check-spec.md")
MARKER = re.compile(r"\*\*last_swept:\s*(\d{4}-\d{2}-\d{2})\*\*")
DEFAULT_MAX_AGE_DAYS = 90  # matches the quarterly /framework-health cadence that owns step 4f


def find_spec(root: pathlib.Path) -> pathlib.Path | None:
    for cand in (root / SPEC, root / "engine" / "consistency-check-spec.md"):
        if cand.is_file():
            return cand
    return None


def sweep_age(text: str, today: datetime.date):
    """Returns (date, age_days) or (None, None) when no marker is present."""
    m = MARKER.search(text)
    if not m:
        return None, None
    try:
        d = datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None, None
    return d, (today - d).days


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    ap.add_argument("--strict", action="store_true", help="exit 1 when missing or stale")
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    spec = find_spec(root)
    print("Promise-registry sweep freshness")
    print("=" * 60)
    if spec is None:
        # EXIT 2 — PRECONDITION UNMET, not a pass. Corrected before shipping, after
        # check_empty_input_honesty flagged the first draft for exiting 0 here:
        # "a check that looked at nothing and reports success is indistinguishable
        # from one that works, and reads green forever." That is right, and the
        # distinction it draws is the one that matters — a MISSING SPEC is a
        # precondition failure, while a spec with no rows is an empty population.
        # Only the second is a legitimate zero. Same contract as
        # check_coverage_floor.py, which exits 2 without the report it reads.
        print(f"  PRECONDITION UNMET — no engine/consistency-check-spec.md under {root}.")
        print("  Nothing was verified. This is not a pass.")
        return 2

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.datetime.now(datetime.UTC).date())
    when, age = sweep_age(spec.read_text(encoding="utf-8", errors="ignore"), today)

    if when is None:
        print("  MISSING — no `last_swept:` marker in the Promise registry.")
        print("  This is not the same finding as a stale sweep: the registry cannot tell")
        print("  'nothing to add' from 'nobody looked' until the marker exists.")
        return 1 if args.strict else 0

    if age < 0:
        # A future date is not a sweep. Without this branch the whole check is
        # bypassable by typing a date far enough ahead — the cheapest possible
        # way to turn an instrument into decoration, and the one a hurried author
        # would reach for. Reported as its own finding, not folded into MISSING.
        print(f"  FUTURE — `last_swept: {when}` is {abs(age)}d ahead, "
              "which is not a sweep.")
        print("  Set it to the date the sweep actually ran.")
        return 1 if args.strict else 0

    if age > args.max_age_days:
        print(f"  STALE — last swept {when} ({age}d ago, limit {args.max_age_days}d).")
        print("  Run /mycelium:framework-health step 4f, then update the marker EVEN IF")
        print("  it adds no row — a sweep that found nothing is a measurement; an absent")
        print("  sweep is not.")
        return 1 if args.strict else 0

    print(f"  ok — last swept {when} ({age}d ago, limit {args.max_age_days}d)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
