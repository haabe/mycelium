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
    import check_doc_references

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


# --- consumer-tree scope (v0.108.0) ----------------------------------------
#
# The five original globs are the FRAMEWORK repo's shape. A plugin consumer has no
# plugins/mycelium/ tree and keeps its docs under .claude/, so on a real dogfood repo
# this check scanned 29 of 212 markdown files and reported "no dead references" while
# 158 links sat unexamined — three of them dead for 88 days, pointing at directories
# removed by that project's plugin migration.

def test_dead_link_in_consumer_claude_tree_is_caught(scripts_path, tmp_path, capsys):
    """THE NEGATIVE CONTROL for the widened scope: the exact shape found in dogfood."""
    mod = _import(scripts_path)
    _write(
        tmp_path / ".claude/canvas/README.md",
        "Schemas live in [`../schemas/canvas/`](../schemas/canvas/).",
    )
    assert mod.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "DEAD" in out
    assert "../schemas/canvas/" in out


def test_live_link_in_consumer_claude_tree_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _write(tmp_path / ".claude/canvas/purpose.yml", "x: 1")
    _write(tmp_path / ".claude/canvas/README.md", "See [purpose](purpose.yml).")
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_fixture_trees_under_claude_are_not_scanned(scripts_path, tmp_path):
    """Vendored fixtures carry links into their own source repos. Those are not a
    finding about THIS project, and flagging them is how a guard gets ignored."""
    mod = _import(scripts_path)
    # A real scannable link so the population is non-empty; with only the excluded
    # fixture present the check correctly refuses rather than reporting a pass.
    _write(tmp_path / ".claude/canvas/purpose.yml", "x: 1")
    _write(tmp_path / ".claude/canvas/README.md", "See [purpose](purpose.yml).")
    _write(
        tmp_path / ".claude/auto-dogfood/.fixtures/vendored/README.md",
        "[logo](./script/output/user_count.svg)",
    )
    assert mod.main(["--root", str(tmp_path)]) == 0
