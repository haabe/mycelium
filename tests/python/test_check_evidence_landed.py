"""Coverage proof for check_evidence_landed.py — the empty quadrant.

canvas-health already flags an OPEN task whose evidence exists (8c(b)) and evidence
with NO task (8c(d)). A CLOSED task whose evidence never landed had no check, and
`canvas_refs` — the field where a task declares where its findings belong — was read
by nothing at all.

Dogfood 2026-08-08: ht-055 was scored, closed, and written only into human-tasks.yml
while its own canvas_refs pointed at purpose.yml. It surfaced because a human asked
"all logged and verified?" — which is not a mechanism. The first run of this check
against the same canvas found SEVEN more, all predating that day.
"""
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_evidence_landed
    return check_evidence_landed


def _canvas(tmp_path, tasks_yaml, files=None):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "human-tasks.yml").write_text(tasks_yaml)
    for name, body in (files or {}).items():
        (d / name).write_text(body)
    return tmp_path


# ------------------------------------------------------------------ the motivating case

HT055_SHAPE = """pending_tasks:
  - id: ht-055
    status: completed
    canvas_refs:
      - "purpose.yml#positioning_evidence"
      - "opportunities.yml#opp-005"
"""


def test_catches_a_closed_task_whose_evidence_never_landed(scripts_path, tmp_path):
    """THE REGRESSION TEST, and it is the real ht-055 shape. Closed, declared two
    canvases, neither mentions it. If this returns nothing, the quadrant is empty again."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE, {
        "purpose.yml": 'positioning_evidence:\n  - "unrelated entry"\n',
        "opportunities.yml": "opportunities: []\n",
    })
    found = c.stranded(c_tasks(c, root), root / ".claude" / "canvas")
    assert found
    assert found[0]["id"] == "ht-055"


def c_tasks(mod, root):
    import yaml
    return yaml.safe_load((root / ".claude" / "canvas" / "human-tasks.yml").read_text())["pending_tasks"]


def test_landed_evidence_is_not_flagged(scripts_path, tmp_path):
    """The repair must actually silence it — otherwise the advisory nags forever and
    the reader learns to skip it, which is how the original failure survives."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE, {
        "purpose.yml": 'positioning_evidence:\n  - "ht-055 SCORED 2026-08-08: 117 impressions"\n',
        "opportunities.yml": "opportunities: []\n",
    })
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


# ------------------------------------------------------------------ negative controls

def test_open_tasks_are_not_flagged(scripts_path, tmp_path):
    """An OPEN task has not claimed to have finished anything, and 8c(b) covers it.
    If this fires, the check has degenerated into 'flag every task'."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE.replace("completed", "in_progress"),
                   {"purpose.yml": "x: 1\n", "opportunities.yml": "y: 2\n"})
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


def test_abandoned_tasks_are_not_expected_to_land(scripts_path, tmp_path):
    """The POINT of abandoning is that nothing came of it. Demanding landed evidence
    from an abandoned task would manufacture entries for work that did not happen."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE.replace("completed", "abandoned"),
                   {"purpose.yml": "x: 1\n", "opportunities.yml": "y: 2\n"})
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


def test_explicit_null_result_is_exempt(scripts_path, tmp_path):
    """'We asked and learned nothing' is a finding, and it belongs in the task rather
    than in the opportunity tree. Recording it must not be punished."""
    c = _import(scripts_path)
    tasks = HT055_SHAPE + '    no_evidence_produced: "Posted, zero responses. Null recorded."\n'
    root = _canvas(tmp_path, tasks, {"purpose.yml": "x: 1\n", "opportunities.yml": "y: 2\n"})
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


def test_task_with_no_canvas_refs_is_not_flagged(scripts_path, tmp_path):
    """A task that never declared a destination made no claim to break. That is a
    weaker and different concern, and conflating them would drown the real finding."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, "pending_tasks:\n  - id: ht-x\n    status: completed\n")
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


def test_one_of_several_refs_is_enough(scripts_path, tmp_path):
    """Landing in ANY declared canvas is landing. Requiring all of them would flag
    correctly-routed evidence and train the reader to ignore the check."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE, {
        "purpose.yml": "x: 1\n",
        "opportunities.yml": "note: ht-055 landed here\n",
    })
    assert c.stranded(c_tasks(c, root), root / ".claude" / "canvas") == []


def test_missing_target_file_is_not_landed(scripts_path, tmp_path):
    """A ref to a canvas that does not exist cannot have received anything."""
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE)
    found = c.stranded(c_tasks(c, root), root / ".claude" / "canvas")
    assert found and found[0]["id"] == "ht-055"


# ------------------------------------------------------------------ empty-input honesty

def test_refuses_when_there_is_no_task_file(scripts_path, tmp_path, monkeypatch, capsys):
    """A green over a population that was never read is the one answer never true."""
    c = _import(scripts_path)
    monkeypatch.setattr(sys, "argv", ["x", "--project-dir", str(tmp_path)])
    assert c.main() == 2
    assert "PRECONDITION NOT MET" in capsys.readouterr().err


def test_json_reports_the_denominator(scripts_path, tmp_path, monkeypatch, capsys):
    """'nothing found' must stay distinguishable from 'nothing looked at'."""
    import json as _json
    c = _import(scripts_path)
    root = _canvas(tmp_path, HT055_SHAPE, {
        "purpose.yml": "e: ht-055 landed\n", "opportunities.yml": "y: 2\n"})
    monkeypatch.setattr(sys, "argv", ["x", "--project-dir", str(root), "--json"])
    assert c.main() == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["completed_tasks_checked"] == 1
