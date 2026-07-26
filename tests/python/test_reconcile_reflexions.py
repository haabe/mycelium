"""Coverage for reconcile_reflexions.py — the learning loop's denominator.

Applies the rule graduated the same day this was written: a guard ships with BOTH
a test proving it BITES (outstanding rises when a reflexion goes unanswered) and
one proving it is CLEAN (outstanding falls to zero when decisions are recorded).
Six guards failed on first contact with real data in the session that produced
this file; every one of them passed its own fixtures first.

The load-bearing test is `test_adding_a_correction_credits_the_balance`. The first
implementation recomputed the corrections baseline as "now" on every run, so
`corrections_since` was permanently 0, no correction ever credited, and the
counter could only ever rise — a nagging number that would have been switched off
within a week.
"""

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
_spec = importlib.util.spec_from_file_location(
    "reconcile_reflexions", _SCRIPTS / "reconcile_reflexions.py",
)
rr = importlib.util.module_from_spec(_spec)
sys.modules["reconcile_reflexions"] = rr
_spec.loader.exec_module(rr)


def _project(tmp_path: Path, corrections: int = 1, fired: int = 0) -> Path:
    (tmp_path / ".claude" / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    body = "# Corrections\n\n" + "".join(
        f"### 2026-07-{i + 1:02d} - entry {i}\nbody\n\n" for i in range(corrections)
    )
    (tmp_path / rr.CORRECTIONS_REL).write_text(body)
    if fired:
        (tmp_path / rr.LOG_REL).write_text("".join(
            json.dumps({"ts": "2026-07-26T00:00:00Z", "tool": "Bash",
                        "command_head": f"cmd-{i}"}) + "\n" for i in range(fired)
        ))
    return tmp_path


def _settle(p: Path) -> dict:
    """status() then persist the baseline, i.e. what the CLI actually does."""
    st = rr.status(p)
    rr.persist_baseline_if_new(p, st)
    return st


# ------------------------------------------------------------------ it bites

def test_a_fired_reflexion_with_no_decision_is_outstanding(tmp_path):
    p = _project(tmp_path, corrections=2, fired=3)
    assert _settle(p)["outstanding"] == 3


def test_outstanding_lists_the_actual_commands(tmp_path):
    """A count alone is unactionable — the operator needs to know which."""
    p = _project(tmp_path, corrections=1, fired=2)
    st = _settle(p)
    assert st["recent"] == ["cmd-0", "cmd-1"]


# ------------------------------------------------------- decisions reconcile

def test_adding_a_correction_credits_the_balance(tmp_path):
    """THE regression test. A baseline recomputed as 'now' on every run made
    corrections_since permanently 0, so the counter could only ever rise."""
    p = _project(tmp_path, corrections=2, fired=3)
    assert _settle(p)["outstanding"] == 3
    with (p / rr.CORRECTIONS_REL).open("a") as fh:
        fh.write("\n### 2026-07-26 - a real learning\nbody\n")
    assert _settle(p)["outstanding"] == 2, "a new correction must credit"


def test_dismissal_with_a_reason_credits_the_balance(tmp_path):
    p = _project(tmp_path, corrections=1, fired=2)
    _settle(p)
    assert rr.dismiss(p, "missing binary on this machine, environment not a learning") == 0
    assert _settle(p)["outstanding"] == 1


def test_dismissal_without_a_real_reason_is_refused(tmp_path):
    """'not a learning' with no why is the silence this exists to end."""
    p = _project(tmp_path, corrections=1, fired=1)
    assert rr.dismiss(p, "nah") == 2
    assert rr.dismiss(p, "") == 2
    assert not (p / rr.DISMISS_REL).exists()
    assert _settle(p)["outstanding"] == 1


def test_both_decision_types_together_reach_zero(tmp_path):
    p = _project(tmp_path, corrections=1, fired=3)
    _settle(p)
    with (p / rr.CORRECTIONS_REL).open("a") as fh:
        fh.write("\n### 2026-07-26 - one\nx\n\n### 2026-07-26 - two\nx\n")
    rr.dismiss(p, "flaky network call, retried successfully, no learning")
    assert _settle(p)["outstanding"] == 0


# ------------------------------------------------------------- honest limits

def test_historical_corrections_do_not_pre_credit(tmp_path):
    """A project with 64 existing corrections must not start with 64 credits."""
    p = _project(tmp_path, corrections=64, fired=2)
    assert _settle(p)["outstanding"] == 2


def test_example_heading_inside_a_code_fence_is_not_a_correction(tmp_path):
    """The template ships an example ### inside a ``` fence."""
    p = _project(tmp_path, corrections=1, fired=1)
    _settle(p)
    with (p / rr.CORRECTIONS_REL).open("a") as fh:
        fh.write("\n```\n### 2026-07-26 - template example, not real\n```\n")
    assert _settle(p)["outstanding"] == 1, "a fenced example must not credit"


def test_no_reflexions_reports_nothing_outstanding(tmp_path):
    p = _project(tmp_path, corrections=3, fired=0)
    st = _settle(p)
    assert st["fired"] == 0
    assert st["outstanding"] == 0


def test_torn_final_line_does_not_crash(tmp_path):
    p = _project(tmp_path, corrections=1, fired=1)
    with (p / rr.LOG_REL).open("a") as fh:
        fh.write('{"ts": "partial')
    assert _settle(p)["fired"] == 1


def test_rebaseline_zeroes_the_balance(tmp_path):
    p = _project(tmp_path, corrections=1, fired=4)
    _settle(p)
    assert rr.rebaseline(p) == 0
    assert rr.status(p)["outstanding"] == 0


def test_missing_project_files_are_not_an_error(tmp_path):
    st = rr.status(tmp_path)
    assert st == {**st, "fired": 0, "outstanding": 0}


# --------------------------------------------------------------------- CLI

def _main(p: Path, *extra: str) -> int:
    argv = sys.argv
    sys.argv = ["reconcile_reflexions.py", "--project-dir", str(p), *extra]
    try:
        return rr.main()
    finally:
        sys.argv = argv


def test_cli_reports_and_never_gates(tmp_path, capsys):
    """Exit 0 even with debt: this reports, it does not block a session end."""
    p = _project(tmp_path, corrections=1, fired=2)
    assert _main(p) == 0
    out = capsys.readouterr().out
    assert "2 OUTSTANDING" in out
    assert "cmd-0" in out


def test_cli_json_shape(tmp_path, capsys):
    p = _project(tmp_path, corrections=1, fired=1)
    assert _main(p, "--json") == 0
    d = json.loads(capsys.readouterr().out)
    assert d["fired"] == 1
    assert d["outstanding"] == 1


def test_cli_persists_the_baseline_so_the_next_run_can_credit(tmp_path, capsys):
    p = _project(tmp_path, corrections=5, fired=1)
    _main(p)
    capsys.readouterr()
    assert (p / rr.LEDGER_REL).is_file(), "baseline must survive the process"
    assert json.loads((p / rr.LEDGER_REL).read_text())["corrections_baseline"] == 5
