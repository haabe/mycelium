"""Coverage for validate_canvas.open_task_criterion_warnings (v0.118.0).

THE DEFECT IT EXISTS FOR. On 2026-08-21 a founder scanning his own open-task list by
eye found five tasks carrying no closure criterion of any kind — no success_criteria,
no pre_registered_outcomes, no scoring_rules, no stop_condition. Two had no horizon
either, so nothing would ever have prompted a look at them. **A task like that cannot
be closed on evidence, only abandoned by neglect.** The same sweep closed three other
tasks whose outcomes had been recorded days earlier and left open anyway.

No check saw any of it. A person did.

The three ways this check could rot, and the tests that stop them:

  1. IT NEVER FIRES. A check that cannot be shown failing is indistinguishable from
     one that is not wired up, which is the built-not-wired class this repo audits
     everywhere else.
  2. IT CRIES WOLF ON CLOSED WORK. Completed tasks legitimately lack criteria, and a
     warning per historical task makes the whole line noise by the second run.
  3. IT REFUSES TO SEE A RETRO-FITTED BAR. Criteria added after the fact are named
     `success_criteria_RETROFITTED_<date>` precisely so they are visibly not
     pre-registered. Matching those keys is required, or the fix reads as the defect.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/validate_canvas.py"


def _mod():
    spec = importlib.util.spec_from_file_location("vc", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["vc"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def canvas(tmp_path):
    d = tmp_path / "canvas"
    d.mkdir()
    return d


def _write(canvas, tasks):
    (canvas / "human-tasks.yml").write_text(
        yaml.safe_dump({"schema_version": 1, "pending_tasks": tasks}, allow_unicode=True),
    )
    return canvas


def test_fires_on_open_task_with_no_criterion(canvas):
    _write(canvas, [{"id": "ht-001", "status": "in_progress", "horizon": "2026-09-01"}])
    out = _mod().open_task_criterion_warnings(canvas)
    assert len(out) == 1
    assert "ht-001" in out[0]
    # The horizon exists, so the warning must NOT claim it is missing.
    assert "no horizon" not in out[0]


def test_names_the_missing_horizon_too(canvas):
    """Both defects in one task is the worst case and must be reported as two."""
    _write(canvas, [{"id": "ht-002", "status": "in_progress"}])
    out = _mod().open_task_criterion_warnings(canvas)
    assert len(out) == 1
    assert "no horizon" in out[0]


@pytest.mark.parametrize("key", [
    "success_criteria",
    "pre_registered_outcomes",
    "scoring_rules",
    "stop_condition",
    "watch_trigger",
    "reopen_trigger",
])
def test_any_recognised_criterion_silences_it(canvas, key):
    _write(canvas, [{"id": "ht-003", "status": "in_progress", key: "something"}])
    assert _mod().open_task_criterion_warnings(canvas) == []


def test_retrofitted_criteria_count(canvas):
    """Retro-fitted bars carry a dated suffix so they are visibly not pre-registered.

    The suffix must not make them invisible to the check that asked for them.
    """
    _write(canvas, [{
        "id": "ht-004",
        "status": "in_progress",
        "success_criteria_RETROFITTED_2026_08_21": "derived from the objective, not a prediction",
    }])
    assert _mod().open_task_criterion_warnings(canvas) == []


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_closed_tasks_are_not_flagged(canvas, status):
    """Historical tasks predate the rule; warning on them makes the line noise."""
    _write(canvas, [{"id": "ht-005", "status": status}])
    assert _mod().open_task_criterion_warnings(canvas) == []


def test_missing_file_is_silent_not_a_crash(canvas):
    """A project with no human-tasks.yml is normal, not a defect."""
    assert _mod().open_task_criterion_warnings(canvas) == []


def test_unparseable_file_defers_rather_than_double_reporting(canvas):
    """Parse failures belong to the fail-loud pass; this check must not duplicate them."""
    (canvas / "human-tasks.yml").write_text("pending_tasks: [oops\n")
    assert _mod().open_task_criterion_warnings(canvas) == []


def test_non_dict_entries_do_not_crash_the_run(canvas):
    (canvas / "human-tasks.yml").write_text(
        yaml.safe_dump({"pending_tasks": ["a bare string", None]}, allow_unicode=True),
    )
    assert _mod().open_task_criterion_warnings(canvas) == []


def test_reports_every_offender_not_just_the_first(canvas):
    _write(canvas, [
        {"id": "ht-006", "status": "in_progress"},
        {"id": "ht-007", "status": "pending"},
        {"id": "ht-008", "status": "in_progress", "success_criteria": "fine"},
    ])
    out = _mod().open_task_criterion_warnings(canvas)
    assert len(out) == 2
    assert {"ht-006", "ht-007"} == {w.split(":")[0] for w in out}
