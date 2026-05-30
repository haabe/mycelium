"""Coverage proofs for scope_check.py (PreToolUse scope-gate hook).

Per G-V12: every enforcer ships with a coverage proof. scope_check.py is on
the critical path for L4 delivery scope enforcement — silent breakage = scope
discipline disappears with no signal. Tests exercise main() directly via
monkeypatched sys.argv + sys.stdin so coverage-py can see the lines.

Both allow and deny exit 0 (the deny payload is in stdout JSON). The test
contract: did the hook print a deny payload, or stay silent (allow)?
"""
import io
import json
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import scope_check  # noqa: PLC0415
    return scope_check


def _run_main(scripts_path, monkeypatch, capsys, *, state_file, project_dir, hook_input):
    """Drive scope_check.main() with controlled argv + stdin. Returns (exit_code, stdout_dict_or_None)."""
    monkeypatch.setattr(sys, "argv", ["scope_check.py", str(state_file), str(project_dir)])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(hook_input)))

    sc = _import(scripts_path)
    with pytest.raises(SystemExit) as ei:
        sc.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out) if out else None
    return ei.value.code, payload


def test_no_state_file_allows(scripts_path, tmp_path, monkeypatch, capsys):
    """state_file missing → emit_allow (silent, no payload)."""
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=tmp_path / "nonexistent.json",
        project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/main.py"}},
    )
    assert code == 0
    assert payload is None  # silent allow


def test_corrupt_state_denies(scripts_path, tmp_path, monkeypatch, capsys):
    """Known-bad: corrupt state JSON → emit_deny."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text("{ this is not valid json")
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file,
        project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/main.py"}},
    )
    assert code == 0
    assert payload is not None
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "corrupt" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_state_wrong_shape_denies(scripts_path, tmp_path, monkeypatch, capsys):
    """Known-bad: state is a list instead of object → emit_deny."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text("[]")
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file,
        project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/main.py"}},
    )
    assert code == 0
    assert payload is not None
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_claude_dir_always_allowed(scripts_path, tmp_path, monkeypatch, capsys):
    """.claude/** edits always allow even when scope is declared."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-test",
        "in_scope_paths": ["src/specific/**"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": ".claude/canvas/foo.yml"}},
    )
    assert code == 0
    assert payload is None  # silent allow


def test_in_scope_match_allows(scripts_path, tmp_path, monkeypatch, capsys):
    """File in declared in_scope → emit_allow."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "in_scope_paths": ["src/feat/**", "tests/feat/**"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/feat/api.py"}},
    )
    assert code == 0
    assert payload is None


def test_out_of_scope_path_denies(scripts_path, tmp_path, monkeypatch, capsys):
    """Known-bad: file matches out_of_scope_paths → emit_deny."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "in_scope_paths": ["src/**"],
        "out_of_scope_paths": ["src/legacy/**"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/legacy/old.py"}},
    )
    assert code == 0
    assert payload is not None
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "out_of_scope_paths" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_not_in_scope_denies(scripts_path, tmp_path, monkeypatch, capsys):
    """Known-bad: file not matching any in_scope pattern → emit_deny."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "in_scope_paths": ["src/feat/**"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/other/api.py"}},
    )
    assert code == 0
    assert payload is not None
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "not in in_scope_paths" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_empty_in_scope_allows(scripts_path, tmp_path, monkeypatch, capsys):
    """No scope declared → permissive (no in_scope_paths field)."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({"diamond_id": "L4-feat"}))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/anywhere.py"}},
    )
    assert code == 0
    assert payload is None


def test_no_file_path_in_input_allows(scripts_path, tmp_path, monkeypatch, capsys):
    """Hook input has no file_path → allow (e.g., non-file tool calls)."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({"in_scope_paths": ["src/**"]}))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {}},
    )
    assert code == 0
    assert payload is None


def test_corrupt_hook_input_allows(scripts_path, tmp_path, monkeypatch, capsys):
    """Hook stdin is not JSON → allow (defensive: hook contract violated by caller)."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({"in_scope_paths": ["src/**"]}))
    monkeypatch.setattr(sys, "argv", ["scope_check.py", str(state_file), str(tmp_path)])
    monkeypatch.setattr(sys, "stdin", io.StringIO("not valid json"))
    sc = _import(scripts_path)
    with pytest.raises(SystemExit) as ei:
        sc.main()
    assert ei.value.code == 0
    assert capsys.readouterr().out.strip() == ""


def test_no_args_denies(scripts_path, monkeypatch, capsys):
    """Known-bad: invoked without state_file/project_dir → emit_deny (hook wrapper bug)."""
    monkeypatch.setattr(sys, "argv", ["scope_check.py"])
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    sc = _import(scripts_path)
    with pytest.raises(SystemExit):
        sc.main()
    out = capsys.readouterr().out.strip()
    assert out
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "without required arguments" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_spec_nested_in_scope_works(scripts_path, tmp_path, monkeypatch, capsys):
    """spec.in_scope_paths (nested format) works equivalently to top-level."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "spec": {"in_scope_paths": ["src/feat/**"]},
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/feat/api.py"}},
    )
    assert code == 0
    assert payload is None  # in_scope match → allow


def test_single_star_does_not_leak_into_subdir(scripts_path, tmp_path, monkeypatch, capsys):
    """H2 regression: a single-star in_scope pattern must NOT match across '/'.

    With the old fnmatch behavior, 'src/feat/*' matched 'src/feat/legacy/old.py'
    (because fnmatch '*' eats '/'), silently widening scope. Segment-aware
    globbing denies it.
    """
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "in_scope_paths": ["src/feat/*"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/feat/legacy/old.py"}},
    )
    assert code == 0
    assert payload is not None
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_double_star_matches_any_depth(scripts_path, tmp_path, monkeypatch, capsys):
    """'**' still matches across segments so existing scope plans keep working."""
    state_file = tmp_path / "active-execution.json"
    state_file.write_text(json.dumps({
        "diamond_id": "L4-feat",
        "in_scope_paths": ["src/feat/**"],
    }))
    code, payload = _run_main(
        scripts_path, monkeypatch, capsys,
        state_file=state_file, project_dir=tmp_path,
        hook_input={"tool_input": {"file_path": "src/feat/deeply/nested/api.py"}},
    )
    assert code == 0
    assert payload is None  # deep match → allow
