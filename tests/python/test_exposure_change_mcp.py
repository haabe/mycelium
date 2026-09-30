"""The exposure-change hook also fires on MCP filesystem writes (v0.289.0, phase migration stage 0a).

It told the agent when a write took the work from "may meet its audience" to "nothing may meet real
people", but was registered only for Write|Edit|MultiEdit, so a diamonds-file write through the MCP
filesystem tools moved the exposure state without a word. PreToolUse already had an MCP group.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "hooks" / "hooks.json"


def _post_hooks_for(tool: str) -> list[str]:
    groups = json.loads(HOOKS.read_text())["hooks"]["PostToolUse"]
    return [h["command"] for g in groups if re.fullmatch(g["matcher"], tool)
            for h in g["hooks"]]


def test_exposure_change_runs_after_an_mcp_filesystem_write():
    for tool in ("mcp__filesystem__write_file", "mcp__filesystem__edit_file", "mcp__filesystem__move_file"):
        assert any("exposure-change.sh" in c for c in _post_hooks_for(tool)), tool


def test_control_it_still_runs_after_the_native_write_tools():
    for tool in ("Write", "Edit", "MultiEdit"):
        assert any("exposure-change.sh" in c for c in _post_hooks_for(tool)), tool


def test_control_the_file_path_hooks_are_not_fed_mcp_input():
    """post-write-nudge and the canvas schema check parse `file_path`; MCP tools send `path`."""
    cmds = _post_hooks_for("mcp__filesystem__write_file")
    assert not any("post-write-nudge.sh" in c or "canvas-schema-check.sh" in c for c in cmds)
