"""Coverage tests for review_schedule.py — scheduled reviews past their cadence (v0.329.0).

Branches: nothing due without diamonds; a day cadence due and not due from a recorded run; never run,
judged against the oldest diamond; a run read from dated file names; applies_if absent; a review another
check reports; a corrections cadence counted from corrections.md; --record (writes, refuses an unknown
id); --list; an unreadable schedule or run record is said, never read as nothing due. Wiring: every
review the shipped schedule marks `stamp` has its --record call in its skill; the advisory ledger and the
next item read the line the script prints; and the real session-start hook carries it. In-process for
the coverage floor.
"""

import io
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
TODAY = "2026-10-23"

SCHEDULE = {
    "schema_version": 1,
    "reviews": [
        {"id": "monthly", "skill": "/x:monthly", "cadence": {"days": 30}, "last_run": {"stamp": True}},
        {"id": "weekly-files", "skill": "/x:weekly", "cadence": {"days": 7},
         "last_run": {"files": ".claude/evals/metrics/*.md"}, "applies_if": ".claude/jit"},
        {"id": "count", "skill": "/x:count", "cadence": {"corrections": 3},
         "last_run": {"files": ".claude/evals/metrics/corrections/*.json"}},
        {"id": "elsewhere", "skill": "/x:other", "cadence": {"days": 30}, "checked_by": "CHECK 1"},
    ],
}


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import review_schedule

    return review_schedule


def _project(tmp_path: Path, born: str | None = "2026-01-01") -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    diamonds = [{"id": "l0", "scale": "L0", "created_at": born}] if born else []
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": diamonds}), encoding="utf-8")
    sched = tmp_path / "schedule.yml"
    sched.write_text(yaml.safe_dump(SCHEDULE), encoding="utf-8")
    return tmp_path


def _run(root: Path, *args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = _mod().main(["--project-dir", str(root), "--today", TODAY,
                            "--schedule", str(root / "schedule.yml"), *args])
    return code, buf.getvalue()


def _rows(root: Path) -> dict[str, str]:
    _, out = _run(root, "--list")
    return {line.split()[0]: line for line in out.splitlines() if line.strip()}


def test_no_diamonds_means_nothing_due(tmp_path):
    root = _project(tmp_path, born=None)
    code, out = _run(root, "--check")
    assert code == 0 and out.startswith("OK:")
    assert "no diamonds yet" in _rows(root)["monthly"]


def test_never_run_is_due_once_the_oldest_diamond_passes_the_cadence(tmp_path):
    code, out = _run(_project(tmp_path), "--check")
    assert code == 0
    assert out.startswith("SCHEDULED REVIEWS DUE — ")
    assert "monthly (every 30 days; no run on record" in out


def test_never_run_on_a_young_project_is_not_due(tmp_path):
    root = _project(tmp_path, born="2026-10-10")
    assert "monthly" not in _run(root, "--check")[1].split("cadence:")[-1].split(";")[0]
    assert " ok " in _rows(root)["monthly"]


def test_a_recorded_run_inside_the_cadence_is_ok_and_outside_is_due(tmp_path):
    root = _project(tmp_path)
    assert _run(root, "--record", "monthly", "--date", "2026-10-01")[0] == 0
    assert " ok " in _rows(root)["monthly"]
    (root / ".claude/harness/review-runs.jsonl").write_text(
        json.dumps({"review": "monthly", "date": "2026-08-01"}) + "\n", encoding="utf-8")
    assert "last run 2026-08-01, 83 days ago" in _rows(root)["monthly"]
    assert "monthly (every 30 days; last run 2026-08-01" in _run(root, "--check")[1]


def test_record_refuses_an_id_the_schedule_does_not_name(tmp_path):
    root = _project(tmp_path)
    assert _run(root, "--record", "no-such-review")[0] == 1
    assert not (root / ".claude/harness/review-runs.jsonl").exists()


def test_a_run_is_read_from_dated_file_names_and_applies_if_gates_the_review(tmp_path):
    root = _project(tmp_path)
    assert "does not apply" in _rows(root)["weekly-files"]
    (root / ".claude/jit").mkdir(parents=True)
    (root / ".claude/evals/metrics").mkdir(parents=True)
    (root / ".claude/evals/metrics/2026-10-20.md").write_text("x", encoding="utf-8")
    (root / ".claude/evals/metrics/notes.md").write_text("x", encoding="utf-8")
    assert "last run 2026-10-20, 3 days ago" in _rows(root)["weekly-files"]


def test_a_review_another_check_reports_is_listed_and_never_reported_twice(tmp_path):
    root = _project(tmp_path)
    assert "elsewhere" in _rows(root)["elsewhere"]
    assert "elsewhere (" not in _run(root, "--check")[1]


def test_a_corrections_cadence_counts_corrections_since_the_last_run(tmp_path):
    root = _project(tmp_path)
    (root / ".claude/memory").mkdir(parents=True)
    heads = ["## 2026-10-01: old", "## 2026-10-21: a", "## 2026-10-22: b", "### 2026-10-22: not a head"]
    (root / ".claude/memory/corrections.md").write_text("\n".join(heads), encoding="utf-8")
    (root / ".claude/evals/metrics/corrections").mkdir(parents=True)
    (root / ".claude/evals/metrics/corrections/2026-10-20.json").write_text("{}", encoding="utf-8")
    assert "2 correction(s) logged since 2026-10-20" in _rows(root)["count"]
    assert " ok " in _rows(root)["count"]
    (root / ".claude/memory/corrections.md").write_text("\n".join([*heads, "## 2026-10-23: c"]),
                                                        encoding="utf-8")
    assert "count (every 3 corrections; 3 correction(s) logged since 2026-10-20)" in _run(root)[1]


def test_an_unreadable_schedule_or_run_record_is_said_not_passed(tmp_path):
    root = _project(tmp_path)
    (root / ".claude/harness").mkdir(parents=True)
    (root / ".claude/harness/review-runs.jsonl").write_text("not json\n", encoding="utf-8")
    code, out = _run(root, "--check")
    assert code == 0 and out.startswith("UNREADABLE (review schedule did NOT run)")
    (root / "schedule.yml").write_text("reviews: []\n", encoding="utf-8")
    code, out = _run(root, "--check")
    assert code == 0 and "no `reviews` list" in out


def test_every_stamp_review_in_the_shipped_schedule_records_itself_in_its_skill():
    doc = yaml.safe_load((PLUGIN / "engine" / "review-schedule.yml").read_text(encoding="utf-8"))
    stamped = [r for r in doc["reviews"] if (r.get("last_run") or {}).get("stamp")]
    assert stamped, "the shipped schedule has no stamp review; this test would pass on nothing"
    for r in stamped:
        skill = PLUGIN / "skills" / r["skill"].split(":", 1)[1] / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        assert f"review_schedule.py\" --record {r['id']}" in text, f"{skill} never records {r['id']}"


def test_every_scheduled_skill_exists():
    doc = yaml.safe_load((PLUGIN / "engine" / "review-schedule.yml").read_text(encoding="utf-8"))
    for r in doc["reviews"]:
        assert (PLUGIN / "skills" / r["skill"].split(":", 1)[1] / "SKILL.md").is_file(), r["skill"]


def test_the_ledger_and_the_next_item_read_the_line_the_script_prints(tmp_path):
    _, out = _run(_project(tmp_path), "--check")
    import advisory_ledger
    import next_item

    hits = [(i, m) for i, p in advisory_ledger.SIGNATURES if (m := re.search(p, out))]
    assert [i for i, _ in hits] == ["reviews-overdue"]
    assert hits[0][1].group("count") == str(out.count(" (every "))
    assert next_item.COMMANDS["reviews-overdue"][1] == "/mycelium:feedback-review"


def test_the_session_start_hook_carries_the_line(tmp_path):
    root = _project(tmp_path)
    (root / ".claude/canvas").mkdir(parents=True)
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_PROJECT_DIR": str(root),
           "MYCELIUM_CROSS_REPO_WATCH": ""}
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup", "session_id": "t1"})
    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "session-start.sh")], input=payload,
                          capture_output=True, text=True, env=env, timeout=180, check=False)
    assert done.returncode == 0, done.stderr
    assert "SCHEDULED REVIEWS DUE" in done.stdout


def test_an_unreadable_diamonds_file_is_said_not_read_as_no_diamonds(tmp_path):
    """Read as "no diamonds", it would say nothing is due when the check could not look."""
    root = _project(tmp_path)
    (root / ".claude/diamonds/active.yml").write_text("active_diamonds: [\n", encoding="utf-8")
    code, out = _run(root, "--check")
    assert code == 0 and out.startswith("UNREADABLE (review schedule did NOT run)")
    assert "active.yml" in out
    (root / ".claude/diamonds/active.yml").unlink()
    assert _run(root, "--check")[1].startswith("OK:"), "control: no diamonds file is nothing due"


def test_a_run_record_line_without_a_valid_date_is_said_not_skipped(tmp_path):
    root = _project(tmp_path)
    (root / ".claude/harness").mkdir(parents=True)
    (root / ".claude/harness/review-runs.jsonl").write_text(
        json.dumps({"review": "monthly", "date": "2026-13-45"}) + "\n", encoding="utf-8")
    code, out = _run(root, "--check")
    assert code == 0 and "no review id or no valid date" in out
