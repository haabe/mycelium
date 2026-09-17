"""Coverage proof for check_dod_shape.py.

The fixtures are the SHAPES from the dogfood L1 on 2026-09-16 and 2026-09-17, scaled down:
a bar buried under dated sub-keys, the same diamond after the notes moved to log[], and a
short L0. The numbers are what this script is for, so the tests assert numbers.
"""

import importlib.util
import json

import pytest
import yaml


@pytest.fixture
def mod(scripts_path):
    spec = importlib.util.spec_from_file_location("check_dod_shape",
                                                  scripts_path / "check_dod_shape.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _write(tmp_path, diamonds):
    p = tmp_path / "active.yml"
    p.write_text(yaml.safe_dump({"active_diamonds": diamonds}, sort_keys=False))
    return p


SHORT = {"id": "l0-purpose", "scale": "L0",
         "definition_of_done": {"outcome": "o" * 200, "signal": "s" * 400, "source": "brief"}}

BURIED = {"id": "l1-strategy", "scale": "L1",
          "definition_of_done": {
              "outcome": "o" * 100, "signal": "s" * 100,
              "kill_criterion": {"state": "k" * 100, "date": "2026-10-20",
                                 "sweep_2026_08_28": "n" * 3000,
                                 "ruling_20260906": "n" * 3000}}}

RETROFITTED = {"id": "l1-strategy", "scale": "L1",
               "definition_of_done": {
                   "outcome": "o" * 100, "signal": "s" * 100,
                   "kill_criterion": {"state": "k" * 100, "date": "2026-10-20"},
                   "log": [{"date": "2026-08-28", "text": "n" * 3000},
                           {"date": "2026-09-06", "text": "n" * 3000,
                            "superseded_2026_09_07": "a dated key INSIDE a log entry"}]}}


# ------------------------------------------------------------------ the motivating case

def test_dated_sub_keys_under_the_bar_are_reported_as_log_as_keys(mod):
    """THE FAILURE DIRECTION. The 2026-09-16 shape: updates written as dated fields of
    kill_criterion. If this stops being found, the script certifies the defect it exists for."""
    r = mod.measure(BURIED)
    assert r["log_as_keys"] == [
        "definition_of_done.kill_criterion.sweep_2026_08_28",
        "definition_of_done.kill_criterion.ruling_20260906",
    ]
    assert r["log"] == 0 and r["log_entries"] == 0
    assert r["bar"] > 6000, "the buried notes are inside the bar, and the bar size has to show it"


def test_the_same_diamond_after_the_retrofit(mod):
    """Notes moved to log[]: the bar shrinks, the log carries them, nothing is flagged.
    A dated key INSIDE a log entry is the key-shape guard's finding, not this script's."""
    r = mod.measure(RETROFITTED)
    assert r["log_as_keys"] == []
    assert r["log_entries"] == 2 and r["log"] > 6000
    assert r["bar"] < 400


def test_bar_log_and_other_partition_the_total(mod):
    r = mod.measure(SHORT)
    assert (r["bar"], r["log"], r["other"]) == (600, 0, len("brief"))
    assert r["total"] == r["bar"] + r["log"] + r["other"]


# ------------------------------------------------------------------ negative controls

def test_a_diamond_without_a_dod_is_skipped_not_scored_as_zero(mod):
    """A missing Definition of Done is step 7c's ABSENT branch. Reporting it here as 'bar 0'
    would read as the healthiest diamond on the page."""
    assert mod.measure({"id": "l2-x", "scale": "L2"}) is None
    assert mod.measure({"id": "l2-x", "definition_of_done": "a bare string"}) is None


def test_an_undated_key_is_not_flagged(mod):
    d = {"id": "x", "definition_of_done": {"outcome": "o", "signal": "s",
                                           "kill_criterion": {"state": "k", "premortem": "p",
                                                              "phase_2_plan": "not a date"}}}
    assert mod.measure(d)["log_as_keys"] == []


def test_no_size_threshold_is_applied(mod):
    """The script must not invent the number it was built to help measure. A 60k bar and a
    600-character bar both exit 0 with the same closing sentence and no WARN."""
    huge = {"id": "big", "scale": "L1",
            "definition_of_done": {"outcome": "o" * 60000, "signal": "s"}}
    text = mod.render([mod.measure(huge), mod.measure(SHORT)])
    assert "WARN" not in text and "too long" not in text.lower()
    assert "No size threshold is applied" in text


# ------------------------------------------------------------------ the command line

def test_cli_reports_every_diamond(mod, tmp_path, capsys):
    p = _write(tmp_path, [SHORT, BURIED])
    assert mod.main(["--diamonds", str(p)]) == 0
    out = capsys.readouterr().out
    assert "l0-purpose (L0): bar 600" in out
    assert "LOG-AS-KEYS: 2 dated key name(s)" in out


def test_cli_single_diamond_and_json(mod, tmp_path, capsys):
    p = _write(tmp_path, [SHORT, RETROFITTED])
    assert mod.main(["--diamonds", str(p), "--diamond-id", "l1-strategy", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in rows] == ["l1-strategy"]
    assert rows[0]["log_entries"] == 2


def test_cli_missing_file_exits_2(mod, tmp_path, capsys):
    assert mod.main(["--diamonds", str(tmp_path / "nope.yml")]) == 2
    assert "not found" in capsys.readouterr().err


def test_cli_unparseable_file_exits_2(mod, tmp_path, capsys):
    p = tmp_path / "active.yml"
    p.write_text("active_diamonds: [unclosed\n")
    assert mod.main(["--diamonds", str(p)]) == 2
    assert "could not be read" in capsys.readouterr().err


def test_a_file_with_no_diamonds_says_so(mod, tmp_path, capsys):
    p = _write(tmp_path, [])
    assert mod.main(["--diamonds", str(p)]) == 0
    assert "no diamond carries" in capsys.readouterr().out
