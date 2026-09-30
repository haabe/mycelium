"""E2E run 10, replayed against the gates on every release (v0.289.0, the phase migration's stage 0a).

Run 10 (2026-09-24, DL-1361 in the dogfood decision log) built an SMS swap app holding staff phone
numbers and private link tokens, put it live at one site and onboarded a second, under an L3 still in
define with every gate pending. The fixture is its recorded diamond state, verbatim.

The phase migration's frozen bet (dogfood `evals/assumption-tests/2026-09-30-phase-migration-keeps-safety.md`)
is that re-keyed safety stops everything the phase-keyed rules stop, and closes the holes found open
on 2026-09-30. Each step here is one of those checks. A hole still open is a STRICT expected failure:
the day a stage closes it, the test fails until the marker is removed, so this list cannot go stale.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "plugins" / "mycelium" / "hooks"
FIXTURE = ROOT / "tests" / "fixtures" / "run10"
OPEN_UNTIL_0B = "open on 2026-09-30; stage 0b of the phase migration closes it"
RELEASE = "fly " + "deploy"  # split so this source does not trip the release gate's own prose match


@pytest.fixture
def run10(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def _hook(name: str, project: Path, payload: dict, *, no_pyyaml: Path | None = None) -> int:
    return _hook_err(name, project, payload, no_pyyaml=no_pyyaml)[0]


def _hook_err(name: str, project: Path, payload: dict, *, no_pyyaml: Path | None = None,
              extra: dict | None = None) -> tuple[int, str]:
    # The user's own environment (their python3 is what the hooks run), minus Mycelium settings.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MYCELIUM_", "CLAUDE_"))}
    env.update({"CLAUDE_PROJECT_DIR": str(project), "MYCELIUM_TODAY": "2026-09-25", "PYTHONPATH": ""})
    if no_pyyaml is not None:
        # A yaml.py that raises ImportError shadows PyYAML: the same path as "not installed".
        (no_pyyaml / "yaml.py").write_text('raise ImportError("simulated: PyYAML not installed")\n')
        env["PYTHONPATH"] = str(no_pyyaml)
    env.update(extra or {})
    res = subprocess.run(["bash", str(HOOKS / name)], input=json.dumps(payload), text=True,
                         capture_output=True, env=env, timeout=60, check=False)
    return res.returncode, res.stderr


def _write(project: Path, rel: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": str(project / rel), "content": "x = 1\n"}}


def _edit(project: Path, rel: str, old: str, new: str) -> dict:
    return {"tool_name": "Edit",
            "tool_input": {"file_path": str(project / rel), "old_string": old, "new_string": new}}


def _shell(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# --- Step 1: building the product ----------------------------------------------------------------

def test_building_a_new_product_file_is_stopped(run10):
    assert _hook("discovery-gate.sh", run10, _write(run10, "app/cadence/web.py")) == 2


@pytest.mark.xfail(strict=True, reason=f"Edit and MultiEdit exit the build gate early; {OPEN_UNTIL_0B}")
def test_editing_product_code_without_a_decision_to_build_is_stopped(run10):
    edit = _edit(run10, "app/cadence/sms.py", "raise NotImplementedError", "return None")
    assert _hook("discovery-gate.sh", run10, edit) == 2


# --- Step 2: releasing it to the first site ------------------------------------------------------

def test_a_remote_release_is_stopped(run10):
    assert _hook("exposure-gate.sh", run10, _shell(RELEASE)) == 2
    assert _hook("exposure-gate.sh", run10,
                 _shell("ssh app@host 'cd app && git pull && systemctl restart cadence'")) == 2


def test_a_tunnel_to_the_running_app_is_stopped(run10):
    assert _hook("exposure-gate.sh", run10, _shell("ngrok http 8000")) == 2


def test_a_push_to_a_host_that_goes_live_on_push_is_stopped(run10):
    (run10 / "vercel.json").write_text("{}\n")
    assert _hook("exposure-gate.sh", run10, _shell("git push origin main")) == 2


def test_a_remote_release_is_stopped_even_without_pyyaml(run10, tmp_path_factory):
    """macOS's own python3 has no PyYAML, and neither the README nor /setup asked for it. On
    2026-09-30 the release gate failed open here (exit 0, with a stdout line a PreToolUse hook does
    not show the agent). Closed in 0.290.0: it refuses, and says how to fix it."""
    shim = tmp_path_factory.mktemp("no-pyyaml")
    assert _hook("exposure-gate.sh", run10, _shell(RELEASE), no_pyyaml=shim) == 2


def test_the_build_gate_refuses_without_pyyaml_and_says_why(run10, tmp_path_factory):
    """0.289.0 called this a control that "already fails closed". It refused, but for a false reason:
    without PyYAML the diamonds went unread, so the project looked undiscovered ("no discovery state
    yet"). Since 0.290.0 the check says it cannot read them, and the gate refuses with the fix."""
    shim = tmp_path_factory.mktemp("no-pyyaml")
    code, err = _hook_err("discovery-gate.sh", run10, _write(run10, "app/cadence/web.py"), no_pyyaml=shim)
    assert code == 2
    assert "PyYAML is not available" in err and "no discovery state" not in err


def test_the_release_gate_uses_myceliums_own_environment_when_path_python_lacks_pyyaml(
        run10, tmp_path_factory):
    """/mycelium:setup can create ${CLAUDE_PLUGIN_DATA}/pyenv; the gates then check with it. The
    stand-in environment is a wrapper that runs this python3 without the shim that hides PyYAML."""
    shim = tmp_path_factory.mktemp("no-pyyaml")
    data = tmp_path_factory.mktemp("plugin-data")
    (data / "pyenv" / "bin").mkdir(parents=True)
    own = data / "pyenv" / "bin" / "python"
    own.write_text(f'#!/bin/sh\nPYTHONPATH= exec "{sys.executable}" "$@"\n')
    own.chmod(0o755)
    code, err = _hook_err("exposure-gate.sh", run10, _shell(RELEASE), no_pyyaml=shim,
                          extra={"CLAUDE_PLUGIN_DATA": str(data)})
    assert code == 2 and "PyYAML is not available" not in err  # refused on the locks, not on PyYAML
    assert "no delivery" in err or "missing" in err


def test_control_an_ordinary_push_with_no_live_host_is_not_stopped(run10):
    """A plain push to a remote with no host that goes live on it is not an exposure."""
    assert _hook("exposure-gate.sh", run10, _shell("git push origin main")) == 0


# --- Step 3: widening to the second site ---------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=f"widening is only compared for an L3 already in deliver; {OPEN_UNTIL_0B}")
def test_widening_the_audience_while_gates_are_pending_is_stopped(run10):
    anchor = '    notes: "2026-09-24: build started'
    widened = ('    learning_delivery:\n      audience: "Harbour staff, and the second site onboarding now"\n'
               '      until: "2026-11-01"\n      means: "the app, by text link"\n' + anchor)
    edit = _edit(run10, ".claude/diamonds/active.yml", anchor, widened)
    assert _hook("scale-lock-gate.sh", run10, edit) == 2
