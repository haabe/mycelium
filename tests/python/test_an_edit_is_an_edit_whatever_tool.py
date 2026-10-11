"""The build gate judges an edit of product code whatever tool makes it (v0.321.1).

WHAT WAS WRONG. Since 0.291.0 editing product code counts as building once discovery is engaged,
and README.md and docs/get-started.md say so: "new files and edits alike". The hook set its
`EDITING` flag for Edit, MultiEdit and the MCP edit tool only, and skipped every other write to an
existing, non-empty file. A whole-file Write over a product file, a notebook edit and a shell edit
all changed product code with no gate firing, in the project where the same change made with the
Edit tool was refused. Found by a blind read of 0.321.0.

The fixture is E2E run 10's recorded state (`tests/fixtures/run10`): an L3 still in define with
every gate pending, and product code under `app/`. `test_run10_replay.py` holds the Edit-tool
cases; these are the same edit made the other ways.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "discovery-gate.sh"
FIXTURE = ROOT / "tests" / "fixtures" / "run10"
PRODUCT = "app/cadence/sms.py"


@pytest.fixture
def run10(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    assert (tmp_path / PRODUCT).stat().st_size > 0, "the fixture's product file must not be empty"
    return tmp_path


def _gate(project: Path, payload: dict) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MYCELIUM_", "CLAUDE_"))}
    env.update({"CLAUDE_PROJECT_DIR": str(project), "MYCELIUM_TODAY": "2026-09-25",
                "PYTHONPATH": ""})
    done = subprocess.run(["bash", str(HOOK)], input=json.dumps({**payload, "cwd": str(project)}),
                          text=True, capture_output=True, env=env, timeout=60, check=False)
    return done.returncode, done.stderr


def _write(project: Path, rel: str) -> dict:
    return {"tool_name": "Write",
            "tool_input": {"file_path": str(project / rel), "content": "x = 2\n"}}


def _shell(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ---------------------------------------------------------------- the same edit, other tools

def test_control_the_edit_tool_is_stopped_as_before(run10):
    """The case 0.291.0 closed. If this passes untouched, nothing below shows anything."""
    edit = {"tool_name": "Edit", "tool_input": {
        "file_path": str(run10 / PRODUCT), "old_string": "raise NotImplementedError",
        "new_string": "return None"}}
    assert _gate(run10, edit)[0] == 2


def test_a_whole_file_write_over_product_code_is_stopped(run10):
    """RED BEFORE 0.321.1: exit 0. Overwriting the file is the largest edit there is."""
    code, err = _gate(run10, _write(run10, PRODUCT))
    assert code == 2
    assert "change product code" in err and "sms.py" in err


def test_a_notebook_edit_of_an_existing_notebook_is_stopped(run10):
    """RED BEFORE 0.321.1."""
    nb = run10 / "app" / "analysis.ipynb"
    nb.write_text('{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}\n')
    edit = {"tool_name": "NotebookEdit",
            "tool_input": {"notebook_path": str(nb), "new_source": "x = 2", "cell_id": "c1"}}
    assert _gate(run10, edit)[0] == 2


@pytest.mark.parametrize("command", [
    f"sed -i '' 's/raise NotImplementedError/return None/' {PRODUCT}",
    f"echo 'x = 2' >> {PRODUCT}",
    f"echo 'x = 2' > {PRODUCT}",
    f"cp /tmp/other.py {PRODUCT}",
    f"printf 'x = 2\\n' | tee {PRODUCT}",
])
def test_a_shell_edit_the_hook_can_read_is_stopped(run10, command):
    """RED BEFORE 0.321.1: each exited 0."""
    code, err = _gate(run10, _shell(command))
    assert code == 2, command
    assert "change product code" in err


def test_a_shell_command_that_also_writes_an_ungated_new_file_is_still_stopped(run10):
    """A new note beside the edit must not carry the edit through: the note is not gated, so the
    command is judged again as an edit. RED BEFORE 0.321.1."""
    command = f"echo 'todo' > NOTES.md; sed -i '' 's/a/b/' {PRODUCT}"
    assert _gate(run10, _shell(command))[0] == 2


# ---------------------------------------------------------------- what must not change

def test_control_where_discovery_has_not_started_such_a_write_is_untouched(tmp_path):
    """The brownfield gate's case, exactly as for the Edit tool: no new refusal in a project with
    no purpose and no diamonds."""
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: []\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    assert _gate(tmp_path, _write(tmp_path, "app.py"))[0] == 0
    assert _gate(tmp_path, _shell("echo 'x = 2' >> app.py"))[0] == 0


def test_control_a_declared_prototype_stays_free(run10):
    active = run10 / ".claude/diamonds/active.yml"
    declared = "dogfood: false\nprototype_paths: [app/]\n"
    active.write_text(active.read_text().replace("dogfood: false\n", declared))
    assert _gate(run10, _write(run10, PRODUCT))[0] == 0
    assert _gate(run10, _shell(f"echo 'x = 2' >> {PRODUCT}"))[0] == 0


@pytest.mark.parametrize("command", [
    f"cat {PRODUCT}",
    f"grep -ln NotImplementedError {PRODUCT}",
    f"wc -l {PRODUCT} > /dev/null",
    "echo 'a note' >> README.md",
    "python3 -m pytest -q",
    "git status",
])
def test_control_reading_code_and_writing_prose_are_untouched(run10, command):
    (run10 / "README.md").write_text("# notes\n")
    assert _gate(run10, _shell(command))[0] == 0, command


def test_control_overwriting_prose_is_untouched(run10):
    (run10 / "README.md").write_text("# notes\n")
    assert _gate(run10, _write(run10, "README.md"))[0] == 0


def test_control_a_new_product_file_is_still_refused_as_a_new_file(run10):
    """The new-file path is unchanged, wording included."""
    code, err = _gate(run10, _write(run10, "app/cadence/web.py"))
    assert code == 2
    assert "create a new source file" in err
