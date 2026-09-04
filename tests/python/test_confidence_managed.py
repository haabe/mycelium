"""Coverage proofs for check_confidence_managed.py.

THE REGRESSION THESE ENCODE IS CONCRETE AND RECENT. On 2026-09-04 a dogfood diamond's confidence
had moved once in the project's history. In the twenty days since, 21 instruments naming that
diamond were scored, a pre-registered test returned SUPPORTS on the first attribution evidence the
bet ever had, and a crossing condition written in advance was met three times over. The number never
moved and no check noticed.

**THE FIRST VERSION OF THIS GUARD DID NOT BITE**, and that is the most important thing these tests
protect. It used a 30-day staleness threshold against a defect that was 20 days old, so it passed
the exact case it was written for. A guard whose threshold is wider than its motivating instance is
a green light with provenance.
"""
import datetime as dt
import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_confidence_managed.py"


def _mod():
    spec = importlib.util.spec_from_file_location("ccm", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["ccm"] = m
    spec.loader.exec_module(m)
    return m


def _root(tmp_path, derivation, instruments):
    """A minimal project: one diamond, and N scored instruments naming it."""
    (tmp_path / ".claude/diamonds").mkdir(parents=True)
    d = {"active": [{"id": "l1-strategy", "confidence": 0.48}]}
    if derivation:
        d["active"][0]["confidence_derivation"] = derivation
    import yaml
    (tmp_path / ".claude/diamonds/active.yml").write_text(yaml.safe_dump(d), encoding="utf-8")
    ev = tmp_path / ".claude/evals/assumption-tests"
    ev.mkdir(parents=True)
    for i in range(instruments):
        (ev / f"t{i}.md").write_text("---\nstatus: scored\n---\ntarget l1-strategy\n", encoding="utf-8")
    return tmp_path


def test_it_bites_on_the_real_defect(tmp_path, monkeypatch):
    """THE NEGATIVE CONTROL. Evidence landed after the derivation and nobody revisited it."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2026-08-15"}, instruments=3)
    monkeypatch.setattr(m, "evidence_since", lambda r, s, i=None: ["a.md", "b.md", "c.md"])
    f = m.audit(root, today=dt.date(2026, 9, 4))
    warns = [x for x in f if x["level"] == "WARN"]
    assert warns, "the guard is blind — this is the exact case it exists for"
    assert "not been revisited" in warns[0]["msg"]


def test_a_twenty_day_gap_still_bites(tmp_path, monkeypatch):
    """The first version used a 30-day threshold and slept through a 20-day defect. No time
    threshold may be reintroduced: the trigger is evidence, not the calendar."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2026-08-15"}, instruments=1)
    monkeypatch.setattr(m, "evidence_since", lambda r, s, i=None: ["one.md"])
    f = m.audit(root, today=dt.date(2026, 9, 4))   # exactly 20 days
    assert any(x["level"] == "WARN" for x in f)


def test_no_evidence_since_derivation_is_a_pass(tmp_path, monkeypatch):
    """A number that did not move is FINE when nothing new landed. The defect is being unexamined,
    never being unchanged."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2026-08-15"}, instruments=0)
    monkeypatch.setattr(m, "evidence_since", lambda r, s, i=None: [])
    assert not [x for x in m.audit(root, today=dt.date(2026, 9, 4)) if x["level"] == "WARN"]


def test_a_freshly_revisited_derivation_passes(tmp_path, monkeypatch):
    """Considered-and-unchanged, recorded with today's date, is a pass. The guard must never
    demand that the number MOVE — that would be an inflation engine aimed at the one value a
    project must not inflate."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2026-09-04"}, instruments=2)
    monkeypatch.setattr(m, "evidence_since",
                        lambda r, s, i=None: [] if s >= dt.date(2026, 9, 4) else ["x.md"])
    assert not [x for x in m.audit(root, today=dt.date(2026, 9, 4)) if x["level"] == "WARN"]


def test_a_diamond_with_no_derivation_is_info_not_warn(tmp_path):
    """Opt-in by presence. A project that never adopted the convention is not failed for it —
    but it is told that its number can only be re-asserted, never re-derived."""
    m = _mod()
    root = _root(tmp_path, None, instruments=0)
    f = m.audit(root, today=dt.date(2026, 9, 4))
    assert f and f[0]["level"] == "INFO"
    assert "only re-asserted" in f[0]["msg"]


def test_evidence_is_target_aware(tmp_path):
    """An instrument about a DIFFERENT diamond is not evidence about this number. Counting it would
    train the reader to ignore the warning, which is how a guard becomes wallpaper."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2026-01-01"}, instruments=0)
    ev = root / ".claude/evals/assumption-tests"
    (ev / "other.md").write_text("---\nstatus: scored\n---\ntarget l4-delivery\n", encoding="utf-8")
    assert m.evidence_since(root, dt.date(2026, 1, 1), "l1-strategy") == []


def test_the_guard_rejects_a_project_that_ignored_its_evidence(tmp_path):
    """FAILURE-DIRECTION ASSERTION, on real input rather than a stubbed one. The guard must EXIT
    NON-ZERO on the defect, not merely mention it — otherwise a guard that stops working keeps
    passing its own tests, which is the verify_citations failure mode this framework already paid
    for once: 14 green unit tests over a matcher that matched 0% of real input for two and a half
    months."""
    m = _mod()
    root = _root(tmp_path, {"changed_at": "2020-01-01"}, instruments=2)
    assert m.main(["--root", str(root)]) == 1


def test_an_absent_diamonds_file_is_refused(tmp_path):
    """A green over a population of zero is the one answer that is never true. Exit 2 names the
    precondition rather than reporting a success nobody earned."""
    m = _mod()
    assert m.main(["--root", str(tmp_path)]) == 2


def test_a_file_that_declares_itself_empty_is_not_a_refusal(tmp_path):
    """THIS BLOCKED THE CHECK'S OWN FIRST PUSH (2026-09-04). The framework tree carries
    `active_diamonds: []` — an explicit empty list — and the check called it "precondition unmet"
    and exited 2, failing every push from a repo that legitimately has no diamonds.

    The framework's own rule settles it: an empty file that DECLARES itself empty is a decision;
    only one that declares itself fresh is a defect. A project that has not started a diamond yet
    must not be failed for not having one."""
    m = _mod()
    (tmp_path / ".claude/diamonds").mkdir(parents=True)
    (tmp_path / ".claude/diamonds/active.yml").write_text("active_diamonds: []\n", encoding="utf-8")
    assert m.main(["--root", str(tmp_path)]) == 0


def test_a_present_but_silent_empty_file_is_still_refused(tmp_path):
    """An empty file that says NOTHING is not a declaration. It cannot be told apart from a
    truncated or half-written one, so it refuses."""
    m = _mod()
    (tmp_path / ".claude/diamonds").mkdir(parents=True)
    (tmp_path / ".claude/diamonds/active.yml").write_text("", encoding="utf-8")
    assert m.main(["--root", str(tmp_path)]) == 2


def test_no_derivation_plus_evidence_is_a_warn_not_a_note(tmp_path, monkeypatch):
    """THE WORST CASE MUST NOT BE THE QUIETEST ONE. The first version reported "no derivation" at
    INFO regardless of whether evidence existed — so a diamond with an un-derivable number AND
    instruments standing against it was the least loudly flagged state in the tool.

    Found 2026-09-04 by running the check across the rest of the board: three diamonds in exactly
    that state, one of them for 107 days with five scored instruments naming it."""
    m = _mod()
    root = _root(tmp_path, None, instruments=2)
    monkeypatch.setattr(m, "evidence_since", lambda r, s, i=None: ["a.md", "b.md"])
    f = m.audit(root, today=dt.date(2026, 9, 4))
    assert f and f[0]["level"] == "WARN"
    assert "evidence standing against it" in f[0]["msg"]


def test_no_derivation_and_no_evidence_stays_a_note(tmp_path, monkeypatch):
    """A project that has not gathered evidence yet is told about the missing derivation without
    being failed for it. Opt-in by presence means the adoption path stays open."""
    m = _mod()
    root = _root(tmp_path, None, instruments=0)
    monkeypatch.setattr(m, "evidence_since", lambda r, s, i=None: [])
    f = m.audit(root, today=dt.date(2026, 9, 4))
    assert f and f[0]["level"] == "INFO"
