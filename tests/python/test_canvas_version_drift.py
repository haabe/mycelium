"""Coverage for check_canvas_version_drift.py (v0.90.0).

THE DEFECT IT EXISTS FOR. A dogfood canvas asserted
`ai-tool-metrics.yml :: model_metrics.version: "Mycelium 0.16.1"` while the running
plugin was 0.89.0 — 73 releases behind, for three months. Nothing compared a version
a canvas CLAIMS against the version actually installed.

The two ways this check could rot, and the tests that stop them:

  1. IT PASSES WHEN IT COULD NOT LOOK. No readable plugin.json must be UNKNOWN
     (exit 2), never a clean 0. Same contract as every other check in this repo.
  2. IT CRIES WOLF. Canvases legitimately cite historical versions ("shipped in
     v0.70.0"). Flagging those makes it noise by day seven, and a muted check
     reads as coverage while providing none.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_canvas_version_drift.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cvd", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cvd"] = m
    spec.loader.exec_module(m)
    return m


def _project(tmp_path, canvas_yaml: str, version="0.89.0", name="ai-tool-metrics.yml"):
    fw = tmp_path / "fw" / ".claude-plugin"
    fw.mkdir(parents=True)
    (fw / "plugin.json").write_text(json.dumps({"version": version}))
    c = tmp_path / "proj" / ".claude" / "canvas"
    c.mkdir(parents=True)
    (c / name).write_text(canvas_yaml)
    return tmp_path / "proj", tmp_path / "fw"


# ---------------------------------------------------------------- the real case

def test_the_2026_08_05_defect_is_caught(tmp_path, capsys):
    proj, fw = _project(tmp_path, 'model_metrics:\n  version: "Mycelium 0.16.1 (framework version)"\n')
    rc = _mod().main(["--root", str(proj), "--framework-root", str(fw)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "0.16.1" in out and "0.89.0" in out
    assert "model_metrics.version" in out


def test_matching_version_is_clean(tmp_path, capsys):
    proj, fw = _project(tmp_path, 'model_metrics:\n  version: "Mycelium 0.89.0 (framework version)"\n')
    assert _mod().main(["--root", str(proj), "--framework-root", str(fw)]) == 0
    assert "OK" in capsys.readouterr().out


# ------------------------------------------------------- unknown is not ok

def test_no_plugin_json_is_unknown_not_ok(tmp_path, capsys):
    proj, _ = _project(tmp_path, 'model_metrics:\n  version: "Mycelium 0.16.1"\n')
    rc = _mod().main(["--root", str(proj), "--framework-root", str(tmp_path / "nowhere")])
    assert rc == 2
    assert "UNKNOWN" in capsys.readouterr().out


# ------------------------------------------------------------- no wolf-crying

@pytest.mark.parametrize("body", [
    # historical citations in PROSE must never fire — canvases are full of them
    'notes: "shipped in Mycelium 0.70.0; regression since 0.61.0"\n',
    'summary: "Mycelium 0.16.1 was the version at the time of the 2026-05 assessment"\n',
    # a `version` key that is not about the framework belongs to someone else
    'model_metrics:\n  version: "Claude Opus 4.5"\n',
    'dependency:\n  version: "1.2.3"\n',
    # the integer schema revision must not be confused for a framework version
    "_meta:\n  version: 1\n",
    "schema_version: 1\n",
])
def test_does_not_fire_on_non_claims(tmp_path, body):
    proj, fw = _project(tmp_path, body)
    assert _mod().main(["--root", str(proj), "--framework-root", str(fw)]) == 0


def test_an_unparseable_canvas_does_not_crash_the_check(tmp_path):
    proj, fw = _project(tmp_path, "this: [is: not: valid: yaml\n")
    assert _mod().main(["--root", str(proj), "--framework-root", str(fw)]) == 0
