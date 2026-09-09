#!/usr/bin/env python3
"""check_idle_opportunities.py — an open opportunity that nothing reads is invisible to every check.

WHAT WAS MEASURED BEFORE THIS EXISTED (dogfood canvas, 2026-09-09). 66 open opportunities. 50 had
no open human task pointing at them; 33 of those had no solution leaf at all; twelve had not moved
since before 2026-08-15. Canvas health flagged stale evidence dates and orphaned references, the
landing check flagged sources with no reader, the retirement report covers mechanisms and the
parking-lot check covers the root. Nothing looked at the NODE. The founder's question that day was
"are all osts also waiting incoming data?", and the answer was that most were waiting on nobody. A
four-reader triage the same day recommended discard for 7, merge for 5 and park for 14 of the 50;
four of the seven discards then had to be withdrawn because no task had ever been pointed at them,
so their silence was routing, not evidence. This check is the routing question, asked of every node.

THE THREE READERS a node can have, any one of which makes it NOT idle:
  TASK      an open human task (any non-terminal status) names the node's id anywhere in its text.
  TEST      a leaf under the node, itself not terminal, carries an assumption with no verdict AND a
            named test (a `cheapest_test`, `smallest_test`, `test_*` or `falsifier` field), or the
            leaf's `riskiest_assumption` names one.
  DECLARED  the node carries `what_would_move_it` (or `reader`): a written statement of what would
            change it. A declared reader that names nothing real is still a declared reader; this
            check cannot judge it and does not try.
Plus a fourth signal that is not a reader but is reported beside them:
  RECENT    any ISO date within `--window` days (default 60) appears in the node's text. Recent
            writes with no reader are still idle; the date says the node is being written to, not
            that anything will read it.

A node with none of TASK, TEST, DECLARED is reported as IDLE, with its age (days since the newest
date anywhere in its text, or "undated"). WARN tier by default: it prints and exits 0, because on a
brownfield canvas the count is large and a red gate on a number that cannot move in a day trains
dismissal. `--strict` exits 1 on any IDLE node, for projects that have cleared the backlog.

WHAT IT DELIBERATELY DOES NOT DO. It does not say a node should be discarded: silence is a fact
about routing, never about the need (the 2026-09-09 correction). It does not read the decision log
as a reader: an append-only log is where findings go to be unread. It does not judge a declared
reader.

PRECONDITION UNMET SPEAKS. No opportunities.yml: prints N/A and exits 0.

Exit 0 clean, N/A, or WARN; 1 only under --strict with at least one IDLE node; 2 on a usage error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

import yaml

TERMINAL_TASK = {"completed", "closed", "cancelled", "abandoned", "done", "scored", "withdrawn"}
TERMINAL_LEAF_PREFIX = ("shipped", "archived", "discarded", "validated", "invalidated", "killed",
                        "not-built", "rejected", "tested", "partially_shipped", "resolved")
TEST_KEYS = ("cheapest_test", "smallest_test", "falsifier", "test_design")
DECLARED_KEYS = ("what_would_move_it", "reader")
#: A test field shorter than this is a label, not a design.
MIN_TEST_TEXT = 20
#: Undated nodes sort as older than anything dated.
UNDATED_AGE = 10**6
_DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


def load_yaml(p: Path):
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:  # speaks: the human sees which file could not be read
        print(f"idle-opportunities: cannot parse {p.name}: {e}")
        return {}


def _open_task_texts(tasks_doc) -> list[str]:
    out = []
    if not isinstance(tasks_doc, dict):
        return out
    for key, lst in tasks_doc.items():
        if not isinstance(lst, list):
            continue
        for t in lst:
            if not isinstance(t, dict):
                continue
            status = str(t.get("status", "")).lower()
            if status in TERMINAL_TASK or key == "completed_tasks":
                continue
            out.append(yaml.dump(t, allow_unicode=True))
    return out


def _names_test(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    return any(isinstance(obj.get(k), str) and len(obj[k]) > MIN_TEST_TEXT for k in TEST_KEYS)


def _leaf_has_live_test(leaf: dict) -> bool:
    status = str(leaf.get("status") or "candidate").lower()
    if status.startswith(TERMINAL_LEAF_PREFIX):
        return False
    if _names_test(leaf.get("riskiest_assumption")) or _names_test(leaf):
        return True
    for a in leaf.get("assumptions") or []:
        if not isinstance(a, dict) or a.get("verdict") not in (None, "", "pending"):
            continue
        if any(str(k).startswith(("test", "cheapest")) for k in a):
            return True
    return False


def _newest_date(text: str) -> _dt.date | None:
    best = None
    for m in _DATE.finditer(text):
        try:
            d = _dt.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    return best


def _row(o: dict, open_texts: list[str], today: _dt.date, window: int) -> dict:
    oid = str(o.get("id", "?"))
    pat = re.compile(rf"\b{re.escape(oid)}\b")
    task = any(pat.search(t) for t in open_texts)
    leaves = [s for s in (o.get("solutions") or []) if isinstance(s, dict)]
    test = any(_leaf_has_live_test(s) for s in leaves)
    declared = any(isinstance(o.get(k), str) and o[k].strip() for k in DECLARED_KEYS)
    newest = _newest_date(yaml.dump(o, allow_unicode=True))
    age = (today - newest).days if newest else None
    return {"id": oid, "task": task, "test": test, "declared": declared,
            "recent": age is not None and age <= window, "age_days": age,
            "idle": not (task or test or declared)}


def analyse(root: Path, today: _dt.date, window: int) -> dict:
    canvas = root / ".claude" / "canvas"
    opps_doc = load_yaml(canvas / "opportunities.yml")
    tasks_path = canvas / "human-tasks.yml"
    open_texts = _open_task_texts(load_yaml(tasks_path) if tasks_path.exists() else {})
    rows = [_row(o, open_texts, today, window)
            for o in opps_doc.get("opportunities") or []
            if isinstance(o, dict) and str(o.get("status", "open")).lower() == "open"]
    return {"rows": rows, "open": len(rows), "idle": [r for r in rows if r["idle"]]}


def _print_report(r: dict, verbose: bool) -> list[dict]:
    idle = sorted(r["idle"], key=lambda x: (-(x["age_days"] or UNDATED_AGE), x["id"]))
    n_read = r["open"] - len(idle)
    print(f"idle-opportunities: {r['open']} open node(s): "
          f"{n_read} with a reader (task, live test or declared), {len(idle)} IDLE")
    if verbose:
        for row in r["rows"]:
            flags = ",".join(k for k in ("task", "test", "declared", "recent") if row[k]) or "-"
            age = row["age_days"] if row["age_days"] is not None else "undated"
            print(f"  {row['id']:<10} readers={flags:<28} age={age}")
    if idle:
        print("WARN: IDLE — no open task names it, no leaf carries a live test, nothing declared "
              "what would move it. Silence is routing, not evidence: name a reader, park with a "
              "resume condition, or merge; discard only on the record.")
        for row in idle:
            age = f"{row['age_days']}d" if row["age_days"] is not None else "undated"
            rec = " recent-writes" if row["recent"] else ""
            print(f"  {row['id']:<10} {age:>8}{rec}")
    return idle


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report open opportunities that nothing reads.")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--window", type=int, default=60, help="days for the RECENT signal")
    ap.add_argument("--today", default=None, help="ISO date override (testing)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any IDLE node")
    ap.add_argument("--verbose", action="store_true", help="print every open node's readers")
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    if not (root / ".claude" / "canvas" / "opportunities.yml").exists():
        print(f"idle-opportunities: N/A — no .claude/canvas/opportunities.yml under {root}; "
              "nothing was checked")
        return 0
    try:
        today = (_dt.date.fromisoformat(args.today) if args.today
                 else _dt.datetime.now(tz=_dt.UTC).date())
    except ValueError:
        print("idle-opportunities: --today is not an ISO date", file=sys.stderr)
        return 2
    idle = _print_report(analyse(root, today, args.window), args.verbose)
    if idle and args.strict:
        print(f"FAIL: {len(idle)} IDLE node(s) under --strict")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
