"""tests/python/test_check_cynefin_freshness.py — the Cynefin staleness check.

WHY THIS MATTERS MORE THAN A BOOKKEEPING CHECK. The Cynefin domain drives METHOD selection.
A node classified Complicated routes to expert analysis; one classified Complex routes to
probe-sense-respond. So a classification that predates its evidence does not produce a stale
label — it produces **the wrong method, applied confidently, to current work.**

MEASURED AT ADOPTION: 75 classifications on the dogfood canvas, 0 checkable, because
`cynefin_domain` was a bare enum with no date. The check could not exist until the schema
carried `cynefin_classified_at`, which is why v0.242.0 is a schema change first.

THE TESTS PIN THREE THINGS THE CHECK MUST NOT DO:
  - must not treat "undated" as "current" (absent is not fresh)
  - must not fail the whole historical corpus, which would force backfilling dates nobody
    knows — inventing a classification date is the fabrication this framework refuses
  - must not print a summary count with an empty detail section. A refactor did exactly that
    during development: it reported 75 uncheckable and listed none, behind an early return.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))

import check_cynefin_freshness as mod


def _project(tmp_path: Path, opportunities: dict) -> Path:
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "opportunities.yml").write_text(yaml.safe_dump(opportunities), encoding="utf-8")
    return tmp_path


def _node(**kw) -> dict:
    base = {"id": "opp-001", "cynefin_domain": "complicated"}
    base.update(kw)
    return {"opportunities": [base]}


def test_stale_when_evidence_landed_after_classification(tmp_path, capsys):
    """THE CORE ASSERTION. Twenty interviews arriving after a Complicated call is exactly
    the case where the method stops matching the domain."""
    root = _project(tmp_path, _node(
        cynefin_classified_at="2026-01-10",
        cynefin_basis="three interviews, cause and effect traceable",
        evidence=[{"captured_at": "2026-06-01"}, {"captured_at": "2026-07-15"}],
    ))
    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "2026-07-15" in out, "must name the newest evidence, not just say stale"
    assert "prompt" in out.lower(), "a stale row is a prompt to re-run, never a verdict"


def test_current_when_classification_postdates_its_evidence(tmp_path):
    root = _project(tmp_path, _node(
        cynefin_classified_at="2026-08-01",
        cynefin_basis="re-read after the pilot",
        evidence=[{"captured_at": "2026-06-01"}],
    ))
    assert mod.main(["--project-dir", str(root)]) == 0


def test_undated_is_uncheckable_and_says_so(tmp_path, capsys):
    """Absent is not current. A check that treated a missing date as fresh would report
    the entire pre-adoption corpus as healthy."""
    root = _project(tmp_path, _node(evidence=[{"captured_at": "2026-06-01"}]))
    mod.main(["--project-dir", str(root)])
    out = capsys.readouterr().out
    assert "UNCHECKABLE" in out
    assert "not the same as current" in out


def test_uncheckable_section_lists_the_nodes(tmp_path, capsys):
    """REGRESSION GUARD. A refactor left this section behind an early `return`, so the
    check printed a count of 75 and listed none — a silent detail block under a green
    summary, produced inside the file written to catch that shape."""
    root = _project(tmp_path, _node(id="opp-042"))
    mod.main(["--project-dir", str(root)])
    out = capsys.readouterr().out
    assert "opp-042" in out, "the count must be accompanied by the rows it counted"


def test_baseline_suppresses_history_but_not_new_classifications(tmp_path, capsys):
    """Failing on all 75 would force inventing dates. Baseline the corpus; bite on what
    is written afterwards."""
    root = _project(tmp_path, _node(id="opp-old"))
    assert mod.main(["--project-dir", str(root), "--write-baseline"]) == 0
    assert mod.main(["--project-dir", str(root)]) == 0, "baselined history must not fail"

    doc = yaml.safe_load((root / ".claude" / "canvas" / "opportunities.yml").read_text())
    doc["opportunities"].append({"id": "opp-new", "cynefin_domain": "complex"})
    (root / ".claude" / "canvas" / "opportunities.yml").write_text(yaml.safe_dump(doc))

    assert mod.main(["--project-dir", str(root)]) == 1
    out = capsys.readouterr().out
    assert "opp-new" in out


def test_baseline_states_it_must_never_grow(tmp_path):
    root = _project(tmp_path, _node(id="opp-1"))
    mod.main(["--project-dir", str(root), "--write-baseline"])
    data = json.loads(
        (root / ".claude" / "evals" / "cynefin-freshness-baseline.json").read_text())
    assert data["undated"] == ["opp-1"]
    assert "never grow" in data["_comment"]
    assert "fabrication" in data["_comment"], (
        "the baseline must say why backfilling is refused, not merely that it is")


def test_missing_basis_is_surfaced(tmp_path, capsys):
    """A domain with no basis cannot be re-argued when the data changes; the next reader
    can only accept or discard it."""
    root = _project(tmp_path, _node(cynefin_classified_at="2026-08-01"))
    mod.main(["--project-dir", str(root)])
    assert "NO BASIS" in capsys.readouterr().out


def test_absent_canvas_exits_2_not_0(tmp_path, capsys):
    """Same rule the empty-input guard enforces project-wide: a check that examined
    nothing must not return success, because only the exit code is read by CI."""
    assert mod.main(["--project-dir", str(tmp_path)]) == 2
    assert "NOTHING WAS EXAMINED" in capsys.readouterr().err


def test_never_reclassifies(tmp_path):
    """The check compares dates. Which domain a thing is in is judgement, and belongs to
    /mycelium:cynefin-classify and a human. If this ever writes a domain, it has taken a
    decision it cannot justify."""
    root = _project(tmp_path, _node(
        cynefin_classified_at="2026-01-01", evidence=[{"captured_at": "2026-06-01"}]))
    before = (root / ".claude" / "canvas" / "opportunities.yml").read_text()
    mod.main(["--project-dir", str(root)])
    assert (root / ".claude" / "canvas" / "opportunities.yml").read_text() == before


@pytest.mark.parametrize("key", ["captured_at", "validated_at", "observed_at", "as_of", "date"])
def test_all_evidence_date_keys_are_read(tmp_path, key):
    """Real canvases use several spellings. A check that read only `captured_at` would
    report most nodes as current because it never saw their evidence."""
    root = _project(tmp_path, _node(
        cynefin_classified_at="2026-01-01", evidence=[{key: "2026-06-01"}]))
    assert mod.main(["--project-dir", str(root)]) == 1, f"{key} must count as evidence"


def test_unreadable_date_is_reported_not_dropped(tmp_path, capsys):
    """THE FAIL-OPEN GUARD, and `check_fail_open.py` blocked this file's first push to force it.

    `_parse` returned None for anything it could not read. For an ABSENT field that is correct —
    absence is handled explicitly as UNCHECKABLE. For a PRESENT but unreadable value it was a
    silent drop: the date vanished from the comparison and the node then read as CURRENT, because
    the check could not see what was under it. A check that reports fresh when it failed to read
    the evidence is the exact shape this whole file exists to catch."""
    mod.UNREADABLE.clear()
    root = _project(tmp_path, _node(
        cynefin_classified_at="2026-01-01",
        cynefin_basis="early read",
        evidence=[{"captured_at": "last spring"}],
    ))
    rc = mod.main(["--project-dir", str(root)])
    out = capsys.readouterr().out
    assert rc == 1, "an unreadable evidence date must fail, not pass as current"
    assert "unreadable" in out.lower()
    assert "last spring" in out, "must quote the value it could not read"
    assert "read as CURRENT" in out, "must say what the silent version would have done"


def test_absent_date_is_not_counted_as_unreadable(tmp_path):
    """The complement. Absence is a different finding from unreadability, and conflating
    them would make every pre-adoption node look like corrupt data."""
    mod.UNREADABLE.clear()
    root = _project(tmp_path, _node(evidence=[{"captured_at": None}]))
    mod.main(["--project-dir", str(root)])
    assert mod.UNREADABLE == [], "a None date is absent, not malformed"
