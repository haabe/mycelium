"""check_touch_log_order must BITE on a descending log, and on an empty scan.

An out-of-order touch_log parses cleanly and looks wrong to nobody. Its only
symptom is that touch_log[-1] silently stops meaning "what happened last" —
which is the question the file exists to answer. Both failure directions are
asserted here because the guard has two: wrong order, and nothing scanned.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_touch_log_order

    return check_touch_log_order


DESCENDING = """
pending_tasks:
  - id: ht-001
    touch_log:
      - date: "2026-08-20"
        note: "second"
      - date: "2026-08-10"
        note: "first — but listed last, so [-1] lies"
"""

ASCENDING = DESCENDING.replace("2026-08-20", "2026-08-01").replace("2026-08-10", "2026-08-15")


def _canvas(tmp_path, body):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "human-tasks.yml").write_text(body)
    return tmp_path


def test_descending_touch_log_exits_1(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, DESCENDING)
    rc = mod.main(["--root", str(root)])
    assert rc == 1
    assert "FAIL" in capsys.readouterr().err


def test_ascending_touch_log_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _canvas(tmp_path, ASCENDING)
    assert mod.main(["--root", str(root)]) == 0


def test_zero_files_scanned_is_not_a_pass(scripts_path, tmp_path, capsys):
    """An empty scan is UNKNOWN. Green on nothing is how a broken scan root hides."""
    mod = _import(scripts_path)
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    assert "UNKNOWN" in capsys.readouterr().out
