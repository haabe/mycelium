"""A hook's Python never imports a file from the project (v0.322.4).

WHAT WAS WRONG. The hooks run inline Python (`python3 -c ...`, `python3 - <<EOF`) with the project
as the current directory, and Python puts the current directory first on its import path for
both. So `import json` in a hook loaded `./json.py` when the project had one. Replayed 2026-10-12
on 0.322.3 with the plugin root set, as Claude Code runs the hooks: preflight and the gate
imported a planted `yaml.py`, the turn-end hook `json.py` too, session start `re.py` as well.
A repository could have its own code run on every prompt and every write, with nothing in its
settings to show for it. In every released version; not found by three rounds of readers, found by
listing every place a hook starts an interpreter.

NOT SHOWN, and first claimed by the author: that an honest project's own `types.py` or `json.py`
changes what a gate decides. A replay on eight gates and on the build gate's two decisions found
every decision unchanged on 0.322.3, so the test below for that case is a control that passes on
the old code too. It is kept so the new launcher is held to the same behaviour.

A second site of an older shape rode along: two hooks built an import path from
`CLAUDE_PLUGIN_ROOT` joined with `scripts`, which is the PROJECT's `scripts` folder when the
variable is unset (blind read round 3).

WHAT HOLDS NOW. `_hook_prelude.sh` exports `PYTHONSAFEPATH=1` (Python 3.11 and later) and defines
a `python3` function that hands inline code to `scripts/_safe_c.py` (every version). The decisive
test plants canary modules in a project and runs EVERY hook registered in hooks.json there. It
does not depend on knowing which hooks run Python, so a new hook is covered by construction.

Each canary re-exports the real module after leaving its mark, so a hook that did import it
carries on and the mark is the only evidence.
"""

from __future__ import annotations

import json
import os
import re
import site
import subprocess
import sys
from pathlib import Path

import _scratch_git
import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
PRELUDE = PLUGIN / "scripts" / "_hook_prelude.sh"
SAFE = PLUGIN / "scripts" / "_safe_c.py"

CANARY = """import os, sys, importlib
_here = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(_here, "{name}.ran"), "a").write("ran\\n")
_saved = list(sys.path)
sys.path[:] = [p for p in sys.path if p not in ("", ".") and os.path.abspath(p) != _here]
del sys.modules["{name}"]
_real = importlib.import_module("{name}")
sys.path[:] = _saved
sys.modules["{name}"] = _real
globals().update(_real.__dict__)
"""
#: Modules the hooks' inline Python imports, and a few an ordinary project might name a file after.
NAMES = ("json", "yaml", "re", "pathlib", "subprocess", "datetime", "hashlib", "glob", "shutil",
         "argparse", "types", "enum", "random", "string", "tempfile", "time", "fnmatch")

_PAYLOADS = {
    "PreToolUse": {"tool_name": "Write", "tool_input": {"file_path": "src/app.py",
                                                         "content": "x = 1\n"}},
    "PostToolUse": {"tool_name": "Write", "tool_input": {"file_path": "src/app.py",
                                                          "content": "x = 1\n"}, "tool_response": {}},
    "PostToolUseFailure": {"tool_name": "Bash", "tool_input": {"command": "false"},
                           "tool_response": {"exit_code": 1, "stderr": ""}},
    "UserPromptSubmit": {"prompt": "what next?"},
    "Stop": {"stop_hook_active": False},
    "SessionStart": {"source": "startup"},
}


def _registered() -> list[tuple[str, str]]:
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    return [(event, hook["command"]) for event, groups in hooks.items() for group in groups
            for hook in group.get("hooks", []) if hook.get("type") == "command"]


REGISTERED = _registered()


def _hook_id(event: str, command: str) -> str:
    tail = command.rsplit("hooks/", 1)[-1]
    return f"{event}:{re.sub(r'[^A-Za-z0-9_.-]+', '_', tail)[:48]}"


def _project(tmp_path: Path, names=NAMES) -> Path:
    project = tmp_path / "project"
    (project / ".claude" / "canvas").mkdir(parents=True)
    (project / ".claude" / "diamonds").mkdir()
    (project / ".claude" / "memory").mkdir()
    (project / ".claude" / "diamonds" / ("active" + ".yml")).write_text(
        "active_diamonds:\n- id: l0\n  scale: L0\n")
    _scratch_git.init(project)
    for name in names:
        (project / f"{name}.py").write_text(CANARY.format(name=name))
    return project


def _ran(project: Path) -> list[str]:
    return sorted(p.stem for p in project.rglob("*.ran"))


def _env(project: Path, **extra) -> dict:
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project.parent),
           "CLAUDE_PROJECT_DIR": str(project), "MYCELIUM_CI_SIGNAL": "off",
           "PYTHONUSERBASE": site.getuserbase()}
    env.update(extra)
    return env


# ---------------------------------------------------------------- every registered hook, for real


def test_every_event_in_the_manifest_has_a_payload_here():
    events = set(json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"])
    assert events <= set(_PAYLOADS), events - set(_PAYLOADS)


@pytest.mark.parametrize(("event", "command"), REGISTERED,
                         ids=[_hook_id(e, c) for e, c in REGISTERED])
def test_a_hook_imports_no_module_from_the_project(tmp_path, event, command):
    """RED BEFORE 0.322.4 for every hook that runs inline Python. The hook is started as Claude
    Code starts it: the manifest's own command line, plugin root set, project as current
    directory."""
    project = _project(tmp_path)
    payload = dict(_PAYLOADS[event], session_id="t", cwd=str(project), hook_event_name=event)
    subprocess.run(["bash", "-c", command], input=json.dumps(payload), cwd=project,
                   env=_env(project, CLAUDE_PLUGIN_ROOT=str(PLUGIN)), capture_output=True,
                   text=True, timeout=180, check=False)
    assert _ran(project) == [], f"{command} imported {_ran(project)} from the project"


@pytest.mark.parametrize("hook", ["session-start.sh", "stop-check.sh"])
def test_with_no_plugin_root_a_hook_imports_nothing_from_a_scripts_folder(tmp_path, hook):
    """RED BEFORE 0.322.4 (blind read round 3): `scripts` in the project was put on the path and
    `scale_locks` imported from it."""
    project = _project(tmp_path, names=())
    planted = project / "scripts" / "scale_locks.py"
    planted.parent.mkdir()
    planted.write_text("import pathlib\npathlib.Path(__file__).with_suffix('.ran').write_text('x')\n"
                       "def phase_of(d):\n    return ''\n")
    event = "SessionStart" if hook.startswith("session") else "Stop"
    payload = dict(_PAYLOADS[event], session_id="t", cwd=str(project), hook_event_name=event)
    subprocess.run(["bash", str(PLUGIN / "hooks" / hook)], input=json.dumps(payload), cwd=project,
                   env=_env(project), capture_output=True, text=True, timeout=180, check=False)
    assert _ran(project) == []


def test_control_a_project_file_named_like_a_module_does_not_change_the_gates_refusal(tmp_path):
    """A CONTROL, green on 0.322.3 as well: `types.py` at a repository's root is ordinary, and a
    file by that name that fails on import must not stop the secret scan from refusing."""
    project = tmp_path / "project"
    (project / ".claude" / "canvas").mkdir(parents=True)
    for name in ("types", "enum", "json", "re", "yaml"):
        (project / f"{name}.py").write_text("raise RuntimeError('this is the project\\'s file')\n")
    secret = "API" + '_KEY="' + "ab12" * 6 + '"'
    payload = {"tool_name": "Write", "permission_mode": "default",
               "tool_input": {"file_path": "src/config.py", "content": secret}}
    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "gate.sh")], input=json.dumps(payload),
                          cwd=project, env=_env(project, CLAUDE_PLUGIN_ROOT=str(PLUGIN)),
                          capture_output=True, text=True, timeout=60, check=False)
    assert "G-S1" in done.stdout, done.stderr[-300:]


# ---------------------------------------------------------------- each half holds alone


def _plain_env(project: Path) -> dict:
    return {"PATH": os.environ["PATH"], "HOME": str(project), "PYTHONUSERBASE": site.getuserbase()}


def test_control_plain_inline_python_does_import_the_canary(tmp_path):
    """If this fails the canaries prove nothing: it is the behaviour the fix exists for."""
    project = _project(tmp_path, names=("json",))
    subprocess.run([sys.executable, "-c", "import json"], cwd=project, env=_plain_env(project),
                   check=False, capture_output=True)
    assert _ran(project) == ["json"]


def test_the_launcher_alone_keeps_the_project_off_the_path(tmp_path):
    """No PYTHONSAFEPATH here: this is what covers Python before 3.11."""
    project = _project(tmp_path, names=("json", "re"))
    done = subprocess.run([sys.executable, str(SAFE), "import json, re; print(json.dumps([1]))"],
                          cwd=project, env=_plain_env(project), capture_output=True, text=True,
                          check=False)
    assert (done.returncode, done.stdout.strip(), _ran(project)) == (0, "[1]", [])


@pytest.mark.parametrize("call", [
    "python3 -c 'import json, re'",
    "python3 - <<'PY'\nimport json, re\nPY",
    "echo x | python3 -c 'import json, sys; sys.stdin.read()'",
    "out=$(python3 -c 'import json; print(1)'); test \"$out\" = 1",
])
def test_the_shell_function_alone_keeps_the_project_off_the_path(tmp_path, call):
    """PYTHONSAFEPATH is unset after the prelude is sourced, so only the function is at work."""
    project = _project(tmp_path, names=("json", "re"))
    script = f'. "{PRELUDE}"\nunset PYTHONSAFEPATH\n{call}\n'
    done = subprocess.run(["bash", "-c", script], cwd=project, text=True, capture_output=True,
                          env=dict(_plain_env(project), CLAUDE_PROJECT_DIR=str(project)),
                          check=False)
    assert done.returncode == 0, done.stderr
    assert _ran(project) == []


def test_the_prelude_sets_the_safe_path_for_everything_a_hook_starts(tmp_path):
    project = _project(tmp_path, names=())
    script = f'. "{PRELUDE}"\nprintf %s "$PYTHONSAFEPATH"; command -v python3 >/dev/null'
    done = subprocess.run(["bash", "-c", script], cwd=project, text=True, capture_output=True,
                          env=dict(_plain_env(project), CLAUDE_PROJECT_DIR=str(project)),
                          check=False)
    assert done.stdout == "1"


def test_no_hook_starts_inline_python_by_an_explicit_interpreter_path():
    """The shell function only catches the name `python3`. An interpreter reached by path
    (`"$own" -c ...`, `"$(mycelium_python)" -c ...`) has to name the launcher itself."""
    found = []
    for f in [*sorted((PLUGIN / "hooks").glob("*.sh")), *sorted((PLUGIN / "scripts").glob("_*.sh"))]:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            # At command position only: `_mycelium_py "$py" -c ...` hands the interpreter to
            # the wrapper and is the covered form.
            if re.search(r'(?:^|[|;&(!]|\bif|\bthen|\bdo)\s*"\$[A-Za-z_({][^"]*"\s+-(?:c\b|\s)',
                         line):
                found.append(f"{f.name}:{n}: {line.strip()[:90]}")
    assert found == [], "\n".join(found)


# ---------------------------------------------------------------- the launcher behaves like -c


def _safe(*args: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SAFE), *args], input=stdin, capture_output=True,
                          text=True, check=False)


def test_the_code_sees_the_arguments_dash_c_would_give_it():
    done = _safe("import sys; print(sys.argv)", "a", "b c")
    assert done.stdout.strip() == "['-c', 'a', 'b c']"


def test_stdin_is_the_codes_own_in_dash_c_mode_and_the_code_itself_in_stdin_mode():
    assert _safe("import sys; print(sys.stdin.read().upper())", stdin="payload").stdout.strip() \
        == "PAYLOAD"
    done = _safe("--stdin", "x", stdin="import sys\nprint(sys.argv, __name__)\n")
    assert done.stdout.strip() == "['-', 'x'] __main__"


def test_exit_status_and_errors_pass_through():
    assert _safe("import sys; sys.exit(3)").returncode == 3
    failed = _safe("raise ValueError('boom')")
    assert failed.returncode == 1 and "ValueError: boom" in failed.stderr
    assert _safe().returncode == 2


def test_a_snippet_can_still_add_myceliums_own_folder_and_import_from_it():
    done = _safe(f"import sys; sys.path.insert(0, {str(PLUGIN / 'scripts')!r}); "
                 "import _state_dir; print(_state_dir.TEMPLATE.name)")
    assert done.stdout.strip() == "state-gitignore.txt"
