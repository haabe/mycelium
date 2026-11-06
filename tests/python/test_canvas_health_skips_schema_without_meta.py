"""canvas-health step 3 must not ask a canvas for `_meta` when its schema has none (v0.333.0).

Found on the dogfood repo 2026-11-06: step 3 flagged doctrine.yml for a missing `_meta` on every
pass, though schemas/canvas/doctrine.schema.json deliberately declares no `_meta` and keeps
freshness in an event-based `last_reviewed` that check_doctrine_due.py reads. A warning a correct
file cannot clear trains the reader to skip the list.

The step is instructions, not a script, so the test pins the two facts the rule rests on: the
step carries the exemption, and every schema it would exempt really has no `_meta` while naming
its own freshness field. If a schema gains `_meta`, or the step loses the rule, this fails.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SKILL = ROOT / "skills" / "canvas-health" / "SKILL.md"
SCHEMAS = ROOT / "schemas" / "canvas"


def _step3(text: str) -> str:
    start = text.index("3. **Check `_meta` blocks**")
    return text[start:text.index("\n4. ", start)]


def test_step_3_carries_the_schema_without_meta_exemption():
    step = _step3(SKILL.read_text(encoding="utf-8"))
    assert "schema declares no `_meta`" in step
    assert "doctrine.yml" in step and "last_reviewed" in step


def test_the_exempted_schema_has_no_meta_and_its_own_freshness_field():
    schema = json.loads((SCHEMAS / "doctrine.schema.json").read_text(encoding="utf-8"))
    props = schema.get("properties") or {}
    assert "_meta" not in props, "doctrine now declares _meta; drop it from the step 3 exemption"
    assert "last_reviewed" in props


def test_schemas_that_declare_meta_are_not_exempted():
    """Control: the exemption is about schemas without `_meta`; most canvas schemas have one."""
    with_meta = [p.name for p in SCHEMAS.glob("*.schema.json")
                 if "_meta" in (json.loads(p.read_text(encoding="utf-8")).get("properties") or {})]
    assert with_meta, "no canvas schema declares _meta; the step's premise has changed"
    assert "doctrine.schema.json" not in with_meta
