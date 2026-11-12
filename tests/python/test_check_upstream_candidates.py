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


# ------------------------------------------------------------------ the different-builder test (0.195.0)

def _registry_dated(tmp_path, surfaced, scenario):
    reg = tmp_path / "registry.yml"
    extra = f"    different_builder: {scenario}\n" if scenario else ""
    reg.write_text(
        "candidates:\n"
        "  - id: thing\n"
        f'    surfaced: "{surfaced}"\n'
        "    status: open\n"
        "    summary: a finding\n"
        + extra
    )
    return reg


def test_a_new_candidate_without_a_scenario_is_refused_under_strict(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "x")
    reg = _registry_dated(tmp_path, "2026-09-12", None)
    assert mod.main(["--registry", str(reg), "--framework-root", str(tree), "--strict"]) == 1
    assert "NO DIFFERENT-BUILDER SCENARIO" in capsys.readouterr().out


def test_a_new_candidate_with_a_scenario_passes(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "x")
    reg = _registry_dated(tmp_path, "2026-09-12", "a solo dev on a CLI tool hits the same silent allow")
    assert mod.main(["--registry", str(reg), "--framework-root", str(tree), "--strict"]) == 0
    assert "NO DIFFERENT-BUILDER SCENARIO" not in capsys.readouterr().out


def test_an_older_candidate_is_not_backfilled(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "x")
    reg = _registry_dated(tmp_path, "2026-09-01", None)
    assert mod.main(["--registry", str(reg), "--framework-root", str(tree), "--strict"]) == 0



# ------------------------------------------------------------------ statuses other than open/shipped

def test_a_proposed_entry_whose_probe_flips_is_landed(scripts_path, tmp_path, capsys):
    """RED BEFORE THE FIX: classify() knew only `open` and `shipped`, so a `proposed` or
    `surfaced` entry whose change had landed printed ok. Dogfood 2026-10-11: 59 such probes."""
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "THE_FIX is here\n")
    for status in ("proposed", "surfaced", "reopened_on_proposal_b"):
        reg = _registry(tmp_path, status, "absent")
        mod.main(["--registry", str(reg), "--framework-root", str(tree)])
        out = capsys.readouterr().out
        assert "LANDED  probe-me" in out, status
        assert f"statuses: {status}" in out


def test_a_closed_entry_is_not_compared_and_is_counted(scripts_path, tmp_path, capsys):
    """Declined, withdrawn and the rest make no claim about the tree: never LANDED."""
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "THE_FIX is here\n")
    for status in ("declined", "withdrawn", "resolved-by-design", "no-longer-reproduces"):
        reg = _registry(tmp_path, status, "absent")
        mod.main(["--registry", str(reg), "--framework-root", str(tree)])
        out = capsys.readouterr().out
        assert "LANDED  probe-me" not in out, status
        assert "1  closed, not compared" in out, status


def test_rule_counts_are_printed_on_every_run(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "nothing\n")
    reg = _registry(tmp_path, "shipped", "absent")
    mod.main(["--registry", str(reg), "--framework-root", str(tree)])
    out = capsys.readouterr().out
    assert "Probes evaluated per rule:" in out
    assert "1  shipped rule" in out
    assert "0  open rule" in out


def _registry_status_dated(tmp_path, status):
    reg = tmp_path / "registry.yml"
    reg.write_text(
        "candidates:\n"
        "  - id: thing\n"
        '    surfaced: "2026-09-12"\n'
        f"    status: {status}\n"
        "    summary: a finding\n"
    )
    return reg


def test_a_closed_candidate_without_a_scenario_does_not_fail_strict(scripts_path, tmp_path, capsys):
    """RED BEFORE THE FIX: _no_scenario read the surfaced date only, so a shipped or withdrawn
    row failed --strict for a sentence that can no longer change any decision."""
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "x")
    for status in ("shipped", "declined", "withdrawn", "retracted", "resolved-by-design",
                   "no-longer-reproduces"):
        reg = _registry_status_dated(tmp_path, status)
        args = ["--registry", str(reg), "--framework-root", str(tree), "--strict"]
        assert mod.main(args) == 0, status
        assert "NO DIFFERENT-BUILDER SCENARIO" not in capsys.readouterr().out


def test_an_open_like_candidate_without_a_scenario_still_fails_strict(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    tree = _tree(tmp_path, "x")
    for status in ("proposed", "surfaced"):
        reg = _registry_status_dated(tmp_path, status)
        args = ["--registry", str(reg), "--framework-root", str(tree), "--strict"]
        assert mod.main(args) == 1, status
        assert "NO DIFFERENT-BUILDER SCENARIO" in capsys.readouterr().out
