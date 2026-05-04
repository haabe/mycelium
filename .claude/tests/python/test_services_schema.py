"""Coverage proofs for services.schema.json.

Per G-V12: schema rules ship with tests that fail on known-bad input.
"""
import json
import sys
import textwrap
from pathlib import Path


def _import_validator(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import validate_canvas  # noqa: PLC0415
    return validate_canvas


def _setup_canvas(tmp_path, scripts_path, monkeypatch, services_yaml):
    """Helper: write a services.yml + the real services schema + _common, return errors."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    schema_dir = tmp_path / ".claude" / "schemas" / "canvas"
    canvas_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)

    # Copy real schemas into the tmp tree (so $ref to _common.schema.json resolves).
    real_schema_dir = scripts_path.parent / "schemas" / "canvas"
    for name in ("services.schema.json", "_common.schema.json"):
        (schema_dir / name).write_text((real_schema_dir / name).read_text())

    (canvas_dir / "services.yml").write_text(services_yaml)

    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")

    registry = validator.build_registry()
    return validator.validate_canvas_against_schema(canvas_dir / "services.yml", registry)


def test_empty_services_array_is_valid(tmp_path, scripts_path, monkeypatch):
    """Negative control: bare canvas with empty services list passes (common starting state)."""
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, "services: []\n")
    assert errors == [], f"Empty services array should pass: {errors}"


def test_service_missing_required_id_is_rejected(tmp_path, scripts_path, monkeypatch):
    """Known-bad: service missing the required 'id' field → schema rejects."""
    yaml_content = textwrap.dedent("""\
        services:
          - name: "Service without id"
            description: "Should be rejected"
    """)
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, yaml_content)
    assert any("'id' is a required property" in e for e in errors), (
        f"Schema should reject service missing 'id'. errors={errors}"
    )


def test_service_missing_required_name_is_rejected(tmp_path, scripts_path, monkeypatch):
    """Known-bad: service missing the required 'name' field → schema rejects."""
    yaml_content = textwrap.dedent("""\
        services:
          - id: "svc-001"
            description: "no name"
    """)
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, yaml_content)
    assert any("'name' is a required property" in e for e in errors), (
        f"Schema should reject service missing 'name'. errors={errors}"
    )


def test_invalid_xai_tier_is_rejected(tmp_path, scripts_path, monkeypatch):
    """Known-bad: xai.tier outside the allowed enum → schema rejects."""
    yaml_content = textwrap.dedent("""\
        services:
          - id: "svc-001"
            name: "Test"
            xai:
              tier: "extreme"
    """)
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, yaml_content)
    assert any("'extreme'" in e and "enum" in e.lower() or "'extreme' is not one of" in e for e in errors), (
        f"Schema should reject xai.tier='extreme'. errors={errors}"
    )


def test_valid_xai_block_passes(tmp_path, scripts_path, monkeypatch):
    """Negative control: well-formed service with full xai block validates."""
    yaml_content = textwrap.dedent("""\
        services:
          - id: "svc-001"
            name: "Recommendation Engine"
            xai:
              tier: "limited"
              last_assessed_at: "2026-05-04T12:00:00Z"
              recourse:
                path_exists: true
                max_clicks_to_human: 2
                sla_documented: true
                logs_contestation: true
                verdict: "pass"
              fidelity:
                samples_audited: 10
                blind_prediction_accuracy: 0.7
                verdict: "pass"
                last_audited_at: "2026-05-04T12:00:00Z"
              system_card:
                path: "docs/ai-system-card.md"
                sections_present: ["intended_use", "limitations", "evaluation_methodology"]
                sections_missing: []
                verdict: "pass"
              validated_functionally: ["stage_1_tier", "stage_4_system_card"]
              needs_user_testing: ["stage_2_matrix"]
    """)
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, yaml_content)
    assert errors == [], f"Valid xai block should pass: {errors}"


def test_invalid_recourse_verdict_is_rejected(tmp_path, scripts_path, monkeypatch):
    """Known-bad: recourse.verdict outside enum → schema rejects."""
    yaml_content = textwrap.dedent("""\
        services:
          - id: "svc-001"
            name: "Test"
            xai:
              tier: "limited"
              recourse:
                path_exists: true
                verdict: "kinda-ok"
    """)
    errors = _setup_canvas(tmp_path, scripts_path, monkeypatch, yaml_content)
    assert any("'kinda-ok'" in e for e in errors), (
        f"Schema should reject recourse.verdict='kinda-ok'. errors={errors}"
    )
