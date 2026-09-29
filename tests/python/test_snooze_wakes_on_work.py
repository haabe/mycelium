"""A door snoozed until asked comes back when the product changes after it (v0.285.0).

E2E relay L3-open on 0.283.0: the builder added fractions and ranges to the recipe code by editing
an existing file, the founder snoozed the L1 door "until asked", and nothing was offered for the
rest of the run while the product was built outside the ladder. Service run 10 went silent the
same way for 12 sessions.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("next_item_wake", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)
al = ni.al

DOOR = "door-l1:l0"
PAST = "2026-01-01T00:00:00+00:00"


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "app").mkdir()
    (tmp_path / "research").mkdir()
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    return tmp_path


def _snooze(root: Path, aid: str = DOOR, until: str = "asked", ts: str = PAST,
            session: str = "s-rule") -> dict:
    ev = {"kind": "ruled", "id": aid, "date": "2026-10-10", "ruling": "snooze", "note": "later",
          "until": until, "ts": ts, "session": session}
    al.append_events(al.ledger_path(root), [ev])
    return al.state(al.read_events(al.ledger_path(root))[0])


def _write(root: Path, rel: str, old: bool = False) -> Path:
    f = root / rel
    f.write_text("x = 1\n")
    if old:
        t = datetime.fromisoformat(PAST).timestamp() - 3600
        os.utime(f, (t, t))
    return f


def test_a_product_change_after_the_snooze_wakes_the_door(tmp_path):
    root = _repo(tmp_path)
    st = _snooze(root)
    _write(root, "app/scale.py")
    assert ni._woken(root, st) == {DOOR: 1}


def test_control_nothing_changed_since_the_snooze(tmp_path):
    root = _repo(tmp_path)
    st = _snooze(root)
    _write(root, "app/scale.py", old=True)
    assert ni._woken(root, st) == {}


def test_control_what_the_ruling_session_wrote_does_not_wake_it(tmp_path):
    root = _repo(tmp_path)
    st = _snooze(root)
    f = _write(root, "app/scale.py")
    (root / ".claude" / "state" / "change-log.jsonl").write_text(json.dumps(
        {"file_path": str(f), "session_id": "s-rule"}) + "\n")
    assert ni._woken(root, st) == {}


def test_control_a_research_note_is_evidence_not_product_work(tmp_path):
    root = _repo(tmp_path)
    st = _snooze(root)
    _write(root, "research/week-one.md")
    assert ni._woken(root, st) == {}


def test_control_other_items_and_dated_snoozes_keep_their_ruling(tmp_path):
    root = _repo(tmp_path)
    _snooze(root, aid="diamonds-no-dod")
    st = _snooze(root, aid="door-l3:l2", until="2027-01-01")
    _write(root, "app/scale.py")
    assert ni._woken(root, st) == {}


def test_pick_offers_the_woken_door_and_says_why(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    _snooze(root)

    def door(_root, today, st):
        blocked = ni._blocked(st.get(DOOR, {}), today)
        return None if blocked else {"id": DOOR, "text": "Open the L1.", "command": "x"}

    monkeypatch.setattr(ni, "_product_paths_item", lambda *a: None)
    monkeypatch.setattr(ni, "_door_item", door)
    monkeypatch.setattr(ni, "_ladder_item", lambda *a: None)
    item, _ = ni.pick(root, "", "2026-10-20")
    assert item is None, "control: snoozed, nothing changed"
    _write(root, "app/scale.py")
    item, _ = ni.pick(root, "", "2026-10-20")
    assert item["id"] == DOOR and item["text"].startswith("Snoozed until asked; since then 1")


def test_a_ruling_records_its_machine_time_and_the_session_it_was_shown_in(tmp_path):
    root = _repo(tmp_path)
    (root / ".claude" / "state" / "next-item.json").write_text(
        json.dumps({"id": DOOR, "session": "s-shown"}))
    before = time.time() - 1
    al.rule(root, DOOR, "snooze", "later", "2026-10-10", until="asked")
    x = al.state(al.read_events(al.ledger_path(root))[0])[DOOR]
    assert x["snooze_session"] == "s-shown"
    assert datetime.fromisoformat(x["snooze_ts"]).timestamp() >= before
    assert datetime.fromisoformat(x["snooze_ts"]).tzinfo == UTC
