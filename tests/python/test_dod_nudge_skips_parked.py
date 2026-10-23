"""The session-start Definition-of-Done nudge skips a closed diamond, parked included (v0.328.6).

CHECK 9 in hooks/session-start.sh kept its own copy of the closed states, {archived, killed}, so a diamond
parked to wait for evidence was reported as "a diamond with no outcome Definition of Done" on every session
start. On the dogfood project the agent put that to the founder as a decision, though his ruling on the
parked diamond already said its bar is written when it resumes. The check now reads scale_locks.CLOSED, the
set derive_closing_path and next_item already use. Runs the real hook.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
NUDGE = "have no outcome Definition of Done"


def _closed():
    if str(PLUGIN / "scripts") not in sys.path:
        sys.path.insert(0, str(PLUGIN / "scripts"))
    import scale_locks

    return scale_locks.CLOSED


def _session_start(root: Path) -> str:
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_PROJECT_DIR": str(root),
           "MYCELIUM_CROSS_REPO_WATCH": ""}
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup", "session_id": "t1"})
    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "session-start.sh"), "--fast"], input=payload,
                          capture_output=True, text=True, env=env, timeout=120, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _project(tmp_path: Path, diamonds: str) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(diamonds, encoding="utf-8")
    return tmp_path


def _flagged(out: str) -> str:
    for line in out.replace("\\n", "\n").splitlines():
        if NUDGE in line:
            return line[line.index(NUDGE):]
    return ""


def test_a_parked_diamond_is_not_flagged_and_an_open_one_is(tmp_path):
    root = _project(tmp_path, "active_diamonds:\n"
                              "  - {id: l3-open, scale: L3}\n"
                              "  - {id: l3-parked, scale: L3, state: parked,"
                              " resume_conditions: [when the interviews are in]}\n")
    flagged = _flagged(_session_start(root))
    assert "l3-open" in flagged, "control: an open diamond with no bar is still flagged"
    assert "l3-parked" not in flagged


def test_every_closed_state_is_skipped(tmp_path):
    states = sorted(_closed())
    body = "active_diamonds:\n" + "".join(
        f"  - {{id: d-{s}, scale: L3, state: {s}}}\n" for s in states)
    assert NUDGE not in _session_start(_project(tmp_path, body))


def test_the_closed_set_includes_parked():
    assert "parked" in _closed()
