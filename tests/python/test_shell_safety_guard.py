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
