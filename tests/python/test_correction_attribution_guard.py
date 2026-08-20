"""G-V12 coverage proof for correction_attribution_guard.py.

THE GAP IT CLOSES. `engine/agent-operating-contract.md` line 57 has required,
as a HARD RULE since 2026-08-03, that every corrections.md entry names who
caught the mistake. Measured 2026-08-20: 15 of the 91 entries written since
carry a catcher (16%) — LOWER than the 29% the rule scored while it was still
advisory. Hardening the wording moved the number down.

THE BIMODAL SHAPE IS WHY A HOOK AND NOT MORE PROSE. 2026-08-03: 9 of 11.
2026-08-08: 8 of 9. Every other day at or near zero, including 0 of 5 on
2026-08-20 in the session that measured this. The rule is obeyed on days the
agent works ON the attribution machinery and ignored otherwise — a timing
failure, not a comprehension one.

THE BASH CASE IS THE LOAD-BEARING ONE, not an extra. Those five unattributed
entries were appended with `cat >> corrections.md` inside a Bash call. A guard
registered on Write|Edit|MultiEdit alone would have shipped green against the
exact corpus that motivated it. `test_bash_heredoc_append_warns` is the
regression fixture for that, and it is the test to keep if any are dropped.

Scenario-per-guardpost:
  happy — a new entry naming its catcher              -> silence
  happy — each of the four vocabulary forms           -> silence
  sad   — a new entry with no catcher                 -> warn
  sad   — the same entry appended via Bash heredoc    -> warn  (the real path)
  sad   — Edit, which uses new_string not content     -> warn
  edge  — editing prose inside an existing entry      -> silence (no heading)
  edge  — a write to a different memory file          -> silence
  edge  — a Bash command that only READS the file     -> silence
  edge  — several unattributed entries in one write   -> all quoted, capped at 3
  bad   — unparseable payload                         -> silence, exit 0
  bad   — tool_input that is not a dict               -> silence, exit 0
"""

import io
import json
import subprocess
import sys

SCRIPT = "correction_attribution_guard.py"
TARGET = "/Users/x/proj/.claude/memory/corrections.md"

ENTRY = "## 2026-08-21 — A claim was published before it was checked\n\nSome prose.\n"


def _run(scripts_path, payload):
    return subprocess.run(
        [sys.executable, str(scripts_path / SCRIPT)],
        input=payload, capture_output=True, text=True, check=False,
    )


def _out(r):
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


def _warn(scripts_path, text, path=TARGET, tool="Write"):
    key = "content" if tool == "Write" else "new_string"
    return _out(_run(scripts_path, json.dumps(
        {"tool_name": tool, "tool_input": {"file_path": path, key: text}})))


def _bash(scripts_path, command):
    return _out(_run(scripts_path, json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command}})))


# ---------------------------------------------------------------- happy

def test_entry_naming_its_catcher_is_silent(scripts_path):
    assert _warn(scripts_path, ENTRY + "\n**Caught by user.**\n") == ""


def test_every_vocabulary_form_is_accepted(scripts_path):
    """The four forms the contract names. If this drifts from
    check_correction_attribution.CATCHERS, the guard is enforcing a private
    definition of compliance — the exact failure it was built to stop."""
    for phrase in ("caught by user", "caught by hook", "caught by review",
                   "self-caught", "Caught by the founder", "surfaced by CI",
                   "flagged by the validator", "detected by review"):
        assert _warn(scripts_path, ENTRY + f"\n**{phrase}.**\n") == "", phrase


# ---------------------------------------------------------------- sad

def test_entry_without_a_catcher_warns(scripts_path):
    msg = _warn(scripts_path, ENTRY)
    assert "no catcher named" in msg
    assert "A claim was published before it was checked" in msg


def test_bash_heredoc_append_warns(scripts_path):
    """THE REGRESSION FIXTURE. This is how the five entries of 2026-08-20 were
    written, and a Write|Edit-only guard would have missed every one."""
    cmd = f"cat >> {TARGET} <<'E'\n{ENTRY}\nE"
    assert "no catcher named" in _bash(scripts_path, cmd)


def test_bash_tee_append_warns(scripts_path):
    cmd = f"printf '%s' \"$X\" | tee -a {TARGET}\n{ENTRY}"
    assert "no catcher named" in _bash(scripts_path, cmd)


def test_edit_reads_new_string_not_content(scripts_path):
    assert "no catcher named" in _warn(scripts_path, ENTRY, tool="Edit")


# ---------------------------------------------------------------- edge

def test_editing_prose_inside_an_existing_entry_is_silent(scripts_path):
    """147 entries predate the rule and are NOT backfillable — who caught a
    mistake six weeks ago is not recoverable by inference. A guard that fired
    every time one was touched would be turned off within a day."""
    assert _warn(scripts_path, "fixed a typo in the third paragraph",
                 tool="Edit") == ""


def test_a_different_memory_file_is_silent(scripts_path):
    other = "/Users/x/proj/.claude/memory/patterns.md"
    assert _warn(scripts_path, ENTRY, path=other) == ""


def test_a_bash_read_of_the_file_is_silent(scripts_path):
    assert _bash(scripts_path, f"grep -c '^## ' {TARGET}") == ""


def test_a_bash_write_to_another_file_is_silent(scripts_path):
    assert _bash(scripts_path, f"cat >> /tmp/notes.md <<'E'\n{ENTRY}\nE") == ""


def test_several_entries_are_quoted_and_capped(scripts_path):
    many = "".join(
        f"## 2026-08-2{i} — Entry number {i}\n\nprose.\n\n" for i in range(1, 6))
    msg = _warn(scripts_path, many)
    assert "and 2 more in this write" in msg
    assert msg.count("    > ") == 3


# ---------------------------------------------------------------- bad

def test_unparseable_payload_fails_open(scripts_path):
    r = _run(scripts_path, "{not json")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_tool_input_that_is_not_a_dict_fails_open(scripts_path):
    r = _run(scripts_path, json.dumps({"tool_name": "Edit", "tool_input": "nope"}))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_empty_payload_fails_open(scripts_path):
    r = _run(scripts_path, "{}")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


# ---------------------------------------------------------------- in-process
# The tests above drive the hook as a subprocess, which is the right shape for
# the stdin/stdout contract and useless for coverage — coverage.py cannot
# instrument a child interpreter, so the per-file floor read this script at 0%
# and blocked the push. THIRD TIME: shell_safety_guard, then absence_claim_guard,
# now this one — and the second of those wrote the explanation into its own test
# file, where it sat unread while this file was being written. A comment is not a
# mechanism; see the note in corrections.md.


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import correction_attribution_guard
    return correction_attribution_guard


def test_findings_returns_one_head_per_unattributed_entry(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings("just prose, no heading") == []
    assert len(mod.findings(ENTRY)) == 1
    assert mod.findings(ENTRY + "\ncaught by hook\n") == []


def test_findings_truncates_a_long_heading(scripts_path):
    mod = _import(scripts_path)
    head = "## 2026-08-21 — " + ("x" * 400)
    out = mod.findings(head + "\n\nprose\n")
    assert len(out) == 1
    assert len(out[0]) <= 160


def test_shell_findings_only_fires_on_a_write_to_the_target(scripts_path):
    mod = _import(scripts_path)
    assert mod.shell_findings(f"cat {TARGET}") == []
    assert mod.shell_findings(f"cat >> {TARGET} <<'E'\n{ENTRY}\nE") != []


def test_hits_for_ignores_a_non_dict_tool_input(scripts_path):
    mod = _import(scripts_path)
    assert mod.hits_for({"tool_name": "Edit", "tool_input": None}) == []
    assert mod.hits_for({}) == []


def test_multiedit_reads_every_new_string(scripts_path):
    mod = _import(scripts_path)
    payload = {"tool_name": "MultiEdit", "tool_input": {"file_path": TARGET, "edits": [
        {"new_string": ENTRY},
        {"new_string": "## 2026-08-22 — Another one\n\nprose\n"},
        {"new_string": "## 2026-08-23 — Attributed\n\ncaught by user\n"},
    ]}}
    assert len(mod.hits_for(payload)) == 2


def test_payload_text_returns_empty_for_an_unknown_tool(scripts_path):
    mod = _import(scripts_path)
    assert mod._payload_text("Grep", {"content": ENTRY}) == ""


def _main_out(mod, monkeypatch, capsys, payload):
    """Drive main() in-process so the protocol path is measured, not just run."""
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    rc = mod.main()
    return rc, capsys.readouterr().out


def test_main_emits_the_hook_protocol_envelope(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    rc, out = _main_out(mod, monkeypatch, capsys, json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": TARGET, "content": ENTRY}}))
    assert rc == 0
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "no catcher named" in env["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_when_the_entry_names_its_catcher(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    rc, out = _main_out(mod, monkeypatch, capsys, json.dumps(
        {"tool_name": "Write",
         "tool_input": {"file_path": TARGET, "content": ENTRY + "\nself-caught\n"}}))
    assert rc == 0
    assert out.strip() == ""


def test_main_fails_open_on_unparseable_stdin(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    rc, out = _main_out(mod, monkeypatch, capsys, "{not json")
    assert rc == 0
    assert out.strip() == ""


def test_main_caps_the_quote_list(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    many = "".join(f"## 2026-08-2{i} — Entry {i}\n\nprose.\n\n" for i in range(1, 6))
    rc, out = _main_out(mod, monkeypatch, capsys, json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": TARGET, "content": many}}))
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert ctx.count("    > ") == mod._QUOTE_MAX
    assert "and 2 more in this write" in ctx


def test_main_fails_open_when_hits_for_raises(scripts_path, monkeypatch, capsys):
    """A guard that breaks a write gets deleted. Any unexpected failure inside
    the analysis must still exit 0 and say nothing."""
    mod = _import(scripts_path)
    monkeypatch.setattr(mod, "hits_for", lambda _: (_ for _ in ()).throw(RuntimeError("x")))
    rc, out = _main_out(mod, monkeypatch, capsys, json.dumps({"tool_name": "Write"}))
    assert rc == 0
    assert out.strip() == ""


def test_findings_is_silent_when_the_shared_vocabulary_is_unavailable(
        scripts_path, monkeypatch):
    """The catcher patterns are imported from check_correction_attribution. If
    that import ever fails, the guard must go quiet rather than guess."""
    mod = _import(scripts_path)
    monkeypatch.setattr(mod, "classify", None)
    assert mod.findings(ENTRY) == []


def test_entry_bodies_is_silent_without_the_shared_entry_definition(
        scripts_path, monkeypatch):
    mod = _import(scripts_path)
    monkeypatch.setattr(mod, "_corrections_lib", None)
    assert mod.findings(ENTRY) == []


def test_bash_payload_with_a_non_string_command_is_ignored(scripts_path):
    mod = _import(scripts_path)
    assert mod.hits_for({"tool_name": "Bash", "tool_input": {"command": None}}) == []
    assert mod.hits_for({"tool_name": "Bash", "tool_input": {"command": "   "}}) == []


def test_an_empty_write_is_ignored(scripts_path):
    mod = _import(scripts_path)
    assert mod.hits_for(
        {"tool_name": "Write", "tool_input": {"file_path": TARGET, "content": "  "}}) == []


def test_a_non_string_file_path_is_ignored(scripts_path):
    mod = _import(scripts_path)
    assert mod.hits_for({"tool_name": "Write", "tool_input": {"file_path": 7}}) == []
