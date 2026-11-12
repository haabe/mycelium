"""check_record_size.py — canonical records past what one Read returns, with their growth.

Founder ruling 2026-11-12, "Size warning only": canvas-health and session start name the record
files past the threshold, with size and growth; nothing moves. In-process for the coverage floor.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import advisory_ledger  # noqa: E402
import check_record_size as crs  # noqa: E402

BIG = crs.READ_LIMIT_BYTES + 10 * 1024


def _project(tmp_path: Path) -> Path:
    for d in ("canvas", "harness", "memory", "diamonds", "state"):
        (tmp_path / ".claude" / d).mkdir(parents=True)
    return tmp_path


def _git(root: Path, *args: str, when: float | None = None) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"@{int(when)} +0000"
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def test_a_record_past_the_threshold_is_named_with_its_growth(tmp_path, capsys):
    root = _project(tmp_path)
    log = root / ".claude" / "harness" / "decision-log.md"
    log.write_text("x" * (BIG - 100 * 1024))
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "old", when=time.time() - 40 * 86400)
    log.write_text("x" * BIG)
    (root / ".claude" / "canvas" / "human-tasks.yml").write_text("y" * BIG)  # not in that commit
    (root / ".claude" / "canvas" / "purpose.yml").write_text("small: true\n")
    assert crs.main(["--project-dir", str(root)]) == 0
    out = capsys.readouterr().out
    assert "2 of 3 record file(s) past 256 KB" in out and "nothing is moved" in out
    assert ".claude/harness/decision-log.md 266 KB (+100 KB in 30 days)" in out
    assert ".claude/canvas/human-tasks.yml 266 KB (new in the last 30 days)" in out
    assert "purpose.yml" not in out
    assert (root / ".claude" / "canvas" / "human-tasks.yml").stat().st_size == BIG  # untouched


def test_the_advisory_is_silent_when_clean_and_the_ledger_reads_it_when_not(tmp_path, capsys):
    root = _project(tmp_path)
    (root / ".claude" / "memory" / "corrections.md").write_text("small\n")
    assert crs.main(["--project-dir", str(root), "--advisory"]) == 0
    assert capsys.readouterr().out == ""
    assert crs.main(["--project-dir", str(root)]) == 0
    assert "OK, none of 1 record file(s)" in capsys.readouterr().out
    (root / ".claude" / "memory" / "corrections.md").write_text("z" * BIG)
    assert crs.main(["--project-dir", str(root), "--advisory"]) == 0
    line = capsys.readouterr().out
    assert line.startswith("RECORDS PAST ONE READ: 1 record file(s)")
    assert "growth unknown: git has no commit that old" in line  # not a repository
    assert advisory_ledger.scan(line) == {"records-past-one-read": 1}


def test_the_session_start_line_names_the_largest_and_counts_the_rest(tmp_path):
    root = _project(tmp_path)
    for i in range(crs.ADVISORY_SHOWN + 2):
        (root / ".claude" / "canvas" / f"f{i}.yml").write_text("a" * (BIG + i * 2048))
    line = crs.advisory(crs.past_limit(root, 30))
    assert f"{crs.ADVISORY_SHOWN + 2} record file(s)" in line and "and 2 more" in line
    assert line.index("f6.yml") < line.index("f5.yml")  # largest first
    assert "f0.yml" not in line


def test_state_logs_and_files_outside_the_records_are_not_counted(tmp_path, capsys):
    root = _project(tmp_path)
    (root / ".claude" / "state" / "read-log.jsonl").write_text("s" * BIG)  # pruned elsewhere
    (root / "big.md").write_text("s" * BIG)
    assert crs.main(["--project-dir", str(root), "--advisory"]) == 0
    assert capsys.readouterr().out == ""


def test_no_claude_directory_is_na(tmp_path, capsys):
    assert crs.main(["--project-dir", str(tmp_path)]) == 0
    assert "N/A" in capsys.readouterr().out
    assert crs.main(["--project-dir", str(tmp_path), "--advisory"]) == 0
    assert capsys.readouterr().out == ""


def test_it_runs_on_this_repository(capsys):
    """The lesson on record: a new check runs over the real tree before it ships."""
    assert crs.main(["--project-dir", str(ROOT)]) == 0
    assert capsys.readouterr().out.startswith("record size: ")


def test_session_start_relays_the_line():
    hook = (ROOT / "plugins" / "mycelium" / "hooks" / "session-start.sh").read_text()
    assert "check_record_size.py" in hook and "^RECORDS PAST ONE READ" in hook
