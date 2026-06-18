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


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import autonomous_evidence_guard  # noqa: PLC0415

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


def test_main_fail_open_bad_json_in_process(scripts_path, monkeypatch, tmp_path, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr("sys.argv", ["autonomous_evidence_guard.py", str(tmp_path)])
    monkeypatch.setattr("sys.stdin", io.StringIO("not json{{"))
    monkeypatch.setenv("MYCELIUM_AUTONOMOUS_RUN", "1")
    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code in (0, None)
    assert capsys.readouterr().out.strip() == ""


def test_fail_open_on_unparseable_stdin(scripts_path, tmp_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "autonomous_evidence_guard.py"),
         str(tmp_path)],
        input="not json{{", capture_output=True, text=True, check=False,
        env={"MYCELIUM_AUTONOMOUS_RUN": "1", "PATH": __import__("os").environ["PATH"]},
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""
