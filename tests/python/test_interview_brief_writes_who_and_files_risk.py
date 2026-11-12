"""The interview brief states the shape of `who`, and files "will people pay" under value.

WHAT WAS WRONG (two findings from one blind brief run, 2026-10-08).

1. `skills/interview/SKILL.md` told the agent to write purpose.yml's `who` "from Q1's for-whom
   half" and never said the schema types it as an object. The brief agent wrote a string, the write
   failed the schema, and it redid it. The L1 entry lock reads this field, and four of eight
   end-to-end runs had already left it out (v0.245.0).
2. The depth heuristic table sent a Q3 answer "will users pay" to Phase 4 Landscape as a viability
   risk. Cagan puts "whether customers will buy it or users will choose to use it" under value, and
   the framework's own theory-gates.md defines viability as alignment with the business model,
   legal and ethical constraints. A willingness-to-pay question went to a market scan instead of a
   value test.

WHAT THIS PINS. The `who` example the skill gives passes the shipped purpose schema and the L1 lock's
emptiness rule, a string `who` still fails the schema (so the sentence that says so stays true), and
the bookkeeping keys the skill names are the ones scale_locks ignores. The heuristic table files
willingness to pay as value and keeps unit economics under viability.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SKILL = PLUGIN / "skills" / "interview" / "SKILL.md"
SCHEMA_DIR = PLUGIN / "schemas" / "canvas"

if str(PLUGIN / "scripts") not in sys.path:
    sys.path.insert(0, str(PLUGIN / "scripts"))

import scale_locks  # noqa: E402
import validate_canvas  # noqa: E402


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _who_example() -> dict:
    m = re.search(r"`(who: \{[^`]*\})`", _text())
    assert m, "the interview skill no longer gives an example of the `who` mapping"
    return yaml.safe_load(m.group(1))


def _purpose_errors(tmp_path: Path, who, monkeypatch) -> list[str]:
    monkeypatch.setattr(validate_canvas, "SCHEMA_DIR", SCHEMA_DIR)
    monkeypatch.setattr(validate_canvas, "COMMON_SCHEMA", SCHEMA_DIR / "_common.schema.json")
    canvas = tmp_path / "purpose.yml"
    doc = {"why": "So that a shipped thing nobody used stops being a quiet defeat", "who": who}
    canvas.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return validate_canvas.validate_canvas_against_schema(canvas, validate_canvas.build_registry())


def test_the_documented_who_passes_the_schema(tmp_path, monkeypatch):
    example = _who_example()
    assert isinstance(example["who"], dict)
    assert _purpose_errors(tmp_path, example["who"], monkeypatch) == []


def test_a_string_who_fails_the_schema_as_the_skill_says(tmp_path, monkeypatch):
    errors = _purpose_errors(tmp_path, "freelance designers", monkeypatch)
    assert any("who" in e and "object" in e for e in errors), errors


def test_the_documented_who_is_not_empty_to_the_l1_lock():
    assert scale_locks._filled(_who_example()["who"])


def test_the_bookkeeping_keys_named_are_the_ones_the_lock_ignores():
    line = next(ln for ln in _text().splitlines() if "**`who` is a mapping" in ln)
    m = re.search(r"other than the bookkeeping keys \(([^)]*)\)", line)
    assert m, "the skill no longer names the bookkeeping keys that do not count"
    named = set(re.findall(r"`([^`]+)`", m.group(1)))
    assert named == set(scale_locks._BOOKKEEPING)


def _heuristic_rows() -> list[str]:
    text = _text()
    start = text.index("**Heuristic table**")
    return [ln for ln in text[start:].splitlines()[:20] if ln.startswith("| Q3 names")]


def test_willingness_to_pay_is_filed_under_value():
    rows = _heuristic_rows()
    pay = [r for r in rows if "will people pay" in r]
    assert len(pay) == 1, rows
    assert "**value**" in pay[0] and "**viability**" not in pay[0]


@pytest.mark.parametrize("phrase", ["will users pay", "will people pay"])
def test_viability_no_longer_holds_willingness_to_pay(phrase):
    viability = [r for r in _heuristic_rows() if "**viability**" in r]
    assert len(viability) == 1
    assert phrase not in viability[0]
    assert "unit economics" in viability[0]
