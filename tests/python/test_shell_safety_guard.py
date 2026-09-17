"""G-V12 coverage proof for shell_safety_guard.py.

THE GAP IT CLOSES. Three shell traps have their own memory files in the dogfood
project, written after earlier incidents. All three were walked into anyway in a
single session — eight times — and one produced a wrong answer to the operator:
`which opencode | head -1; echo $?` reported `head`'s status, so the agent stated
a tool was not installed when the binary was merely absent from PATH.

Scenario-per-guardpost:
  happy — an ordinary command                       -> silence
  sad   — `$?` after a pipeline                     -> warn, names PIPESTATUS
  sad   — backticks                                 -> warn, names $(...) and heredocs
  sad   — grep gating an && chain                   -> warn, names grep's exit 1
  edge  — PIPESTATUS already used                   -> silence (author knows)
  edge  — backticks inside a QUOTED heredoc         -> silence (author knows)
  edge  — backticks inside an UNQUOTED heredoc      -> warn (it still expands)
  edge  — `$?` BEFORE any pipe                      -> silence
  edge  — `||` is not a pipe                        -> silence
  edge  — several traps in one command              -> several warnings
  bad   — unparseable hook payload                  -> silence, exit 0 (fail open)
  bad   — payload with no command                   -> silence, exit 0
"""

import json
import subprocess
import sys

import pytest

SCRIPT = "shell_safety_guard.py"


def _run(scripts_path, payload):
    return subprocess.run(
        [sys.executable, str(scripts_path / SCRIPT)],
        input=payload, capture_output=True, text=True, check=False,
    )


def _cmd(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _warnings(scripts_path, command):
    r = _run(scripts_path, _cmd(command))
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


# ---------------------------------------------------------------- happy


def test_ordinary_command_is_silent(scripts_path):
    assert _warnings(scripts_path, "git status --short") == ""


def test_pipeline_without_status_check_is_silent(scripts_path):
    """Pipes are normal. Only `$?` AFTER one is the trap."""
    assert _warnings(scripts_path, "grep -c foo file | wc -l") == ""


# ---------------------------------------------------------------- sad


def test_dollar_status_after_pipe_warns(scripts_path):
    """The exact command that produced the wrong opencode answer."""
    out = _warnings(scripts_path, 'which opencode | head -1; echo "rc=$?"')
    assert "PIPESTATUS" in out
    assert "last command in the pipeline" in out.lower()


def test_backticks_warn(scripts_path):
    out = _warnings(scripts_path, 'git commit -m "see `| head` for details"')
    assert "SC2006" in out
    assert "heredoc" in out.lower()


def test_grep_gating_an_and_chain_warns(scripts_path):
    out = _warnings(scripts_path, "grep -q needle file && echo found")
    assert "exits 1" in out
    assert "|| true" in out


# ---------------------------------------------------------------- edge


def test_pipestatus_present_suppresses_the_warning(scripts_path):
    """Using PIPESTATUS is the documented remedy; nagging about it would be
    the false-positive that gets a guard disabled."""
    assert _warnings(scripts_path, 'foo | head -1; echo "${PIPESTATUS[0]}"') == ""


def test_status_check_before_any_pipe_is_silent(scripts_path):
    """`$?` is only misleading when a pipeline precedes it."""
    assert _warnings(scripts_path, "mycmd; echo $?; other | head") == ""


def test_backticks_inside_a_quoted_heredoc_are_silent(scripts_path):
    """A quoted heredoc is the remedy this very warning recommends.

    Warning on it is the same defect already fixed for PIPESTATUS: telling the
    author to apply a remedy they have applied. Observed firing ~13 times in one
    session on commands that were already using `<<'EOF'`, and correctly ignored
    every time — which is how a guard trains the blindness its neighbours rely on.
    """
    cmd = "cat >> notes.md <<'EOF'\nsee `foo | bar` in the docs\nEOF"
    assert _warnings(scripts_path, cmd) == ""


def test_backticks_inside_an_unquoted_heredoc_still_warn(scripts_path):
    """`<<EOF` without quotes DOES expand, so the trap is real there."""
    cmd = "cat <<EOF\nsee `date` here\nEOF"
    assert "SC2006" in _warnings(scripts_path, cmd)


def test_backtick_on_the_heredoc_opener_still_warns(scripts_path):
    """Only the heredoc BODY is inert; the command line around it is not."""
    cmd = "cat >> `pick_file`.md <<'EOF'\nbody\nEOF"
    assert "SC2006" in _warnings(scripts_path, cmd)


def test_logical_or_is_not_a_pipe(scripts_path):
    assert _warnings(scripts_path, "mycmd || fallback; echo $?") == ""


def test_multiple_traps_produce_multiple_warnings(scripts_path):
    out = _warnings(scripts_path, "grep x f && echo `date` | head; echo $?")
    assert out.count("  - ") >= 2


def test_the_warning_says_the_command_still_runs(scripts_path):
    """It advises; it must never read as a block, or the agent will work
    around it instead of with it."""
    out = _warnings(scripts_path, "foo | head; echo $?")
    assert "still runs" in out
    assert "not blocks" in out


# ---------------------------------------------------------------- bad


@pytest.mark.parametrize("payload", [
    "not json at all",
    "",
    json.dumps({"tool_name": "Bash"}),                      # no tool_input
    json.dumps({"tool_input": "a string, not an object"}),
    json.dumps({"tool_input": {"command": "   "}}),         # whitespace only
])
def test_malformed_payloads_fail_open(scripts_path, payload):
    """A guard that breaks the Bash tool is worse than the traps it catches."""
    r = _run(scripts_path, payload)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_never_emits_a_permission_decision(scripts_path):
    """This hook advises. If it ever gained the power to deny, a false positive
    would block real work and the guard would be removed rather than fixed."""
    r = _run(scripts_path, _cmd("foo | head; echo $?"))
    assert "permissionDecision" not in r.stdout


# ---------------------------------------------------------------- in-process
# The tests above drive the hook as a subprocess, which is the right shape for
# the stdin/stdout contract and useless for coverage — coverage.py cannot
# instrument a child interpreter. That exact mistake was logged as a correction
# earlier the same day and repeated here, so these call the functions directly.


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import shell_safety_guard
    return shell_safety_guard


def test_findings_is_pure_and_returns_one_entry_per_trap(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings("git status") == []
    assert len(mod.findings("foo | head; echo $?")) == 1
    assert len(mod.findings("grep x f && echo `date` | head; echo $?")) == 3


def test_findings_suppresses_on_pipestatus(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings('foo | head; echo "${PIPESTATUS[0]}"') == []


def test_main_reads_stdin_and_emits_additional_context(scripts_path,
                                                       monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(
        sys, "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "a | head; echo $?"}})),
    )
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "PIPESTATUS" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_when_nothing_matches(scripts_path, monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "ls"}})))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


def test_main_fails_open_on_garbage(scripts_path, monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


# ------------------------------------------------- shell portability (v0.81.1)
# The remedy this guard recommends was bash-only, and this project's shell is
# zsh — where `${PIPESTATUS[0]}` expands to the empty string. So the advice
# shipped for the trap that produced a wrong answer to the operator silently did
# not work in the environment it was written for. Two bugs, one root cause:
# assuming bash. Caught by the author's own command printing `EXIT=` while
# testing something unrelated.


def test_zsh_pipestatus_suppresses_the_warning(scripts_path):
    """THE WORSE OF THE TWO. The suppression regex was case-sensitive, so
    someone who had ALREADY applied the correct zsh remedy was still warned —
    a false positive aimed squarely at the people doing it right."""
    mod = _import(scripts_path)
    assert mod.findings("foo | head; echo ${pipestatus[1]}") == []


def test_bash_pipestatus_still_suppresses(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings("foo | head; echo ${PIPESTATUS[0]}") == []


def test_the_warning_names_both_shells_and_the_index_difference(scripts_path):
    """zsh's array is lowercase AND 1-indexed, so `${pipestatus[0]}` is also
    empty. Naming the variable without the index would trade one silent
    failure for another."""
    mod = _import(scripts_path)
    msg = mod.findings("foo | head; echo $?")[0]
    assert "${PIPESTATUS[0]}" in msg
    assert "${pipestatus[1]}" in msg
    assert "1-INDEXED" in msg


def test_a_bare_status_check_after_a_pipe_still_warns(scripts_path):
    """The fix must not silence the actual trap."""
    mod = _import(scripts_path)
    assert len(mod.findings("which opencode | head -1; echo $?")) == 1


# ------------------------------------------------- narrowing (2026-08-30)
#
# Rule 1 used to ask only "is there a `$?` somewhere after some `|`?", over the
# raw command. Measured over 12,260 real Bash commands from dogfood session
# transcripts: 223 fires, 53-60% of them effective false positives — five to six
# times outside Tricorder's <10% advisory bar. These pin the two shapes that
# caused it. Ground truth from that corpus: the narrowed rule keeps 88/88 true
# positives and drops 135/135 false ones.


def test_pipe_inside_a_quoted_string_is_not_a_pipeline(scripts_path):
    """`grep "a\\|b"` is an alternation in an argument, not a shell pipeline.

    The largest single false-positive source in the measured corpus."""
    mod = _import(scripts_path)
    assert mod.findings('grep "a\\|b" file; echo $?') == []


def test_pipe_inside_a_single_quoted_filter_is_not_a_pipeline(scripts_path):
    """`jq '.a[] | select(.b)'` — the pipe belongs to jq's language."""
    mod = _import(scripts_path)
    assert mod.findings("jq '.a[] | select(.b)' f.json; echo $?") == []


def test_status_after_a_redirect_is_correct_and_silent(scripts_path):
    """`cmd > log 2>&1; echo $?` reads cmd's status. It is the RECOMMENDED
    idiom, and warning on it taught the reader to scroll past the rule."""
    mod = _import(scripts_path)
    assert mod.findings('python3 check.py > /tmp/o.txt 2>&1; echo "rc=$?"') == []


def test_a_redirect_on_a_later_line_does_not_inherit_an_earlier_pipe(
        scripts_path):
    """The `$?` belongs to the git push, not to the grep two lines up."""
    mod = _import(scripts_path)
    cmd = ('bash tests/run.sh 2>&1 | grep -E "Results"\n'
           'git push origin main > /tmp/p.log 2>&1; echo "push rc=$?"')
    assert mod.findings(cmd) == []


def test_adjacency_the_pipe_must_be_the_previous_command(scripts_path):
    """A pipe two segments back is not what `$?` reports."""
    mod = _import(scripts_path)
    assert mod.findings("a | b; c; echo $?") == []
    assert len(mod.findings("c; a | b; echo $?")) == 1


def test_pipe_inside_a_quoted_heredoc_body_is_not_a_pipeline(scripts_path):
    """Rule 2 already stripped quoted heredocs; rule 1 did not, and fired on a
    `|` inside a Python string in a heredoc."""
    mod = _import(scripts_path)
    cmd = ("python3 - <<'PY'\n"
           "print('present:', k in kc, '| chars', n)\n"
           "PY\n"
           'python3 check.py > /tmp/v.txt 2>&1; echo "rc=$?"')
    assert mod.findings(cmd) == []


def test_the_real_trap_still_warns_after_narrowing(scripts_path):
    """Guard against over-narrowing: every shape that IS the trap still fires."""
    mod = _import(scripts_path)
    for cmd in ("which opencode | head -1; echo $?",
                'ls | wc -l\necho "count rc=$?"',
                'cat f | grep x; echo "rc=$?"'):
        assert len(mod.findings(cmd)) == 1, cmd


# ---------------------------------------------------------------- rule 4 (v0.208.0)
#
# Two dogfood commands from 2026-09-09: a canvas-writing python heredoc that exited 1, followed
# on new lines by a decision-log append, git add, commit and push, all of which ran. The rule
# fires on that shape and stays silent when the steps are gated with && or the commit is in a
# separate command.

_WRITE_THEN_COMMIT = (
    "python3 - <<'EOF'\n"
    "from pathlib import Path\n"
    "p = Path('.claude/canvas/opportunities.yml'); t = p.read_text()\n"
    "assert t.count('x') == 1; p.write_text(t.replace('x', 'y'))\n"
    "EOF\n"
    "cat >> .claude/harness/decision-log.md <<'EOF'\n## DL-1230\nEOF\n"
    "git add -A\n"
    "git commit -q -m 'DL-1230'\n"
    "git push origin main\n"
)


def test_a_durable_write_then_commit_on_separate_lines_warns(scripts_path):
    assert "ungated commit" in _warnings(scripts_path, _WRITE_THEN_COMMIT)


def test_semicolons_are_the_same_shape(scripts_path):
    cmd = "sed -i '' 's/a/b/' .claude/canvas/purpose.yml; git add -A; git commit -m x"
    assert "ungated commit" in _warnings(scripts_path, cmd)


def test_and_gating_is_silent(scripts_path):
    """With a heredoc the gate lives on the opener line: the whole chain is one step."""
    gated = ("python3 - <<'EOF' && git add -A && git commit -m x && git push\n"
             "p='.claude/canvas/x.yml'; open(p,'w').write('a')\n"
             "EOF")
    assert "ungated commit" not in _warnings(scripts_path, gated)
    plain = "sed -i '' 's/a/b/' .claude/canvas/purpose.yml && git add -A && git commit -m x"
    assert "ungated commit" not in _warnings(scripts_path, plain)


def test_a_commit_with_no_durable_write_is_silent(scripts_path):
    assert "ungated commit" not in _warnings(scripts_path, "git add -A\ngit commit -m x\ngit push")


def test_a_write_after_the_commit_is_silent(scripts_path):
    cmd = "git commit -m x\necho note >> .claude/memory/notes.md"
    assert "ungated commit" not in _warnings(scripts_path, cmd)


def test_a_path_inside_a_heredoc_counts_as_the_heredoc_steps_write(scripts_path):
    """The path is inside the quoted heredoc body, which the other rules strip; this rule
    must still see it as the write of the step that opened the heredoc."""
    cmd = ("python3 - <<'EOF'\nfrom pathlib import Path\n"
           "Path('.claude/diamonds/active.yml').write_text('x')\nEOF\n"
           "git commit -am x")
    assert "ungated commit" in _warnings(scripts_path, cmd)


# ------------------------------------------------------------------ rule 5 (v0.223.0)
# A scripted multi-file edit that can half-apply. Scope was set by measurement before it
# shipped (14,419 real commands): the broad form fires on 11% of all commands, this one on
# 2.1%, and every one of those can leave the tree half-edited.

_HALF = "safe_replace.py"  # the phrase that identifies rule 5's warning


def test_multi_file_edit_with_a_late_anchor_check_warns(scripts_path):
    """THE SHAPE. File a is written, then file b's anchor is asserted: if it fails, a is
    already changed. Verbatim the shape of a version-bump script from the 2026-09-17 session."""
    cmd = (
        "python3 - <<'PY'\n"
        "s=open('plugin.json').read(); open('plugin.json','w').write(s.replace('0.1','0.2'))\n"
        "t=open('CHANGELOG.md').read(); assert t.count('## v0.1')==1\n"
        "open('CHANGELOG.md','w').write(t.replace('## v0.1','## v0.2\\n\\n## v0.1'))\n"
        "PY"
    )
    assert _HALF in _warnings(scripts_path, cmd)


def test_multi_file_edit_with_no_anchor_check_at_all_warns(scripts_path):
    cmd = (
        "python3 -c \"open('a','w').write(open('a').read().replace('x','y')); "
        "open('b','w').write(open('b').read().replace('x','y'))\""
    )
    assert _HALF in _warnings(scripts_path, cmd)


def test_single_file_edit_is_silent_however_many_anchors(scripts_path):
    """NEGATIVE CONTROL, and the reason the rule was narrowed: 1,300+ real commands have
    this shape and none of them can half-apply."""
    cmd = (
        "python3 - <<'PY'\n"
        "s=open('a.yml').read(); assert s.count('x')==1\n"
        "s=s.replace('x','y').replace('q','r'); open('a.yml','w').write(s)\n"
        "PY"
    )
    assert _HALF not in _warnings(scripts_path, cmd)


def test_multi_file_edit_with_every_check_before_the_first_write_is_silent(scripts_path):
    """The rule's substance kept by hand. Warning here would punish the careful script."""
    cmd = (
        "python3 - <<'PY'\n"
        "a=open('a').read(); b=open('b').read(); assert a.count('x')==1 and b.count('x')==1\n"
        "open('a','w').write(a.replace('x','y')); open('b','w').write(b.replace('x','y'))\n"
        "PY"
    )
    assert _HALF not in _warnings(scripts_path, cmd)


def test_using_the_helper_is_silent(scripts_path):
    cmd = "python3 scripts/safe_replace.py --spec edits.json"
    assert _HALF not in _warnings(scripts_path, cmd)


# ------------------------------------------------------------------ opt-in trigger (v0.224.0)
# Default is a rate, not a transcript. With MYCELIUM_LEDGER_TRIGGER=on the ledger row also
# carries the first 200 characters of the command, obvious secrets masked.

_PIPE_STATUS = 'grep -c foo bar.txt | head -1; echo "rc=$?"'


def _ledger_rows(tmp_path):
    f = tmp_path / ".claude" / "state" / "shell-safety-guard-log.jsonl"
    return [json.loads(line) for line in f.read_text().splitlines()] if f.exists() else []


def _run_in(scripts_path, tmp_path, command, **env):
    import os

    full = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path), **env)
    full.pop("MYCELIUM_LEDGER_TRIGGER", None) if "MYCELIUM_LEDGER_TRIGGER" not in env else None
    return subprocess.run(
        [sys.executable, str(scripts_path / "shell_safety_guard.py")],
        input=_cmd(command), capture_output=True, text=True, env=full, check=False,
    )


def test_by_default_the_ledger_carries_no_trigger(scripts_path, tmp_path):
    """THE DEFAULT IS THE PRIVACY PROMISE. A fire is ledgered; the command is not."""
    _run_in(scripts_path, tmp_path, _PIPE_STATUS)
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1, "the guard did not fire, so this test would prove nothing"
    assert "trigger" not in rows[0]


def test_opt_in_records_the_command(scripts_path, tmp_path):
    _run_in(scripts_path, tmp_path, _PIPE_STATUS, MYCELIUM_LEDGER_TRIGGER="on")
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["trigger"].startswith("grep -c foo bar.txt | head -1")


@pytest.mark.parametrize(
    ("command", "secret"),
    [
        ('curl -H "Authorization: Bearer abcDEF1234567890xyz" https://x.test | head; echo $?', "abcDEF1234567890xyz"),
        ("GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123 gh api user | head -1; echo $?", "ghp_abcdefghijklmnopqrstuvwxyz0123"),
        ("git clone https://haabe:hunter2secret@github.com/haabe/x.git | tail; echo $?", "hunter2secret"),
        ('mysql --password hunter2pass -e "select 1" | head; echo $?', "hunter2pass"),
    ],
)
def test_opt_in_masks_the_obvious_secret_shapes(scripts_path, tmp_path, command, secret):
    _run_in(scripts_path, tmp_path, command, MYCELIUM_LEDGER_TRIGGER="on")
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1
    assert secret not in rows[0]["trigger"], rows[0]["trigger"]
    assert "<masked>" in rows[0]["trigger"]


def test_the_trigger_is_truncated(scripts_path, tmp_path):
    long = "grep -c foo " + "x" * 600 + " | head -1; echo $?"
    _run_in(scripts_path, tmp_path, long, MYCELIUM_LEDGER_TRIGGER="on")
    assert len(_ledger_rows(tmp_path)[0]["trigger"]) <= 200


# ------------------------------------------------- in-process, rules 4 and 5 (v0.226.2)
# WHY THESE EXIST. Every test of rules 4 and 5 above drives a subprocess, so none of it
# counted toward coverage. Rule 5 landed in v0.223.0 and took this file to 68%, under the
# 70% per-file floor. That floor runs in CI only, so the push gate passed and FOUR versions
# (0.223.0 to 0.226.0) were pushed and never released. The header of the in-process section
# above already named this mistake; it was made a third time. Same commands, called directly.

_LATE_CHECK = (
    "python3 - <<'PY'\n"
    "s=open('plugin.json').read(); open('plugin.json','w').write(s.replace('0.1','0.2'))\n"
    "t=open('CHANGELOG.md').read(); assert t.count('## v0.1')==1\n"
    "open('CHANGELOG.md','w').write(t.replace('## v0.1','## v0.2'))\n"
    "PY"
)
_EARLY_CHECK = (
    "python3 - <<'PY'\n"
    "a=open('a').read(); b=open('b').read(); assert a.count('x')==1 and b.count('x')==1\n"
    "open('a','w').write(a.replace('x','y')); open('b','w').write(b.replace('x','y'))\n"
    "PY"
)
_NO_CHECK = (
    "python3 -c \"open('a','w').write(open('a').read().replace('x','y')); "
    "open('b','w').write(open('b').read().replace('x','y'))\""
)
_ONE_FILE = (
    "python3 - <<'PY'\n"
    "s=open('a.yml').read(); assert s.count('x')==1\n"
    "s=s.replace('x','y'); open('a.yml','w').write(s)\n"
    "PY"
)
_GATED = ("python3 - <<'EOF' && git add -A && git commit -m x\n"
          "p='.claude/canvas/x.yml'; open(p,'w').write('a')\n"
          "EOF")


@pytest.mark.parametrize(
    ("command", "phrase", "warns"),
    [
        (_LATE_CHECK, _HALF, True),
        (_NO_CHECK, _HALF, True),
        (_EARLY_CHECK, _HALF, False),
        (_ONE_FILE, _HALF, False),
        ("python3 scripts/safe_replace.py --spec edits.json", _HALF, False),
        (_WRITE_THEN_COMMIT, "ungated commit", True),
        ("sed -i '' 's/a/b/' .claude/canvas/purpose.yml; git add -A; git commit -m x",
         "ungated commit", True),
        (_GATED, "ungated commit", False),
        ("git commit -m x\necho note >> .claude/memory/notes.md", "ungated commit", False),
        ("echo 'a; git commit' >> .claude/memory/n.md", "ungated commit", False),
    ],
)
def test_rules_four_and_five_in_process(scripts_path, command, phrase, warns):
    got = _import(scripts_path).findings(command)
    assert isinstance(got, list)
    assert any(phrase in w for w in got) is warns, got


def test_raw_steps_keep_a_heredoc_body_with_the_step_that_opened_it(scripts_path):
    mod = _import(scripts_path)
    steps = mod._raw_steps("python3 - <<'EOF'\na = 1; b = 2\nEOF\ngit status; echo 'x; y'")
    assert len(steps) == 3, steps
    assert "a = 1; b = 2" in steps[0]
    assert steps[2].strip() == "echo 'x; y'"


def test_raw_steps_survive_a_heredoc_with_no_body(scripts_path):
    assert _import(scripts_path)._raw_steps("cat <<'EOF'") == ["cat <<'EOF'"]


def test_masked_trigger_in_process(scripts_path):
    mod = _import(scripts_path)
    out = mod._masked_trigger("GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123 gh api user " + "x" * 600)
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123" not in out
    assert "<masked>" in out
    assert len(out) <= 200
