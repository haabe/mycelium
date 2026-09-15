"""v0.208.0: a claim of novelty must say what it was checked against."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_merge_markers.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cmm", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cmm"] = m
    spec.loader.exec_module(m)
    return m


def _canvas(tmp_path, doc, name="go-to-market.yml"):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(yaml.safe_dump(doc, sort_keys=False))
    return d


def test_an_unmarked_novelty_claim_is_reported_with_its_entry(tmp_path):
    d = _canvas(tmp_path, {"study": {"id": "s1", "note": "THE ONE ORIGINAL, CHEAP, UNTESTED MECHANISM the sweep surfaced."}})
    out, marked = _mod().findings(d)
    assert len(out) == 1 and out[0][0] == "go-to-market" and out[0][1] == "s1"
    assert marked == 0


def test_a_marked_claim_is_counted_not_reported(tmp_path):
    d = _canvas(tmp_path, {"study": {"id": "s1", "checked_skills": "2026-09-14",
                                     "note": "the one original untested mechanism"}})
    out, marked = _mod().findings(d)
    assert out == [] and marked == 1
    d2 = _canvas(tmp_path, {"comp": [{"id": "comp-1", "checked_against": "landscape.yml",
                                      "note": "nobody has built it"}]}, name="landscape.yml")
    out, marked = _mod().findings(d2)
    assert out == [] and marked == 2   # both files are in the dir now


def test_ordinary_prose_and_scoped_claims_are_silent(tmp_path):
    d = _canvas(tmp_path, {"x": {"id": "x", "note": "This lever has never been tried here — zero instances across 25 channels."},
                           "y": {"id": "y", "note": "Bentes drove the ship."}})
    out, _ = _mod().findings(d)
    assert out == []


def test_strict_exits_1_only_with_findings(tmp_path, capsys):
    mod = _mod()
    d = _canvas(tmp_path, {"s": {"id": "s", "note": "nobody has built this"}})
    assert mod.main(["--canvas-dir", str(d), "--strict"]) == 1
    assert "UNMARKED [go-to-market] s" in capsys.readouterr().out
    assert mod.main(["--canvas-dir", str(tmp_path / "none")]) == 2
