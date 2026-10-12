"""A decision the person made is kept in git, or they are told that it is not (v0.322.2).

WHAT WAS WRONG. The ignore file Mycelium writes into `.claude/state/` keeps a few files IN git,
"because these record a DECISION the user made ... and a fresh clone should not be asked again".
The person's own override of a scale lock (0.245.0) was not among them, so it was ignored: a fresh
clone, or a second machine, had the lock closed again with no record that it was ever opened.
Found 2026-10-12 while listing state files for the privacy page; the maintainer, shown it: "not
intentional to my knowledge".

WHAT HOLDS NOW. The rules keep it. And because an ignore file that exists is never rewritten
(`test_state_ignore.py`), a project whose file was written before a name joined the rules still
ignores that decision: session start now says so, with the line to add, and touches nothing.

The file names are built from parts so that this file's own text is not a write to guard state.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import _scratch_git

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
_spec = importlib.util.spec_from_file_location("_state_dir", SCRIPTS / "_state_dir.py")
sd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sd)
sys.path.insert(0, str(SCRIPTS))
import advisory_ledger  # noqa: E402

LOCK_ACK = "scale-lock" + "-ack"
SKIP_ACK = "discovery-skip" + "-ack"
MARK = "DECISION FILE NOT IN GIT"
#: The rules as every release from 0.318.0 to 0.322.1 wrote them.
RULES_BEFORE = ("*\n!.gitignore\n!README.md\n!" + SKIP_ACK + "\n!brownfield" + "-ack\n"
                "!delivery-skip" + "-ack\n!upstream.json\n")
#: What `/mycelium:setup` wrote from 0.226.0: no ack is kept at all.
RULES_OLDEST = "*\n!.gitignore\n!README.md\n!upstream.json\n"


def _project(tmp_path: Path, rules: str | None, *files: str, git: bool = True) -> Path:
    project = tmp_path / "proj"
    state = project / ".claude" / "state"
    state.mkdir(parents=True)
    if git:
        _scratch_git.init(project)
    if rules is not None:
        (state / ".gitignore").write_text(rules)
    for name in files:
        (state / name).write_text("l3-a L3 2026-10-12 mine, in my own words\n")
    return project


# ---------------------------------------------------------------- the rules


def test_the_rules_keep_the_scale_lock_override():
    """RED BEFORE 0.322.2: the one decision file the rules left out."""
    rules = (SCRIPTS / "state-gitignore.txt").read_text().splitlines()
    assert "!" + LOCK_ACK in rules


def test_a_new_project_keeps_it_out_of_the_ignored_set(tmp_path):
    project = _project(tmp_path, None, LOCK_ACK)
    sd.write_ignore(project / ".claude" / "state")
    assert sd.ignored_decisions(project) == ([], "")
    seen = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=project, text=True,
                          capture_output=True, check=True, env=_scratch_git.clean_env()).stdout
    assert LOCK_ACK in seen, "git does not offer the override for commit"


def test_the_decision_files_are_read_from_the_rules():
    """One list. A name added to the rules is checked here without a second edit."""
    names = sd.decision_files()
    assert {LOCK_ACK, SKIP_ACK, "upstream.json"} <= set(names)
    assert ".gitignore" not in names and "README.md" not in names


# ---------------------------------------------------------------- an ignore file that exists


def test_an_older_ignore_file_that_ignores_the_override_is_said(tmp_path):
    """RED BEFORE 0.322.2: nothing said it, and nothing could: the function did not exist."""
    project = _project(tmp_path, RULES_BEFORE, LOCK_ACK)
    line = sd.ignored_decisions_line(project)
    assert line.startswith(MARK)
    assert f".claude/state/{LOCK_ACK}" in line and f"`!{LOCK_ACK}`" in line
    assert "theirs to decide" in line                        # the commit is the person's


def test_every_ignored_decision_is_named(tmp_path):
    """The oldest setup-written file keeps no ack at all, so the first-file answer is lost too."""
    project = _project(tmp_path, RULES_OLDEST, LOCK_ACK, SKIP_ACK, "upstream.json")
    ignored, note = sd.ignored_decisions(project)
    assert sorted(ignored) == sorted([LOCK_ACK, SKIP_ACK]) and note == ""
    line = sd.ignored_decisions_line(project)
    assert f"`!{LOCK_ACK}`" in line and f"`!{SKIP_ACK}`" in line and "ignores them" in line


def test_the_ignore_file_is_not_touched(tmp_path):
    """Telling is the whole fix for a file that exists: a person's own edits to it stand."""
    project = _project(tmp_path, RULES_BEFORE + "# my own line\nscratch-*.md\n", LOCK_ACK)
    before = (project / ".claude" / "state" / ".gitignore").read_text()
    assert sd.ignored_decisions_line(project).startswith(MARK)
    assert (project / ".claude" / "state" / ".gitignore").read_text() == before


# ---------------------------------------------------------------- what must stay quiet


def test_control_a_decision_that_is_already_tracked_is_not_reported(tmp_path):
    project = _project(tmp_path, RULES_BEFORE, LOCK_ACK)
    subprocess.run(["git", "add", "-f", f".claude/state/{LOCK_ACK}"], cwd=project, check=True,
                   env=_scratch_git.clean_env(), capture_output=True)
    assert sd.ignored_decisions(project) == ([], "")


def test_control_a_decision_file_that_does_not_exist_is_not_reported(tmp_path):
    assert sd.ignored_decisions(_project(tmp_path, RULES_OLDEST)) == ([], "")


def test_control_a_folder_that_is_no_repository_is_not_reported(tmp_path):
    assert sd.ignored_decisions(_project(tmp_path, RULES_BEFORE, LOCK_ACK, git=False)) == ([], "")


def test_control_ignoring_all_of_dot_claude_is_the_persons_choice(tmp_path):
    """A root rule that leaves Mycelium's whole folder out of git is not ours to argue with, and
    a line in the state folder's file would not change it."""
    project = _project(tmp_path, None, LOCK_ACK)
    sd.write_ignore(project / ".claude" / "state")
    (project / ".gitignore").write_text(".claude/\n")
    assert sd.ignored_decisions(project) == ([], "")


def test_control_the_rules_themselves_report_nothing(tmp_path):
    project = _project(tmp_path, None, *sd.decision_files())
    sd.write_ignore(project / ".claude" / "state")
    assert sd.ignored_decisions_line(project) == ""


# ---------------------------------------------------------------- wiring


def test_the_cli_prints_the_line_and_creates_nothing(tmp_path):
    project = _project(tmp_path, RULES_BEFORE, LOCK_ACK)
    done = subprocess.run([sys.executable, str(SCRIPTS / "_state_dir.py"), "--project-dir",
                           str(project), "--ignored-decisions"], capture_output=True, text=True,
                          check=False)
    assert done.returncode == 0 and done.stdout.startswith(MARK)
    bare = tmp_path / "bare"
    bare.mkdir()
    done = subprocess.run([sys.executable, str(SCRIPTS / "_state_dir.py"), "--project-dir",
                           str(bare), "--ignored-decisions"], capture_output=True, text=True,
                          check=False)
    assert done.returncode == 0 and done.stdout == ""
    assert not (bare / ".claude").exists(), "asking must not create the state folder"


def test_session_start_asks_and_the_ledger_knows_the_line(tmp_path):
    """A reminder session start cannot emit, or one the advisory ledger cannot count, is the
    built-but-not-wired shape."""
    hook = (PLUGIN / "hooks" / "session-start.sh").read_text()
    assert "_state_dir.py" in hook and "--ignored-decisions" in hook
    line = sd.ignored_decisions_line(_project(tmp_path, RULES_BEFORE, LOCK_ACK))
    assert "decision-file-not-in-git" in advisory_ledger.scan(line)
