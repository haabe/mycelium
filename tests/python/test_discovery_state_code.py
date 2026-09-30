"""The discovery check tells "not engaged" from "cannot check" (v0.290.0).

Without PyYAML the diamonds file went unread, so a project with diamonds read as one with none, and
the build gate refused with "this project has no discovery state yet", which was false. Exit 3 now
means "cannot check", and the gate refuses with the real reason and the fix.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
_spec = importlib.util.spec_from_file_location("_hook_input_dsc", SCRIPTS / "_hook_input.py")
hi = importlib.util.module_from_spec(_spec)
sys.modules["_hook_input_dsc"] = hi  # its dataclasses look their module up by name
_spec.loader.exec_module(hi)

DIAMONDS = "active_diamonds:\n  - id: l3-001\n    scale: L3\n    phase: define\n"


def _project(tmp_path: Path, diamonds: str | None) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    if diamonds is not None:
        (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(diamonds)
    return tmp_path


def test_diamonds_that_cannot_be_read_are_cannot_check(tmp_path, monkeypatch):
    p = _project(tmp_path, DIAMONDS)
    monkeypatch.setitem(sys.modules, "yaml", None)  # import yaml now raises ImportError
    assert hi.discovery_state_code(str(p)) == 3


def test_control_with_pyyaml_the_same_project_is_engaged(tmp_path):
    p = _project(tmp_path, DIAMONDS)
    assert hi.discovery_state_code(str(p)) == 0


def test_control_without_pyyaml_and_without_diamonds_it_is_not_engaged(tmp_path, monkeypatch):
    p = _project(tmp_path, "active_diamonds: []\n")
    monkeypatch.setitem(sys.modules, "yaml", None)
    assert hi.discovery_state_code(str(p)) == 1


def test_no_diamonds_file_is_not_engaged(tmp_path, monkeypatch):
    p = _project(tmp_path, None)
    monkeypatch.setitem(sys.modules, "yaml", None)
    assert hi.discovery_state_code(str(p)) == 1
