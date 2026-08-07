"""Coverage proof for check_source_authenticity.py.

Fixtures are VERBATIM shapes from the 2026-08-07 dogfood session that motivated the
check, not invented ones. Three defects were found by running the first cut against a
LIVE canvas rather than a fixture; each has a regression test here.
"""
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_source_authenticity
    return check_source_authenticity


# ------------------------------------------------------------------ the motivating case

CONVERGENCE_UNCHECKED = """  - id: finding_x
    summary: >-
      THE WORKAROUND TEST, SECOND SIGHTING. u/NoShame9976 here: "describing the repeated
      workaround people use today". Near-identical to u/NoCucumber4783, different account,
      different thread. Convergence, weak.
    source_class: external_human
"""


def test_catches_the_motivating_instance(scripts_path):
    """THE REGRESSION TEST. Two handles supporting a convergence claim with nobody
    checked. This is the shape that would have put ONE templated account into canvas as
    three convergent strangers."""
    c = _import(scripts_path)
    rules = [r for r, _ in c.scan_text(CONVERGENCE_UNCHECKED)]
    assert any(r.startswith("B/") for r in rules), f"missed the motivating case: {rules}"


def test_authenticity_note_suppresses_the_finding(scripts_path):
    """The repaired record names what was checked. It must not keep nagging -- an
    advisory that fires on records that already did the work is one readers learn to
    skip (the check_stale_prose.py lesson)."""
    c = _import(scripts_path)
    repaired = CONVERGENCE_UNCHECKED + (
        "      BOTH ACCOUNTS CHECKED: u/NoCucumber4783 has 92 comment karma and domain\n"
        "      specifics; u/NoShame9976 is templated. Convergence WITHDRAWN.\n"
    )
    assert c.scan_text(repaired) == [], "re-flagged an already-checked record"


# ------------------------------------------------------------------ negative controls

def test_named_person_without_a_handle_is_not_flagged(scripts_path):
    """NEGATIVE CONTROL. A named person the founder actually corresponded with is a
    different evidence situation entirely. If this fires, the rule has degenerated into
    'flag every external_human entry'."""
    c = _import(scripts_path)
    txt = ("    summary: Brooks Talley replied the same day and answered both questions.\n"
           "    source_class: external_human\n")
    assert c.scan_text(txt) == []


def test_internal_tiers_are_never_flagged(scripts_path):
    """Authenticity bears on claims that someone EXTERNAL said something. A simulated
    or speculative entry claims nobody."""
    c = _import(scripts_path)
    txt = "    summary: u/SomeAccount said a thing.\n    source_class: internal_simulated\n"
    assert c.scan_text(txt) == []


def test_subreddit_is_not_a_person(scripts_path):
    """r/buildinpublic is a place. Handles and subs sit side by side in this prose, so
    the exclusion has to be explicit."""
    c = _import(scripts_path)
    assert c.distinct_handles("posted in r/buildinpublic and r/SideProject") == []


# ------------------------------------------------------------------ defects found on a live canvas

def test_package_scope_is_not_a_person(scripts_path):
    """DEFECT 1, found by running against a live canvas. `@haabe-mycelium` is a plugin
    marketplace name and was being read as a person, sending the maintainer to check an
    account that does not exist."""
    c = _import(scripts_path)
    assert c.distinct_handles("A Claude Code plugin (@haabe-mycelium) that structures") == []


def test_self_handle_is_excluded_including_accents(scripts_path, monkeypatch):
    """DEFECT 2 and 3, both found on a live canvas. Records quoting inbound Slack carry
    `@<founder>` mentions written by OTHER people -- the handle names the READER, not a
    source. And git config carried "Håvard" while the canvas wrote "@Havard", so without
    accent folding the exclusion silently missed."""
    c = _import(scripts_path)
    monkeypatch.setattr(c, "_self_handles", lambda: {"havard", "bartnes"})
    assert c.distinct_handles("Hei @Havard, takk for godt spor") == []
    assert c.distinct_handles("Bra svar @Havard, enig") == []


def test_convergence_rule_needs_two_distinct_accounts(scripts_path):
    """DEFECT 4. A convergence claim resting on ONE handle is not a
    convergence-across-strangers claim. Firing rule B on a single account overstates
    what the record did. It still gets rule A."""
    c = _import(scripts_path)
    txt = ("    summary: u/OnlyOne said it, convergence with our own read.\n"
           "    source_class: external_human\n")
    rules = [r for r, _ in c.scan_text(txt)]
    assert rules and all(r.startswith("A/") for r in rules), rules


def test_handles_are_counted_once_each(scripts_path):
    """The 2026-08-07 failure was ONE account quoted from three threads reading as three
    voices. A check counting OCCURRENCES rather than ACCOUNTS would agree with the
    mistake it exists to catch."""
    c = _import(scripts_path)
    assert c.distinct_handles("u/Same said x. Later u/Same said y. And u/Same again.") == ["same"]


# ------------------------------------------------------------------ empty-input honesty

def test_refuses_over_an_empty_population(scripts_path, tmp_path, monkeypatch, capsys):
    """EMPTY-INPUT HONESTY. check_empty_input_honesty.py caught check_stale_prose.py
    exiting 0 over an empty repo on 2026-08-07. A green over an empty population is the
    one answer that is never true."""
    c = _import(scripts_path)
    (tmp_path / ".claude").mkdir()
    monkeypatch.setattr(sys, "argv", ["check_source_authenticity.py", "--root", str(tmp_path)])
    rc = c.main()
    assert rc == 2, "must refuse, not pass, when nothing was scanned"
    assert "PRECONDITION NOT MET" in capsys.readouterr().err


# ------------------------------------------------------------------ the reporting paths

FIXTURE_CANVAS = """pending_tasks:
  - id: rec-1
    summary: >-
      u/AccountOne and u/AccountTwo both said it, convergence across strangers.
    source_class: external_human
"""


def _canvas(tmp_path):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "evidence.yml").write_text(FIXTURE_CANVAS)
    return tmp_path


def test_text_report_names_the_rule_and_the_remedy(scripts_path, tmp_path, monkeypatch, capsys):
    """The advisory has to say what to DO. A finding that names a defect without the
    cheapest next test is one the reader skips."""
    c = _import(scripts_path)
    root = _canvas(tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root)])
    assert c.main() == 0
    out = capsys.readouterr().out
    assert "ADVISORY" in out
    assert "DOES THE OP REPLY" in out, "the free first test must appear in the output"
    assert "Count ACCOUNTS, not comments" in out


def test_json_report_carries_the_scanned_count_even_when_clean(scripts_path, tmp_path,
                                                               monkeypatch, capsys):
    """Empty-input honesty at the reporting layer: 'nothing found' must stay
    distinguishable from 'nothing looked at'."""
    import json as _json
    c = _import(scripts_path)
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "clean.yml").write_text("pending_tasks: []\n")
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(tmp_path), "--json"])
    assert c.main() == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["files_scanned"] == 1, "a clean run must still report what it scanned"


def test_json_report_lists_violations(scripts_path, tmp_path, monkeypatch, capsys):
    import json as _json
    c = _import(scripts_path)
    root = _canvas(tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--json"])
    assert c.main() == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "violations"
    assert payload["violations"][0]["rule"].startswith("B/")


def test_quiet_when_clean_says_nothing(scripts_path, tmp_path, monkeypatch, capsys):
    c = _import(scripts_path)
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "clean.yml").write_text("pending_tasks: []\n")
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(tmp_path), "--quiet-when-clean"])
    assert c.main() == 0
    assert capsys.readouterr().out == ""


def test_self_handles_never_raises(scripts_path):
    """It shells out to git. A repo without git config, or without git at all, must
    degrade to 'no exclusions' rather than failing the scan."""
    c = _import(scripts_path)
    assert isinstance(c._self_handles(), set)


def test_unreadable_file_is_skipped_not_fatal(scripts_path, tmp_path):
    """A non-UTF-8 file in the tree must not abort the whole scan."""
    c = _import(scripts_path)
    from pathlib import Path
    p = tmp_path / "bad.yml"
    p.write_bytes(b"\xff\xfe\x00binary")
    assert list(c.iter_records(Path(p))) == []
