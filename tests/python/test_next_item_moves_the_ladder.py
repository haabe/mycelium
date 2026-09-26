"""The session-start next item proposes the step that moves a diamond (v0.249.0).

E2E run 18, the first happy-path run built to test Mycelium's own behaviour: four diamonds sat in
discover for three sessions with no progression ruling while research notes landed every session.
Nothing in Mycelium proposed the step that moves them; `next_item.py` proposed /diamond-progress only
for a FIRED closing path. On the happy path the ladder then climbs only if the driver remembers to
move it, and a route that never fires is no route.
"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "next_item", ROOT / "plugins" / "mycelium" / "scripts" / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)


def _project(tmp_path: Path, diamonds: list[dict]) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"product_paths": [], "active_diamonds": diamonds}))
    note = tmp_path / ".claude" / "canvas" / "purpose.yml"
    note.write_text("why: a purpose\n")
    stamp = time.mktime((2026, 9, 24, 12, 0, 0, 0, 0, -1))
    os.utime(note, (stamp, stamp))
    return tmp_path


def test_a_never_assessed_delivering_diamond_is_the_next_item(tmp_path):
    root = _project(tmp_path, [{"id": "l0", "scale": "L0", "phase": "discover"},
                               {"id": "l3", "scale": "L3", "phase": "discover"}])
    item, _ = ni.pick(root, "", "2026-09-24")
    assert item["command"] == "/mycelium:diamond-progress l3"
    assert "never been assessed" in item["text"] and "discover -> define" in item["text"]


def test_a_ruling_older_than_the_evidence_is_proposed_again(tmp_path):
    root = _project(tmp_path, [{"id": "l3", "scale": "L3", "phase": "define",
                                "progression_ruling": "needs-evidence",
                                "progression_ruled_at": "2026-09-20"}])
    item, _ = ni.pick(root, "", "2026-09-24")
    assert item and "evidence has landed since" in item["text"]


def test_a_ruling_newer_than_the_evidence_is_left_alone(tmp_path):
    root = _project(tmp_path, [{"id": "l3", "scale": "L3", "phase": "develop",
                                "progression_ruling": "progressed",
                                "progression_ruled_at": "2026-09-25"}])
    item, _ = ni.pick(root, "", "2026-09-25")
    assert item is None or not str(item.get("id", "")).startswith("unassessed:")


def test_closed_diamonds_are_never_proposed(tmp_path):
    root = _project(tmp_path, [{"id": "l3", "scale": "L3", "phase": "complete"},
                               {"id": "l4", "scale": "L4", "phase": "parked"}])
    assert ni._unassessed(root, "2026-09-24") == []
