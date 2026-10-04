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

import pytest

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
FOURRISKS = "11 solution leaf/leaves passed a decision with no risk evaluation. See /devils-advocate. "


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


def test_unclearable_advisory_reports_na_not_a_zero_clear_rate(tmp_path, capsys, monkeypatch):
    """An advisory whose flag is a permanent record must not be scored like a defect.

    `decided-leaves-no-four-risks` can only be cleared by falsifying the record, and
    check_leaf_lifecycle says so in its own output. A 0.00 beside genuinely unactioned
    advisories reads as neglect: the dogfood project's own BVSSH #15 made exactly that
    misreading and retracted it. The contrast is the point — `bvssh-overdue` fires the same
    number of times in this test and DOES get a rate, because it is clearable.
    """
    m = _mod()
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, FOURRISKS + BVSSH, "s1", "2026-09-01", monkeypatch)
    _settle(tmp_path, capsys, FOURRISKS + BVSSH, "s2", "2026-09-02", monkeypatch)
    m.main(["report", "--project-dir", str(tmp_path)])
    rep = capsys.readouterr().out
    assert "decided-leaves-no-four-risks | 2 | 0 | 1 | n/a |" in rep
    assert "decided-leaves-no-four-risks | 2 | 0 | 1 | 0.00 |" not in rep
    assert "bvssh-overdue | 2 | 0 | 1 | 0.00 |" in rep
    assert "clear_rate n/a: decided-leaves-no-four-risks" in rep
    assert "not to backfill" in rep


def test_membership_in_unclearable_is_narrow(tmp_path, capsys, monkeypatch):
    """open-human-tasks is a deliberate non-member and the test pins that.

    It can never reach zero in a working project, so its rate is arguably as meaningless —
    but no check tells anyone not to clear it, and admitting it on that reasoning is the
    judgement the rule excludes. If someone adds it, this fails and they must say why.
    """
    m = _mod()
    assert frozenset({"decided-leaves-no-four-risks"}) == m.UNCLEARABLE
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, TASKS, "s1", "2026-09-01", monkeypatch)
    _settle(tmp_path, capsys, TASKS, "s2", "2026-09-02", monkeypatch)
    m.main(["report", "--project-dir", str(tmp_path)])
    rep = capsys.readouterr().out
    assert "open-human-tasks | 2 | 0 | 1 | 0.00 |" in rep
    assert "clear_rate n/a" not in rep


def test_rule_validation(tmp_path, capsys):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    assert m.main(["rule", "--project-dir", str(tmp_path)]) == 2
    # A refused ruling exits 2 (v0.280.0); it exited 0, so a caller read it as recorded.
    assert m.main(["rule", "--project-dir", str(tmp_path), "--id", "x", "--ruling", "maybe"]) == 2
    assert "must be one of" in capsys.readouterr().out


@pytest.mark.parametrize("aid", ["start-l3:l3-a", "deliver-l3:l3-a",
                                 "delivery-over-l3:l3-a:2026-11-03"])
def test_an_item_only_its_doing_answers_cannot_wait_until_asked(tmp_path, capsys, aid):
    """v0.280.0, E2E service world run 7: the pilot's start item was snoozed until month-end data
    that exists only once the pilot starts, and nothing ever asked."""
    m = _mod()
    (tmp_path / ".claude").mkdir()
    base = ["rule", "--project-dir", str(tmp_path), "--id", aid, "--ruling", "snooze"]
    assert m.main([*base, "--until", "asked", "--note", "when the data lands"]) == 2
    assert "cannot be snoozed until asked" in capsys.readouterr().out
    assert not (tmp_path / ".claude" / "state" / "advisory-ledger.jsonl").exists()
    assert m.main([*base, "--until", "2026-12-01"]) == 0, "a dated snooze is still allowed"


def test_control_other_items_still_wait_until_asked(tmp_path, capsys):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    assert m.main(["rule", "--project-dir", str(tmp_path), "--id", "door-l4:l3-a",
                   "--ruling", "snooze", "--until", "asked"]) == 0


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


def test_ruling_snooze_silences_until_date_then_returns(tmp_path, capsys, monkeypatch):
    m = _mod()
    (tmp_path / ".claude").mkdir()
    _settle(tmp_path, capsys, BVSSH + TASKS, "s1", "2026-09-01", monkeypatch)
    assert (
        m.main(
            ["rule", "--project-dir", str(tmp_path), "--id", "bvssh-overdue", "--ruling", "snooze"]
        )
        == 2
    )
    assert "needs --until" in capsys.readouterr().out
    m.main(
        [
            "rule",
            "--project-dir",
            str(tmp_path),
            "--id",
            "bvssh-overdue",
            "--ruling",
            "snooze",
            "--until",
            "2026-09-05",
            "--today",
            "2026-09-02",
        ]
    )
    assert "ruled snooze until 2026-09-05" in capsys.readouterr().out
    rc, out = _settle(tmp_path, capsys, BVSSH + TASKS, "s2", "2026-09-03", monkeypatch)
    assert "days overdue" not in out and "OPEN human task" in out
    rc, out = _settle(tmp_path, capsys, BVSSH + TASKS, "s3", "2026-09-06", monkeypatch)
    assert "days overdue" in out
    m.main(["report", "--project-dir", str(tmp_path)])
    assert "snoozed until 2026-09-05" in capsys.readouterr().out


# ---- v0.312.0: a muted or ruled advisory speaks again when its count rises ----------------------
# Dogfood 2026-10-03: decided-leaves-no-four-risks was dropped at 12 as unclearable, and a 13th leaf
# decided with no risk evaluation would have been announced to nobody.


def _tasks(n):
    return f"You have {n} OPEN human task(s) (0 closed/parked, not counted). If you completed offline work, run /log-evidence. "


def _rule(tmp_path, capsys, aid, ruling, today="2026-09-20"):
    rc = _mod().main(["rule", "--project-dir", str(tmp_path), "--id", aid, "--ruling", ruling,
                      "--note", "test", "--today", today])
    capsys.readouterr()
    return rc


def test_muted_advisory_speaks_once_when_its_count_rises(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch, text=_tasks(10))
    rc, out = _settle(tmp_path, capsys, _tasks(11), "s-rise", "2026-09-20", monkeypatch)
    assert "ADVISORY open-human-tasks ROSE from 10 to 11 since it was muted" in out
    assert "You have 11 OPEN human task" in out  # the advisory's own text is shown, not a stub
    assert any(e["kind"] == "rebaselined" and e["count"] == 11 for e in _events(tmp_path))
    rc, out = _settle(tmp_path, capsys, _tasks(11), "s-same", "2026-09-21", monkeypatch)
    assert "ROSE" not in out and "MUTED ADVISORY open-human-tasks" in out


def test_dropped_advisory_speaks_when_its_count_rises_and_not_before(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch, text=_tasks(10))
    assert _rule(tmp_path, capsys, "open-human-tasks", "drop") == 0
    rc, out = _settle(tmp_path, capsys, _tasks(10), "s-a", "2026-09-21", monkeypatch)
    assert "OPEN human task" not in out and "ROSE" not in out
    rc, out = _settle(tmp_path, capsys, _tasks(12), "s-b", "2026-09-22", monkeypatch)
    assert "ROSE from 10 to 12 since it was ruled drop on 2026-09-20" in out


def test_a_fall_lowers_the_baseline_so_a_later_rise_is_seen(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch, text=_tasks(10))
    _rule(tmp_path, capsys, "open-human-tasks", "drop")
    _settle(tmp_path, capsys, _tasks(6), "s-fall", "2026-09-21", monkeypatch)
    rc, out = _settle(tmp_path, capsys, _tasks(8), "s-up", "2026-09-22", monkeypatch)
    assert "ROSE from 6 to 8" in out


def test_ruling_keep_clears_the_baseline(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch, text=_tasks(10))
    _rule(tmp_path, capsys, "open-human-tasks", "keep")
    rc, out = _settle(tmp_path, capsys, _tasks(12), "s-k", "2026-09-21", monkeypatch)
    assert "ROSE" not in out and "You have 12 OPEN human task" in out


def test_unclearable_advisory_mutes_without_asking_for_a_ruling(tmp_path, capsys, monkeypatch):
    (tmp_path / ".claude").mkdir()
    _mute(tmp_path, capsys, monkeypatch, text=FOURRISKS)
    rc, out = _settle(tmp_path, capsys, FOURRISKS, "s-u", "2026-09-20", monkeypatch)
    assert "MUTED ADVISORY decided-leaves-no-four-risks" in out
    assert "needs no ruling" in out and "--ruling" not in out
