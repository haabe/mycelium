"""Coverage tests for derive_closing_path.py — what would close a diamond's phase, off the record.

Branches: no active.yml -> N/A; unknown diamond -> N/A; all gates pass; pending four_risks with no
leaves; STALE four_risks (every live leaf reviewed); leaf assumptions with and without a named test;
open task with horizon; owed ruling in what_would_move_it; cynefin/evidence/other gate rows; nothing on
record line; unparseable file speaks. Runs in-process for the per-file coverage floor.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import derive_closing_path
    return derive_closing_path


def _run(root, capsys, did="l1"):
    rc = _mod().main(["--project-dir", str(root), "--diamond-id", did])
    return rc, capsys.readouterr().out


def _project(root, active, opps="opportunities: []\n", tasks=None):
    (root / ".claude" / "diamonds").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "diamonds" / "active.yml").write_text(active)
    (root / ".claude" / "canvas" / "opportunities.yml").write_text(opps)
    if tasks is not None:
        (root / ".claude" / "canvas" / "human-tasks.yml").write_text(tasks)


ACTIVE = """active_diamonds:
- id: l1
  scale: L1
  phase: define
  confidence: 0.6
  theory_gates_status:
    evidence: pass
    four_risks: pending
    cynefin: pending
    bias: pass-with-risk
"""


def test_no_active_is_na(tmp_path, capsys):
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "N/A" in out


def test_unknown_diamond_is_na(tmp_path, capsys):
    _project(tmp_path, ACTIVE)
    rc, out = _run(tmp_path, capsys, "l9")
    assert rc == 0 and "N/A" in out


def test_all_pass_says_none_pending(tmp_path, capsys):
    _project(tmp_path, "active_diamonds:\n- id: l1\n  theory_gates_status:\n    evidence: pass\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "(none pending)" in out


def test_pending_gates_with_nothing_on_record(tmp_path, capsys):
    _project(tmp_path, ACTIVE)
    rc, out = _run(tmp_path, capsys)
    assert "four_risks (pending)" in out and "cynefin (pending)" in out and "bias (pass-with-risk)" in out
    assert "nothing on record moves any pending gate" in out


def test_stale_four_risks_when_every_live_leaf_is_reviewed(tmp_path, capsys):
    opps = """opportunities:
- id: opp-1
  status: open
  rolls_up_to: l1
  solutions:
  - id: sol-1a
    status: candidate
    four_risks: {value: {risk_level: high}, usability: {risk_level: medium}, feasibility: {risk_level: low}, viability: {risk_level: medium}}
    assumptions:
    - id: a-1
      statement: 'the builder stalls on who and how'
      verdict: null
      test_2026_09_09: 'read the replies already in hand against a pre-registered reading'
"""
    _project(tmp_path, ACTIVE, opps)
    rc, out = _run(tmp_path, capsys)
    assert "STALE FIELD" in out and "1 of 1" in out
    assert "a-1" in out and "test named" in out


def test_leaf_without_named_test_is_called_out(tmp_path, capsys):
    opps = """opportunities:
- id: opp-2
  status: open
  canvas_refs: ['diamonds/active.yml#l1']
  solutions:
  - id: sol-2a
    status: proposed
    assumptions:
    - id: a-2
      statement: 'something'
      verdict: null
  - id: sol-2b
    status: shipped
    assumptions:
    - id: a-3
      verdict: null
"""
    _project(tmp_path, ACTIVE, opps)
    rc, out = _run(tmp_path, capsys)
    assert "NO TEST NAMED" in out and "a-3" not in out
    assert "four_risks (pending) | a chosen leaf" in out and "0 of 1" in out


def test_open_task_horizon_and_owed_ruling(tmp_path, capsys):
    opps = """opportunities:
- id: opp-3
  status: open
  rolls_up_to: l1
  what_would_move_it: 'the founder ruling on sol-3a; then the 2026-10-02 close'
"""
    tasks = """pending_tasks:
- id: ht-1
  status: waiting
  diamond_ref: l1
  horizon: '2026-09-13'
- id: ht-2
  status: completed
  diamond_ref: l1
completed_tasks:
- id: ht-3
  status: completed
  diamond_ref: l1
"""
    _project(tmp_path, ACTIVE, opps, tasks)
    rc, out = _run(tmp_path, capsys)
    assert "ht-1 waiting | horizon 2026-09-13" in out and "ht-2" not in out and "ht-3" not in out
    assert "rulings already asked" in out and "opp-3" in out


def test_unparseable_file_speaks(tmp_path, capsys):
    _project(tmp_path, "active_diamonds: [\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "cannot parse" in out and "N/A" in out


OUTCOME_ACTIVE = """active_diamonds:
- id: l1
  scale: L1
  phase: define
  confidence: 0.6
  definition_of_done:
    rolls_up_to: opportunities.yml#desired_outcomes.adoption
  theory_gates_status:
    four_risks: pending
"""

OUTCOME_OPPS = """opportunities:
- id: opp-1
  status: open
  rolls_up_to: adoption
  solutions:
  - id: sol-1a
    status: candidate
    four_risks: {value: high, usability: medium, feasibility: low, viability: medium}
    assumptions:
    - id: a-1a-1
      statement: outcome-linked leaf is seen
      verdict: null
"""


def test_outcome_rooted_tree_is_seen(tmp_path, capsys):
    """Dogfood 2026-09-09: every opportunity carried `rolls_up_to: adoption` (an outcome, per the
    one-root ruling) and no diamond id, so the script read 0 of 0 leaves for every diamond."""
    _project(tmp_path, OUTCOME_ACTIVE, OUTCOME_OPPS)
    rc, out = _run(tmp_path, capsys)
    assert rc == 0
    assert "1 open opportunity cite it" in out
    assert "a-1a-1" in out and "outcome-linked leaf is seen" in out
    assert "tree unread" not in out


def test_no_link_by_id_or_outcome_says_so(tmp_path, capsys):
    """An empty leaf table must be distinguishable from a tree the script cannot read."""
    _project(tmp_path, OUTCOME_ACTIVE, OUTCOME_OPPS.replace("rolls_up_to: adoption",
                                                            "rolls_up_to: retention"))
    rc, out = _run(tmp_path, capsys)
    assert rc == 0
    assert "0 open opportunities cite it" in out
    assert "by id or by outcome (adoption)" in out and "tree unread" in out


def test_no_outcome_on_diamond_names_that(tmp_path, capsys):
    _project(tmp_path, ACTIVE, OUTCOME_OPPS)
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "names no rolls_up_to outcome" in out


# --- 0.197.0: pre-registered reads, prose rolls_up_to ---------------------------------------

TASKS_WITH_READS = """schema_version: 1
pending_tasks:
- id: ht-1
  status: waiting
  horizon: '2026-09-22'
  diamond_ref: l1
  created_at: '2026-09-08'
  read_dates:
  - '2026-09-10 (48 h): views, ratio, removal check'
  - '2026-09-22 (+14): full read'
- id: ht-2
  status: waiting
  horizon: '2026-09-22'
  diamond_ref: l1
  created_at: '2026-09-08'
  read_48h_2026_09_11: recorded a day late
  read_dates:
  - date: '2026-09-10'
    what: 48 h read
"""


def _run_today(root, capsys, today, did="l1"):
    rc = _mod().main(["--project-dir", str(root), "--diamond-id", did, "--today", today])
    return rc, capsys.readouterr().out


def test_read_due_is_printed_when_unrecorded(tmp_path, capsys):
    _project(tmp_path, ACTIVE, tasks=TASKS_WITH_READS)
    _, out = _run_today(tmp_path, capsys, "2026-09-11")
    assert "READ DUE on 1 task(s)" in out
    assert "ht-1 | read dated 2026-09-10 | 48 h): views, ratio, removal check" in out
    # ht-2 recorded activity on 09-11 (a dated field name), so its 09-10 read is not due
    assert "ht-2 | read dated" not in out
    # the future read shows as the task's next read, not as due
    assert "ht-1 waiting | horizon 2026-09-22 | next read 2026-09-22" in out


def test_read_not_due_before_its_date(tmp_path, capsys):
    _project(tmp_path, ACTIVE, tasks=TASKS_WITH_READS)
    _, out = _run_today(tmp_path, capsys, "2026-09-09")
    assert "READ DUE" not in out
    assert "next read 2026-09-10" in out


def test_reads_for_states_and_undated_strings():
    m = _mod()
    t = {
        "read_dates": ["2026-09-10 (48 h)", "no date here", {"date": "2026-09-30", "what": "x"}],
        "touch_log": [{"date": "2026-09-10", "direction": "internal"}],
    }
    rows = m.reads_for(t, "2026-09-11")
    assert [r["state"] for r in rows] == ["recorded", "upcoming"]
    assert rows[0]["what"] == "48 h"


def test_prose_rolls_up_to_is_named_not_silent(tmp_path, capsys):
    active = ACTIVE + """  definition_of_done:
    rolls_up_to: 'l0-purpose - evidence that the switch happens in the wild.'
"""
    opps = "opportunities:\n- id: opp-1\n  status: open\n  rolls_up_to: adoption\n  solutions: []\n"
    _project(tmp_path, active, opps=opps)
    _, out = _run(tmp_path, capsys)
    assert "0 open opportunities cite it" in out
    assert "is prose that keys to no outcome id" in out
    assert "opportunities.yml#desired_outcomes.<id>" in out


def test_outcome_key_rejects_prose():
    m = _mod()
    assert m._outcome_key("opportunities.yml#desired_outcomes.adoption") == "adoption"
    assert m._outcome_key("l0-purpose - evidence that x. y.") == ""
