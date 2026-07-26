#!/usr/bin/env python3
"""How many reflexions fired, and how many produced a decision?

WHY (2026-07-26). `reflexion-gate.sh` prompted after every project-relevant
command failure and left **no trace**. `stop-check.sh` counted corrections. So
the loop had a numerator and no denominator: an ignored reflexion was
indistinguishable from one that never fired, and "64 corrections" said nothing
about how many learnings were prompted and dropped.

Found by auditing a session in which three in-flight fixes went unrecorded. The
audit only happened because a human asked. That is the same shape as every other
failure in this family — a measurement that lands only when someone remembers to
go looking.

WHAT COUNTS AS RECONCILED. A reflexion is answered by a *decision*, and there are
two legitimate ones:
  * a **corrections.md entry** — "this was a real mistake, here is the rule"; or
  * an explicit **dismissal with a reason** — "environment, not a learning".
Both are decisions. Silence is not. The dismissal path exists precisely because
most command failures genuinely are not learnings; the point is that deciding so
should leave a record, not evaporate.

THIS IS A FLOOR, NOT A LEDGER — stated plainly because an over-precise claim here
would be its own false green. Corrections are credited by COUNT, not attributed
to specific reflexions, so a session that adds corrections for unrelated reasons
will over-credit and under-report the outstanding number. That leniency is
deliberate: a nagging counter gets ignored, and today's other lesson is that a
guard which cries wolf is switched off and then worth less than none. What it
will never do is report zero outstanding when nothing at all was decided.

KNOWN BLIND SPOT, and it is half the problem. This only sees failures that
FIRE the hook. Two of the three unlogged fixes that motivated it produced no
failure at all — a pipeline that printed `exit: 0` while swallowing the real
status, and a guard that exited 0 after measuring nothing. A hook keyed to
command failure is structurally blind to a wrong answer delivered confidently.
No mechanical signal for that class was found, so `stop-check.sh` asks for it in
prose and this docstring records that the prose is a stopgap, not a mechanism.

Exit 0 always — this reports, it does not gate. Learning debt should accumulate
visibly, not block a session end.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

LOG_REL = ".claude/state/reflexion-log.jsonl"
DISMISS_REL = ".claude/state/reflexion-dismissed.jsonl"
LEDGER_REL = ".claude/state/reflexion-ledger.json"
CORRECTIONS_REL = ".claude/memory/corrections.md"

# A dismissal shorter than this is not a reason. "n/a", "env", "nah" restore the
# silence this whole mechanism exists to end — the decision has to be legible to
# whoever reads the log next week.
MIN_REASON_LEN = 8

# `### ` headings outside fenced code — the template carries an example heading
# inside a ``` fence that must not be counted, same rule stop-check.sh uses.
_FENCE = re.compile(r"^```")
_HEADING = re.compile(r"^### ")


def count_corrections(path: Path) -> int:
    if not path.is_file():
        return 0
    n, in_code = 0, False
    for line in path.read_text(errors="replace").splitlines():
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code and _HEADING.match(line):
            n += 1
    return n


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue  # a torn final line is not a reason to fail the report
    return out


def _load_ledger(path: Path) -> dict:
    if not path.is_file():
        return {"credited": 0, "corrections_baseline": None}
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"credited": 0, "corrections_baseline": None}
    return {
        "credited": int(d.get("credited", 0)),
        "corrections_baseline": d.get("corrections_baseline"),
    }


def status(project_dir: Path) -> dict:
    fired_records = _read_jsonl(project_dir / LOG_REL)
    dismissals = _read_jsonl(project_dir / DISMISS_REL)
    corrections_now = count_corrections(project_dir / CORRECTIONS_REL)
    ledger = _load_ledger(project_dir / LEDGER_REL)

    baseline = ledger["corrections_baseline"]
    fresh_baseline = baseline is None
    if fresh_baseline:
        # First sight: today's count becomes the baseline, so the corrections
        # written before this ledger existed are not credited against reflexions
        # that postdate them. It MUST then be persisted — recomputing it as
        # "now" on every run made corrections_since permanently 0, so adding a
        # correction never credited anything and the counter only ever rose.
        # Caught by the test that adds an entry and expects the count to fall.
        baseline = corrections_now
    corrections_since = max(0, corrections_now - int(baseline))

    fired = len(fired_records)
    credited = ledger["credited"] + corrections_since + len(dismissals)
    outstanding = max(0, fired - credited)

    return {
        "fired": fired,
        "corrections_since_baseline": corrections_since,
        "dismissed": len(dismissals),
        "outstanding": outstanding,
        "recent": (
            [r.get("command_head", "") for r in fired_records[-outstanding:]]
            if outstanding else []
        ),
        "corrections_now": corrections_now,
        "corrections_baseline": int(baseline),
        "_baseline_is_fresh": fresh_baseline,
    }


def persist_baseline_if_new(project_dir: Path, st: dict) -> None:
    """Write the baseline the first time we see this project.

    Without this the ledger never exists, so every run re-derives the baseline
    from the current corrections count and no correction is ever credited.
    """
    if not st.get("_baseline_is_fresh"):
        return
    path = project_dir / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "credited": 0,
        "corrections_baseline": st["corrections_now"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2) + "\n")


def dismiss(project_dir: Path, reason: str) -> int:
    """Record an explicit 'not a learning' decision. A reason is mandatory."""
    if not reason or len(reason.strip()) < MIN_REASON_LEN:
        print(f"ERROR: --dismiss needs a real reason (>={MIN_REASON_LEN} chars). "
              "'not a learning' without a why is the silence this exists to end.",
              file=sys.stderr)
        return 2
    path = project_dir / DISMISS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason.strip(),
        }) + "\n")
    print(f"Recorded dismissal: {reason.strip()}")
    return 0


def rebaseline(project_dir: Path) -> int:
    """Fold the current balance into the ledger so counting starts clean."""
    st = status(project_dir)
    path = project_dir / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "credited": st["fired"],
        "corrections_baseline": st["corrections_now"],
        "rebaselined_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2) + "\n")
    print(f"Ledger rebaselined: {st['fired']} reflexion(s) credited, "
          f"corrections baseline {st['corrections_now']}.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dismiss", metavar="REASON",
                    help="record an explicit 'not a learning' decision")
    ap.add_argument("--rebaseline", action="store_true",
                    help="credit all outstanding reflexions and start clean")
    args = ap.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if args.dismiss is not None:
        return dismiss(project_dir, args.dismiss)
    if args.rebaseline:
        return rebaseline(project_dir)

    st = status(project_dir)
    persist_baseline_if_new(project_dir, st)
    if args.json:
        print(json.dumps(st, indent=2))
        return 0

    if st["fired"] == 0:
        print("Reflexion ledger: no reflexions recorded yet.")
        return 0

    print(f"Reflexion ledger: {st['fired']} fired, "
          f"{st['corrections_since_baseline']} correction(s) added, "
          f"{st['dismissed']} dismissed -> {st['outstanding']} OUTSTANDING")
    if st["outstanding"]:
        print("\n  These failures prompted a reflexion and produced no recorded decision:")
        for cmd in st["recent"]:
            print(f"    - {cmd[:110]}")
        print("\n  Each needs one of two decisions, not silence:")
        print("    * a corrections.md entry (a real mistake, with the rule), or")
        print("    * reconcile_reflexions.py --dismiss 'why this was not a learning'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
