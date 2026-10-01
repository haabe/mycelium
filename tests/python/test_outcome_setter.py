"""An L2 opens under the L1 that set its outcome (v0.304.0).

0.301.0's L2 door paired an unmapped outcome with the first L1 whose lock held. With two L1s live
it named the wrong parent: on the dogfood repo, 2026-10-01, it proposed the L2 on the outcome
`adoption` under `l1-enforcement-substrate`, whose decision is a runtime choice and set no outcome.
Now the outcome names its L1 (`desired_outcomes[].set_by`); with no name and several L1s, the next
item asks which, and the lock refuses a new L2 under an L1 other than the one named.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import next_item as ni  # noqa: E402
import scale_locks as sl  # noqa: E402

TODAY = "2026-10-01"
L1A = {"id": "l1-a", "scale": "L1", "phase": "develop", "object_ref": "a runtime choice"}
L1B = {"id": "l1-b", "scale": "L1", "phase": "develop", "object_ref": "who we serve first"}


def _root(tmp_path: Path, diamonds: list[dict], set_by: str | None = None) -> Path:
    out = {"id": "adoption", "metric": "decisions made on outside evidence"}
    if set_by:
        out["set_by"] = set_by
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas" / "opportunities.yml").write_text(
        yaml.safe_dump({"desired_outcomes": [out], "opportunities": []}))
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": diamonds}))
    return tmp_path


def _door(monkeypatch, root: Path, diamonds: list[dict]):
    monkeypatch.setattr(ni.sl, "can_open", lambda *a, **k: [])  # every lock holds
    return ni._entry_door(root, TODAY, {}, diamonds, [])


def test_with_two_l1s_and_no_setter_the_door_asks_which(monkeypatch, tmp_path):
    item = _door(monkeypatch, _root(tmp_path, [L1A, L1B]), [L1A, L1B])
    assert item["id"] == "outcome-setter:adoption", item
    assert not ni.agent_owned(item), "which L1 set it is the founder's to say"


def test_the_door_opens_under_the_l1_that_set_the_outcome(monkeypatch, tmp_path):
    item = _door(monkeypatch, _root(tmp_path, [L1A, L1B], set_by="l1-b"), [L1A, L1B])
    assert item["id"] == "door-l2:l1-b", "not l1-a, first in file order"


def test_a_lone_l1_needs_no_setter(monkeypatch, tmp_path):
    item = _door(monkeypatch, _root(tmp_path, [L1A]), [L1A])
    assert item["id"] == "door-l2:l1-a"


def test_the_lock_refuses_an_l2_under_another_l1(tmp_path):
    l2 = {"id": "l2", "scale": "L2", "phase": "discover", "parent": "l1-a",
          "object_ref": "adoption"}
    st = sl.State(str(_root(tmp_path / "a", [L1A, L1B, l2], set_by="l1-b")))
    assert any("the L1 that set adoption" in m for m in st._l2_setter_missing(l2))
    st = sl.State(str(_root(tmp_path / "b", [L1A, L1B, {**l2, "parent": "l1-b"}], set_by="l1-b")))
    assert st._l2_setter_missing({**l2, "parent": "l1-b"}) == []
    st = sl.State(str(_root(tmp_path / "c", [L1A, L1B, l2])))
    assert st._l2_setter_missing(l2) == [], "no set_by: not refused, the next item asks"
