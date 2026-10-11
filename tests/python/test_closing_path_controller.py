"""Coverage tests for derive_closing_path.py --write / --all (the closing-path controller, v0.187.0).

Branches: --write stores closes_on on the diamond and stamps reader/on_close where absent; a second
write is idempotent and touches no other line; a hand-written reader is never overwritten; a
hand-written sibling field's routes_on_record is watched; an assumption verdict landing FIRES once
with a proposal and stays fired; a task closing fires; --all walks every diamond and says N/A on an
empty file; a diamond with every gate passing stores nothing; preserved sub-keys survive
re-derivation. In-process for the coverage floor.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
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
    jtbd: pass
    cynefin: pass
    bias: pass
    corrections: pass
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
    evidence: pass
    bias: pass
    security: pass
    bvssh: pass
    service_quality: pass
    delivery_metrics: pass
    corrections: pass
"""
    )
    _project(tmp_path, active=active)
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert "closing-path l1: 1 gate(s) pending" in out
    assert "closing-path l4: every gate reads pass; nothing to store" in out
    assert "closes_on" not in next(
        d for d in _active(tmp_path)["active_diamonds"] if d["id"] == "l4"
    )


def test_a_gate_never_evaluated_is_pending_not_passed(tmp_path, capsys):
    """v0.278.0, E2E rung L4-define on 0.276.0: an L4 with no gate status printed "every gate
    reads pass; nothing to store", and the builder read that as nothing to do."""
    bare = ACTIVE + "- id: l4\n  scale: L4\n  phase: discover\n"
    _project(tmp_path, active=bare)
    rc, out = _run(tmp_path, capsys, "--all")
    assert "closing-path l4: every gate reads pass" not in out
    assert "closing-path l4: 3 gate(s) pending" in out  # evidence, bias, corrections
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l4")
    assert "evidence (not recorded) | never evaluated" in out and "| agent | now" in out


def test_the_assessment_records_gates_on_every_outcome():
    """The closing path reads `theory_gates_status`; the skill that evaluates gates must write it
    on a needs-evidence ruling too, or the next session re-derives every gate from nothing."""
    skill = (Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "skills"
             / "diamond-progress" / "SKILL.md").read_text()
    assert "in `theory_gates_status` on the diamond, on\n        every outcome" in skill


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


# --------------------------------------- an L0 or L1 diamond closes on its own bar (v0.227.0)
# Each scale has its own object and only two of them are leaves. Dogfood 2026-09-17: a verdict
# landed on a solution-level assumption, this script announced "the path can now be chosen" on
# the STRATEGY diamond, and the founder ruled that it could not: that diamond is decided by its
# definition of done, read from one task. The script was asking an L3 question of an L1 object.

DOD = """  definition_of_done:
    signal: three counts, read from human-tasks.yml#ht-9
    kill_criterion:
      state: two kills
      date: '2026-10-28'
    log:
    - date: '2026-09-01'
      text: history that mentions ht-77, which is not an input to anything
"""

TASKS_DOD = TASKS + """- id: ht-9
  status: pending
  horizon: '2026-10-28'
- id: ht-77
  status: pending
  horizon: '2026-12-01'
"""


def _input_ids(root):
    return {i["id"] for i in _l1(root)["closes_on"]["inputs"]}


def test_an_l1_diamond_with_a_bar_watches_what_the_bar_reads_not_leaves(tmp_path, capsys):
    _project(tmp_path, active=ACTIVE + DOD, tasks=TASKS_DOD)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    ids = _input_ids(tmp_path)
    assert "ht-9" in ids, "the task the bar reads from is an input even with no diamond_ref"
    assert "ht-1" in ids, "a task that names the diamond is still an input"
    assert "a-1a-1" not in ids and "a-1a-2" not in ids, "a leaf assumption does not close a strategy bet"
    assert "ht-77" not in ids, "a task mentioned only in the bar's LOG is history, not an input"


DOD_PREMORTEM = """  definition_of_done:
    signal: three counts, read from human-tasks.yml#ht-9
    kill_criterion:
      state: two kills, counted on ht-1
      date: '2026-10-28'
      premortem: >-
        It is 2026-12-10 and the bar failed: moderators removed the replies, as one was removed
        on 2026-10-06 (ht-77).
"""


def test_a_task_the_premortem_mentions_is_history_not_an_input(tmp_path, capsys):
    """Dogfood 2026-10-09 (v0.318.1): an L1 premortem named another diamond's task and the check
    made it a closing input; the duplicate it wrote then failed validate_canvas."""
    _project(tmp_path, active=ACTIVE + DOD_PREMORTEM, tasks=TASKS_DOD)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    ids = _input_ids(tmp_path)
    assert "ht-77" not in ids, "a premortem is a story told in the past tense"
    assert {"ht-9", "ht-1"} <= ids, "the bar's signal and its kill state are still read"


def test_the_printed_path_names_the_bar_its_date_and_its_tasks(tmp_path, capsys):
    _project(tmp_path, active=ACTIVE + DOD, tasks=TASKS_DOD)
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1")
    assert "definition of done" in out.lower()
    assert "2026-10-28" in out and "ht-9" in out
    assert "leaf assumptions without a verdict" not in out
    assert "DATE PASSED" not in out


def test_an_unlinked_tree_is_not_reported_on_a_diamond_that_closes_on_its_bar(tmp_path, capsys):
    _project(tmp_path, active=ACTIVE + DOD, opps="opportunities: []\n", tasks=TASKS_DOD)
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1")
    assert "tree unread" not in out and "definition of done" in out.lower()


def test_a_passed_date_is_said_out_loud(tmp_path, capsys):
    _project(tmp_path, active=ACTIVE + DOD, tasks=TASKS_DOD)
    _mod().main(["--project-dir", str(tmp_path), "--today", "2026-11-01", "--diamond-id", "l1"])
    assert "DATE PASSED" in capsys.readouterr().out


def test_the_four_risks_row_stops_asking_an_l1_diamond_for_a_leaf(tmp_path, capsys):
    _project(tmp_path, active=ACTIVE + DOD, tasks=TASKS_DOD)
    rc, out = _run(tmp_path, capsys, "--diamond-id", "l1")
    row = next(ln for ln in out.splitlines() if ln.startswith("four_risks"))
    assert "definition of done" in row and "chosen leaf" not in row


def test_a_solution_diamond_keeps_its_leaves(tmp_path, capsys):
    """NEGATIVE CONTROL. L2 and L3 ARE closed by leaves; a bar on them changes nothing here."""
    _project(tmp_path, active=(ACTIVE + DOD).replace("scale: L1", "scale: L3"), tasks=TASKS_DOD)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "a-1a-1" in _input_ids(tmp_path)


def test_an_l1_diamond_with_no_bar_is_unchanged(tmp_path, capsys):
    """NEGATIVE CONTROL. No definition_of_done, nothing to read: the old derivation stands."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "a-1a-1" in _input_ids(tmp_path)


def test_a_definition_of_done_that_only_points_at_an_outcome_is_not_a_bar(tmp_path, capsys):
    """NEGATIVE CONTROL, found by an existing test failing while this was built: a block holding
    only `rolls_up_to` names no signal, no date and no task, so there is nothing to derive from."""
    pointer = "  definition_of_done:\n    rolls_up_to: opportunities.yml#desired_outcomes.adoption\n"
    _project(tmp_path, active=ACTIVE + pointer)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "a-1a-1" in _input_ids(tmp_path)


def test_routes_under_a_superseded_condition_are_no_longer_watched(tmp_path, capsys):
    active = ACTIVE + """  define_closes_on:
    superseded: retired by the founder; the bar decides this diamond now
    routes_on_record:
    - assumption: opportunities.yml#opp-9.sol-9a.assumptions[a-9a-1]
      fires_when: hand-named route, kept as history
"""
    opps = OPPS + """- id: opp-9
  status: closed
  solutions:
  - id: sol-9a
    status: candidate
    assumptions:
    - id: a-9a-1
      statement: on a closed node
      verdict: null
"""
    _project(tmp_path, active=active, opps=opps)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    assert "a-9a-1" not in _input_ids(tmp_path)


# v0.312.1: a parked diamond is a ruling that nothing moves it for now, not an unnoticed gap.
_EMPTY_OPPS = "opportunities: []\n"
_EMPTY_TASKS = "schema_version: 1\npending_tasks: []\n"
_BLOCKED = """active_diamonds:
- id: l1x
  scale: L1
  theory_gates_status:
    evidence: pending
    bias: pending
"""


def test_unparked_diamond_with_no_inputs_is_the_finding(tmp_path, capsys):
    _project(tmp_path, active=_BLOCKED, opps=_EMPTY_OPPS, tasks=_EMPTY_TASKS)
    rc, out = _run(tmp_path, capsys, "--all")
    assert "NOTHING ON RECORD" in out


def test_parked_diamond_is_reported_as_parked_and_not_derived(tmp_path, capsys):
    parked = _BLOCKED.replace("  scale: L1\n", "  scale: L1\n  state: parked\n  parked_at: '2026-10-04'\n"
                              "  resume_conditions:\n  - a runtime drops hooks\n  - review 2027-01-03\n")
    _project(tmp_path, active=parked, opps=_EMPTY_OPPS, tasks=_EMPTY_TASKS)
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert "NOTHING ON RECORD" not in out
    assert "l1x: parked since 2026-10-04; resumes on 2 condition(s)" in out
    d = next(x for x in _active(tmp_path)["active_diamonds"] if x["id"] == "l1x")
    assert "closes_on" not in d  # nothing stored for a parked diamond


# v0.312.2: every closed state is not derived, not only parked. The dogfood L4 was archived in place
# (`state: archived` left in active_diamonds) and kept a stored closing path that fired proposals.
@pytest.mark.parametrize("state", ["archived", "completed", "killed", "retargeted"])
def test_a_closed_diamond_is_reported_closed_and_not_derived(tmp_path, capsys, state):
    closed = _BLOCKED.replace("  scale: L1\n", f"  scale: L1\n  state: {state}\n")
    _project(tmp_path, active=closed, opps=_EMPTY_OPPS, tasks=_EMPTY_TASKS)
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert "NOTHING ON RECORD" not in out
    assert f"l1x: closed ({state}); not derived." in out
    d = next(x for x in _active(tmp_path)["active_diamonds"] if x["id"] == "l1x")
    assert "closes_on" not in d


def test_an_active_or_blocked_state_is_still_derived(tmp_path, capsys):
    open_ = _BLOCKED.replace("  scale: L1\n", "  scale: L1\n  state: blocked\n")
    _project(tmp_path, active=open_, opps=_EMPTY_OPPS, tasks=_EMPTY_TASKS)
    rc, out = _run(tmp_path, capsys, "--all", "--write")
    assert "not derived" not in out and "NOTHING ON RECORD" in out


# ----------------------- hand-written content inside the derived keys is not overwritten (v0.321.2)
# Session start runs `--all --write` on every start and replaced `gates`, `inputs` and `fired`
# whole. A `note:` someone wrote on a gate row, an input of their own, any other key under
# `closes_on`: gone after the next start, with nothing said. The script now leaves such a block
# as it is and says which diamond, which place and where the content can live.

HAND_WRITTEN = [
    # (text the script wrote, the same text with a person's addition, the place the line names)
    ("    - gate: four_risks\n",
     "    - gate: four_risks\n      note: hand-written, keep me\n", "gates[0].note"),
    ("      id: a-1a-1\n",
     "      id: a-1a-1\n      note: ask Kari before scoring this\n", "inputs[0].note"),
    ("      id: a-1a-1\n",
     "      id: a-1a-1\n      date: '2026-09-20'\n", "inputs[0].date"),
    ("    inputs:\n",
     "    inputs:\n    - kind: question\n      id: q-1\n      text: who owns the pricing page\n",
     "inputs[0].kind (question)"),
    ("    inputs:\n", "    inputs:\n    - a line someone typed here\n", "inputs[0] (not a mapping)"),
    ("    fired: []\n", "    fired: []\n    note: hand-written beside the derived keys\n", "(note)"),
    ("    fired: []\n",
     "    fired:\n    - id: a-9\n      kind: assumption\n      note: typed by hand\n",
     "fired[0].note"),
]


def _yml(root):
    return {p: p.read_text() for p in (root / ".claude").rglob("*.yml")}


def _hand_edit(root, old, new):
    active = root / ".claude" / "diamonds" / "active.yml"
    text = active.read_text()
    assert text.count(old) == 1, old
    active.write_text(text.replace(old, new))


@pytest.mark.parametrize(("old", "new", "place"), HAND_WRITTEN)
def test_hand_written_content_in_a_derived_key_is_not_overwritten(tmp_path, capsys, old, new, place):
    """RED ON 0.321.0: the next `--write` dropped the addition and printed the usual receipt."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    _hand_edit(tmp_path, old, new)
    before = _yml(tmp_path)
    rc, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-11")
    assert rc == 0
    assert "CLOSING PATH NOT STORED for l1:" in out          # which diamond
    assert place in out                                        # which place
    assert "caveat" in out and "then_do" in out                # where it can live
    assert "closing-path l1:" not in out                       # no receipt for a store that did not happen
    assert _yml(tmp_path) == before                            # the block, and every other file, untouched
    assert _l1(tmp_path)["closes_on"]["stored_at"] == "2026-09-10"


def test_the_warning_is_one_line_and_starts_with_the_words_session_start_greps(tmp_path, capsys):
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    _hand_edit(tmp_path, *HAND_WRITTEN[0][:2])
    _, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-11")
    lines = [ln for ln in out.splitlines() if "NOT STORED" in ln]
    assert len(lines) == 1 and lines[0].startswith("CLOSING PATH NOT STORED for l1: ")
    hook = (SCRIPTS.parent / "hooks" / "session-start.sh").read_text()
    assert "grep '^CLOSING PATH NOT STORED'" in hook


def test_many_places_are_counted_not_listed(tmp_path):
    stored = {"gates": [{"gate": "g", "a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6}]}
    line = _mod().not_stored_line("l1", _mod().hand_written(stored))
    assert "gates[0].a, gates[0].b, gates[0].c, gates[0].d and 2 more" in line


def test_a_landing_waits_until_the_content_is_moved_and_then_fires(tmp_path, capsys):
    """Nothing is lost by refusing: the stored block still says the input was open, so the
    landing fires on the first run that can store it."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    _hand_edit(tmp_path, *HAND_WRITTEN[0][:2])
    opps = tmp_path / ".claude" / "canvas" / "opportunities.yml"
    opps.write_text(opps.read_text().replace(
        "statement: first leaf assumption\n      verdict: null",
        "statement: first leaf assumption\n      verdict: SUPPORTS"))
    _, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-11")
    assert "CLOSING PATH NOT STORED for l1:" in out and "CLOSING PATH FIRED" not in out
    assert _l1(tmp_path)["closes_on"]["fired"] == []
    # the person moves the note to a key that is kept
    _hand_edit(tmp_path, "      note: hand-written, keep me\n", "")
    _hand_edit(tmp_path, "    fired: []\n", "    fired: []\n    caveat: hand-written, keep me\n")
    _, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-12")
    assert "CLOSING PATH FIRED for l1: a-1a-1 has a verdict (SUPPORTS)" in out
    assert "NOT STORED" not in out
    stored = _l1(tmp_path)["closes_on"]
    assert stored["caveat"] == "hand-written, keep me" and stored["stored_at"] == "2026-09-12"


def test_a_diamond_with_nothing_to_store_is_not_warned_about(tmp_path, capsys):
    """No pending gate means no write, so nothing hand-written is at risk and nothing is said."""
    passed = ACTIVE.replace("four_risks: pending", "four_risks: pass").replace(
        "  notes: keep me\n",
        "  closes_on:\n    stored_at: '2026-09-01'\n    gates: []\n    inputs: []\n    fired: []\n"
        "    note: hand-written beside the derived keys\n  notes: keep me\n")
    _project(tmp_path, active=passed)
    before = _yml(tmp_path)
    _, out = _run(tmp_path, capsys, "--all", "--write")
    assert "closing-path l1: every gate reads pass; nothing to store" in out
    assert "NOT STORED" not in out and _yml(tmp_path) == before


def test_control_a_block_the_script_wrote_is_rewritten_exactly_as_before(tmp_path, capsys):
    """GREEN ON 0.321.0 TOO. Nothing hand-written, so the next derivation replaces the block."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    first = (tmp_path / ".claude" / "diamonds" / "active.yml").read_text()
    _, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-11")
    assert "NOT STORED" not in out
    assert "closing-path l1: 1 gate(s) pending, 3 input(s) watched; stored." in out
    second = (tmp_path / ".claude" / "diamonds" / "active.yml").read_text()
    assert second == first.replace("stored_at: '2026-09-10'", "stored_at: '2026-09-11'")
    assert set(_l1(tmp_path)["closes_on"]) == {"stored_at", "gates", "inputs", "fired"}


KEPT = """  closes_on:
    stored_at: '2026-09-01'
    gates: []
    inputs: []
    fired: []
    routes_on_record:
    - assumption: opportunities.yml#opp-1.sol-1a.assumptions[a-1a-1]
      fires_when: the first leaf gets a verdict
    then_do:
    - flip four_risks against the chosen leaf
    caveat: hand-written, keep me
    why_a_field: the log is not read when the condition is met
    does_not_close:
    - a verdict on a leaf that is not the front runner
"""


def test_control_the_five_kept_keys_and_a_ruling_survive_with_no_warning(tmp_path, capsys):
    """GREEN ON 0.321.0 TOO. The keys a person may write are still carried across."""
    _project(tmp_path, active=ACTIVE + KEPT)
    was = _l1(tmp_path)["closes_on"]
    _, out = _run(tmp_path, capsys, "--all", "--write")
    now = _l1(tmp_path)["closes_on"]
    assert "NOT STORED" not in out and now["stored_at"] == "2026-09-10"
    for key in _mod().PRESERVED_KEYS:
        assert now[key] == was[key], key
    # a verdict lands, the person rules on it under the fired entry, and that survives too
    opps = tmp_path / ".claude" / "canvas" / "opportunities.yml"
    opps.write_text(opps.read_text().replace("      verdict: null\n", "      verdict: validated\n", 1))
    _run(tmp_path, capsys, "--all", "--write")
    _hand_edit(tmp_path, "      noticed_at: '2026-09-10'\n",
               "      noticed_at: '2026-09-10'\n      ruling: does not choose a path\n"
               "      ruled_at: '2026-09-11'\n")
    _, out = _run(tmp_path, capsys, "--all", "--write", "--today", "2026-09-12")
    again = _l1(tmp_path)["closes_on"]
    assert "NOT STORED" not in out and again["stored_at"] == "2026-09-12"
    assert again["fired"][0]["ruling"] == "does not choose a path"
    for key in _mod().PRESERVED_KEYS:
        assert again[key] == was[key], key


def test_what_the_script_writes_and_what_a_person_may_write_is_not_hand_written():
    """The shapes the refusal must never fire on: every key the renderer emits, the five kept
    keys, and a ruling on a fired entry."""
    wrote = {
        "stored_at": "2026-09-10",
        "gates": [{"gate": "four_risks", "status": "pending", "what_would_flip_it": "x",
                   "owner": "human", "date": "-"}],
        "inputs": [{"kind": "assumption", "id": "a-1", "ref": "r", "state": "no verdict"},
                   {"kind": "task", "id": "ht-1", "ref": "r", "state": "waiting",
                    "date": "2026-09-13"}],
        "fired": [{"id": "a-2", "kind": "assumption", "landed_as": "verdict x",
                   "noticed_at": "2026-09-10", "proposal": "p", "ruling": "no",
                   "ruled_at": "2026-09-11"}],
        **dict.fromkeys(_mod().PRESERVED_KEYS, "kept"),
    }
    assert _mod().hand_written(wrote) == []
    assert _mod().hand_written({"gates": None, "inputs": [], "fired": []}) == []
    assert _mod().hand_written(None) == [] and _mod().hand_written("a string") == []
    odd = {"gates": "see the notes", "inputs": [{"kind": "task", "id": "t"}, 7],
           "fired": [{"id": "a-3"}]}
    assert _mod().hand_written(odd) == [
        "gates (not a list)", "inputs[1] (not a mapping)", "fired[0] (no kind)",
        "fired[0] (no landed_as)", "fired[0] (no noticed_at)", "fired[0] (no proposal)"]


def _session_start(root, *mode):
    plugin = SCRIPTS.parent
    env = {"CLAUDE_PROJECT_DIR": str(root), "CLAUDE_PLUGIN_ROOT": str(plugin),
           "MYCELIUM_CROSS_REPO_WATCH": "", "MYCELIUM_SESSION_START_BUDGET": "600",
           "TMPDIR": str(root), "HOME": str(root),
           "PATH": str(Path(sys.executable).parent) + os.pathsep + "/usr/bin:/bin"}
    done = subprocess.run(["bash", str(plugin / "hooks" / "session-start.sh"), *mode],
                          input="", capture_output=True, text=True, env=env, check=False)
    assert done.returncode == 0, done.stderr[-400:]
    return json.loads(done.stdout) if done.stdout.strip() else {}


def test_the_warning_reaches_the_agent_through_session_start(tmp_path, capsys):
    """RED ON 0.321.0: the hook relayed only FIRED lines and a NOTHING ON RECORD count, threw the
    script's stderr away, and the note was gone when the hook returned. This runs the HOOK."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    _hand_edit(tmp_path, *HAND_WRITTEN[0][:2])
    said = _session_start(tmp_path)["hookSpecificOutput"]["additionalContext"]
    assert "CLOSING PATH NOT STORED for l1:" in said and "gates[0].note" in said
    assert "caveat" in said
    assert _l1(tmp_path)["closes_on"]["gates"][0]["note"] == "hand-written, keep me"


def test_the_background_tier_stores_the_warning_for_the_next_prompt(tmp_path, capsys):
    """Claude Code runs the heavy tier with --async; what it relays is the cache preflight.sh
    delivers at the next prompt. RED ON 0.321.0 for the same reason as the test above."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    _hand_edit(tmp_path, *HAND_WRITTEN[0][:2])
    assert _session_start(tmp_path, "--async") == {}
    cache = json.loads((tmp_path / ".claude" / "state" / "session-checks.json").read_text())
    assert "CLOSING PATH NOT STORED for l1:" in cache["reminders"]
    assert _l1(tmp_path)["closes_on"]["gates"][0]["note"] == "hand-written, keep me"


def test_control_session_start_says_nothing_about_a_block_the_script_wrote(tmp_path, capsys):
    """GREEN ON 0.321.0 TOO."""
    _project(tmp_path)
    _run(tmp_path, capsys, "--diamond-id", "l1", "--write")
    said = _session_start(tmp_path).get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "NOT STORED" not in said
    assert _l1(tmp_path)["closes_on"]["stored_at"] != "2026-09-10"  # re-derived, as before
