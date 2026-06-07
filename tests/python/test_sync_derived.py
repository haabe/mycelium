"""Unit tests for sync_derived.py (version + skill-count token sync)."""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import sync_derived  # noqa: PLC0415
    return sync_derived


def _mini_repo(root, version="1.2.3", n_skills=3, plugin_version="1.2.3", token_count=3,
               card_version=None):
    """Build a minimal repo tree the syncer understands."""
    (root / "plugins/mycelium/.claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "docs/skills").mkdir(parents=True)
    for i in range(n_skills):
        # First real skill dir is diamond-assess — it carries a "<N> skills"
        # harness-thickness token that the syncer now sweeps (finding C guard).
        name = "diamond-assess" if i == 0 else f"skill{i}"
        d = root / f"plugins/mycelium/skills/{name}"
        d.mkdir(parents=True)
        body = "---\nname: x\n---\n"
        if i == 0:
            body += f"\n- Current: {token_count} skills, 12 gates\n"
        (d / "SKILL.md").write_text(body)

    (root / "CLAUDE.md").write_text(
        f"# Title\n\n*Version {version} -- prose that must survive.*\n\nAll {token_count} skills are discovered.\n"
    )
    (root / "README.md").write_text(
        f"Not {token_count} skills dumped on you.\n\n| look up | ({token_count} skills) |\n"
    )
    (root / "docs/skills/README.md").write_text(f"This index lists all {token_count} skills.\n")
    (root / "docs/skills/by-category.md").write_text(f"Same {token_count} skills, different ordering.\n")
    (root / "docs/ai-system-card.md").write_text(
        f"# AI System Card\n\n- **Version:** {card_version or plugin_version}\n\n"
        f"- **Skills:** {token_count} skills define the procedures.\n"
    )
    (root / "plugins/mycelium/.claude-plugin/plugin.json").write_text(
        f'{{\n  "version": "{plugin_version}",\n  "description": "{token_count} skills, 13 gates."\n}}\n'
    )
    (root / ".claude-plugin/marketplace.json").write_text(
        f'{{\n  "description": "{token_count} skills, six scales."\n}}\n'
    )
    return root


def test_no_drift_is_noop(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, version="1.2.3", n_skills=3, plugin_version="1.2.3", token_count=3)
    assert mod.sync(root, check_only=True) == 0


def test_check_detects_version_drift(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, version="2.0.0", plugin_version="1.9.9", n_skills=3, token_count=3)
    assert mod.sync(root, check_only=True) == 1  # plugin.json behind CLAUDE.md


def test_check_detects_skill_count_drift(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, n_skills=5, token_count=3)  # 5 real dirs, docs say 3
    assert mod.sync(root, check_only=True) == 1


def test_check_detects_card_version_drift(scripts_path, tmp_path):
    mod = _import(scripts_path)
    # CLAUDE.md and plugin.json agree; only the system card's version is stale.
    root = _mini_repo(tmp_path, version="2.0.0", plugin_version="2.0.0",
                      card_version="1.0.0", n_skills=3, token_count=3)
    assert mod.sync(root, check_only=True) == 1


def test_sync_fixes_version_and_skill_count(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, version="2.0.0", plugin_version="1.0.0", n_skills=5, token_count=3)
    assert mod.sync(root, check_only=False) == 0
    # plugin.json version now matches CLAUDE.md
    plugin = (root / "plugins/mycelium/.claude-plugin/plugin.json").read_text()
    assert '"version": "2.0.0"' in plugin
    # every "<N> skills" token is now 5
    assert "5 skills" in plugin
    assert "5 skills" in (root / "CLAUDE.md").read_text()
    assert "5 skills" in (root / "README.md").read_text()
    assert "5 skills" in (root / ".claude-plugin/marketplace.json").read_text()
    assert "5 skills" in (root / "docs/skills/README.md").read_text()
    assert "5 skills" in (root / "docs/skills/by-category.md").read_text()
    assert "5 skills" in (root / "plugins/mycelium/skills/diamond-assess/SKILL.md").read_text()
    # the published AI System Card gets BOTH the version and the skill count
    card = (root / "docs/ai-system-card.md").read_text()
    assert "**Version:** 2.0.0" in card
    assert "5 skills" in card
    # prose around the version token survived untouched
    assert "prose that must survive" in (root / "CLAUDE.md").read_text()
    # re-check is now clean
    assert mod.sync(root, check_only=True) == 0


def test_sync_is_idempotent(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, version="2.0.0", plugin_version="1.0.0", n_skills=5, token_count=3)
    mod.sync(root, check_only=False)
    before = (root / "plugins/mycelium/.claude-plugin/plugin.json").read_text()
    mod.sync(root, check_only=False)
    after = (root / "plugins/mycelium/.claude-plugin/plugin.json").read_text()
    assert before == after


def test_missing_version_line_raises(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path)
    (root / "CLAUDE.md").write_text("# Title\n\nno version line here\n")
    try:
        mod.canonical_version(root)
    except ValueError:
        return
    raise AssertionError("expected ValueError on missing *Version line")


def test_zero_skills_raises(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _mini_repo(tmp_path, n_skills=0)
    try:
        mod.canonical_skill_count(root)
    except ValueError:
        return
    raise AssertionError("expected ValueError on zero SKILL.md files")
