"""Tests for check_coverage_floor.py — the per-file coverage gate."""
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts" / "check_coverage_floor.py"
_spec = importlib.util.spec_from_file_location("check_coverage_floor", _SCRIPT)
ccf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccf)


def _make_root(tmp_path, scripts: dict, integrations: dict | None = None):
    """Create a fake repo root with scripts/ (+ optional integrations/) .py files."""
    sdir = tmp_path / "plugins" / "mycelium" / "scripts"
    sdir.mkdir(parents=True)
    (sdir / "__init__.py").write_text("")  # must be excluded
    for name in scripts:
        (sdir / name).write_text("x = 1\n")
    if integrations:
        idir = tmp_path / "plugins" / "mycelium" / "integrations" / "opencode"
        idir.mkdir(parents=True)
        for name in integrations:
            (idir / name).write_text("y = 1\n")
    return tmp_path


def _cov_json(tmp_path, pct_by_relpath: dict):
    files = {rel: {"summary": {"percent_covered": pct}} for rel, pct in pct_by_relpath.items()}
    p = tmp_path / "coverage.json"
    p.write_text(json.dumps({"files": files}))
    return p


def test_all_above_floor_passes(tmp_path, capsys):
    root = _make_root(tmp_path, {"a.py": 90, "b.py": 80})
    _cov_json(tmp_path, {
        "plugins/mycelium/scripts/a.py": 90.0,
        "plugins/mycelium/scripts/b.py": 80.0,
    })
    rc = ccf.main(["--root", str(root), "--floor", "70"])
    assert rc == 0
    assert "All 2 shipped scripts" in capsys.readouterr().out


def test_untested_script_absent_from_report_fails(tmp_path, capsys):
    # b.py exists on disk but is NOT in coverage.json — the new-untested-script case.
    root = _make_root(tmp_path, {"a.py": 90, "b.py": 0})
    _cov_json(tmp_path, {"plugins/mycelium/scripts/a.py": 90.0})
    rc = ccf.main(["--root", str(root), "--floor", "70"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "b.py" in err and "NO COVERAGE" in err


def test_below_floor_fails(tmp_path, capsys):
    root = _make_root(tmp_path, {"a.py": 50})
    _cov_json(tmp_path, {"plugins/mycelium/scripts/a.py": 50.0})
    rc = ccf.main(["--root", str(root), "--floor", "70"])
    assert rc == 1
    assert "50%" in capsys.readouterr().err


def test_floor_is_configurable(tmp_path):
    root = _make_root(tmp_path, {"a.py": 65})
    _cov_json(tmp_path, {"plugins/mycelium/scripts/a.py": 65.0})
    assert ccf.main(["--root", str(root), "--floor", "60"]) == 0
    assert ccf.main(["--root", str(root), "--floor", "70"]) == 1


def test_init_py_excluded(tmp_path):
    # Only __init__.py present (always excluded) → nothing to check → passes.
    root = _make_root(tmp_path, {})
    _cov_json(tmp_path, {})
    assert ccf.main(["--root", str(root), "--floor", "70"]) == 0


def test_integrations_dir_is_scanned(tmp_path, capsys):
    root = _make_root(tmp_path, {"a.py": 90}, integrations={"check-tool-calling.py": 0})
    _cov_json(tmp_path, {"plugins/mycelium/scripts/a.py": 90.0})  # integration file absent
    rc = ccf.main(["--root", str(root), "--floor", "70"])
    assert rc == 1
    assert "check-tool-calling.py" in capsys.readouterr().err


def test_basename_fallback_match(tmp_path):
    # coverage.json keyed by a differently-rooted path but same basename still resolves.
    root = _make_root(tmp_path, {"a.py": 90})
    _cov_json(tmp_path, {"/abs/elsewhere/a.py": 90.0})
    assert ccf.main(["--root", str(root), "--floor", "70"]) == 0


def test_missing_coverage_json_is_setup_error(tmp_path, capsys):
    root = _make_root(tmp_path, {"a.py": 90})
    rc = ccf.main(["--root", str(root), "--coverage-json", "nope.json", "--floor", "70"])
    assert rc == 2
    assert "coverage json not found" in capsys.readouterr().err


def test_evaluate_helper_directly(tmp_path):
    root = _make_root(tmp_path, {"a.py": 90, "b.py": 50})
    checked, violations = ccf.evaluate(root, {
        "plugins/mycelium/scripts/a.py": {"summary": {"percent_covered": 90.0}},
        "plugins/mycelium/scripts/b.py": {"summary": {"percent_covered": 50.0}},
    }, 70.0)
    assert checked == 2
    assert ("plugins/mycelium/scripts/b.py", 50.0) in violations
