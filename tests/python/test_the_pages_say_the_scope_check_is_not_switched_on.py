"""The pages say the scope check is not switched on by anything Mycelium ships (v0.323.2).

WHAT WAS WRONG. `hooks/scope-gate.sh` holds the agent's writes to the paths named in
`.claude/state/active-execution.json` and leaves at once when that file is absent. No skill, script
or hook writes the file, so in a plugin install the check has never been on. A blind reader of the
installed plugin found it (dogfood 2026-10-11). The README stopped claiming the hold in 0.322.3.
Five other pages went on describing it as working, upstream's own state README named a skill as
the file's writer, and two of the helper's refusals told the reader to run that skill "to recreate"
a file it never writes.

WHAT HOLDS NOW. The mechanism that would switch it on is tested in a scratch copy and not released.
Until it is, each page says the check is off unless you write the file yourself, and the
maintainer's page no longer mentions it (his choice of wording, 2026-10-13).

THIS TEST HOLDS THE PAGES AND THE PLUGIN TOGETHER, BOTH WAYS. While nothing shipped writes the
file, the pages must say so. The day something does (a new file that names it, or the field in a
skill or a schema), the last two tests here fail and say to take the admissions out in the same
release: a page that still admits a hole that has been closed is as untrue as one that hides it.
"""

from __future__ import annotations

import json
import os
import site
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
GATE = PLUGIN / "hooks" / "scope-gate.sh"
STATE_REL = ".claude/state/active-execution.json"

#: page -> the words it must carry while the check is not switched on.
MUST_SAY = {
    "docs/ai-system-card.md": "The scope check is not switched on by anything Mycelium ships",
    "docs/context-surface.md": "nothing Mycelium ships writes that file",
    "PRIVACY.md": "Nothing Mycelium ships writes this file",
    "plugins/mycelium/hooks/README.md": "no skill, script or hook that Mycelium ships writes the file",
    ".claude/state/README.md": "is written by nothing Mycelium ships",
}
#: page -> words that described the check as working, or sent the reader to a skill for the file.
MUST_NOT_SAY = {
    "docs/nobody-used-it.md": "There is a scope check that holds writes",
    "docs/ai-system-card.md": "framework-guard / scope-gate / reflexion hooks catch it",
    "plugins/mycelium/hooks/README.md": "This is the common case before L4 delivery work begins.",
    ".claude/state/README.md": "| `/diamond-progress` (L4 only) | `scope-gate.sh`",
    "plugins/mycelium/scripts/scope_check.py": "run /diamond-progress",
}
#: The plugin files that name the state file today. None of them writes it: the gate and its
#: helper read it, two logs read it for a label, and the rest list it as a file that switches a
#: stop off or describe the gate.
NAMES_THE_FILE = {
    "engine/agent-operating-contract.md",
    "hooks/README.md",
    "hooks/change-log.sh",
    "hooks/guard-state-gate.sh",
    "hooks/read-log.sh",
    "hooks/scope-gate.sh",
    "scripts/_hook_input.py",
    "scripts/scope_check.py",
}
NAMES_THE_FIELD = {"hooks/README.md", "hooks/scope-gate.sh", "scripts/scope_check.py"}
TAKE_THEM_OUT = (
    "If this now gets written by something Mycelium ships, the scope check is being switched on: "
    "take the admissions out of the pages in the same release (MUST_SAY above), put the hold back "
    "in the maintainer's page in his words, and rewrite this test for what the hold then does.")


def _project(tmp_path: Path) -> Path:
    for sub in (".claude/canvas", ".claude/state", "app/billing", "app/users"):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path


def _gate(project: Path, rel: str) -> str:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "permission_mode": "default",
               "cwd": str(project),
               "tool_input": {"file_path": str(project / rel), "content": "x = 1\n"}}
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase()}
    done = subprocess.run(["bash", str(GATE)], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, cwd=project, timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_control_with_the_file_written_by_hand_the_check_holds(tmp_path):
    """The gate works when its file exists; without this the next test would prove nothing."""
    project = _project(tmp_path)
    (project / STATE_REL).write_text(json.dumps({"diamond_id": "l4-billing",
                                                 "in_scope_paths": ["app/billing/**"]}))
    assert _gate(project, "app/billing/new.py") == ""
    assert '"permissionDecision": "deny"' in _gate(project, "app/users/new.py")


def test_in_a_project_as_setup_leaves_it_the_check_says_nothing(tmp_path):
    """What every plugin install has: no state file, so a write anywhere passes this gate."""
    assert _gate(_project(tmp_path), "app/users/new.py") == ""


@pytest.mark.parametrize("page", sorted(MUST_SAY))
def test_the_page_says_the_check_is_off_unless_you_write_the_file(page):
    assert MUST_SAY[page] in (ROOT / page).read_text(), (
        f"{page} no longer says that nothing Mycelium ships switches the scope check on. While "
        "that is true (the two tests at the end of this file), the page has to say it.")


@pytest.mark.parametrize("page", sorted(MUST_NOT_SAY))
def test_the_page_does_not_describe_the_check_as_working(page):
    assert MUST_NOT_SAY[page] not in (ROOT / page).read_text(), (
        f"{page} again carries the words that described the scope check as on, or that sent the "
        "reader to a skill for a file no skill writes.")


def _plugin_files_naming(word: str) -> set[str]:
    found = set()
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if word in text:
            found.add(path.relative_to(PLUGIN).as_posix())
    return found


def test_nothing_new_in_the_plugin_names_the_state_file():
    new = _plugin_files_naming("active-execution") - NAMES_THE_FILE
    assert not new, f"new in the plugin, naming the scope check's state file: {sorted(new)}. " + TAKE_THEM_OUT


def test_nothing_new_in_the_plugin_names_the_field():
    new = _plugin_files_naming("in_scope_paths") - NAMES_THE_FIELD
    assert not new, f"new in the plugin, naming `in_scope_paths`: {sorted(new)}. " + TAKE_THEM_OUT
