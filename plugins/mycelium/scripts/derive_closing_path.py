#!/usr/bin/env python3
"""derive_closing_path.py — what would close this diamond's current phase, read off the record.

WHY THIS EXISTS (dogfood, 2026-09-09). `/diamond-assess` reports where a diamond stands and which
gates pass. That morning it gave status; the founder had to ask twice ("what's needed to close
define?", "work through the distance points") before the closing path was derived, and every input
to it was already on disk: leaf assumptions with null verdicts, a dated read four days out, a gate
status field stale since a review three days earlier, a ruling already on the founder's desk. His
words, verbatim, on the framework: "too passive about keeping up with data and progress ... The user
most certainly doesn't have the state of every nitbits of the project, and can't tell the agent what
is needed to progress." This script derives the path so the skill prints it rather than the human
asking for it.

WHAT IT DERIVES, per diamond, from three files:
  GATES     `theory_gates_status` entries that are not `pass` (pending, fail, pass-with-risk).
  LEAVES    under opportunities that roll up to or cite the diamond: candidate/proposed/open leaves
            with an assumption lacking a verdict, and whether a test is named for it (the input the
            Four Risks and Cynefin gates wait on).
  TASKS     open human tasks whose `diamond_ref` names the diamond, with their `horizon`: the dated
            reads the path waits on.
  STALE     a gate marked pending/fail while every live leaf under the diamond's opportunities
            carries a four_risks block (the 2026-09-09 case: `four_risks: pending` three days after
            a blind review wrote the blocks). Reported as a field to reconcile, not as a pass.
  OWED      `what_would_move_it` / `reader` text on those opportunities that names a ruling or the
            founder: rulings already asked, so the skill says owed rather than re-asking.

It prints a table: gate | what would flip it | owner (agent or human) | date if the record holds
one. It does NOT flip anything, score anything, or move confidence. Where the record holds no input
for a gate it says so ("nothing on record"), which is itself the finding.

PRECONDITION UNMET SPEAKS. No active.yml or no such diamond: prints N/A and exits 0.
Exit 0 always except 2 on a usage error; this is a derivation, not a gate.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

TERMINAL_TASK = {"completed", "closed", "cancelled", "abandoned", "done", "scored", "withdrawn"}
LIVE_LEAF = ("candidate", "proposed", "open")
TEST_KEYS = ("cheapest_test", "smallest_test", "falsifier", "test_design")
LINK_KEYS = ("rolls_up_to", "diamond_ref", "diamond", "canvas_refs", "parent_diamond")
#: A four_risks block with fewer dimensions than this is a note, not a block.
FOUR_RISK_DIMS = 4
_RULING = re.compile(r"\b(ruling|founder|human|decide|decision)\b", re.IGNORECASE)


def load_yaml(p: Path):
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:  # speaks
        print(f"closing-path: cannot parse {p.name}: {e}")
        return {}


def _find_diamond(doc, did: str):
    for key in ("active_diamonds", "parked_diamonds", "diamonds"):
        for d in doc.get(key) or []:
            if isinstance(d, dict) and d.get("id") == did:
                return d
    return None


def _is_live(leaf: dict) -> bool:
    return str(leaf.get("status") or "candidate").lower().startswith(LIVE_LEAF)


def _outcome_key(v) -> str:
    """`opportunities.yml#desired_outcomes.adoption`, `desired_outcomes.adoption` and `adoption`
    all name the same outcome: the last dotted segment, lowercased."""
    return str(v or "").strip().split("#")[-1].split(".")[-1].strip().lower()


def _diamond_outcomes(d: dict) -> set[str]:
    """Outcomes the diamond rolls up to, read from its top level and its definition_of_done.
    A tree rooted on outcomes ("one root, one tree") links opportunities to a diamond only
    through these; nothing there carries a diamond id."""
    vals = [d.get("rolls_up_to"), (d.get("definition_of_done") or {}).get("rolls_up_to")]
    return {k for k in (_outcome_key(v) for v in vals if isinstance(v, str)) if k}


def _opps_for(opps_doc, did: str, outcomes: set[str] | None = None) -> list[dict]:
    """Open opportunities that cite the diamond by id in a link key, OR roll up to an outcome
    the diamond itself rolls up to. Without the second branch an outcome-rooted tree reads as
    0 of 0 leaves for every diamond, which the dogfood repo hit the day this script shipped."""
    out = []
    for o in opps_doc.get("opportunities") or []:
        if not isinstance(o, dict) or str(o.get("status", "open")).lower() != "open":
            continue
        links = yaml.dump({k: v for k, v in o.items() if k in LINK_KEYS}, allow_unicode=True)
        by_outcome = bool(outcomes) and _outcome_key(o.get("rolls_up_to")) in outcomes
        if did in links or by_outcome:
            out.append(o)
    return out


def _test_named(leaf: dict, a: dict) -> bool:
    if any(str(k).startswith(("test", "cheapest")) for k in a):
        return True
    ra = leaf.get("riskiest_assumption")
    return isinstance(ra, dict) and any(isinstance(ra.get(k), str) for k in TEST_KEYS)


def _leaf_rows(opps: list[dict]) -> list[dict]:
    rows = []
    for o in opps:
        for s in o.get("solutions") or []:
            if not isinstance(s, dict) or not _is_live(s):
                continue
            for a in s.get("assumptions") or []:
                if not isinstance(a, dict) or a.get("verdict") not in (None, "", "pending"):
                    continue
                rows.append({"opp": o.get("id"), "leaf": s.get("id"), "assumption": a.get("id"),
                             "statement": str(a.get("statement", ""))[:90],
                             "test_named": _test_named(s, a)})
    return rows


def _leaf_totals(opps: list[dict]) -> tuple[int, int]:
    total = reviewed = 0
    for o in opps:
        for s in o.get("solutions") or []:
            if not isinstance(s, dict) or not _is_live(s):
                continue
            total += 1
            fr = s.get("four_risks")
            if isinstance(fr, dict) and len(fr) >= FOUR_RISK_DIMS:
                reviewed += 1
    return total, reviewed


def _open_tasks_for(tasks_doc, did: str) -> list[dict]:
    out = []
    if not isinstance(tasks_doc, dict):
        return out
    for key, lst in tasks_doc.items():
        if not isinstance(lst, list) or key == "completed_tasks":
            continue
        for t in lst:
            if not isinstance(t, dict) or str(t.get("status", "")).lower() in TERMINAL_TASK:
                continue
            if did in str(t.get("diamond_ref", "")):
                out.append({"id": t.get("id"), "status": t.get("status"),
                            "horizon": t.get("horizon")})
    return out


def _owed(opps: list[dict]) -> list[tuple[str, str]]:
    out = []
    for o in opps:
        for k in ("what_would_move_it", "reader"):
            v = o.get(k)
            if isinstance(v, str) and _RULING.search(v):
                out.append((str(o.get("id")), v.strip().split("\n")[0][:110]))
    return out


def derive(root: Path, did: str) -> dict | None:
    canvas = root / ".claude" / "canvas"
    active = root / ".claude" / "diamonds" / "active.yml"
    if not active.exists():
        return None
    d = _find_diamond(load_yaml(active), did)
    if d is None:
        return None
    opps_path, tasks_path = canvas / "opportunities.yml", canvas / "human-tasks.yml"
    outcomes = _diamond_outcomes(d)
    opps = _opps_for(load_yaml(opps_path) if opps_path.exists() else {}, did, outcomes)
    tasks = _open_tasks_for(load_yaml(tasks_path) if tasks_path.exists() else {}, did)
    gates = {k: v for k, v in (d.get("theory_gates_status") or {}).items()
             if str(v).lower() != "pass"}
    total, reviewed = _leaf_totals(opps)
    stale = [g for g in gates if g == "four_risks" and total and reviewed == total]
    return {"diamond": d, "gates": gates, "leaves": _leaf_rows(opps), "tasks": tasks,
            "stale": stale, "owed": _owed(opps), "n_opps": len(opps),
            "leaf_totals": (total, reviewed), "outcomes": sorted(outcomes)}


def _gate_row(g: str, v, r: dict) -> str:
    total, reviewed = r["leaf_totals"]
    if g in r["stale"]:
        return (f"{g} ({v}) | STALE FIELD: all {reviewed} of {total} live leaves carry a "
                "four_risks block; reconcile the status, do not re-review | agent | now")
    if g == "four_risks":
        return (f"{g} ({v}) | a chosen leaf with four_risks and a validated riskiest assumption "
                f"({reviewed} of {total} live leaves have a block) "
                "| human chooses, agent tests | -")
    if g == "cynefin":
        return f"{g} ({v}) | assumption-test evidence on record for a complex domain | agent | -"
    if g == "evidence":
        return (f"{g} ({v}) | an external source landed on a canvas entry this diamond cites "
                "| human + agent | -")
    return f"{g} ({v}) | nothing on record names an input for this gate | - | -"


def _print_inputs(r: dict) -> None:
    if r["leaves"]:
        print("leaf assumptions without a verdict (the inputs Four Risks and Cynefin wait on):")
        for lr in r["leaves"]:
            how = ("test named; agent can run or schedule it" if lr["test_named"]
                   else "NO TEST NAMED; design one or archive the leaf")
            print(f"  {lr['opp']} {lr['leaf']} {lr['assumption']} | {lr['statement']} | {how}")
    if r["tasks"]:
        print("open human tasks on this diamond (dated reads the path waits on):")
        for t in sorted(r["tasks"], key=lambda x: str(x.get("horizon") or "9999")):
            print(f"  {t['id']} {t['status']} | horizon {t.get('horizon') or 'undated'}")
    if r["owed"]:
        print("rulings already asked (say owed, do not re-ask):")
        for oid, line in r["owed"]:
            print(f"  {oid} | {line}")
    if not (r["leaves"] or r["tasks"] or r["owed"]) and r["gates"]:
        print("nothing on record moves any pending gate: no live assumption, no open task, "
              "no declared reader. That is the finding.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Derive what would close a diamond's current phase.")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--diamond-id", required=True)
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    r = derive(root, args.diamond_id)
    if r is None:
        print(f"closing-path: N/A — no diamond {args.diamond_id} in "
              f"{root}/.claude/diamonds/active.yml; nothing derived")
        return 0
    d = r["diamond"]
    plural = "y" if r["n_opps"] == 1 else "ies"
    print(f"closing-path: {args.diamond_id} ({d.get('scale', '?')} {d.get('phase', '?')}, "
          f"confidence {d.get('confidence', '?')}); {r['n_opps']} open opportunit{plural} cite it")
    if r["n_opps"] == 0:
        via = (f"by id or by outcome ({', '.join(r['outcomes'])})" if r["outcomes"]
               else "by id, and the diamond names no rolls_up_to outcome")
        print(f"no open opportunity links to this diamond {via}; the leaf rows below are the tree "
              "unread, not the tree empty")
    print("gate | what would flip it | owner | date")
    if not r["gates"]:
        print("(none pending) | every gate in theory_gates_status reads pass | - | -")
    for g, v in r["gates"].items():
        print(_gate_row(g, v, r))
    _print_inputs(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
