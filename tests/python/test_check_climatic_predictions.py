"""Tests for check_climatic_predictions.py.

The behaviours worth pinning are not "does it parse YAML". They are the three
ways a forecasting record quietly stops being one:

  1. Predictions come due and nobody scores them.
  2. A prediction carries no due date, so it can never be overdue, so it is free
     to be right forever.
  3. Every scored prediction held, which means none was ever at risk.

Each has a test below. The third is advisory in the tool and still tested,
because an advisory line that silently stops appearing is the same as a check
that silently stops running.
"""

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "mycelium"
    / "scripts"
    / "check_climatic_predictions.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("check_climatic_predictions", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_climatic_predictions"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mod():
    return _load()


def _write(root: Path, body: str) -> Path:
    d = root / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "landscape.yml").write_text(body)
    return root


TODAY = dt.date(2026, 8, 5)


def test_missing_landscape_is_unknown_not_clean(mod, tmp_path):
    """The first draft returned a clean 0 here, reasoning that flagging a fresh
    project would make the check noise on day one. `check_empty_input_honesty.py`
    rejected that on the first run and was right: a check that reports a pass over
    an empty repository has verified nothing and said everything is fine — the
    blind-green shape (opp-023). The rationalisation was persuasive, which is why
    the guard is a mechanism and not a habit."""
    preds, map_exists, err = mod._load_predictions(
        tmp_path / ".claude" / "canvas" / "landscape.yml"
    )
    assert preds == []
    assert map_exists is False
    assert err is not None


def test_map_with_no_predictions_is_a_finding(mod, tmp_path):
    """The detection the empty-input guard forced into existence. A map holding
    components but no predictions means Step 7 never ran: someone mapped positions
    and emitted nothing that could turn out wrong."""
    _write(
        tmp_path,
        "components:\n  - id: comp-001\n    name: a\n    evolution_stage: genesis\n",
    )
    preds, map_exists, err = mod._load_predictions(
        tmp_path / ".claude" / "canvas" / "landscape.yml"
    )
    assert preds == []
    assert map_exists is True
    assert err is None


def test_overdue_open_prediction_is_flagged(mod, tmp_path):
    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: climpred-001\n"
        "    pattern: inertia\n"
        "    prediction: p\n"
        "    made_on: '2026-05-01'\n"
        "    due: '2026-07-01'\n"
        "    status: open\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    res = mod.analyse(preds, TODAY)
    assert len(res["due"]) == 1
    assert res["due"][0][1] == 35  # overdue by exactly the day count, not "recently"


def test_missing_status_counts_as_open_not_settled(mod, tmp_path):
    """An entry with no status has not been settled. Defaulting it to settled
    would be the absent-read-as-negative failure removed elsewhere (v0.92.0)."""
    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: climpred-001\n"
        "    pattern: inertia\n"
        "    prediction: p\n"
        "    due: '2026-07-01'\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    assert len(mod.analyse(preds, TODAY)["due"]) == 1


def test_undated_prediction_is_flagged_separately(mod, tmp_path):
    """The silent-forever case. It never comes due, so a due-date check alone
    would report it clean in perpetuity."""
    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: climpred-002\n"
        "    pattern: inertia\n"
        "    prediction: p\n"
        "    status: open\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    res = mod.analyse(preds, TODAY)
    assert len(res["undated"]) == 1
    assert res["due"] == []


def test_scored_predictions_are_not_due(mod, tmp_path):
    for status in ("held", "refuted", "unscoreable"):
        _write(
            tmp_path,
            "climatic_predictions:\n"
            "  - id: climpred-003\n"
            "    pattern: everything-evolves\n"
            "    prediction: p\n"
            "    due: '2026-01-01'\n"
            f"    status: {status}\n",
        )
        preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
        res = mod.analyse(preds, TODAY)
        assert res["due"] == [], status
        assert len(res["scored"]) == 1, status


def test_never_refuted_record_is_detectable(mod, tmp_path):
    """A record that has never been wrong was not at risk. The tool reports this
    advisorily; the signal it rests on is asserted here."""
    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: a\n    pattern: inertia\n    prediction: p\n    due: '2026-01-01'\n    status: held\n"
        "  - id: b\n    pattern: inertia\n    prediction: p\n    due: '2026-01-02'\n    status: held\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    res = mod.analyse(preds, TODAY)
    assert len(res["scored"]) == 2
    assert res["refuted"] == []  # this emptiness is the finding

    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: a\n    pattern: inertia\n    prediction: p\n    due: '2026-01-01'\n    status: held\n"
        "  - id: b\n    pattern: inertia\n    prediction: p\n    due: '2026-01-02'\n    status: refuted\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    assert len(mod.analyse(preds, TODAY)["refuted"]) == 1


def test_unused_patterns_reported(mod, tmp_path):
    _write(
        tmp_path,
        "climatic_predictions:\n"
        "  - id: a\n    pattern: inertia\n    prediction: p\n    due: '2027-01-01'\n    status: open\n",
    )
    preds, _, _ = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    unused = mod.analyse(preds, TODAY)["unused_patterns"]
    assert "inertia" not in unused
    assert len(unused) == len(mod.PATTERNS) - 1


def test_unparseable_canvas_is_unknown_never_clean(mod, tmp_path):
    """A check that cannot run must not report a pass — the fail-open shape this
    project has logged repeatedly."""
    _write(tmp_path, "climatic_predictions: [unclosed\n")
    _, _, err = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    assert err is not None


def test_non_list_predictions_is_unknown(mod, tmp_path):
    _write(tmp_path, "climatic_predictions: not-a-list\n")
    _, _, err = mod._load_predictions(tmp_path / ".claude" / "canvas" / "landscape.yml")
    assert err is not None


# --- CLI surface -----------------------------------------------------------
# The logic tests above exercise _load_predictions and analyse. main() and
# _report are the parts a consumer actually runs, and the per-file coverage
# floor caught them untested — the script-level analog of the same gap G-V12
# exists to close. Exit codes are the contract: 0 clean, 1 findings, 2 UNKNOWN.


def _run(mod, monkeypatch, root, today="2026-08-05"):
    argv = ["check_climatic_predictions.py", "--root", str(root)]
    if today:
        argv += ["--today", today]
    monkeypatch.setattr(sys, "argv", argv)
    return mod.main()


def test_main_exits_2_when_there_is_no_map(mod, monkeypatch, tmp_path, capsys):
    """UNKNOWN, never clean. This is the assertion check_empty_input_honesty.py
    enforces from the outside; pinning it here means a future refactor that
    reintroduces the vacuous pass fails in this file too."""
    assert _run(mod, monkeypatch, tmp_path) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_main_exits_1_when_a_map_predicts_nothing(mod, monkeypatch, tmp_path, capsys):
    _write(tmp_path, "components:\n  - id: comp-001\n    name: a\n")
    assert _run(mod, monkeypatch, tmp_path) == 1
    assert "Step 7" in capsys.readouterr().out


def test_main_exits_1_on_overdue_and_names_it(mod, monkeypatch, tmp_path, capsys):
    _write(
        tmp_path,
        "components: [{id: comp-001, name: a}]\n"
        "climatic_predictions:\n"
        "  - id: climpred-009\n"
        "    pattern: inertia\n"
        "    prediction: the thing happens\n"
        "    due: '2026-07-01'\n"
        "    status: open\n",
    )
    assert _run(mod, monkeypatch, tmp_path) == 1
    out = capsys.readouterr().out
    assert "OVERDUE by 35d" in out
    assert "climpred-009" in out


def test_main_exits_0_when_nothing_is_due(mod, monkeypatch, tmp_path, capsys):
    _write(
        tmp_path,
        "components: [{id: comp-001, name: a}]\n"
        "climatic_predictions:\n"
        "  - id: climpred-010\n"
        "    pattern: inertia\n"
        "    prediction: p\n"
        "    due: '2027-01-01'\n"
        "    status: open\n",
    )
    assert _run(mod, monkeypatch, tmp_path) == 0
    assert "none due" in capsys.readouterr().out


def test_main_rejects_a_bad_today(mod, monkeypatch, tmp_path, capsys):
    _write(tmp_path, "components: [{id: comp-001, name: a}]\n")
    assert _run(mod, monkeypatch, tmp_path, today="not-a-date") == 2
    assert "not an ISO date" in capsys.readouterr().err


def test_main_exits_2_on_unparseable_canvas(mod, monkeypatch, tmp_path, capsys):
    _write(tmp_path, "climatic_predictions: [unclosed\n")
    assert _run(mod, monkeypatch, tmp_path) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_report_prints_the_never_refuted_note_on_a_clean_run(
    mod, monkeypatch, tmp_path, capsys
):
    """The advisory rides along on exit 0. An advisory that only appears on
    failure would never be seen by the corpus it is about — a record of
    predictions that all held is exactly the one that exits clean."""
    _write(
        tmp_path,
        "components: [{id: comp-001, name: a}]\n"
        "climatic_predictions:\n"
        "  - id: a\n    pattern: inertia\n    prediction: p\n"
        "    due: '2026-01-01'\n    status: held\n",
    )
    assert _run(mod, monkeypatch, tmp_path) == 0
    out = capsys.readouterr().out
    assert "never been wrong was not at risk" in out
    assert "COVERAGE" in out  # unused patterns reported too
