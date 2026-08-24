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
