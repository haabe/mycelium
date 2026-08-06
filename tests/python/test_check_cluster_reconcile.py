"""Coverage tests for check_cluster_reconcile.py — the corrections->cluster hop guard.

Locks in the defect (dogfood 2026-08-06, opp-034): `cluster-instances.md`
graduates clusters on instance COUNTS, and nothing writes those counts. In one
measured window corrections.md gained 24 entries while the catalogue gained one
row, so count-keyed graduation triggers were evaluating a number that had
drifted and could not fire.

The most important test here is `test_dated_prose_edit_does_not_green_it`. The
first version of this script matched any ISO date anywhere in the catalogue and
went green on its own first live run, because that session had added a dated
closure note to an existing instance's outcome cell. A dated sentence anywhere
would have silenced it permanently — the "cheapest green is a no-op edit"
failure the script's own header warns about. Found by running it, not by
reading it.
"""
import json
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_cluster_reconcile

    return check_cluster_reconcile


def _memory(project, corrections="", clusters=""):
    mem = project / ".claude" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "corrections.md").write_text(corrections)
    (mem / "cluster-instances.md").write_text(clusters)
    return mem


def _corrections(*dates):
    return "\n\n".join(f"### {d} — something went wrong\n\nbody" for d in dates)


def _rows(*dates):
    """An instance-log table with one row per date."""
    head = "| # | Date | Title | Subclass | Outcome |\n|---|---|---|---|---|\n"
    return head + "\n".join(
        f"| {i} | {d} | a title | a subclass | an outcome |"
        for i, d in enumerate(dates, start=1)
    )


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_cluster_reconcile", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


# --- the defect this shipped for -------------------------------------------

def test_lapse_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections("2026-08-01", "2026-08-02", "2026-08-03",
                                 "2026-08-04", "2026-08-05"),
        clusters=_rows("2026-07-20"),
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "does NOT classify" in out          # the non-goal is stated to the user
    assert "reviewed-no-cluster-applies" in out  # both escape routes offered


def test_under_threshold_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections("2026-08-01", "2026-08-02"),
        clusters=_rows("2026-07-20"),
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_logging_an_instance_greens_it(scripts_path, tmp_path):
    """Honest route 1: a real dated instance row."""
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters=_rows("2026-07-20", "2026-08-05"),
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


# --- the false green found by running it ------------------------------------

def test_dated_prose_edit_does_not_green_it(scripts_path, tmp_path):
    """A dated closure note is prose maintenance, not a logged instance.

    This is the regression the first implementation shipped with.
    """
    mod = _import(scripts_path)
    clusters = _rows("2026-07-20") + (
        "\n\n**CLOSED 2026-08-09** — fixed upstream, note added to the outcome cell.\n"
        "**Most recent:** 2026-08-09\n"
    )
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters=clusters,
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 1


def test_whitespace_edit_does_not_green_it(scripts_path, tmp_path):
    mod = _import(scripts_path)
    corrections = _corrections(*[f"2026-08-0{n}" for n in range(1, 6)])
    _memory(tmp_path, corrections=corrections, clusters=_rows("2026-07-20") + "\n\n\n   \n")
    assert _run(mod, "--project-dir", str(tmp_path)) == 1


# --- the dated escape hatch -------------------------------------------------

def test_reviewed_marker_greens_it(scripts_path, tmp_path, capsys):
    """Honest route 2: declare them considered and inapplicable, with a date."""
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters=_rows("2026-07-20") + "\n\nreviewed-no-cluster-applies: 2026-08-05\n",
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 0
    assert "reviewed through 2026-08-05" in capsys.readouterr().out


def test_stale_reviewed_marker_does_not_green_it(scripts_path, tmp_path):
    """The marker is dated so it cannot be a permanent silencer."""
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters=_rows("2026-07-20") + "\n\nreviewed-no-cluster-applies: 2026-07-01\n",
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 1


# --- absent-input discipline (anti-pattern #9) ------------------------------

def test_missing_files_are_not_a_violation(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "memory").mkdir(parents=True)
    assert _run(mod, "--project-dir", str(tmp_path)) == 0
    assert "SKIP" in capsys.readouterr().out


def test_no_dated_corrections_says_so_with_its_pattern(scripts_path, tmp_path, capsys):
    """'None found' and 'my regex is broken' must not be the same output."""
    mod = _import(scripts_path)
    _memory(tmp_path, corrections="# Corrections\n\nprose, no dated headings\n",
            clusters=_rows("2026-07-20"))
    assert _run(mod, "--project-dir", str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "no-dated-corrections" in out
    assert "pattern was" in out


def test_catalogue_with_no_rows_counts_everything(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters="# Cluster Instances\n\nNo instances logged yet.\n",
    )
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
    assert "NO date at all" in capsys.readouterr().out


def test_lettered_suffix_date_is_counted(scripts_path, tmp_path):
    """corrections.md really carries a `### 2026-08-02b` entry."""
    mod = _import(scripts_path)
    body = _corrections("2026-08-01") + "\n\n### 2026-08-02b — a second entry that day\n\nbody"
    _memory(tmp_path, corrections=body, clusters=_rows("2026-07-20"))
    assert _run(mod, "--project-dir", str(tmp_path), "--threshold", "2") == 1


# --- interface --------------------------------------------------------------

def test_json_output(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _memory(
        tmp_path,
        corrections=_corrections(*[f"2026-08-0{n}" for n in range(1, 6)]),
        clusters=_rows("2026-07-20"),
    )
    assert _run(mod, "--project-dir", str(tmp_path), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "unreconciled"
    assert payload["unreconciled_count"] == 5


def test_bad_threshold_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _memory(tmp_path, corrections=_corrections("2026-08-01"), clusters=_rows("2026-07-20"))
    assert _run(mod, "--project-dir", str(tmp_path), "--threshold", "0") == 2
    assert "must be >= 1" in capsys.readouterr().err


def test_missing_project_dir_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    assert _run(mod, "--project-dir", str(tmp_path / "nope")) == 2
    assert "not a directory" in capsys.readouterr().err
