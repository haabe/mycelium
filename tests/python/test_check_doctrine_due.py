"""check_doctrine_due.py — the evaluator the firing condition did not have.

v0.231.0 gave the doctrine retrospective a firing condition and wired its producer to its
consumer, then left the condition as prose inside a skill. Nothing computed it, so it fired only
when someone opened that skill — the same "runs when a person remembers" shape the condition was
written to replace. These tests pin the evaluator's contract, including the two cases where a
quiet answer would be a lie: "nothing completed yet" must not read as "doctrine is current", and
an unreadable register must not read as "nothing due".
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/mycelium/scripts/check_doctrine_due.py"

COMPLETED = textwrap.dedent("""\
    schema_version: 1
    active_diamonds: []
    completed_diamonds:
      - id: l4-x
        scale: L4
        phase: complete
        confidence: 0.8
        completed_at: "2026-09-20"
        dod_verdict:
          signal_observed: "three strangers ran it unaided"
          verified_by: "touch log"
    """)


def run(project: Path, today: str = "2026-09-21") -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(project), "--today", today],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def make(tmp_path: Path, diamonds: str | None, doctrine: str | None) -> Path:
    if diamonds is not None:
        d = tmp_path / ".claude/diamonds"
        d.mkdir(parents=True, exist_ok=True)
        (d / "active.yml").write_text(diamonds, encoding="utf-8")
    if doctrine is not None:
        c = tmp_path / ".claude/canvas"
        c.mkdir(parents=True, exist_ok=True)
        (c / "doctrine.yml").write_text(doctrine, encoding="utf-8")
    return tmp_path


def test_due_when_a_diamond_completed_and_doctrine_never_reviewed(tmp_path: Path) -> None:
    rc, out = run(make(tmp_path, COMPLETED, None))
    assert rc == 0, "advisory, never a gate"
    assert out.startswith("DOCTRINE RETROSPECTIVE DUE")
    assert "never reviewed" in out


def test_due_when_a_diamond_completed_after_the_last_review(tmp_path: Path) -> None:
    rc, out = run(make(tmp_path, COMPLETED, "schema_version: 1\nlast_reviewed: '2026-09-01'\n"))
    assert rc == 0
    assert out.startswith("DOCTRINE RETROSPECTIVE DUE")
    assert "2026-09-20" in out


def test_not_due_when_the_review_is_newer_than_the_newest_completion(tmp_path: Path) -> None:
    rc, out = run(make(tmp_path, COMPLETED, "schema_version: 1\nlast_reviewed: '2026-09-21'\n"))
    assert rc == 0
    assert out.startswith("OK:")


def test_due_on_a_climate_prediction_past_horizon_and_unscored(tmp_path: Path) -> None:
    """An unscored prediction is not a held one. A register that only grows is a wish list."""
    doctrine = textwrap.dedent("""\
        schema_version: 1
        last_reviewed: '2026-09-21'
        climate:
          - id: cl-001
            prediction: "X commoditises"
            as_of: '2026-06-01'
            horizon: '2026-09-15'
        """)
    rc, out = run(make(tmp_path, COMPLETED, doctrine))
    assert rc == 0
    assert "past horizon and unscored" in out
    assert "cl-001" in out


def test_a_scored_prediction_past_horizon_is_not_due(tmp_path: Path) -> None:
    doctrine = textwrap.dedent("""\
        schema_version: 1
        last_reviewed: '2026-09-21'
        climate:
          - id: cl-001
            prediction: "X commoditises"
            as_of: '2026-06-01'
            horizon: '2026-09-15'
            outcome: unclear
        """)
    rc, out = run(make(tmp_path, COMPLETED, doctrine))
    assert rc == 0
    assert out.startswith("OK:")


def test_no_completion_yet_does_not_read_as_doctrine_is_current(tmp_path: Path) -> None:
    """The load-bearing honesty case. Nothing reviewable is not the same as nothing to review."""
    rc, out = run(make(tmp_path, "schema_version: 1\nactive_diamonds: []\n", None))
    assert rc == 0
    assert "cannot fire" in out
    assert "NOT 'doctrine is current'" in out


def test_an_unreadable_register_is_announced_not_swallowed(tmp_path: Path) -> None:
    """'Could not look' and 'nothing due' are indistinguishable unless the first says so."""
    rc, out = run(make(tmp_path, COMPLETED, "last_reviewed: [unclosed\n"))
    assert rc == 0, "still advisory"
    assert out.startswith("UNREADABLE")
    assert "did NOT run" in out


@pytest.mark.parametrize("missing", ["diamonds", "both"])
def test_missing_files_are_not_an_error(tmp_path: Path, missing: str) -> None:
    diamonds = None if missing in {"diamonds", "both"} else COMPLETED
    rc, out = run(make(tmp_path, diamonds, None))
    assert rc == 0
    assert out.startswith("OK:")
