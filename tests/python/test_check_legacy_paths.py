"""Coverage tests for check_legacy_paths.py — the static legacy-path-rot guard.

These lock in the regression cases behind the v0.49.7/9 CI failures and the
v0.49.10 fix:
  - v0.49.7: the CLAUDE.md `*Version ...` changelog line legitimately quotes moved
    paths and must be skipped (but only that line).
  - v0.49.9: receipts-case files documenting the rot itself are allowlisted, as are
    the generic ALLOWLIST_FILES entries.
The check's scope is narrow on purpose: only `.claude/{engine,orchestration,schemas}/`
in `.md` files under SCAN_GLOBS, minus the allowlist.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_legacy_paths  # noqa: PLC0415

    return check_legacy_paths


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_positive_prose_codespan_is_flagged(scripts_path, tmp_path):
    """A docs/*.md prose code-span referencing a moved dir is one hit; exit 1."""
    mod = _import(scripts_path)
    _write(tmp_path / "docs/foo.md", "see `.claude/engine/theory-gates.md` for details")
    report = mod.scan(tmp_path)
    assert len(report["hits"]) == 1
    src, lineno, _ = report["hits"][0]
    assert src == "docs/foo.md"
    assert lineno == 1
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_claude_md_version_line_is_skipped(scripts_path, tmp_path):
    """Regression (v0.49.7): the `*Version` changelog line in CLAUDE.md is skipped."""
    mod = _import(scripts_path)
    _write(
        tmp_path / "CLAUDE.md",
        "*Version 0.49.10 — fixed $PROJECT_DIR/.claude/schemas/canvas/x.schema.json rot*\n",
    )
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_claude_md_non_version_line_still_flagged(scripts_path, tmp_path):
    """The version-line skip is scoped: a normal CLAUDE.md line is still flagged."""
    mod = _import(scripts_path)
    _write(
        tmp_path / "CLAUDE.md",
        "*Version 0.49.10 — fixed .claude/schemas/canvas/x.schema.json rot*\n"
        "Routing: see `.claude/engine/x.md` for gate order.\n",
    )
    report = mod.scan(tmp_path)
    # Only the non-version line is a hit.
    assert len(report["hits"]) == 1
    src, lineno, _ = report["hits"][0]
    assert src == "CLAUDE.md"
    assert lineno == 2
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_receipts_case_file_is_allowlisted(scripts_path, tmp_path):
    """Regression (v0.49.9): the per-case receipts file documenting the rot is allowed."""
    mod = _import(scripts_path)
    _write(
        tmp_path / "docs/receipts/cases/2026-06-18-legacy-path-rot-guard.md",
        "the rot quoted `.claude/engine/x.md` as its subject",
    )
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_generic_allowlisted_files_are_skipped(scripts_path, tmp_path):
    """Generic ALLOWLIST_FILES entries (AGENTS.md, docs/changelog.md) are skipped."""
    mod = _import(scripts_path)
    _write(tmp_path / "AGENTS.md", "legacy form put it at .claude/orchestration/x.md")
    _write(tmp_path / "docs/changelog.md", "fixed .claude/orchestration/x.md pointer")
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_out_of_pattern_dirs_not_flagged(scripts_path, tmp_path):
    """Only engine|orchestration|schemas are in scope — skills/harness/canvas are not."""
    mod = _import(scripts_path)
    _write(
        tmp_path / "docs/scope.md",
        "skills at `.claude/skills/x`\n"
        "state at `.claude/harness/x`\n"
        "canvas at `.claude/canvas/x.yml`\n",
    )
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_clean_repo_is_green(scripts_path, tmp_path):
    """A clean repo: 0 hits, exit 0."""
    mod = _import(scripts_path)
    _write(tmp_path / "docs/clean.md", "no legacy refs here, just prose")
    _write(tmp_path / "README.md", "see plugins/mycelium/engine/x.md")
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert report["files_scanned"] >= 1
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_non_scanned_location_not_flagged(scripts_path, tmp_path):
    """A file outside SCAN_GLOBS (.claude/memory/) is not scanned even with a hit."""
    mod = _import(scripts_path)
    _write(tmp_path / ".claude/memory/x.md", "see .claude/engine/y.md")
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0
