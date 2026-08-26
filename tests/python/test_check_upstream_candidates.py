"""check_upstream_candidates must BITE on the two disagreements it exists for.

The registry's value is not remembering what to build — it is knowing what is
ALREADY built. A dogfood pass once found six of ten surfaced items already
shipped, because the log is append-only and nothing walked back to check. So the
guard has to detect both directions: LANDED (marked open, but present) and
REGRESSED (marked shipped, but gone).
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_upstream_candidates

    return check_upstream_candidates


def _tree(tmp_path, marker_body):
    """resolve_root only accepts a dir that LOOKS like the framework repo."""
    tree = tmp_path / "tree"
    (tree / "plugins" / "mycelium").mkdir(parents=True)
    (tree / "marker.txt").write_text(marker_body)
    return tree


def _registry(tmp_path, status, expect):
    reg = tmp_path / "registry.yml"
    reg.write_text(
        "candidates:\n"
        "  - id: probe-me\n"
        "    surfaced: '2026-08-26'\n"
        "    summary: fixture\n"
        f"    status: {status}\n"
        "    verify:\n"
        "      file: marker.txt\n"
        "      pattern: 'THE_FIX'\n"
        f"      expect: {expect}\n"
    )
    return reg


def test_landed_is_detected(scripts_path, tmp_path, capsys):
    """Marked open, but the fix is in the tree. Closing it is the whole point."""
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "THE_FIX is here\n")
    reg = _registry(tmp_path, "open", "absent")
    mod.main(["--registry", str(reg), "--framework-root", str(tree)])
    assert "LANDED" in capsys.readouterr().out


def test_regressed_is_detected(scripts_path, tmp_path, capsys):
    """Marked shipped, but the probe can no longer find it."""
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "the fix was reverted\n")
    reg = _registry(tmp_path, "shipped", "present")
    mod.main(["--registry", str(reg), "--framework-root", str(tree)])
    captured = capsys.readouterr()
    assert "REGRESS" in captured.out + captured.err


def test_missing_registry_is_a_setup_error_not_a_clean_run(scripts_path, tmp_path):
    """No registry must not read as 'nothing outstanding'."""
    mod = _import(scripts_path)
    assert mod.main(["--registry", str(tmp_path / "nope.yml")]) != 0
