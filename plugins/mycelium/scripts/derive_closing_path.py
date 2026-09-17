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
            reads the path waits on. Since 0.197.0 also each task's `read_dates` (a pre-registered
            intermediate read such as "+48h"): a read whose date has passed with no activity on the
            task on or after it is printed as READ DUE. Dogfood 2026-09-10: two 48-hour reads were
            registered on two tasks, five sessions ran that day, and nothing read them, because only
            `horizon` was watched.
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
import datetime as _dt
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_replace import write_checked  # parse-before-write for every canvas text edit (0.220.0)

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
    s = str(v or "").strip()
    if " " in s:
        # Prose ("l0-purpose - evidence that ...") is a note, not an id. Dogfood 2026-09-11: a
        # definition_of_done.rolls_up_to holding a paragraph keyed to "" by luck of a trailing
        # full stop and the diamond read as unlinked for two days; without the full stop it
        # would have keyed to the last sentence fragment and matched nothing, silently.
        return ""
    return s.split("#")[-1].split(".")[-1].strip().lower()


def _rolls_up_to_prose(d: dict) -> list[str]:
    """`rolls_up_to` values on the diamond that are prose rather than an outcome id."""
    vals = [d.get("rolls_up_to"), (d.get("definition_of_done") or {}).get("rolls_up_to")]
    return [v.strip() for v in vals if isinstance(v, str) and v.strip() and " " in v.strip()]


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
                rows.append(
                    {
                        "opp": o.get("id"),
                        "leaf": s.get("id"),
                        "assumption": a.get("id"),
                        "statement": str(a.get("statement", ""))[:90],
                        "test_named": _test_named(s, a),
                    }
                )
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


_READ_DATE = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")


def _activity_dates(t: dict) -> list[str]:
    """Every ISO date the task itself carries: touch_log dates, dated field NAMES
    (`read_48h_2026_09_11`, `reply_sent_2026_08_11`), updated_at. The same sources
    session-start's staleness label reads, so a read counts as recorded by exactly the
    activity that would refresh the task's clock."""
    out = []
    for k in ("updated_at", "reopened_at", "commitment_received_at"):
        v = t.get(k)
        if isinstance(v, str) and _READ_DATE.match(v):
            out.append(v[:10])
    for lk in ("touch_log", "partial_findings"):
        for e in t.get(lk) or []:
            d = e.get("date") if isinstance(e, dict) else None
            if isinstance(d, str) and _READ_DATE.match(d):
                out.append(d[:10])
    for k in t:
        m = _READ_DATE.search(str(k))
        if m:
            out.append("-".join(m.groups()))
    return out


def reads_for(t: dict, today: str) -> list[dict]:
    """Pre-registered reads on a task, from `read_dates` (strings led by a date, or
    {date, what} mappings). A read is DUE when its date is on or before `today` and the task
    holds no activity dated on or after it; UPCOMING when its date is after today; RECORDED
    otherwise. Reads with no parseable date are skipped: a string nothing can date is prose."""
    out = []
    acts = _activity_dates(t)
    for r in t.get("read_dates") or []:
        if isinstance(r, dict):
            date, what = str(r.get("date") or ""), str(r.get("what") or "")
        else:
            date, what = str(r), ""
        m = _READ_DATE.search(date)
        if not m:
            continue
        iso = "-".join(m.groups())
        if not what:
            what = date[m.end() :].strip(" :()-")
        if iso > today:
            state = "upcoming"
        elif any(a >= iso for a in acts):
            state = "recorded"
        else:
            state = "DUE"
        out.append({"date": iso, "what": what, "state": state})
    return out


def _open_tasks_for(tasks_doc, did: str, today: str | None = None) -> list[dict]:
    out = []
    if not isinstance(tasks_doc, dict):
        return out
    today = today or _dt.datetime.now(tz=_dt.UTC).date().isoformat()
    for key, lst in tasks_doc.items():
        if not isinstance(lst, list) or key == "completed_tasks":
            continue
        for t in lst:
            if not isinstance(t, dict) or str(t.get("status", "")).lower() in TERMINAL_TASK:
                continue
            if did in str(t.get("diamond_ref", "")):
                out.append(
                    {
                        "id": t.get("id"),
                        "status": t.get("status"),
                        "horizon": t.get("horizon"),
                        "reads": reads_for(t, today),
                    }
                )
    return out


def _owed(opps: list[dict]) -> list[tuple[str, str]]:
    out = []
    for o in opps:
        for k in ("what_would_move_it", "reader"):
            v = o.get(k)
            if isinstance(v, str) and _RULING.search(v):
                out.append((str(o.get("id")), v.strip().split("\n")[0][:110]))
    return out


def derive(root: Path, did: str, today: str | None = None) -> dict | None:
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
    tasks = _open_tasks_for(load_yaml(tasks_path) if tasks_path.exists() else {}, did, today)
    gates = {
        k: v for k, v in (d.get("theory_gates_status") or {}).items() if str(v).lower() != "pass"
    }
    total, reviewed = _leaf_totals(opps)
    stale = [g for g in gates if g == "four_risks" and total and reviewed == total]
    return {
        "diamond": d,
        "gates": gates,
        "leaves": _leaf_rows(opps),
        "tasks": tasks,
        "stale": stale,
        "owed": _owed(opps),
        "n_opps": len(opps),
        "leaf_totals": (total, reviewed),
        "outcomes": sorted(outcomes),
        "rolls_up_to_prose": _rolls_up_to_prose(d),
        "reads_due": [
            (t["id"], r) for t in tasks for r in t.get("reads") or [] if r["state"] == "DUE"
        ],
    }


def _gate_row(g: str, v, r: dict) -> str:
    total, reviewed = r["leaf_totals"]
    if g in r["stale"]:
        return (
            f"{g} ({v}) | STALE FIELD: all {reviewed} of {total} live leaves carry a "
            "four_risks block; reconcile the status, do not re-review | agent | now"
        )
    if g == "four_risks":
        return (
            f"{g} ({v}) | a chosen leaf with four_risks and a validated riskiest assumption "
            f"({reviewed} of {total} live leaves have a block) "
            "| human chooses, agent tests | -"
        )
    if g == "cynefin":
        return f"{g} ({v}) | assumption-test evidence on record for a complex domain | agent | -"
    if g == "evidence":
        return (
            f"{g} ({v}) | an external source landed on a canvas entry this diamond cites "
            "| human + agent | -"
        )
    return f"{g} ({v}) | nothing on record names an input for this gate | - | -"


def _print_inputs(r: dict) -> None:
    if r["leaves"]:
        print("leaf assumptions without a verdict (the inputs Four Risks and Cynefin wait on):")
        for lr in r["leaves"]:
            how = (
                "test named; agent can run or schedule it"
                if lr["test_named"]
                else "NO TEST NAMED; design one or archive the leaf"
            )
            print(f"  {lr['opp']} {lr['leaf']} {lr['assumption']} | {lr['statement']} | {how}")
    if r["reads_due"]:
        print(
            f"READ DUE on {len(r['reads_due'])} task(s): a pre-registered read whose date has "
            "passed with nothing recorded on the task since (run it, record it on the task):"
        )
        for tid, rd in r["reads_due"]:
            print(f"  {tid} | read dated {rd['date']} | {rd['what'] or 'no description'}")
    if r["tasks"]:
        print("open human tasks on this diamond (dated reads the path waits on):")
        for t in sorted(r["tasks"], key=lambda x: str(x.get("horizon") or "9999")):
            nxt = [x for x in t.get("reads") or [] if x["state"] == "upcoming"]
            tail = f" | next read {min(x['date'] for x in nxt)}" if nxt else ""
            print(f"  {t['id']} {t['status']} | horizon {t.get('horizon') or 'undated'}{tail}")
    if r["owed"]:
        print("rulings already asked (say owed, do not re-ask):")
        for oid, line in r["owed"]:
            print(f"  {oid} | {line}")
    if not (r["leaves"] or r["tasks"] or r["owed"]) and r["gates"]:
        print(
            "nothing on record moves any pending gate: no live assumption, no open task, "
            "no declared reader. That is the finding."
        )


# ---------------------------------------------------------------- store where it fires (v0.187.0)
#
# WHY (dogfood 2026-09-09, DL-1242). The closing path was derived twice into the decision log,
# which nothing reads at the moment the condition is met. Founder: "did you log what would close
# define so that when it happens it actually does so?" It had not been. The fix on the dogfood side
# was a hand-written field on the diamond plus `reader` on the assumptions and `on_close` on the
# tasks it names. `--write` does that from the derivation, and `--all --write` at session start
# re-derives every diamond, so a stored condition is never older than the last start (a stored
# condition can go stale against the tree; k8s re-reconciles rather than trusting the last write).
# What the controller ACTS on is deliberately narrow: it stores, it stamps readers, and it detects
# that a named input has landed (an assumption got a verdict, a task closed). It never flips a
# gate, moves confidence or chooses a path; those stay human and are PARKED as one proposal line
# with the options, per the 2026-09-09 discovery (F2: do the derivable step, park the ruling).
#
# Hand-written sub-keys under `closes_on` (`routes_on_record`, `then_do`, `caveat`, `why_a_field`)
# are PRESERVED across re-derivation; only the derived keys are replaced.

DERIVED_KEYS = ("stored_at", "gates", "inputs", "fired")
_INLINE_MAX = 80
_ROW_OWNER, _ROW_DATE = 2, 3
PRESERVED_KEYS = ("routes_on_record", "then_do", "caveat", "why_a_field", "does_not_close")


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_scalar(key: str, text: str, indent: int) -> list[str]:
    pad = " " * indent
    out = [f"{pad}{key}: >-"]
    out += [f"{pad}  {ln}" if ln.strip() else "" for ln in text.rstrip("\n").split("\n")]
    return out


def _render_fired(fired: list[dict], indent: int) -> list[str]:
    pad = " " * indent
    if not fired:
        return [f"{pad}  fired: []"]
    out = [f"{pad}  fired:"]
    for f in fired:
        out.append(f"{pad}  - id: {f['id']}")
        out.append(f"{pad}    kind: {f['kind']}")
        out.append(f"{pad}    landed_as: {json.dumps(f['landed_as'])}")
        out.append(f"{pad}    noticed_at: '{f['noticed_at']}'")
        out += _block_scalar("proposal", f["proposal"], indent + 4)
        # A hand-written ruling on a fired entry is preserved: the block is script-owned but
        # the answer to its own question is not (dogfood 2026-09-11: the first FIRED was ruled
        # "does not choose a path" and the ruling had nowhere to live).
        if f.get("ruling"):
            out += _block_scalar("ruling", str(f["ruling"]), indent + 4)
        if f.get("ruled_at"):
            out.append(f"{pad}    ruled_at: '{f['ruled_at']}'")
    return out


def _render_closes_on(entry: dict, indent: int) -> list[str]:
    """Render the closes_on mapping as YAML lines at `indent` (the diamond's field indent)."""
    pad = " " * indent
    out = [f"{pad}closes_on:"]
    out.append(f"{pad}  stored_at: '{entry['stored_at']}'")
    out.append(f"{pad}  gates:")
    for g in entry["gates"]:
        out.append(f"{pad}  - gate: {g['gate']}")
        out.append(f"{pad}    status: {json.dumps(g['status'])}")
        out += _block_scalar("what_would_flip_it", g["what_would_flip_it"], indent + 4)
        out.append(f"{pad}    owner: {json.dumps(g['owner'])}")
        out.append(f"{pad}    date: {json.dumps(str(g['date']))}")
    out.append(f"{pad}  inputs:")
    if not entry["inputs"]:
        out[-1] = f"{pad}  inputs: []"
    for inp in entry["inputs"]:
        out.append(f"{pad}  - kind: {inp['kind']}")
        out.append(f"{pad}    id: {inp['id']}")
        out.append(f"{pad}    ref: {json.dumps(inp['ref'])}")
        out.append(f"{pad}    state: {json.dumps(inp['state'])}")
        if inp.get("date"):
            out.append(f"{pad}    date: '{inp['date']}'")
    out += _render_fired(entry.get("fired") or [], indent)
    for k in PRESERVED_KEYS:
        if k in entry and entry[k] is not None:
            out += _render_preserved(k, entry[k], indent + 2)
    return out


def _render_preserved(key: str, value, indent: int) -> list[str]:
    """Re-emit a preserved hand-written sub-key. Strings become block scalars; lists of dicts and
    dicts are emitted as simple YAML; anything else falls back to JSON-quoted scalars."""
    pad = " " * indent
    if isinstance(value, str):
        return _block_scalar(key, value, indent)
    if isinstance(value, list):
        out = [f"{pad}{key}:"]
        for item in value:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    lead = f"{pad}- " if first else f"{pad}  "
                    first = False
                    if isinstance(v, str) and ("\n" in v or ": " in v or len(v) > _INLINE_MAX):
                        out.append(f"{lead}{k}: >-")
                        out += [f"{pad}    {ln}" for ln in v.rstrip("\n").split("\n")]
                    else:
                        out.append(f"{lead}{k}: {json.dumps(v, ensure_ascii=False)}")
            else:
                out.append(f"{pad}- {json.dumps(item, ensure_ascii=False)}")
        return out
    if isinstance(value, dict):
        out = [f"{pad}{key}:"]
        for k, v in value.items():
            out += _render_preserved(k, v, indent + 2)
        return out
    return [f"{pad}{key}: {json.dumps(value, ensure_ascii=False)}"]


def _assumption_index(opps_doc) -> dict[str, dict]:
    """Every assumption in the tree by id, live or not, with its leaf and opp ids and verdict."""
    idx = {}
    for o in (opps_doc.get("opportunities") or []) if isinstance(opps_doc, dict) else []:
        for s in o.get("solutions") or []:
            if not isinstance(s, dict):
                continue
            for a in s.get("assumptions") or []:
                if isinstance(a, dict) and a.get("id"):
                    idx[str(a["id"])] = {
                        "opp": o.get("id"),
                        "leaf": s.get("id"),
                        "verdict": a.get("verdict"),
                    }
    return idx


def _task_index(tasks_doc) -> dict[str, dict]:
    idx = {}
    if not isinstance(tasks_doc, dict):
        return idx
    for key, lst in tasks_doc.items():
        if isinstance(lst, list):
            for t in lst:
                if isinstance(t, dict) and t.get("id"):
                    idx[str(t["id"])] = {
                        "status": t.get("status"),
                        "horizon": t.get("horizon"),
                        "list": key,
                    }
    return idx


def _route_refs(existing: dict | None, diamond: dict | None = None) -> list[str]:
    """Assumption and task ids named by hand in routes_on_record, so a route the script cannot
    derive (an outcome-rooted tree, a closed parent node) is still watched. Reads the stored
    closes_on AND any hand-written sibling field whose name ends in closes_on (the dogfood
    canvas wrote `define_closes_on` by hand before this existed)."""
    refs = []
    routes = list((existing or {}).get("routes_on_record") or [])
    for k, v in (diamond or {}).items():
        if k != "closes_on" and str(k).endswith("closes_on") and isinstance(v, dict):
            routes += list(v.get("routes_on_record") or [])
    for r in routes:
        if not isinstance(r, dict):
            continue
        for k in ("assumption", "task", "fires_when"):
            v = str(r.get(k) or "")
            refs += re.findall(r"\b(a-[0-9a-z]+-\d+|ht-\d+)\b", v)
    return refs


def build_closes_on(  # noqa: C901, PLR0912, PLR0915 — one derivation, three input kinds, two landings
    root: Path, did: str, today: str
) -> tuple[dict | None, dict | None]:
    """Derive the stored form: gates rows, watched inputs (assumptions without a verdict, open
    tasks, hand-named routes), and what has FIRED since the previous store. Returns
    (entry, previous)."""
    r = derive(root, did)
    if r is None:
        return None, None
    d = r["diamond"]
    prev = d.get("closes_on") if isinstance(d.get("closes_on"), dict) else None
    canvas = root / ".claude" / "canvas"
    aidx = _assumption_index(
        load_yaml(canvas / "opportunities.yml") if (canvas / "opportunities.yml").exists() else {}
    )
    tidx = _task_index(
        load_yaml(canvas / "human-tasks.yml") if (canvas / "human-tasks.yml").exists() else {}
    )
    gates = []
    for g, v in r["gates"].items():
        row = _gate_row(g, v, r).split(" | ")
        gates.append(
            {
                "gate": g,
                "status": str(v),
                "what_would_flip_it": row[1] if len(row) > 1 else "",
                "owner": row[_ROW_OWNER] if len(row) > _ROW_OWNER else "-",
                "date": row[_ROW_DATE] if len(row) > _ROW_DATE else "-",
            }
        )
    inputs = []
    seen = set()
    for lr in r["leaves"]:
        aid = str(lr["assumption"])
        if aid in seen:
            continue
        seen.add(aid)
        inputs.append(
            {
                "kind": "assumption",
                "id": aid,
                "ref": f"opportunities.yml#{lr['opp']}.{lr['leaf']}",
                "state": "no verdict",
            }
        )
    for t in r["tasks"]:
        tid = str(t["id"])
        if tid in seen:
            continue
        seen.add(tid)
        inputs.append(
            {
                "kind": "task",
                "id": tid,
                "ref": f"human-tasks.yml#{tid}",
                "state": str(t.get("status") or "open"),
                "date": t.get("horizon"),
            }
        )
    for ref in _route_refs(prev, d):
        if ref in seen:
            continue
        seen.add(ref)
        if ref.startswith("ht-"):
            inputs.append(
                {
                    "kind": "task",
                    "id": ref,
                    "ref": f"human-tasks.yml#{ref}",
                    "state": str((tidx.get(ref) or {}).get("status") or "unknown"),
                    "date": (tidx.get(ref) or {}).get("horizon"),
                }
            )
        else:
            a = aidx.get(ref) or {}
            inputs.append(
                {
                    "kind": "assumption",
                    "id": ref,
                    "ref": f"opportunities.yml#{a.get('opp', '?')}.{a.get('leaf', '?')}",
                    "state": "no verdict"
                    if a.get("verdict") in (None, "", "pending")
                    else f"verdict {a.get('verdict')}",
                }
            )
    # what fired: a previously watched input whose state moved to a landing
    fired = list((prev or {}).get("fired") or [])
    already = {f.get("id") for f in fired if isinstance(f, dict)}
    prev_inputs = {
        i.get("id"): i for i in ((prev or {}).get("inputs") or []) if isinstance(i, dict)
    }
    for pid, pi in prev_inputs.items():
        if pid in already:
            continue
        # Only a watched input that was OPEN when stored can fire: an input first watched in a
        # landed state (a task already completed, a verdict already on record) is state, not news.
        prev_state = str(pi.get("state") or "").lower()
        if pi.get("kind") == "assumption" and prev_state != "no verdict":
            continue
        if pi.get("kind") == "task" and prev_state in TERMINAL_TASK:
            continue
        if pi.get("kind") == "assumption":
            a = aidx.get(str(pid)) or {}
            v = a.get("verdict")
            if v not in (None, "", "pending"):
                fired.append(
                    {
                        "id": pid,
                        "kind": "assumption",
                        "landed_as": f"verdict {v}",
                        "noticed_at": today,
                        "proposal": (
                            f"{pid} has a verdict ({v}), the first input named on this "
                            f"diamond's closing path to land. The path can now be chosen: "
                            f"run /mycelium:diamond-progress "
                            f"{did}, or rule that this verdict does not choose one: write "
                            f"`ruling:` and `ruled_at:` under this fired entry and say why."
                        ),
                    }
                )
        elif pi.get("kind") == "task":
            t = tidx.get(str(pid)) or {}
            if str(t.get("status") or "").lower() in TERMINAL_TASK:
                fired.append(
                    {
                        "id": pid,
                        "kind": "task",
                        "landed_as": f"status {t.get('status')}",
                        "noticed_at": today,
                        "proposal": (
                            f"{pid} closed ({t.get('status')}); it was named on this "
                            f"diamond's closing "
                            f"path. Read its findings against the gate it was waiting on, then run "
                            f"/mycelium:diamond-progress {did} or say what still blocks."
                        ),
                    }
                )
    # A landed input is reported under `fired` and nowhere else (v0.226.3). A hand-named route
    # stays in routes_on_record for good, so _route_refs re-added it to `inputs` on every run:
    # one id in two lists, and validate_canvas rejects that as a duplicate id. The script was
    # failing the framework's own validator with its own output.
    landed = {f.get("id") for f in fired if isinstance(f, dict)}
    inputs = [i for i in inputs if i.get("id") not in landed]
    entry = {"stored_at": today, "gates": gates, "inputs": inputs, "fired": fired}
    for k in PRESERVED_KEYS:
        if prev and k in prev:
            entry[k] = prev[k]
    return entry, prev


def write_closes_on(root: Path, did: str, entry: dict) -> bool:  # noqa: C901 — replace-or-insert
    """Replace or insert the `closes_on:` block inside the diamond's entry in active.yml, touching
    no other line. Returns True when the file changed. Bounds are indent-aware: a nested `- id:`
    (a fired entry, an input) must not end the diamond or the block; only a sibling item does."""
    path = root / ".claude" / "diamonds" / "active.yml"
    lines = path.read_text(encoding="utf-8").split("\n")
    id_re = re.compile(rf"^(\s*)- id: {re.escape(did)}\s*$")
    start = next((n for n, ln in enumerate(lines) if id_re.match(ln)), None)
    if start is None:
        return False
    item_indent = _indent_of(lines[start])
    field_indent = item_indent + 2

    def sibling_or_top(ln: str) -> bool:
        if not ln.strip():
            return False
        ind = _indent_of(ln)
        return (ind <= item_indent and ln.lstrip().startswith("- ")) or (
            ind == 0 and re.match(r"^[a-z_]+:", ln) is not None
        )

    end = start + 1
    while end < len(lines) and not sibling_or_top(lines[end]):
        end += 1
    rendered = _render_closes_on(entry, field_indent)

    def block_end(ln: str) -> bool:
        return bool(ln.strip()) and _indent_of(ln) <= field_indent

    cstart = next(
        (n for n in range(start + 1, end) if lines[n] == " " * field_indent + "closes_on:"), None
    )
    if cstart is not None:
        cend = cstart + 1
        while cend < end and not block_end(lines[cend]):
            cend += 1
        new = lines[:cstart] + rendered + lines[cend:]
    else:
        tstart = next(
            (
                n
                for n in range(start + 1, end)
                if lines[n] == " " * field_indent + "theory_gates_status:"
            ),
            None,
        )
        if tstart is not None:
            at = tstart + 1
            while at < end and not block_end(lines[at]):
                at += 1
        else:
            at = end
        while at > start + 1 and not lines[at - 1].strip():
            at -= 1
        new = lines[:at] + rendered + lines[at:]
    text = "\n".join(new)
    if text == "\n".join(lines):
        return False
    write_checked(path, text)
    return True


def _stamp_after_id(path: Path, id_line_re: str, key: str, text: str) -> bool:
    """Insert `key: >-` + text right after the line matching id_line_re, at that item's field
    indent, unless the item already carries `key`. Returns True when written."""
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").split("\n")
    rx = re.compile(id_line_re)
    start = next((n for n, ln in enumerate(lines) if rx.match(ln)), None)
    if start is None:
        return False
    item_indent = _indent_of(lines[start])
    field_indent = item_indent + 2
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        if ln.strip() and _indent_of(ln) <= item_indent:
            break
        end += 1
    if any(ln.startswith(" " * field_indent + key + ":") for ln in lines[start + 1 : end]):
        return False
    ins = _block_scalar(key, text, field_indent)
    new = lines[: start + 1] + ins + lines[start + 1 :]
    write_checked(path, "\n".join(new))
    return True


def stamp_readers(root: Path, did: str, entry: dict) -> list[str]:
    """`reader` on each watched assumption, `on_close` on each watched task, only where absent."""
    canvas = root / ".claude" / "canvas"
    stamped = []
    for inp in entry["inputs"]:
        if inp["kind"] == "assumption":
            ok = _stamp_after_id(
                canvas / "opportunities.yml",
                rf"^\s*- id: {re.escape(inp['id'])}\s*$",
                "reader",
                f"Named on diamonds/active.yml#{did}.closes_on (derived {entry['stored_at']}). "
                f"A verdict here is an input to closing {did}'s current phase; the session that "
                f"scores it re-runs derive_closing_path.py --diamond-id {did} --write and acts on "
                "the proposal it prints.",
            )
        else:
            ok = _stamp_after_id(
                canvas / "human-tasks.yml",
                rf"^\s*- id: {re.escape(inp['id'])}\s*$",
                "on_close",
                f"Named on diamonds/active.yml#{did}.closes_on (derived {entry['stored_at']}). "
                f"Closing this task is an input to closing {did}'s current phase; the session that "
                f"closes it re-runs derive_closing_path.py --diamond-id {did} --write and acts on "
                "the proposal it prints.",
            )
        if ok:
            stamped.append(inp["id"])
    return stamped


def all_diamond_ids(root: Path) -> list[str]:
    active = root / ".claude" / "diamonds" / "active.yml"
    if not active.exists():
        return []
    doc = load_yaml(active)
    return [
        str(d["id"])
        for key in ("active_diamonds", "diamonds")
        for d in (doc.get(key) or [])
        if isinstance(d, dict) and d.get("id")
    ]


def controller_line(
    did: str, entry: dict, prev: dict | None, changed: bool, stamped: list[str]
) -> str:
    """One line per diamond: a receipt, or a parked proposal when something fired."""
    new_fired = [
        f
        for f in entry["fired"]
        if not any(p.get("id") == f["id"] for p in ((prev or {}).get("fired") or []))
    ]
    if new_fired:
        return f"CLOSING PATH FIRED for {did}: " + " ".join(f["proposal"] for f in new_fired)
    pend = len(entry["gates"])
    if pend == 0:
        return f"closing-path {did}: every gate reads pass; nothing to store"
    parts = [f"closing-path {did}: {pend} gate(s) pending, {len(entry['inputs'])} input(s) watched"]
    parts.append("stored" if changed else "unchanged since last derivation")
    if stamped:
        parts.append(f"readers stamped on {', '.join(stamped)}")
    if not entry["inputs"]:
        parts.append("NOTHING ON RECORD moves a pending gate; that is the finding")
    return "; ".join(parts) + "."


def run_controller(root: Path, ids: list[str], write: bool, today: str) -> None:
    """One line per diamond: store (when asked and something is pending), stamp, report."""
    if not ids:
        print(
            f"closing-path: N/A — no diamonds in {root}/.claude/diamonds/active.yml; "
            "nothing to store"
        )
        return
    for did in ids:
        entry, prev = build_closes_on(root, did, today)
        if entry is None:
            print(f"closing-path: N/A — no diamond {did}")
            continue
        changed, stamped = False, []
        if write and entry["gates"]:
            changed = write_closes_on(root, did, entry)
            stamped = stamp_readers(root, did, entry)
        print(controller_line(did, entry, prev, changed, stamped))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Derive what would close a diamond's current phase.")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--diamond-id", default="")
    ap.add_argument(
        "--all", action="store_true", help="every diamond in active.yml (controller mode)"
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="store the derivation as closes_on on the diamond; stamp reader/on_close on inputs",
    )
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    if args.all or (args.write and args.diamond_id):
        ids = all_diamond_ids(root) if args.all else [args.diamond_id]
        run_controller(root, ids, args.write, args.today)
        if not args.diamond_id:
            return 0
    if not args.diamond_id:
        ap.error("--diamond-id or --all is required")
    r = derive(root, args.diamond_id, args.today)
    if r is None:
        print(
            f"closing-path: N/A — no diamond {args.diamond_id} in "
            f"{root}/.claude/diamonds/active.yml; nothing derived"
        )
        return 0
    d = r["diamond"]
    plural = "y" if r["n_opps"] == 1 else "ies"
    print(
        f"closing-path: {args.diamond_id} ({d.get('scale', '?')} {d.get('phase', '?')}, "
        f"confidence {d.get('confidence', '?')}); {r['n_opps']} open opportunit{plural} cite it"
    )
    if r["n_opps"] == 0:
        if r["outcomes"]:
            via = f"by id or by outcome ({', '.join(r['outcomes'])})"
        elif r["rolls_up_to_prose"]:
            first = r["rolls_up_to_prose"][0][:60]
            via = (
                f"by id, and its rolls_up_to is prose that keys to no outcome id "
                f"('{first}...'); set rolls_up_to to the id the opportunities roll up to, "
                f"e.g. opportunities.yml#desired_outcomes.<id>"
            )
        else:
            via = "by id, and the diamond names no rolls_up_to outcome"
        print(
            f"no open opportunity links to this diamond {via}; the leaf rows below are the tree "
            "unread, not the tree empty"
        )
    print("gate | what would flip it | owner | date")
    if not r["gates"]:
        print("(none pending) | every gate in theory_gates_status reads pass | - | -")
    for g, v in r["gates"].items():
        print(_gate_row(g, v, r))
    _print_inputs(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
