"""Coverage proofs for the closure-discipline gate (_common.schema.json#/$defs/closure_discipline).

Per G-V12: schema rules ship with tests that fail on known-bad input.

WHY THIS GATE EXISTS. Solution leaves have had a never-delete archive protocol for a long time
(archived-solutions.yml: "Dead leaves from the OST lifecycle. Never deleted -- they are learning"),
with a reason enum, the phase it died at, and snapshots. Opportunities and human-tasks had nothing
equivalent: `status` was not even a declared property on opportunities, and reopen semantics appeared
17 times in one dogfood canvas against 0 mentions in its schema.

THE FAILURE IT IS BUILT FROM (dogfood, 2026-08-04). A human-task was closed with
`closure_reason: channel-ended`, justified by an expectation recorded a month earlier plus the
observation that the window had passed. Nobody asked the one person who knew. The organisation had
not folded. Before anyone checked, that reason was cited as established fact across 12 sites, and
each citation compressed it further from the inference underneath. A one-line message falsified it.

The gate does not try to detect bad reasoning. It forces two companions whenever a REASON is
claimed: `closure_basis` (observed vs inferred) and `reopen_trigger` (what would make this wrong).
Had `closure_basis` been mandatory, the honest answer was `inferred`, and no later reader would
have cited it as fact.
"""
import json
import sys
import textwrap
from pathlib import Path


def _import_validator(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import validate_canvas
    return validate_canvas


def _setup_canvas(tmp_path, scripts_path, monkeypatch, filename, schema_name, content):
    """Write a canvas file + its real schema into a tmp tree, return validation errors."""
    canvas_dir = tmp_path / ".claude" / "canvas"
    schema_dir = tmp_path / ".claude" / "schemas" / "canvas"
    canvas_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)

    real_schema_dir = scripts_path.parent / "schemas" / "canvas"
    for name in (schema_name, "_common.schema.json"):
        (schema_dir / name).write_text((real_schema_dir / name).read_text())

    (canvas_dir / filename).write_text(content)

    validator = _import_validator(scripts_path)
    monkeypatch.setattr(validator, "CANVAS_DIR", canvas_dir)
    monkeypatch.setattr(validator, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validator, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    registry = validator.build_registry()
    return validator.validate_canvas_against_schema(canvas_dir / filename, registry)


def _task(tmp_path, scripts_path, monkeypatch, body):
    return _setup_canvas(
        tmp_path, scripts_path, monkeypatch,
        "human-tasks.yml", "human-tasks.schema.json", body,
    )


# --------------------------------------------------------------------------
# GUARD PATH: no reason asserted -> no ceremony demanded.
# The gate is conditional on purpose. Work that is simply finished must not be
# forced to invent closure metadata, or the gate becomes noise and gets removed.
# --------------------------------------------------------------------------

def test_completed_task_without_closure_reason_needs_nothing(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-001"
            type: "interview"
            objective: "Talk to a user"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
    """))
    assert errors == [], f"A closure with no asserted reason must pass untouched: {errors}"


# --------------------------------------------------------------------------
# BAD PATH: the exact shape that produced the 12-site cascade.
# --------------------------------------------------------------------------

def test_closure_reason_alone_is_rejected(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "channel-ended"
    """))
    assert any("'closure_basis' is a required property" in e for e in errors), (
        f"A bare closure_reason is the ht-002 shape and must be rejected. errors={errors}"
    )


# --------------------------------------------------------------------------
# SAD PATHS: one companion present, the other missing. Both must fail.
# --------------------------------------------------------------------------

def test_basis_without_reopen_trigger_is_rejected(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "channel-ended"
            closure_basis: "inferred"
    """))
    assert any("'reopen_trigger' is a required property" in e for e in errors), (
        f"Declaring a basis without a reopen trigger leaves the closure undetectable. errors={errors}"
    )


def test_reopen_trigger_without_basis_is_rejected(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "channel-ended"
            reopen_trigger: "a member self-initiates"
    """))
    assert any("'closure_basis' is a required property" in e for e in errors), (
        f"A reopen trigger does not excuse an unlabelled basis. errors={errors}"
    )


def test_invalid_closure_basis_value_is_rejected(tmp_path, scripts_path, monkeypatch):
    """`assumed`, `probably`, `stale` and friends are how the enum would erode."""
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "channel-ended"
            closure_basis: "assumed"
            reopen_trigger: "a member self-initiates"
    """))
    assert any("'assumed' is not one of" in e for e in errors), (
        f"closure_basis must stay a two-value choice. errors={errors}"
    )


# --------------------------------------------------------------------------
# HAPPY PATH: a full closure record, in both allowed bases.
# `inferred` must be perfectly valid -- the gate labels guesses, it does not ban them.
# --------------------------------------------------------------------------

def test_full_closure_record_passes(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "programme-criteria-unmeetable"
            closure_basis: "observed"
            reopen_trigger: "a member self-initiates and runs it"
    """))
    assert errors == [], f"A complete closure record must pass: {errors}"


def test_inferred_basis_is_allowed_not_banned(tmp_path, scripts_path, monkeypatch):
    errors = _task(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        completed_tasks:
          - id: "ht-002"
            type: "usability_test"
            objective: "Run a cohort programme"
            status: "completed"
            completed_at: "2026-08-04"
            source_class: "external_human"
            closure_reason: "no reply in 45 days on the only open channel"
            closure_basis: "inferred"
            reopen_trigger: "they reply, or a second channel opens"
    """))
    assert errors == [], (
        f"`inferred` is the honest label for a defensible guess and must pass: {errors}"
    )


# --------------------------------------------------------------------------
# The same gate on the opportunities canvas, plus the status enum that was
# never declared -- which is how one canvas drifted to five spellings of
# `status`, including an uppercase variant no validator could see.
# --------------------------------------------------------------------------

def _opp(tmp_path, scripts_path, monkeypatch, body):
    return _setup_canvas(
        tmp_path, scripts_path, monkeypatch,
        "opportunities.yml", "opportunities.schema.json", body,
    )


_OPP_PROVENANCE = """\
    provenance:
      evidence_type: anecdotal
      evidence_sources:
        - "dogfood 2026-08-04"
      confidence: 0.3
"""


def test_opportunity_closure_reason_alone_is_rejected(tmp_path, scripts_path, monkeypatch):
    errors = _opp(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        opportunities:
          - name: "Some opportunity"
            status: closed
            closure_reason: "superseded"
        """) + _OPP_PROVENANCE)
    assert any("'closure_basis' is a required property" in e for e in errors), (
        f"The gate must bind on opportunities too, not only tasks. errors={errors}"
    )


def test_opportunity_uppercase_status_is_rejected(tmp_path, scripts_path, monkeypatch):
    """The observed drift: `OPEN` sat in a dogfood canvas because nothing declared the field."""
    errors = _opp(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        opportunities:
          - name: "Some opportunity"
            status: OPEN
        """) + _OPP_PROVENANCE)
    assert any("'OPEN' is not one of" in e for e in errors), (
        f"status must be a declared enum so casing drift is visible. errors={errors}"
    )


def test_opportunity_without_status_still_passes(tmp_path, scripts_path, monkeypatch):
    """status stays optional: adding the enum must not invalidate every existing entry."""
    errors = _opp(tmp_path, scripts_path, monkeypatch, textwrap.dedent("""\
        opportunities:
          - name: "Some opportunity"
        """) + _OPP_PROVENANCE)
    assert errors == [], f"status is optional; absence must not fail: {errors}"
