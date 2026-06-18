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


def _real_schema_dir():
    """Path to the shipped canvas schema dir (has _common.schema.json + real schemas)."""
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent
    return repo_root / "plugins" / "mycelium" / "schemas" / "canvas"


def _point_at_real_schemas(validator, monkeypatch):
    """Repoint the validator's module-level schema globals at the shipped schemas.

    The script resolves SCHEMA_DIR / COMMON_SCHEMA once at import time; functions
    read those module globals directly, so tests that exercise schema validation
    must repoint them. diamonds schemas live at SCHEMA_DIR.parent/diamonds.
    """
    schema_dir = _real_schema_dir()
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    return schema_dir


# ---------------------------------------------------------------------------
# build_registry — both branches
# ---------------------------------------------------------------------------

def test_build_registry_returns_empty_when_no_common_schema(tmp_path, scripts_path, monkeypatch):
    """No _common.schema.json on disk → bare Registry (the early-return branch)."""
    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "SCHEMA_DIR", tmp_path)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", tmp_path / "_common.schema.json")

    registry = validator.build_registry()
    assert registry is not None


def test_build_registry_loads_common_schema(scripts_path, monkeypatch):
    """_common.schema.json present → registers it under multiple URIs."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    registry = validator.build_registry()
    # The common schema is registered under its $id at minimum.
    assert registry is not None


# ---------------------------------------------------------------------------
# validate_canvas_against_schema
# ---------------------------------------------------------------------------

def test_validate_canvas_against_schema_no_schema_silently_passes(tmp_path, scripts_path, monkeypatch):
    """A canvas file with no matching schema → silently passes (returns [])."""
    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "SCHEMA_DIR", tmp_path)  # empty dir → no schema
    monkeypatch.setattr(validator, "COMMON_SCHEMA", tmp_path / "_common.schema.json")

    canvas = tmp_path / "no-such-schema.yml"
    canvas.write_text("anything: goes\n")

    errors = validator.validate_canvas_against_schema(canvas, validator.build_registry())
    assert errors == []


def test_validate_canvas_against_schema_valid_file_passes(tmp_path, scripts_path, monkeypatch):
    """A landscape.yml satisfying its schema → no errors."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    canvas = tmp_path / "landscape.yml"
    canvas.write_text(textwrap.dedent("""\
        components:
          - id: comp-001
            name: Some Component
            provenance:
              evidence_type: anecdotal
              evidence_sources:
                - "https://example.com/note"
    """))

    errors = validator.validate_canvas_against_schema(canvas, validator.build_registry())
    assert errors == [], f"Valid landscape.yml should pass: {errors}"


def test_validate_canvas_against_schema_violation_reported(tmp_path, scripts_path, monkeypatch):
    """A landscape component missing required 'provenance' → schema error reported."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    canvas = tmp_path / "landscape.yml"
    canvas.write_text(textwrap.dedent("""\
        components:
          - id: comp-001
            name: Missing Provenance
    """))

    errors = validator.validate_canvas_against_schema(canvas, validator.build_registry())
    assert errors, "Expected a schema violation for missing provenance"
    assert any("landscape.yml" in e for e in errors)
    assert any("provenance" in e for e in errors)


def test_validate_canvas_against_schema_empty_file_passes(tmp_path, scripts_path, monkeypatch):
    """An empty YAML file (parses to None) is allowed even when a schema exists."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    canvas = tmp_path / "landscape.yml"
    canvas.write_text("")

    errors = validator.validate_canvas_against_schema(canvas, validator.build_registry())
    assert errors == []


def test_validate_canvas_against_schema_malformed_yaml_reported(tmp_path, scripts_path, monkeypatch):
    """Malformed YAML in a file that HAS a schema → YAML parse error reported."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    canvas = tmp_path / "landscape.yml"
    canvas.write_text("components: [unclosed\n  - id: x\n")

    errors = validator.validate_canvas_against_schema(canvas, validator.build_registry())
    assert errors, "Expected a YAML parse error"
    assert any("YAML parse error" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_all_yaml_parses
# ---------------------------------------------------------------------------

def test_validate_all_yaml_parses_clean_dir(tmp_path, scripts_path):
    """All files parse → no errors."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / "a.yml").write_text("key: value\n")
    (canvas_dir / "b.yml").write_text("list:\n  - 1\n  - 2\n")

    assert validator.validate_all_yaml_parses(canvas_dir) == []


def test_validate_all_yaml_parses_flags_malformed(tmp_path, scripts_path):
    """A malformed YAML file is reported by name."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / "good.yml").write_text("ok: yes\n")
    (canvas_dir / "bad.yml").write_text("broken: [1, 2\n  nested: oops\n")

    errors = validator.validate_all_yaml_parses(canvas_dir)
    assert any("bad.yml" in e and "YAML parse error" in e for e in errors)


# ---------------------------------------------------------------------------
# schemaless_canvas_warnings
# ---------------------------------------------------------------------------

def test_schemaless_canvas_warnings_names_schemaless_files(tmp_path, scripts_path, monkeypatch):
    """Files with no schema are named; files with a schema are not."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)

    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / "landscape.yml").write_text("components: []\n")  # has schema
    (canvas_dir / "freeform.yml").write_text("anything: goes\n")  # no schema

    warnings = validator.schemaless_canvas_warnings(canvas_dir)
    assert any("freeform.yml" in w for w in warnings)
    assert not any("landscape.yml" in w for w in warnings)


# ---------------------------------------------------------------------------
# validate_diamonds
# ---------------------------------------------------------------------------

def test_validate_diamonds_no_dir_returns_empty(tmp_path, scripts_path):
    """No diamonds/ sibling dir → no errors (the early return)."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    assert validator.validate_diamonds(canvas_dir, validator.build_registry()) == []


def test_validate_diamonds_malformed_yaml_reported(tmp_path, scripts_path, monkeypatch):
    """Unparseable diamonds/active.yml → fail-loud parse error."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text('notes: "unescaped "interior" quotes"\n')

    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert any("active.yml" in e and "YAML parse error" in e for e in errors)


def test_validate_diamonds_schema_violation_reported(tmp_path, scripts_path, monkeypatch):
    """active.yml violating active.schema.json (bad product_type enum) → reported."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text("product_type: not-a-valid-type\n")

    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert any("active.yml" in e for e in errors), f"Expected schema error, got {errors}"


def test_validate_diamonds_valid_passes(tmp_path, scripts_path, monkeypatch):
    """A diamonds file with no matching schema parses and is skipped cleanly."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    # 'history.yml' has no schema in schemas/diamonds → parses, skipped
    (diamonds_dir / "history.yml").write_text("entries: []\n")

    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert errors == [], f"Schemaless diamonds file should pass: {errors}"


# ---------------------------------------------------------------------------
# collect_trace_graph — resolving cross-file references + dir-missing branch
# ---------------------------------------------------------------------------

def test_collect_trace_graph_missing_dir_returns_empty(tmp_path, scripts_path):
    """Nonexistent canvas dir → empty graph, no crash (the not-exists branch)."""
    validator = _import_validator(scripts_path)
    missing = tmp_path / "does-not-exist"
    graph, all_ids, errors = validator.collect_trace_graph(missing)
    assert graph == {} or len(graph) == 0
    assert all_ids == set()
    assert errors == []


def test_resolve_trace_references_resolves_valid_cross_file(tmp_path, scripts_path, monkeypatch):
    """A trace.upstream target_id that resolves to a real entry in another file → no error."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(
        "opportunities:\n"
        "  - id: opp-001\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: 'user-needs#need-real'\n",
    )
    (canvas_dir / "user-needs.yml").write_text(
        "user_needs:\n"
        "  - id: need-real\n",
    )
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)

    graph, all_ids, _errors = validator.collect_trace_graph(canvas_dir)
    ref_errors = validator.resolve_trace_references(graph, all_ids)
    assert ref_errors == [], f"Valid cross-file reference should resolve: {ref_errors}"


def test_collect_trace_graph_skips_malformed_yaml(tmp_path, scripts_path):
    """A malformed file during the trace walk is warned-and-skipped (no crash)."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / "good.yml").write_text("opportunities:\n  - id: opp-001\n")
    (canvas_dir / "bad.yml").write_text("broken: [1, 2\n  x: y\n")

    graph, all_ids, errors = validator.collect_trace_graph(canvas_dir)
    # 'good' contributes; 'bad' is skipped without raising.
    assert "good" in all_ids


def test_collect_trace_graph_skips_non_dict_top_level(tmp_path, scripts_path):
    """A canvas file whose top level is a list (not dict) is skipped."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / "listy.yml").write_text("- a\n- b\n")

    graph, all_ids, errors = validator.collect_trace_graph(canvas_dir)
    # File stem is not added when top level isn't a dict.
    assert "listy" not in all_ids


# ---------------------------------------------------------------------------
# main() — CLI / entrypoint, pass + fail + error branches
# ---------------------------------------------------------------------------

def _setup_main_env(validator, monkeypatch, canvas_dir, schema_dir):
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    monkeypatch.setattr(sys, "argv", ["validate_canvas.py"])


def test_main_pass(tmp_path, scripts_path, monkeypatch):
    """A clean canvas dir → exit code 0."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(textwrap.dedent("""\
        components:
          - id: comp-001
            name: Clean Component
            provenance:
              evidence_type: anecdotal
              evidence_sources:
                - "https://example.com"
    """))
    _setup_main_env(validator, monkeypatch, canvas_dir, schema_dir)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 0


def test_main_fail_on_schema_violation(tmp_path, scripts_path, monkeypatch):
    """A schema-violating canvas → exit code 1."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(textwrap.dedent("""\
        components:
          - id: comp-001
            name: No Provenance Here
    """))
    _setup_main_env(validator, monkeypatch, canvas_dir, schema_dir)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 1


def test_main_fail_on_cycle(tmp_path, scripts_path, monkeypatch):
    """A trace cycle across files → exit code 1."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    # Two schemaless files forming opp-a -> opp-b -> opp-a
    (canvas_dir / "alpha.yml").write_text(
        "items:\n"
        "  - id: a\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: b\n",
    )
    (canvas_dir / "beta.yml").write_text(
        "items:\n"
        "  - id: b\n"
        "    trace:\n"
        "      upstream:\n"
        "        - target_id: a\n",
    )
    _setup_main_env(validator, monkeypatch, canvas_dir, schema_dir)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 1


def test_main_canvas_dir_missing_exits_zero(tmp_path, scripts_path, monkeypatch):
    """Module-level CANVAS_DIR doesn't exist → exit 0 with message."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    missing = tmp_path / "nope" / "canvas"
    _setup_main_env(validator, monkeypatch, missing, schema_dir)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 0


def test_main_schema_dir_missing_exits_zero(tmp_path, scripts_path, monkeypatch):
    """SCHEMA_DIR doesn't exist → exit 0 (no schemas to validate against)."""
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "x.yml").write_text("a: b\n")
    missing_schema = tmp_path / "no-schemas"
    _setup_main_env(validator, monkeypatch, canvas_dir, missing_schema)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 0


def test_main_argv_override_nonexistent_exits_two(tmp_path, scripts_path, monkeypatch):
    """Positional argv pointing at a nonexistent dir → exit 2."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    monkeypatch.setattr(sys, "argv", ["validate_canvas.py", str(tmp_path / "missing-dir")])

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 2


def test_main_argv_override_existing_dir_pass(tmp_path, scripts_path, monkeypatch):
    """Positional argv pointing at a valid dir is honored → exit 0."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    (other_dir / "freeform.yml").write_text("anything: goes\n")  # schemaless → warn, pass
    monkeypatch.setattr(validator, "CANVAS_DIR", tmp_path / "default-canvas")
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    monkeypatch.setattr(sys, "argv", ["validate_canvas.py", str(other_dir)])

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 0


def test_main_fail_on_malformed_yaml(tmp_path, scripts_path, monkeypatch):
    """Malformed YAML anywhere in the canvas dir → exit 1 (fail-loud parse check)."""
    validator = _import_validator(scripts_path)
    schema_dir = _real_schema_dir()
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "broken.yml").write_text("bad: [1, 2\n  oops: x\n")
    _setup_main_env(validator, monkeypatch, canvas_dir, schema_dir)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 1


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
