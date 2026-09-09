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
