"""Coverage tests for check_bvssh_reconcile.py — the BVSSH orphan guard (G-V12).

Locks in the real defect this shipped for: `/bvssh-check` mandated a
decision-log append and never mentioned `bvssh-health.yml`, while
`hooks/session-start.sh` computes the "overdue" reminder from that canvas.
Assessments landed in provenance and never in the file the framework reads.

Three historical orphans are the fixtures behind these cases:
  - 2026-05-20 (framework repo)
  - 2026-06-20 (dogfood; noticed, "fixed" with a prose rule in a notes field)
  - 2026-07-11 (dogfood; the prose rule did not hold, because the skill never
    had the step)

The absent-input cases matter as much as the positive one: a project that has
never run /bvssh-check must not be flagged (anti-pattern #9 cuts both ways —
fail loud on a real gap, stay quiet when there is genuinely nothing to check).
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_bvssh_reconcile

    return check_bvssh_reconcile


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _log(project, *dates):
    body = "\n\n".join(
        f"### BVSSH Assessment — {d} (assessment #{i}; some context)\n\nnotes here"
        for i, d in enumerate(dates, start=1)
    )
    _write(project / ".claude/harness/decision-log.md", body)


def _canvas(project, *dates):
    entries = "\n".join(
        f'  - date: "{d}T00:00:00Z"\n'
        f'    better: "stable"\n'
        f'    notes: "entry for {d}"'
        for d in dates
    )
    history = f"assessment_history:\n{entries}\n" if dates else "assessment_history: []\n"
    _write(project / ".claude/canvas/bvssh-health.yml", history)


def test_orphaned_assessment_is_flagged(scripts_path, tmp_path):
    """The core defect: logged but never reconciled to canvas -> exit 1."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _canvas(tmp_path, "2026-06-22")

    result = mod.check(tmp_path)
    assert result["status"] == "orphaned"
    assert result["orphaned_in_log_only"] == ["2026-07-11"]


def test_all_three_historical_orphans_are_caught(scripts_path, tmp_path):
    """The real-world fixture set that motivated the guard."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-05-20", "2026-06-20", "2026-06-22", "2026-07-11")
    _canvas(tmp_path, "2026-06-22")

    result = mod.check(tmp_path)
    assert result["orphaned_in_log_only"] == ["2026-05-20", "2026-06-20", "2026-07-11"]


def test_reconciled_project_passes(scripts_path, tmp_path):
    """Every logged assessment present in the canvas -> exit 0."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-06-22", "2026-07-25")
    _canvas(tmp_path, "2026-06-22", "2026-07-25")

    result = mod.check(tmp_path)
    assert result["status"] == "reconciled"
    assert result["orphaned_in_log_only"] == []


def test_never_assessed_project_is_not_flagged(scripts_path, tmp_path):
    """A project that never ran /bvssh-check is not in violation."""
    mod = _import(scripts_path)
    _write(tmp_path / ".claude/harness/decision-log.md", "# Decision Log\n\nno bvssh yet")
    _write(tmp_path / ".claude/canvas/bvssh-health.yml", "last_assessed: null\n")

    result = mod.check(tmp_path)
    assert result["status"] == "nothing-to-reconcile"


def test_missing_files_entirely_is_not_flagged(scripts_path, tmp_path):
    """Absent input is not evidence of an orphan (anti-pattern #9, quiet side)."""
    mod = _import(scripts_path)

    result = mod.check(tmp_path)
    assert result["status"] == "nothing-to-reconcile"


def test_canvas_written_without_log_is_info_not_failure(scripts_path, tmp_path):
    """The harmless direction: canvas is the source of truth, so do not fail it."""
    mod = _import(scripts_path)
    _write(tmp_path / ".claude/harness/decision-log.md", "# Decision Log\n")
    _canvas(tmp_path, "2026-07-25")

    result = mod.check(tmp_path)
    assert result["status"] == "reconciled"
    assert result["canvas_only_info"] == ["2026-07-25"]


def test_log_entries_with_empty_canvas_fail(scripts_path, tmp_path):
    """Assessments logged while the canvas holds no history at all -> orphaned."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _canvas(tmp_path)

    result = mod.check(tmp_path)
    assert result["status"] == "orphaned"
    assert result["orphaned_in_log_only"] == ["2026-07-11"]


def test_bare_date_and_timestamp_history_forms_both_match(scripts_path, tmp_path):
    """History dates appear as ISO timestamps, bare strings, or parsed dates."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-25")
    _write(
        tmp_path / ".claude/canvas/bvssh-health.yml",
        'assessment_history:\n  - date: 2026-07-25\n    notes: "unquoted -> parsed date"\n',
    )

    result = mod.check(tmp_path)
    assert result["status"] == "reconciled"


def test_duplicate_log_dates_reconcile_against_one_entry(scripts_path, tmp_path):
    """Two assessments the same day need only one canvas entry."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-25", "2026-07-25")
    _canvas(tmp_path, "2026-07-25")

    result = mod.check(tmp_path)
    assert result["status"] == "reconciled"


def _run_cli(mod, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["check_bvssh_reconcile.py", *argv])
    return mod.main()


def test_cli_exits_1_and_names_the_orphan(scripts_path, tmp_path, monkeypatch, capsys):
    """Operator-facing path: non-zero exit + the orphaned date in the output."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _canvas(tmp_path, "2026-06-22")

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "2026-07-11" in out
    assert "ORPHANED" in out
    # The message must explain WHY it matters, not just that it failed.
    assert "session-start.sh" in out


def test_cli_exits_0_when_reconciled(scripts_path, tmp_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-25")
    _canvas(tmp_path, "2026-07-25")

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_reports_canvas_only_as_info(scripts_path, tmp_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    _write(tmp_path / ".claude/harness/decision-log.md", "# Decision Log\n")
    _canvas(tmp_path, "2026-07-25")

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(tmp_path)]) == 0
    assert "INFO (not a failure)" in capsys.readouterr().out


def test_cli_nothing_to_reconcile_is_quiet_success(scripts_path, tmp_path, monkeypatch, capsys):
    mod = _import(scripts_path)

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(tmp_path)]) == 0
    assert "nothing to reconcile" in capsys.readouterr().out


def test_cli_json_mode_round_trips(scripts_path, tmp_path, monkeypatch, capsys):
    import json as _json

    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _canvas(tmp_path, "2026-06-22")

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(tmp_path), "--json"]) == 1
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "orphaned"
    assert payload["orphaned_in_log_only"] == ["2026-07-11"]


def test_cli_bad_project_dir_is_argument_error(scripts_path, tmp_path, monkeypatch, capsys):
    """Exit 2 (input error), distinct from exit 1 (a real orphan)."""
    mod = _import(scripts_path)
    missing = tmp_path / "does-not-exist"

    assert _run_cli(mod, monkeypatch, ["--project-dir", str(missing)]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_unparseable_canvas_does_not_crash(scripts_path, tmp_path):
    """Malformed YAML does not raise — AND is not reported as a pile of orphans.

    AMENDED 2026-08-26. The intent in the original docstring ("degrades to 'no
    canvas dates', it does not raise") still holds and is still asserted. What
    changed is the means: the old assertion `status == "orphaned"` proved the
    no-crash property by pinning the CONSEQUENCE of the fail-open — an unreadable
    canvas made every decision-log date look missing from it, so the check
    reported the wrong thing loudly. Reading a parse failure as data was the
    defect; the test had frozen it as the contract.
    """
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _write(tmp_path / ".claude/canvas/bvssh-health.yml", "assessment_history: [oops\n")

    result = mod.check(tmp_path)          # still does not raise
    assert result["status"] == "unreadable"
    assert result["unreadable"] == ["bvssh-health.yml"]


def test_history_entries_without_dates_are_ignored(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-11")
    _write(
        tmp_path / ".claude/canvas/bvssh-health.yml",
        'assessment_history:\n  - notes: "no date field"\n  - date: null\n',
    )

    result = mod.check(tmp_path)
    assert result["orphaned_in_log_only"] == ["2026-07-11"]


def test_canvas_env_override_is_honoured(scripts_path, tmp_path, monkeypatch):
    """Framework-self-host keeps its canvas in a sibling repo (MYCELIUM_BVSSH_CANVAS)."""
    mod = _import(scripts_path)
    _log(tmp_path, "2026-07-25")
    _canvas(tmp_path)  # local canvas is empty -> would be orphaned

    sibling = tmp_path / "sibling" / "bvssh-health.yml"
    _write(
        sibling,
        'assessment_history:\n  - date: "2026-07-25T00:00:00Z"\n    notes: "in sibling"\n',
    )
    monkeypatch.setenv("MYCELIUM_BVSSH_CANVAS", str(sibling))

    result = mod.check(tmp_path)
    assert result["status"] == "reconciled"
