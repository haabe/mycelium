"""Coverage tests for autonomous_evidence_guard.py — the PreToolUse guard.

Covers the decision branches:
  - not autonomous -> allow (silent)
  - autonomous via env / via diamonds/active.yml
  - enforced-path + forbidden assignment -> deny (JSON permissionDecision)
  - non-enforced path / no forbidden content / empty -> allow
  - fail-open on unparseable stdin
plus the pure helpers (truthy, extract, autonomous_active).
"""
import json
import subprocess
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import autonomous_evidence_guard

    return autonomous_evidence_guard


def _run(scripts_path, project_dir, payload, env=None):
    """Invoke the script as the hook would. Returns (rc, stdout)."""
    import os
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    r = subprocess.run(
        ["python3", str(scripts_path / "autonomous_evidence_guard.py"),
         str(project_dir)],
        input=json.dumps(payload), capture_output=True, text=True,
        check=False, env=full_env,
    )
    return r.returncode, r.stdout


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------

def test_truthy_accepts_known_forms(scripts_path):
    mod = _import(scripts_path)
    for v in ("1", "true", "TRUE", "Yes", "on"):
        assert mod.truthy(v) is True
    for v in ("0", "false", "no", "", "off"):
        assert mod.truthy(v) is False


def test_extract_write_content(scripts_path):
    mod = _import(scripts_path)
    path, content = mod.extract({"file_path": "a.yml", "content": "x"}, "Write")
    assert path == "a.yml"
    assert content == "x"


def test_extract_edit_new_string(scripts_path):
    mod = _import(scripts_path)
    path, content = mod.extract({"path": "b.yml", "new_string": "y"}, "Edit")
    assert path == "b.yml"
    assert content == "y"


def test_extract_multiedit_joins(scripts_path):
    mod = _import(scripts_path)
    _, content = mod.extract(
        {"edits": [{"new_string": "a"}, {"new_string": "b"}]}, "MultiEdit")
    assert content == "a\nb"


def test_extract_filesystem_edit_newtext(scripts_path):
    mod = _import(scripts_path)
    _, content = mod.extract(
        {"edits": [{"newText": "z"}]}, "mcp__filesystem__edit_file")
    assert content == "z"


def test_autonomous_active_env(scripts_path, monkeypatch, tmp_path):
    mod = _import(scripts_path)
    monkeypatch.setenv("MYCELIUM_AUTONOMOUS_RUN", "true")
    assert mod.autonomous_active(str(tmp_path)) is True


def test_autonomous_active_via_active_yml(scripts_path, monkeypatch, tmp_path):
    mod = _import(scripts_path)
    monkeypatch.delenv("MYCELIUM_AUTONOMOUS_RUN", raising=False)
    d = tmp_path / ".claude" / "diamonds"
    d.mkdir(parents=True)
    (d / "active.yml").write_text("autonomous: true\n")
    assert mod.autonomous_active(str(tmp_path)) is True


def test_autonomous_inactive_default(scripts_path, monkeypatch, tmp_path):
    mod = _import(scripts_path)
    monkeypatch.delenv("MYCELIUM_AUTONOMOUS_RUN", raising=False)
    assert mod.autonomous_active(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# end-to-end (subprocess, since main() reads stdin + sys.exit)
# ---------------------------------------------------------------------------

def test_not_autonomous_allows_silently(scripts_path, tmp_path):
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/x.yml",
                              "content": "validated: true\n"}}
    rc, out = _run(scripts_path, tmp_path, payload)
    assert rc == 0
    assert out.strip() == ""


def test_autonomous_blocks_forbidden_assignment(scripts_path, tmp_path):
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/opportunities.yml",
                              "content": "source_class: external_human\n"}}
    rc, out = _run(scripts_path, tmp_path, payload,
                   env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert rc == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "external_human" in decision["permissionDecisionReason"]


def test_autonomous_blocks_validated_true(scripts_path, tmp_path):
    payload = {"tool_name": "Edit",
               "tool_input": {"file_path": ".claude/diamonds/active.yml",
                              "new_string": "  validated: true\n"}}
    rc, out = _run(scripts_path, tmp_path, payload,
                   env={"MYCELIUM_AUTONOMOUS_RUN": "yes"})
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_autonomous_allows_permitted_content(scripts_path, tmp_path):
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/x.yml",
                              "content": "source_class: internal_simulated\n"
                                         "validated: false\n"}}
    rc, out = _run(scripts_path, tmp_path, payload,
                   env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert rc == 0
    assert out.strip() == ""


def test_autonomous_allows_non_enforced_path(scripts_path, tmp_path):
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/memory/notes.md",
                              "content": "validated: true\n"}}
    rc, out = _run(scripts_path, tmp_path, payload,
                   env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert rc == 0
    assert out.strip() == ""


def test_autonomous_allows_empty_content(scripts_path, tmp_path):
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/x.yml"}}
    rc, out = _run(scripts_path, tmp_path, payload,
                   env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert rc == 0
    assert out.strip() == ""


# ---------------------------------------------------------------------------
# in-process main()/deny() coverage (monkeypatch stdin/argv, catch SystemExit)
# ---------------------------------------------------------------------------

def _call_main(mod, monkeypatch, project_dir, payload, env=None):
    """Drive main() in-process: stub argv + stdin, catch sys.exit. Returns stdout."""
    import io
    monkeypatch.setattr("sys.argv", ["autonomous_evidence_guard.py", str(project_dir)])
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("MYCELIUM_AUTONOMOUS_RUN", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code in (0, None)


def test_main_deny_in_process(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/x.yml",
                              "content": "evidence_type: data-supported\n"}}
    _call_main(mod, monkeypatch, tmp_path, payload,
               env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    out = capsys.readouterr().out
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "evidence_type above speculation" in decision["permissionDecisionReason"]


def test_main_allow_not_autonomous_in_process(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/canvas/x.yml",
                              "content": "validated: true\n"}}
    _call_main(mod, monkeypatch, tmp_path, payload)
    assert capsys.readouterr().out.strip() == ""


def test_main_allow_non_enforced_path_in_process(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".claude/memory/notes.md",
                              "content": "validated: true\n"}}
    _call_main(mod, monkeypatch, tmp_path, payload,
               env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert capsys.readouterr().out.strip() == ""


def test_main_bad_json_denies_in_process(scripts_path, monkeypatch, tmp_path, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr("sys.argv", ["autonomous_evidence_guard.py", str(tmp_path)])
    monkeypatch.setattr("sys.stdin", io.StringIO("not json{{"))
    monkeypatch.setenv("MYCELIUM_AUTONOMOUS_RUN", "1")
    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code in (0, None)
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"  # 2026-09-11: no guess on bad input


def test_unparseable_stdin_denies(scripts_path, tmp_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "autonomous_evidence_guard.py"),
         str(tmp_path)],
        input="not json{{", capture_output=True, text=True, check=False,
        env={"MYCELIUM_AUTONOMOUS_RUN": "1", "PATH": __import__("os").environ["PATH"]},
    )
    assert r.returncode == 0
    assert '"permissionDecision": "deny"' in r.stdout


# ---------------------------------------------------------------------------
# 0.196.x: the YAML walk, the post-edit scan, the Bash branch, the un-declare guard
# ---------------------------------------------------------------------------

def _decision(capsys):
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


@pytest.mark.parametrize(("text", "expect"), [
    ("- {id: o1, source_class: external_human}", "source_class: external_human"),
    ("- id: o1\n  validated: yes", "validated: true"),
    ("- id: o1\n  evidence_type: Anecdotal", "evidence_type above speculation"),
    ("- &a external_data\n- id: o1\n  source_class: *a", "source_class: external_data"),
    ("nested:\n  deeper:\n    - validated: true", "validated: true"),
])
def test_forbidden_in_walks_every_yaml_spelling(scripts_path, text, expect):
    mod = _import(scripts_path)
    assert expect in mod.forbidden_in(text)


def test_forbidden_in_regex_fallback_on_unparseable_yaml(scripts_path):
    mod = _import(scripts_path)
    assert "validated: true" in mod.forbidden_in("- id: [unclosed\nvalidated: true\n")
    assert mod.forbidden_in("- id: o1\n  source_class: internal_simulated\n") == []


def test_apply_edits_shows_the_file_as_it_would_be(scripts_path):
    mod = _import(scripts_path)
    disk = "- id: o1\n  source_class: internal_simulated\n  validated: false\n"
    after = mod._apply_edits("Edit", {"old_string": "internal_simulated", "new_string": "external_human"}, disk)
    assert "external_human" in after
    after = mod._apply_edits("MultiEdit", {"edits": [{"old_string": "false", "new_string": "true"}]}, disk)
    assert "validated: true" in after
    after = mod._apply_edits("mcp__filesystem__edit_file", {"edits": [{"oldText": "o1", "newText": "o2"}]}, disk)
    assert "id: o2" in after
    assert mod._apply_edits("Write", {"content": "fresh"}, disk) == "fresh"
    assert mod._apply_edits("Edit", {"old_string": "", "new_string": "tail"}, disk).endswith("tail")


def test_edit_that_replaces_only_the_value_is_denied(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "opportunities.yml").write_text("- id: o1\n  source_class: internal_simulated\n")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(canvas / "opportunities.yml"),
               "old_string": "internal_simulated", "new_string": "external_human"}}
    _call_main(mod, monkeypatch, tmp_path, payload, env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    d = _decision(capsys)
    assert d and d["permissionDecision"] == "deny"


def test_bash_append_to_canvas_is_denied(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    payload = {"tool_name": "Bash", "tool_input": {
        "command": "printf 'source_class: external_human\\n' >> .claude/canvas/opportunities.yml"}}
    _call_main(mod, monkeypatch, tmp_path, payload, env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    d = _decision(capsys)
    assert d and d["permissionDecision"] == "deny"


def test_bash_that_does_not_touch_the_canvas_is_allowed(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    _call_main(mod, monkeypatch, tmp_path, payload, env={"MYCELIUM_AUTONOMOUS_RUN": "1"})
    assert _decision(capsys) is None


def test_undeclaring_the_run_is_denied(scripts_path, monkeypatch, tmp_path, capsys):
    mod = _import(scripts_path)
    diamonds = tmp_path / ".claude" / "diamonds"
    diamonds.mkdir(parents=True)
    (diamonds / "active.yml").write_text("autonomous: true\nactive_diamonds: []\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(diamonds / "active.yml"),
               "content": "autonomous: false\nactive_diamonds: []\n"}}
    _call_main(mod, monkeypatch, tmp_path, payload)
    d = _decision(capsys)
    assert d and d["permissionDecision"] == "deny" and "un-declare" in d["permissionDecisionReason"]


def test_autonomous_active_reads_yaml_and_regex_forms(scripts_path, tmp_path, monkeypatch):
    mod = _import(scripts_path)
    monkeypatch.delenv("MYCELIUM_AUTONOMOUS_RUN", raising=False)
    diamonds = tmp_path / ".claude" / "diamonds"
    diamonds.mkdir(parents=True)
    (diamonds / "active.yml").write_text("autonomous: yes\n")
    assert mod.autonomous_active(str(tmp_path))
    (diamonds / "active.yml").write_text("autonomous: false\n")
    assert not mod.autonomous_active(str(tmp_path))
    assert mod._autonomous_in_text("- [broken\nautonomous: true\n")


def test_canvas_target_matches_by_real_path_anywhere(scripts_path, tmp_path):
    mod = _import(scripts_path)
    import _hook_input as hi
    assert mod._canvas_target(hi.resolve("/elsewhere/.claude/canvas/x.yml", str(tmp_path)))
    assert mod._canvas_target(hi.resolve(".claude/diamonds/sub/a.yaml", str(tmp_path)))
    assert not mod._canvas_target(hi.resolve("docs/notes.md", str(tmp_path)))


# ------------------------------------------------- the fire log must never change the verdict

def test_log_fire_writes_a_row_a_consumer_can_read(scripts_path, tmp_path, monkeypatch):
    """The guard is BLOCKING and wrote no record until v0.234.0, so how often it refused a
    write was unmeasurable — `check_retirement_candidates.py` could answer neither of its two
    questions for it."""
    mod = _import(scripts_path)
    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    mod._log_fire("blocked", "source_class,validated")
    rows = (tmp_path / ".claude/state/autonomous-evidence-guard-fires.jsonl").read_text().strip()
    import json
    row = json.loads(rows)
    assert row["outcome"] == "blocked"
    assert row["hook"] == "autonomous-evidence-guard.sh"
    assert row["detail"] == "source_class,validated"
    assert row["ts"].endswith("Z")


def test_log_fire_swallows_an_unwritable_target(scripts_path, tmp_path, monkeypatch):
    """THE CLAUSE THAT MATTERS, and it was hand-verified and never asserted until now.

    A guard that started DENYING WRITES because its own log could not be written would be a
    far worse defect than a missing row. Here PROJECT_DIR points at a regular file, so
    `os.makedirs` raises — and the function must still return without propagating.
    """
    mod = _import(scripts_path)
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")
    monkeypatch.setenv("PROJECT_DIR", str(blocker))
    mod._log_fire("blocked", "anything")  # must not raise


def test_log_fire_omits_an_empty_detail_rather_than_writing_a_blank(scripts_path, tmp_path, monkeypatch):
    """A row carries a label or no label; an empty string is neither, and a consumer
    counting labelled rows would count it."""
    mod = _import(scripts_path)
    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    mod._log_fire("blocked")
    import json
    row = json.loads((tmp_path / ".claude/state/autonomous-evidence-guard-fires.jsonl").read_text().strip())
    assert "detail" not in row
