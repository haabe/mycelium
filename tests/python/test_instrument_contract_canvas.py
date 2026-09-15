"""v0.207.0: frozen predictions in canvas files are visible to the contract check.

On 2026-09-03 the check reported "problems: 0" while human-tasks.yml carried a prediction
one day past its horizon; the task-staleness rule caught it and offered the wrong remedy.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import yaml


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_instrument_contract
    return check_instrument_contract


def _canvas(tmp_path, tasks):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "human-tasks.yml").write_text(yaml.safe_dump({"pending_tasks": tasks}, sort_keys=False))
    return tmp_path


def test_due_live_scored_and_undated_are_told_apart(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, [
        {"id": "ht-060", "frozen_prediction": "x", "horizon": "2026-09-02", "status": "waiting"},
        {"id": "ht-053", "frozen_prediction": "x", "horizon": "2026-12-01"},
        {"id": "ht-058", "frozen_prediction": "x", "horizon": "2026-08-20", "prediction_scored": "y"},
        {"id": "ht-055", "frozen_prediction": "x"},
    ])
    cp = mod.canvas_predictions(root, datetime.date(2026, 9, 3))
    assert [d[0] for d in cp["due"]] == ["human-tasks#ht-060"]
    assert cp["due"][0][2] == 1
    assert [x[0] for x in cp["live"]] == ["human-tasks#ht-053"]
    assert cp["scored"] == ["human-tasks#ht-058"]
    assert cp["undated"] == ["human-tasks#ht-055"]


def test_no_canvas_dir_is_empty_not_an_error(scripts_path, tmp_path):
    mod = _import(scripts_path)
    cp = mod.canvas_predictions(tmp_path, datetime.date(2026, 9, 3))
    assert all(v == [] for v in cp.values())


def test_the_report_names_the_due_prediction_and_not_a_nudge(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, [{"id": "ht-060", "frozen_prediction": "x", "horizon": "2026-09-02"}])
    (root / ".claude" / "evals" / "assumption-tests").mkdir(parents=True)
    mod.main(["--root", str(root), "--today", "2026-09-03"])
    out = capsys.readouterr().out
    assert "PREDICTIONS IN THE CANVAS, OUTSIDE THE CONTRACT — 1: 1 due" in out
    assert "DUE     human-tasks#ht-060 (horizon 2026-09-02, 1 days ago)" in out
    assert "the remedy is not a nudge" in out
