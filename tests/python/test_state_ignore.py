""".claude/state never exists without its ignore file (v0.318.0).

Anthropic's plugin directory review of v0.317.4: the hooks write logs there (files read and
changed, failed commands, search terms) in any project the plugin runs in, and only
/mycelium:setup wrote the ignore file, so in a project where setup never ran the logs could be
committed by accident. Verified 2026-10-10: one Read in a bare git repo left
.claude/state/read-log.jsonl and no ignore file.

The decisive test runs EVERY hook registered in hooks.json, each in its own empty project, and
checks that a state folder the hook leaves behind has its ignore file. It does not depend on
knowing which hooks write where, so a new hook or a new writer is covered by construction.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
_spec = importlib.util.spec_from_file_location("_state_dir", SCRIPTS / "_state_dir.py")
sd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sd)
TEMPLATE = (SCRIPTS / "state-gitignore.txt").read_text()


# ---------------------------------------------------------------- the Python helper


def test_ensure_creates_the_folder_with_the_template(tmp_path):
    state = sd.ensure(tmp_path / ".claude" / "state")
    assert (state / ".gitignore").read_text() == TEMPLATE


def test_an_existing_ignore_file_is_never_rewritten(tmp_path):
    state = tmp_path / ".claude" / "state"
    state.mkdir(parents=True)
    (state / ".gitignore").write_text("mine\n")
    assert sd.write_ignore(state) is False
    sd.ensure(state)
    assert (state / ".gitignore").read_text() == "mine\n"


def test_write_ignore_does_not_create_the_folder(tmp_path):
    assert sd.write_ignore(tmp_path / ".claude" / "state") is False
    assert not (tmp_path / ".claude").exists()


def test_prepare_inside_state_writes_the_ignore_file(tmp_path):
    target = tmp_path / ".claude" / "state" / "bash-guard" / "active.yml.before"
    assert sd.prepare(target) == target
    assert (tmp_path / ".claude" / "state" / ".gitignore").read_text() == TEMPLATE
    sd.prepare_dir(tmp_path / ".claude" / "state" / "snapshots")
    assert (tmp_path / ".claude" / "state" / "snapshots").is_dir()


def test_prepare_outside_state_writes_no_ignore_file(tmp_path):
    sd.prepare(tmp_path / ".claude" / "canvas" / "x.yml")
    sd.prepare_dir(tmp_path / "state" / "not-mycelium")
    assert not list(tmp_path.rglob(".gitignore"))


def test_cli_creates_the_folder_and_prints_it(tmp_path, capsys):
    assert sd.main(["--project-dir", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / ".claude" / "state")
    assert (tmp_path / ".claude" / "state" / ".gitignore").is_file()


def test_the_template_keeps_logs_out_and_decisions_in():
    rules = [line for line in TEMPLATE.splitlines() if line and not line.startswith("#")]
    assert rules[0] == "*"
    assert {"!discovery-skip-ack", "!brownfield-ack", "!delivery-skip-ack"} <= set(rules)


# ---------------------------------------------------------------- the shell half


def _bash(project: Path, script: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    return subprocess.run(["bash", "-c", f'. "{SCRIPTS}/_state_ignore.sh"\n{script}'],
                          env=env, capture_output=True, text=True, timeout=30, check=False)


def test_on_exit_a_state_folder_without_the_file_gets_one(tmp_path):
    r = _bash(tmp_path, f'mkdir -p "{tmp_path}/.claude/state"; exit 3')
    assert r.returncode == 3, "the exit check must not change the hook's exit status"
    assert r.stdout == "", "the exit check must not write to stdout, which hooks use for JSON"
    assert (tmp_path / ".claude" / "state" / ".gitignore").read_text() == TEMPLATE


def test_on_exit_no_folder_means_nothing_is_created(tmp_path):
    _bash(tmp_path, "true")
    assert not (tmp_path / ".claude").exists()


def test_on_exit_an_existing_file_stands(tmp_path):
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    (tmp_path / ".claude" / "state" / ".gitignore").write_text("mine\n")
    _bash(tmp_path, "true")
    assert (tmp_path / ".claude" / "state" / ".gitignore").read_text() == "mine\n"


def test_every_hook_script_sources_the_exit_check():
    missing = [p.name for p in sorted((PLUGIN / "hooks").glob("*.sh"))
               if "/../scripts/_state_ignore.sh" not in p.read_text()]
    assert missing == []


def test_a_hook_with_its_own_exit_trap_keeps_the_check():
    text = (PLUGIN / "hooks" / "install-runtime-hooks.sh").read_text()
    traps = re.findall(r"^\s*trap (.+) EXIT", text, re.MULTILINE)
    assert traps and all("mycelium_state_ignore" in t for t in traps), traps


def test_every_script_creates_folders_through_the_helper():
    """A raw mkdir in a script that writes under .claude/state would skip the ignore file when the
    script runs outside a hook (a skill running it directly)."""
    allowed = {"_state_dir.py", "check_empty_input_honesty.py"}  # the helper; throwaway fixtures
    raw = [f"{p.name}:{n}" for p in sorted(SCRIPTS.glob("*.py")) if p.name not in allowed
           for n, line in enumerate(p.read_text().splitlines(), 1) if ".mkdir(" in line]
    assert raw == []


# ---------------------------------------------------------------- every registered hook, for real

_PAYLOADS = {
    "PreToolUse": {"tool_name": "Read", "tool_input": {"file_path": "README.md"}},
    "PostToolUse": {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_response": {}},
    "PostToolUseFailure": {"tool_name": "Bash", "tool_input": {"command": "false"},
                           "tool_response": {"exit_code": 1, "stderr": ""}},
    "UserPromptSubmit": {"prompt": "what next?"},
    "Stop": {"stop_hook_active": False},
    "SessionStart": {"source": "startup"},
}


def _registered() -> list[tuple[str, str]]:
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    out = []
    for event, groups in hooks.items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command" and event in _PAYLOADS:
                    out.append((event, hook["command"]))
    return out


REGISTERED = _registered()


def _hook_id(event: str, command: str) -> str:
    return f"{event}:{re.search(r'hooks/([A-Za-z0-9_.-]+)', command).group(1)}"


def test_the_payload_table_covers_every_registered_event():
    events = set(json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"])
    assert events <= set(_PAYLOADS), events - set(_PAYLOADS)


@pytest.mark.parametrize(("event", "command"), REGISTERED,
                         ids=[_hook_id(e, c) for e, c in REGISTERED])
def test_a_state_folder_a_hook_leaves_has_its_ignore_file(tmp_path, event, command):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    (project / "README.md").write_text("hello\n")
    payload = dict(_PAYLOADS[event], session_id="t", cwd=str(project), hook_event_name=event)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project), CLAUDE_PLUGIN_ROOT=str(PLUGIN),
               MYCELIUM_CI_SIGNAL="off")
    subprocess.run(["bash", "-c", command], input=json.dumps(payload), cwd=project, env=env,
                   capture_output=True, text=True, timeout=120, check=False)
    state = project / ".claude" / "state"
    if state.exists():
        assert (state / ".gitignore").is_file(), f"{command} left .claude/state without its ignore file"
