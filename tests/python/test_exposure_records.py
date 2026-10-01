"""Exposure records (v0.294.0, phase migration stage 1; founder rulings a, b, g, h, i).

The work that reaches people is recorded on its diamond as `exposures[]`: audience, channel, data
class, end date, consent, and the gates passed for that exposure. Stage 1 reports against the
records (report only); a write that adds one with personal or sensitive data asks the person.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import scale_locks as sl  # noqa: E402

PASSED_GATES = {"security": "pass", "privacy": "pass", "service_quality": "pass", "regulatory": "pass"}
RECORD = {"recorded_at": "2026-10-01", "audience": "Harbour staff, opted in",
          "channel": "moderated session", "data_class": "personal", "until": "2026-10-25",
          "consent": "signed pilot note", "gates": PASSED_GATES}


def _project(tmp_path: Path, diamonds: list[dict], ai: bool = False) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": diamonds}, sort_keys=False))
    if ai:
        (tmp_path / ".claude" / "jit-tooling").mkdir(parents=True)
        (tmp_path / ".claude" / "jit-tooling" / "active-stack.yml").write_text(
            "ai_components:\n  detected: true\n")
    return tmp_path


def _l3(**extra) -> dict:
    return {"id": "l3-a", "scale": "L3", "phase": "deliver",
            "learning_delivery": {"audience": "Harbour staff", "until": "2026-10-25",
                                  "means": "by hand", "started": "2026-10-01"}, **extra}


def test_work_that_reaches_people_with_no_record_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    lines = sl.exposure_report(str(_project(tmp_path, [_l3()])))
    assert any("no exposure record" in x for x in lines)
    assert any("migrate_phase.py" in x for x in lines), \
        "v0.307.0: the old field is not read as a delivery, and still keeps the exposure reported"


def test_a_complete_record_with_its_gates_passed_reports_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    assert sl.exposure_report(str(_project(tmp_path, [_l3(exposures=[RECORD])]))) == []


def test_missing_consent_and_unpassed_gates_are_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    rec = {k: v for k, v in RECORD.items() if k != "consent"} | {"gates": {"security": "pass"}}
    lines = sl.exposure_report(str(_project(tmp_path, [_l3(exposures=[rec])])))
    assert any("missing consent" in x for x in lines)
    assert any("gates not passed" in x and "privacy" in x for x in lines)


def test_an_exposure_past_its_end_date_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-11-02")
    lines = sl.exposure_report(str(_project(tmp_path, [_l3(exposures=[RECORD])])))
    assert any("ran past its end date" in x for x in lines)


def test_with_ai_components_explainability_is_one_of_the_exposure_gates(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    lines = sl.exposure_report(str(_project(tmp_path, [_l3(exposures=[RECORD])], ai=True)))
    assert any("explainability" in x for x in lines)


def test_control_archived_or_undelivered_work_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    archived = _l3(state="archived")
    planning = {"id": "l3-b", "scale": "L3", "phase": "develop",
                "learning_delivery": {"audience": "x", "until": "2026-12-01", "means": "y"}}
    assert sl.exposure_report(str(_project(tmp_path, [archived, planning]))) == []


# --- ruling g: a personal-data exposure is confirmed by the person ----------------------------------

def _payload(tmp_path: Path, record: dict, mode: str = "default") -> dict:
    target = tmp_path / ".claude" / "diamonds" / "active.yml"
    before = target.read_text()
    after = yaml.safe_dump({"active_diamonds": [_l3(exposures=[record])]}, sort_keys=False)
    return {"tool_name": "Write", "permission_mode": mode,
            "tool_input": {"file_path": str(target), "content": after}} if before else {}


def _decision(tmp_path, payload, capsys):
    sl._launch_approval(str(tmp_path), payload)
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


def test_recording_a_personal_data_exposure_asks_the_person(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path, [_l3()])
    assert _decision(p, _payload(p, RECORD), capsys) == "ask"


def test_with_nobody_to_ask_it_is_refused(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path, [_l3()])
    assert _decision(p, _payload(p, RECORD, mode="bypassPermissions"), capsys) == "deny"


def test_control_a_synthetic_data_exposure_is_not_asked(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path, [_l3()])
    assert _decision(p, _payload(p, RECORD | {"data_class": "synthetic"}), capsys) is None
