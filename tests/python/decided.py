"""Test fixtures written with a `phase` get the decisions that phase stands for (v0.306.0).

Since stage 5c (DL-1368) the phase is not read: where a diamond is comes from its decision log. The
fixtures still say where each diamond is with a `phase`, because that is the readable way to set
up a state; this converts them through the migration's own function (`migrate_phase.convert`), so a
test exercises the same conversion a project gets: decisions for a phase that placed the diamond,
`state` for one that closed it. A diamond that already records decisions is left alone.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))
import migrate_phase as mp

_LISTS = ("active_diamonds", "completed_diamonds", "archived_diamonds")


def decided_one(d: dict, key: str = "active_diamonds") -> dict:
    """One diamond, converted (a copy; the fixture is not changed)."""
    if not isinstance(d, dict):
        return d
    out = copy.deepcopy(d)
    mp.convert(out, key)
    return out


def decided(obj):
    """A diamonds document, a list of diamonds, or one diamond, converted."""
    if isinstance(obj, list):
        return [decided_one(d) for d in obj]
    if isinstance(obj, dict) and any(k in obj for k in _LISTS):
        return {k: ([decided_one(d, k) for d in v] if k in _LISTS and isinstance(v, list) else v)
                for k, v in obj.items()}
    return decided_one(obj)


def decided_text(text: str) -> str:
    """A diamonds file's text, converted; text that does not parse is returned as it is."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return text
    if not isinstance(doc, (dict, list)):
        return text
    converted = decided(doc)
    # unchanged text when nothing needed converting, so a test that edits by exact text still can
    return text if converted == doc else yaml.safe_dump(converted)
