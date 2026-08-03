"""Regressions for the 2026-08-03 code-review findings (G-V12).

A max-effort review of the v0.70.0-v0.76.1 releases returned 15 confirmed
findings. The theme is uncomfortable and worth stating in the file that guards
against its recurrence: **the releases built to eliminate green-over-nothing
shipped green-over-nothing.**

The three defects covered here are the ones a unit test can hold:

1. `--json` SKIPPED EVERY REFUSAL. All the refuse-on-empty branches added in
   v0.74.0/v0.75.0 were written inside the `else` of `if args.json:`, so the
   machine-readable path — the one a CI wrapper actually consumes — still exited
   0 over an empty population. Five scripts, including the meta-guard built to
   catch exactly this, which could not see it because it invokes children with
   `--root .` only.

2. validate_canvas INVERTED ITS OWN DISTINCTION. It was made to exit 1 on a
   present-but-empty canvas while an ABSENT canvas kept exiting 0 — backwards,
   since absent is the less-informed case. Worse, `/mycelium:setup` creates
   `.claude/canvas/` holding only `.gitkeep` while the shipped pre-push hook
   gates on the DIRECTORY existing, so every push from a freshly set-up project
   was blocked until the user hand-wrote a YAML file or found `--no-verify`.

3. THE IGNORE FILTER COVERED ONE OF TWO TREE WALKS. v0.73.1 wired `_scan_lib`
   into `_iter_test_files` and missed `_production_modules`, so names harvested
   from git-ignored vendored trees still counted as production reach — silencing
   real findings rather than raising false ones.
"""
import subprocess
import sys
from pathlib import Path

import pytest

# Scripts whose plain and --json paths must agree. The bug was that they did not.
JSON_PARITY = [
    "check_wiring.py",
    "check_negative_control.py",
    "check_doc_references.py",
    "check_legacy_paths.py",
    "check_empty_input_honesty.py",
]


def _empty_repo(tmp_path: Path) -> Path:
    """A tree where every check's PRECONDITION is met and its POPULATION is empty.

    Not a bare directory: with the N/A state in place, a bare tree makes every
    check answer "not applicable" and nothing gets exercised. Precondition met,
    population zero — that is the state under test.
    """
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / "plugins" / "mycelium" / "scripts").mkdir(parents=True)
    (tmp_path / "plugins" / "mycelium" / "hooks").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=False,
                   capture_output=True)
    return tmp_path


@pytest.mark.parametrize("script", JSON_PARITY)
def test_json_and_plain_agree_over_an_empty_population(script, scripts_path, tmp_path):
    """THE SYSTEMIC ONE. Both surfaces must reach the same verdict.

    A wrapper reading exit 0 plus `{"findings": []}` concludes the check passed.
    It had matched nothing.
    """
    repo = _empty_repo(tmp_path)
    target = scripts_path / script
    plain = subprocess.run([sys.executable, str(target), "--root", "."],
                           cwd=repo, capture_output=True, text=True, check=False)
    js = subprocess.run([sys.executable, str(target), "--root", ".", "--json"],
                        cwd=repo, capture_output=True, text=True, check=False)
    assert plain.returncode == js.returncode, (
        f"{script}: plain exited {plain.returncode}, --json exited "
        f"{js.returncode}. The machine-readable surface must not be more "
        f"forgiving than the human one.\nplain: {plain.stdout[-300:]}"
    )
    assert plain.returncode == 1, (
        f"{script} should refuse over an empty population, got "
        f"{plain.returncode}: {plain.stdout[-300:]}"
    )


def _run_validate(scripts_path, arg=None, cwd=None):
    cmd = [sys.executable, str(scripts_path / "validate_canvas.py")]
    if arg:
        cmd.append(str(arg))
    # check=False: a non-zero exit is part of what these tests assert.
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def test_fresh_setup_canvas_is_not_a_failure(scripts_path, tmp_path):
    """`/mycelium:setup` leaves `.claude/canvas/` holding only `.gitkeep`.

    Making that exit 1 blocked every push from a new project through the shipped
    pre-push hook, whose only precondition is that the directory exists.
    """
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / ".gitkeep").touch()
    r = _run_validate(scripts_path, canvas)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "N/A" in r.stdout
    assert "NOT a pass" in r.stdout, (
        "N/A must say it is not a pass, or it becomes the false green it replaced"
    )


def test_absent_canvas_is_na_not_a_silent_success(scripts_path, tmp_path):
    """Absent used to exit 0 with 'Canvas directory not found' while empty exited 1.

    Absent is the STRICTLY LESS INFORMED case; it cannot be the more forgiving one.
    """
    (tmp_path / ".claude").mkdir(parents=True)
    r = _run_validate(scripts_path, cwd=tmp_path)
    assert r.returncode == 0
    assert "N/A" in r.stdout
    assert "nothing was supposed to be" in r.stdout


def test_populated_canvas_still_reports_its_denominator(scripts_path):
    """The pass must remain falsifiable: a count of what it actually validated."""
    r = _run_validate(scripts_path, cwd=scripts_path.parents[2])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout
    assert "canvas files" in r.stdout


def test_ignored_tree_names_do_not_count_as_production_reach(scripts_path, tmp_path):
    """A vendored file name must not satisfy a test's production-reach check.

    Reproduced by the review with a control: a test whose only reference is a
    string matching a file inside a git-ignored tree was NOT flagged, and WAS
    flagged once that tree was removed. The filter suppressed real findings.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True,
                   capture_output=True)
    (tmp_path / ".gitignore").write_text("vendored/\n")
    (tmp_path / "vendored").mkdir()
    (tmp_path / "vendored" / "uniquevendorname.py").write_text("x = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_fake.py").write_text(
        'def test_a():\n    assert "uniquevendorname"\n'
    )
    r = subprocess.run(
        [sys.executable, str(scripts_path / "check_test_authenticity.py"),
         "--root", "."],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert "production names derived: 0" in r.stdout, (
        "names inside a git-ignored tree must not be harvested as production:\n"
        + r.stdout
    )
    assert "no-production-reach" in r.stdout, (
        "and the real finding must therefore surface"
    )
    assert r.returncode == 1
