"""Coverage tests for check_doc_references.py (G-V12).

The dead-link validator must (a) flag genuinely broken markdown links, (b) NOT
flag the legitimate resolution shapes that made the 2026-05-30 recon's first cut
~95% false positives: file-relative `../` links, the .claude/<->plugins/mycelium/
dual-tree mapping, and plugin-tree docs whose relative paths are correct only at
their installed `.claude/<sub>` location.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_doc_references  # noqa: PLC0415

    return check_doc_references


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_flags_a_broken_markdown_link(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _write(tmp_path / "README.md", "See [the guide](docs/missing.md).")
    report = mod.scan(tmp_path)
    assert any(t == "docs/missing.md" for _, t in report["dead"])


def test_resolves_relative_parent_link(scripts_path, tmp_path):
    """`../X` must resolve against the linking file's own directory."""
    mod = _import(scripts_path)
    _write(tmp_path / "CONTRIBUTORS.md", "people")
    _write(tmp_path / "docs/receipts/cases/c.md", "[Dan](../../../CONTRIBUTORS.md)")
    report = mod.scan(tmp_path)
    assert report["dead"] == []


def test_flags_wrong_relative_depth(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _write(tmp_path / "CONTRIBUTORS.md", "people")
    # one `..` too few — resolves to docs/CONTRIBUTORS.md, which is absent
    _write(tmp_path / "docs/receipts/cases/c.md", "[Dan](../../CONTRIBUTORS.md)")
    report = mod.scan(tmp_path)
    assert any("CONTRIBUTORS.md" in t for _, t in report["dead"])


def test_dual_tree_claude_maps_to_plugin_source(scripts_path, tmp_path):
    """A `.claude/X` link resolves if plugins/mycelium/X exists."""
    mod = _import(scripts_path)
    _write(tmp_path / "plugins/mycelium/engine/foo.md", "x")
    _write(tmp_path / "docs/d.md", "[foo](.claude/engine/foo.md)")
    report = mod.scan(tmp_path)
    assert report["dead"] == []


def test_runtime_equivalent_resolution_for_plugin_docs(scripts_path, tmp_path):
    """A plugin-tree doc's `../../CLAUDE.md` is correct at its installed
    .claude/<sub> location and must resolve even though the repo-root .claude/
    tree does not contain the intermediate dir."""
    mod = _import(scripts_path)
    _write(tmp_path / "CLAUDE.md", "root")
    _write(tmp_path / "plugins/mycelium/domains/README.md", "[c](../../CLAUDE.md)")
    report = mod.scan(tmp_path)
    assert report["dead"] == []


def test_skips_placeholder_and_external_targets(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _write(
        tmp_path / "docs/d.md",
        "[a](path) [b](https://x.com) [c](#anchor) [d](*.yml) [e]({{X}})",
    )
    report = mod.scan(tmp_path)
    assert report["dead"] == []
    assert report["links_checked"] == 0


def test_allowlist_suppresses_illustrative_link(scripts_path, tmp_path):
    mod = _import(scripts_path)
    mod.ALLOWLIST.add(("docs/contributing/style.md", "evaluate.md"))
    _write(tmp_path / "docs/contributing/style.md", "bad: [here](evaluate.md)")
    report = mod.scan(tmp_path)
    assert report["dead"] == []


def test_real_repo_has_no_dead_references(scripts_path):
    """The shipped tree must stay clean — this is the standing CI guard."""
    mod = _import(scripts_path)
    root = scripts_path.parents[2]  # <repo>/plugins/mycelium/scripts -> <repo>
    report = mod.scan(root)
    assert report["dead"] == [], "dead doc references:\n" + "\n".join(
        f"  {s} -> {t}" for s, t in report["dead"]
    )
