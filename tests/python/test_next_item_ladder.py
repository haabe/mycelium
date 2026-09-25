"""An unanswered next item escalates on a ladder that stops on any ruling (v0.250.0).

E2E run 19: the agent had the same next item in context for 16 sessions and never acted, and the
human line said the same words every session. next-item.json was rewritten from scratch each
session, so nothing counted and nothing escalated. The design and its sources are in next_item.py
(THE LADDER); these tests pin each rung.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("next_item", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)

L0 = "active_diamonds:\n  - id: l0-x\n    scale: L0\n    phase: discover\n"


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(L0)
    return tmp_path


def _session(root: Path, session: str, today: str, monkeypatch) -> dict:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr("sys.stdout", io.StringIO())
    ni.main(["--project-dir", str(root), "--session", session, "--today", today, "--write-state"])
    return json.loads((root / ni.STATE_REL).read_text())


def _rule(root: Path, item_id: str, date: str) -> None:
    with (root / ".claude" / "state" / "advisory-ledger.jsonl").open("a") as f:
        f.write(json.dumps({"kind": "ruled", "id": item_id, "date": date, "ruling": "keep"}) + "\n")


def test_the_count_carries_across_sessions_not_within_one(tmp_path, monkeypatch):
    root = _project(tmp_path)
    assert _session(root, "s1", "2026-09-24", monkeypatch)["shown"] == 1
    assert _session(root, "s1", "2026-09-24", monkeypatch)["shown"] == 1  # same session
    st = _session(root, "s2", "2026-09-25", monkeypatch)
    assert st["shown"] == 2 and st["first_shown"] == "2026-09-24"


def test_the_third_unanswered_session_asks_for_a_decision(tmp_path, monkeypatch):
    root = _project(tmp_path)
    for i, day in enumerate(("2026-09-24", "2026-09-25")):
        st = _session(root, f"s{i}", day, monkeypatch)
        assert "unanswered" not in st["text_human"]  # below the threshold: the plain item
    st = _session(root, "s9", "2026-09-26", monkeypatch)
    assert "unanswered for 3 sessions since 2026-09-24" in st["text_human"]
    assert "If the item is wrong, say so" in st["text_human"]
    assert "put it to the user this session" in st["text"]


def test_any_ruling_resets_the_ladder(tmp_path, monkeypatch):
    root = _project(tmp_path)
    for i, day in enumerate(("2026-09-24", "2026-09-25", "2026-09-26")):
        _session(root, f"s{i}", day, monkeypatch)
    _rule(root, "unassessed", "2026-09-26")
    st = _session(root, "s4", "2026-09-27", monkeypatch)
    assert st["shown"] == 1 and st["first_shown"] == "2026-09-27"


def test_the_agent_gets_it_once_per_session_beside_the_request(tmp_path, monkeypatch):
    root = _project(tmp_path)
    for i, day in enumerate(("2026-09-24", "2026-09-25")):
        _session(root, f"s{i}", day, monkeypatch)
    assert ni.prompt_line(root) == ""  # below the threshold
    _session(root, "s3", "2026-09-26", monkeypatch)
    line = ni.prompt_line(root)
    assert line.startswith("MYCELIUM OPEN ITEM, unanswered for 3 sessions")
    assert "--id unassessed" in line
    assert "The item: NEXT ITEM, unanswered for 3 sessions" in line and "{" not in line
    assert ni.prompt_line(root) == ""  # later prompts in the same session: quiet
    _session(root, "s4", "2026-09-27", monkeypatch)
    _rule(root, "unassessed", "2026-09-27")
    assert ni.prompt_line(root) == ""  # answered this session: quiet


def test_an_item_that_leaves_is_recorded_with_its_count(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    _session(root, "s2", "2026-09-25", monkeypatch)
    (root / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: []\n")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    ni.main(["--project-dir", str(root), "--session", "s3", "--today", "2026-09-26", "--write-state"])
    assert not (root / ni.STATE_REL).exists()
    row = json.loads((root / ni.LOG_REL).read_text().splitlines()[-1])
    assert row == {"id": "unassessed", "first_shown": "2026-09-24", "shown": 2,
                   "left": "2026-09-26", "outcome": "left"}


def test_the_prompt_line_flag_prints_and_exits(tmp_path, monkeypatch):
    root = _project(tmp_path)
    for i, day in enumerate(("2026-09-24", "2026-09-25", "2026-09-26")):
        _session(root, f"s{i}", day, monkeypatch)
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert ni.main(["--project-dir", str(root), "--prompt-line"]) == 0
    assert "MYCELIUM OPEN ITEM" in out.getvalue()


def test_an_unreadable_state_is_said_and_the_count_restarts(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    (root / ni.STATE_REL).write_text("{broken")
    out = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr("sys.stdout", out)
    ni.main(["--project-dir", str(root), "--session", "s2", "--today", "2026-09-25", "--write-state"])
    assert "unreadable" in out.getvalue()
    assert json.loads((root / ni.STATE_REL).read_text())["shown"] == 1


def test_resumes_in_one_sitting_neither_count_nor_repeat(tmp_path, monkeypatch):
    """v0.250.1: a driver that resumes per message fired session start per message (E2E run 20)."""
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    assert ni.claim_human(root).startswith("NEXT ITEM")  # the human gets it once
    st = _session(root, "s1", "2026-09-24", monkeypatch)  # a resume, same session, same day
    assert st["shown"] == 1 and st["repeated_at_stop"] is True
    assert ni.claim_human(root) == ""  # not again this sitting


def test_a_resume_on_a_later_day_is_a_new_sitting(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    ni.claim_human(root)
    st = _session(root, "s1", "2026-09-26", monkeypatch)
    assert st["shown"] == 2 and st["repeated_at_stop"] is False
    assert ni.claim_human(root)  # the re-entry moment shows it again


def test_claim_human_flag_prints_once(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    for expected in (True, False):
        out = io.StringIO()
        monkeypatch.setattr("sys.stdout", out)
        assert ni.main(["--project-dir", str(root), "--claim-human"]) == 0
        assert bool(out.getvalue().strip()) is expected


def test_doing_what_the_item_asks_resets_the_ladder(tmp_path, monkeypatch):
    """v0.250.2, E2E run 21: an L3 assessed in session 1 was escalated as unanswered in session 3
    because new evidence brought the same item back. Assessing the diamond answers the item."""
    prev = {"id": "unassessed:l3-x", "session": "s2", "emitted_at": "2026-09-25", "shown": 2,
            "first_shown": "2026-09-24", "first_shown_at": "2026-09-24T09:00:00+00:00"}
    later = {"id": "unassessed:l3-x", "assessed_at": "2026-09-24T19:29:00+00:00"}
    assert ni.carry(tmp_path, prev, later, "s3", "2026-09-26") == (1, "2026-09-26")
    before = {"id": "unassessed:l3-x", "assessed_at": "2026-09-24T08:00:00+00:00"}
    assert ni.carry(tmp_path, prev, before, "s3", "2026-09-26") == (3, "2026-09-24")


# --- v0.251.0: one item for the ladder, evidence counted, snooze until asked ------------------
# E2E run 21: one item per diamond fired on every canvas edit, rotated through all four diamonds,
# and the human snoozed each in turn, burying the L3 move go-live needed.

FOUR = """\
active_diamonds:
  - id: l0-x
    scale: L0
    phase: discover
  - id: l3-x
    scale: L3
    phase: develop
"""


def test_one_item_covers_every_diamond_and_the_delivering_one_leads(tmp_path, monkeypatch):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(FOUR)
    st = _session(tmp_path, "s1", "2026-09-24", monkeypatch)
    assert st["id"] == "unassessed"
    assert st["text_human"].startswith("NEXT ITEM: l3-x (L3)")
    assert "Also waiting: l0-x (L0)" in st["text_human"]


def test_one_snooze_covers_the_family_until_asked(tmp_path, monkeypatch):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(FOUR)
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    with (tmp_path / ".claude" / "state" / "advisory-ledger.jsonl").open("a") as f:
        f.write(json.dumps({"kind": "ruled", "id": "unassessed", "date": "2026-09-24",
                            "ruling": "snooze", "until": "asked"}) + "\n")
    item, _ = ni.pick(tmp_path, "", "2099-01-01")  # no date ever reaches "asked"
    assert item is None or item["id"] != "unassessed"


def test_an_edit_that_adds_no_evidence_does_not_repropose(tmp_path, monkeypatch):
    import diamond_rulings as dr
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    active = tmp_path / ".claude" / "diamonds" / "active.yml"
    active.write_text("active_diamonds:\n  - id: l3-x\n    scale: L3\n    phase: develop\n")
    canvas = tmp_path / ".claude" / "canvas" / "opportunities.yml"
    canvas.write_text("o:\n  - id: opp-1\n    provenance: {evidence_sources: [a]}\n")
    dr.record(tmp_path, "s0")
    active.write_text(active.read_text() + "    progression_ruled_at: '2026-09-24'\n")
    dr.record(tmp_path, "s1")  # the assessment, with 1 source on the canvas
    canvas.write_text("o:\n  - id: opp-1\n    note: reworded\n    provenance: {evidence_sources: [a]}\n")
    assert ni._unassessed(tmp_path, "2026-09-25") == []  # synthesis, not evidence
    canvas.write_text("o:\n  - id: opp-1\n    provenance: {evidence_sources: [a, b]}\n")
    items = ni._unassessed(tmp_path, "2026-09-25")
    assert items and "1 new evidence entry since" in items[0]["text"]


def test_the_ledger_accepts_and_labels_snooze_until_asked(tmp_path):
    import advisory_ledger as al
    out = al.rule(tmp_path, "unassessed", "snooze", "", "2026-09-24", until="asked")
    assert "until asked" in out
    events, _ = al.read_events(al.ledger_path(tmp_path))
    x = al.state(events)["unassessed"]
    assert al._snoozed_label(x) == "snoozed until you ask"


# --- v0.252.2: an answer in plain words is pointed at the command that records it -------------
# E2E run 22: the founder said "snooze it until 2026-10-26"; the agent never recorded it, and the
# item came back to the human as "unanswered for 3 sessions".


def test_a_plain_words_answer_gets_the_record_command(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    line = ni.answer_line(root, "On the desk-derived evidence item: snooze it until 2026-10-26.")
    assert line.startswith("MYCELIUM: this prompt looks like the user's answer")
    assert "--id unassessed" in line and "--ruling" in line
    assert ni.answer_line(root, "not now, ask me after the pilot")
    assert ni.answer_line(root, "Build the request page first.") == ""


def test_no_answer_prompt_once_the_answer_is_recorded(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    _rule(root, "unassessed", "2026-09-24")
    assert ni.answer_line(root, "snooze it") == ""


def test_the_prompt_hook_passes_the_prompt_through(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _session(root, "s1", "2026-09-24", monkeypatch)
    out = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "drop it, that's wrong"})))
    monkeypatch.setattr("sys.stdout", out)
    assert ni.main(["--project-dir", str(root), "--prompt-line"]) == 0
    assert "--id unassessed" in out.getvalue()
    assert ni._prompt_of("not json") == "" and ni._prompt_of("[]") == ""


def test_mycelium_today_sets_the_date_rulings_and_snoozes_use(monkeypatch):
    """v0.253.4, E2E run 25: a snooze given in a simulated calendar never expired on the machine's."""
    import advisory_ledger as al
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-13")
    assert al.today_iso() == "2026-10-13"
    assert ni._blocked({"snoozed_until": "2026-10-12"}, al.today_iso()) is False  # expired
    monkeypatch.setenv("MYCELIUM_TODAY", "next tuesday")
    assert al.today_iso() != "next tuesday"  # malformed: the real date
    monkeypatch.delenv("MYCELIUM_TODAY")
    assert len(al.today_iso()) == 10


def test_a_conditional_snooze_reaches_the_agent_once_per_sitting(tmp_path):
    """v0.254.1, E2E run 27: "not now, ask after the test design is frozen" became a snooze "until
    asked" that nothing would bring back. The condition now reaches the agent, never the human."""
    root = _project(tmp_path)
    (root / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    ledger = root / ".claude" / "state" / "advisory-ledger.jsonl"
    ledger.write_text(json.dumps({"kind": "ruled", "id": "unassessed", "date": "2026-09-24",
                                  "ruling": "snooze", "until": "asked",
                                  "note": "ask after the test design is frozen"}) + "\n"
                      + json.dumps({"kind": "ruled", "id": "bvssh-overdue", "date": "2026-09-24",
                                    "ruling": "snooze", "until": "2026-12-01",
                                    "note": "after the quarter"}) + "\n")
    line = ni.conditions_line(root, "s1", "2026-09-24")
    assert "`unassessed`: ask after the test design is frozen" in line
    assert "bvssh-overdue" not in line  # a dated snooze comes back on its own
    assert ni.conditions_line(root, "s1", "2026-09-24") == ""  # once per sitting
    assert ni.conditions_line(root, "s2", "2026-09-24")  # a new sitting says it again
    assert ni._session_of(json.dumps({"session_id": "s9"})) == "s9"
    assert ni._session_of("x") == ""
