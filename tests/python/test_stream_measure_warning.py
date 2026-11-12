"""A diamond that has not closed must not carry a measure keyed on the delivery stream.

WHAT WAS WRONG. A Definition of Done `measure` is read only after its diamond closes, and a delivery
stream never closes. The dogfood L4 that modelled the stream carried `measure: {source:
dora-metrics, ...}` and sat open 48 days with that block read by nothing, and no check said so.

FOUNDER RULING 2026-11-12, "Stream lives in dora-metrics": engine/diamond-rules.md says the stream
is measured in dora-metrics.yml, and validate_canvas warns (WARN tier) when a diamond that has not
closed carries a measure it can never reach.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "mycelium" / "scripts"))

import validate_canvas  # noqa: E402

RELEASED = "".join(f"      - {{decision: {x}, on: 2026-09-01}}\n"
                   for x in ("set_target", "start_experiment", "commit_to_build", "release"))
CLOSED = RELEASED + "      - {decision: close, on: 2026-10-01}\n"


def _canvas(tmp_path: Path, *, source: str = "dora-metrics", decisions: str = RELEASED,
            state: str = "active") -> Path:
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        "active_diamonds:\n"
        "  - id: l4-delivery\n"
        "    scale: L4\n"
        f"    state: {state}\n"
        "    confidence: 0.85\n"
        "    decisions:\n" + decisions +
        "    definition_of_done:\n"
        "      outcome: the framework ships well\n"
        "      signal: delivery health holds\n"
        "      measure:\n"
        f"        source: {source}\n"
        "        field: overall_classification\n"
        "        target: elite\n"
        "        check_after: 30d\n"
    )
    return canvas


def test_an_open_diamond_with_a_stream_measure_is_warned(tmp_path, capsys):
    """RED ON THE OLD CODE: no check looked, so the dogfood shape printed nothing."""
    canvas = _canvas(tmp_path)
    validate_canvas.print_advisory_warnings(canvas)
    out = capsys.readouterr().out
    assert "WARN (stream measure)" in out
    assert "l4-delivery" in out and "dora-metrics.yml" in out


@pytest.mark.parametrize("source", ["dora-metrics", "DORA", ".claude/canvas/dora-metrics.yml"])
def test_every_spelling_of_the_stream_is_read(tmp_path, source):
    assert len(validate_canvas.stream_measure_findings(_canvas(tmp_path, source=source))) == 1


@pytest.mark.parametrize("kwargs", [
    {"source": "manual"},                 # an outcome the diamond's own close can reach
    {"source": "github"},                 # a metric adapter, read after close as designed
    {"decisions": CLOSED},                # closed: the outcome loop does read its measure
    {"state": "killed"},                  # ended without a close: nothing is owed any more
])
def test_a_measure_its_close_can_reach_is_not_warned(tmp_path, kwargs):
    assert validate_canvas.stream_measure_findings(_canvas(tmp_path, **kwargs)) == []


def test_no_diamonds_file_and_a_broken_one_are_silent(tmp_path):
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    assert validate_canvas.stream_measure_findings(canvas) == []
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: [\n")
    assert validate_canvas.stream_measure_findings(canvas) == []
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: {}\n")
    assert validate_canvas.stream_measure_findings(canvas) == []


def test_without_scale_locks_the_recorded_phase_is_read(monkeypatch):
    monkeypatch.setitem(sys.modules, "scale_locks", None)   # import fails, as on a partial install
    phase_of = validate_canvas._phase_reader()
    assert phase_of({"phase": "complete"}) == "complete"


def test_diamond_rules_says_where_the_stream_lives():
    text = (ROOT / "plugins" / "mycelium" / "engine" / "diamond-rules.md").read_text()
    assert "A continuous delivery stream is measured in `dora-metrics.yml`, not on a diamond" in text
    assert "WARN (stream measure)" in text
