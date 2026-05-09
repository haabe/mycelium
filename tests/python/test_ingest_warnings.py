"""Coverage proofs for ingest_warnings.py.

Per G-V12: the ingestor is itself a classification mechanism — it must ship
with tests that fail on known-bad inputs (misclassification, drop, malformed
log). Each test constructs a CI-output fixture and asserts the expected
class / log shape.
"""
import sys
import textwrap


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import ingest_warnings  # noqa: PLC0415
    return ingest_warnings


def test_classify_each_known_signature(scripts_path):
    iw = _import(scripts_path)
    cases = [
        ("upgrade.sh contains 1 hardcoded top-level filename literal(s) — review",
         "hardcoded_top_level_literal"),
        ("upgrade.sh contains 2 hardcoded framework-directory literal(s)",
         "hardcoded_directory_literal"),
        ("3 new skill(s) show strong user-content-handling signal",
         "user_content_skill_unclassified"),
        ("Curated at-risk skill missing: foo",
         "wrapping_convention_missing"),
        ("Canvas file scenarios.yml not in canvas-update mapping",
         "canvas_in_update_mapping_missing"),
        ("ruff: 35 total errors across all .claude/scripts/*.py",
         "ruff_total_above_baseline"),
        ("VALIDATION FAILED",
         "validation_failed"),
        ("Uncommitted changes detected. Commit or stash first:",
         "dirty_state_pre_upgrade"),
        ("framework changes shipped without L4 delivery discipline",
         "framework_dev_without_l4_dod"),
    ]
    for message, expected in cases:
        assert iw.classify(message) == expected, (
            f"misclassified {message!r}: got {iw.classify(message)!r}, want {expected!r}"
        )


def test_unclassified_for_unknown_pattern(scripts_path):
    iw = _import(scripts_path)
    assert iw.classify("Some never-seen-before warning text") == "unclassified"


def test_parse_ci_output_extracts_warn_and_fail_lines(scripts_path):
    iw = _import(scripts_path)
    text = textwrap.dedent("""\
        --- Check 16: drift ---
          PASS: upgrade.sh contains no hardcoded framework-directory literals
          WARN: upgrade.sh contains 1 hardcoded top-level filename literal(s) — review
          FAIL: VALIDATION FAILED
          info: ignore me
    """)
    records = iw.parse_ci_output(text)
    assert len(records) == 2
    assert records[0]["severity"] == "WARN"
    assert records[0]["class"] == "hardcoded_top_level_literal"
    assert records[1]["severity"] == "FAIL"
    assert records[1]["class"] == "validation_failed"


def test_parse_ci_output_ignores_unrelated_lines(scripts_path):
    iw = _import(scripts_path)
    text = "regular output\nPASS: nothing to flag\nINFO: just a note\n"
    assert iw.parse_ci_output(text) == []


def test_aggregate_groups_and_promotes_severity(scripts_path):
    iw = _import(scripts_path)
    records = [
        {"severity": "WARN", "message": "x", "class": "hardcoded_top_level_literal"},
        {"severity": "WARN", "message": "y", "class": "hardcoded_top_level_literal"},
        {"severity": "FAIL", "message": "z", "class": "hardcoded_top_level_literal"},
    ]
    out = iw.aggregate(records)
    assert out["hardcoded_top_level_literal"]["count"] == 3
    # FAIL should win over WARN when promoting
    assert out["hardcoded_top_level_literal"]["severity"] == "FAIL"


def test_merge_preserves_first_seen_increments_count(scripts_path):
    iw = _import(scripts_path)
    existing = {
        "hardcoded_top_level_literal": {
            "first_seen": "2026-05-01",
            "last_seen": "2026-05-03",
            "count": "5",
            "severity": "WARN",
            "sample": "old sample",
            "status": "open",
        },
    }
    current = {
        "hardcoded_top_level_literal": {
            "count": 2,
            "severity": "WARN",
            "sample": "new sample",
        },
    }
    merged = iw.merge(existing, current, "2026-05-04")
    assert merged["hardcoded_top_level_literal"]["first_seen"] == "2026-05-01"
    assert merged["hardcoded_top_level_literal"]["last_seen"] == "2026-05-04"
    assert merged["hardcoded_top_level_literal"]["count"] == 7
    assert merged["hardcoded_top_level_literal"]["sample"] == "new sample"
    assert merged["hardcoded_top_level_literal"]["status"] == "open"


def test_merge_new_class_initializes_first_seen(scripts_path):
    iw = _import(scripts_path)
    merged = iw.merge(
        {},
        {"validation_failed": {"count": 1, "severity": "FAIL", "sample": "VALIDATION FAILED"}},
        "2026-05-04",
    )
    assert merged["validation_failed"]["first_seen"] == "2026-05-04"
    assert merged["validation_failed"]["count"] == 1


def test_render_includes_all_fields(scripts_path):
    iw = _import(scripts_path)
    rendered = iw.render({
        "validation_failed": {
            "first_seen": "2026-05-04",
            "last_seen": "2026-05-04",
            "count": 1,
            "severity": "FAIL",
            "sample": "VALIDATION FAILED",
            "status": "open",
        },
    })
    assert "## validation_failed" in rendered
    assert "First seen" in rendered
    assert "Last seen" in rendered
    assert "Count" in rendered
    assert "FAIL" in rendered
    assert "warning-handbook.md#validation-failed" in rendered


def test_parse_existing_log_roundtrip(tmp_path, scripts_path):
    iw = _import(scripts_path)
    log = tmp_path / "warnings-log.md"
    sample = {
        "validation_failed": {
            "first_seen": "2026-05-04",
            "last_seen": "2026-05-04",
            "count": 3,
            "severity": "FAIL",
            "sample": "VALIDATION FAILED",
            "status": "open",
        },
    }
    log.write_text(iw.render(sample))
    parsed = iw.parse_existing_log(log)
    assert "validation_failed" in parsed
    assert parsed["validation_failed"]["first_seen"] == "2026-05-04"
    assert parsed["validation_failed"]["count"] == "3"  # parsed as string


def test_dry_run_does_not_write_log(tmp_path, scripts_path, monkeypatch, capsys):
    iw = _import(scripts_path)
    log = tmp_path / "warnings-log.md"
    monkeypatch.setattr(sys, "argv", [
        "ingest_warnings.py",
        "--dry-run",
        "--log-path", str(log),
    ])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("  WARN: VALIDATION FAILED\n"))
    iw.main()
    assert not log.exists()
    out = capsys.readouterr().out
    assert "validation_failed" in out


def test_real_write_creates_log(tmp_path, scripts_path, monkeypatch):
    iw = _import(scripts_path)
    log = tmp_path / "subdir" / "warnings-log.md"  # tests mkdir
    monkeypatch.setattr(sys, "argv", [
        "ingest_warnings.py",
        "--log-path", str(log),
    ])
    monkeypatch.setattr(
        "sys.stdin",
        __import__("io").StringIO("  WARN: VALIDATION FAILED\n"),
    )
    iw.main()
    assert log.exists()
    content = log.read_text()
    assert "validation_failed" in content
