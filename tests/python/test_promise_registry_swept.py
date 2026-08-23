"""Coverage for check_promise_registry_swept (v0.122.0).

WHY. The Promise registry is the framework's instrument for prose that claims a surface
does something nothing implements. On 2026-08-23 it held four rows, all closed, all from a
single 2026-06-12 analysis, and had gained nothing in ten weeks — while a rule census that
same day found two fresh instances. **The registry did not fail; nothing swept it.** Its
sweep is `/framework-health` step 4f, prose in a skill, so the file could not tell "nothing
to add" from "nobody looked".

THE FOUR WAYS THIS COULD ROT:

  1. IT BECOMES BYPASSABLE. A future `last_swept` silences it forever, for the cost of
     typing a date. That is the cheapest possible way to turn an instrument into decoration
     and it is the first thing a hurried author reaches for.
  2. IT CONFLATES ABSENT WITH STALE. Absent means the contract was never adopted; stale
     means it was adopted and then not honoured. Reporting them the same way loses the
     distinction the whole check exists to make.
  3. IT BREAKS A CONSUMER'S BUILD. Downstream projects inherit this file and cannot set the
     date. Advisory by default, teeth only under --strict.
  4. IT REPORTS A PASS OVER NOTHING. A missing spec is a PRECONDITION failure (exit 2),
     not a zero. check_empty_input_honesty caught exactly this in the first draft.
  5. ITS FIXTURES DECAY. A test pinned to the real clock fails on a date nobody chose, so
     every case pins --today.
"""
import datetime
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_promise_registry_swept.py"
TODAY = datetime.date(2026, 8, 23)


def _mod():
    spec = importlib.util.spec_from_file_location("prs", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["prs"] = m
    spec.loader.exec_module(m)
    return m


def _repo(tmp_path, marker: str | None):
    d = tmp_path / "engine"
    d.mkdir(parents=True, exist_ok=True)   # callable twice in one test (advisory then --strict)
    body = "# spec\n## Promise registry\n"
    if marker:
        body += f"**last_swept: {marker}**\n"
    (d / "consistency-check-spec.md").write_text(body)
    return tmp_path


def _run(root, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--today", "2026-08-23", *extra],
        capture_output=True, text=True, check=False,
    )


def test_recent_sweep_passes(tmp_path):
    r = _run(_repo(tmp_path, "2026-08-01"))
    assert r.returncode == 0
    assert "ok — last swept" in r.stdout
    assert "22d ago" in r.stdout, "the age must be reported, not just a verdict"


def test_stale_sweep_is_named(tmp_path):
    r = _run(_repo(tmp_path, "2020-01-01"))
    assert "STALE" in r.stdout
    assert "EVEN IF" in r.stdout, "the remedy must say to update the marker even when nothing is added"


def test_absent_marker_is_not_the_same_finding_as_stale(tmp_path):
    """Rule 2."""
    r = _run(_repo(tmp_path, None))
    assert "MISSING" in r.stdout
    assert "STALE" not in r.stdout
    assert "nobody looked" in r.stdout


def test_future_date_is_refused(tmp_path):
    """Rule 1 — the bypass path."""
    r = _run(_repo(tmp_path, "2999-01-01"))
    assert "FUTURE" in r.stdout
    assert "ok — last swept" not in r.stdout


def test_future_date_fails_under_strict(tmp_path):
    assert _run(_repo(tmp_path, "2999-01-01"), "--strict").returncode == 1


def test_unparseable_date_reads_as_missing(tmp_path):
    r = _run(_repo(tmp_path, "not-a-date"))
    assert "MISSING" in r.stdout


def test_advisory_by_default_strict_has_teeth(tmp_path):
    """Rule 3."""
    root = _repo(tmp_path, "2020-01-01")
    assert _run(root).returncode == 0
    assert _run(root, "--strict").returncode == 1


def test_a_missing_spec_is_a_precondition_failure_not_a_pass(tmp_path):
    """Rule 5, added after check_empty_input_honesty flagged the first draft.

    A MISSING SPEC and a SPEC WITH NO ROWS are different states, and only the second is a
    legitimate zero. Exiting 0 on the first is the shape that "reads green forever".
    """
    r = _run(tmp_path)
    assert r.returncode == 2, "precondition failure, not success"
    assert "PRECONDITION UNMET" in r.stdout
    assert "not a pass" in r.stdout


def test_it_also_finds_the_spec_at_the_plugin_path(tmp_path):
    d = tmp_path / "plugins" / "mycelium" / "engine"
    d.mkdir(parents=True)
    (d / "consistency-check-spec.md").write_text("**last_swept: 2026-08-20**")
    assert "ok — last swept" in _run(tmp_path).stdout


def test_max_age_is_configurable(tmp_path):
    root = _repo(tmp_path, "2026-06-01")
    assert "ok — last swept" in _run(root).stdout           # 83d, under the 90d default
    assert "STALE" in _run(root, "--max-age-days", "30").stdout


@pytest.mark.parametrize(("marker", "expected"), [("2026-08-23", 0), ("2026-05-01", 114)])
def test_sweep_age_helper(marker, expected):
    when, age = _mod().sweep_age(f"**last_swept: {marker}**", TODAY)
    assert when == datetime.date.fromisoformat(marker)
    assert age == expected


# ---------------------------------------------------------------------------
# IN-PROCESS TESTS. The subprocess tests above pin the CLI contract — exit codes
# are the interface CI and the pre-push hook consume, and a test that never runs
# the real entry point does not prove them. But a subprocess executes in its own
# interpreter and records NO coverage in this one, so those tests alone left the
# script at 31% and the per-file floor blocked the push. Both layers are needed:
# subprocess for the contract, in-process for the lines.
# ---------------------------------------------------------------------------


def _call_main(monkeypatch, capsys, root, *extra):
    m = _mod()
    monkeypatch.setattr(
        sys, "argv",
        ["check_promise_registry_swept.py", "--root", str(root), "--today", "2026-08-23", *extra],
    )
    rc = m.main()
    return rc, capsys.readouterr().out


def test_main_in_process_recent(tmp_path, monkeypatch, capsys):
    rc, out = _call_main(monkeypatch, capsys, _repo(tmp_path, "2026-08-01"))
    assert rc == 0
    assert "ok — last swept" in out


def test_main_in_process_stale(tmp_path, monkeypatch, capsys):
    rc, out = _call_main(monkeypatch, capsys, _repo(tmp_path, "2020-01-01"))
    assert rc == 0, "advisory by default"
    assert "STALE" in out
    rc, _ = _call_main(monkeypatch, capsys, _repo(tmp_path, "2020-01-01"), "--strict")
    assert rc == 1


def test_main_in_process_missing_marker(tmp_path, monkeypatch, capsys):
    rc, out = _call_main(monkeypatch, capsys, _repo(tmp_path, None))
    assert rc == 0
    assert "MISSING" in out
    rc, _ = _call_main(monkeypatch, capsys, _repo(tmp_path, None), "--strict")
    assert rc == 1


def test_main_in_process_future(tmp_path, monkeypatch, capsys):
    rc, out = _call_main(monkeypatch, capsys, _repo(tmp_path, "2999-01-01"))
    assert rc == 0
    assert "FUTURE" in out


def test_main_in_process_precondition(tmp_path, monkeypatch, capsys):
    rc, out = _call_main(monkeypatch, capsys, tmp_path)
    assert rc == 2, "a missing spec is a precondition failure, never a pass"
    assert "PRECONDITION UNMET" in out


def test_main_uses_the_real_clock_when_today_is_absent(tmp_path, monkeypatch, capsys):
    """The --today path is for tests; the default path is what ships."""
    m = _mod()
    monkeypatch.setattr(sys, "argv",
                        ["x", "--root", str(_repo(tmp_path, "2026-08-01")), "--max-age-days", "1"])
    rc = m.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "STALE" in out, "a 2026-08-01 sweep is stale against any later real clock"


def test_find_spec_prefers_the_plugin_path(tmp_path):
    m = _mod()
    (tmp_path / "engine").mkdir()
    (tmp_path / "engine" / "consistency-check-spec.md").write_text("x")
    assert m.find_spec(tmp_path).name == "consistency-check-spec.md"
    assert m.find_spec(tmp_path / "nope") is None


def test_sweep_age_returns_none_on_a_malformed_date():
    m = _mod()
    assert m.sweep_age("**last_swept: 2026-13-45**", TODAY) == (None, None)
    assert m.sweep_age("no marker here", TODAY) == (None, None)
