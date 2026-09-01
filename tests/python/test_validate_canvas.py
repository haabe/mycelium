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
    import validate_canvas
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


def test_validate_diamonds_source_class_in_evidence_type_reported(tmp_path, scripts_path, monkeypatch):
    """A diamond record carrying a source_class value in evidence_type is rejected.

    Regression guard for the 2026-07-19 gap: the diamond schema typed
    evidence_type as {"type": "string"} instead of $ref-ing the enum, so
    'internal_stakeholder' (a source_class value, disjoint from the evidence_type
    enum) survived ~3 weeks of PASSes. Caught only by a human canvas-health grep.
    """
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text(
        "active_diamonds:\n"
        "  - id: l0-purpose\n"
        "    scale: L0\n"
        "    phase: deliver\n"
        "    evidence_type: internal_stakeholder\n"
    )
    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert any("evidence_type" in e or "internal_stakeholder" in e for e in errors), (
        f"Expected an evidence_type enum error, got {errors}"
    )


def test_validate_diamonds_valid_evidence_type_passes(tmp_path, scripts_path, monkeypatch):
    """A valid evidence_type enum value on a diamond passes (no regression)."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text(
        "active_diamonds:\n"
        "  - id: l0-purpose\n"
        "    scale: L0\n"
        "    phase: deliver\n"
        "    confidence: 0.7\n"  # required as of v0.92.0; this fixture is about evidence_type
        "    evidence_type: data-supported\n"
    )
    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert errors == [], f"Valid evidence_type should pass: {errors}"


def test_validate_diamonds_missing_confidence_fails(tmp_path, monkeypatch, scripts_path):
    """A diamond without `confidence` is REJECTED (v0.92.0).

    diamond-rules.md spawns L3 from L2 only when "opportunities have sufficient
    evidence" and L4 from L3 only when "solutions pass confidence threshold" — so a
    spawn gate consults this field. It cannot be optional at the point the gate reads
    it. Before this, absent was indistinguishable from recorded: one downstream
    consumer defaulted it to 0.5, which reads as a deliberate mid position and passed
    checks a real 0.5 would have passed. Absent is not low confidence, it is no
    position.
    """
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text(
        "active_diamonds:\n"
        "  - id: l0-purpose\n"
        "    scale: L0\n"
        "    phase: discover\n"
    )
    errors = validator.validate_diamonds(canvas_dir, validator.build_registry())
    assert any("confidence" in e for e in errors), (
        f"Diamond without confidence must be rejected, got: {errors}"
    )


def test_validate_diamonds_progression_ruling_enum_enforced(tmp_path, monkeypatch, scripts_path):
    """`progression_ruling` accepts only the three rulings, and rejects prose.

    Written by /mycelium:diamond-progress on every assessment as of v0.92.0. It is
    enumerated on purpose: the field's only prior consumer fell back to grepping
    decision-log prose for "block"/"gate"/"insufficient", which any paragraph
    EXPLAINING the gates satisfies without a gate having fired. A free-text ruling
    would reproduce that ambiguity inside the structured field that exists to end it.
    """
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    base = (
        "active_diamonds:\n"
        "  - id: l0-purpose\n"
        "    scale: L0\n"
        "    phase: discover\n"
        "    confidence: 0.2\n"
    )
    registry = validator.build_registry()

    (diamonds_dir / "active.yml").write_text(base + "    progression_ruling: blocked\n")
    assert validator.validate_diamonds(canvas_dir, registry) == []

    (diamonds_dir / "active.yml").write_text(
        base + '    progression_ruling: "blocked on insufficient evidence"\n'
    )
    errors = validator.validate_diamonds(canvas_dir, registry)
    assert any("progression_ruling" in e for e in errors), (
        f"Prose ruling must be rejected, got: {errors}"
    )


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


def test_main_schema_dir_missing_over_populated_canvas_exits_one(
    tmp_path, scripts_path, monkeypatch, capsys
):
    """SCHEMA_DIR missing while the canvas HAS files → exit 1, not a silent pass.

    THIS TEST ASSERTED exit 0 UNTIL 2026-08-03, and that is finding 11. The
    script printed "(no schemas to validate against — silently passing)" and
    exited 0 over a populated canvas — reachable in normal use whenever
    CLAUDE_PLUGIN_ROOT points at a stale plugin-cache path. It also made
    check_empty_input_honesty's exemption for this script false: the exemption
    asserted "there is no state where it verifies nothing AND claims a pass",
    and this was exactly that state, sitting in the file the whole time.

    A missing schema directory over real canvas files is a broken installation,
    not an early project — the fresh-setup and absent-canvas cases return N/A
    before this point, so reaching here means there was something to validate
    and nothing to validate it with.
    """
    validator = _import_validator(scripts_path)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "x.yml").write_text("a: b\n")
    missing_schema = tmp_path / "no-schemas"
    _setup_main_env(validator, monkeypatch, canvas_dir, missing_schema)

    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 1
    out = capsys.readouterr()
    assert "Refusing to report a pass" in (out.out + out.err)


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


# ---------------------------------------------------------------------------
# enum_consistency_errors (evidence_type / source_class values in their enum
# EVERYWHERE, including undeclared entry-level occurrences — 2026-07-19)
# ---------------------------------------------------------------------------

def test_enum_consistency_flags_source_class_value_in_evidence_type(tmp_path, scripts_path, monkeypatch):
    """A source_class value in a canvas entry's evidence_type field is a swap → flagged.
    (evidence_type is polymorphic, but source_class values are never valid there.)"""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(
        "components:\n  - id: src-research-005\n    name: x\n    evidence_type: internal_stakeholder\n"
    )
    errors = validator.enum_consistency_errors(canvas_dir)
    assert any("internal_stakeholder" in e and "source_class" in e for e in errors), errors


def test_enum_consistency_flags_source_class_swap_in_diamond(tmp_path, scripts_path, monkeypatch):
    """A source_class value (external_human) in a diamond's evidence_type field → flagged
    (the i-productified / roadmap dogfood bug)."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    diamonds_dir = tmp_path / ".claude" / "diamonds"
    diamonds_dir.mkdir(parents=True)
    (diamonds_dir / "active.yml").write_text(
        "active_diamonds:\n  - id: l0\n    scale: L0\n    phase: deliver\n    evidence_type: external_human\n"
    )
    errors = validator.enum_consistency_errors(canvas_dir)
    assert any("external_human" in e and "source_class" in e for e in errors), errors


def test_enum_consistency_flags_reverse_swap(tmp_path, scripts_path, monkeypatch):
    """A Gilad evidence_type value sitting in a source_class field → flagged."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(
        "components:\n  - id: c1\n    name: x\n    provenance:\n      source_class: data-supported\n"
    )
    errors = validator.enum_consistency_errors(canvas_dir)
    assert any("data-supported" in e and "evidence_type" in e for e in errors), errors


def test_enum_consistency_ignores_polymorphic_evidence_type(tmp_path, scripts_path, monkeypatch):
    """Regression guard for the v0.57.4 over-fire: legitimate polymorphic evidence_type
    values (gathering-method in _meta, signal-type, intentional extensions) must NOT be
    flagged. Only source_class-value swaps are errors."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "landscape.yml").write_text(
        "_meta:\n"
        "  evidence_type: interview\n"          # gathering-method vocabulary (canvas-guidance.yml)
        "components:\n"
        "  - id: c1\n"
        "    name: x\n"
        "    evidence_type: market_signal\n"     # signal-type vocabulary
        "  - id: c2\n"
        "    name: y\n"
        "    evidence_type: llm_positioning_mirror\n"  # intentional extension
    )
    assert validator.enum_consistency_errors(canvas_dir) == []


def test_enum_consistency_passes_valid_values(tmp_path, scripts_path, monkeypatch):
    """Valid evidence_type + source_class values produce no errors (no false positive)."""
    validator = _import_validator(scripts_path)
    _point_at_real_schemas(validator, monkeypatch)
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "opportunities.yml").write_text(
        "opportunities:\n  - id: opp-1\n    evidence_type: data-supported\n    source_class: external_human\n"
    )
    assert validator.enum_consistency_errors(canvas_dir) == []


# ---------------------------------------------------------------------------
# Multi-root OST (v0.93.0). An OST rooted on a metric the project does not steer
# by will faithfully optimise the wrong thing. These pin the enforcement that
# makes a second root usable without breaking the ID references pointing into
# the canvas, or creating a second file nothing reads.
# ---------------------------------------------------------------------------


def _opps(tmp_path, body: str):
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True, exist_ok=True)
    (canvas_dir / "opportunities.yml").write_text(body)
    return canvas_dir


TWO_ROOTS = """
desired_outcomes:
  - id: framework
    metric: framework_correctness
    north_star_input_ref: off_north_star
  - id: adoption
    metric: products_shipped_using_mycelium
    north_star_input_ref: products_shipped
opportunities:
"""


def test_single_root_file_needs_no_rolls_up_to(tmp_path, scripts_path):
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        "desired_outcome:\n  metric: framework_correctness\n"
        "opportunities:\n  - name: a\n    provenance: {}\n",
    )
    assert validator.ost_root_errors(canvas_dir) == []


def test_rolls_up_to_without_declared_roots_is_an_error(tmp_path, scripts_path):
    """The reference points at nothing. Silent here would be the built-not-wired
    shape: a field written, read by no root, changing nothing."""
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        "desired_outcome:\n  metric: framework_correctness\n"
        "opportunities:\n  - name: a\n    provenance: {}\n    rolls_up_to: adoption\n",
    )
    errors = validator.ost_root_errors(canvas_dir)
    assert any("points at nothing" in e for e in errors), errors


def test_declaring_both_root_forms_is_an_error(tmp_path, scripts_path):
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        "desired_outcome:\n  metric: one\n" + TWO_ROOTS + "  - name: a\n    provenance: {}\n",
    )
    assert any("BOTH" in e for e in validator.ost_root_errors(canvas_dir))


def test_untagged_opportunity_in_multi_root_file_is_an_error(tmp_path, scripts_path):
    """NOT default-to-first. Defaulting is how an opportunity ends up under a
    root nobody chose for it -- the original problem, one layer down."""
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(tmp_path, TWO_ROOTS + "  - name: a\n    provenance: {}\n")
    errors = validator.ost_root_errors(canvas_dir)
    assert any("no defined parent" in e for e in errors), errors


def test_rolls_up_to_must_resolve_to_a_declared_root(tmp_path, scripts_path):
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        TWO_ROOTS + "  - name: a\n    provenance: {}\n    rolls_up_to: typo-root\n",
    )
    errors = validator.ost_root_errors(canvas_dir)
    assert any("not a declared root" in e for e in errors), errors


def test_duplicate_root_ids_rejected(tmp_path, scripts_path):
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        TWO_ROOTS.replace("id: adoption", "id: framework")
        + "  - name: a\n    provenance: {}\n    rolls_up_to: framework\n",
    )
    assert any("duplicate root id" in e for e in validator.ost_root_errors(canvas_dir))


def test_well_formed_multi_root_file_passes(tmp_path, scripts_path):
    validator = _import_validator(scripts_path)
    canvas_dir = _opps(
        tmp_path,
        TWO_ROOTS
        + "  - name: a\n    provenance: {}\n    rolls_up_to: framework\n"
        + "  - name: b\n    provenance: {}\n    rolls_up_to: adoption\n",
    )
    assert validator.ost_root_errors(canvas_dir) == []


# ---------------------------------------------------------------------------
# task_list_findings (v0.130.0) — a closed task read as an open commitment
#
# THE DEFECT: of 94 entries under `pending_tasks` in the dogfood project, nine were
# pending. The founder caught it, not the framework. Nothing flagged it because
# `pending_tasks.items.status` shares the full six-value enum, so a completed task in
# the pending list is schema-VALID. These tests pin the failure direction first.
# ---------------------------------------------------------------------------

def _tasks(tmp_path, doc):
    import yaml
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "human-tasks.yml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return canvas


def test_completed_task_in_pending_list_is_flagged(tmp_path, scripts_path):
    """The failure direction. This is the exact shape the founder caught by memory."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [
        {"id": "ht-081", "status": "completed"},
        {"id": "ht-091", "status": "pending"},
    ], "completed_tasks": []})
    out = " ".join(v.task_list_findings(canvas))
    assert "ht-081" in out
    assert "completed_tasks" in out
    assert "ht-091" not in out


def test_abandoned_and_cancelled_are_routed_to_the_third_list(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [
        {"id": "ht-005", "status": "abandoned"},
        {"id": "ht-048", "status": "cancelled"},
    ], "completed_tasks": []})
    out = " ".join(v.task_list_findings(canvas))
    assert out.count("closed_without_evidence") == 2
    assert "completed_tasks" not in out


def test_in_progress_is_at_home_in_pending_tasks(tmp_path, scripts_path):
    """`pending_tasks` holds OPEN work. Flagging in_progress would make the check noise
    on 16 live tasks and teach the reader to scroll past it."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [{"id": "ht-083", "status": "in_progress"}]})
    assert v.task_list_findings(canvas) == []


def test_waiting_and_watching_are_open_states_not_misfiles(tmp_path, scripts_path):
    """v0.132.0. Flagging these would fire on the MAJORITY of a real project's open
    work — measured 2026-08-24, 13 of 16 in_progress tasks were sent-and-awaiting and
    3 of 9 pending were watches. A check that noisy gets scrolled past, which is how
    the probe-specificity advisory went unread for six days."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [
        {"id": "ht-083", "status": "waiting"},
        {"id": "ht-075", "status": "watching"},
    ]})
    assert v.task_list_findings(canvas) == []


def test_a_correctly_filed_canvas_is_silent(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {
        "pending_tasks": [{"id": "ht-091", "status": "pending"}],
        "completed_tasks": [{"id": "ht-081", "status": "completed"}],
        "closed_without_evidence": [{"id": "ht-048", "status": "cancelled",
                                     "closure_reason": "superseded"}],
    })
    assert v.task_list_findings(canvas) == []


def test_missing_completed_tasks_list_is_named_as_the_cause(tmp_path, scripts_path):
    """The root cause, not a symptom: /log-evidence writes to a list that does not exist,
    so the instruction silently does nothing."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [{"id": "ht-081", "status": "completed"}]})
    out = " ".join(v.task_list_findings(canvas))
    assert "no `completed_tasks:` list" in out


def test_the_finding_names_a_count_and_caps_the_ids(tmp_path, scripts_path):
    """A bare count is unactionable; sixty ids is scrollable-past, which mutes a warning."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [
        {"id": f"ht-{i:03d}", "status": "completed"} for i in range(1, 11)
    ], "completed_tasks": []})
    out = v.task_list_findings(canvas)[0]
    assert "10 task(s)" in out
    assert "+6 more" in out


def test_absent_file_and_unparseable_file_are_silent(tmp_path, scripts_path):
    """A broken advisory check must never take the whole canvas validation down."""
    v = _import_validator(scripts_path)
    canvas = tmp_path / "empty"
    canvas.mkdir()
    assert v.task_list_findings(canvas) == []
    (canvas / "human-tasks.yml").write_text("pending_tasks: [oops\n")
    assert v.task_list_findings(canvas) == []


def test_entries_without_a_status_are_not_guessed_at(tmp_path, scripts_path):
    """An absent status is unknown, not 'completed'. Inferring it would put a task in a
    list on the validator's guess."""
    v = _import_validator(scripts_path)
    canvas = _tasks(tmp_path, {"pending_tasks": [{"id": "ht-999"}]})
    assert v.task_list_findings(canvas) == []


# --- purpose.yml carries a `why` at all ---------------------------------------
# THE GAP (dogfood 2026-08-31). interview/SKILL.md promises a user who cannot yet name the
# change "proceeds, flagged for the deeper Phase-1 purpose questions". Nothing did the
# flagging: no script read purpose["why"] to test presence, and no hook did either. So
# "permissive at entry" was indistinguishable from "permanently empty, and nobody will say
# so" — the same silent-green this release fixes one level down.


def _purpose_canvas(tmp_path, body):
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "purpose.yml").write_text(body)
    return canvas


def test_absent_why_is_flagged_at_entry(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.purpose_why_findings(_purpose_canvas(tmp_path, "what:\n  - a microblog\n"))
    assert out and "no `why`" in out[0]


def test_empty_string_why_is_flagged_because_the_template_ships_one(tmp_path, scripts_path):
    """THE CASE THAT DEFEATED THE FIRST VERSION OF THIS CHECK.

    An `is not None` test passes `why: ""` — the shape the LEGACY (pre-plugin, v0.1.x) canvas
    template wrote, still sitting in the framework repo's own v0.1.0 scaffold on 2026-08-31.
    A key that is present and empty satisfies both a naive presence test and a bare
    JSON-Schema `required`. Current /mycelium:setup writes no purpose.yml at all.
    """
    v = _import_validator(scripts_path)
    assert v.purpose_why_findings(_purpose_canvas(tmp_path, 'why: ""\nhow: []\n'))


def test_whitespace_only_why_is_flagged(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    assert v.purpose_why_findings(_purpose_canvas(tmp_path, 'why: "   "\n'))


def test_a_real_why_is_not_flagged(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    assert v.purpose_why_findings(
        _purpose_canvas(tmp_path, "why: know what is worth building\n")) == []


def test_no_purpose_file_is_a_different_state_and_is_not_flagged(tmp_path, scripts_path):
    """Absent canvas is 'never started', not 'started without a why'. Flagging it would fire
    on every project that has not run /mycelium:setup."""
    v = _import_validator(scripts_path)
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    assert v.purpose_why_findings(canvas) == []


def test_the_flag_never_fails_a_build(tmp_path, scripts_path):
    """Entry-tier only. The hard requirement lives in the schema, gated on
    purpose_properties — see test_deriving_properties_from_an_empty_why_fails_validation."""
    v = _import_validator(scripts_path)
    canvas = _purpose_canvas(tmp_path, 'why: ""\n')
    assert v.purpose_why_findings(canvas)          # it is reported
    v.print_advisory_warnings(canvas)              # and printing it raises nothing


# --- the derived case is a HARD requirement, not an advisory ------------------


def _purpose_main(tmp_path, validator, monkeypatch, body):
    canvas_dir = tmp_path / ".claude" / "canvas"
    canvas_dir.mkdir(parents=True)
    (canvas_dir / "purpose.yml").write_text(body)
    _setup_main_env(validator, monkeypatch, canvas_dir, _real_schema_dir())
    with __import__("pytest").raises(SystemExit) as exc:
        validator.main()
    return exc.value.code


def test_deriving_properties_from_an_empty_why_fails_validation(tmp_path, scripts_path, monkeypatch):
    """`required: [why]` alone would PASS this: the key is present. minLength is what bites."""
    v = _import_validator(scripts_path)
    code = _purpose_main(tmp_path, v, monkeypatch,
                         'why: ""\npurpose_properties:\n  properties: []\n')
    assert code == 1


def test_deriving_properties_from_an_absent_why_fails_validation(tmp_path, scripts_path, monkeypatch):
    v = _import_validator(scripts_path)
    code = _purpose_main(tmp_path, v, monkeypatch,
                         "what: []\npurpose_properties:\n  properties: []\n")
    assert code == 1


def test_an_empty_why_without_derived_properties_still_passes(tmp_path, scripts_path, monkeypatch):
    """The onboarding path stays open. This is the line the whole design turns on: entry is
    permissive because Sinek's diagnosis is that people start from what they are building;
    derivation is not, because properties taken from an absent purpose are taken from nothing."""
    v = _import_validator(scripts_path)
    code = _purpose_main(tmp_path, v, monkeypatch, 'why: ""\nhow: []\nwhat: []\n')
    assert code == 0


def test_a_real_why_with_derived_properties_passes(tmp_path, scripts_path, monkeypatch):
    v = _import_validator(scripts_path)
    code = _purpose_main(tmp_path, v, monkeypatch,
                         "why: know what is worth building\npurpose_properties:\n  properties: []\n")
    assert code == 0


# --- bvssh-health schema: the field a hook depends on ------------------------
# Consumer finding 2026-08-31 (F9): validate_canvas reported bvssh-health.yml as
# "parse-checked only" while hooks/session-start.sh reads `last_assessed` from it every
# session. That hook passes the value to datetime.fromisoformat and falls back to an age of
# 999 days on ANY failure — so a malformed or wrongly-typed value is indistinguishable from
# a genuinely stale assessment. The schema is strict on that field and permissive elsewhere.


def _bvssh_schema():
    import json
    with open(_real_schema_dir() / "bvssh-health.schema.json") as fh:
        return json.load(fh)


def _bvssh_errors(doc):
    import jsonschema
    return list(jsonschema.Draft202012Validator(_bvssh_schema()).iter_errors(doc))


def test_bvssh_schema_exists_so_the_canvas_is_not_parse_checked_only():
    assert (_real_schema_dir() / "bvssh-health.schema.json").exists()


def test_bvssh_rejects_a_last_assessed_the_hook_could_not_parse():
    """The whole point of the schema. A dict here reads to session-start as 999 days overdue."""
    assert _bvssh_errors({"last_assessed": {"date": "2026-08-31"}})
    assert _bvssh_errors({"last_assessed": "August 31st"})


def test_bvssh_allows_null_last_assessed_because_never_assessed_is_an_honest_state():
    """The shipped stub carries null, and the hook reports it as 'never assessed'. Rejecting
    it would fail every project that has not yet run /mycelium:bvssh-check."""
    assert _bvssh_errors({"last_assessed": None}) == []


def test_bvssh_stays_permissive_on_the_dimension_blocks():
    """Metric sets are product-type specific. A consumer running Mycelium on a non-software
    object legitimately carries different metrics, and the schema must not fail them."""
    doc = {"last_assessed": "2026-08-31",
           "happier": {"description": "n=1: colleagues axis is the builder",
                       "metrics": {"anything": ["at", "all"]}, "trend": None,
                       "SOME_LOUD_CONSUMER_ANNOTATION": "kept"}}
    assert _bvssh_errors(doc) == []


# --- purpose_properties: weight + conditional unlock (consumer finding F5) ----
# A builder rejected the boolean frame: "I have problem seeing them as booleans. They have a
# value (say 1-10), and then can be weighed against each other." Both are needed: a pure
# weighted score permits compensatory trade-offs, so a high total can outvote a violated must.


def _purpose_schema_errors(doc):
    import json

    import jsonschema
    with open(_real_schema_dir() / "purpose.schema.json") as fh:
        s = json.load(fh)
    return list(jsonschema.Draft202012Validator(s).iter_errors(doc))


def _pp(**kw):
    item = dict(id="pp-001", property="anonymous", source="how", **kw)
    return {"why": "x", "purpose_properties": {"properties": [item]}}


def test_a_weighted_non_binding_property_is_allowed():
    assert _purpose_schema_errors(_pp(binding=False, weight=7)) == []


def test_weight_is_pinned_to_the_stated_one_to_ten_range():
    assert _purpose_schema_errors(_pp(binding=False, weight=44))
    assert _purpose_schema_errors(_pp(binding=False, weight=0))


def test_an_unlock_needs_a_named_state_because_a_soft_unlock_launders_erosion():
    """'when things get bad enough' fires exactly when judgement is worst, so an empty or
    missing state must not validate."""
    assert _purpose_schema_errors(_pp(binding=True, unlock={"state": ""}))
    assert _purpose_schema_errors(_pp(binding=True, unlock={}))
    assert _purpose_schema_errors(
        _pp(binding=True, unlock={"state": "a family conversation held and logged"})) == []


def test_an_unlock_on_a_non_binding_property_is_rejected():
    """Nothing was constraining, so there is nothing to unlock."""
    assert _purpose_schema_errors(_pp(binding=False, unlock={"state": "something happened"}))


def test_the_existing_boolean_shape_still_validates_unchanged():
    """Every project predating this release must keep passing."""
    assert _purpose_schema_errors(_pp(binding=True, contradicted_by=["sign-in first"])) == []


# --- technical_capabilities_required: the OUTER object, read for its meaning --
# Founder, 2026-08-31: "shouldn't the outer field be the one being wired? that's the data
# object being used?" Traversing generic `derived_from` links inside an object is not the
# same as anything reading the object for what it means.


def _caps(tmp_path, caps):
    import yaml
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "purpose.yml").write_text(
        yaml.safe_dump({"technical_capabilities_required": caps}, sort_keys=False))
    return canvas


def test_a_capability_with_no_fallback_is_a_silent_dependency(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.technical_capability_findings(
        _caps(tmp_path, [{"id": "tcr-001", "substrate_status": {"a": 1}}]))
    assert any("fallback_if_absent" in f for f in out)


def test_a_row_missing_a_column_its_siblings_record_is_flagged(tmp_path, scripts_path):
    """The matrix is only useful if every row covers the same columns."""
    v = _import_validator(scripts_path)
    out = v.technical_capability_findings(_caps(tmp_path, [
        {"id": "tcr-001", "fallback_if_absent": "x", "substrate_status": {"a": 1, "b": 2}},
        {"id": "tcr-002", "fallback_if_absent": "y", "substrate_status": {"a": 1}},
    ]))
    assert any("omits b" in f and "tcr-002" in f for f in out)


def test_a_complete_matrix_is_silent(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.technical_capability_findings(_caps(tmp_path, [
        {"id": "tcr-001", "fallback_if_absent": "x", "substrate_status": {"a": 1, "b": 2}},
        {"id": "tcr-002", "fallback_if_absent": "y", "substrate_status": {"a": 1, "b": 2}},
    ]))
    assert out == []


def test_absent_capabilities_block_is_not_an_error(tmp_path, scripts_path):
    """Most projects will never write this block; firing on them is how a check gets muted."""
    v = _import_validator(scripts_path)
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "purpose.yml").write_text("why: something\n")
    assert v.technical_capability_findings(canvas) == []


# --- source_class_target: intent recorded, outcome unrecorded -----------------
# 20 tasks declared the KIND of evidence they intended to produce. Nothing read it.
# check_source_class_fidelity already reads `source_class`; the target was one hop away
# and unwired only by omission.


def _tasks_doc(tmp_path, completed=None, pending=None):
    import yaml
    canvas = tmp_path / "canvas"
    canvas.mkdir(parents=True, exist_ok=True)
    (canvas / "human-tasks.yml").write_text(yaml.safe_dump(
        {"completed_tasks": completed or [], "pending_tasks": pending or []}, sort_keys=False))
    return canvas


def test_a_completed_task_that_never_said_where_its_evidence_landed_is_flagged(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.source_class_target_findings(_tasks_doc(
        tmp_path, completed=[{"id": "ht-001", "source_class_target": "external_human"}]))
    assert len(out) == 1
    assert "evidence_logged_to" in out[0]


def test_a_pointer_at_top_level_satisfies_it(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.source_class_target_findings(_tasks_doc(tmp_path, completed=[
        {"id": "ht-001", "source_class_target": "external_human",
         "evidence_logged_to": "opportunities.yml#opp-001"}]))
    assert out == []


def test_a_pointer_inside_the_touch_log_also_satisfies_it(tmp_path, scripts_path):
    """Real entries record it per-touch, not only at the top level."""
    v = _import_validator(scripts_path)
    out = v.source_class_target_findings(_tasks_doc(tmp_path, completed=[
        {"id": "ht-001", "source_class_target": "external_human",
         "touch_log": [{"date": "2026-08-01",
                        "evidence_logged_to": "landscape.yml#comp-001"}]}]))
    assert out == []


def test_a_pending_task_is_not_flagged(tmp_path, scripts_path):
    """A task still running has not produced its evidence yet. Warning about it would fire
    on every open task from the day it is created, which is how a check gets muted."""
    v = _import_validator(scripts_path)
    out = v.source_class_target_findings(_tasks_doc(
        tmp_path, pending=[{"id": "ht-001", "source_class_target": "external_human"}]))
    assert out == []


def test_a_task_without_the_field_is_not_flagged(tmp_path, scripts_path):
    v = _import_validator(scripts_path)
    out = v.source_class_target_findings(_tasks_doc(
        tmp_path, completed=[{"id": "ht-001"}]))
    assert out == []


# --- archived-solutions schema (added 2026-09-01) ----------------------------
# This canvas was one of seven reported as "parse-checked only" — and it had just acquired a
# DEPENDENT: check_log_reconcile (v0.155.0) reads `archived[].leaf_id` to reconcile kills
# against cycle-history, and nothing guaranteed the field existed.


def _archived_errors(doc):
    import json

    import jsonschema
    with open(_real_schema_dir() / "archived-solutions.schema.json") as fh:
        return list(jsonschema.Draft202012Validator(json.load(fh)).iter_errors(doc))


def test_an_archived_entry_must_carry_the_field_its_consumer_reads(tmp_path):
    """`leaf_id` is required because check_log_reconcile keys on it. An entry without one is
    invisible to the reconciliation and reads as though the kill never happened."""
    assert _archived_errors({"archived": [{"opportunity_id": "opp-001"}]})
    assert _archived_errors({"archived": [{"leaf_id": "sol-047a"}]}) == []


def test_the_reason_enum_comes_from_the_documented_contract(tmp_path):
    """The enum is engine/leaf-lifecycle.md's, not this project's sample. `low-ice-score`
    appears there parenthesised and is included, so a real kill for that reason is not forced
    to mislabel itself."""
    for good in ("failed-assumption", "feasibility-block", "superseded", "low-ice-score"):
        assert _archived_errors({"archived": [{"leaf_id": "x", "reason": good}]}) == [], good
    assert _archived_errors({"archived": [{"leaf_id": "x", "reason": "because-i-said-so"}]})


def test_both_recorded_ice_key_shapes_are_accepted(tmp_path):
    """A RECORDED COMPROMISE, not an oversight. engine/leaf-lifecycle.md documents
    `{i, c, e, total}`; the live entries use `{impact, confidence, ease, total}`; and
    opportunities.yml uses `{impact, confidence, ease, score}`. Pinning one would invalidate
    real records written in good faith against another. Converging them is a migration."""
    for shape in ({"i": 3, "c": 4, "e": 2, "total": 24},
                  {"impact": 8, "confidence": 4, "ease": 5, "total": 160},
                  {"impact": 8, "confidence": 4, "ease": 5, "score": 160}):
        assert _archived_errors(
            {"archived": [{"leaf_id": "x", "ice_score_at_archive": shape}]}) == [], shape


def test_the_live_dogfood_canvas_validates(tmp_path):
    """The schema must describe the file that exists, or it is a rule nobody follows."""
    import yaml
    live = Path("/Users/bartnes/Repos/mycelium-roadmap/.claude/canvas/archived-solutions.yml")
    if not live.is_file():
        import pytest
        pytest.skip("dogfood canvas not present in this checkout")
    assert _archived_errors(yaml.safe_load(live.read_text())) == []


# --- thresholds schema (added 2026-09-01) ------------------------------------
# Second of the seven "parse-checked only" canvases. Field set from
# engine/adaptive-thresholds.md's Threshold Registry, not from the entries present.


def _thresholds_errors(doc):
    import json

    import jsonschema
    with open(_real_schema_dir() / "thresholds.schema.json") as fh:
        return list(jsonschema.Draft202012Validator(json.load(fh)).iter_errors(doc))


def test_an_uncalibrated_threshold_is_valid_because_null_is_an_honest_state(tmp_path):
    """Every `calibrated` on the dogfood canvas is null with based_on_n 0. That is correct
    until the sample reaches minimum_n, and a schema that rejected it would push people to
    invent a number — the exact failure calibration exists to avoid."""
    assert _thresholds_errors({"thresholds": {"ice_advance": {
        "default": 100, "calibrated": None, "calibrated_at": None,
        "based_on_n": 0, "minimum_n": 10}}}) == []


def test_a_negative_sample_size_is_rejected(tmp_path):
    assert _thresholds_errors({"thresholds": {"ice_advance": {"based_on_n": -1}}})


def test_a_calibrated_at_that_is_not_a_date_is_rejected(tmp_path):
    """`last_calibrated` and `calibrated_at` answer "when", and prose there cannot be compared
    against anything."""
    assert _thresholds_errors({"thresholds": {"ice_advance": {"calibrated_at": "soon"}}})
    assert _thresholds_errors({"last_calibrated": "recently"})


def test_the_live_thresholds_canvas_validates(tmp_path):
    import yaml
    live = Path("/Users/bartnes/Repos/mycelium-roadmap/.claude/canvas/thresholds.yml")
    if not live.is_file():
        import pytest
        pytest.skip("dogfood canvas not present in this checkout")
    assert _thresholds_errors(yaml.safe_load(live.read_text())) == []



# ---------------------------------------------------------------------------
# team-shape + bounded-contexts schemas (added 2026-09-01)
#
# Both canvases were "parse-checked only" until now. bounded-contexts holds ZERO real
# leaves, which is the argument FOR schema-ing it rather than against: an empty canvas is
# first populated later, by an agent, unobserved, and nothing else checks the shape at that
# moment. Its enums were already written in the template's YAML comments, where nothing
# could enforce them.
# ---------------------------------------------------------------------------

def _canvas_errors(stem, doc, tmp_path, scripts_path):
    """Validate `doc` as <stem>.yml THROUGH THE SHIPPED CODE PATH.

    An earlier version of this helper built a bare Draft202012Validator of its own, with no
    `referencing` registry — so it could not resolve a $ref into _common.schema.json, and a
    schema could pass this suite via a path production never takes. Same defect class this
    repo already documents: one rule, two implementations, only one of which runs.
    """
    import yaml
    validator = _import_validator(scripts_path)
    canvas = tmp_path / f"{stem}.yml"
    canvas.write_text(yaml.safe_dump(doc, sort_keys=False))
    return validator.validate_canvas_against_schema(canvas, validator.build_registry())


def _live(stem, scripts_path):
    """Errors for the real dogfood canvas, or None when this checkout has no roadmap repo."""
    import yaml
    live = Path("/Users/bartnes/Repos/mycelium-roadmap/.claude/canvas") / f"{stem}.yml"
    if not live.is_file():
        return None
    validator = _import_validator(scripts_path)
    yaml.safe_load(live.read_text())  # parse guard: a YAML error must not read as schema-valid
    return validator.validate_canvas_against_schema(live, validator.build_registry())


def test_the_four_skelton_team_types_are_accepted_and_others_are_not(tmp_path, scripts_path):
    """The enum is the four FUNDAMENTAL types, re-verified against teamtopologies.com on
    2026-09-01: the second edition (Sept 2025) and the 2026 AI material both still carry
    exactly four. Third parties propose AI-specific types; the authors do not."""
    for t in ("stream-aligned", "enabling", "complicated-subsystem", "platform"):
        assert _canvas_errors("team-shape", {"teams": [{"name": "x", "type": t}]}, tmp_path, scripts_path) == [], t
    assert _canvas_errors("team-shape", {"teams": [{"name": "x", "type": "devops"}]}, tmp_path, scripts_path)


def test_a_team_must_state_its_type_even_if_the_answer_is_unclassified(tmp_path, scripts_path):
    """`type` is required but nullable: an unclassified team is legal, an entry that never
    mentions classification is not. Making you answer is the assessment's whole job, and a
    silently absent field is how that gets skipped."""
    assert _canvas_errors("team-shape", {"teams": [{"type": "platform"}]}, tmp_path, scripts_path)
    assert _canvas_errors("team-shape", {"teams": [{"name": "x"}]}, tmp_path, scripts_path)
    assert _canvas_errors("team-shape", {"teams": [{"name": "x", "type": None}]}, tmp_path, scripts_path) == []


def test_team_size_accepts_both_a_number_and_a_string(tmp_path, scripts_path):
    """The live entry records the float 1.5 — one human plus a primary agent counted as 0.5.
    A string is accepted too: a team writing '1 + 2 agents' is saying something a number
    cannot, and this canvas is read by humans as often as by scripts."""
    assert _canvas_errors("team-shape", {"teams": [{"name": "x", "type": "stream-aligned", "size": 1.5}]}, tmp_path, scripts_path) == []
    assert _canvas_errors("team-shape", {"teams": [{"name": "x", "type": "stream-aligned", "size": "1 + 2 agents"}]}, tmp_path, scripts_path) == []


def test_interaction_modes_are_deliberately_not_enum_pinned(tmp_path, scripts_path):
    """Three modes exist (collaboration, x-as-a-service, facilitating) but the KEYS here are
    other teams' names, not mode names. Pinning was also checked against the live site, which
    renders the third mode 'Facilitation' while the book says 'facilitating' — an enum would
    have to pick a side of a naming drift the authors themselves have not resolved."""
    doc = {"teams": [{"name": "x", "type": "platform",
                      "interaction_modes": {"other-team": "x-as-a-service"}}]}
    assert _canvas_errors("team-shape", doc, tmp_path, scripts_path) == []


def test_team_shape_last_assessed_must_be_a_date(tmp_path, scripts_path):
    """Read against the 120-day technical-feasibility horizon; prose cannot be compared."""
    assert _canvas_errors("team-shape", {"last_assessed": "a while ago"}, tmp_path, scripts_path)
    assert _canvas_errors("team-shape", {"last_assessed": "2026-09-01"}, tmp_path, scripts_path) == []


def test_the_seven_ddd_context_map_relationships_are_accepted(tmp_path, scripts_path):
    """Verbatim from the bounded-contexts template's own comment block — the schema moves
    them from prose to enforcement, it does not invent them."""
    for r in ("partnership", "shared_kernel", "customer_supplier", "conformist",
              "anti_corruption_layer", "open_host_service", "published_language"):
        doc = {"context_map": [{"upstream": "a", "downstream": "b", "relationship": r}]}
        assert _canvas_errors("bounded-contexts", doc, tmp_path, scripts_path) == [], r
    bogus = {"context_map": [{"upstream": "a", "downstream": "b", "relationship": "friends"}]}
    assert _canvas_errors("bounded-contexts", bogus, tmp_path, scripts_path)


def test_bounded_context_type_is_evans_distillation_not_free_text(tmp_path, scripts_path):
    for t in ("core", "supporting", "generic"):
        assert _canvas_errors("bounded-contexts", {"contexts": [{"name": "x", "type": t}]}, tmp_path, scripts_path) == []
    assert _canvas_errors("bounded-contexts", {"contexts": [{"name": "x", "type": "important"}]}, tmp_path, scripts_path)


def test_bounded_context_evolution_stage_matches_the_wardley_axis(tmp_path, scripts_path):
    """Same four stages landscape.yml uses; a context and a component must not disagree."""
    for st in ("genesis", "custom", "product", "commodity"):
        assert _canvas_errors("bounded-contexts", {"contexts": [{"name": "x", "evolution_stage": st}]}, tmp_path, scripts_path) == []
    assert _canvas_errors("bounded-contexts", {"contexts": [{"name": "x", "evolution_stage": "mature"}]}, tmp_path, scripts_path)


def test_both_live_canvases_validate(scripts_path):
    for stem in ("team-shape", "bounded-contexts"):
        errs = _live(stem, scripts_path)
        if errs is None:
            import pytest
            pytest.skip("dogfood canvas not present in this checkout")
        assert errs == [], (stem, errs)


def test_every_canvas_schema_accepts_the_template_that_ships_beside_it(scripts_path):
    """A schema that rejects its own shipped template is broken on arrival.

    This is a RATCHET over every schema, not a test of one. It was written because
    bounded-contexts.schema.json shipped with `additionalProperties: false` and no
    declaration for `last_updated` — a field sitting in the shipped template itself. The
    failure surfaced only indirectly, through an unrelated test that happened to validate
    the whole canvas directory. Nothing was checking the direct question.

    Note this bites ONLY for schemas with additionalProperties:false. The older canvas
    schemas set it true and would pass this vacuously; that is the gap being closed, not a
    reason to weaken the check.
    """
    validator = _import_validator(scripts_path)
    repo_canvas = Path(scripts_path).parents[2] / ".claude" / "canvas"
    if not repo_canvas.is_dir():
        import pytest
        pytest.skip("no shipped canvas templates in this checkout")

    registry = validator.build_registry()
    checked, failures = 0, []
    for schema in sorted(_real_schema_dir().glob("*.schema.json")):
        if schema.name.startswith("_"):
            continue
        template = repo_canvas / f"{schema.stem.replace('.schema', '')}.yml"
        if not template.is_file():
            continue  # schema for a canvas this repo does not itself keep
        checked += 1
        errors = validator.validate_canvas_against_schema(template, registry)
        if errors:
            failures.append((template.name, errors))

    assert checked > 0, (
        "matched no templates at all — a green result here would mean nothing. "
        "Empty input must refuse, not pass."
    )
    assert not failures, failures
