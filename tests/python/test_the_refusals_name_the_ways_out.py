"""The refusals name the ways out, cheapest first, and the warning says nothing untrue (v0.336.0).

WHAT WAS WRONG (harms check with the plugin as the product, 2026-10-11, Happier-negative). The
build refusal named the full diamond chain and a five-field acknowledgement, and not the cheapest
exit, a prototype folder. The release refusal did not say that the person can run the deploy
themselves, so a builder read it as a lock on her own deploy. And the shell-safety warning told
every project "Each of these traps has produced a wrong answer in this project before - see
corrections.md", which is true of the project Mycelium is built in and of no fresh one.

Not changed here: whether there is a project-level pause. That is the maintainer's to decide.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder

DEFINED = [{"decision": "set_target", "on": "2026-09-20"}]
NOT_READY = {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "decisions": DEFINED}
RELEASED = [{"decision": d, "on": "2026-09-20"}
            for d in ("set_target", "start_experiment", "commit_to_build")] + [
                {"decision": "release", "on": "2026-09-22"}]


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _project(tmp_path: Path, diamonds: list[dict]) -> str:
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds)


# ---------------------------------------------------------------- the build refusal

def _build_refusal(tmp_path: Path) -> str:
    p = Path(_project(tmp_path, [NOT_READY]))
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env.update(CLAUDE_PROJECT_DIR=str(p), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": str(p / "app" / "main.py"), "content": "x = 1\n"}}
    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "discovery-gate.sh")], env=env,
                          input=json.dumps(payload), text=True, capture_output=True, timeout=60,
                          check=False)
    assert done.returncode == 2, done.stderr
    return done.stderr


def test_the_build_refusal_names_the_prototype_folder_first(tmp_path):
    """RED BEFORE 0.336.0: `prototype_paths` was not in the refusal at all."""
    err = _build_refusal(tmp_path)
    assert "`prototype_paths`" in err and ".claude/diamonds/active.yml" in err
    proto, chain, ack = (err.index("`prototype_paths`"), err.index("Open the delivery cycle"),
                         err.index(".claude/state/delivery-skip-ack"))
    assert proto < chain < ack, "the exits are not listed cheapest first"
    assert "releasing anything under" in err      # and it says what the folder does not free


# ---------------------------------------------------------------- the release refusal

def _l3(*records: dict) -> dict:
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(RELEASED),
            "exposures": [dict(r) for r in records]}


def _release(project: str, monkeypatch, capsys, mode: str = "default"):
    payload = {**tsl._bash("fly deploy"), "permission_mode": mode}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    code = sl.main(["--project-dir", project, "--exposure-hook"])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_release_refusal_says_the_person_may_run_it_themselves(tmp_path, monkeypatch, capsys):
    """RED BEFORE 0.336.0."""
    bare = dict(tsl.RECORD, gates={})               # no gate passed for this exposure: refused
    code, _, err = _release(_project(tmp_path, [_l3(bare)]), monkeypatch, capsys)
    assert code == 2
    assert "The person can run this command themselves" in err
    assert "do not recommend it" in err             # told as their choice, not as advice


def test_where_nobody_can_be_asked_the_refusal_says_it_too(tmp_path, monkeypatch, capsys):
    """Two current records ask the person; with nobody to ask that is a refusal. RED BEFORE."""
    second = dict(tsl.RECORD, audience="A second cohort of twelve, opted in by email")
    code, _, err = _release(_project(tmp_path, [_l3(tsl.RECORD, second)]), monkeypatch, capsys,
                            mode="bypassPermissions")
    assert code == 2 and "Nobody can be asked here" in err
    assert "The person can run this command themselves" in err


def test_control_an_allowed_release_says_nothing_about_it(tmp_path, monkeypatch, capsys):
    code, out, err = _release(_project(tmp_path, [_l3(tsl.RECORD)]), monkeypatch, capsys)
    assert code == 0 and "run this command themselves" not in out + err


# ---------------------------------------------------------------- the shell-safety footer

def test_the_shell_safety_footer_claims_nothing_about_this_project():
    """RED BEFORE 0.336.0: the footer printed in every project, fresh ones included."""
    payload = {"tool_name": "Bash", "tool_input": {"command": "pytest | tail -3; echo $?"}}
    done = subprocess.run([sys.executable, str(SCRIPTS / "shell_safety_guard.py")],
                          input=json.dumps(payload), text=True, capture_output=True, timeout=60,
                          check=False)
    said = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SHELL-SAFETY WARNING" in said
    assert "in this project before" not in said and "corrections.md" not in said
    assert "warnings, not blocks" in said
