"""Coverage for check_purpose_stance (v0.120.0).

THE GAP IT EXISTS FOR. Measured in plugin 0.119.0: nothing anywhere read `purpose.yml`'s why/how/what
values. Two scripts opened the file and read neither; four hooks checked existence or edit; no theory
gate named Sinek. So a solution could contradict the product's own definition and pass every gate the
framework had.

THE THREE WAYS THIS COULD ROT, one test class each:

  1. IT FIRES ON PROJECTS THAT NEVER OPTED IN — every project predating the field drowns in warnings
     for a defect it did not introduce, and gets muted within a day.
  2. IT ACCEPTS A QUALITY ADJECTIVE AS BINDING. Measured 2026-08-23 by blind subagent: "accessible
     and secure" yields no checkable property, because every solution claims to satisfy it. A binding
     property nothing can contradict produces a stance answered `preserves` forever — this
     mechanism's own failure reintroduced at its entry point.
  3. AN AGENT CLEARS ITS OWN CONTRADICTION — founder's rule: an agent may not override. Without a
     human actor the mechanism nullifies itself while every record looks complete.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_purpose_stance.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cps", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cps"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def canvas(tmp_path):
    d = tmp_path / "canvas"
    d.mkdir()
    return d


def _purpose(canvas, **over):
    doc = {
        "why": "Better to know what's worth building before you build it.",
        "how": ["anonymously"],
        "what": "a microblog",
    }
    pp = over.pop("purpose_properties", None)
    doc.update(over)
    if pp is not None:
        doc["purpose_properties"] = pp
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    return doc


def _props(m, doc, properties, confirmed="human", stale=False):
    h = m.purpose_hash(doc)
    return {
        "derived_from_hash": "0" * 64 if stale else h,
        "confirmed_by": confirmed,
        "properties": properties,
    }


BINDING = {
    "id": "pp-001",
    "property": "anonymous",
    "source": "how",
    "binding": True,
    "contradicted_by": ["sign-in with Google before posting"],
}


def _sol(canvas, stance=None):
    sol = {"id": "sol-001a"}
    if stance is not None:
        sol["purpose_stance"] = stance
    (canvas / "opportunities.yml").write_text(
        yaml.safe_dump({"opportunities": [{"id": "opp-001", "solutions": [sol]}]},
                       allow_unicode=True, sort_keys=False)
    )


# --- rot-mode 1: adoption path ------------------------------------------------
def test_silent_when_the_project_never_opted_in(canvas):
    _purpose(canvas)
    _sol(canvas)
    assert _mod().purpose_stance_findings(canvas) == []


def test_silent_with_no_purpose_file_at_all(canvas):
    assert _mod().purpose_stance_findings(canvas) == []


def test_silent_when_properties_exist_but_none_are_binding(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [{"id": "pp-001", "property": "short",
                                                 "source": "what", "binding": False}])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)
    assert m.purpose_stance_findings(canvas) == []


# --- rot-mode 2: the quality-adjective trap -----------------------------------
def test_binding_property_with_nothing_that_could_contradict_it_is_flagged(canvas):
    """The 2026-08-23 finding: 'secure' is not binding, 'no plaintext credentials' is."""
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [{"id": "pp-001", "property": "secure",
                                                 "source": "how", "binding": True}])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    out = m.purpose_stance_findings(canvas)
    assert any("nothing that could contradict it" in w for w in out)


def test_an_aspiration_is_accepted_without_a_contradiction(canvas):
    """A skipped definition is a recorded choice, not a defect — and not checked."""
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [{"id": "pp-001", "property": "secure",
                                                 "source": "how", "binding": True,
                                                 "aspiration_reason": "builder skipped defining it"}])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "no credentials stored"}})
    assert m.purpose_stance_findings(canvas) == []


# --- rot-mode 3: an agent clearing its own contradiction ----------------------
def test_contradiction_without_a_human_override_is_flagged(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "contradicts", "note": "requires login",
                             "override": {"reason": "agent decided it was fine"}}})
    out = m.purpose_stance_findings(canvas)
    assert any("no human override" in w for w in out)


def test_contradiction_with_a_human_override_passes(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "contradicts", "note": "requires login",
                             "override": {"human": "havard", "decision": "DL-1234"}}})
    assert m.purpose_stance_findings(canvas) == []


# --- the declaration checks ---------------------------------------------------
def test_solution_with_no_stance_at_all_is_flagged(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)
    out = m.purpose_stance_findings(canvas)
    assert any("no purpose_stance" in w for w in out)
    assert any("Silence is the finding" in w for w in out)


def test_a_verdict_without_a_note_is_flagged_including_not_applicable(canvas):
    """opp-061's explicit-null clause: a null must be a claim with an author."""
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "not_applicable"}})
    assert any("with no note" in w for w in m.purpose_stance_findings(canvas))


def test_a_complete_stance_passes(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "session-scoped, no account"}})
    assert m.purpose_stance_findings(canvas) == []


# --- staleness and confirmation ----------------------------------------------
def test_a_stale_hash_supersedes_everything_below(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING], stale=True)
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "fine"}})
    assert any("superseded" in w for w in m.purpose_stance_findings(canvas))


def test_editing_the_why_changes_the_hash(canvas):
    """The anti-drift mechanism, exercised rather than asserted."""
    m = _mod()
    doc = _purpose(canvas)
    before = m.purpose_hash(doc)
    doc["why"] = "something else entirely"
    assert m.purpose_hash(doc) != before


def test_reformatting_does_not_change_the_hash(canvas):
    """Intent changed, not indentation — a false staleness alarm would mute this fast."""
    m = _mod()
    a = {"why": "w", "how": ["x", "y"], "what": "z"}
    b = {"what": "z", "why": "w", "how": ["x", "y"]}
    assert m.purpose_hash(a) == m.purpose_hash(b)


def test_an_unconfirmed_list_is_flagged(canvas):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING], confirmed="pending")
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "fine"}})
    assert any("confirmed_by" in w for w in m.purpose_stance_findings(canvas))


def test_unparseable_files_are_skipped_not_crashed(canvas):
    (canvas / "purpose.yml").write_text("why: [oops\n")
    assert _mod().purpose_stance_findings(canvas) == []


# --- the negative control: the gate must be able to FAIL --------------------------
# check_negative_control.py rejected this file's first version for having no
# failure-direction assertion. It was right: --strict was the mode that can fail and
# it had no test at all. A guard whose failing path is untested keeps passing its own
# tests after it stops working — the verify_citations failure mode, which shipped with
# green tests and a matcher that matched 0% of real citations for ~2.5 months.
def test_strict_mode_exits_nonzero_on_a_real_finding(canvas, monkeypatch, capsys):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)  # no stance at all
    monkeypatch.setattr(sys, "argv", ["check_purpose_stance.py", "--canvas-dir", str(canvas), "--strict"])
    assert m.main() == 1
    assert "FAIL" in capsys.readouterr().out


def test_advisory_mode_exits_zero_on_the_same_finding(canvas, monkeypatch, capsys):
    """Same input, different tier. The validator must not break projects predating the field."""
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)
    monkeypatch.setattr(sys, "argv", ["check_purpose_stance.py", "--canvas-dir", str(canvas)])
    assert m.main() == 0
    assert "WARN" in capsys.readouterr().out


def test_strict_mode_exits_zero_when_clean(canvas, monkeypatch):
    m = _mod()
    doc = _purpose(canvas)
    doc["purpose_properties"] = _props(m, doc, [BINDING])
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "session-scoped"}})
    monkeypatch.setattr(sys, "argv", ["check_purpose_stance.py", "--canvas-dir", str(canvas), "--strict"])
    assert m.main() == 0


# --- grandfathering: the retrofit must not flood on adoption ----------------------
# Measured on the dogfood canvas 2026-08-23: retrofitting there would have produced
# 53 solutions x 8 binding properties = 424 findings on day one, on the only project
# then able to adopt. A check that floods on adoption is one nobody adopts. The
# exemption is an explicit list rather than a date comparison, because only 10 of
# those 53 solutions carried any date at all.
def test_grandfathered_solutions_are_not_flagged(canvas):
    m = _mod()
    doc = _purpose(canvas)
    pp = _props(m, doc, [BINDING])
    pp["grandfathered"] = ["sol-001a"]
    doc["purpose_properties"] = pp
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)  # no stance at all
    assert m.purpose_stance_findings(canvas) == []


def test_a_solution_not_in_the_list_is_still_flagged(canvas):
    """The exemption is a list, not an amnesty. New work still carries the obligation."""
    m = _mod()
    doc = _purpose(canvas)
    pp = _props(m, doc, [BINDING])
    pp["grandfathered"] = ["sol-999z"]
    doc["purpose_properties"] = pp
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas)
    assert any("no purpose_stance" in w for w in m.purpose_stance_findings(canvas))


def test_the_exemption_is_reported_every_run_never_silently(canvas, monkeypatch, capsys):
    """An exemption nobody sees becomes the permanent state of the canvas."""
    m = _mod()
    doc = _purpose(canvas)
    pp = _props(m, doc, [BINDING])
    pp["grandfathered"] = ["sol-001a", "sol-002a"]
    doc["purpose_properties"] = pp
    (canvas / "purpose.yml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    _sol(canvas, {"pp-001": {"verdict": "preserves", "note": "fine"}})
    monkeypatch.setattr(sys, "argv", ["check_purpose_stance.py", "--canvas-dir", str(canvas)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "2 solution(s) grandfathered" in out
    assert "never will be until someone backfills" in out
