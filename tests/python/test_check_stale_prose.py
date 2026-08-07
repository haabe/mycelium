"""Coverage proof for check_stale_prose.py.

The regression fixtures are VERBATIM shapes from the 2026-08-07 dogfood session that
motivated the check, not invented ones. Three bugs were found while building it, each
by running against the real pre-fix record; each has a test here so they cannot return.
"""
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_stale_prose
    return check_stale_prose


# ------------------------------------------------------------------ Rule B: the motivating case

HT060_PREFIX = """  - id: ht-060
    type: outreach
    objective: >-
      TWO THINGS, AND THE FIRST IS OWED TODAY. (1) Reply to Frida's 2026-08-02 message. She
      apologised twice, at length, for silence she owed nobody.
    status: pending
    touch_log:
      - date: "2026-08-02"
        direction: inbound
        note: Her reply, carried over so the reply-owed check has a live task to fire on.
      - date: "2026-08-02"
        direction: outbound
        note: Reply sent, same day. REPLY-OWED DISCHARGED without the check ever needing to fire.
"""


def test_catches_the_motivating_instance(scripts_path):
    """THE REGRESSION TEST. ht-060 advertised a live obligation for five days while its
    own touch_log recorded the reply sent. If this ever returns nothing, the checker is
    decoration -- which it was, twice, during construction."""
    c = _import(scripts_path)
    found = c.scan_text(HT060_PREFIX)
    rules = [r for r, _ in found]
    assert any(r.startswith("B/") for r in rules), f"missed the motivating case: {found}"


def test_nested_touch_log_does_not_hide_the_done_marker(scripts_path):
    """BUG 1. A flat field split let `touch_log:` capture only the bytes before its first
    child, so 'Reply sent' never reached the log side and the case produced NO finding."""
    c = _import(scripts_path)
    fields = c.split_fields(HT060_PREFIX)
    assert "Reply sent" in fields.get("touch_log", ""), \
        "touch_log must own its nested children"


def test_child_keys_are_not_classified_as_record_fields(scripts_path):
    """BUG 3. `note` is a record-level framing field AND a child key inside every
    touch_log entry. Classifying children dragged 'DISCHARGED' into the framing bucket,
    where the resolution-suppressor silenced the very instance this check exists for."""
    c = _import(scripts_path)
    fields = c.split_fields(HT060_PREFIX)
    assert "DISCHARGED" not in fields.get("note", ""), \
        "nested note: must not be classified as the record's framing note"


def test_quoted_stale_phrase_in_a_repair_note_is_not_flagged(scripts_path):
    """BUG 2. A record documenting a FIXED instance quotes the stale phrase. Without the
    quote guard the checker re-flags its own repair notes forever, and an advisory that
    nags about reconciled records is one the reader learns to skip."""
    c = _import(scripts_path)
    repaired = HT060_PREFIX.replace(
        "TWO THINGS, AND THE FIRST IS OWED TODAY.",
        'ONE THING LIVE; (1) DISCHARGED 2026-08-02. The objective kept reading '
        '"THE FIRST IS OWED TODAY" until 2026-08-07 because the touch_log moved and this '
        'line did not.',
    )
    found = [r for r, _ in c.scan_text(repaired)]
    assert not any(r.startswith("B/") for r in found), \
        f"re-flagged a record that was already repaired: {found}"


def test_honest_open_work_is_not_flagged(scripts_path):
    """NEGATIVE CONTROL for rule B. A task that says it is not done and HAS no completion
    record is honest open work. If this ever fires, the rule has degenerated into
    'flag every pending task'."""
    c = _import(scripts_path)
    open_task = """  - id: ht-999
    objective: >-
      The metrics pull has not run and the question is open.
    status: pending
    touch_log:
      - date: "2026-08-01"
        direction: outbound
        note: Question posted. No reply.
"""
    found = [r for r, _ in c.scan_text(open_task)]
    assert not any(r.startswith("B/") for r in found), f"flagged honest open work: {found}"


# ------------------------------------------------------------------ Rule A: unanchored deixis

def test_unanchored_today_is_flagged(scripts_path):
    c = _import(scripts_path)
    found = [r for r, _ in c.scan_text("    note: The brief is due today and nobody has it.")]
    assert any(r.startswith("A/") for r in found)


def test_today_next_to_a_date_is_not_flagged(scripts_path):
    """'as of today (2026-08-07)' is fine: the reader can see when today was."""
    c = _import(scripts_path)
    found = [r for r, _ in c.scan_text("    note: As of today, 2026-08-07, the pull is clean.")]
    assert not any(r.startswith("A/") for r in found)


def test_clean_record_produces_nothing(scripts_path):
    """Empty-input honesty: a clean record must produce zero findings, not a default one."""
    c = _import(scripts_path)
    assert c.scan_text("  - id: ht-1\n    objective: Ship the thing.\n    status: pending\n") == []


def test_refuses_over_an_empty_population(scripts_path, tmp_path, monkeypatch, capsys):
    """EMPTY-INPUT HONESTY. The first cut exited 0 over an empty repo, reporting
    'no candidates across 0 files'. check_empty_input_honesty.py caught it — a green
    result over an empty population is the one answer that is never true, and it is the
    exact failure this checker exists to report, committed inside the checker."""
    c = _import(scripts_path)
    (tmp_path / ".claude").mkdir()
    monkeypatch.setattr(sys, "argv", ["check_stale_prose.py", "--root", str(tmp_path)])
    rc = c.main()
    assert rc == 2, "must refuse, not pass, when nothing was scanned"
    assert "PRECONDITION NOT MET" in capsys.readouterr().err
