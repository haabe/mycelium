#!/usr/bin/env python3
"""check_cluster_reconcile.py — catch corrections that never reach the cluster catalogue.

THE DEFECT THIS EXISTS FOR (measured in dogfood 2026-08-06, opp-034):

    `cluster-instances.md` graduates clusters on instance COUNTS ("graduate at
    instance 6", ">=3 instances", "next instance in a NEW surface"). NOTHING
    WRITES THOSE COUNTS. They are maintained by hand, by whichever session
    happens to notice.

    Measured: `corrections.md` gained 24 entries between 2026-08-01 and
    2026-08-05. `cluster-instances.md` gained ONE row in the same window.
    `consistency-as-evidence` still read "Total instances: 31 / Most recent:
    2026-07-27" while at least four August corrections were unmistakably its
    shape.

WHY THIS IS NOT A HOUSEKEEPING CHORE. A count-keyed trigger evaluating a
hand-maintained number cannot fire on its own. Both clusters currently sitting
at criterion-met-mechanism-not-built were found by a human reading the file. So
"no cluster graduated" and "no cluster crossed its criterion" are
indistinguishable from outside — anti-pattern #9 (Fail-Open on Absent Input)
operating on the accounting FOR anti-pattern #9.

It had already been diagnosed once. The 2026-07-25 re-count found the identical
drift and named the identical cause ("nothing writes them, the count is
hand-maintained"), then answered it with another hand re-count. Twelve days
later it was stale again. A structural diagnosis answered with a manual fix has
been restated, not acted on.

WHAT IT CHECKS
    How many `### <date>` correction entries are newer than the newest date
    recorded anywhere in the cluster catalogue. At or above the threshold, the
    corrections -> cluster hop has gone unconsidered and this fails loud.

WHAT IT DELIBERATELY DOES NOT DO — THE LOAD-BEARING NON-GOAL
    It does NOT decide which cluster a correction belongs to, and must never
    learn to. Mis-binning a correction silently corrupts a count that GATES A
    MECHANISM, which is strictly worse than the drift it replaces: drift is at
    least honest about being behind. The check asserts the hop was CONSIDERED
    and stops there. Same shape as `check_bvssh_reconcile.py`, which asserts an
    assessment reached the canvas without judging its content.

WHAT IT DETECTS, AND WHAT IT DOES NOT — STATED SO NOBODY READS IT WIDER
    It detects LAPSE: corrections piling up with no new instance logged at all.
    It does NOT detect UNDER-LOGGING: twenty corrections answered with one row
    look the same to it as twenty answered with twenty.

    That gap is not an oversight, it is forced. Telling those apart requires
    deciding which corrections were cluster instances, which is classification,
    which is the one thing this check must never do (see the non-goal below).
    So the honest claim is narrow: it catches the hop going UNCONSIDERED, not
    the hop being done thinly. A green result means someone looked recently. It
    does not mean the counts are right.

    Do not widen this claim later without solving the classification problem
    first, because a check believed to guarantee correct counts, while only
    guaranteeing recent attention, is worse than no check.

NOT SATISFIABLE BY TOUCHING THE FILE
    The pass condition is a DATE COMPARISON between two file contents, never a
    modification timestamp and never "the cluster file changed". A whitespace
    commit moves nothing here. That is deliberate: a check whose cheapest green
    is a no-op edit joins the blind-green family it was built against (opp-023).

    Two honest ways to green:
      1. Log the instance(s) — a dated row in the catalogue.
      2. Declare them considered and inapplicable — a dated
         `reviewed-no-cluster-applies: YYYY-MM-DD` marker in the catalogue.
    Both require a human judgement to have happened. Neither can be faked by
    saving the file.

ABSENT-INPUT DISCIPLINE (anti-pattern #9 — fail loud, but only on real gaps)
    - Either file missing        -> exit 0. A project without a corrections log
      or a cluster catalogue has not started this loop; it is not in violation.
    - Corrections file has no parseable dated entries -> exit 0 and SAY SO with
      the `no-dated-corrections` token, printing the pattern used. "None found"
      and "my regex is broken" must never be the same output.
    - Cluster file has no parseable date at all -> treated as "never
      reconciled": every dated correction counts. Reported distinctly.

Usage:
    check_cluster_reconcile.py [--project-dir DIR] [--threshold N] [--json]

Exit codes:
    0 — reconciled, or nothing to reconcile
    1 — corrections have accumulated with no cluster-catalogue movement
    2 — argument/input error

Python stdlib only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 5

# `### 2026-08-04 — <title>` and `### 2026-08-02b - <title>`. The optional
# trailing letter is real: corrections.md carries a "2026-08-02b" entry, and a
# stricter pattern would silently drop it.
CORRECTION_RE = re.compile(r"^#{2,4}\s+(\d{4}-\d{2}-\d{2})[a-z]?\b", re.MULTILINE)

# ONLY dates in the second column of an instance-log table row:
#   | 10 | 2026-08-04 | <title> | <subclass> | <outcome> |
#
# NOT any date in the file. The first version of this script matched any ISO
# date anywhere, and it went green on its own first live run — because the same
# session had added a dated CLOSURE NOTE to an existing instance's outcome cell,
# which is prose maintenance, not a logged instance. A single dated sentence
# anywhere would have silenced it permanently. That is the exact
# "cheapest green is a no-op edit" failure this file's header warns about, found
# by running the check instead of reasoning about it.
#
# Only a genuinely NEW logged instance moves this date forward.
CLUSTER_DATE_RE = re.compile(
    r"^\|[^|]*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", re.MULTILINE
)

# The explicit escape hatch. Dated, so it cannot be a permanent silencer.
REVIEWED_MARKER_RE = re.compile(
    r"reviewed-no-cluster-applies:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
)


def newest_date(text: str, pattern: re.Pattern):
    """Return the max ISO date matched by `pattern`, or None."""
    found = pattern.findall(text)
    return max(found) if found else None


def corrections_after(text: str, cutoff):
    """Dated correction entries strictly newer than `cutoff` (all, if None)."""
    dates = CORRECTION_RE.findall(text)
    if cutoff is None:
        return sorted(dates), len(dates)
    return sorted(d for d in dates if d > cutoff), len(dates)


def evaluate(project_dir: Path, threshold: int):
    """Return a result mapping. Pure — no printing, no exit."""
    memory = project_dir / ".claude" / "memory"
    corrections_file = memory / "corrections.md"
    cluster_file = memory / "cluster-instances.md"

    if not corrections_file.is_file() or not cluster_file.is_file():
        missing = [
            f.name for f in (corrections_file, cluster_file) if not f.is_file()
        ]
        return {
            "status": "skip",
            "reason": f"missing {', '.join(missing)} — this loop has not started, not a violation",
        }

    corrections_text = corrections_file.read_text(encoding="utf-8", errors="replace")
    cluster_text = cluster_file.read_text(encoding="utf-8", errors="replace")

    all_correction_dates = CORRECTION_RE.findall(corrections_text)
    if not all_correction_dates:
        return {
            "status": "ok",
            "token": "no-dated-corrections",
            "detail": (
                f"no-dated-corrections — no `### YYYY-MM-DD` entries in corrections.md; "
                f"pattern was {CORRECTION_RE.pattern!r}"
            ),
        }

    # The escape hatch wins outright when it covers the newest correction.
    reviewed = newest_date(cluster_text, REVIEWED_MARKER_RE)
    newest_correction = max(all_correction_dates)
    if reviewed is not None and reviewed >= newest_correction:
        return {
            "status": "ok",
            "token": "reviewed-no-cluster-applies",
            "reviewed_through": reviewed,
            "newest_correction": newest_correction,
        }

    cluster_newest = newest_date(cluster_text, CLUSTER_DATE_RE)
    unreconciled, total = corrections_after(corrections_text, cluster_newest)

    return {
        "status": "unreconciled" if len(unreconciled) >= threshold else "ok",
        "cluster_newest": cluster_newest,
        "never_reconciled": cluster_newest is None,
        "unreconciled_count": len(unreconciled),
        "unreconciled_dates": unreconciled,
        "total_corrections": total,
        "threshold": threshold,
        "reviewed_through": reviewed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when corrections accumulate with no cluster-catalogue movement."
    )
    parser.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    parser.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD,
        help=f"unreconciled corrections before failing (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"check_cluster_reconcile: not a directory: {project_dir}", file=sys.stderr)
        return 2
    if args.threshold < 1:
        print("check_cluster_reconcile: --threshold must be >= 1", file=sys.stderr)
        return 2

    result = evaluate(project_dir, args.threshold)

    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "unreconciled" else 0

    status = result["status"]
    if status == "skip":
        print(f"check_cluster_reconcile: SKIP — {result['reason']}")
    elif status == "ok" and result.get("token") == "no-dated-corrections":
        print(f"check_cluster_reconcile: OK — {result['detail']}")
    elif status == "ok" and result.get("token") == "reviewed-no-cluster-applies":
        print(
            f"check_cluster_reconcile: OK — catalogue reviewed through "
            f"{result['reviewed_through']}, covering the newest correction "
            f"({result['newest_correction']})."
        )
    elif status == "ok":
        print(
            f"check_cluster_reconcile: OK — {result['unreconciled_count']} correction(s) "
            f"newer than the catalogue's newest date ({result['cluster_newest']}), "
            f"under threshold {result['threshold']}."
        )
    else:
        scope = (
            "the catalogue carries NO date at all, so every dated correction counts"
            if result["never_reconciled"]
            else f"the catalogue's newest date is {result['cluster_newest']}"
        )
        shown = ", ".join(result["unreconciled_dates"][:8])
        extra = len(result["unreconciled_dates"]) - 8
        if extra > 0:
            shown += f" (+{extra} more)"
        print(
            f"check_cluster_reconcile: FAIL — {result['unreconciled_count']} correction(s) "
            f"logged since {scope}, threshold {result['threshold']}.\n"
            f"  Dates: {shown}\n"
            f"  The corrections -> cluster hop has gone unconsidered. Count-keyed graduation\n"
            f"  reads a hand-maintained number, so a stale count means the triggers cannot fire.\n"
            f"  Two honest ways to green, both requiring a judgement that actually happened:\n"
            f"    1. Log the instance(s) as dated rows in cluster-instances.md.\n"
            f"    2. Add `reviewed-no-cluster-applies: YYYY-MM-DD` to cluster-instances.md if\n"
            f"       none of them belong to a cluster.\n"
            f"  This check does NOT classify corrections. Mis-binning corrupts a count that\n"
            f"  gates a mechanism, which is worse than drift that is honest about being behind."
        )

    return 1 if status == "unreconciled" else 0


if __name__ == "__main__":
    sys.exit(main())
