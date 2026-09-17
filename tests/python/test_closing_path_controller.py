"""Coverage tests for derive_closing_path.py --write / --all (the closing-path controller, v0.187.0).

Branches: --write stores closes_on on the diamond and stamps reader/on_close where absent; a second
write is idempotent and touches no other line; a hand-written reader is never overwritten; a
hand-written sibling field's routes_on_record is watched; an assumption verdict landing FIRES once
with a proposal and stays fired; a task closing fires; --all walks every diamond and says N/A on an
empty file; a diamond with every gate passing stores nothing; preserved sub-keys survive
re-derivation. In-process for the coverage floor.
"""

import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import derive_closing_path

    return derive_closing_path


def _run(root, capsys, *args):
    rc = _mod().main(["--project-dir", str(root), "--today", "2026-09-10", *args])
    return rc, capsys.readouterr().out


ACTIVE = """active_diamonds:
- id: l1
  scale: L1
  phase: define
  confidence: 0.6
  theory_gates_status:
    evidence: pass
    four_risks: pending
  notes: keep me
"""

OPPS = """opportunities:
- id: opp-1
  status: open
  diamond_ref: l1
  solutions:
  - id: sol-1a
    status: candidate
    assumptions:
    - id: a-1a-1
      statement: first leaf assumption
      verdict: null
    - id: a-1a-2
      statement: already has a hand reader
      reader: HAND-WRITTEN, keep me
      verdict: null
"""

TASKS = """schema_version: 1
pending_tasks:
- id: ht-1
  status: waiting
  horizon: '2026-09-13'
  diamond_ref: l1
"""


def _project(root, active=ACTIVE, opps=OPPS, tasks=TASKS):
    (root / ".claude" / "diamonds").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "diamonds" / "active.yml").write_text(active)
    (root / ".claude" / "canvas" / "opportunities.yml").write_text(opps)
    (root / ".claude" / "canvas" / "human-tasks.yml").write_text(tasks)


def _active(root):
    return yaml.safe_load((root / ".claude" / "diamonds" / "active.yml").read_text())


def _l1(root):
    return next(d for d in _active(root)["active_diamonds"] if d["id"] == "l1")


def test_write_stores_and_stamps(tmp_path, capsys):
    _project(tmp_path)
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert rc == 0 and "closing-path l1: 1 gate(s) pending, 3 input(s) watched; stored" in out
    c = _l1(tmp_path)["closes_on"]
    assert c["stored_at"] == "2026-09-10"
    assert [g["gate"] for g in c["gates"]] == ["four_risks"]
    assert {i["id"] for i in c["inputs"]} == {"a-1a-1", "a-1a-2", "ht-1"}
    assert _l1(tmp_path)["notes"] == "keep me"
    opps = yaml.safe_load((tmp_path / ".claude" / "canvas" / "opportunities.yml").read_text())
    a = {x["id"]: x for x in opps["opportunities"][0]["solutions"][0]["assumptions"]}
    assert "closes_on" in a["a-1a-1"]["reader"] and "l1" in a["a-1a-1"]["reader"]
    assert a["a-1a-2"]["reader"] == "HAND-WRITTEN, keep me"
    tasks = yaml.safe_load((tmp_path / ".claude" / "canvas" / "human-tasks.yml").read_text())
    assert "closes_on" in tasks["pending_tasks"][0]["on_close"]
    assert "readers stamped on a-1a-1, ht-1" in out


def test_second_write_is_idempotent(tmp_path, capsys):
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    before = {p: p.read_text() for p in (tmp_path / ".claude").rglob("*.yml")}
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "unchanged since last derivation" in out
    after = {p: p.read_text() for p in (tmp_path / ".claude").rglob("*.yml")}
    assert before == after


def test_assumption_verdict_fires_once(tmp_path, capsys):
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    p = tmp_path / ".claude" / "canvas" / "opportunities.yml"
    p.write_text(
        p.read_text().replace(
            "statement: first leaf assumption\n      verdict: null",
            "statement: first leaf assumption\n      verdict: SUPPORTS",
        )
    )
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "CLOSING PATH FIRED for l1: a-1a-1 has a verdict (SUPPORTS)" in out
    assert "/mycelium:diamond-progress l1" in out
    fired = _l1(tmp_path)["closes_on"]["fired"]
    assert [f["id"] for f in fired] == ["a-1a-1"] and fired[0]["landed_as"] == "verdict SUPPORTS"
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "CLOSING PATH FIRED" not in out and len(_l1(tmp_path)["closes_on"]["fired"]) == 1


def test_task_close_fires(tmp_path, capsys):
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    p = tmp_path / ".claude" / "canvas" / "human-tasks.yml"
    p.write_text(p.read_text().replace("status: waiting", "status: completed"))
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "CLOSING PATH FIRED for l1: ht-1 closed (completed)" in out


def test_hand_written_sibling_routes_are_watched(tmp_path, capsys):
    active = (
        ACTIVE
        + """  define_closes_on:
    routes_on_record:
    - assumption: opportunities.yml#opp-9.sol-9a.assumptions[a-9a-1]
      fires_when: hand-named route
"""
    )
    opps = (
        OPPS
        + """- id: opp-9
  status: closed
  solutions:
  - id: sol-9a
    status: candidate
    assumptions:
    - id: a-9a-1
      statement: on a closed node the script cannot link
      verdict: null
"""
    )
    _project(tmp_path, active=active, opps=opps)
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "a-9a-1" in {i["id"] for i in _l1(tmp_path)["closes_on"]["inputs"]}
    p = tmp_path / ".claude" / "canvas" / "opportunities.yml"
    p.write_text(
        p.read_text().replace(
            "cannot link\n      verdict: null", "cannot link\n      verdict: REFUTES"
        )
    )
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "CLOSING PATH FIRED for l1: a-9a-1 has a verdict (REFUTES)" in out
    # v0.226.3: a landed input is listed under `fired` and nowhere else. A hand-named route stays in
    # routes_on_record for good, so it was re-added to `inputs` on every run, the same id sat in both
    # lists, and validate_canvas rejected the script's own output on a duplicate id. Met on the dogfood
    # canvas 2026-09-17, the first time a hand-routed input got a verdict.
    stored = _l1(tmp_path)["closes_on"]
    assert "a-9a-1" in {f["id"] for f in stored["fired"]}
    assert "a-9a-1" not in {i["id"] for i in stored["inputs"]}
    ids = [e["id"] for e in stored["inputs"] + stored["fired"]]
    assert len(ids) == len(set(ids)), ids
    # and it stays that way on the next run, which is when the re-adding happened
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    again = _l1(tmp_path)["closes_on"]
    ids = [e["id"] for e in again["inputs"] + again["fired"]]
    assert len(ids) == len(set(ids)), ids


def test_preserved_subkeys_survive(tmp_path, capsys):
    active = (
        ACTIVE
        + """  closes_on:
    stored_at: '2026-09-01'
    gates: []
    inputs: []
    fired: []
    then_do:
    - flip four_risks against the chosen leaf
    caveat: hand-written, keep me
"""
    )
    _project(tmp_path, active=active)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    c = _l1(tmp_path)["closes_on"]
    assert c["stored_at"] == "2026-09-10" and c["caveat"] == "hand-written, keep me"
    assert c["then_do"] == ["flip four_risks against the chosen leaf"]


def test_all_walks_every_diamond_and_all_pass_stores_nothing(tmp_path, capsys):
    active = (
        ACTIVE
        + """- id: l4
  scale: L4
  phase: deliver
  theory_gates_status:
    dora: pass
"""
    )
    _project(tmp_path, active=active)
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert "closing-path l1: 1 gate(s) pending" in out
    assert "closing-path l4: every gate reads pass; nothing to store" in out
    assert "closes_on" not in next(
        d for d in _active(tmp_path)["active_diamonds"] if d["id"] == "l4"
    )


def test_all_on_empty_file_is_na(tmp_path, capsys):
    _project(tmp_path, active="active_diamonds: []\n")
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert rc == 0 and "N/A" in out


def test_nothing_on_record_is_named(tmp_path, capsys):
    _project(tmp_path, opps="opportunities: []\n", tasks="schema_version: 1\npending_tasks: []\n")
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "NOTHING ON RECORD moves a pending gate" in out


def test_ruling_on_fired_entry_is_preserved_and_rendered(tmp_path, capsys):
    """0.197.0: the fired block is script-owned, but the answer to its own question is not.
    A hand-written `ruling:` and `ruled_at:` under a fired entry survive re-derivation."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    opps = OPPS.replace("      verdict: null\n", "      verdict: validated\n", 1)
    (tmp_path / ".claude" / "canvas" / "opportunities.yml").write_text(opps)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    fired = _l1(tmp_path)["closes_on"]["fired"]
    assert fired and fired[0]["id"] == "a-1a-1"
    assert "write `ruling:` and `ruled_at:`" in fired[0]["proposal"]
    text = (tmp_path / ".claude" / "diamonds" / "active.yml").read_text()
    text = text.replace(
        "      noticed_at: '2026-09-10'\n",
        "      noticed_at: '2026-09-10'\n      ruling: not the riskiest assumption; does not choose\n      ruled_at: '2026-09-11'\n",
        1,
    )
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(text)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    fired = _l1(tmp_path)["closes_on"]["fired"]
    assert fired[0]["ruling"] == "not the riskiest assumption; does not choose"
    assert fired[0]["ruled_at"] == "2026-09-11"
