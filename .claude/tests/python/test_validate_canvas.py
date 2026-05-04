"""Coverage proofs for validate_canvas.py.

Per G-V12 (corrections.md 2026-05-04 — graduated from "validator passes on
incomplete checks" recurring pattern): every validator ships with a test that
fails on a known-bad input.
"""
import sys
import textwrap
from pathlib import Path


def _import_validator(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import validate_canvas  # noqa: PLC0415
    return validate_canvas


def test_collect_trace_graph_flags_duplicate_ids_within_file(tmp_path, scripts_path, monkeypatch):
    """Known-bad input: two entries with id 'comp-007' in the same file → duplicate error."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(textwrap.dedent("""\
        components:
          - id: comp-007
            name: First
          - id: comp-007
            name: Second (collision — known-bad)
    """))

    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    _graph, _ids, errors = validator.collect_trace_graph()

    assert any("duplicate id 'comp-007'" in e for e in errors), (
        f"Validator did not catch the planted duplicate. errors={errors}"
    )
    assert any("landscape.yml" in e for e in errors)


def test_collect_trace_graph_passes_when_ids_unique(tmp_path, scripts_path, monkeypatch):
    """Negative control: unique ids → no duplicate errors raised."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(textwrap.dedent("""\
        components:
          - id: comp-001
            name: First
          - id: comp-002
            name: Second
    """))

    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    _graph, _ids, errors = validator.collect_trace_graph()

    duplicate_errors = [e for e in errors if "duplicate id" in e]
    assert duplicate_errors == [], f"False positive on unique IDs: {duplicate_errors}"


def test_collect_trace_graph_handles_multiple_distinct_duplicates(tmp_path, scripts_path, monkeypatch):
    """Known-bad: two different IDs each appearing twice → both reported, sorted."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(textwrap.dedent("""\
        opportunities:
          - id: opp-aaa
          - id: opp-bbb
          - id: opp-aaa
          - id: opp-bbb
    """))

    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    _graph, _ids, errors = validator.collect_trace_graph()

    duplicate_errors = [e for e in errors if "duplicate id" in e]
    assert len(duplicate_errors) == 2
    assert any("'opp-aaa'" in e for e in duplicate_errors)
    assert any("'opp-bbb'" in e for e in duplicate_errors)
