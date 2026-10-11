"""A refusal that cannot be printed is still a refusal (v0.322.1).

`hi_deny` and `hi_ask` (scripts/_hook_input_read.sh) print a gate's decision as JSON through
python3 and leave with status 0. When python3 could not run, nothing was printed and the status
was still 0, which Claude Code reads as an allow. Found 2026-10-11 by running every gate with a
python3 that exits 127: gate.sh, discovery-gate.sh and brownfield-gate.sh each exited 0 with
nothing on stdout, at the point where they had decided to refuse. The call was refused anyway,
only because another gate happened to leave with python's status.

Now the reason goes to stderr and the status is 2, the block form that needs no JSON.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pretooluse_on_failure as pf  # the hook runner and the project builder

GATES = ("gate.sh", "discovery-gate.sh", "brownfield-gate.sh")
BLOCKED = 2  # the exit status Claude Code reads as "block this call"


def _no_python(tmp_path: Path) -> str:
    """A PATH whose python3 exits 127, as on a machine where it is missing or broken."""
    fake = tmp_path / "fakebin"
    fake.mkdir(exist_ok=True)
    (fake / "python3").write_text("#!/bin/sh\nexit 127\n")
    (fake / "python3").chmod(0o755)
    return f"{fake}:/usr/bin:/bin"


@pytest.mark.parametrize("script", GATES)
def test_with_no_python3_the_gate_refuses_and_says_why_on_stderr(tmp_path, script):
    """RED BEFORE 0.322.1: exit 0, nothing on stdout, nothing on stderr."""
    project = pf._mycelium_project(tmp_path)
    done = pf._run(script, project, pf._write("print('hi')\n", "app/main.py"),
                   PATH=_no_python(tmp_path))
    assert done.returncode == BLOCKED
    assert done.stdout == ""
    assert "refused" in done.stderr and "_hook_input.py exited 127" in done.stderr


@pytest.mark.parametrize("script", GATES)
def test_control_with_a_working_python3_the_refusal_is_json_and_status_0(tmp_path, script):
    """GREEN BEFORE 0.322.1 TOO. A call whose fields are not the documented shape is refused
    through `hi_deny`; with python3 working that is a JSON deny and exit 0, as it was."""
    project = pf._mycelium_project(tmp_path)
    done = pf._run(script, project, pf.CALLS["not a tool call"])
    assert done.returncode == 0 and done.stderr == ""
    said = json.loads(done.stdout)["hookSpecificOutput"]
    assert said["permissionDecision"] == "deny"
    assert "not the documented shape" in said["permissionDecisionReason"]


def _call(function: str, path: str | None, tmp_path: Path) -> subprocess.CompletedProcess:
    """Source the library and call one of its two functions, as a gate does."""
    lib = pf.SCRIPTS / "_hook_input_read.sh"
    env = {"PATH": path or str(Path(sys.executable).parent) + ":/usr/bin:/bin",
           "CLAUDE_PROJECT_DIR": str(tmp_path), "PROJECT_DIR": str(tmp_path)}
    return subprocess.run(["bash", "-c", f'. "{lib}"; {function} "the reason"; echo NOT-REACHED'],
                          capture_output=True, text=True, env=env, check=False)


@pytest.mark.parametrize(("function", "decision"), [("hi_deny", "deny"), ("hi_ask", "ask")])
def test_control_each_function_prints_its_decision_when_python3_works(tmp_path, function, decision):
    """GREEN BEFORE 0.322.1 TOO."""
    done = _call(function, None, tmp_path)
    said = json.loads(done.stdout)["hookSpecificOutput"]
    assert (done.returncode, said["permissionDecision"]) == (0, decision)
    assert said["permissionDecisionReason"] == "the reason" and "NOT-REACHED" not in done.stdout


@pytest.mark.parametrize("function", ["hi_deny", "hi_ask"])
def test_each_function_refuses_on_stderr_when_python3_cannot_run(tmp_path, function):
    """RED BEFORE 0.322.1 (exit 0). A question that cannot be put to a person is a refusal."""
    done = _call(function, _no_python(tmp_path), tmp_path)
    assert (done.returncode, done.stdout) == (BLOCKED, "")
    assert done.stderr.startswith("the reason")
    if function == "hi_ask":
        assert "could not be put to a person" in done.stderr
