"""Secrets are stopped at the commit and at the push, not at the write (v0.323.0).

WHAT WAS WRONG. Mycelium looked for secrets when the agent WROTE a file, with a short list of its
own. Replayed 2026-10-12: an unquoted `KEY=value` passed, an env file was treated like source
code, and nothing ever looked at what was staged or committed. The maintainer: "Don't let
passwords into the repo", at the commit, with an established scanner.

WHAT HOLDS NOW.
- A write is not scanned: the agent may put a key in a file. It may not commit or push one.
- The agent's `git commit` is scanned first (the index; with `-a` or a named path, the tracked
  files as on disk; since 0.337.4 with what a `git add` in the same command would stage). A
  finding refuses it.
- Since 0.337.4 a step Mycelium cannot account for, before a commit or push in the same command,
  refuses the command with nothing found.
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

sys.path.insert(0, str(Path(__file__).parent))
import _scratch_git  # noqa: E402

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
    _scratch_git.init(proj, "-b", "main")
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


SPELLINGS = ["/usr/bin/git {verb}", "env git {verb}", "/usr/bin/env git {verb}", "env LANG=C git {verb}",
             "timeout 60 git {verb}", "timeout -k 5 60 git {verb}", "nice -n 10 git {verb}",
             "sudo -u me git {verb}", "bash -c 'git {verb}'",
             "command /usr/bin/git {verb}"]


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_a_commit_spelled_by_path_or_behind_a_wrapper_word_is_scanned(project, spelling):
    """RED BEFORE 0.337.3. The pattern read `git` by name behind five wrapper words; `git` by
    path and `env`, `timeout`, `nice`, `xargs` in front got no answer (blind read of 0.337.2,
    2026-11-25, replayed)."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, spelling.format(verb="commit -m work"))) == "deny"


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_a_push_spelled_by_path_or_behind_a_wrapper_word_is_scanned(project, spelling):
    """RED BEFORE 0.337.3, and the half that mattered: a missed commit is scanned afterwards, a
    missed push has gone."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    git(project, "commit", "-q", "-m", "oops")
    out = gate(project, "Bash", {"command": spelling.format(verb="push origin main")})
    assert decision(out) == "deny" and "push is refused" in reason(out)


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_control_such_a_spelling_of_a_clean_commit_or_push_is_not_refused(project, spelling):
    assert decision(commit(project, spelling.format(verb="commit -m work"))) == "allow"
    out = gate(project, "Bash", {"command": spelling.format(verb="push origin main")})
    assert decision(out) == "allow"


@pytest.mark.parametrize("command", ["make release", "npm version patch", "./scripts/release.sh",
                                     "git ci -m work"])
def test_a_command_that_commits_or_pushes_inside_itself_is_not_seen_beforehand(project, command):
    """THE LIMIT, HELD AS A TEST SO IT CANNOT BE FORGOTTEN: no pattern over the command's text
    can know what a script, a make target or a git alias does. Such a commit is scanned after
    the command (the test further down); such a push is not seen. If this test goes red because
    one of these is now refused, the pages that state the limit need the same change."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, command)) == "allow"
    assert cs.read_command(command, str(project)) == {"commits": [], "pushes": [], "blocked": None}


# ---------------------------------------------------------------- vouch or refuse (0.337.4)
#
# WHAT WAS WRONG. The scan before a commit looked at the index as it was before the command ran.
# `git add -A && git commit -m work && git push` stages its key AFTER that look, so the key was
# committed and pushed with nothing having looked (blind read of 0.337.3, 2026-11-25, replayed).
# WHAT HOLDS NOW. The command is read step by step. A `git add` before the commit is replayed
# into a scratch index and that is scanned. A step Mycelium cannot account for, before a commit
# or a push in the same command, refuses the command with nothing found.

HEREDOC = "git add -A && git commit -m \"$(cat <<'EOF'\nwork; and && more\n\nEOF\n)\""
STAGED_BY_THE_COMMAND = [
    "git add -A && git commit -m work",
    "git add config.py && git commit -m work",
    "git add . && git commit -m work && git push",
    "git add -A; git commit -m work",
    "git stage -A && git commit -m work",
    "git status && git add -A && git commit -m work",
    "cd . && git add -- config.py && git commit -m work",
    "bash -c 'git add -A && git commit -m work && git push'",
    "git checkout -b topic && git add -A && git commit -m work",
    "if git add -A; then git commit -m work; fi",
    HEREDOC,
]


@pytest.mark.parametrize("command", STAGED_BY_THE_COMMAND)
@pytest.mark.parametrize("tracked", [False, True], ids=["a new file", "a tracked file"])
def test_a_key_the_same_command_stages_is_seen_before_the_commit(project, command, tracked):
    if tracked:
        (project / "config.py").write_text("x = 1\n")
        git(project, "add", "config.py")
        git(project, "commit", "-q", "-m", "config")
    (project / "config.py").write_text(LINE + "\n")
    out = commit(project, command)
    assert decision(out) == "deny", command
    assert "what its `git add` stages" in reason(out)
    assert git(project, "diff", "--cached", "--name-only") == "", "the real index was touched"


@pytest.mark.parametrize("command", STAGED_BY_THE_COMMAND)
def test_control_a_clean_add_and_commit_is_not_refused(project, command):
    (project / "config.py").write_text("y = 2\n")
    assert decision(commit(project, command)) == "allow", command
    assert git(project, "diff", "--cached", "--name-only") == "", "the real index was touched"
    assert not list(project.parent.glob("mycelium-index-*")), "a scratch index was left behind"


def test_control_only_what_the_add_names_is_scanned(project):
    """A key in a file the command does not stage does not stop a commit of another file."""
    (project / "local-notes.py").write_text(LINE + "\n")
    (project / "notes.txt").write_text("nothing secret\n")
    assert decision(commit(project, "git add notes.txt && git commit -m work")) == "allow"
    assert decision(commit(project, "git add -A && git commit -m work")) == "deny"


@needs_gitleaks
def test_gitleaks_reads_what_the_add_would_stage(project):
    token = "gh" + "p_" + "R4nd0mT0k3nV4lu3" + "F0rT3st1ngPurp0s3s00"
    (project / "config.py").write_text(f'TOKEN = "{token}"\n')
    out = commit(project, "git add -A && git commit -m work && git push", path=WITH_SCANNER)
    assert decision(out) == "deny" and "config.py:1" in reason(out)
    assert token not in json.dumps(out)
    (project / "config.py").write_text("y = 2\n")
    assert decision(commit(project, "git add -A && git commit -m work",
                           path=WITH_SCANNER)) == "allow"


@pytest.mark.parametrize("command", [
    "if git commit -m work; then git push; fi",
    "{ git commit -m work; }",
    "! git commit -m work",
    "until git commit -m work; do sleep 1; done",
    "(git commit -m work)",
    "true && { git commit -m work; }",
])
def test_a_commit_behind_a_shell_keyword_or_a_bracket_is_scanned(project, command):
    """Until 0.337.4 none of these was read as a commit at all."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, command)) == "deny", command
    git(project, "reset", "-q")
    (project / "config.py").write_text("y = 2\n")
    git(project, "add", "config.py")
    assert decision(commit(project, command)) == "allow", command


@pytest.mark.parametrize(("command", "verb"), [
    ("make build && git commit -m work", "commit"),
    ("./scripts/release.sh; git push", "push"),
    ("echo k > config.py && git add config.py && git commit -m work", "commit"),
    ("python3 gen.py && git add -A && git commit -m work && git push", "commit"),
    ("git add -f secrets/ && git commit -m work", "commit"),
    ("sudo git add -A && sudo git commit -m work", "commit"),
    ("HOME=/tmp/elsewhere git add -A && git commit -m work", "commit"),
    ("git switch main && git add . && git commit -m work && git push", "commit"),
    ("git pull -q && git add -A && git commit -m work", "commit"),
    ("git rm -q .gitignore && git add -A && git commit -m work", "commit"),
    ("XDG_CONFIG_HOME=/nonexistent; git add -A; git commit -m work", "commit"),
    ("git add $FILES && git commit -m work", "commit"),
    ("git add $(echo -f .env) && git commit -m work", "commit"),
    ("git add --forc .env && git commit -m work", "commit"),
    ("git pull -q sibling main && git push", "push"),
    ("cat .env >&2notes; git add 2notes; git commit -m work", "commit"),
    ("git init && git add -A && git commit -m first", "commit"),
    ("git commit -m work && npm test && git push", "push"),
    ("git stash pop && git commit -am work", "commit"),
    ("git checkout stash@{0} -- config.py && git commit -m work", "commit"),
    ('cd "$WHERE" && git commit -m work', "commit"),
    ("for f in a b; do git add $f; done; git commit -m work", "commit"),
    ("tee notes.txt < /dev/null | git commit -m work", "commit"),
    ("git status > status.txt; git commit -m work", "commit"),
])
def test_a_step_that_cannot_be_accounted_for_before_a_commit_or_push_refuses(project, command,
                                                                              verb):
    """Nothing is staged and nothing is wrong: the refusal is that Mycelium cannot say what the
    commit or push would take once the earlier step has run. It says so, and what to do."""
    out = commit(project, command)
    assert decision(out) == "deny", command
    assert f"before its `git {verb}`" in reason(out), reason(out)
    assert "Nothing was found" in reason(out) and "a command of its own" in reason(out)


@pytest.mark.parametrize("command", [
    "GIT_INDEX_FILE=/tmp/other-index git commit -m work",
    "GIT_DIR=/tmp/elsewhere/.git git push",
    "git --git-dir=/tmp/elsewhere/.git commit -m work",
    'git -C "$WHERE" commit -m work',
])
def test_a_commit_or_push_that_names_another_index_or_repository_refuses(project, command):
    out = commit(project, command)
    assert decision(out) == "deny", command
    assert "cannot follow how" in reason(out) and "another repository or index" in reason(out)


def test_a_command_whose_text_cannot_be_followed_refuses_when_it_commits(project):
    out = commit(project, 'git commit -m "work')
    assert decision(out) == "deny" and "could not follow its text" in reason(out)
    out = commit(project, r"bash -c $'git add -f .env\x3b git commit -m work'")
    assert decision(out) == "deny" and "could not follow its text" in reason(out)
    assert decision(commit(project, 'echo "work')) == "allow", "no commit, so nothing to refuse"


@pytest.mark.parametrize("command", [
    "git commit -m work && npm test",
    "git commit -m work; ./deploy.sh",
    "git commit -m 'fix; make build && ship' && git push",
    "git commit -m \"$(cat <<'EOF'\nfix: make build; ./run.sh && more\nEOF\n)\"",
    "git diff --stat | cat; git commit -m work",
    "echo committing 2>&1 && git commit -m work 2>&1 | tail -3",
    "git checkout -b topic && git commit -m work",
    "git switch main && git pull && git push",
    "git config user.name t && git commit -m work  # make build",
    "cd . && git log --oneline | head -3 && git push > /dev/null",
])
def test_control_steps_that_are_accounted_for_do_not_refuse(project, command):
    (project / "app.py").write_text("x = 2\n")
    git(project, "add", "app.py")
    assert decision(commit(project, command)) == "allow", command


def test_a_folder_changed_inside_brackets_does_not_move_the_scan(project, tmp_path):
    """`(cd other)` changes folder for the bracket only. The commit after it is the project's."""
    other = tmp_path / "other"
    other.mkdir()
    _scratch_git.init(other, "-b", "main")
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    out = commit(project, f"(cd {other} && git status); git commit -m work")
    assert decision(out) == "deny" and str(project.resolve()) in reason(out)
    assert decision(commit(project, f"(cd {other} && git commit -m work)")) == "allow"


@pytest.mark.parametrize("command", [
    "uv run git commit -am work",
    "gtimeout 60 git push",
    "direnv exec . git commit -m work",
    r"find . -name app.py -exec git commit -m work {} \;",
    "git diff --name-only | xargs git commit -m work",
    "xargs git push",
    "git --git-dir .git --work-tree . commit -am work",
    "env GIT_INDEX_FILE=.git/alt git commit -m work",
    "bash <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    "cat <<'EOF' | bash\ngit add -A\ngit commit -m work\ngit push\nEOF",
    'echo "git add -A && git commit -m work" | sh',
    "python3 -c \"import os; os.system('git commit -am work')\"",
])
def test_git_run_by_another_program_or_from_handed_text_refuses(project, command):
    """Found by an independent read of this change before it was released (2026-11-25), each
    proven by running it: none of these was scanned and none was refused."""
    out = commit(project, command)
    assert decision(out) == "deny", command
    assert "cannot follow how" in reason(out) and "Nothing was found" in reason(out)


@pytest.mark.parametrize("command", [
    "git diff --name-only | xargs git add && git commit -m work",
    "cd nowhere-at-all; git add -A; git commit -m work",
    "cd pro* && git add -A && git commit -m work",
    "cat .env >& notes.txt; git commit -am work",
    "sort -o notes.txt .env && git commit -am work",
    "uniq .env notes.txt && git commit -am work",
    "git diff --no-index --output=notes.txt /dev/null .env; git commit -am work",
    "git pull -q ../sibling main && git push",
    "git fetch -q ../sibling main:feature && git push origin feature",
    "git branch wip 'stash@{0}' && git push origin wip",
    "git checkout 'stash@{0}' && git push origin HEAD:refs/heads/wip",
    "git config core.worktree ../elsewhere && git add -A && git commit -m work",
    "echo \\ # ; cp .env notes.txt; git commit -am work",
])
def test_more_steps_that_are_not_accounted_for_refuse(project, command):
    out = commit(project, command)
    assert decision(out) == "deny", command
    assert "before its `git" in reason(out), reason(out)


@pytest.mark.parametrize("command", [
    "git stash push -m wip", "git revert --no-commit HEAD", "git config push.default current",
    "git help commit", "git reset --soft HEAD~1  # undo the last commit",
    "git show --stat HEAD > /tmp/commit.txt", "chmod +x .git/hooks/pre-commit",
    "rg -n 'git push' docs/", "sed -n '/git commit/p' README.md",
    "gh pr create --title 'Fix git push scan' --body 'git commit now refuses'",
    "cat > CONTRIBUTING.md <<'EOF'\nRun git commit, then git push.\nEOF",
    "echo 'run git push when done' >> notes.txt",
    "git log --oneline | awk '{print $1}'  # then git commit",
    "bash build.sh", "npm test",
    "awk '/git commit -m/' README.md", "python3 scripts/check.py --pattern 'git commit -m'",
    "find . -name '*.md' -exec grep -l 'git push' {} +", "git notes add -m 'git push pending'",
    "git stash push -m 'git commit wip'", "git log --grep 'git push' > out.txt",
])
def test_control_a_command_that_neither_commits_nor_pushes_is_never_refused(project, command):
    """A second independent read (2026-11-25) found a draft of this change refusing each of
    these, because the words stood somewhere in the text."""
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, command)) == "allow", command


@pytest.mark.parametrize("command", [
    "git -C pro* commit -am work",
    "/bin/bash <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    "cat <<'EOF' | /bin/sh\ngit add -A\ngit commit -m work\ngit push\nEOF",
    "bash -c \"$(cat <<'EOF'\ngit add -A\ngit commit -m work\nEOF\n)\"",
    "CMD='git add -A && git commit -m work'; eval \"$CMD\"",
    "bash /dev/stdin <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    "bash -s -- x <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    "source /dev/stdin <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    "python3 - <<'EOF'\nimport os\nos.system('git add -A && git commit -m work')\nEOF",
    "ssh host 'cd repo && git push'",
    "bash 2>&1 <<'EOF'\ngit add -A\ngit commit -m work\nEOF",
    'echo "git add -A && git commit -m work" | sh >/dev/null 2>&1',
    "python3 2>&1 <<'EOF'\nimport os\nos.system('git add -A && git commit -m work')\nEOF",
    "uv run sh -c 'if true; then git commit -am work; fi'",
    "direnv exec . sh -c '/usr/bin/git commit -am work'",
    'source <(echo "git add -A && git commit -m work")',
    "git -c alias.ship='!git add -A && git commit -m work' ship",
    "env -C ../other git commit -am work",
    "git push origin $(git rev-parse 'stash@{0}'):refs/heads/wip",
    "git -c core.worktree=../other commit -am work",
    "git -c user.name=\"A & B\" commit -m one; bash <<'EOF'\ngit add -f .env\ngit commit -m two\nEOF",
])
def test_more_forms_mycelium_cannot_follow_refuse(project, command):
    out = commit(project, command)
    assert decision(out) == "deny" and "cannot follow how" in reason(out), command


def test_a_commit_option_cut_short_is_read_as_wider(project):
    (project / "app.py").write_text(LINE + "\n")
    (project / "list.txt").write_text("app.py\n")
    assert decision(commit(project, "git commit --pathspec-from=list.txt -m work")) == "deny"


def test_a_step_put_in_the_background_beside_a_commit_refuses(project):
    out = commit(project, "sleep 1 && git commit -am work & cp .env notes.txt; wait")
    assert decision(out) == "deny" and "at the same time" in reason(out)
    out = commit(project, "{ sleep 1; git commit -am work; } | cp .env notes.txt")
    assert decision(out) == "deny" and "at the same time" in reason(out)
    assert decision(commit(project, "git push |& tail -3")) == "allow"
    assert decision(commit(project, "git push --dry-run 2>&1 | tee push.log")) == "allow"
    assert decision(commit(project, "sleep 1 & echo started")) == "allow"


@pytest.mark.parametrize("command", [
    "git add **/*.py && git commit -m work",
    "git add *.py && git commit -m work",
    "git add {config,app}.py && git commit -m work",
    "bash -c $'git add -A\\ngit commit -m work'",
    "git add -A && git commit -F <(echo work)",
])
def test_an_add_the_shell_may_widen_is_replayed_as_everything(project, command):
    (project / "config.py").write_text(LINE + "\n")
    assert decision(commit(project, command)) == "deny", command


@pytest.mark.parametrize("command", [
    'git commit -m"first draft" -a',
    "git commit -mwork -a",
    "git commit --pathspec-from-file=list.txt -m work",
    "git commit -m work --pathspec-from-file list.txt",
    "git commit -F <(echo work) -a",
    "git commit -qam work",
])
def test_a_commit_that_takes_tracked_files_is_read_as_wider_however_written(project, command):
    (project / "app.py").write_text(LINE + "\n")
    (project / "list.txt").write_text("app.py\n")
    assert decision(commit(project, command)) == "deny", command


@pytest.mark.parametrize(("words", "wider"), [
    (["-m", "x"], False), (["-mfirst draft", "-a"], True), (["-am", "x"], True),
    (["-m", "-a"], False), (["--amend", "--no-edit"], False), (["-C", "HEAD", "f.py"], True),
    (["--pathspec-from-file=l"], True), (["-qm", "x", "--", "."], True), (["-F", "-"], False),
])
def test_what_a_commit_takes(words, wider):
    assert cs._takes_more(words) is wider


def _unpushed_key_off_any_branch(project: Path, tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    git(project, "clone", "-q", "--bare", str(project), str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "push", "-q", "-u", "origin", "main")
    git(project, "checkout", "-q", "--detach")
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    git(project, "commit", "-q", "-m", "by hand")


@pytest.mark.parametrize("command", [
    "git push origin HEAD:refs/heads/wip",
    "git switch -c wip && git push -u origin wip",
    "git tag v1 && git push origin v1",
])
def test_a_push_of_a_commit_that_is_on_no_branch_is_scanned(project, tmp_path, command):
    """Until 0.337.4 the scan before a push read local branches only."""
    _unpushed_key_off_any_branch(project, tmp_path)
    out = commit(project, command)
    assert decision(out) == "deny" and "on no remote yet" in reason(out), command


def test_a_push_that_names_a_stash_is_scanned_and_a_stash_alone_stops_nothing(project, tmp_path):
    remote = tmp_path / "remote.git"
    git(project, "clone", "-q", "--bare", str(project), str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "push", "-q", "-u", "origin", "main")
    (project / "app.py").write_text(LINE + "\n")
    git(project, "stash")
    assert decision(commit(project, "git push")) == "allow", "a stash is not what a push sends"
    assert decision(commit(project, "git push origin 'stash@{0}:refs/heads/wip'")) == "deny"


@pytest.mark.parametrize("command", [
    "GIT_EDITOR=true git commit --amend",
    "GIT_AUTHOR_DATE=2020-01-01T00:00:00 git commit -m work",
    "GIT_SSH_COMMAND='ssh -i key' git push",
    "git commit -F - <<< 'work'",
    "git rm -q --cached app.py && git commit -m work",
    "git switch main && git pull && git push",
    "git pull --rebase origin main && git push",
    "git tag v2 && git push origin v2",
    "git switch -c topic && git commit -m work && git push -u origin topic",
    "git pull origin feature/x && git push",
    "git tag -a v1.0 -m 'Release 1.0' && git push origin v1.0",
    "git fetch origin && git rebase main && git push --force-with-lease",
    "git restore --staged app.py && git commit -m work",
    "git branch -d old && git push origin --delete old",
    "git ls-files -o --exclude-standard && git add -A && git commit -m work",
    "GIT_LFS_SKIP_SMUDGE=1 git push",
    "git commit -m 'docs: explain git push flow' && gh pr create --fill",
    "git commit -m 'fix git commit hook' && npm test",
    "git mv app.py main.py && git commit -m work",
    "mkdir -p docs && git commit -am work",
    "git merge --no-edit main && git push",
])
def test_control_ordinary_forms_the_first_draft_refused_are_let_through(project, command):
    git(project, "remote", "add", "origin", str(project))
    assert decision(commit(project, command)) == "allow", command


@pytest.mark.parametrize(("command", "expect"), [
    ("git add -A && git commit -m x", ["git add -A", "git commit -m x"]),
    ("a; b | c\nd & e && f", ["a", "b", cs._PIPE, "c", "d", cs._BACKGROUND, "e", "f"]),
    ("echo 'a; b' \"c && d\"", ["echo 'a; b' \"c && d\""]),
    ("x 2>&1 && y &> out", ["x 2>&1", "y &> out"]),
    ('git commit -m "$(date)"', [cs._OPEN, "date", cs._CLOSE, 'git commit -m "$SUB"']),
    ("(cd a; b)", [cs._OPEN, "cd a", "b", cs._CLOSE]),
    ("cat <<'EOF' > f\n$(rm -rf x); y\nEOF\nz", ["cat   > f", "z"]),
    ("a # b; c\nd", ["a", "d"]),
    ("a \\\n b", ["a  b"]),
])
def test_a_command_is_read_into_its_steps(command, expect):
    assert cs.steps(command) == expect


@pytest.mark.parametrize("command", ["echo 'open", 'echo "open', "echo $(open", "cat <<EOF\nopen",
                                     "cat <<EOF\n$(date)\nEOF", "echo ${x:-$(date)}"])
def test_a_command_that_cannot_be_followed_says_so(command):
    with pytest.raises(cs.UnreadableError):
        cs.steps(command)


@pytest.mark.parametrize(("part", "expect"), [
    ("git commit -m x", ("commit", "/w", False)),
    ("git commit -am x", ("commit", "/w", True)),
    ("then /usr/bin/git -C sub push -u origin x", ("push", "/w/sub", ["-u", "origin", "x"])),
    ("/usr/bin/env git commit -m x", ("commit", "/w", False)),
    ("uv run git commit -m x", ("unknown",)),
    ("xargs git add", ("unknown",)),
    ("GIT_EDITOR=true git commit --amend", ("commit", "/w", False)),
    ("GIT_DIR=x git commit", ("unknown",)),
    ("git add *.py", ("add", "/w", None)),
    ("git pull", ("moves",)),
    ("git mv a b", ("moves",)),
    ("sudo git add -A", ("unknown",)),
    ("HOME=/tmp git add -A", ("unknown",)),
    ("/bin/bash", ("fed",)),
    ("bash -s -- x", ("fed",)),
    ("source /dev/stdin", ("fed",)),
    ("python3 -", ("fed",)),
    ("python3 -c 'print(1)'", ("unknown",)),
    ('bash -c "$SUB"', ("fed",)),
    ('eval "$CMD"', ("fed",)),
    ("git pull ../other main", ("unknown",)),
    ("git switch -c topic", ("quiet",)),
    ("git switch -c topic stash@{0}", ("unknown",)),
    ("git checkout main", ("unknown",)),
    ("git config user.name t", ("quiet",)),
    ("git config core.worktree /x", ("unknown",)),
    ("sort -o f g", ("unknown",)),
    ("cat a >& b", ("unknown",)),
    ("cat a 2>&1", ("quiet",)),
    ("LANG=C env git add -A", ("unknown",)),
    ("command git add -A", ("add", "/w", ["-A"])),
    ("git add $F", ("unknown",)),
    ("git push origin $B", ("unknown",)),
    ("env -C ../other git commit -m x", ("unknown",)),
    ("git -C pro* commit -m x", ("unknown",)),
    ("git -c core.worktree=/x commit -m x", ("unknown",)),
    ("git -c user.name=t commit -m x", ("commit", "/w", False)),
    ("git stash push -m wip", ("unknown",)),
    ("bash", ("fed",)),
    ("bash build.sh", ("unknown",)),
    ("source ./env.sh", ("unknown",)),
    ("python3 scripts/check.py", ("unknown",)),
    ("git add -Af", ("unknown",)),
    ("git add --patch", ("unknown",)),
    ("cd sub", ("cd", "/w/sub")),
    ("cd -", ("unknown",)),
    ("bash -lc 'git push'", ("run", "git push")),
    ("eval git push", ("run", "git push")),
    ("echo hi", ("quiet",)),
    ("echo hi > f", ("unknown",)),
    ("echo hi > /dev/null", ("quiet",)),
    ("git status", ("quiet",)),
    ("git checkout -b topic", ("quiet",)),
    ("git checkout main -- f", ("unknown",)),
    ("git reset --hard", ("unknown",)),
    ("git ci -m x", ("unknown",)),
    ("timeout 60 make release", ("unknown",)),
    ("fi", ("quiet",)),
])
def test_what_one_step_is(part, expect):
    assert cs.step_kind(part, "/w") == expect


def test_control_a_command_that_only_mentions_the_words_is_not_scanned(project):
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project, "echo 'remember to git commit later'")) == "allow"
    assert decision(commit(project, "git log --grep=commit")) == "allow"


def test_a_commit_in_another_repository_is_scanned_there(project, tmp_path):
    """The agent often works in one repository and commits in another: `cd other && git commit`,
    or `git -C other commit`. The scan follows the folder the command names."""
    other = tmp_path / "other"
    other.mkdir()
    _scratch_git.init(other, "-b", "main")
    (other / "config.py").write_text(LINE + "\n")
    git(other, "add", "config.py")
    for command in (f"cd {other} && git commit -m work", f"git -C {other} commit -m work",
                    f"cd {tmp_path} && cd other && git commit -m work"):
        out = commit(project, command)
        assert decision(out) == "deny" and str(other.resolve()) in reason(out), command
    assert decision(commit(project)) == "allow", "the project's own index is clean"


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


OWN_HOOK = "#!/bin/sh\nexec gitleaks git --pre-commit --staged\n"
OWN_CONFIG = ("repos:\n  - repo: https://github.com/gitleaks/gitleaks\n    rev: v8.18.0\n"
              "    hooks:\n      - id: gitleaks\n")


def _own(project: Path, rel: str, text: str) -> None:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.mark.parametrize(("rel", "text"), [
    (".git/hooks/pre-commit", OWN_HOOK),
    (".pre-commit-config.yaml", OWN_CONFIG),
    (".pre-commit-config.yaml", "# TODO: maybe add gitleaks later\n"),
])
def test_a_file_that_names_the_scanner_does_not_switch_the_scan_off(project, rel, text):
    """CHANGED IN 0.337.2. From 0.323.0 a `hooks/pre-commit` or a `.pre-commit-config.yaml` that
    held the scanner's name switched this scan off for a commit that honours hooks. Neither file
    shows that a hook ran, and the agent may write both unasked (blind read of 0.337.1,
    2026-11-25). The README says of this stop that there is no switch for it."""
    _own(project, rel, text)
    (project / "config.py").write_text(LINE + "\n")
    git(project, "add", "config.py")
    assert decision(commit(project)) == "deny"
    assert decision(commit(project, "git commit --no-verify -m work")) == "deny"
    assert decision(commit(project, "git commit -nm work")) == "deny"


@pytest.mark.parametrize(("rel", "text"), [
    (".git/hooks/pre-commit", OWN_HOOK),
    (".pre-commit-config.yaml", OWN_CONFIG),
])
def test_control_a_clean_commit_beside_such_a_file_is_not_refused(project, rel, text):
    _own(project, rel, text)
    (project / "notes.txt").write_text("nothing secret\n")
    git(project, "add", "notes.txt")
    assert decision(commit(project)) == "allow"


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


# ---------------------------------------------------------------- the git hook setup offers


def test_the_git_hook_is_written_once_and_never_over_someone_elses(project, tmp_path, capsys):
    import install_git_secret_hook as ig
    hook = project / ".git" / "hooks" / "pre-commit"
    assert ig.main(["--project-dir", str(project), "--check"]) == 0 and not hook.exists()
    assert ig.main(["--project-dir", str(project)]) == 0
    assert "gitleaks git --pre-commit --staged" in hook.read_text() and os.access(hook, os.X_OK)
    assert ig.main(["--project-dir", str(project)]) == 0, "a second run is a no-op"
    assert "already runs gitleaks" in capsys.readouterr().out
    hook.write_text("#!/bin/sh\nnpm test\n")
    assert ig.main(["--project-dir", str(project)]) == 1
    assert hook.read_text() == "#!/bin/sh\nnpm test\n", "the person's own hook was changed"
    assert "add these lines" in capsys.readouterr().out
    assert ig.main(["--project-dir", str(tmp_path / "nowhere")]) == 2


def test_the_installed_hook_runs_and_does_not_block_without_a_scanner(project):
    import install_git_secret_hook as ig
    assert ig.main(["--project-dir", str(project)]) == 0
    done = subprocess.run(["sh", str(project / ".git" / "hooks" / "pre-commit")], cwd=project,
                          text=True, capture_output=True, env={"PATH": "/usr/bin:/bin"},
                          check=False)
    assert done.returncode == 0 and "not scanned" in done.stderr


def _their_hook_with_the_printed_lines(tmp_path, path_env):
    """The printed lines pasted at the top of a person's own hook, then that hook's own work."""
    import install_git_secret_hook as ig
    hook = tmp_path / "their-hook.sh"
    hook.write_text("#!/bin/sh\n" + ig.SCAN + "echo their own checks ran\n")
    return subprocess.run(["sh", str(hook)], cwd=tmp_path, text=True, capture_output=True,
                          env={"PATH": path_env}, check=False)


def test_the_printed_lines_do_not_refuse_a_commit_without_a_scanner(tmp_path):
    """Until 0.323.1 the printed line exited 1 when gitleaks was not installed, so a hook that
    carried it refused every commit on a machine without the scanner (dogfood 2026-10-13)."""
    done = _their_hook_with_the_printed_lines(tmp_path, "/usr/bin:/bin")
    assert done.returncode == 0, done.stderr
    assert "not scanned" in done.stderr and "their own checks ran" in done.stdout


@pytest.mark.parametrize(("scanner_exit", "goes_on"), [(0, True), (1, False)])
def test_the_printed_lines_stop_on_a_finding_and_go_on_without_one(tmp_path, scanner_exit, goes_on):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    scanner = bindir / "gitleaks"
    scanner.write_text(f"#!/bin/sh\nexit {scanner_exit}\n")
    scanner.chmod(0o755)
    done = _their_hook_with_the_printed_lines(tmp_path, f"{bindir}:/usr/bin:/bin")
    assert (done.returncode == 0) is goes_on
    assert ("their own checks ran" in done.stdout) is goes_on


def test_the_written_hook_and_the_printed_lines_are_one_block():
    import install_git_secret_hook as ig
    assert ig.HOOK.endswith(ig.SCAN)


def test_the_readme_says_where_a_key_is_stopped():
    """The maintainer's wording, chosen 2026-10-12. The sentence it replaces said a key going
    into a file is refused, which stopped being true in this release."""
    readme = (ROOT / "README.md").read_text()
    assert ("A key the agent has written into a file cannot be committed or pushed, and there is "
            "no switch for that one. What you commit yourself is not checked, unless you let "
            "setup add the check to git.") in readme
    # Added 0.337.3 on the maintainer's choice of 2026-11-25: the limit of the sentence above.
    assert ("A commit the agent makes from inside another command, a release script say, is "
            "checked right after and you are told. A push made that way gets through.") in readme
    assert "going into a file is refused outright" not in readme


def test_setup_offers_the_hook_and_never_installs_it_unasked():
    skill = (PLUGIN / "skills" / "setup" / "SKILL.md").read_text()
    assert "install_git_secret_hook.py" in skill
    assert "Never install it unasked" in skill


def test_the_entry_point_refuses_when_the_scan_itself_breaks(project, monkeypatch, capsys):
    def boom(*_args, **_kw):
        raise RuntimeError("simulated")
    monkeypatch.setattr(cs, "pre", boom)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO('{"tool_input": {}}'))
    assert cs.main(["--pre", "--project-dir", str(project)]) == 0
    assert "could not run" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("not json"))
    assert cs.main(["--project-dir", str(project)]) == 0
