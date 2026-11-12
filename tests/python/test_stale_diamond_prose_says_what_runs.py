"""Stale-diamond detection is described as what runs, not as a check nothing implements (2026-09-19).

WHAT WAS WRONG. `engine/diamond-rules.md` and `orchestration/operations.md` both defined a stale
diamond ("No progress for 30+ days", "Phase hasn't changed in 2+ weeks", ...) as if something
detected it. Nothing did: no script computes a diamond's age, and the one mechanism that proposes a
diamond for a ruling, `next_item.py`'s `_unassessed`, is driven by new evidence. A reader believed a
staleness check ran; on the dogfood project an L0 sat 109 days and nothing flagged it.

WHAT THIS PINS. Both prose sites say nothing computes staleness and name the evidence-driven rule
that does run, and the old automatic-sounding wording is gone. The facts the prose leans on are
checked against the code: `_unassessed` exists, no script or hook reads an age field, and the
confidence check still documents why it has no time threshold. If someone adds age detection, the
third test fails and the prose must be rewritten with it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SITES = {"diamond-rules": PLUGIN / "engine" / "diamond-rules.md",
         "operations": PLUGIN / "orchestration" / "operations.md"}


def _section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index("### Stale Diamond Detection")
    return text[start:text.index("### Cleanup Process", start)]


@pytest.mark.parametrize("name", sorted(SITES))
def test_the_prose_says_what_runs(name):
    section = _section(SITES[name])
    assert "scripts/next_item.py" in section
    assert "never proposed" in section
    assert "No progress for 30+ days" not in section
    assert "Phase hasn't changed" not in section


def test_the_engine_says_nothing_computes_the_signs():
    assert "nothing computes them" in _section(SITES["diamond-rules"])


def test_the_code_still_matches_the_prose():
    scripts = (PLUGIN / "scripts" / "next_item.py").read_text(encoding="utf-8")
    assert "def _unassessed(" in scripts
    readers = [p for d in ("scripts", "hooks") for p in (PLUGIN / d).rglob("*")
               if p.is_file() and p.suffix in (".py", ".sh")
               and "last_progressed" in p.read_text(encoding="utf-8", errors="replace")]
    assert readers == [], f"an age field is now read by {readers}: rewrite the stale-diamond prose"
    confidence = (PLUGIN / "scripts" / "check_confidence_managed.py").read_text(encoding="utf-8")
    assert "NO TIME THRESHOLD" in confidence
