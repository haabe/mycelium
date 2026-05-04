"""Coverage proofs for parse_manifest.py CLI logic.

The existing test_parse_manifest.py uses subprocess — exercises the CLI surface
but coverage-py can't see subprocess execution from the parent test process,
which is why parse_manifest.py reports 0% coverage. These tests import main()
directly with sys.argv monkeypatched, so coverage actually counts.

Per G-V12: every validator/enforcer ships with a coverage proof that exercises
its own code paths, not just its observable I/O.
"""
import sys

import pytest


def _import_main(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import parse_manifest  # noqa: PLC0415
    return parse_manifest


def test_main_top_level_prints_files(
    scripts_path, project_dir, manifest_path, monkeypatch, capsys,
):
    """Direct main() invocation — coverage-visible."""
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "top_level"])
    pm = _import_main(scripts_path)
    # parse_manifest discovers manifest via Path(__file__) — symlink scripts_path
    # so the discovery resolves to project_dir's manifest.
    monkeypatch.setattr(pm.Path, "__file__", scripts_path / "parse_manifest.py", raising=False)
    pm.main()
    out = capsys.readouterr().out.strip().split()
    assert "CLAUDE.md" in out
    assert "AGENTS.md" in out


def test_main_unknown_key_exits_1(scripts_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "totally_made_up_key"])
    pm = _import_main(scripts_path)
    with pytest.raises(SystemExit) as ei:
        pm.main()
    assert ei.value.code == 1


def test_main_no_args_exits_1(scripts_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py"])
    pm = _import_main(scripts_path)
    with pytest.raises(SystemExit) as ei:
        pm.main()
    assert ei.value.code == 1


def test_main_directories_prints_paths(scripts_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "directories"])
    pm = _import_main(scripts_path)
    pm.main()
    out = capsys.readouterr().out.strip()
    assert ".claude/skills/" in out
    assert ".claude/engine/" in out


def test_main_evals_replace_resolves(scripts_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "evals_replace"])
    pm = _import_main(scripts_path)
    pm.main()
    out = capsys.readouterr().out.strip()
    assert ".claude/evals/scenarios/" in out


def test_main_metrics_adapters_resolves(scripts_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "metrics_adapters_framework"])
    pm = _import_main(scripts_path)
    pm.main()
    out = capsys.readouterr().out.strip()
    assert "github.md" in out


def test_main_project_state_resolves(scripts_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parse_manifest.py", "project_state"])
    pm = _import_main(scripts_path)
    pm.main()
    out = capsys.readouterr().out.strip()
    # project_state contains paths like .claude/memory/, .claude/state/
    assert ".claude/memory/" in out or ".claude/state/" in out
