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


def test_resolve_trace_references_flags_missing_target(tmp_path, scripts_path, monkeypatch):
    """Known-bad: trace edge points to a target_id that doesn't exist in any canvas."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(
        "opportunities:\n"
        "  - id: opp-001\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: 'user-needs#need-DOES-NOT-EXIST'\n",
    )
    (canvas_dir / "user-needs.yml").write_text(
        "user_needs:\n"
        "  - id: need-real\n",
    )
    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    graph, all_ids, _errors = validator.collect_trace_graph()
    ref_errors = validator.resolve_trace_references(graph, all_ids)
    assert any("does not resolve" in e for e in ref_errors)
    assert any("need-DOES-NOT-EXIST" in e for e in ref_errors)


def test_resolve_trace_references_passes_for_external_namespaces(tmp_path, scripts_path, monkeypatch):
    """Negative control: 'decision-log#...' / 'external#...' / 'memory#...' assumed valid."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(
        "opportunities:\n"
        "  - id: opp-001\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: 'decision-log#2026-04-09-pivot'\n"
        "        - target_id: 'external#some-doc'\n"
        "        - target_id: 'memory#corrections-2026-05-04'\n",
    )
    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    graph, all_ids, _errors = validator.collect_trace_graph()
    ref_errors = validator.resolve_trace_references(graph, all_ids)
    assert ref_errors == [], f"External namespace refs should pass: {ref_errors}"


def test_resolve_trace_references_flags_unknown_canvas_basename(tmp_path, scripts_path, monkeypatch):
    """Known-bad: target with no '#' but referencing a non-existent canvas basename."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(
        "opportunities:\n"
        "  - id: opp-001\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: 'nonexistent-canvas'\n",
    )
    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    graph, all_ids, _errors = validator.collect_trace_graph()
    ref_errors = validator.resolve_trace_references(graph, all_ids)
    assert any("nonexistent-canvas" in e for e in ref_errors)
    assert any("does not resolve to any canvas file" in e for e in ref_errors)


def test_detect_cycles_flags_simple_cycle(scripts_path):
    """Known-bad: A → B → A is a cycle."""
    validator = _import_validator(scripts_path)
    graph = {"A": {"B"}, "B": {"A"}}
    errors = validator.detect_cycles(graph)
    assert len(errors) == 1
    assert "cycle" in errors[0].lower()


def test_detect_cycles_dag_passes(scripts_path):
    """Negative control: a clean DAG returns no errors."""
    validator = _import_validator(scripts_path)
    graph = {"A": {"B", "C"}, "B": {"D"}, "C": {"D"}, "D": set()}
    errors = validator.detect_cycles(graph)
    assert errors == []


def test_detect_cycles_self_loop(scripts_path):
    """Known-bad: A → A (self-loop) is a cycle."""
    validator = _import_validator(scripts_path)
    graph = {"A": {"A"}}
    errors = validator.detect_cycles(graph)
    assert len(errors) == 1


def test_detect_cycles_three_node_cycle(scripts_path):
    """Known-bad: A → B → C → A is a cycle, all three named in error."""
    validator = _import_validator(scripts_path)
    graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    errors = validator.detect_cycles(graph)
    assert len(errors) == 1
    msg = errors[0]
    assert "A" in msg and "B" in msg and "C" in msg


def test_detect_cycles_empty_graph_passes(scripts_path):
    validator = _import_validator(scripts_path)
    assert validator.detect_cycles({}) == []


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
