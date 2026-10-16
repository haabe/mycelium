"""Lesson triggers (v0.327.0): a lesson on record, shown at the call it is about, refused where its
entry marks the call as the mistake itself. Off unless MYCELIUM_LESSON_TRIGGERS=on.

Each test that it fires is paired with one that it stays quiet (the dogfood pattern "a new guard is
wrong on first contact with real data")."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
import lesson_triggers as lt  # noqa: E402

TRIGGERS = """
schema_version: 1
lessons:
- id: date-in-a-key-name
  rule: "Put a date in a value, never in a key's name."
  match: {tools: [Write, Edit, MultiEdit], path: '\\.claude/canvas/', content: '^\\s*[a-z_]+_\\d{4}_\\d{2}_\\d{2}\\s*:'}
  refuse: true
- id: reddit-through-the-connector
  rule: "Read Reddit through the connector; a direct fetch returns 403."
  match: {tools: [WebFetch, Bash], url: 'reddit\\.com', command: '(curl|wget)[^\\n]*reddit\\.com'}
  refuse: true
- id: child-agents
  rule: "Set what tools child agents get before launching claude -p runs."
  match: {tools: [Bash], command: '\\bclaude\\s+-p\\b'}
  refuse: false
- id: bad-pattern
  rule: "Never shown: its pattern does not compile."
  match: {tools: [Bash], command: '(unclosed'}
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "memory").mkdir()
    (tmp_path / ".claude" / "memory" / "lesson-triggers.yml").write_text(TRIGGERS)
    return tmp_path


def _decide(project, tool, tool_input):
    return lt.decide(lt.load(project / lt.TRIGGERS), tool, tool_input)


def _ids(found):
    return [x["id"] for x in found]


def test_a_matching_call_shows_its_rule_line_and_the_call_runs(project):
    refused, shown = _decide(project, "Bash", {"command": "claude -p 'build it'"})
    assert refused == [] and _ids(shown) == ["child-agents"]
    out = lt.output(refused, shown)["hookSpecificOutput"]
    assert "permissionDecision" not in out
    assert "Set what tools child agents get" in out["additionalContext"]


def test_control_a_call_that_matches_nothing_is_silent(project):
    assert _decide(project, "Bash", {"command": "ls -la"}) == ([], [])
    assert lt.output([], []) is None


def test_an_entry_marked_refuse_stops_the_call_with_its_rule_line(project):
    edit = {"file_path": str(project / ".claude/canvas/landscape.yml"), "new_string": "  update_2026_10_07: >-\n"}
    refused, _ = _decide(project, "Edit", edit)
    out = lt.output(refused, [])["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    assert "Put a date in a value" in out["permissionDecisionReason"]


def test_control_the_same_text_outside_its_path_is_not_refused(project):
    edit = {"file_path": str(project / "notes.md"), "new_string": "  update_2026_10_07: >-\n"}
    assert _decide(project, "Edit", edit) == ([], [])


def test_each_key_applies_to_the_tools_that_carry_it(project):
    fetch = _decide(project, "WebFetch", {"url": "https://www.reddit.com/r/x/comments/abc/"})
    curl = _decide(project, "Bash", {"command": "curl -s https://www.reddit.com/r/x.json"})
    assert _ids(fetch[0]) == ["reddit-through-the-connector"] == _ids(curl[0])


def test_control_a_key_that_applies_must_match(project):
    assert _decide(project, "Bash", {"command": "echo reddit.com"}) == ([], [])
    assert _decide(project, "WebFetch", {"url": "https://example.com/"}) == ([], [])


def test_multiedit_reads_every_edit_it_writes(project):
    path = str(project / ".claude/canvas/opportunities.yml")
    refused, _ = _decide(project, "MultiEdit", {"file_path": path, "edits": [
        {"old_string": "a", "new_string": "fine: 1"}, {"old_string": "b", "new_string": "seen_2026_09_01: x"}]})
    assert _ids(refused) == ["date-in-a-key-name"]


def test_a_pattern_that_does_not_compile_is_skipped_not_raised(project):
    assert _decide(project, "Bash", {"command": "(unclosed"}) == ([], [])


def test_at_most_three_rule_lines_are_shown():
    lessons = [{"id": f"l{i}", "rule": f"rule {i}", "match": {"tools": ["Bash"], "command": "x"}} for i in range(5)]
    body = lt.output(*lt.decide(lessons, "Bash", {"command": "x"}))["hookSpecificOutput"]["additionalContext"]
    assert body.count("  - rule ") == lt.MAX_SHOWN


def test_a_tool_it_does_not_read_is_silent(project):
    assert _decide(project, "apply_patch", {"patch": "claude -p"}) == ([], [])


def test_a_missing_or_unreadable_file_means_nothing_is_shown(tmp_path):
    assert lt.load(tmp_path / "nope.yml") == []
    bad = tmp_path / "bad.yml"
    bad.write_text("lessons: [unclosed")
    assert lt.load(bad) == []


def test_a_triggers_file_that_cannot_be_parsed_is_said_out_loud(project):
    (project / lt.TRIGGERS).write_text("lessons: [unclosed")
    r = _hook(project, {"tool_name": "Bash", "tool_input": {"command": "ls"}}, on=True)
    assert "could not be read" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert lt.main(["--check", str(project / lt.TRIGGERS)]) == 2


def test_control_no_triggers_file_at_all_is_silent(project):
    (project / lt.TRIGGERS).unlink()
    r = _hook(project, {"tool_name": "Bash", "tool_input": {"command": "claude -p go"}}, on=True)
    assert r.returncode == 0 and r.stdout == ""


def test_check_reports_a_rule_line_that_names_a_handle_or_an_address(tmp_path):
    f = tmp_path / "t.yml"
    f.write_text('lessons:\n- id: a\n  rule: "Ask u/someone first."\n  match: {tools: [Bash], command: x}\n'
                 '- id: b\n  rule: "Mail them at a.person@example.com."\n  match: {tools: [Bash], command: x}\n')
    assert [x.split(":")[0] for x in lt.check(f)] == ["a", "b"]
    assert lt.main(["--check", str(f)]) == 1


def test_control_check_passes_rule_lines_that_name_nobody(project):
    assert lt.check(project / lt.TRIGGERS) == []
    assert lt.main(["--check", str(project / lt.TRIGGERS)]) == 0


def _hook(project, payload, on):
    env = {k: v for k, v in os.environ.items() if k != lt.ENV}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
    if on:
        env[lt.ENV] = "on"
    return subprocess.run(["bash", str(PLUGIN / "hooks" / "lesson-triggers.sh")], input=json.dumps(payload),
                          capture_output=True, text=True, env=env, cwd=project, timeout=30, check=False)


def test_off_by_default_the_hook_says_nothing_even_on_a_match(project):
    r = _hook(project, {"tool_name": "Bash", "tool_input": {"command": "claude -p go"}}, on=False)
    assert r.returncode == 0 and r.stdout == ""


def test_switched_on_the_hook_shows_the_line_and_records_a_refusal(project):
    shown = _hook(project, {"tool_name": "Bash", "tool_input": {"command": "claude -p go"}}, on=True)
    assert "child agents" in json.loads(shown.stdout)["hookSpecificOutput"]["additionalContext"]
    refused = _hook(project, {"tool_name": "WebFetch", "tool_input": {"url": "https://reddit.com/r/x"}}, on=True)
    assert json.loads(refused.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (project / ".claude" / "state" / "lesson-triggers-fires.jsonl").exists()


def test_a_broken_payload_fails_open(project):
    env = {**os.environ, lt.ENV: "on", "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
    r = subprocess.run(["bash", str(PLUGIN / "hooks" / "lesson-triggers.sh")], input="not json",
                       capture_output=True, text=True, env=env, cwd=project, timeout=30, check=False)
    assert r.returncode == 0 and r.stdout == ""
