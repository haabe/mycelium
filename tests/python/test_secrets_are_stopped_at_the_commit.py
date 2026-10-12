"""Secrets are stopped at the commit and at the push, not at the write (v0.323.0).

WHAT WAS WRONG. Mycelium looked for secrets when the agent WROTE a file, with a short list of its
own. Replayed 2026-10-12: an unquoted `KEY=value` passed, an env file was treated like source
code, and nothing ever looked at what was staged or committed. The maintainer: "Don't let
passwords into the repo", at the commit, with an established scanner.

WHAT HOLDS NOW.
- A write is not scanned: the agent may put a key in a file. It may not commit or push one.
- The agent's `git commit` is scanned first (the index; with `-a` or a named path, the tracked
  files as on disk). A finding refuses it.
- Commits a shell command made by any other route are scanned afterwards and reported.
- The agent's `git push` is scanned first (every commit on no remote). A finding refuses it.
- gitleaks does the scanning where it is installed; where it is not, Mycelium's own short list
  does, and the person is told once a session that it is the weaker check.
- The scanner's own ways past a finding are the person's to write.
- A key typed into a shell command is still refused.

Every key-shaped value here is BUILT AT RUN TIME from harmless parts, as in
test_gate_secret_scan.py. The hook tests run the real hook scripts. Most run with no scanner on
the PATH, so they hold on any machine; the ones that need gitleaks skip where it is absent, and
the wrapper around it is tested in-process against a stand-in.
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
PLUGIN = ROOT / "plugins" / "mycelium"
GATE = PLUGIN / "hooks" / "gate.sh"
GUARD_GATE = PLUGIN / "hooks" / "guard-state-gate.sh"
SHELL_GUARD = PLUGIN / "hooks" / "bash-state-guard.sh"
sys.path.insert(0, str(PLUGIN / "scripts"))
import commit_scan as cs  # noqa: E402

KEY = "Zx9Qv7Lm" + "2Rt8Kp4W" + "n6Yb3Hd5"            # 24 characters, mixed, not a real key
LINE = "API" + "_KEY" + ' = "' + KEY + '"'
PYTHON_DIR = str(Path(sys.executable).parent)
NO_SCANNER = f"{PYTHON_DIR}:/usr/bin:/bin"
REAL = shutil.which("gitleaks")
WITH_SCANNER = f"{Path(REAL).parent}:{NO_SCANNER}" if REAL else NO_SCANNER
needs_gitleaks = pytest.mark.skipif(REAL is None, reason="gitleaks is not installed here")
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True,
                          env={**os.environ, **GIT_ENV}, check=True)
    return done.stdout.strip()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A Mycelium project that is a git repository with one commit."""
    proj = tmp_path / "proj"
    (proj / ".claude" / "canvas").mkdir(parents=True)
    (proj / ".claude" / "state").mkdir()
    (proj / ".gitignore").write_text(".claude/state/\n")
    (proj / "app.py").write_text("x = 1\n")
    git(proj, "init", "-q", "-b", "main", ".")
    git(proj, "add", "-A")
    git(proj, "commit", "-q", "-m", "seed")
    return proj


def _env(project: Path, path: str) -> dict:
    return {"PATH": path, "HOME": str(project.parent), "TMPDIR": str(project.parent),
            "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN), **GIT_ENV}


def gate(project: Path, tool: str, tool_input: dict, path: str = NO_SCANNER,
         session: str = "s1") -> dict:
    payload = {"tool_name": tool, "tool_input": tool_input, "permission_mode": "default",
               "cwd": str(project), "session_id": session}
    done = subprocess.run(["bash", str(GATE)], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project, path), cwd=project, timeout=120,
                          check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout) if done.stdout.strip() else {}


def decision(out: dict) -> str:
    return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


def reason(out: dict) -> str:
    return out.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def commit(project: Path, command: str = "git commit -m work", **kw) -> dict:
    return gate(project, "Bash", {"command": command}, **kw)


# ---------------------------------------------------------------- a write is not scanned


@pytest.mark.parametrize("rel", [".env", "src/config.py", ".claude/canvas/purpose.yml"])
def test_a_key_written_into_a_file_is_no_longer_refused(project, rel):
    """CHANGED IN 0.323.0, on the maintainer's ruling "Stop refusing writes". Until then this
    was refused, for a quoted value; an unquoted one passed."""
    out = gate(project, "Write", {"file_path": str(project / rel), "content": LINE + "\n"})
    assert decision(out) == "allow"


def test_control_a_key_typed_into_a_shell_command_is_still_refused(project):
    out = gate(project, "Bash", {"command": f"curl -H '{LINE}' https://example.invalid"})
    assert decision(out) == "deny" and "shell command" in reason(out)


# ---------------------------------------------------------------- the agent's commit


def test_a_commit_that_would_take_a_key_is_refused(project):
    """RED BEFORE 0.323.0: nothing looked at what was staged."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    out = commit(project)
    assert decision(out) == "deny"
    assert "commit is refused" in reason(out) and KEY not in reason(out)


def test_control_a_clean_commit_is_not_refused(project):
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    assert decision(commit(project)) == "allow"


def test_control_a_key_that_is_not_staged_does_not_stop_a_plain_commit(project):
    """A plain commit takes the index. A key in the working tree is not in it."""
    (project / "app.py").write_text(LINE + "\n")
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    assert decision(commit(project)) == "allow"


@pytest.mark.parametrize("command", ["git commit -am work", "git commit --all -m work",
                                     "git commit -m work app.py", "git commit -m work -- app.py"])
def test_a_commit_that_takes_files_as_they_are_on_disk_is_scanned_wider(project, command):
    (project / "app.py").write_text(LINE + "\n")
    assert decision(commit(project, command)) == "deny"


@pytest.mark.parametrize("command", ["cd . && git commit -m work", "git -c user.name=x commit -m w",
                                     "git add -A; git commit -m work", "(git commit -m work)"])
def test_the_commit_is_found_in_the_forms_it_is_typed(project, command):
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, command)) == "deny"


def test_control_a_command_that_only_mentions_the_words_is_not_scanned(project):
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, "echo 'remember to git commit later'")) == "allow"
    assert decision(commit(project, "git log --grep=commit")) == "allow"


# ---------------------------------------------------------------- the agent's push


def test_a_push_of_a_commit_that_holds_a_key_is_refused(project):
    """RED BEFORE 0.323.0. The commit was made some way the commit scan did not see."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    git(project, "commit", "-q", "-m", "oops")
    out = gate(project, "Bash", {"command": "git push origin main"})
    assert decision(out) == "deny" and "push is refused" in reason(out)


def test_control_a_push_of_clean_commits_is_not_refused(project):
    assert decision(gate(project, "Bash", {"command": "git push origin main"})) == "allow"


def test_control_a_key_already_on_a_remote_does_not_stop_a_later_push(project, tmp_path):
    """Only commits that are on no remote are scanned: what is already out is not this push."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    git(project, "commit", "-q", "-m", "oops")
    remote = tmp_path / "origin.git"
    git(project, "clone", "-q", "--bare", str(project), str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "fetch", "-q", "origin")
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    git(project, "commit", "-q", "-m", "fine")
    assert decision(gate(project, "Bash", {"command": "git push"})) == "allow"


# ---------------------------------------------------------------- no scanner installed


def test_with_no_scanner_the_short_list_runs_and_the_person_is_told_once(project):
    """Maintainer's ruling: "Fall back, and say so"."""
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    first = commit(project)
    assert "no secret scanner is installed" in first.get("systemMessage", "")
    assert "gitleaks" in first["systemMessage"]
    assert commit(project) == {}, "said twice in one session"
    assert "systemMessage" in commit(project, session="s2"), "not said in a new session"


def test_with_no_scanner_a_finding_says_which_check_found_it(project):
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert "own short list" in reason(commit(project))


def test_a_scan_that_cannot_run_refuses_the_commit(project, tmp_path):
    """The 0.319.1 rule, kept: a scan that cannot look does not say "clean"."""
    fake = tmp_path / "fakebin"
    fake.mkdir()
    (fake / "grep").write_text("#!/bin/sh\necho 'grep: simulated failure' >&2\nexit 2\n")
    (fake / "grep").chmod(0o755)
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    out = commit(project, path=f"{fake}:{NO_SCANNER}")
    assert decision(out) == "deny" and "could not run" in reason(out)


# ---------------------------------------------------------------- with the established scanner


@needs_gitleaks
def test_gitleaks_refuses_a_staged_key_and_names_the_file_and_line(project):
    (project / "config.py").write_text("a = 1\n" + LINE + "\n")
    git(project, "add", "config.py")
    out = commit(project, path=WITH_SCANNER)
    assert decision(out) == "deny"
    assert "gitleaks found" in reason(out) and "config.py:2" in reason(out)
    assert KEY not in json.dumps(out)


@needs_gitleaks
def test_gitleaks_says_nothing_about_a_clean_commit(project):
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    assert commit(project, path=WITH_SCANNER) == {}


@needs_gitleaks
def test_gitleaks_scans_an_env_file_only_when_it_is_staged(project):
    """The maintainer's first point: an env file is where a key belongs, and it must not go into
    the repository. Unstaged it is not looked at; staged it is refused."""
    (project / ".env").write_text(LINE + "\n")
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    assert decision(commit(project, path=WITH_SCANNER)) == "allow"
    git(project, "add", "-f", ".env")
    assert decision(commit(project, path=WITH_SCANNER)) == "deny"


def test_the_repositorys_own_scanning_hook_is_not_doubled(project):
    """Where the person has installed a pre-commit hook that runs the scanner, a commit that
    honours hooks is theirs to scan; one that skips hooks is scanned here."""
    hook = project / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\nexec gitleaks git --pre-commit --staged\n")
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project)) == "allow"
    assert decision(commit(project, "git commit --no-verify -m work")) == "deny"
    assert decision(commit(project, "git commit -nm work")) == "deny"


# ---------------------------------------------------------------- commits a command made


def _shell_guard(project: Path, half: str) -> dict:
    payload = {"tool_name": "Bash", "tool_use_id": "call-1", "permission_mode": "default",
               "session_id": "s1", "cwd": str(project),
               "tool_input": {"command": "python3 tools/release.py"}}
    done = subprocess.run(["bash", str(SHELL_GUARD), half], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project, NO_SCANNER), timeout=120,
                          check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout) if done.stdout.strip() else {}


def test_a_commit_made_inside_a_script_is_scanned_afterwards_and_said(project):
    """RED BEFORE 0.323.0. The command's text says nothing about a commit."""
    assert _shell_guard(project, "pre") == {}
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    git(project, "commit", "-q", "-m", "made by a script")
    said = _shell_guard(project, "post")
    assert said["decision"] == "block"
    assert "has not changed the commit" in said["systemMessage"]
    assert "refuse to push" in said["systemMessage"] and KEY not in json.dumps(said)


def test_control_a_clean_commit_made_by_a_command_is_silent(project):
    assert _shell_guard(project, "pre") == {}
    (project / "ok.py").write_text("y = 2\n")
    git(project, "add", "ok.py")
    git(project, "commit", "-q", "-m", "fine")
    assert _shell_guard(project, "post") == {}


def test_control_a_commit_that_arrived_by_pull_is_not_the_commands(project, tmp_path):
    """A teammate's commit is history arriving, not something this command made."""
    remote = tmp_path / "origin.git"
    git(project, "clone", "-q", "--bare", str(project), str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "fetch", "-q", "origin")
    git(project, "branch", "-q", "--set-upstream-to=origin/main", "main")
    mate = tmp_path / "mate"
    git(tmp_path, "clone", "-q", str(remote), str(mate))
    (mate / "theirs.py").write_text(LINE + "\n")
    git(mate, "add", "-A")
    git(mate, "commit", "-q", "-m", "a teammate's commit")
    git(mate, "push", "-q", "origin", "main")
    assert _shell_guard(project, "pre") == {}
    git(project, "pull", "-q")
    assert (project / "theirs.py").exists()
    assert _shell_guard(project, "post") == {}


# ---------------------------------------------------------------- the scanner's ways past a finding


def _guard_gate(project: Path, tool: str, tool_input: dict, mode: str = "default") -> dict:
    payload = {"tool_name": tool, "tool_input": tool_input, "permission_mode": mode,
               "cwd": str(project), "session_id": "s1"}
    done = subprocess.run(["bash", str(GUARD_GATE)], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project, NO_SCANNER), timeout=60,
                          check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else {}


@pytest.mark.parametrize("rel", [".gitleaksignore", ".gitleaks.toml"])
def test_the_scanners_ignore_list_and_config_ask_the_person(project, rel):
    """Maintainer's ruling: "Agent must ask you first". RED BEFORE 0.323.0."""
    said = _guard_gate(project, "Write", {"file_path": str(project / rel), "content": "x\n"})
    assert said.get("permissionDecision") == "ask" and rel in said["permissionDecisionReason"]
    refused = _guard_gate(project, "Write", {"file_path": str(project / rel), "content": "x\n"},
                          mode="bypassPermissions")
    assert refused.get("permissionDecision") == "deny"


def test_an_inline_allow_comment_asks_the_person(project):
    edit = {"file_path": str(project / "app.py"), "old_string": "x = 1",
            "new_string": "x = 1  # " + "gitleaks" + ":allow"}
    said = _guard_gate(project, "Edit", edit)
    assert said.get("permissionDecision") == "ask"
    assert "secret scanner" in said["permissionDecisionReason"]


def test_control_an_ordinary_edit_is_not_asked_about(project):
    edit = {"file_path": str(project / "app.py"), "old_string": "x = 1", "new_string": "x = 2"}
    assert _guard_gate(project, "Edit", edit) == {}


# ---------------------------------------------------------------- the reading of a command


@pytest.mark.parametrize(("command", "expect"), [
    ("git commit -m x", {"commit": True, "wider": False, "no_verify": False, "push": False}),
    ("git commit -am x", {"commit": True, "wider": True, "no_verify": False, "push": False}),
    ("git commit -m 'take -a look' ", {"commit": True, "wider": False, "no_verify": False, "push": False}),
    ("git commit --amend --no-edit", {"commit": True, "wider": False, "no_verify": False, "push": False}),
    ("git commit -n -m x", {"commit": True, "wider": False, "no_verify": True, "push": False}),
    ("git commit -F msg.txt", {"commit": True, "wider": False, "no_verify": False, "push": False}),
    ("git commit -m x src/", {"commit": True, "wider": True, "no_verify": False, "push": False}),
    ("git commit -m 'unbalanced", {"commit": True, "wider": True, "no_verify": False, "push": False}),
    ("git push --force-with-lease", {"commit": False, "wider": False, "no_verify": False, "push": True}),
    ("git commit -m x && git push", {"commit": True, "wider": False, "no_verify": False, "push": True}),
    ("git status", {"commit": False, "wider": False, "no_verify": False, "push": False}),
    ("legit commit", {"commit": False, "wider": False, "no_verify": False, "push": False}),
])
def test_what_a_command_does_with_git(command, expect):
    assert cs.what_it_runs(command) == expect


# ---------------------------------------------------------------- the wrapper, in this process


STAND_IN = """#!/bin/sh
# a stand-in for gitleaks: the mode comes from a file beside it
mode=$(cat "$(dirname "$0")/mode")
report=""
while [ $# -gt 0 ]; do [ "$1" = "--report-path" ] && report="$2"; shift; done
case "$mode" in
  clean) exit 0;;
  found) printf '[{"File": "config.py", "StartLine": 3, "RuleID": "generic-api-key"}]' > "$report"; exit 42;;
  empty) printf '[]' > "$report"; exit 42;;
  garbage) printf 'not json' > "$report"; exit 42;;
  *) echo "FTL could not open repository" >&2; exit 1;;
esac
"""


@pytest.fixture
def stand_in(tmp_path, monkeypatch):
    folder = tmp_path / "bin"
    folder.mkdir()
    (folder / "gitleaks").write_text(STAND_IN)
    (folder / "gitleaks").chmod(0o755)
    monkeypatch.setenv("PATH", f"{folder}:{os.environ['PATH']}")
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)

    def set_mode(mode: str) -> None:
        (folder / "mode").write_text(mode)
    return set_mode


def test_the_scanners_three_answers_are_kept_apart(project, stand_in):
    stand_in("clean")
    assert cs.scan_staged(str(project), wider=True) == ("clean", [])
    stand_in("found")
    assert cs.scan_staged(str(project), wider=False) == ("found", ["config.py:3 (generic-api-key)"])
    stand_in("empty")
    assert cs.scan_unpushed(str(project)) == ("found", ["a finding it did not describe"])
    stand_in("broken")
    status, said = cs.scan_commits(str(project), ["HEAD"])
    assert status == "error" and "gitleaks exited 1" in said[0] and "could not open" in said[0]
    stand_in("garbage")
    assert cs.scan_staged(str(project), wider=False)[0] == "error"


def test_the_hooks_answer_with_a_scanner(project, stand_in, capsys):
    payload = {"tool_input": {"command": "git commit -m x && git push"}, "cwd": str(project),
               "session_id": "s1"}
    stand_in("clean")
    assert cs.pre(payload, str(project)) == 0
    assert capsys.readouterr().out == ""
    stand_in("found")
    cs.pre(payload, str(project))
    said = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "gitleaks found" in said and "config.py:3" in said and "commit is refused" in said
    stand_in("broken")
    cs.pre({**payload, "tool_input": {"command": "git push"}}, str(project))
    assert "push is refused" in capsys.readouterr().out


def test_the_hook_says_nothing_outside_a_repository_or_for_other_commands(tmp_path, capsys):
    assert cs.pre({"tool_input": {"command": "git commit -m x"}, "cwd": str(tmp_path)},
                  str(tmp_path)) == 0
    assert cs.pre({"tool_input": {"command": "ls"}}, str(tmp_path)) == 0
    assert cs.pre({"tool_input": "not an object"}, str(tmp_path)) == 0
    assert capsys.readouterr().out == ""
    assert cs.repo_of(str(tmp_path / "nowhere")) is None


def test_the_short_list_in_this_process(project, monkeypatch, capsys):
    monkeypatch.setenv("PATH", NO_SCANNER)
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)
    assert cs.scanner() is None
    assert cs.scan_staged(str(project), wider=True) == ("clean", [])
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    status, said = cs.scan_staged(str(project), wider=False)
    assert status == "found" and "own list" in said[0]
    assert cs.scan_commits(str(project), ["not-a-commit"])[0] == "error"
    cs.pre({"tool_input": {"command": "git push"}, "cwd": str(project), "session_id": "s9"},
           str(project))
    assert "no secret scanner is installed" in capsys.readouterr().out
    cs.pre({"tool_input": {"command": "git push"}, "cwd": str(project), "session_id": "s9"},
           str(project))
    assert capsys.readouterr().out == ""


def test_commits_made_are_read_from_the_reflog(project):
    repo = str(project)
    head, length = cs.head_of(repo), cs.reflog_length(repo)
    assert cs.made_commits(repo, head, length) == []
    (project / "a.py").write_text("a = 1\n")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "one")
    one = cs.head_of(repo)
    git(project, "commit", "-q", "--amend", "-m", "one, amended")
    amended = cs.head_of(repo)
    assert cs.made_commits(repo, head, length) == [amended, one]
    git(project, "switch", "-q", "-c", "side")
    assert cs.made_commits(repo, amended, cs.reflog_length(repo)) == []
    # with no reflog count to go by: what is on HEAD, on no remote, and not under the old pointer
    assert cs.made_commits(repo, head, None) == [amended]
    assert cs.made_commits(repo, "", None)[0] == amended


def test_the_entry_point_refuses_when_the_scan_itself_breaks(project, monkeypatch, capsys):
    def boom(*_args, **_kw):
        raise RuntimeError("simulated")
    monkeypatch.setattr(cs, "pre", boom)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO('{"tool_input": {}}'))
    assert cs.main(["--pre", "--project-dir", str(project)]) == 0
    assert "could not run" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("not json"))
    assert cs.main(["--project-dir", str(project)]) == 0
