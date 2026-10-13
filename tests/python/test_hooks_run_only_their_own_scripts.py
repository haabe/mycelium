"""A hook never runs a script it found in the project (v0.322.3).

WHAT WAS WRONG. When `CLAUDE_PLUGIN_ROOT` is not set, which the installer's own notes say is the
case on Cursor and Codex, a hook that needed a helper looked for it in the PROJECT:
`$PROJECT_DIR/.claude/scripts/<name>.py`, `.claude/hooks/preflight.sh`, or the same path relative
to the working directory. That was the layout of the old install, where Mycelium's files were
copied into the project. In a plugin install it meant a repository that carried a file by the
right name had it run by the hook, at session start or on the first write. Found by the second
blind read (2026-10-12), by reading; nothing here was run on Cursor or Codex.

WHAT HOLDS NOW. A hook resolves its helpers beside itself (`_MYCELIUM_ROOT`, set in
`_hook_prelude.sh` from that file's own location). In a plugin install that is the plugin. In an
old install it is still the project's `.claude/`, because there the hooks themselves live in the
project, so nothing changes for it.

The canary tests plant a script in a project, run the real hook with no plugin root, and check the
script did not run. Each has a control showing the hook still did its own job by its own helper.
"""

from __future__ import annotations

import json
import os
import re
import site
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"

CANARY_PY = "import pathlib, sys\npathlib.Path(sys.argv[0]).with_suffix('.ran').write_text('ran')\n"
CANARY_SH = '#!/usr/bin/env bash\necho ran > "${BASH_SOURCE[0]}.ran"\n'
#: A path in the project that a hook would execute or source. Comments are not code.
PROJECT_SCRIPT = re.compile(r"""(?:\$\{?PROJECT_DIR\}?/|["'=\s])\.claude/(?:scripts|hooks)/[\w.-]+\.(?:py|sh)""")


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".claude" / "canvas").mkdir(parents=True)
    (project / ".claude" / "diamonds").mkdir()
    (project / ".claude" / "state").mkdir()
    return project


def _run(project: Path, hook: str, payload: dict, *args: str) -> subprocess.CompletedProcess:
    """The hook as Cursor or Codex would start it: its real path, and no CLAUDE_PLUGIN_ROOT."""
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "PYTHONUSERBASE": site.getuserbase()}
    return subprocess.run(["bash", str(HOOKS / hook), *args], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, cwd=project, timeout=180, check=False)


def _plant(project: Path, rel: str) -> Path:
    target = project / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CANARY_SH if rel.endswith(".sh") else CANARY_PY)
    return target


def _ran(planted: Path) -> bool:
    return any(p.exists() for p in (planted.with_suffix(".ran"), Path(str(planted) + ".ran")))


# ---------------------------------------------------------------- no hook names a project script


def test_no_hook_resolves_a_script_from_the_project():
    """RED BEFORE 0.322.3: 41 such lines in 12 files (counted by this test on the 0.322.2 tree)."""
    found = []
    for f in [*sorted(HOOKS.glob("*.sh")), PLUGIN / "scripts" / "_hook_input_read.sh",
              PLUGIN / "scripts" / "_hook_prelude.sh", PLUGIN / "scripts" / "_hook_fire_log.sh"]:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split("#", 1)[0] if line.lstrip().startswith("#") else line
            # A refusal's own wording may name the old place; only a path the shell would use counts.
            if "permissionDecisionReason" in code:
                continue
            if PROJECT_SCRIPT.search(code):
                found.append(f"{f.name}:{n}: {line.strip()[:90]}")
    assert found == [], "\n".join(found)


def test_the_prelude_says_where_myceliums_own_files_are():
    script = f'. "{PLUGIN}/scripts/_hook_prelude.sh"; printf %s "$_MYCELIUM_ROOT"'
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], "MYCELIUM_PRELUDE_ANY_PROJECT": "1"},
                          check=False)
    assert Path(done.stdout).resolve() == PLUGIN.resolve()


# ---------------------------------------------------------------- canaries


def test_the_gate_does_not_run_a_preflight_script_the_project_carries(tmp_path):
    """RED BEFORE 0.322.3: with no preflight stamp the gate ran `.claude/hooks/preflight.sh` from
    the project."""
    project = _project(tmp_path)
    planted = _plant(project, ".claude/hooks/preflight.sh")
    _run(project, "gate.sh", {"tool_name": "Write", "permission_mode": "default",
                              "tool_input": {"file_path": "src/app.py", "content": "x = 1\n"}})
    assert not _ran(planted), "the gate ran a script from the project's own folder"


@pytest.mark.parametrize(("hook", "helper", "payload"), [
    ("shell-safety-guard.sh", "shell_safety_guard.py",
     {"tool_name": "Bash", "tool_input": {"command": "grep x f | tail -1; echo $?"}}),
    ("absence-claim-guard.sh", "absence_claim_guard.py",
     {"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "none exist\n"}}),
    ("read-before-research-guard.sh", "read_before_research_guard.py",
     {"tool_name": "WebSearch", "tool_input": {"query": "acme widgets"}}),
    ("correction-attribution-guard.sh", "correction_attribution_guard.py",
     {"tool_name": "Write", "tool_input": {"file_path": ".claude/memory/corrections.md",
                                           "content": "### a\n"}}),
    ("discovery-trigger-guard.sh", "discovery_trigger_guard.py",
     {"prompt": "let us build a new feature"}),
    ("framework-guard.sh", "framework_guard.py",
     {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x = 1\n"}}),
    ("scope-gate.sh", "scope_check.py",
     {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x = 1\n"}}),
    ("autonomous-evidence-guard.sh", "autonomous_evidence_guard.py",
     {"tool_name": "Write", "tool_input": {"file_path": ".claude/canvas/purpose.yml",
                                           "content": "why: x\n"}}),
])
def test_a_hook_does_not_run_a_helper_the_project_carries(tmp_path, hook, helper, payload):
    """A GUARD, NOT A RED TEST. On 0.322.2 all eight of these passed: each hook found its own
    helper before it reached the project path, so the planted file did not run. The fallback
    line was there all the same and is gone; this keeps it gone. The two tests either side of
    this one are the ones that failed on 0.322.2."""
    project = _project(tmp_path)
    planted = _plant(project, f".claude/scripts/{helper}")
    # What switches two of these hooks on at all; harmless for the rest. Since 0.324.0 the
    # scope hold reads the delivery cycle's record, and that read is where its helper imports
    # scale_locks, settings_switches and PyYAML, so the record names a folder here.
    (project / ".claude" / "diamonds" / "active.yml").write_text(
        "autonomous: true\nactive_diamonds:\n- id: l4-x\n  scale: L4\n  decisions:\n"
        "  - {decision: set_target, on: '2026-10-01'}\n"
        "  - {decision: start_experiment, on: '2026-10-02'}\n"
        "  - {decision: commit_to_build, on: '2026-10-02'}\n"
        "  in_scope_paths: [lib/]\n")
    _run(project, hook, {**payload, "cwd": str(project), "session_id": "s1"})
    assert not _ran(planted), f"{hook} ran {helper} from the project's own folder"


def test_session_start_does_not_run_a_check_the_project_carries(tmp_path):
    """RED BEFORE 0.322.3: two dozen of its checks had the fallback."""
    project = _project(tmp_path)
    planted = [_plant(project, f".claude/scripts/{name}") for name in
               ("check_source_authenticity.py", "check_source_class_fidelity.py",
                "validate_canvas.py", "advisory_ledger.py", "next_item.py")]
    _run(project, "session-start.sh", {"hook_event_name": "SessionStart", "source": "startup",
                                       "session_id": "s1", "cwd": str(project)})
    assert [p.name for p in planted if _ran(p)] == []


# ---------------------------------------------------------------- the hooks still do their job


def test_control_without_a_plugin_root_a_hook_still_finds_its_own_helper(tmp_path):
    """The other half of the change: on a runtime that sets no plugin root the advisory hooks used
    to find nothing and say nothing. They now find the helper beside themselves."""
    project = _project(tmp_path)
    done = _run(project, "shell-safety-guard.sh", {
        "tool_name": "Bash", "cwd": str(project), "session_id": "s1",
        "tool_input": {"command": "grep x f | tail -1; echo $?"}})
    assert "SHELL-SAFETY" in done.stdout


def test_control_an_old_install_still_runs_its_own_copies(tmp_path):
    """Where the hooks themselves were copied into the project, "beside the hook" IS the project's
    `.claude/`, so that layout keeps working."""
    project = _project(tmp_path)
    for sub in ("hooks", "scripts"):
        dest = project / ".claude" / sub
        dest.mkdir(exist_ok=True)
        for f in (PLUGIN / sub).iterdir():
            if f.is_file():
                (dest / f.name).write_bytes(f.read_bytes())
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "PYTHONUSERBASE": site.getuserbase()}
    done = subprocess.run(["bash", str(project / ".claude" / "hooks" / "shell-safety-guard.sh")],
                          input=json.dumps({"tool_name": "Bash", "cwd": str(project),
                                            "tool_input": {"command": "grep x f | tail -1; echo $?"}}),
                          text=True, capture_output=True, env=env, cwd=project, timeout=60,
                          check=False)
    assert "SHELL-SAFETY" in done.stdout
