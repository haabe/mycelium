"""Coverage tests for check_evidence_landing.py — every evidence-bearing source lands or is an orphan.

Branches: no canvas -> N/A rc 0 (speaks); LANDED; ORPHAN new vs baselined; CLAIMED_NOT_LANDED;
REVIEWED via ledger; file sources incl. ledger-declared extra dirs; user needs; unparseable file
speaks. Runs the module in-process so the per-file coverage floor sees it.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import check_evidence_landing
    return check_evidence_landing


def _run(root, capsys, *extra):
    rc = _mod().main(["--project-dir", str(root), *extra])
    return rc, capsys.readouterr().out


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


def test_no_canvas_is_na_and_speaks(tmp_path, capsys):
    rc, out = _run(tmp_path, capsys)
    assert rc == 0
    assert "N/A" in out and "nothing was checked" in out


def test_landed_when_reader_cites_task(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK,
            "opportunities:\n- id: opp-001\n  provenance:\n    evidence_sources: ['ht-001 reply']\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "LANDED 1" in out and "ORPHAN 0" in out


def test_new_orphan_fails(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK)
    rc, out = _run(tmp_path, capsys)
    assert rc == 1 and "new orphan" in out and "ht-001" in out


def test_baselined_orphan_passes_and_is_counted(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK)
    rc, out = _run(tmp_path, capsys, "--write-baseline")
    assert "baseline written with 1 orphan" in out
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "1 orphan(s) at adoption, 1 still to land" in out


def test_claimed_not_landed_fails_even_with_no_other_evidence(tmp_path, capsys):
    _canvas(tmp_path, "completed_tasks:\n- id: ht-002\n  evidence_logged_to: opportunities.yml#opp-009\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 1 and "claim a landing that does not cite them back" in out and "ht-002" in out


def test_ledger_reviewed_never_fails(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK)
    h = tmp_path / ".claude" / "harness"
    h.mkdir(parents=True)
    (h / "evidence-landing-ledger.yml").write_text(
        "reviewed:\n- source: ht-001\n  reason: produced nothing citable\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "REVIEWED 1" in out


def test_file_sources_default_and_ledger_dirs(tmp_path, capsys):
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
    rc, out = _run(tmp_path, capsys, "--verbose")
    assert rc == 1
    assert "LANDED 1" in out and "ORPHAN 2" in out
    assert "2026-09-02-test-b" in out and "note-c" in out


def test_user_need_without_opportunity_is_orphan(tmp_path, capsys):
    _canvas(tmp_path, "pending_tasks: []\n", needs_yaml="needs:\n- id: need-001\n  statement: x\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 1 and "need-001" in out


def test_unparseable_file_speaks(tmp_path, capsys):
    _canvas(tmp_path, "pending_tasks: [\n")  # broken YAML
    rc, out = _run(tmp_path, capsys)
    assert "cannot parse" in out and "human-tasks.yml" in out
    assert rc == 0


def test_has_evidence_helper():
    m = _mod()
    assert m.has_evidence({"partial_findings": ["x"]})
    assert m.has_evidence({"reply_from_bob": "yes"})
    assert m.has_evidence({"touch_log": [{"direction": "inbound"}]})
    assert not m.has_evidence({"touch_log": [{"direction": "outbound"}], "objective": "o"})


# --- mutation sample 2026-10-11 (seed 20260910): or/and swaps and an inverted membership ---
# Each predicate below is taken one branch at a time: an entry that is a mapping without an id
# (or a ledger row without a source) is skipped, a needs file written under `user_needs:` is read,
# the listing prints for a new orphan alone, and an orphan that landed since the baseline is
# counted as landed.

def test_entries_without_an_id_or_source_are_skipped_not_crashed_on(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK + "- note: a row with no id\n",
            needs_yaml="needs:\n- statement: no id here\n- id: need-001\n  statement: x\n")
    h = tmp_path / ".claude" / "harness"
    h.mkdir(parents=True)
    (h / "evidence-landing-ledger.yml").write_text(
        "reviewed:\n- reason: a row with no source\n- source: ht-001\n  reason: nothing citable\n")
    rc, out = _run(tmp_path, capsys)
    assert "evidence landing: 2 source(s)" in out
    assert "REVIEWED 1" in out and "need-001" in out and rc == 1


def test_a_needs_file_under_user_needs_is_read(tmp_path, capsys):
    _canvas(tmp_path, "pending_tasks: []\n", needs_yaml="user_needs:\n- id: need-002\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 1 and "ORPHAN 1" in out and "need-002" in out


def test_a_new_orphan_alone_lists_the_rows_and_marks_it_new(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK)
    rc, out = _run(tmp_path, capsys)                 # no --verbose, no claimed source
    assert rc == 1
    assert any(line.startswith("  NEW ORPHAN") and "ht-001" in line for line in out.splitlines())


def test_an_orphan_that_landed_since_the_baseline_is_counted_as_landed(tmp_path, capsys):
    _canvas(tmp_path, ORPHAN_TASK)
    _run(tmp_path, capsys, "--write-baseline")
    _canvas(tmp_path, ORPHAN_TASK,
            "opportunities:\n- id: opp-001\n  provenance:\n    evidence_sources: ['ht-001 reply']\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0 and "1 orphan(s) at adoption, 0 still to land, 1 landed since" in out
