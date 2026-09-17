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


def test_a_score_under_a_dated_or_suffixed_key_counts_as_scored(scripts_path, tmp_path):
    """v0.226.3. Eleven of eleven DUE lines on the dogfood canvas were already scored, under keys
    this check did not read: `scored_at_horizon`, `scored_2026_08_18`, `outcome_scored`,
    `SCORED_2026_08_25_...`. A key that STARTS with `scored` is a score."""
    mod = _import(scripts_path)
    root = _canvas(tmp_path, [
        {"id": "ht-1", "frozen_prediction": "x", "horizon": "2026-08-01", "scored_at_horizon": "held"},
        {"id": "ht-2", "frozen_prediction": "x", "horizon": "2026-08-01", "scored_2026_08_18": "held"},
        {"id": "ht-3", "frozen_prediction": "x", "horizon": "2026-08-01", "outcome_scored": "class c"},
        {"id": "ht-4", "frozen_prediction": "x", "horizon": "2026-08-01", "SCORED_2026_08_25_ZERO": "0"},
    ])
    cp = mod.canvas_predictions(root, datetime.date(2026, 9, 3))
    assert cp["due"] == []
    assert sorted(cp["scored"]) == [f"human-tasks#ht-{n}" for n in (1, 2, 3, 4)]


def test_a_key_that_only_names_the_plan_is_not_a_score(scripts_path, tmp_path):
    """NEGATIVE CONTROL. The dangerous direction is hiding an unscored prediction, so the prefix is
    `scored`, never `score` or `outcome`: `score_by` is a date and `outcome_classes` is the plan."""
    mod = _import(scripts_path)
    root = _canvas(tmp_path, [
        {"id": "ht-5", "frozen_prediction": "x", "horizon": "2026-08-01", "score_by": "2026-08-01",
         "outcome_classes": "a, b, c", "scoring_rules": "frozen"},
    ])
    cp = mod.canvas_predictions(root, datetime.date(2026, 9, 3))
    assert [d[0] for d in cp["due"]] == ["human-tasks#ht-5"] and cp["scored"] == []


def test_a_closed_task_with_no_known_score_key_is_not_called_due(scripts_path, tmp_path, capsys):
    """A closed task whose score sits in prose is a bookkeeping gap, not overdue work, and telling
    its owner to "score it" every session teaches them to skim the list."""
    mod = _import(scripts_path)
    root = _canvas(tmp_path, [
        {"id": "ht-6", "frozen_prediction": "x", "horizon": "2026-08-01", "status": "completed",
         "closure_reason": "PREDICTION HELD, see above"},
        {"id": "ht-7", "frozen_prediction": "x", "horizon": "2026-08-01", "status": "waiting"},
    ])
    cp = mod.canvas_predictions(root, datetime.date(2026, 9, 3))
    assert [d[0] for d in cp["due"]] == ["human-tasks#ht-7"]
    assert [d[0] for d in cp["closed_unscored"]] == ["human-tasks#ht-6"]
    (root / ".claude" / "evals" / "assumption-tests").mkdir(parents=True)
    mod.main(["--root", str(root), "--today", "2026-09-03"])
    out = capsys.readouterr().out
    assert "CLOSED  human-tasks#ht-6" in out and "prediction_scored" in out
    assert "DUE     human-tasks#ht-6" not in out


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
