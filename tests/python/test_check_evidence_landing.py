"""Coverage tests for check_evidence_landing.py — every evidence-bearing source lands or is an orphan.

Branches: no canvas -> N/A rc 0 (speaks); LANDED; ORPHAN new vs baselined; CLAIMED_NOT_LANDED;
REVIEWED via ledger; file sources incl. ledger-declared extra dirs; user needs.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts" / "check_evidence_landing.py"


def _run(root, *extra):
    r = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(root), *extra],
                       capture_output=True, text=True, check=False)
    return r.returncode, r.stdout


def _canvas(root, tasks_yaml, opps_yaml="opportunities: []\n", needs_yaml=None):
    c = root / ".claude" / "canvas"
    c.mkdir(parents=True, exist_ok=True)
    (c / "human-tasks.yml").write_text(tasks_yaml)
    (c / "opportunities.yml").write_text(opps_yaml)
    if needs_yaml is not None:
        (c / "user-needs.yml").write_text(needs_yaml)
    return c


ORPHAN_TASK = """pending_tasks:
- id: ht-001
  touch_log:
  - date: '2026-09-01'
    direction: inbound
    note: 'a reply'
"""


def test_no_canvas_is_na_and_speaks(tmp_path):
    rc, out = _run(tmp_path)
    assert rc == 0
    assert "N/A" in out and "nothing was checked" in out


def test_landed_when_reader_cites_task(tmp_path):
    _canvas(tmp_path, ORPHAN_TASK, "opportunities:\n- id: opp-001\n  provenance:\n    evidence_sources: ['ht-001 reply']\n")
    rc, out = _run(tmp_path)
    assert rc == 0 and "LANDED 1" in out and "ORPHAN 0" in out


def test_new_orphan_fails(tmp_path):
    _canvas(tmp_path, ORPHAN_TASK)
    rc, out = _run(tmp_path)
    assert rc == 1 and "new orphan" in out and "ht-001" in out


def test_baselined_orphan_passes_and_is_counted(tmp_path):
    _canvas(tmp_path, ORPHAN_TASK)
    rc, out = _run(tmp_path, "--write-baseline")
    assert "baseline written with 1 orphan" in out
    rc, out = _run(tmp_path)
    assert rc == 0 and "1 orphan(s) at adoption, 1 still to land" in out


def test_claimed_not_landed_fails_even_with_no_other_evidence(tmp_path):
    _canvas(tmp_path, "completed_tasks:\n- id: ht-002\n  evidence_logged_to: opportunities.yml#opp-009\n")
    rc, out = _run(tmp_path)
    assert rc == 1 and "claim a landing that does not cite them back" in out and "ht-002" in out


def test_ledger_reviewed_never_fails(tmp_path):
    _canvas(tmp_path, ORPHAN_TASK)
    h = tmp_path / ".claude" / "harness"
    h.mkdir(parents=True)
    (h / "evidence-landing-ledger.yml").write_text(
        "reviewed:\n- source: ht-001\n  reason: produced nothing citable\n")
    rc, out = _run(tmp_path)
    assert rc == 0 and "REVIEWED 1" in out


def test_file_sources_default_and_ledger_dirs(tmp_path):
    _canvas(tmp_path, "pending_tasks: []\n",
            "opportunities:\n- id: opp-001\n  note: 'cites 2026-09-01-test-a'\n")
    at = tmp_path / ".claude" / "evals" / "assumption-tests"
    at.mkdir(parents=True)
    (at / "2026-09-01-test-a.md").write_text("# a\n")
    (at / "2026-09-02-test-b.md").write_text("# b\n")
    extra = tmp_path / "friction-log"
    extra.mkdir()
    (extra / "note-c.md").write_text("# c\n")
    h = tmp_path / ".claude" / "harness"
    h.mkdir(parents=True)
    (h / "evidence-landing-ledger.yml").write_text("source_dirs:\n- friction-log\nreviewed: []\n")
    rc, out = _run(tmp_path, "--verbose")
    assert rc == 1
    assert "LANDED 1" in out and "ORPHAN 2" in out
    assert "2026-09-02-test-b" in out and "note-c" in out


def test_user_need_without_opportunity_is_orphan(tmp_path):
    _canvas(tmp_path, "pending_tasks: []\n", needs_yaml="needs:\n- id: need-001\n  statement: x\n")
    rc, out = _run(tmp_path)
    assert rc == 1 and "need-001" in out
