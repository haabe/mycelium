"""Coverage proof for check_instrument_contract.py.

THE GAP IT CLOSES. `/mycelium:assumption-test` Step 5 asks for a prediction before
the run and Step 6 never says where it lands. Measured in dogfood 2026-08-20: 27 of
36 instrument files stated a freeze convention in prose, in 27 different phrasings,
and none carried an expiry. Two frozen predictions were lost to that — one held
thresholds 102 days and was closed never-run, one sat in a repo that was never
committed.

WHY THE GREEN CASE IS TESTED FIRST AND HARDEST. This check was run against a real
36-file corpus before these tests existed and reported 32 problems. A check that has
only ever been red has not been tested either — it has been run. The first test below
exists to prove the thing can pass, and `test_drift_*` exists to prove the most
valuable report is not permanently unreachable.

Scenario-per-guardpost:
  happy — full contract, live, not yet due                 -> clean, exit 0
  happy — scored instrument, prediction block untouched    -> clean
  happy — metric adapter spec with no prediction prose     -> ignored, not flagged
  happy — `status: not-an-instrument`                      -> suppressed by choice
  sad   — prediction prose, no header                      -> UNCONTRACTED
  sad   — contract present, no score_by                    -> NO EXPIRY
  sad   — live and score_by in the past                    -> DUE / OVERDUE
  sad   — status not in the enum                           -> BAD STATUS
  bad   — prediction block edited after first commit       -> DRIFTED
  bad   — same edit, but `amended:` recorded               -> NOT drifted
  bad   — directory missing entirely                       -> UNKNOWN, exit 2
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_MOD = (Path(__file__).resolve().parents[2]
        / "plugins" / "mycelium" / "scripts" / "check_instrument_contract.py")
_spec = importlib.util.spec_from_file_location("check_instrument_contract", _MOD)
cic = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cic)

TODAY = _dt.date(2026, 8, 20)

HEADER = """---
type: assumption-test
frozen_at: 2026-08-16
frozen_before: "any comment is fetched"
score_by: {score_by}
status: {status}
---

# Test

## Frozen prediction

{prediction}
"""


def _repo(tmp_path: Path) -> Path:
    d = tmp_path / ".claude" / "evals" / "assumption-tests"
    d.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _commit(root: Path, msg: str = "add") -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=root, check=True)


def _write(root: Path, name: str, text: str) -> Path:
    p = root / ".claude" / "evals" / "assumption-tests" / name
    p.write_text(text, encoding="utf-8")
    return p


# --- happy -----------------------------------------------------------------

def test_full_contract_not_yet_due_is_clean(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="live",
                                       prediction="I expect 3 of 5."))
    _commit(root)
    r = cic.analyse(root, TODAY)
    assert r["contracted"] == ["a.md"]
    assert not r["undated"] and not r["due"] and not r["drifted"]
    assert not r["uncontracted"] and not r["untracked"]


def test_scored_and_untouched_is_clean(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-08-18", status="scored",
                                       prediction="I expect 3 of 5. Result: missed."))
    _commit(root)
    r = cic.analyse(root, TODAY)
    assert r["scored"] == ["a.md"]
    assert r["refuted"] == ["a.md"]  # "missed" counts as a refutation record
    assert not r["due"] and not r["drifted"]


def test_adapter_spec_without_prediction_prose_is_ignored(tmp_path):
    """The four metric adapters that drifted into the real directory must not be
    reported forever. A surface with no membership rule collects what is nearby."""
    root = _repo(tmp_path)
    _write(root, "stripe-adapter.md",
           '---\nname: stripe-metrics\ndescription: "Pull Stripe revenue."\n---\n\n# Adapter\n')
    _commit(root)
    r = cic.analyse(root, TODAY)
    assert not r["uncontracted"] and not r["contracted"]


def test_not_an_instrument_is_suppressed_by_choice(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-01-01", status="not-an-instrument",
                                       prediction="I expect nothing; no prediction is frozen."))
    _commit(root)
    r = cic.analyse(root, TODAY)
    assert not r["undated"] and not r["due"] and not r["contracted"]


# --- sad -------------------------------------------------------------------

def test_prediction_prose_without_header_is_uncontracted(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", "# Test\n\n**PRE-REGISTERED 2026-08-16, BEFORE ANY FETCH.**\n")
    _commit(root)
    assert cic.analyse(root, TODAY)["uncontracted"] == ["a.md"]


def test_missing_score_by_is_undated(tmp_path):
    """The field whose absence produced the 102-day never-run test."""
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="", status="live",
                                       prediction="I expect 3 of 5."))
    _commit(root)
    assert cic.analyse(root, TODAY)["undated"] == ["a.md"]


def test_live_and_past_due_is_reported_with_age(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-05-10", status="live",
                                       prediction="I expect 3 of 5."))
    _commit(root)
    due = cic.analyse(root, TODAY)["due"]
    assert due and due[0][0] == "a.md" and due[0][2] == 102  # the real one was 102 days


def test_status_outside_the_enum_is_reported(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="in_progress",
                                       prediction="I expect 3 of 5."))
    _commit(root)
    assert cic.analyse(root, TODAY)["bad_status"] == [("a.md", "in_progress")]


# --- bad path: drift, the report this check exists for ----------------------

def test_edited_prediction_block_is_drift(tmp_path):
    """Outcome switching: the failure COMPare found in registered trials, where the
    registry existed and nobody diffed it against what was reported."""
    root = _repo(tmp_path)
    p = _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="live",
                                           prediction="I expect 3 of 5."))
    _commit(root)
    p.write_text(p.read_text(encoding="utf-8").replace("3 of 5", "1 of 5"), encoding="utf-8")
    _commit(root, "quietly loosen the threshold")
    drifted = cic.analyse(root, TODAY)["drifted"]
    assert drifted and drifted[0][0] == "a.md"


def test_recorded_amendment_is_not_drift(tmp_path):
    """Amendments are recorded, never forbidden — ClinicalTrials.gov keeps every
    revision in a public History of Changes rather than preventing edits."""
    root = _repo(tmp_path)
    p = _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="live",
                                           prediction="I expect 3 of 5."))
    _commit(root)
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("3 of 5", "1 of 5")
                 .replace("status: live", 'status: live\namended: "2026-08-19, before any data"'),
                 encoding="utf-8")
    _commit(root, "amend, recorded")
    assert not cic.analyse(root, TODAY)["drifted"]


def test_uncommitted_instrument_is_untracked(tmp_path):
    """The habisji failure: a pre-registration in a repo that was never committed,
    so not even a git timestamp exists for it."""
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="live",
                                       prediction="I expect 3 of 5."))
    # deliberately not committed
    assert cic.analyse(root, TODAY)["untracked"] == ["a.md"]


def test_missing_directory_is_unknown_not_clean(tmp_path, monkeypatch, capsys):
    """A check that cannot run must never report a pass."""
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(tmp_path), "--today", "2026-08-20"])
    assert cic.main() == 2


def test_bad_today_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(tmp_path), "--today", "not-a-date"])
    assert cic.main() == 2


def test_output_states_what_it_cannot_check(tmp_path, monkeypatch, capsys):
    """Preregistration adds no severity on its own. A green here that reads as a
    quality signal is the veneer-of-rigor failure, so the limit is printed, always."""
    root = _repo(tmp_path)
    _write(root, "a.md", HEADER.format(score_by="2026-08-30", status="live",
                                       prediction="I expect 3 of 5."))
    _commit(root)
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--today", "2026-08-20"])
    assert cic.main() == 0
    out = capsys.readouterr().out
    assert "cannot tell you a prediction was good" in out
    assert "paperwork" in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
