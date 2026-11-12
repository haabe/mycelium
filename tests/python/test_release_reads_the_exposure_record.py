"""The release gate reads two things from the exposure record itself (founder rulings 2026-11-12).

1. "Team-only exposure is n/a". An L3's Evidence gate at `release` asks for one trial outside the
   team first. When the exposure's only audience is the builder or the team, the release IS the
   trial, and Evidence reads `n/a` with that reason. The exposure says so with an `audience` that
   starts with the documented token `team-only`. For any other audience the outside trial is still
   required: `n/a` on an L3's Evidence does not count while an exposure reaches outsiders. Until
   this release `n/a` counted for every audience, and nothing read who the audience was.

2. "On the exposure". A /mycelium:service-check scoped to one exposure writes its 15 principles to
   that exposure's `gates_basis.service_quality`; services.yml stays the product-wide record. The
   release gate reads the exposure's own record first. Until this release only services.yml was
   read, so a scoped check had to overwrite the product-wide reading or go unread.

Each test that is not a control fails on 0.336.0.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
SCHEMA = SCRIPTS.parent / "schemas" / "diamonds" / "active.schema.json"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder

RELEASED = [{"decision": d, "on": "2026-09-20"}
            for d in ("set_target", "start_experiment", "commit_to_build")] + [
                {"decision": "release", "on": "2026-09-22"}]
HARMS = {"on": "2026-09-24", "verdict": "not-applicable", "note": "no flows of that kind"}
TEAM = dict(tsl.RECORD, audience="team-only: the builder, in their own sessions",
            data_class="none", consent="the builder switches it on", harms_check=HARMS)
OUTSIDE = dict(tsl.RECORD, harms_check=HARMS)          # nine named staff: outside the team
EVIDENCE_NA = dict(tsl.EXPOSE_PASSED, evidence="n/a")


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _l3(*records: dict, **gates) -> dict:
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": {**tsl.EXPOSE_PASSED, **gates}, "decisions": list(RELEASED),
            "exposures": [dict(r) for r in records]}


def _project(tmp_path: Path, diamonds: list[dict], services=None) -> str:
    p = tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds)
    if services is not None:
        (Path(p) / ".claude" / "canvas" / "services.yml").write_text(yaml.safe_dump(services))
    return p


def _deploy(project: str, monkeypatch, capsys):
    payload = {**tsl._bash("fly deploy"), "permission_mode": "default"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    code = sl.main(["--project-dir", project, "--exposure-hook"])
    return code, capsys.readouterr().err


# ---------------------------------------------------------------- 1. a team-only exposure

def test_team_only_token_is_read_from_the_audience():
    assert sl.team_only({"audience": "team-only: the builder"})
    assert sl.team_only({"audience": "  Team-only"})
    assert not sl.team_only({"audience": "the builder and three friends"})
    assert not sl.team_only({"audience": "not team-only: a pilot"})
    assert not sl.team_only({"audience": "team-only-ish"})
    assert not sl.team_only({})


def test_a_team_only_exposure_passes_release_evidence_as_na(tmp_path):
    st = sl.State(_project(tmp_path, []))
    d = _l3(TEAM, evidence="n/a")
    assert st.release_evidence_missing(d) is None
    assert st.move_missing(d, "develop") == []


def test_an_outside_audience_still_needs_release_evidence(tmp_path):
    """RED ON 0.336.0: `n/a` counted on the Evidence gate whoever the exposure reached."""
    st = sl.State(_project(tmp_path, []))
    d = _l3(OUTSIDE, evidence="n/a")
    miss = st.move_missing(d, "develop")
    assert any("outside the team" in m and "Harbour" in m for m in miss), miss


def test_one_outside_exposure_beside_a_team_only_one_still_needs_evidence(tmp_path):
    st = sl.State(_project(tmp_path, []))
    assert st.release_evidence_missing(_l3(TEAM, OUTSIDE, evidence="n/a"))


def test_na_with_no_exposure_record_says_none_is_team_only(tmp_path):
    st = sl.State(_project(tmp_path, []))
    why = st.release_evidence_missing(_l3(evidence="n/a"))
    assert why and "team alone" in why


def test_the_release_hook_allows_a_team_only_exposure_with_evidence_na(tmp_path, monkeypatch,
                                                                         capsys):
    code, err = _deploy(_project(tmp_path, [_l3(TEAM, evidence="n/a")]), monkeypatch, capsys)
    assert code == 0, err


def test_the_release_hook_refuses_an_outside_exposure_with_evidence_na(tmp_path, monkeypatch,
                                                                        capsys):
    """RED ON 0.336.0: the deploy went out on `n/a`."""
    code, err = _deploy(_project(tmp_path, [_l3(OUTSIDE, evidence="n/a")]), monkeypatch, capsys)
    assert code == 2
    assert "outside the team" in err


def test_the_exposure_report_names_an_outside_exposure_on_evidence_na(tmp_path):
    lines = sl.exposure_report(_project(tmp_path, [_l3(OUTSIDE, evidence="n/a")]))
    assert any("outside the team" in x for x in lines), lines


def test_control_an_outside_exposure_with_evidence_passed_is_allowed(tmp_path, monkeypatch,
                                                                       capsys):
    code, err = _deploy(_project(tmp_path, [_l3(OUTSIDE)]), monkeypatch, capsys)
    assert code == 0, err


def test_control_the_rule_is_an_l3_rule(tmp_path):
    st = sl.State(_project(tmp_path, []))
    l4 = dict(_l3(OUTSIDE, evidence="n/a"), scale="L4", id="l4-a")
    assert st.release_evidence_missing(l4) is None


def test_the_schema_declares_the_token_on_the_audience_field():
    props = json.loads(SCHEMA.read_text())["$defs"]["diamond"]["properties"]["exposures"]
    assert sl.TEAM_ONLY in props["items"]["properties"]["audience"]["description"]


# ---------------------------------------------------------------- 2. a scoped service check

def _principles(evidence=True, upto=15):
    return [{"id": i, "assessment": "pass", "evidence": "tried in the pilot" if evidence else ""}
            for i in range(1, upto + 1)]


NOT_DONE = {"principles": [{"id": i, "assessment": "not-assessed", "evidence": ""}
                           for i in range(1, 16)]}


def _scoped(**over):
    return dict(OUTSIDE, gates_basis={"service_quality": {
        "on": "2026-09-24", "decision_log": "DL-0001", "principles": _principles(**over)}})


def test_a_release_passes_service_quality_on_a_record_scoped_to_the_exposure(tmp_path, monkeypatch,
                                                                              capsys):
    """RED ON 0.336.0: the gate read services.yml alone, which here the product has not done."""
    p = _project(tmp_path, [_l3(_scoped())], services=NOT_DONE)
    services = Path(p) / ".claude" / "canvas" / "services.yml"
    before = services.read_bytes()
    st = sl.State(p)
    d = st.by_id["l3-a"]
    assert st.gate_missing(d, "service_quality") is None
    assert sl._record_problems(st, d, d["exposures"][0], "2026-09-25") == []
    code, err = _deploy(p, monkeypatch, capsys)
    assert code == 0, err
    assert services.read_bytes() == before            # services.yml was not touched


def test_with_neither_record_service_quality_is_still_pending(tmp_path):
    st = sl.State(_project(tmp_path, [], services=NOT_DONE))
    d = _l3(OUTSIDE)
    msg = st.gate_missing(d, "service_quality")
    assert msg and "services.yml" in msg
    assert any("service_quality" in m for m in sl._record_problems(st, d, OUTSIDE, "2026-09-25"))


def test_an_incomplete_scoped_record_is_named_and_not_covered_by_services_yml(tmp_path):
    """The exposure's own record is read first: a scoped check missing principle 15 does not
    pass on a complete product-wide record."""
    st = sl.State(_project(tmp_path, []))              # services.yml complete
    e = _scoped(upto=14)
    msg = st.gate_missing(_l3(e), "service_quality")
    assert msg and "gates_basis.service_quality" in msg and "15" in msg


def test_a_text_basis_is_a_note_and_services_yml_is_read(tmp_path):
    st = sl.State(_project(tmp_path, [], services=NOT_DONE))
    e = dict(OUTSIDE, gates_basis={"service_quality": "DL-1522, scoped: 10 pass / 2 partial"})
    assert sl.scoped_service_record(e) is None
    assert st.gate_missing(_l3(e), "service_quality")


def test_control_a_complete_services_yml_still_passes_without_a_scoped_record(tmp_path):
    st = sl.State(_project(tmp_path, []))
    assert st.gate_missing(_l3(OUTSIDE), "service_quality") is None


def test_an_ended_exposure_is_read_at_close(tmp_path):
    """At an L3's close every exposure has ended; its scoped record still backs the gate."""
    st = sl.State(_project(tmp_path, [], services=NOT_DONE))
    e = dict(_scoped(), ended={"how": "withdrawn", "on": "2026-09-24"})
    assert st.gate_missing(_l3(e), "service_quality") is None


def test_the_expose_stage_reads_the_same_rule(tmp_path):
    """The readiness check for exposed work names the same gap as the release decision."""
    st = sl.State(_project(tmp_path, []))
    assert any("outside the team" in m for m in st.stage_missing(_l3(OUTSIDE, evidence="n/a"),
                                                                 "expose"))
    assert not any("outside the team" in m for m in st.stage_missing(_l3(TEAM, evidence="n/a"),
                                                                     "expose"))
