"""Coverage tests for check_cycle_recording.py — the meta-dogfood cycle trigger.

Locks in the defect this shipped for (dogfood 2026-08-06): every trigger in
`engine/cycle-learning.md#when-to-record` was keyed to the LEAF lifecycle, and
the only opener of a `meta-dogfood` cycle in the codebase fired at a diamond
PHASE TRANSITION. Framework work does not move diamonds through phases — it
ships releases. So the dogfood project shipped 48 minor releases across 49 days
with zero cycles, and nothing could distinguish "no cycle was owed" from "a
cycle was owed and nobody noticed".

The absent-input cases carry as much weight as the positive one. This check
lives inside anti-pattern #9 (Fail-Open on Absent Input), so a branch that
cannot tell "no releases exist" from "my pattern never matched" would reproduce
the class it was built against — hence the `no-releases-matched` token test and
the loud failure when git cannot be reached at all.
"""
import subprocess
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_cycle_recording

    return check_cycle_recording


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(path, subjects=()):
    """Build a real git repo whose commit subjects are `subjects`."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "T")
    for i, subject in enumerate(subjects):
        (path / f"f{i}.txt").write_text(str(i))
        _git(path, "add", "-A")
        _git(path, "commit", "-q", "-m", subject)
    return path


def _cycles(project, *completions):
    """Write a cycle-history.yml with the given completed_at stamps."""
    body = ["schema_version: 1", "cycles:"]
    for i, stamp in enumerate(completions, start=1):
        body.append(f"  - cycle_id: cycle-{i:03d}")
        body.append("    cycle_class: meta-dogfood")
        body.append(f'    completed_at: "{stamp}"')
    if not completions:
        body[-1] = "cycles: []"
    path = project / ".claude" / "canvas" / "cycle-history.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n")
    return path


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_cycle_recording", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


# --- the positive case: releases piled up after a recorded cycle -------------

def test_arc_owed_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [
        "v0.90.0: a", "v0.91.0: b", "v0.92.0: c", "v0.93.0: d", "v0.94.0: e",
    ])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "cycle-001" in out          # names the cycle it measured from
    assert "retrospective" in out      # states the one available remedy


def test_arc_under_threshold_passes(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "OK" in capsys.readouterr().out


def test_patch_releases_do_not_count(scripts_path, tmp_path):
    """Steady-state maintenance earns no cycle — the 2026-06-18 ruling."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [
        "v0.90.1: a", "v0.90.2: b", "v0.90.3: c", "v0.90.4: d", "v0.90.5: e",
    ])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0


def test_two_releases_in_one_subject_both_counted(scripts_path, tmp_path):
    """Upstream v0.95.2 exists because an earlier step read only the first."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.95.0 + v0.96.0: two in one commit"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--threshold", "2") == 1


# --- absent-input discipline (anti-pattern #9) ------------------------------

def test_no_cycle_history_is_not_a_violation(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "SKIP" in capsys.readouterr().out


def test_never_recorded_is_its_own_state_not_a_giant_arc(scripts_path, tmp_path, capsys):
    """An unmeetable demand gets muted, which leaves the check decorative."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [f"v0.{n}.0: r" for n in range(10, 40)])
    _cycles(project)  # file exists, zero cycles

    assert _run(mod, "--project-dir", str(project)) == 1
    out = capsys.readouterr().out
    assert "never-recorded" in out
    assert "NOT an arc" in out
    assert "one-time step" in out


def test_no_releases_matched_says_so_with_its_pattern(scripts_path, tmp_path, capsys):
    """'None found' and 'my pattern is broken' must not be the same output."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: no version here", "fix: nor here"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0
    out = capsys.readouterr().out
    assert "no-releases-matched" in out
    assert "commit subject" in out
    assert "pattern was" in out         # shows its working


def test_not_a_git_repo_fails_loud_not_silent(scripts_path, tmp_path, capsys):
    """'I could not look' must never render as 'nothing to report'."""
    mod = _import(scripts_path)
    project = tmp_path / "plain"
    (project / ".claude" / "canvas").mkdir(parents=True)
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 2
    assert "ERROR" in capsys.readouterr().err


# --- cross-repo pairing -----------------------------------------------------

def test_release_repo_can_differ_from_ledger_and_is_disclosed(scripts_path, tmp_path, capsys):
    """A dogfood consumer records cycles locally while releases ship upstream.

    Scanning the wrong repo yields a plausible number rather than an error, so
    the output must always say where the count came from.
    """
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["chore: local work only"])
    upstream = _repo(tmp_path / "upstream", [f"v0.{n}.0: r" for n in range(10, 20)])
    _cycles(ledger, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(ledger), "--release-repo", str(upstream)) == 1
    out = capsys.readouterr().out
    assert "releases counted in" in out
    assert str(upstream) in out


def test_missing_release_repo_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--release-repo", str(tmp_path / "nope")) == 2
    assert "not a directory" in capsys.readouterr().err


# --- threshold resolution ---------------------------------------------------

def test_threshold_read_from_canvas(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text(
        "thresholds:\n  cycle_recording_arc:\n    default: 2\n    calibrated: null\n"
    )

    assert _run(mod, "--project-dir", str(project)) == 1
    assert "cycle_recording_arc" in capsys.readouterr().out


def test_calibrated_threshold_wins_over_default(scripts_path, tmp_path):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text(
        "thresholds:\n  cycle_recording_arc:\n    default: 2\n    calibrated: 9\n"
    )

    assert _run(mod, "--project-dir", str(project)) == 0


def test_unreadable_thresholds_falls_back_visibly(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text("{[not: valid yaml")

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "unreadable" in capsys.readouterr().out


def test_bad_release_pattern_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--release-pattern", "((") == 2
    assert "bad --release-pattern" in capsys.readouterr().err


def test_json_output_is_machine_readable(scripts_path, tmp_path, capsys):
    import json

    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [f"v0.{n}.0: r" for n in range(10, 20)])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "cycle-owed"
    assert payload["releases"] == 10
