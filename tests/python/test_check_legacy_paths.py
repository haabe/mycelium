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
    import check_legacy_paths

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
    # A clean, SCANNED, non-allowlisted file so the run has a real denominator.
    # Added v0.75.0: without it every file in this fixture is excluded, the scan
    # examines nothing, and the exit-0 assertion was testing the vacuous pass
    # that v0.75.0 removes rather than the exclusion this test is about.
    _write(tmp_path / "docs/clean.md", "nothing legacy here")
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_generic_allowlisted_files_are_skipped(scripts_path, tmp_path):
    """Generic ALLOWLIST_FILES entries (AGENTS.md, docs/changelog.md) are skipped."""
    mod = _import(scripts_path)
    _write(tmp_path / "AGENTS.md", "legacy form put it at .claude/orchestration/x.md")
    _write(tmp_path / "docs/changelog.md", "fixed .claude/orchestration/x.md pointer")
    # A clean, SCANNED, non-allowlisted file so the run has a real denominator.
    # Added v0.75.0: without it every file in this fixture is excluded, the scan
    # examines nothing, and the exit-0 assertion was testing the vacuous pass
    # that v0.75.0 removes rather than the exclusion this test is about.
    _write(tmp_path / "docs/clean.md", "nothing legacy here")
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
    # A clean, SCANNED, non-allowlisted file so the run has a real denominator.
    # Added v0.75.0: without it every file in this fixture is excluded, the scan
    # examines nothing, and the exit-0 assertion was testing the vacuous pass
    # that v0.75.0 removes rather than the exclusion this test is about.
    _write(tmp_path / "docs/clean.md", "nothing legacy here")
    report = mod.scan(tmp_path)
    assert report["hits"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


# --- consumer-tree scope (v0.108.0) ----------------------------------------

def test_moved_dir_reference_in_consumer_readme_is_flagged(scripts_path, tmp_path):
    """A consumer's own README routing at the moved framework tree. Before v0.108.0
    the globs stopped at docs/ and plugins/mycelium/, so .claude/ was never read."""
    mod = _import(scripts_path)
    _write(
        tmp_path / ".claude/canvas/README.md",
        "Schemas are defined in `.claude/schemas/canvas/`.",
    )
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_append_only_record_under_claude_is_not_scanned(scripts_path, tmp_path):
    """The historical record legitimately QUOTES moved paths while narrating the
    migration that moved them — the same reasoning as the `*Version` line skip.
    A first cut globbing .claude/**/*.md returned 28 hits on a real repo: 2 genuine
    and 26 from decision-log.md and memory/. A 13:1 noise ratio gets a guard ignored."""
    mod = _import(scripts_path)
    # A real scannable file so the population is non-empty — otherwise the check
    # correctly REFUSES ("0 doc file(s) were scanned, so nothing was verified")
    # rather than passing, which is the empty-input honesty contract doing its job.
    _write(tmp_path / ".claude/canvas/README.md", "Canvas notes, no moved-dir refs.")
    _write(
        tmp_path / ".claude/harness/decision-log.md",
        "2026-05-12: migrated off `.claude/engine/` to plugin form.",
    )
    _write(
        tmp_path / ".claude/memory/corrections.md",
        "The old path was `.claude/scripts/validate_canvas.py`.",
    )
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_relative_form_is_not_matched_here(scripts_path, tmp_path):
    """Deliberate non-goal, reverted the hour it was tried. A regex over a relative
    path cannot know where it resolves: `[engine](../engine/)` inside
    plugins/mycelium/harness/ points at a directory that EXISTS. Resolution is
    check_doc_references.py's job and it catches these correctly."""
    mod = _import(scripts_path)
    _write(
        tmp_path / ".claude/diamonds/README.md",
        "See [rules](../engine/diamond-rules.md).",
    )
    assert mod.main(["--root", str(tmp_path)]) == 0
