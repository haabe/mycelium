"""The suite cannot write into the repository of whoever runs it (0.319.1).

WHAT HAPPENED. On 2026-10-11 a `git push` from a git WORKTREE of this repository ran the suite
through the pre-push hook. Afterwards the checked-out feature branch carried fourteen commits by
"t <t@t>" with subjects like "add" and "quietly loosen the threshold", the shared `.git/config`
said `core.bare = true` and `user.name = t`, and the worktree's index held a temp folder's files.

WHY. In a worktree git exports `GIT_DIR=<main>/.git/worktrees/<name>` to its hooks; in an ordinary
checkout it exports no `GIT_DIR`, which is why the same suite had always been harmless there. With
`GIT_DIR` set git ignores the folder it runs in, so a fixture's `git init`, `git config`,
`git add -A` and `git commit` in a temp folder all acted on the caller's repository. Traced file
by file: twelve pytest files, three bash suites and one gate in the declared set did it.

HOW THESE TESTS REPRODUCE IT. Each builds a scratch repository with a worktree, then has GIT ITSELF
run the thing under test as a hook of that worktree (a pre-commit hook that always refuses, so git
writes nothing of its own). The environment is therefore the one git really gives a hook there,
not a guess at it; a pre-commit hook gets everything a pre-push hook gets, and `GIT_INDEX_FILE`
besides. The assertion is the one the incident failed: the scratch repository's config and refs
are byte-identical before and after.

NEGATIVE CONTROL (run before the fix, on the tree 0.319.0 shipped): every test below marked
`# RED BEFORE` failed, each with the scratch repository's config rewritten or its branch moved.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import _scratch_git
import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
PRE_PUSH = PLUGIN / "scripts" / "git-pre-push-example.sh"

#: What a fixture did on 2026-10-11, in one script: a repository in a temp folder, a config
#: write, a commit. Harmless when git looks at the temp folder; the incident when it does not.
FIXTURE_BUILDER = """\
d="$(mktemp -d)"
cd "$d" || exit 0
git init -q
git config user.name leaked
git config user.email leaked@example.invalid
echo x > leaked.txt
git add -A
git commit -q -m "a fixture commit that must stay in its temp folder"
touch "$PROBE_RAN"
"""


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=_scratch_git.clean_env(), check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def caller(tmp_path):
    """A repository with one commit and a worktree on a branch: the shape that was damaged."""
    main = _scratch_git.init(tmp_path / "main")
    _git(main, "config", "user.name", "Caller")
    _git(main, "config", "user.email", "caller@example.invalid")
    (main / "tracked.txt").write_text("the caller's own file\n")
    _git(main, "add", "-A")
    _git(main, "commit", "-q", "-m", "the caller's commit")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt), "-b", "feature")
    return SimpleNamespace(main=main, wt=wt, tmp=tmp_path,
                           gitdir=main / ".git" / "worktrees" / "wt")


def _as_a_git_hook(caller, command: list[str], extra_env: dict | None = None):
    """Have git run `command` as a hook of the worktree; returns (exit status, output).

    A pre-commit hook that runs the command and then refuses the commit. git sets the hook's
    environment and, because the hook refuses, writes no commit, ref or config of its own.
    A commit made BY the command can reach this same hook (that is the defect); it is let
    through at once, so the unprotected control can show its damage and nothing recurses."""
    hooks = caller.main / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    out, rc = caller.tmp / "hook.out", caller.tmp / "hook.rc"
    for f in (out, rc):
        f.unlink(missing_ok=True)
    (hooks / "pre-commit").write_text(
        "#!/bin/sh\n"
        '[ -n "${MYC_PROBE_HOOK_RUNNING:-}" ] && exit 0\n'
        "export MYC_PROBE_HOOK_RUNNING=1\n"
        f"{shlex.join(command)} > {shlex.quote(str(out))} 2>&1\n"
        f"echo $? > {shlex.quote(str(rc))}\n"
        "exit 1\n")
    (hooks / "pre-commit").chmod(0o755)
    env = _scratch_git.clean_env()
    env.pop("CLAUDE_PLUGIN_ROOT", None)   # as CI runs; a session exports it (gates.sh, 2026-09-11)
    env.update(extra_env or {})
    done = subprocess.run(
        ["git", "-c", f"core.hooksPath={hooks}", "commit", "--allow-empty", "-q", "-m", "probe"],
        cwd=caller.wt, env=env, capture_output=True, text=True, check=False)
    assert done.returncode != 0, "the probe commit was meant to be refused by its own hook"
    assert rc.exists(), f"git did not run the hook: {done.stderr}"
    return int(rc.read_text().strip()), out.read_text(errors="replace")


def _status(cwd: Path) -> str:
    """`git status`, or what git said instead: a repository whose config now says it is bare
    refuses to report one, and that refusal must read as a difference, not crash the test."""
    done = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cwd,
                          env=_scratch_git.clean_env(), capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else f"git status refused: {done.stderr.strip()}"


def _state(caller) -> dict:
    """What the incident changed: the shared config, every ref, both HEADs, both trees' status,
    and which files exist under .git (a merge left in progress shows there). Config and refs
    come first, so a failure names them before anything that follows from them."""
    gitdir = caller.main / ".git"
    skip_dirs, skip_names = {"objects", "logs"}, {"index", "COMMIT_EDITMSG", "ORIG_HEAD"}
    listing = sorted(
        str(p.relative_to(gitdir)) for p in gitdir.rglob("*")
        if p.is_file() and not (set(p.relative_to(gitdir).parts) & skip_dirs)
        and p.name not in skip_names)
    return {
        "config": (gitdir / "config").read_bytes(),
        "refs": _git(caller.main, "for-each-ref"),
        "head": (gitdir / "HEAD").read_bytes(),
        "worktree_head": (caller.gitdir / "HEAD").read_bytes(),
        "status": _status(caller.main),
        "worktree_status": _status(caller.wt),
        "git_files": listing,
    }


def _run_and_compare(caller, command: list[str], extra_env: dict | None = None):
    """Run `command` as a hook of the worktree; returns (status, output, before, after)."""
    _as_a_git_hook(caller, ["true"])           # whatever the probe itself leaves is in `before`
    before = _state(caller)
    status, out = _as_a_git_hook(caller, command, extra_env)
    return status, out, before, _state(caller)


def _assert_untouched(before: dict, after: dict, out: str) -> None:
    for key, was in before.items():
        assert after[key] == was, (
            f"the caller's repository changed ({key}):\n  before: {was!r}\n"
            f"  after:  {after[key]!r}\n--- output ---\n{out[-1500:]}")


# ---------------------------------------------------------------- the premise

def test_premise_git_gives_a_hook_in_a_worktree_the_callers_git_dir(caller):
    """If git stops doing this, every test below proves nothing; this one says so first."""
    _, out = _as_a_git_hook(caller, ["env"])
    seen = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    assert os.path.realpath(seen.get("GIT_DIR", "")) == os.path.realpath(caller.gitdir), out


def test_premise_the_fixture_builder_does_the_damage_when_nothing_clears(caller):
    """The control for the method: unprotected, the builder writes the caller's config and moves
    its branch. A harness in which this passed untouched could not show the fix working."""
    probe = caller.tmp / "unprotected.sh"
    probe.write_text(FIXTURE_BUILDER)
    config = caller.main / ".git" / "config"
    before = (config.read_bytes(), _git(caller.main, "for-each-ref"))
    _, out = _as_a_git_hook(caller, ["sh", str(probe)], {"PROBE_RAN": str(caller.tmp / "ran")})
    # Read directly: once the config says the repository is bare, `git status` refuses to run.
    assert b"bare = true" in config.read_bytes(), out
    assert b"leaked" in config.read_bytes(), out
    assert _git(caller.main, "for-each-ref") != before[1], (
        "the fixture commit did not land on the caller's branch")
    assert "must stay in its temp folder" in _git(caller.main, "log", "-1", "--format=%s", "feature")


# ---------------------------------------------------------------- the suites themselves

@pytest.mark.parametrize("test_file", [
    "test_instrument_contract.py",      # `git init` with cwd; wrote the fourteen commits
    "test_check_cycle_recording.py",    # `git -C <tmp> init`
    "test_snooze_wakes_on_work.py",     # `git init <tmp>`
])
def test_a_pytest_file_that_builds_repositories_leaves_the_caller_alone(caller, test_file):
    # RED BEFORE: conftest cleared nothing and each helper ran a bare `git init`.
    status, out, before, after = _run_and_compare(caller, [
        sys.executable, "-m", "pytest", str(ROOT / "tests" / "python" / test_file),
        "-q", "-p", "no:cacheprovider"])
    _assert_untouched(before, after, out)
    assert status == 0, out[-1500:]


@pytest.mark.parametrize("test_file", ["test_check_26.sh", "test_git_pre_commit_hook.sh",
                                       "test_provision_skills_guards.sh"])
def test_a_bash_test_that_builds_repositories_leaves_the_caller_alone(caller, test_file):
    # RED BEFORE: test_git_pre_commit_hook also left a branch `other` and a merge in progress.
    status, out, before, after = _run_and_compare(
        caller, ["bash", str(ROOT / "tests" / "bash" / test_file)])
    _assert_untouched(before, after, out)
    assert status == 0, out[-1500:]


def test_the_gate_that_builds_an_empty_repository_leaves_the_caller_alone(caller):
    # RED BEFORE: check_empty_input_honesty.py is in the declared gate set, so the pre-push hook
    # ran its `git init` against the caller's repository whether or not any test did.
    status, out, before, after = _run_and_compare(caller, [
        sys.executable, str(PLUGIN / "scripts" / "check_empty_input_honesty.py"),
        "--root", str(ROOT)])
    _assert_untouched(before, after, out)
    assert status == 0, out[-1500:]


# ---------------------------------------------------------------- the places that run the suite

def _probe(caller) -> tuple[Path, dict]:
    probe = caller.tmp / "fixture_builder.sh"
    probe.write_text(FIXTURE_BUILDER)
    return probe, {"PROBE_RAN": str(caller.tmp / "probe-ran")}


def test_the_pre_push_hook_clears_it_for_everything_it_runs(caller):
    """A framework-shaped tree in the worktree whose validator, test and gate each build a
    repository the way the fixtures did. The hook runs all three; none reaches the caller."""
    # RED BEFORE: the hook cleared nothing.
    probe, env = _probe(caller)
    wt = caller.wt
    scripts = wt / "plugins" / "mycelium" / "scripts"
    for d in (wt / ".claude" / "canvas", scripts, wt / "tests" / "python"):
        d.mkdir(parents=True)
    (scripts / "validate_canvas.py").write_text("print('canvas ok')\n")
    (wt / "tests" / "validate-template.sh").write_text(f"sh {shlex.quote(str(probe))}\n")
    (wt / "tests" / "python" / "test_probe.py").write_text(
        "import subprocess\n\n\ndef test_probe():\n"
        f"    subprocess.run(['sh', {str(probe)!r}], check=True)\n")
    (scripts / "probe_gate.py").write_text(
        f"import subprocess\nsubprocess.run(['sh', {str(probe)!r}], check=True)\n")
    (scripts / "local-gate-set.txt").write_text("probe_gate.py\n")
    # `python3` on the hook's PATH is this interpreter, which has pytest; no requirements-ci.txt
    # in the tree, so the hook takes it rather than uv.
    bindir = caller.tmp / "bin"
    bindir.mkdir()
    (bindir / "python3").write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
    (bindir / "python3").chmod(0o755)
    env["PATH"] = f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"
    # The hook's own pytest must leave no cache or bytecode in the tree, or the worktree's
    # status would differ for a reason that is not the one under test.
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    status, out, before, after = _run_and_compare(caller, ["bash", str(PRE_PUSH)], env)
    assert status == 0, out[-2000:]
    for ran in ("Validating template integrity", "fast tests", "declared gate set"):
        assert ran in out, f"the hook did not reach '{ran}':\n{out[-2000:]}"
    assert Path(env["PROBE_RAN"]).exists(), "no fixture builder ran, so nothing was shown"
    _assert_untouched(before, after, out)


def _sandbox_bash_suite(caller, probe: Path) -> Path:
    sb = caller.tmp / "bash-suite"
    sb.mkdir()
    for name in ("run.sh", "_assert.sh"):
        shutil.copy(ROOT / "tests" / "bash" / name, sb / name)
    (sb / "test_probe.sh").write_text(f"sh {shlex.quote(str(probe))}\n")
    return sb


def test_the_bash_runner_clears_it_for_every_test_file(caller):
    # RED BEFORE: run.sh cleared nothing.
    probe, env = _probe(caller)
    sb = _sandbox_bash_suite(caller, probe)
    status, out, before, after = _run_and_compare(caller, ["bash", str(sb / "run.sh")], env)
    assert Path(env["PROBE_RAN"]).exists(), out
    _assert_untouched(before, after, out)
    assert status == 0, out


def test_a_bash_test_run_on_its_own_is_cleared_by_the_shared_helpers(caller):
    # RED BEFORE: _assert.sh cleared nothing, so one test file run from a hook did the damage.
    probe, env = _probe(caller)
    sb = _sandbox_bash_suite(caller, probe)
    (sb / "test_alone.sh").write_text(
        f'. "$(dirname "$0")/_assert.sh"\nsh {shlex.quote(str(probe))}\n')
    _, out, before, after = _run_and_compare(caller, ["bash", str(sb / "test_alone.sh")], env)
    assert Path(env["PROBE_RAN"]).exists(), out
    _assert_untouched(before, after, out)


def test_gates_sh_clears_it_for_every_gate(caller):
    # RED BEFORE: gates.sh cleared nothing. The sandbox has one gate, the validator; the rest are
    # reported missing, which is gates.sh being honest and not what is asserted here.
    probe, env = _probe(caller)
    sb = caller.tmp / "gates-tree"
    (sb / "scripts").mkdir(parents=True)
    (sb / "tests").mkdir()
    shutil.copy(ROOT / "scripts" / "gates.sh", sb / "scripts" / "gates.sh")
    (sb / "tests" / "validate-template.sh").write_text(f"sh {shlex.quote(str(probe))}\n")
    _, out, before, after = _run_and_compare(caller, ["bash", str(sb / "scripts" / "gates.sh")], env)
    assert Path(env["PROBE_RAN"]).exists(), out
    # The hook writes this output to a file (`> out 2>&1`), which is how gates.sh says to be run.
    # RED ON LINUX BEFORE 0.319.1: each verdict line went through `tee /dev/stderr`, which there
    # re-opens the log with truncation, so the gate lines came back as NUL bytes and only the
    # last verdict line survived. macOS does not truncate, so this was green on a Mac.
    assert "\x00" not in out, "the redirected log was truncated under its own writer"
    assert "GATES: INCOMPLETE" in out, out
    assert "PASS  validate-template" in out, out
    _assert_untouched(before, after, out)


def test_the_validator_clears_it_before_its_first_check(caller):
    """The validator's own opening lines, run as they are. Running all of it takes minutes, so
    this runs everything up to its first section and then builds a fixture in the same shell."""
    # RED BEFORE: the opening lines cleared nothing.
    probe, env = _probe(caller)
    text = (ROOT / "tests" / "validate-template.sh").read_text(encoding="utf-8")
    marker = "# --- Skills tree detection"
    assert marker in text, "the validator's first section moved; point this test at the new one"
    opening = caller.tmp / "validator-opening.sh"
    # BASH_SOURCE must resolve to the real validator, so its `cd` lands where it always does.
    opening.write_text(text[:text.index(marker)].replace(
        '"${BASH_SOURCE[0]}"', shlex.quote(str(ROOT / "tests" / "validate-template.sh")))
        + f"\nsh {shlex.quote(str(probe))}\n")
    status, out, before, after = _run_and_compare(caller, ["bash", str(opening)], env)
    assert Path(env["PROBE_RAN"]).exists(), out
    _assert_untouched(before, after, out)
    assert status == 0, out


# ---------------------------------------------------------------- the helpers refuse, loudly

def test_the_python_helper_refuses_when_git_would_look_elsewhere(caller, monkeypatch):
    """The second layer on its own: something set GIT_DIR after conftest cleared it."""
    before = _state(caller)
    monkeypatch.setenv("GIT_DIR", str(caller.gitdir))
    with pytest.raises(_scratch_git.ScratchRepoEscapedError) as refused:
        _scratch_git.init(caller.tmp / "throwaway")
    monkeypatch.delenv("GIT_DIR")
    assert "GIT_DIR" in str(refused.value)
    assert "Nothing was configured or committed" in str(refused.value)
    _assert_untouched(before, _state(caller), str(refused.value))


def test_the_bash_helper_refuses_when_git_would_look_elsewhere(caller):
    before = _state(caller)
    script = caller.tmp / "escape.sh"
    script.write_text(
        f'. {shlex.quote(str(ROOT / "tests" / "bash" / "_assert.sh"))}\n'
        f'export GIT_DIR={shlex.quote(str(caller.gitdir))}\n'
        f'scratch_git_init {shlex.quote(str(caller.tmp / "throwaway"))}\n'
        'git config user.name leaked\n')
    done = subprocess.run(["bash", str(script)], env=_scratch_git.clean_env(),
                          capture_output=True, text=True, check=False)
    assert done.returncode == 97, done.stderr
    assert "NOT WHERE GIT LOOKS" in done.stderr
    _assert_untouched(before, _state(caller), done.stderr)


def test_control_the_helpers_build_an_ordinary_repository(tmp_path):
    """The other direction: with nothing redirecting git, the helper's repository is usable."""
    repo = _scratch_git.init(tmp_path / "r")
    assert (repo / ".git").is_dir()
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit",
         "--allow-empty", "-q", "-m", "works")
    assert "works" in _git(repo, "log", "--format=%s")


def test_clearing_removes_what_redirects_git_and_nothing_else(monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/somewhere/.git/worktrees/x")
    monkeypatch.setenv("GIT_INDEX_FILE", "/somewhere/.git/worktrees/x/index")
    monkeypatch.setenv("GIT_WORK_TREE", "/somewhere")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "kept")
    removed = _scratch_git.clear_inherited_git_env()
    assert {"GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"} <= set(removed)
    assert not any(n in os.environ for n in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"))
    assert os.environ["GIT_AUTHOR_NAME"] == "kept", "identity variables redirect nothing"


# ---------------------------------------------------------------- no test goes around the helpers

#: A `git init` run by a test. Python: a "git" argument list that reaches "init", or a `_git(...)`
#: style wrapper given "init". Bash: `git ... init` in command position.
_PY_INIT = re.compile(
    r"""["']git["'][^\n\]]*["']init["']|\b_?git\w*\([^\n)]*["']init["']|\*git\s*,\s*["']init["']""")
_SH_INIT = re.compile(r"""(?m)^\s*(?:\(\s*)?(?:cd\s+\S+\s*&&\s*)?git(?:\s+-[Cc]\s+\S+)*\s+init\b""")
#: The two helpers, and this file, whose controls below quote the old forms.
_HELPERS = {"_scratch_git.py", "_assert.sh", "test_suite_safe_in_a_worktree.py"}


def _raw_inits() -> list[str]:
    found = []
    for path in sorted((ROOT / "tests" / "python").glob("*.py")):
        if path.name not in _HELPERS and _PY_INIT.search(path.read_text(encoding="utf-8")):
            found.append(f"tests/python/{path.name}")
    for path in sorted((ROOT / "tests" / "bash").glob("*.sh")):
        if path.name not in _HELPERS and _SH_INIT.search(path.read_text(encoding="utf-8")):
            found.append(f"tests/bash/{path.name}")
    return found


def test_no_test_runs_git_init_except_through_the_helpers():
    """A new fixture repository goes through `_scratch_git.init` or `scratch_git_init`, which
    check where git looks before anything is written. A bare `git init` is how this started."""
    assert _raw_inits() == [], (
        "these build a repository with a bare `git init`; use _scratch_git.init(path) in "
        "tests/python or scratch_git_init DIR in tests/bash")


@pytest.mark.parametrize("line", [
    'subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)',
    'subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)',
    '_git(repo, "init", "-q")',
    'subprocess.run([*git, "init", "-q"], cwd=tmp_path, check=True)',
])
def test_control_the_python_pattern_sees_every_form_the_suite_used(line):
    assert _PY_INIT.search(line)


@pytest.mark.parametrize("line", ["        git init --quiet", '    (cd "$tmp" && git init -q 2>/dev/null)',
                                  'git -C "$tmp" init -q'])
def test_control_the_bash_pattern_sees_every_form_the_suite_used(line):
    assert _SH_INIT.search(line)


@pytest.mark.parametrize("line", ['assert_contains "$out" "git init" "gives the one-command fix"',
                                  "# `git init` is the fix and it is cheap",
                                  'scratch_git_init "$PWD"'])
def test_control_the_bash_pattern_leaves_prose_and_the_helper_alone(line):
    assert not _SH_INIT.search(line)
