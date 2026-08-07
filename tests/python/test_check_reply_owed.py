"""Coverage proof for check_reply_owed.py — the extracted single implementation.

Fixtures are the real 2026-08-05 / 2026-08-07 shapes. The same-day cases are the
reason this module exists: the rule had two implementations, the same-day fix landed
in the one made of prose, and the executable one kept the bug for two more days.
"""
import datetime
import sys

import pytest

TODAY = datetime.date(2026, 8, 7)


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_reply_owed
    return check_reply_owed


def _task(tid, log, status="pending", **kw):
    return {"id": tid, "status": status, "touch_log": log, **kw}


# ------------------------------------------------------------------ the motivating defect

def test_same_day_reply_is_not_owed(scripts_path):
    """THE REGRESSION TEST. ht-060: inbound and reply on the same date. Day-granular
    dates cannot order two contacts, and the tie used to break toward the inbound, so
    a reply sent the same day scored as unanswered."""
    c = _import(scripts_path)
    t = _task("ht-060", [
        {"date": "2026-08-02", "direction": "inbound", "note": "her reply"},
        {"date": "2026-08-02", "direction": "outbound", "note": "Reply sent, same day."},
    ])
    assert c.owed([t], TODAY) == []


def test_same_day_inbound_after_outbound_is_owed(scripts_path):
    """The reason the tiebreak is POSITION and not DIRECTION. Preferring outbound on a
    tie would silence this — a reply went out and they answered it again the same day,
    which is a real owed reply."""
    c = _import(scripts_path)
    t = _task("ht-x", [
        {"date": "2026-08-02", "direction": "outbound"},
        {"date": "2026-08-02", "direction": "inbound"},
    ])
    assert [f["id"] for f in c.owed([t], TODAY)] == ["ht-x"]


# ------------------------------------------------------------------ the original rule

def test_unanswered_inbound_is_owed(scripts_path):
    c = _import(scripts_path)
    t = _task("ht-a", [{"date": "2026-08-01", "direction": "inbound"}])
    got = c.owed([t], TODAY)
    assert got and got[0]["age_days"] == 6


def test_outbound_last_is_not_owed(scripts_path):
    """Waiting on them is the healthy state and must stay silent."""
    c = _import(scripts_path)
    t = _task("ht-b", [{"date": "2026-08-01", "direction": "outbound"}])
    assert c.owed([t], TODAY) == []


def test_internal_note_does_not_mask_an_inbound(scripts_path):
    """An internal note (a metric reading, a status line) is not contact. Letting one
    sit on top of an inbound is exactly how an owed reply disappears."""
    c = _import(scripts_path)
    t = _task("ht-c", [
        {"date": "2026-08-01", "direction": "inbound"},
        {"date": "2026-08-06", "direction": "internal", "note": "metrics pull"},
    ])
    assert [f["id"] for f in c.owed([t], TODAY)] == ["ht-c"]


def test_out_of_order_log_still_orders_by_date(scripts_path):
    """The position tiebreak must NOT weaken this: different dates order by date."""
    c = _import(scripts_path)
    t = _task("ht-d", [
        {"date": "2026-08-06", "direction": "outbound"},
        {"date": "2026-08-01", "direction": "inbound"},
    ])
    assert c.owed([t], TODAY) == [], "a later outbound listed first must still win"


def test_terminal_tasks_are_never_owed(scripts_path):
    c = _import(scripts_path)
    for status in ("completed", "abandoned", "stalled", "cancelled"):
        t = _task("ht-e", [{"date": "2026-08-01", "direction": "inbound"}], status=status)
        assert c.owed([t], TODAY) == [], status


def test_status_with_trailing_comment_is_parsed(scripts_path):
    """Real canvases carry YAML comments on the status line."""
    c = _import(scripts_path)
    t = _task("ht-f", [{"date": "2026-08-01", "direction": "inbound"}],
              status="completed  # CLOSED 2026-07-26 — question answered")
    assert c.owed([t], TODAY) == []


def test_under_threshold_is_silent(scripts_path):
    c = _import(scripts_path)
    t = _task("ht-g", [{"date": "2026-08-06", "direction": "inbound"}])
    assert c.owed([t], TODAY) == []


def test_explicit_reply_owed_forces_the_flag(scripts_path):
    c = _import(scripts_path)
    t = _task("ht-h", [{"date": "2026-08-01", "direction": "outbound"}],
              reply_owed="founder owes an answer")
    assert [f["id"] for f in c.owed([t], TODAY)] == ["ht-h"]


def test_missing_direction_is_unevaluable_not_owed(scripts_path):
    """Pre-v0.68.0 logs predate the direction contract. They must not false-fire."""
    c = _import(scripts_path)
    t = _task("ht-i", [{"date": "2026-08-01"}, {"date": "2026-08-02"}])
    assert c.owed([t], TODAY) == []


def test_malformed_entries_do_not_crash(scripts_path):
    c = _import(scripts_path)
    t = _task("ht-j", ["not a dict", {"direction": "inbound"}, {"date": "nope", "direction": "inbound"}])
    assert c.owed([t], TODAY) == []


# ------------------------------------------------------------------ failure direction
# A guard whose tests only cover the quiet path keeps passing after it stops
# working — the verify_citations failure mode. These assert the guard REJECTS.

def test_guard_rejects_an_unanswered_inbound(scripts_path):
    """SAD PATH. The whole purpose: someone wrote and was not answered. If this ever
    returns empty, the check has silently stopped guarding anything."""
    c = _import(scripts_path)
    findings = c.owed([_task("ht-owed", [{"date": "2026-07-25", "direction": "inbound"}])], TODAY)
    assert findings
    assert len(findings) == 1
    assert findings[0]["id"] == "ht-owed"
    assert findings[0]["age_days"] == 13


def test_guard_rejects_every_owed_task_in_a_mixed_batch(scripts_path):
    """Two owed among four. A guard that returns the first hit, or drops one, fails here."""
    c = _import(scripts_path)
    tasks = [
        _task("ok-1", [{"date": "2026-08-01", "direction": "outbound"}]),
        _task("owed-1", [{"date": "2026-08-01", "direction": "inbound"}]),
        _task("ok-2", [{"date": "2026-08-02", "direction": "inbound"},
                       {"date": "2026-08-02", "direction": "outbound"}]),
        _task("owed-2", [{"date": "2026-07-20", "direction": "inbound"}]),
    ]
    findings = c.owed(tasks, TODAY)
    assert len(findings) == 2
    assert sorted(f["id"] for f in findings) == ["owed-1", "owed-2"]


def test_json_status_reports_violations(scripts_path, tmp_path, monkeypatch, capsys):
    """The reporting layer must carry the rejection, not just the internal list."""
    import json as _json
    c = _import(scripts_path)
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "human-tasks.yml").write_text(
        "pending_tasks:\n"
        "  - id: ht-owed\n"
        "    status: pending\n"
        "    touch_log:\n"
        '      - date: "2026-07-25"\n'
        "        direction: inbound\n"
    )
    monkeypatch.setattr(sys, "argv",
                        ["x", "--project-dir", str(tmp_path), "--json", "--today", "2026-08-07"])
    assert c.main() == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "violations"
    assert len(payload["violations"]) == 1
