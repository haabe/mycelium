"""One session start adds one to an open assumption-test counter (v0.322.3).

WHAT WAS WRONG. `hooks.json` registers `session-start.sh` twice for a session start on Claude Code,
`--fast` and then `--async` (the split is from 0.186.0), and the counter's increment had no guard
for that. Both passes added one, so a test set to review after ten sessions reported done after
five: the direction the hook's own comment calls dangerous, since it makes a shadow log look more
observed than it is. A reader of the first blind read flagged it as a maybe and it was left
unchecked; two readers of the second found it again, and a replay showed 0, 1, 2.

WHAT HOLDS NOW. The background pass reads the counter and does not write it.
"""

from __future__ import annotations

import json
import os
import site
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOK = PLUGIN / "hooks" / "session-start.sh"


def _project(tmp_path: Path, **fields) -> tuple[Path, Path]:
    project = tmp_path / "proj"
    (project / ".claude" / "canvas").mkdir(parents=True)
    (project / ".claude" / "diamonds").mkdir()
    tests = project / ".claude" / "evals" / "assumption-tests"
    tests.mkdir(parents=True)
    counter = tests / "t.count.json"
    counter.write_text(json.dumps({"test": "t", "started": "2026-10-12", "target": 10,
                                   "sessions": 0, "closed": False, "doc": "x", **fields}))
    return project, counter


def _start(project: Path, *mode: str, source: str = "startup") -> None:
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase()}
    payload = json.dumps({"hook_event_name": "SessionStart", "source": source,
                          "session_id": "s1", "cwd": str(project)})
    done = subprocess.run(["bash", str(HOOK), *mode], input=payload, text=True,
                          capture_output=True, env=env, timeout=180, check=False)
    assert done.returncode == 0, done.stderr[-400:]


def _sessions(counter: Path) -> int:
    return json.loads(counter.read_text())["sessions"]


def test_the_two_passes_of_one_start_count_once(tmp_path):
    """RED BEFORE 0.322.3: 2."""
    project, counter = _project(tmp_path)
    _start(project, "--fast")
    _start(project, "--async")
    assert _sessions(counter) == 1


def test_the_background_pass_alone_does_not_count(tmp_path):
    """RED BEFORE 0.322.3: 1. Whichever pass finishes first, the count is the fast one's."""
    project, counter = _project(tmp_path)
    _start(project, "--async")
    assert _sessions(counter) == 0


def test_control_a_runtime_with_one_unflagged_pass_still_counts(tmp_path):
    """Codex and Cursor register the hook once, with no flag."""
    project, counter = _project(tmp_path)
    _start(project)
    assert _sessions(counter) == 1


def test_control_a_continuation_does_not_count(tmp_path):
    """Unchanged since 0.104.0: resume, clear and fork carry the same session on."""
    project, counter = _project(tmp_path)
    for source in ("resume", "clear", "fork"):
        _start(project, "--fast", source=source)
    assert _sessions(counter) == 0


def test_control_a_closed_counter_is_left_alone(tmp_path):
    project, counter = _project(tmp_path, closed=True, sessions=4)
    _start(project, "--fast")
    assert _sessions(counter) == 4
