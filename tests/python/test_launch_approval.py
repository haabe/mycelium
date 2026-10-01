"""The L5 human-approval floor, enforced (v0.292.0; dogfood decision log DL-1364).

It was prose in confidence-thresholds.yml (`NO_REDUCTION` on L5 develop->deliver and
deliver->complete) that no code read, so an agent could move a launch forward on its own. A write
that moves an L5 into deliver or complete now asks the person in the permission dialog, and is
refused where nobody would be asked. The ask runs only once the write passes the scale lock.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import scale_locks as sl  # noqa: E402

#: In develop by their decisions (v0.306.0: the phase is not read). A move adds the next decision.
DEV = "decisions: [{decision: set_target}, {decision: start_experiment}, {decision: commit_to_build}]"
BEFORE = f"""active_diamonds:
  - id: l4-a
    scale: L4
    phase: develop
    {DEV}
  - id: l5-a
    scale: L5
    phase: develop
    {DEV}
"""
RELEASED = DEV[:-1] + ", {decision: release}]"


def _project(tmp_path: Path, text: str = BEFORE) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(text)
    return tmp_path


def _move(tmp_path: Path, diamond: str, to: str, mode: str | None = "default") -> dict:
    target = tmp_path / ".claude" / "diamonds" / "active.yml"
    old = f"  - id: {diamond}\n" + target.read_text().split(f"  - id: {diamond}\n", 1)[1].split("  - id:")[0]
    new = old.replace("phase: develop", f"phase: {to}").replace(
        DEV, RELEASED[:-1] + (", {decision: close}]" if to == "complete" else "]"))
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": old,
                                                   "new_string": new}}
    if mode is not None:
        payload["permission_mode"] = mode
    return payload


def _decision(tmp_path, payload, capsys) -> str | None:
    sl._launch_approval(str(tmp_path), payload)
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


@pytest.mark.parametrize("to", ["deliver", "complete"])
def test_moving_an_l5_to_launch_asks_the_person(tmp_path, capsys, monkeypatch, to):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path)
    assert _decision(p, _move(p, "l5-a", to), capsys) == "ask"


def test_with_permissions_bypassed_it_is_refused(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path)
    assert _decision(p, _move(p, "l5-a", "deliver", mode="bypassPermissions"), capsys) == "deny"


def test_on_codex_it_is_refused(tmp_path, capsys, monkeypatch):
    """Codex treats an `ask` as a failed hook and lets the call through, so an ask there is an allow."""
    monkeypatch.setenv("MYCELIUM_RUNTIME", "codex")
    p = _project(tmp_path)
    assert _decision(p, _move(p, "l5-a", "deliver"), capsys) == "deny"


def test_control_an_l5_already_delivering_is_not_asked_again(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    released = BEFORE.split("  - id: l5-a\n")
    p = _project(tmp_path, released[0] + "  - id: l5-a\n"
                 + released[1].replace("phase: develop", "phase: deliver").replace(DEV, RELEASED))
    target = p / ".claude" / "diamonds" / "active.yml"
    payload = {"tool_name": "Edit", "permission_mode": "default", "tool_input": {
        "file_path": str(target), "old_string": "    phase: deliver\n",
        "new_string": "    phase: deliver\n    notes: a note\n"}}
    assert _decision(p, payload, capsys) is None


def test_control_an_l4_moving_to_deliver_is_not_asked(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    p = _project(tmp_path)
    assert _decision(p, _move(p, "l4-a", "deliver"), capsys) is None


def test_moving_into_the_completed_list_counts(tmp_path):
    before = BEFORE.replace("    phase: develop\n", "    phase: deliver\n")
    after = ("active_diamonds:\n  - id: l4-a\n    scale: L4\n    phase: deliver\n"
             "completed_diamonds:\n  - id: l5-a\n    scale: L5\n    phase: deliver\n")
    assert sl.launch_moves(before.replace("id: l5-a\n    scale: L5\n    phase: deliver",
                                          "id: l5-a\n    scale: L5\n    phase: develop"), after) == ["l5-a"]
