"""An L2 that never had an L3 is offered its door before one whose opportunity is served (v0.283.0).

E2E service run 9: two L2s could open an L3. The first in file order was the one whose L3 had
completed and whose solution was already in production; the founder ruled that door done, and the
untried L2, the audience the new L5 was about, was never offered.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("next_item_untried", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)

TODAY = "2027-02-10"
L1 = {"id": "l1", "scale": "L1", "phase": "discover"}
SERVED = {"id": "l2-clients", "scale": "L2", "phase": "discover", "parent": "l1",
          "object_ref": "opp-001"}
UNTRIED = {"id": "l2-members", "scale": "L2", "phase": "discover", "parent": "l1",
           "object_ref": "opp-002"}
DONE_L3 = {"id": "l3-pilot", "scale": "L3", "phase": "complete", "parent": "l2-clients",
           "object_ref": "opp-001"}


def _door(monkeypatch, past):
    monkeypatch.setattr(ni.sl, "can_open", lambda *a, **k: [])  # every lock holds
    return ni._entry_door(Path("."), TODAY, {}, [L1, SERVED, UNTRIED], past)


def test_the_untried_l2_is_offered_first(monkeypatch):
    item = _door(monkeypatch, [DONE_L3])
    assert item["id"] == "door-l3:l2-members", item["id"]


def test_control_with_no_history_file_order_holds(monkeypatch):
    item = _door(monkeypatch, [])
    assert item["id"] == "door-l3:l2-clients", "no history: nothing to prefer, file order"


def test_the_served_door_still_comes_once_the_untried_one_is_ruled_away(monkeypatch):
    monkeypatch.setattr(ni.sl, "can_open", lambda *a, **k: [])
    st = {"door-l3:l2-members": {"ruling": "drop"}}
    item = ni._entry_door(Path("."), TODAY, st, [L1, SERVED, UNTRIED], [DONE_L3])
    assert item["id"] == "door-l3:l2-clients", "the served L2 is not hidden, only second"
