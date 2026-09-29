"""Mycelium on Codex CLI as a plugin (v0.286.0).

Measured 2026-09-29 on Codex CLI 0.158.0, installed from the haabe-mycelium marketplace: all 63
skills loaded; with the hooks untrusted, no hook ran and a source file was written with nothing
said; with them trusted, the session-start contract held. Codex had no manifest of its own to read,
so it fell back to hooks/hooks.json and would drop that file's four `async` hooks, and it cannot
honour a hook's `ask`.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _hook_input as hi  # noqa: E402

_spec = importlib.util.spec_from_file_location("codex_plugin_hooks", SCRIPTS / "codex_plugin_hooks.py")
cph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cph)

DERIVED = PLUGIN / "hooks" / "hooks.codex-plugin.json"
ENTRY_SKILLS = ("start", "setup", "adopt", "interview", "diamond-assess")


def _commands(doc: dict) -> list[str]:
    return [h["command"] for groups in doc["hooks"].values() for g in groups for h in g["hooks"]]


# ------------------------------------------------------------------ the manifest Codex reads


def test_codex_reads_its_own_manifest_and_it_names_the_derived_hooks():
    m = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    c = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert (PLUGIN / m["hooks"]).resolve() == DERIVED.resolve()
    assert m["version"] == c["version"] and m["name"] == c["name"]


def test_the_derived_hooks_are_current_with_their_source():
    assert cph.main(["--check"]) == 0


def test_control_a_stale_derived_file_is_caught(tmp_path):
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "hooks.codex.json").write_text((PLUGIN / "hooks" / "hooks.codex.json").read_text())
    (tmp_path / "hooks" / "hooks.codex-plugin.json").write_text(DERIVED.read_text() + " ")
    assert cph.main(["--root", str(tmp_path), "--check"]) == 1


def test_the_derived_hooks_hold_nothing_codex_drops_or_cannot_resolve():
    doc = json.loads(DERIVED.read_text())
    hooks = [h for groups in doc["hooks"].values() for g in groups for h in g["hooks"]]
    assert not [h for h in hooks if h.get("async")], "Codex drops async hooks at load"
    assert "PostToolUseFailure" not in doc["hooks"], "not a Codex event"
    assert cph.PLACEHOLDER not in DERIVED.read_text()
    for cmd in _commands(doc):
        assert cmd.startswith("MYCELIUM_RUNTIME=codex bash ${CLAUDE_PLUGIN_ROOT}/"), cmd
        script = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+\.sh)", cmd).group(1)
        assert (PLUGIN / script).is_file(), script


def test_control_the_claude_code_file_still_carries_what_codex_would_drop():
    """Why the Codex manifest is needed: without it Codex falls back to this file."""
    doc = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    assert [h for groups in doc["hooks"].values() for g in groups for h in g["hooks"] if h.get("async")]


# ------------------------------------------------------------------ no `ask` on Codex


@pytest.fixture
def decide(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    (tmp_path / ".claude" / "state").mkdir(parents=True)

    def run(mode):
        capsys.readouterr()
        try:
            hi.guard_state_check("t", "Write", {"file_path": ".claude/state/scale-lock-ack",
                                                "content": "x"}, str(tmp_path), mode)
        except SystemExit:
            pass
        out = capsys.readouterr().out.strip()
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"
    return run


def test_on_codex_an_off_switch_write_is_refused_where_claude_code_would_ask(decide, monkeypatch):
    monkeypatch.setenv("MYCELIUM_RUNTIME", "codex")
    assert decide("default") == "deny", "Codex turns an ask into an allow"


def test_control_on_claude_code_the_same_write_asks(decide, monkeypatch):
    monkeypatch.delenv("MYCELIUM_RUNTIME", raising=False)
    assert decide("default") == "ask"


# ------------------------------------------------------------------ hooks-alive


def _preflight(project: Path) -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    subprocess.run(["bash", str(PLUGIN / "hooks" / "preflight.sh")], input="{}", text=True,
                   capture_output=True, env=env, timeout=60, check=False)


def test_a_prompt_refreshes_the_marker_the_entry_skills_read(tmp_path):
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    _preflight(tmp_path)
    assert (tmp_path / ".claude" / "state" / "hooks-alive").is_file()


def test_control_a_prompt_outside_a_mycelium_project_creates_nothing(tmp_path):
    _preflight(tmp_path)
    assert not (tmp_path / ".claude").exists()


def test_session_start_writes_the_marker_before_any_check_can_time_out():
    lines = (PLUGIN / "hooks" / "session-start.sh").read_text().splitlines()
    first = next(i for i, line in enumerate(lines) if "hooks-alive" in line and "touch" in line)
    assert first < 20, "written first, so a hook cancelled later still counts as having run"


def test_every_entry_skill_checks_the_marker_and_says_what_to_do():
    for s in ENTRY_SKILLS:
        text = (PLUGIN / "skills" / s / "SKILL.md").read_text()
        assert "find .claude/state/hooks-alive -mmin -60" in text, s
        assert "open `/hooks`" in text, s


def test_start_checks_it_inside_its_one_first_command():
    """start's Step 2 allows exactly one command before anything else; a separate check would
    contradict its own hard gate."""
    text = (PLUGIN / "skills" / "start" / "SKILL.md").read_text()
    step2 = text[text.index("## Step 2"):text.index("## Step 3")]
    block = re.search(r"```bash\n(.+?)\n```", step2, re.DOTALL).group(1)
    assert "\n" not in block and "hooks-alive" in block and "${CLAUDE_PROJECT_DIR:-.}" in block
    assert "hooks-alive" not in text[:text.index("## Step 2")], "no second check before it"
