"""The secret scan looks at files under `.claude/` too (v0.322.3).

WHAT WAS WRONG. `gate.sh` skipped every write target under `.claude/`, so a credential written
into a canvas file, the decision log, memory or the diamonds file was never scanned. Those files
are committed. README.md said "Anything that looks like a password or a key going into a file is
refused outright". Found by all three readers of the second blind read (2026-10-12).

WHAT HOLDS NOW (maintainer's ruling the same day: "Scan .claude/ too"). Every target inside the
project is scanned except `.claude/state/`, which holds the hooks' own logs and is ignored by git.
A target outside the project is still not scanned; that was not part of the ruling and
`test_control_a_file_outside_the_project_is_still_not_scanned` pins it so a change is a decision.

Every credential-shaped value is BUILT AT RUN TIME from harmless parts, as in
`test_gate_secret_scan.py`, so this file is not refused by the hook it tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "gate.sh"

KEY = "ab12" * 6
SECRET = f'API_KEY="{KEY}"'
HARMLESS = "The key assumption is that people come back in week two."
REFUSED = "G-S1"

COMMITTED = [
    ".claude/canvas/purpose.yml",
    ".claude/canvas/opportunities.yml",
    ".claude/harness/decision-log.md",
    ".claude/memory/corrections.md",
    ".claude/diamonds/active.yml",
    ".claude/handoffs/2026-10-12-a-note.md",
    ".claude/skills/mine/SKILL.md",
    ".claude/settings.json",
]


def _gate(project: Path, tool: str, tool_input: dict) -> str:
    (project / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)  # a Mycelium project
    payload = json.dumps({"tool_name": tool, "permission_mode": "default", "tool_input": tool_input})
    env = {"CLAUDE_PROJECT_DIR": str(project), "HOME": str(project), "TMPDIR": str(project),
           "PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)}
    done = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                          env=env, cwd=project, check=False)
    return done.stdout


@pytest.mark.parametrize("rel", COMMITTED)
def test_a_credential_written_under_dot_claude_is_refused(tmp_path, rel):
    """RED BEFORE 0.322.3: every one of these passed unscanned."""
    out = _gate(tmp_path, "Write", {"file_path": rel, "content": SECRET})
    assert REFUSED in out, rel


def test_an_edit_that_adds_a_credential_to_a_canvas_file_is_refused(tmp_path):
    """RED BEFORE 0.322.3. The Edit tool's new text is content too."""
    canvas = tmp_path / ".claude" / "canvas" / "purpose.yml"
    canvas.parent.mkdir(parents=True)
    canvas.write_text("why: to be written\n")
    out = _gate(tmp_path, "Edit", {"file_path": str(canvas), "old_string": "to be written",
                                   "new_string": SECRET})
    assert REFUSED in out


def test_control_ordinary_canvas_text_is_not_refused(tmp_path):
    """The word "key" in prose is what a canvas mostly holds; refusing it would stop all work."""
    for rel in COMMITTED:
        assert REFUSED not in _gate(tmp_path, "Write", {"file_path": rel, "content": HARMLESS}), rel


def test_control_myceliums_own_state_folder_stays_out(tmp_path):
    """Logs and stamps the hooks write, ignored by git. Scanning them would have the gate judge
    its own records."""
    out = _gate(tmp_path, "Write", {"file_path": ".claude/state/read-log.jsonl", "content": SECRET})
    assert REFUSED not in out


def test_control_product_code_is_refused_as_before(tmp_path):
    assert REFUSED in _gate(tmp_path, "Write", {"file_path": "src/config.py", "content": SECRET})


def test_control_a_file_outside_the_project_is_still_not_scanned(tmp_path):
    """Not changed in 0.322.3, and said so in README.md. Pinned so widening it is a decision."""
    project = tmp_path / "proj"
    project.mkdir()
    outside = tmp_path / "elsewhere" / "notes.txt"
    outside.parent.mkdir()
    assert REFUSED not in _gate(project, "Write", {"file_path": str(outside), "content": SECRET})
