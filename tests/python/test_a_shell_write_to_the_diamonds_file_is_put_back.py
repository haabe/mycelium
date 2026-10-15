"""Any change a shell command makes to the diamonds file is put back (v0.325.0).

WHAT WAS WRONG, dogfood 2026-10-14. `bash-state-guard.sh` judged the diamonds file by the command's
text. `python3 newbar.py values.yml`, a script that opened `.claude/diamonds/active.yml` itself,
replaced a whole definition of done; the scale locks found nothing to object to, and the change
stood with nothing said. Minutes later a heredoc appending to another file was refused because its
text mentioned the path. The before-and-after comparison added in 0.321.1 and 0.324.0 covered the
guard-state files and the folders a delivery cycle may write to, and nothing else in the file.

WHAT HOLDS NOW. The whole file is compared around every shell command. A change is put back, the
command's version is kept under `.claude/state/bash-guard/put-back/` and named, and the person and
the agent are told which diamonds it touched. Not put back: Mycelium's own writers run on their
own, the person's override, and git leaving the file as it is committed at HEAD, unless the command
itself committed a change to it. The text refusal keeps only writes whose target is the file.

Every test drives both halves around a change the test itself makes, standing in for the command.
"""

from __future__ import annotations

import json
import os
import site
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
import _scratch_git  # noqa: E402
import bash_state_guard as bsg  # noqa: E402

REC = ".claude/diamonds/active.yml"
OPAQUE = "python3 tool.py"
RECORD = ("active_diamonds:\n- id: l1-strategy\n  scale: L1\n  definition_of_done:\n"
          "    outcome: builders talk to users\n- id: l2-reach\n  scale: L2\n"
          "  evidence:\n  - id: ev-1\n    note: a\ncompleted_diamonds: []\n")
NEW_BAR = RECORD.replace("builders talk to users", "builders find posts in time")


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    for sub in (".claude/canvas", ".claude/diamonds", ".claude/state"):
        (tmp_path / sub).mkdir(parents=True)
    (tmp_path / REC).write_text(RECORD)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    monkeypatch.delenv("GIT_DIR", raising=False)
    return tmp_path


def _payload(project: Path, command: str = OPAQUE, call: str = "call-1") -> dict:
    return {"tool_name": "Bash", "tool_use_id": call, "session_id": "s1", "cwd": str(project),
            "tool_input": {"command": command}}


def _around(project: Path, act, capsys, command: str = OPAQUE) -> dict:
    assert bsg.pre(_payload(project, command), project) == 0
    capsys.readouterr()
    act()
    assert bsg.post(_payload(project, command), project) == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else {}


def _git(project: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(project), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *args], text=True, capture_output=True,
                          check=False, env=_scratch_git.clean_env())
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@pytest.fixture
def repo(project: Path) -> Path:
    _scratch_git.init(project, "-b", "main")
    _git(project, "add", REC)
    _git(project, "commit", "-q", "-m", "record")
    return project


# ---------------------------------------------------------------- the hole, closed


def test_a_script_s_change_to_a_bar_is_put_back_and_kept(project, capsys):
    """RED ON 0.324.0: nothing was said and the new bar stood."""
    rec = project / REC
    said = _around(project, lambda: rec.write_text(NEW_BAR), capsys)
    assert rec.read_text() == RECORD
    for text in (said["reason"], said["systemMessage"]):
        assert "A shell command changed .claude/diamonds/active.yml (l1-strategy)" in text
        assert "you were not asked first" in text and "undone with it" in text
    kept = said["reason"].split("The command's version is kept at ")[1].split(". ")[0]
    assert kept.startswith(".claude/state/bash-guard/put-back/")
    assert (project / kept).read_text() == NEW_BAR
    assert "Do not try another way" in said["reason"]
    assert "where a delivery cycle may write" not in said["reason"]


def test_the_diamonds_named_are_the_ones_whose_lines_changed(project, capsys):
    """A nested `- id:` (an evidence entry) is not taken for a diamond."""
    rec = project / REC
    said = _around(project, lambda: rec.write_text(RECORD.replace("note: a", "note: b")), capsys)
    assert "(l2-reach)" in said["reason"] and "ev-1" not in said["reason"]


def test_a_deleted_file_is_put_back(project, capsys):
    rec = project / REC
    said = _around(project, rec.unlink, capsys)
    assert rec.read_text() == RECORD
    assert "kept at" not in said["reason"] and "could not be kept" not in said["reason"]


def test_a_command_that_changes_nothing_says_nothing(project, capsys):
    assert _around(project, lambda: None, capsys) == {}


def test_a_file_created_where_there_was_none_is_left(project, capsys):
    """Setting a project up writes the file for the first time; with no folders named, nothing
    is said about it here, as before."""
    rec = project / REC
    rec.unlink()
    said = _around(project, lambda: rec.write_text(RECORD), capsys)
    assert rec.read_text() == RECORD
    assert "not asked first" not in json.dumps(said)


def test_when_the_command_s_version_cannot_be_kept_that_is_said(project, capsys, monkeypatch):
    rec = project / REC

    def refuse(*_a, **_k):
        raise PermissionError("no")

    def act():
        rec.write_text(NEW_BAR)
        monkeypatch.setattr(bsg, "_keep", refuse)

    said = _around(project, act, capsys)
    assert rec.read_text() == RECORD
    assert "The command's version could not be kept" in said["reason"]


def test_when_the_file_cannot_be_read_that_is_said_and_nothing_is_put_back(project, capsys):
    rec = project / REC

    copy = project / bsg.STATE_REL / bsg.GUARD_SNAP / "call-1" / bsg.RECORD_SNAP

    def act():
        rec.write_text(NEW_BAR)
        copy.chmod(0)  # the copy from before the command can no longer be read

    try:
        said = _around(project, act, capsys)
    finally:
        if copy.exists():
            copy.chmod(0o600)
    assert rec.read_text() == NEW_BAR
    assert "could not be read (PermissionError)" in said["reason"]
    assert "nothing was put back" in said["systemMessage"]


def test_a_file_that_no_longer_parses_is_put_back_and_said(project, capsys):
    rec = project / REC
    said = _around(project, lambda: rec.write_text("active_diamonds: [not closed\n"), capsys)
    assert rec.read_text() == RECORD
    assert "does not parse as the command left it" in said["reason"]


# ---------------------------------------------------------------- what is not put back


SCRIPTS = PLUGIN / "scripts"


@pytest.mark.parametrize("command", [
    f"python3 {SCRIPTS}/derive_closing_path.py --project-dir . --diamond-id l1-strategy --write",
    f'python3 "{SCRIPTS}/migrate_phase.py" --project-dir .',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/derive_closing_path.py" --diamond-id l1 --write',
    "python3 $CLAUDE_PLUGIN_ROOT/scripts/migrate_phase.py",
])
def test_mycelium_s_own_writers_run_on_their_own_are_not_put_back(project, capsys, command):
    rec = project / REC
    said = _around(project, lambda: rec.write_text(NEW_BAR), capsys, command=command)
    assert rec.read_text() == NEW_BAR and "not asked first" not in json.dumps(said)


@pytest.mark.parametrize("command", [
    f"python3 {SCRIPTS}/migrate_phase.py && python3 tool.py",
    # The name alone: a script of the agent's own, called what Mycelium's writer is called.
    "python3 /tmp/elsewhere/derive_closing_path.py --write",
    "python3 scripts/derive_closing_path.py --write",
])
def test_anything_else_called_an_own_writer_is_put_back(project, capsys, command):
    rec = project / REC
    _around(project, lambda: rec.write_text(NEW_BAR), capsys, command=command)
    assert rec.read_text() == RECORD


def test_with_the_person_s_override_on_nothing_is_put_back(project, capsys, monkeypatch):
    monkeypatch.setenv("MYCELIUM_GUARD_STATE_EDIT", "1")
    rec = project / REC
    _around(project, lambda: rec.write_text(NEW_BAR), capsys)
    assert rec.read_text() == NEW_BAR


def test_git_restoring_the_committed_version_is_not_put_back(repo, capsys):
    """`git checkout -- <file>`, which Mycelium's own gates suggest for a broken file."""
    rec = repo / REC
    rec.write_text(NEW_BAR)  # an earlier change, made before this command
    said = _around(repo, lambda: _git(repo, "checkout", "--", REC), capsys,
                   command=f"git checkout -- {REC}")
    assert rec.read_text() == RECORD and "not asked first" not in json.dumps(said)


def test_git_moving_to_another_commit_is_not_put_back(repo, capsys):
    """A pull or a reset brings a version committed elsewhere; it is history, not a write."""
    rec = repo / REC
    first = _git(repo, "rev-parse", "HEAD")
    rec.write_text(NEW_BAR)
    _git(repo, "commit", "-q", "-am", "new bar")
    later = _git(repo, "rev-parse", "HEAD")
    _git(repo, "reset", "-q", "--hard", first)
    said = _around(repo, lambda: _git(repo, "reset", "-q", "--hard", later), capsys,
                   command=f"git reset --hard {later}")
    assert rec.read_text() == NEW_BAR and "not asked first" not in json.dumps(said)


def test_a_commit_the_command_made_of_its_own_change_does_not_count_as_git(repo, capsys):
    """Control: writing the file and committing it in one command leaves it equal to HEAD."""
    rec = repo / REC

    def act():
        rec.write_text(NEW_BAR)
        _git(repo, "commit", "-q", "-am", "new bar")

    said = _around(repo, act, capsys)
    assert rec.read_text() == RECORD
    assert "you were not asked first" in said["reason"]


def test_a_stash_pop_is_put_back_and_the_popped_version_kept(repo, capsys):
    """Said in the docstring as a cost: the person's own stashed changes come back through the
    shell like any other write. Nothing is lost: the popped version is kept and named."""
    rec = repo / REC
    rec.write_text(NEW_BAR)
    _git(repo, "stash", "-q")
    said = _around(repo, lambda: _git(repo, "stash", "pop", "-q"), capsys,
                   command="git stash pop")
    assert rec.read_text() == RECORD
    kept = said["reason"].split("The command's version is kept at ")[1].split(". ")[0]
    assert (repo / kept).read_text() == NEW_BAR


def test_a_merge_stopped_on_a_conflict_is_left(repo, capsys):
    rec = repo / REC
    merging = "<<<<<<< HEAD\n" + RECORD + "=======\n" + NEW_BAR + ">>>>>>> other\n"

    def act():
        (repo / ".git" / "MERGE_HEAD").write_text(_git(repo, "rev-parse", "HEAD") + "\n")
        rec.write_text(merging)

    _around(repo, act, capsys, command="git merge other")
    assert rec.read_text() == merging


# ---------------------------------------------------------------- through the real hook


def test_through_the_hook_as_the_runtime_calls_it(project):
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase()}

    def hook(mode: str) -> str:
        done = subprocess.run(["bash", str(PLUGIN / "hooks" / "bash-state-guard.sh"), mode],
                              input=json.dumps(_payload(project)), text=True,
                              capture_output=True, env=env, cwd=project, timeout=60, check=False)
        assert done.returncode == 0, done.stderr[:300]
        return done.stdout.strip()

    assert hook("pre") == ""
    (project / REC).write_text(NEW_BAR)
    said = json.loads(hook("post"))
    assert "(l1-strategy)" in said["systemMessage"] and (project / REC).read_text() == RECORD
