"""In-process coverage for check_reads_due.py: due, recorded, upcoming, terminal tasks skipped,
missing file, unreadable file. Runs in-process for the per-file coverage floor."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import check_reads_due
    return check_reads_due


def _run(root, capsys, today="2026-09-11"):
    rc = _mod().main(["--project-dir", str(root), "--today", today])
    return rc, capsys.readouterr().out


def _tasks(root, text):
    (root / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "canvas" / "human-tasks.yml").write_text(text)


TASKS = """schema_version: 1
pending_tasks:
- id: ht-1
  status: waiting
  created_at: '2026-09-08'
  read_dates:
  - '2026-09-10 (48 h): views, ratio'
  - '2026-09-22 (+14): full read'
- id: ht-2
  status: waiting
  created_at: '2026-09-08'
  read_48h_2026_09_11: done a day late
  read_dates:
  - '2026-09-10 (48 h)'
- id: ht-3
  status: completed
  read_dates:
  - '2026-09-01 (never mind, closed)'
completed_tasks: []
"""


def test_due_read_is_named(tmp_path, capsys):
    _tasks(tmp_path, TASKS)
    rc, out = _run(tmp_path, capsys)
    assert rc == 0
    assert out.startswith("READ DUE on 1 task(s): ht-1 (read dated 2026-09-10: 48 h): views, ratio)")
    assert "ht-2" not in out and "ht-3" not in out


def test_nothing_due_before_the_date(tmp_path, capsys):
    _tasks(tmp_path, TASKS)
    rc, out = _run(tmp_path, capsys, today="2026-09-09")
    assert rc == 0 and out.startswith("OK: no read due across 2 open task(s).")


def test_missing_file_is_ok(tmp_path, capsys):
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "no human-tasks.yml" in out


def test_unreadable_file_speaks(tmp_path, capsys):
    _tasks(tmp_path, "pending_tasks:\n- id: ht-1\n  status: waiting\n  read_dates: [unclosed\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and out.startswith("UNREADABLE")


def test_non_mapping_doc_is_nothing_due(tmp_path, capsys):
    _tasks(tmp_path, "- just a list\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "OK: no read due across 0 open task(s)." in out
