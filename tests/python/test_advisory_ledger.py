"""Coverage tests for advisory_ledger.py — every advisory counts whether anything follows.

Branches: first session records seen; same text next session -> still_firing; absent -> cleared; count
drop -> cleared; age rise is not a count -> still_firing; same session twice not settled; mute after
MUTE_DAYS distinct days replaces the segment with one line; ruling keep unmutes; ruling fix stays muted
until it clears; ruling drop removes silently and reports as dropped; unreadable ledger line speaks and
is skipped; no .claude dir passes text through; report N/A; report table; rule validation. Runs the
module in-process so the per-file coverage floor sees it.
"""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import advisory_ledger

    return advisory_ledger


def _settle(root, capsys, text, session, today, monkeypatch):
    monkeypatch.setattr("sys.stdin", _Stdin(text))
    rc = _mod().main(["settle", "--project-dir", str(root), "--session", session, "--today", today])
    return rc, capsys.readouterr().out


class _Stdin:
    def __init__(self, s):
        self._s = s

    def read(self):
        return self._s


def _events(root):
    p = root / ".claude" / "state" / "advisory-ledger.jsonl"
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # the corrupt-line test plants one on purpose
    return out


BVSSH = "BVSSH health check is 32 days overdue (monthly cadence). Run /bvssh-check. "
TASKS = "You have 26 OPEN human task(s) (0 closed/parked, not counted). If you completed offline work, run /log-evidence. "
CLUSTER = "27 correction(s) logged since the last cluster instance — the corrections-to-cluster hop is unconsidered. "


def test_first_session_records_seen(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    rc, out = _settle(tmp_path, capsys, BVSSH + TASKS, "s1", "2026-09-01", monkeypatch)
    assert rc == 0 and out == BVSSH + TASKS
    ev = _events(tmp_path)
    assert [e["kind"] for e in ev] == ["seen"]
    assert ev[0]["ids"] == {"bvssh-overdue": None, "open-human-tasks": 26}


def test_next_session_settles_still_firing_and_cleared(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, BVSSH + TASKS + CLUSTER, "s1", "2026-09-01", monkeypatch)
    # bvssh still there (age rose, not a count), tasks dropped 26->20 (cleared), cluster gone (cleared)
    text2 = BVSSH.replace("32", "33") + TASKS.replace("26", "20")
    _settle(tmp_path, capsys, text2, "s2", "2026-09-02", monkeypatch)
    settled = next(e for e in _events(tmp_path) if e["kind"] == "settled")
    assert settled["results"] == {
        "bvssh-overdue": "still_firing",
        "open-human-tasks": "cleared",
        "corrections-to-cluster": "cleared",
    }


def test_count_rise_is_still_firing(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, TASKS, "s1", "2026-09-01", monkeypatch)
    _settle(tmp_path, capsys, TASKS.replace("26", "30"), "s2", "2026-09-02", monkeypatch)
    settled = next(e for e in _events(tmp_path) if e["kind"] == "settled")
    assert settled["results"] == {"open-human-tasks": "still_firing"}


def test_same_session_twice_is_not_settled_against_itself(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, BVSSH, "s1", "2026-09-01", monkeypatch)
    rc, out = _settle(tmp_path, capsys, BVSSH, "s1", "2026-09-01", monkeypatch)
    assert "same session seen twice" in out
    assert not [e for e in _events(tmp_path) if e["kind"] == "settled"]


def test_mute_after_threshold_days_replaces_segment(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    text = BVSSH + TASKS
    for i in range(1, m.MUTE_DAYS):
        rc, out = _settle(tmp_path, capsys, text, f"s{i}", f"2026-09-{i:02d}", monkeypatch)
        assert "MUTED ADVISORY" not in out
    rc, out = _settle(tmp_path, capsys, text, "s-last", f"2026-09-{m.MUTE_DAYS:02d}", monkeypatch)
    assert "MUTED ADVISORY bvssh-overdue" in out and "MUTED ADVISORY open-human-tasks" in out
    assert "days overdue" not in out and "OPEN human task" not in out
    assert any(e["kind"] == "muted" and e["id"] == "bvssh-overdue" for e in _events(tmp_path))


def test_two_sessions_one_day_do_not_advance_the_streak(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    for i in range(1, m.MUTE_DAYS * 2):
        _settle(tmp_path, capsys, BVSSH, f"s{i}", "2026-09-01", monkeypatch)
    rc, out = _settle(tmp_path, capsys, BVSSH, "s-x", "2026-09-01", monkeypatch)
    assert "MUTED ADVISORY" not in out


def _mute(tmp_path, capsys, monkeypatch, text=BVSSH):
    m = _mod()
    for i in range(1, m.MUTE_DAYS + 1):
        _settle(tmp_path, capsys, text, f"s{i}", f"2026-09-{i:02d}", monkeypatch)


def test_ruling_keep_unmutes_and_resets_streak(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch)
    rc = m.main(
        [
            "rule",
            "--project-dir",
            str(tmp_path),
            "--id",
            "bvssh-overdue",
            "--ruling",
            "keep",
            "--today",
            "2026-09-08",
            "--note",
            "monthly by design",
        ]
    )
    assert rc == 0 and "ruled keep" in capsys.readouterr().out
    rc, out = _settle(tmp_path, capsys, BVSSH, "s-after", "2026-09-09", monkeypatch)
    assert "MUTED ADVISORY" not in out and "days overdue" in out


def test_ruling_fix_stays_muted_until_it_clears(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch)
    m.main(
        [
            "rule",
            "--project-dir",
            str(tmp_path),
            "--id",
            "bvssh-overdue",
            "--ruling",
            "fix",
            "--today",
            "2026-09-08",
        ]
    )
    capsys.readouterr()
    rc, out = _settle(tmp_path, capsys, BVSSH, "s-a", "2026-09-09", monkeypatch)
    assert "MUTED ADVISORY bvssh-overdue" in out
    _settle(tmp_path, capsys, TASKS, "s-b", "2026-09-10", monkeypatch)  # cleared
    rc, out = _settle(tmp_path, capsys, BVSSH, "s-c", "2026-09-11", monkeypatch)
    assert "MUTED ADVISORY" not in out and "days overdue" in out


def test_ruling_drop_removes_silently_and_report_shows_it(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, BVSSH + TASKS, "s1", "2026-09-01", monkeypatch)
    m.main(
        [
            "rule",
            "--project-dir",
            str(tmp_path),
            "--id",
            "bvssh-overdue",
            "--ruling",
            "drop",
            "--today",
            "2026-09-02",
        ]
    )
    capsys.readouterr()
    rc, out = _settle(tmp_path, capsys, BVSSH + TASKS, "s2", "2026-09-03", monkeypatch)
    assert "days overdue" not in out and "MUTED" not in out and "OPEN human task" in out
    m.main(["report", "--project-dir", str(tmp_path)])
    rep = capsys.readouterr().out
    assert "bvssh-overdue |" in rep and "| drop" in rep


def test_unreadable_ledger_line_speaks_and_is_skipped(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    p = tmp_path / ".claude" / "state" / "advisory-ledger.jsonl"
    p.write_text(
        '{"kind":"seen","session":"s0","date":"2026-08-30","ids":{"bvssh-overdue":null}}\n{not json\n'
    )
    rc, out = _settle(tmp_path, capsys, BVSSH, "s1", "2026-09-01", monkeypatch)
    assert rc == 0 and out.startswith(BVSSH) and "advisory ledger: line 2" in out
    settled = [e for e in _events(tmp_path) if e["kind"] == "settled"]
    assert settled and settled[0]["results"] == {"bvssh-overdue": "still_firing"}


def test_no_claude_dir_passes_text_through(tmp_path, capsys, monkeypatch):
    rc, out = _settle(tmp_path, capsys, BVSSH, "s1", "2026-09-01", monkeypatch)
    assert rc == 0 and out.startswith(BVSSH) and "N/A" in out
    assert not (tmp_path / ".claude").exists()


def test_report_na_then_table(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    m.main(["report", "--project-dir", str(tmp_path)])
    assert "N/A" in capsys.readouterr().out
    _settle(tmp_path, capsys, BVSSH + CLUSTER, "s1", "2026-09-01", monkeypatch)
    _settle(tmp_path, capsys, BVSSH, "s2", "2026-09-02", monkeypatch)
    m.main(["report", "--project-dir", str(tmp_path)])
    rep = capsys.readouterr().out
    assert "2 session(s) recorded" in rep
    assert "corrections-to-cluster | 1 | 1 | 0 | 1.00 | 0" in rep
    assert "bvssh-overdue | 2 | 0 | 1 | 0.00 | 2" in rep


def test_rule_validation(tmp_path, capsys):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    assert m.main(["rule", "--project-dir", str(tmp_path)]) == 2
    assert m.main(["rule", "--project-dir", str(tmp_path), "--id", "x", "--ruling", "maybe"]) == 0
    assert "must be one of" in capsys.readouterr().out


def test_unregistered_text_is_left_with_the_segment_before_it(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    text = BVSSH + "SOMETHING NEW nobody registered. " + TASKS
    _mute(tmp_path, capsys, monkeypatch, text)
    rc, out = _settle(tmp_path, capsys, text, "s-z", "2026-09-20", monkeypatch)
    # bvssh segment (which carries the unregistered sentence) is replaced; the unregistered text goes with it
    assert "MUTED ADVISORY bvssh-overdue" in out and "MUTED ADVISORY open-human-tasks" in out


def test_settle_crash_passes_text_through_and_speaks(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    monkeypatch.setattr(m, "settle", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    rc, out = _settle(tmp_path, capsys, BVSSH, "s1", "2026-09-01", monkeypatch)
    assert rc == 0 and out.startswith(BVSSH) and "could not run (RuntimeError: boom)" in out
