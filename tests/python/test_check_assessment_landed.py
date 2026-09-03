"""Coverage proof for check_assessment_landed.py — a file that CLAIMS freshness and holds nothing.

Every other freshness check in the harness reads a DATE. None of them asks whether anything
sits under it, and a field at its schema default is not a MISSING record — it is a PRESENT
record saying `not-assessed`, indistinguishable from "assessed and found nothing" to anything
that tests presence.

Dogfood 2026-09-03, three files at once: `services.yml` held 15 of 15 principles at
`not-assessed` for 103 days after a full assessment had run and landed in the decision log
instead; `privacy-assessment.yml` held 7 of 7 unassessed while carrying
`last_assessed: 2026-05-04`; `threat-model.yml` held zero threats. All three carried a live
`_meta.last_validated` stamp written by a DIFFERENT skill. The theory gates reading them —
Service Quality, Privacy, Security, all Required at L4 — got nothing, while every staleness
check saw three recently-validated files.
"""
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_assessment_landed
    return check_assessment_landed


def _canvas(tmp_path, files):
    d = tmp_path / "canvas"
    d.mkdir(parents=True)
    for name, body in files.items():
        (d / name).write_text(body)
    return d


def _run(mod, canvas, *extra):
    argv = sys.argv
    sys.argv = ["check_assessment_landed.py", "--canvas-dir", str(canvas), *extra]
    try:
        return mod.main()
    finally:
        sys.argv = argv


# --------------------------------------------------------------- the motivating cases

PRIVACY_DATED_BUT_EMPTY = """_meta:
  last_validated: "2026-07-05"
last_assessed: "2026-05-04"
principles:
  proactive_not_reactive: {assessment: not-assessed, evidence: ""}
  privacy_as_default: {assessment: not-assessed, evidence: ""}
"""

THREATS_EMPTY_BUT_STAMPED = """_meta:
  last_validated: "2026-07-05"
threats: []
"""

SERVICES_ASSESSED = """_meta:
  last_validated: "2026-09-03"
last_assessed: "2026-09-03"
principles:
  - {id: 1, assessment: pass, evidence: "README leads with the pain"}
  - {id: 2, assessment: fail, evidence: "homepage field is blank"}
"""


def test_bites_on_a_date_asserting_an_assessment_that_never_landed(scripts_path, tmp_path, capsys):
    """THE REGRESSION TEST, and it is the real privacy-assessment.yml shape: a
    `last_assessed` date over principles that are all still at their default."""
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {"privacy-assessment.yml": PRIVACY_DATED_BUT_EMPTY,
                           "services.yml": SERVICES_ASSESSED,
                           "threat-model.yml": THREATS_EMPTY_BUT_STAMPED})
    rc = _run(mod, c, "--strict")
    out = capsys.readouterr().out
    assert rc == 1, "strict must FAIL on a file claiming freshness while holding nothing"
    assert "privacy-assessment.yml" in out
    assert "threat-model.yml" in out
    assert "2026-05-04" in out, "the report must show the date being asserted"
    assert "0 of 2 assessed" in out


def test_reports_only_by_default_so_a_mid_assessment_day_does_not_fail_a_build(
        scripts_path, tmp_path):
    """Gate-remedy proportionality: failing a build over a half-finished assessment
    teaches people to delete the stamp rather than finish the work."""
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {"privacy-assessment.yml": PRIVACY_DATED_BUT_EMPTY,
                           "services.yml": SERVICES_ASSESSED,
                           "threat-model.yml": THREATS_EMPTY_BUT_STAMPED})
    assert _run(mod, c) == 0


# --------------------------------------------------------------- it must NOT bite here

DECLARES_ITSELF_EMPTY = """_meta:
  last_validated: "2026-07-05"
  applicability: "Schema-only as of 2026-06-04. Populate when an L3 solution exists."
threats: []
"""

EMPTY_AND_CLAIMS_NOTHING = """_meta: {}
principles:
  proactive_not_reactive: {assessment: not-assessed}
"""


def test_does_not_bite_on_a_file_that_declares_itself_empty(scripts_path, tmp_path, capsys):
    """AN EMPTY FILE THAT DECLARES ITSELF EMPTY IS A DECISION. `trust-signals.yml`,
    `bounded-contexts.yml` and `value-stream.yml` are all legitimately empty and say so
    in `_meta.applicability`. Flagging them would make this check noise on day one."""
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {"threat-model.yml": DECLARES_ITSELF_EMPTY,
                           "services.yml": SERVICES_ASSESSED,
                           "privacy-assessment.yml": EMPTY_AND_CLAIMS_NOTHING})
    rc = _run(mod, c, "--strict")
    out = capsys.readouterr().out
    assert rc == 0
    assert "declares itself empty" in out
    assert "CLAIMS FRESH" not in out


def test_does_not_bite_when_the_file_asserts_no_freshness(scripts_path, tmp_path, capsys):
    """Empty with no date is not a lie. Nothing is being asserted, so there is nothing
    to contradict — that is a backlog item, not a defect this check owns."""
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {"privacy-assessment.yml": EMPTY_AND_CLAIMS_NOTHING,
                           "services.yml": SERVICES_ASSESSED,
                           "threat-model.yml": DECLARES_ITSELF_EMPTY})
    assert _run(mod, c, "--strict") == 0
    assert "makes no freshness claim" in capsys.readouterr().out


# --------------------------------------------------------------- UNKNOWN is never a pass

def test_missing_canvas_dir_is_unknown_not_clean(scripts_path, tmp_path):
    mod = _import(scripts_path)
    assert _run(mod, tmp_path / "nope") == 2


def test_empty_canvas_is_unknown_not_clean(scripts_path, tmp_path):
    """A scan that finds none of its registered files has checked NOTHING. Reporting
    clean there is a success claim over empty input."""
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {})
    assert _run(mod, c) == 2


def test_unparseable_canvas_is_unknown_not_clean(scripts_path, tmp_path):
    mod = _import(scripts_path)
    c = _canvas(tmp_path, {"services.yml": "principles: [\n  broken\n"})
    assert _run(mod, c) == 2
