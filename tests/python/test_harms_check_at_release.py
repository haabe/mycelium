"""The harms check is named at release, as advice (v0.321.0).

WHY. /mycelium:harms-check asks who a product could harm when it works as designed, which neither
Security nor Privacy asks. Until 0.321.0 nothing that runs named it: in 175 end-to-end runs of the
installed plugin it was mentioned in 1, against 33 for the privacy check, which the release gate's
refusal names. Six blind readers running the shipped skill flagged three harmful designs of three
and none of three honest ones. The maintainer's ruling on that test: name it at release, keyed to
the exposure record, and never let it block.

So every test here has two halves: the advice is GIVEN where a release is decided, and NOTHING
about the check changes what is allowed or refused. The second half is the one that must not rot.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
SCHEMA = SCRIPTS.parent / "schemas" / "diamonds" / "active.schema.json"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder

RELEASED = [{"decision": d, "on": "2026-09-20"}
            for d in ("set_target", "start_experiment", "commit_to_build")] + [
                {"decision": "release", "on": "2026-09-22"}]
CHECKED = {"on": "2026-09-24", "verdict": "net-positive", "note": "no deceptive pattern found"}


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _l3(*records: dict) -> dict:
    """An L3 that has released, carrying these exposure records (one complete record by default)."""
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(RELEASED),
            "exposures": [dict(r) for r in (records or (tsl.RECORD,))]}


def _project(tmp_path: Path, diamonds: list[dict]) -> str:
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds)


def _hook(project: str, command: str, monkeypatch, capsys, mode: str = "default"):
    payload = {**tsl._bash(command), "permission_mode": mode}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    code = sl.main(["--project-dir", project, "--exposure-hook"])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------- the advice is given

def test_a_current_exposure_with_no_harms_check_is_told_so(tmp_path):
    """RED BEFORE 0.321.0: the readiness report said `current exposure: ...` and nothing else."""
    ok, text = sl.exposure_state(_project(tmp_path, [_l3()]))
    assert ok, text
    assert "/mycelium:harms-check" in text
    assert "never blocks" in text
    assert "l3-a" in text                       # it names the exposure it is about
    assert "not-applicable" in text             # and the way to say it does not apply


def test_the_release_hook_allows_and_hands_the_agent_the_advice(tmp_path, monkeypatch, capsys):
    """RED BEFORE 0.321.0: an allowed release printed nothing. The command still runs: exit 0 and
    no permission decision, only context."""
    code, out, err = _hook(_project(tmp_path, [_l3()]), "fly deploy", monkeypatch, capsys)
    assert code == 0 and err == ""
    spoken = json.loads(out)["hookSpecificOutput"]
    assert spoken["hookEventName"] == "PreToolUse"
    assert "/mycelium:harms-check" in spoken["additionalContext"]
    assert "permissionDecision" not in spoken   # advice is not a decision


def test_a_refused_release_names_the_check_beside_the_required_ones(tmp_path, monkeypatch, capsys):
    """The record shows a skill gets run when the gate's own refusal names it. RED BEFORE 0.321.0."""
    bare = dict(tsl.RECORD, gates={})           # no gate passed for this exposure: refused
    code, _, err = _hook(_project(tmp_path, [_l3(bare)]), "fly deploy", monkeypatch, capsys)
    assert code == 2
    assert "/mycelium:privacy-check" in err     # the required ones, as before
    assert "/mycelium:harms-check" in err
    assert "never blocks" in err                # and it says which kind this one is


def test_with_two_current_exposures_the_advice_is_in_the_question(tmp_path, monkeypatch, capsys):
    second = dict(tsl.RECORD, audience="A second cohort of twelve, opted in by email")
    code, out, _ = _hook(_project(tmp_path, [_l3(tsl.RECORD, second)]), "fly deploy",
                         monkeypatch, capsys)
    asked = json.loads(out)["hookSpecificOutput"]
    assert code == 0 and asked["permissionDecision"] == "ask"
    assert "/mycelium:harms-check" in asked["permissionDecisionReason"]


def test_the_exposures_report_prints_the_advice_apart_from_the_gaps(tmp_path, capsys):
    """`nothing to report` keeps meaning "no gap in the records". The advice is its own line."""
    project = _project(tmp_path, [_l3()])
    assert sl.exposure_report(project) == []
    assert sl.main(["--project-dir", project, "--exposures"]) == 0
    out = capsys.readouterr().out
    assert "exposure records: nothing to report" in out
    assert "/mycelium:harms-check" in out


# ---------------------------------------------------------------- and it goes quiet when answered

@pytest.mark.parametrize("verdict", ["net-positive", "not-applicable", "Net-Positive"])
def test_a_recorded_check_is_quiet(tmp_path, monkeypatch, capsys, verdict):
    record = dict(tsl.RECORD, harms_check=dict(CHECKED, verdict=verdict))
    project = _project(tmp_path, [_l3(record)])
    ok, text = sl.exposure_state(project)
    assert ok and "harms" not in text.lower()
    code, out, err = _hook(project, "fly deploy", monkeypatch, capsys)
    assert (code, out, err) == (0, "", "")      # allowed in silence, as before 0.321.0


@pytest.mark.parametrize("unreadable", [
    {"verdict": "net-positive"},                               # no date
    {"on": "2026-09-24", "verdict": "looks fine"},             # not one of the three verdicts
    {"on": "2026-09-24"},                                      # no verdict
    "done",                                                    # not a record at all
])
def test_an_unreadable_record_is_not_a_check(tmp_path, unreadable):
    record = dict(tsl.RECORD, harms_check=unreadable)
    ok, text = sl.exposure_state(_project(tmp_path, [_l3(record)]))
    assert ok                                   # and still does not stop anything
    assert "no harms check is recorded" in text


def test_an_ended_exposure_is_not_advised_about(tmp_path, capsys):
    ended = dict(tsl.RECORD, ended={"how": "withdrawn", "on": "2026-09-24", "note": "cohort over"})
    project = _project(tmp_path, [_l3(ended)])
    assert sl.main(["--project-dir", project, "--exposures"]) == 0
    assert "harms" not in capsys.readouterr().out.lower()


# ---------------------------------------------------------------- it never decides

def test_a_happier_negative_verdict_does_not_stop_the_release_and_is_said(tmp_path, monkeypatch,
                                                                          capsys):
    """The one thing this change must never become: a verdict that refuses. The person decides."""
    record = dict(tsl.RECORD, harms_check=dict(CHECKED, verdict="happier-negative",
                                               note="cancelling takes a phone call"))
    project = _project(tmp_path, [_l3(record)])
    ok, text = sl.exposure_state(project)
    assert ok
    assert "Happier-negative" in text and "does not stop a release" in text
    code, out, err = _hook(project, "fly deploy", monkeypatch, capsys)
    assert code == 0 and err == ""
    assert "permissionDecision" not in json.loads(out)["hookSpecificOutput"]


@pytest.mark.parametrize("harms", [None, CHECKED, dict(CHECKED, verdict="happier-negative"),
                                   "done", ["x"], {"verdict": 7}])
def test_no_harms_record_changes_whether_an_exposure_is_current(tmp_path, harms):
    """Whatever is or is not written under `harms_check`, the same record covers the same release."""
    record = dict(tsl.RECORD) if harms is None else dict(tsl.RECORD, harms_check=harms)
    project = _project(tmp_path, [_l3(record)])
    any_records, current, reasons = sl.current_exposures(sl.State(project))
    assert (any_records, len(current), reasons) == (True, 1, [])
    assert sl.exposure_violation(project, tsl._bash("fly deploy")) is None


def test_no_harms_record_makes_a_refused_release_allowed(tmp_path, monkeypatch, capsys):
    """And the other direction: a check on record does not buy a release the gates refuse."""
    bare = dict(tsl.RECORD, gates={}, harms_check=CHECKED)
    code, _, _ = _hook(_project(tmp_path, [_l3(bare)]), "fly deploy", monkeypatch, capsys)
    assert code == 2


def test_the_schema_declares_the_field_and_cannot_refuse_a_write_over_it():
    """Declared, so the field is findable; no enum and nothing required, so a typo in a verdict
    never turns the diamonds file invalid. An unreadable verdict is handled as advice above."""
    exposure = json.loads(SCHEMA.read_text())["$defs"]["diamond"]["properties"]["exposures"]["items"]
    field = exposure["properties"]["harms_check"]
    assert set(field["properties"]) == {"on", "verdict", "note"}
    assert "enum" not in field["properties"]["verdict"]
    assert "required" not in field
    assert "harms_check" not in (exposure.get("required") or [])
    assert "harms" not in " ".join(sl.EXPOSURE_GATES)   # never one of the gates


def test_the_skill_and_the_release_step_say_where_the_verdict_goes():
    """The advice asks for `harms_check` on the exposure; the two skills that write it say how."""
    skills = SCRIPTS.parent / "skills"
    harms = (skills / "harms-check" / "SKILL.md").read_text()
    progress = (skills / "diamond-progress" / "SKILL.md").read_text()
    for text in (harms, progress):
        assert "harms_check" in text
        assert "not-applicable" in text
    assert "/mycelium:harms-check" in progress
    assert "never blocks" in progress
