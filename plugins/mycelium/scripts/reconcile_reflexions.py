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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _corrections_lib
import _state_dir

LOG_REL = ".claude/state/reflexion-log.jsonl"
DISMISS_REL = ".claude/state/reflexion-dismissed.jsonl"
LEDGER_REL = ".claude/state/reflexion-ledger.json"
CORRECTIONS_REL = ".claude/memory/corrections.md"

# A dismissal shorter than this is not a reason. "n/a", "env", "nah" restore the
# silence this whole mechanism exists to end — the decision has to be legible to
# whoever reads the log next week.
MIN_REASON_LEN = 8

# An entry is what `_corrections_lib.ENTRY_RE` says it is: a dated heading of depth 2 to 4, or
# a dated bold bullet. Lines inside a fenced block are left out first, because an example
# entry shown in a ``` fence is not a correction.
#
# This script counted `### ` headings only. A correction written as `## <date>: ...` or as
# a dated bullet credited nothing, so the outstanding count only rose in a project that
# writes its entries that way. `COUNTER` is written to the ledger beside the baseline so a
# baseline taken with the old count can be told from one taken with this one.
_FENCE = re.compile(r"^```")
_HEADING = re.compile(r"^### ")
COUNTER = "entries"


def _outside_fences(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out, in_code = [], False
    for line in path.read_text(errors="replace").splitlines():
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code:
            out.append(line)
    return out


def count_corrections(path: Path) -> int:
    return _corrections_lib.count("\n".join(_outside_fences(path)))


def _count_headings(path: Path) -> int:
    """The count this script used before `COUNTER` existed. Read only to carry an old
    baseline over, in `status`."""
    return sum(1 for line in _outside_fences(path) if _HEADING.match(line))


def _count_dated_after(path: Path, day: str) -> int:
    """Entries whose own date is later than `day` (YYYY-MM-DD)."""
    dates = _corrections_lib.entry_dates("\n".join(_outside_fences(path)))
    return sum(1 for d in dates if d > day)


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
        return {"credited": 0, "corrections_baseline": None, "corrections_counter": None,
                "baseline_day": "", "pruned_fired": 0}
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"credited": 0, "corrections_baseline": None, "corrections_counter": None,
                "baseline_day": "", "pruned_fired": 0}
    return {
        "credited": int(d.get("credited", 0)),
        "corrections_baseline": d.get("corrections_baseline"),
        "corrections_counter": d.get("corrections_counter"),
        "baseline_day": str(d.get("rebaselined_at") or d.get("created_at") or "")[:10],
        # Lines prune_state_logs.py removed for age (v0.318.0) still count as fired, or trimming
        # old answered failures would hide new unanswered ones.
        "pruned_fired": int(d.get("pruned_fired", 0)),
    }


def _describe(row: dict) -> str:
    """One line for a firing. Since v0.318.0 rows carry no command text unless the user opted in
    (MYCELIUM_LEDGER_TRIGGER=on, masked), so the line names the time, program and exit code."""
    if row.get("command_head"):
        return str(row["command_head"])
    code = row.get("exit_code")
    return f"{row.get('ts', '?')}  {row.get('program') or 'a command'}" + (
        f" (exit {code})" if code not in (None, "") else "")


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
    # A baseline with no counter named was taken with the heading count. Comparing it with
    # the entry count would credit every entry the old count never saw, in one step. So
    # credit what was written since the baseline was taken and nothing older: the entries
    # dated after the day the ledger was written, and never fewer than the heading count
    # had already credited. A ledger with no day on it carries over the heading credit only.
    stale_counter = not fresh_baseline and ledger["corrections_counter"] != COUNTER
    if stale_counter:
        credited_since = max(
            0, _count_headings(project_dir / CORRECTIONS_REL) - int(baseline))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ledger["baseline_day"]):
            credited_since = max(credited_since, _count_dated_after(
                project_dir / CORRECTIONS_REL, ledger["baseline_day"]))
        baseline = max(0, corrections_now - credited_since)
    corrections_since = max(0, corrections_now - int(baseline))

    # SUPPRESSED ROWS ARE NOT LEARNING DEBT (added 2026-08-03). reflexion-gate
    # now classifies documented non-failures — grep exit 1 = no match, diff exit
    # 1 = differences found, test exit 1 = false — and records them WITH the
    # reason instead of dropping them. They are kept in the log so the classifier
    # stays auditable, and excluded here so the outstanding count means something.
    # Before this, 39 firings included 23 from one session that were largely
    # greps finding nothing, and the resulting "30 outstanding" was ignored —
    # correctly, and that is how a guard dies.
    suppressed_records = [r for r in fired_records if r.get("suppressed")]
    fired_records = [r for r in fired_records if not r.get("suppressed")]
    fired = len(fired_records) + ledger["pruned_fired"]
    credited = ledger["credited"] + corrections_since + len(dismissals)
    outstanding = max(0, fired - credited)

    return {
        "fired": fired,
        "suppressed_non_events": len(suppressed_records),
        "corrections_since_baseline": corrections_since,
        "dismissed": len(dismissals),
        "outstanding": outstanding,
        "recent": (
            [_describe(r) for r in fired_records[-outstanding:]]
            if outstanding else []
        ),
        "corrections_now": corrections_now,
        "corrections_baseline": int(baseline),
        "pruned_fired": ledger["pruned_fired"],
        "_baseline_is_fresh": fresh_baseline,
        "_baseline_counter_is_stale": stale_counter,
    }


def persist_baseline_if_new(project_dir: Path, st: dict) -> None:
    """Write the baseline the first time we see this project.

    Without this the ledger never exists, so every run re-derives the baseline
    from the current corrections count and no correction is ever credited.
    """
    path = project_dir / LEDGER_REL
    if st.get("_baseline_counter_is_stale"):
        # Keep everything the ledger holds; move the baseline to the entry count and say so.
        try:
            held = json.loads(path.read_text())
        except (OSError, ValueError):
            return
        held["corrections_baseline"] = st["corrections_baseline"]
        held["corrections_counter"] = COUNTER
        _state_dir.prepare(path)
        path.write_text(json.dumps(held, indent=2) + "\n")
        return
    if not st.get("_baseline_is_fresh"):
        return
    _state_dir.prepare(path)
    path.write_text(json.dumps({
        "credited": 0,
        "corrections_baseline": st["corrections_now"],
        "corrections_counter": COUNTER,
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
    _state_dir.prepare(path)
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
    _state_dir.prepare(path)
    path.write_text(json.dumps({
        "credited": st["fired"],
        "corrections_baseline": st["corrections_now"],
        "corrections_counter": COUNTER,
        "pruned_fired": st["pruned_fired"],
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

    supp = st.get("suppressed_non_events", 0)
    if st["fired"] == 0:
        # State the suppressed count even here. "No reflexions recorded" over a
        # log full of suppressed rows would be a green over a population the
        # reader cannot see.
        if supp:
            print(f"Reflexion ledger: no reflexions to reconcile "
                  f"({supp} documented non-failure(s) recorded and excluded).")
        else:
            print("Reflexion ledger: no reflexions recorded yet.")
        return 0

    print(f"Reflexion ledger: {st['fired']} fired, "
          f"{st['corrections_since_baseline']} correction(s) added, "
          f"{st['dismissed']} dismissed -> {st['outstanding']} OUTSTANDING")
    if supp:
        print(f"  ({supp} further firing(s) were documented non-failures — grep "
              f"no-match, diff differences, test false — recorded with a reason "
              f"and excluded from learning debt.)")
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
