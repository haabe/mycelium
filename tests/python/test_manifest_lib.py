"""Unit tests for _manifest_lib.parse_manifest()."""
import sys
from pathlib import Path


def _import_lib(scripts_path):
    """Import _manifest_lib via sys.path (not packaged)."""
    sys.path.insert(0, str(scripts_path))
    import _manifest_lib  # noqa: PLC0415
    return _manifest_lib


def test_missing_manifest_returns_empty_buckets(project_dir, scripts_path):
    """Nonexistent manifest path returns the empty-bucket dict (fail-open)."""
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(project_dir / "nonexistent.yml")
    for key in lib.SECTION_KEY_MAP.values():
        assert framework[key] == [], f"{key} should be empty"


def test_top_level_files_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert "CLAUDE.md" in framework["top_level"]
    assert "README.md" in framework["top_level"]
    assert "AGENTS.md" in framework["top_level"]
    assert len(framework["top_level"]) == 3


def test_directories_parsed_with_trailing_slash(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/skills/" in framework["directories"]
    assert ".claude/scripts/" in framework["directories"]


def test_single_files_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/manifest.yml" in framework["single_files"]


def test_harness_framework_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/harness/guardrails.md" in framework["harness_framework"]
    assert ".claude/harness/security-trust.md" in framework["harness_framework"]


def test_project_state_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/memory/" in framework["project_state"]
    assert ".claude/state/" in framework["project_state"]


def test_evals_replace_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/evals/scenarios/" in framework["evals_replace"]


def test_metrics_adapters_framework_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/jit-tooling/metrics-adapters/github.md" in framework[
        "metrics_adapters_framework"
    ]


def test_preserved_dir_readmes_parsed(manifest_path, scripts_path):
    lib = _import_lib(scripts_path)
    framework = lib.parse_manifest(manifest_path)
    assert ".claude/canvas/README.md" in framework["preserved_dir_readmes"]


def test_inline_comments_stripped(project_dir, scripts_path):
    lib = _import_lib(scripts_path)
    manifest = """\
framework:
  top_level:
    - CLAUDE.md  # the operating manual
    - AGENTS.md  # the router
"""
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    framework = lib.parse_manifest(path)
    assert framework["top_level"] == ["CLAUDE.md", "AGENTS.md"]


def test_quoted_values_unwrapped(project_dir, scripts_path):
    lib = _import_lib(scripts_path)
    manifest = """\
framework:
  top_level:
    - "CLAUDE.md"
    - 'README.md'
"""
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    framework = lib.parse_manifest(path)
    assert framework["top_level"] == ["CLAUDE.md", "README.md"]


def test_empty_lines_and_comments_skipped(project_dir, scripts_path):
    lib = _import_lib(scripts_path)
    manifest = """\
# Top-level comment
framework:

  # Indented comment
  top_level:
    - CLAUDE.md

    - README.md
"""
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    framework = lib.parse_manifest(path)
    assert framework["top_level"] == ["CLAUDE.md", "README.md"]


def test_unknown_section_ignored(project_dir, scripts_path):
    lib = _import_lib(scripts_path)
    manifest = """\
framework:
  top_level:
    - CLAUDE.md
mystery_section:
  - some-value
"""
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    framework = lib.parse_manifest(path)
    assert framework["top_level"] == ["CLAUDE.md"]
    # mystery_section doesn't go anywhere — silently ignored, no error


def test_indentation_drift_raises(project_dir, scripts_path):
    """C3 regression: a non-empty manifest whose list items bucket into nothing
    (e.g. reindented to 4 spaces) must raise, not silently fail open."""
    import pytest  # noqa: PLC0415

    lib = _import_lib(scripts_path)
    manifest = """\
framework:
    top_level:
      - CLAUDE.md
"""
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    with pytest.raises(ValueError):
        lib.parse_manifest(path)


def test_comment_only_manifest_does_not_raise(project_dir, scripts_path):
    """No list items at all → no drift signal → empty buckets, no error."""
    lib = _import_lib(scripts_path)
    path = project_dir / ".claude" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# just a comment\nframework:\n")
    framework = lib.parse_manifest(path)
    assert not any(framework.values())
