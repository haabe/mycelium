"""The three fail-open defects found while writing verdicts for all 43 sites.

Each produced a GREEN by not being able to look, which is the one answer that is
never true. These assert the failure direction — a check that cannot distinguish
"clean" from "unreadable" is decoration.
"""
import json
import sys


def _import(scripts_path, name):
    sys.path.insert(0, str(scripts_path))
    return __import__(name)


CORRUPT = "pending_tasks:\n  - id: ht-001\n   bad: [unclosed\n"


def test_unreadable_task_file_is_not_no_reply_owed(scripts_path, tmp_path, capsys):
    """It printed 'OK: no reply owed across 0 task(s)' with status ok."""
    mod = _import(scripts_path, "check_reply_owed")
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "human-tasks.yml").write_text(CORRUPT)
    rc = mod.main(["--project-dir", str(tmp_path), "--json"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unreadable"


def test_a_missing_task_file_still_says_which(scripts_path, tmp_path, capsys):
    """The honest branch that already existed must survive the fix."""
    mod = _import(scripts_path, "check_reply_owed")
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    mod.main(["--project-dir", str(tmp_path), "--json"])
    assert json.loads(capsys.readouterr().out)["status"] == "no_task_file"


def test_a_readable_task_file_still_reports_normally(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path, "check_reply_owed")
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "human-tasks.yml").write_text("pending_tasks: []\n")
    rc = mod.main(["--project-dir", str(tmp_path), "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def _bvssh(tmp_path, log_text, canvas_text):
    (tmp_path / ".claude" / "harness").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "harness" / "decision-log.md").write_text(log_text)
    (tmp_path / ".claude" / "canvas" / "bvssh-health.yml").write_text(canvas_text)
    return tmp_path


def test_an_unparseable_canvas_is_not_a_pile_of_orphans(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path, "check_bvssh_reconcile")
    root = _bvssh(tmp_path, "/bvssh-check 2026-08-01\n", "assessment_history: [unclosed\n")
    rc = mod.main(["--project-dir", str(root)])
    assert rc == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_both_unreadable_is_not_nothing_to_reconcile(scripts_path, tmp_path, capsys):
    """This one exited 0 and printed 'nothing to reconcile'."""
    mod = _import(scripts_path, "check_bvssh_reconcile")
    root = _bvssh(tmp_path, "x\n", "a: [unclosed\n")
    assert mod.main(["--project-dir", str(root)]) == 2


def test_a_malformed_score_by_is_not_reported_as_missing(scripts_path):
    """`score_by: 2026-13-45` was reported as having no scoring date."""
    mod = _import(scripts_path, "check_instrument_contract")
    res = {"due": [], "undated": [], "no_review": [], "review_due": [], "bad_anchor": []}
    out = mod._scoring_date("inst-a", {"score_by": "2026-13-45", "status": "live"}, res)
    assert out is mod._MALFORMED
    assert res["undated"] and "2026-13-45" in res["undated"][0]


def test_an_absent_score_by_is_still_absent(scripts_path):
    mod = _import(scripts_path, "check_instrument_contract")
    res = {"due": [], "undated": [], "no_review": [], "review_due": [], "bad_anchor": []}
    assert mod._scoring_date("inst-a", {"status": "live"}, res) is None
    assert res["undated"] == []
