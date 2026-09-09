"""Coverage tests for check_idle_opportunities.py — an open node that nothing reads is IDLE.

Branches: no canvas -> N/A rc 0 (speaks); TASK reader; TEST reader (assumption without verdict and a
named test; riskiest_assumption.cheapest_test); DECLARED reader (what_would_move_it); IDLE with age and
recent-writes flag; terminal leaf does not count as a test; closed task does not count as a reader;
--strict exits 1; --verbose prints every row; bad --today; unparseable file speaks. Runs the module
in-process so the per-file coverage floor sees it.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import check_idle_opportunities
    return check_idle_opportunities


def _run(root, capsys, *extra):
    rc = _mod().main(["--project-dir", str(root), "--today", "2026-09-09", *extra])
    return rc, capsys.readouterr().out


def _canvas(root, opps_yaml, tasks_yaml=None):
    c = root / ".claude" / "canvas"
    c.mkdir(parents=True, exist_ok=True)
    (c / "opportunities.yml").write_text(opps_yaml)
    if tasks_yaml is not None:
        (c / "human-tasks.yml").write_text(tasks_yaml)
    return c


def test_no_canvas_is_na_and_speaks(tmp_path, capsys):
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "N/A" in out


def test_open_task_naming_the_node_is_a_reader(tmp_path, capsys):
    _canvas(tmp_path, "opportunities:\n- id: opp-001\n  status: open\n  name: n\n",
            "pending_tasks:\n- id: ht-001\n  status: waiting\n  objective: 'about opp-001'\n")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 0 and "0 IDLE" in out


def test_closed_task_is_not_a_reader(tmp_path, capsys):
    _canvas(tmp_path, "opportunities:\n- id: opp-001\n  status: open\n  name: n\n",
            "completed_tasks:\n- id: ht-001\n  status: completed\n  objective: 'about opp-001'\n")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 1 and "opp-001" in out and "IDLE" in out


def test_leaf_assumption_with_named_test_is_a_reader(tmp_path, capsys):
    _canvas(tmp_path, """opportunities:
- id: opp-002
  status: open
  solutions:
  - id: sol-002a
    status: candidate
    assumptions:
    - id: a-1
      statement: s
      verdict: null
      test_2026_09_09: 'a retrodiction on data on disk, run blind'
""")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 0


def test_riskiest_assumption_cheapest_test_is_a_reader(tmp_path, capsys):
    _canvas(tmp_path, """opportunities:
- id: opp-003
  status: open
  solutions:
  - id: sol-003a
    status: candidate
    riskiest_assumption:
      statement: s
      cheapest_test: 'count the canvases on record whose who names a team; fewer than two, wait'
""")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 0


def test_terminal_leaf_test_does_not_count(tmp_path, capsys):
    _canvas(tmp_path, """opportunities:
- id: opp-004
  status: open
  solutions:
  - id: sol-004a
    status: ARCHIVED-2026-09-01
    riskiest_assumption:
      statement: s
      cheapest_test: 'this test will never run because the leaf is archived already'
""")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 1 and "opp-004" in out


def test_declared_reader_counts(tmp_path, capsys):
    _canvas(tmp_path, "opportunities:\n- id: opp-005\n  status: open\n  what_would_move_it: 'ht-107 close 2026-10-02'\n")
    rc, out = _run(tmp_path, capsys, "--strict")
    assert rc == 0


def test_idle_reports_age_and_recent_flag_and_warn_exit_zero(tmp_path, capsys):
    _canvas(tmp_path, """opportunities:
- id: opp-006
  status: open
  evidence:
  - 'written 2026-09-01, one voice'
- id: opp-007
  status: open
  evidence:
  - 'written 2026-05-01'
- id: opp-008
  status: closed
""")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "2 IDLE" in out and "WARN" in out
    assert "opp-006" in out and "recent-writes" in out and "8d" in out
    assert "131d" in out and "opp-008" not in out


def test_verbose_prints_readers_per_row(tmp_path, capsys):
    _canvas(tmp_path, "opportunities:\n- id: opp-009\n  status: open\n  what_would_move_it: 'x'\n")
    rc, out = _run(tmp_path, capsys, "--verbose")
    assert rc == 0 and "readers=declared" in out


def test_bad_today_is_usage_error(tmp_path, capsys):
    _canvas(tmp_path, "opportunities: []\n")
    rc = _mod().main(["--project-dir", str(tmp_path), "--today", "not-a-date"])
    assert rc == 2


def test_unparseable_file_speaks(tmp_path, capsys):
    _canvas(tmp_path, "opportunities: [\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "cannot parse" in out
