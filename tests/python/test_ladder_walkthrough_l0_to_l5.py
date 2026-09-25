"""The whole ladder, L0 to L5, walked through Mycelium's real gate (v0.253.3).

Founder, 2026-09-25: "the happy path from L0 to L5 is the highest priority as I cannot confirm it
manually." Twenty-four E2E runs never got past L3, so L4 and L5 had never been exercised at all.
This drives no agent. It writes each artefact in the order a project produces them and pushes every
change to diamonds/active.yml through `hooks/scale-lock-gate.sh`, the hook Claude Code runs. At each
rung it asserts both halves: the door stays SHUT one artefact short, and OPENS once the artefact is
on record. Since v0.255.0 it also asserts, at every rung, that Mycelium PROPOSES the door once its
lock holds, and not before or after: a door the test opens itself proves the lock, not the door. Every phase move carries its transition's gates and a history entry, as the gate demands.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
GATE = PLUGIN / "hooks" / "scale-lock-gate.sh"
_spec = importlib.util.spec_from_file_location("scale_locks", PLUGIN / "scripts" / "scale_locks.py")
sl = importlib.util.module_from_spec(_spec)
sys.modules["scale_locks"] = sl
_spec.loader.exec_module(sl)
_nspec = importlib.util.spec_from_file_location("next_item", PLUGIN / "scripts" / "next_item.py")
ni = importlib.util.module_from_spec(_nspec)
_nspec.loader.exec_module(ni)


def _proposed(root: Path) -> str:
    """The id of the one item Mycelium proposes at the next session start."""
    item, _ = ni.pick(root, "", DAY)
    return item["id"] if item else ""

DAY = "2026-09-25"


class Project:
    """A project on disk, and a diamonds file that changes only when the real gate allows it."""

    def __init__(self, root: Path):
        self.root = root
        self.canvas = root / ".claude" / "canvas"
        self.active = root / ".claude" / "diamonds" / "active.yml"
        self.canvas.mkdir(parents=True)
        self.active.parent.mkdir(parents=True)
        (root / ".claude" / "state").mkdir()
        self.diamonds: list[dict] = []
        self.active.write_text(yaml.safe_dump({"active_diamonds": []}))

    def canvas_file(self, name: str, doc: dict) -> None:
        (self.canvas / name).write_text(yaml.safe_dump(doc, sort_keys=False))

    def gate(self, diamonds: list[dict]) -> tuple[int, str]:
        payload = {"tool_name": "Write", "tool_input": {
            "file_path": str(self.active),
            "content": yaml.safe_dump({"active_diamonds": diamonds}, sort_keys=False)}}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root),
               "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
        r = subprocess.run(["bash", str(GATE)], input=json.dumps(payload), capture_output=True,
                           text=True, env=env, timeout=60, check=False)
        return r.returncode, r.stderr

    def write(self, diamonds: list[dict]) -> None:
        """The write must pass the gate; then it lands."""
        rc, err = self.gate(diamonds)
        assert rc == 0, f"the gate refused a write the ladder allows:\n{err}"
        self.diamonds = diamonds
        self.active.write_text(yaml.safe_dump({"active_diamonds": diamonds}, sort_keys=False))

    def refused(self, diamonds: list[dict], because: str) -> None:
        """The write must be refused, and say why."""
        rc, err = self.gate(diamonds)
        assert rc == 2, f"the gate allowed a write it should refuse ({because})"
        assert because in err, f"refused, but not for '{because}':\n{err}"

    def add(self, d: dict) -> list[dict]:
        return [*self.diamonds, d]

    def moved(self, did: str, to: str, **extra) -> list[dict]:
        """The diamonds with `did` moved forward to `to`, its gates passed and history written."""
        out = []
        for d in self.diamonds:
            if d["id"] != did:
                out.append(d)
                continue
            crossed = sl._crossed(d.get("phase", "discover"), to)
            gates = dict(d.get("theory_gates_status") or {})
            for t in crossed:
                gates.update(dict.fromkeys(sl.transition_gates(d["scale"], t), "pass"))
            hist = list(d.get("progression_history") or []) + [
                {"transition": t.replace("->", " -> "), "date": DAY, "ruling": "progressed"}
                for t in crossed]
            out.append({**d, **extra, "phase": to, "theory_gates_status": gates,
                        "progression_history": hist, "progression_ruled_at": DAY})
        return out


def test_the_ladder_opens_rung_by_rung_from_l0_to_l5(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", DAY)
    p = Project(tmp_path)

    # L0: the idea. Nothing above it.
    l0 = {"id": "l0", "scale": "L0", "phase": "discover"}
    p.write(p.add(l0))

    # L1 opens on a stated purpose (why and who).
    l1 = {"id": "l1", "scale": "L1", "phase": "discover",
          "object_ref": "lead with multi-site cafes"}
    p.refused(p.add(l1), "purpose")
    assert _proposed(tmp_path) != "door-l1:l0", "no L1 door before the purpose is stated"
    p.canvas_file("purpose.yml", {
        "why": "Swaps are approved in one place so nobody relays them by hand",
        "who": {"description": "Shift leads at cafes with 2-10 sites"}})
    # v0.255.0: every door is asserted to be PROPOSED, not only to open when a test opens it.
    assert _proposed(tmp_path) == "door-l1:l0", "the L1 door is proposed once the purpose is stated"
    p.write(p.add(l1))
    assert _proposed(tmp_path) != "door-l1:l0", "and not again once the L1 is open"

    # L2 opens on a strategy (the L1, a North Star, the landscape) and a desired outcome.
    l2 = {"id": "l2", "scale": "L2", "phase": "discover", "object_ref": "opp-001"}
    p.refused(p.add(l2), "north-star")
    assert _proposed(tmp_path) != "door-l2:l1", "no L2 door before the strategy is on record"
    p.canvas_file("north-star.yml", {"metric": {"name": "swaps settled in the app per week"}})
    p.canvas_file("landscape.yml", {"components": [{"id": "comp-1", "name": "group chat"}]})
    opps = {"desired_outcome": {"metric": "share of swaps approved without a phone call",
                                "north_star_input_ref": "swaps settled in the app per week"},
            "opportunities": [{"id": "opp-001", "name": "Approver is off", "status": "open",
                               "provenance": {"evidence_type": "speculation"},
                               "solutions": [{"id": "sol-001", "name": "Backup approver"}]}]}
    p.canvas_file("opportunities.yml", opps)
    assert _proposed(tmp_path) == "door-l2:l1", "the L2 door is proposed once its lock holds"
    p.write(p.add(l2))
    assert _proposed(tmp_path) != "door-l2:l1", "and not again once the L2 is open"

    # L3 opens on a target opportunity with evidence and a source.
    l3 = {"id": "l3", "scale": "L3", "phase": "discover", "object_ref": "sol-001", "parent": "l2"}
    p.refused(p.add(l3), "evidence behind the opportunity")
    assert _proposed(tmp_path) != "door-l3:l2", "no L3 door before the opportunity has evidence"
    opps["opportunities"][0]["provenance"] = {
        "evidence_type": "anecdotal",
        "evidence_sources": ["decliner calls: 3 of 5 sites lost swaps while the manager was off"]}
    p.canvas_file("opportunities.yml", opps)
    assert _proposed(tmp_path) == "door-l3:l2", "the L3 door is proposed once its lock holds"
    p.write(p.add(l3))
    assert _proposed(tmp_path) != "door-l3:l2", "and not again once the L3 is open"

    # The L3 builds only after naming the lightest test of its riskiest assumption (v0.253.0), and
    # the safety gates need their records.
    p.canvas_file("threat-model.yml", {"threats": [{"id": "t1", "description": "guessed link"}]})
    p.canvas_file("privacy-assessment.yml", {"last_assessed": DAY,
                                             "data_inventory": [{"data_type": "phone number"}]})
    p.write(p.moved("l3", "define"))
    p.refused(p.moved("l3", "develop"), "the lightest test that answers it")
    sol = opps["opportunities"][0]["solutions"][0]
    sol["riskiest_assumption"] = {"statement": "a named backup approves when the manager is off",
                                  "cheapest_test": "live trial at Harbour while Ines is away, "
                                                   "thresholds frozen before the window"}
    p.canvas_file("opportunities.yml", opps)
    p.write(p.moved("l3", "develop"))
    assert sl.delivery_state(str(tmp_path))[0], "code may be written once the L3 is in develop"

    _deliver_to_learn_then_open_l4(p, tmp_path, opps)
    _ship_and_open_l5(p, tmp_path)


def _deliver_to_learn_then_open_l4(p: Project, root: Path, opps: dict) -> None:
    """The L3 delivers to learn, its trial reads out, and the L4 opens on the verdict."""
    # v0.257.0: the L3 DELIVERS TO LEARN. Its test needs real use, so its own Deliver is proposed;
    # the L4 builds to earn and waits on the verdict (E2E run 29, where 0.256.0 routed it wrong).
    l4 = {"id": "l4", "scale": "L4", "phase": "discover", "parent": "l3",
          "object_ref": "sol-001"}
    p.refused(p.add(l4), "medium confidence")
    assert _proposed(root) == "deliver-l3:l3", "the L3's learning delivery is proposed"
    p.write(p.moved("l3", "deliver"))
    assert _proposed(root) != "deliver-l3:l3", "and not again once the L3 is in Deliver"
    ok, why = sl.exposure_state(str(root))
    assert not ok and "learning_delivery" in why, "no audience recorded, nobody meets it"
    p.write([{**d, "learning_delivery": {
        "audience": "Harbour's nine staff, opted in by the site lead",
        "until": "2026-10-25",
        "means": "infrastructure as code: one environment, torn down after the trial"}}
        if d["id"] == "l3" else d for d in p.diamonds])
    assert sl.exposure_state(str(root))[0], "the learning build may meet its audience"
    assert _proposed(root) != "door-l4:l3", "no L4 door while the trial has not read out"

    # The trial reads out: the verdict is the medium-confidence evidence the L4 opens on.
    opps["opportunities"][0]["solutions"][0]["riskiest_assumption"]["verdict"] = "validated"
    p.canvas_file("opportunities.yml", opps)
    assert _proposed(root) == "door-l4:l3", "the L4 door is proposed once its lock holds"
    p.write(p.add(l4))
    assert _proposed(root) != "door-l4:l3", "and not again once the L4 is open"


def _ship_and_open_l5(p: Project, root: Path) -> None:
    """The second half of the walk: the L4 ships and the L5 opens on it."""
    # L4 ships: through define and develop into deliver, gates passed at every step.
    for phase in ("define", "develop", "deliver"):
        p.write(p.moved("l4", phase))
    assert sl.exposure_state(str(root))[0], "a shipped L4 may meet real people"

    # L5 opens on the shipped L4 plus launch data; the shipped L4 is the L5 door's event (v0.254.0).
    assert _proposed(root) == "door-l5:l4", "a shipped L4 proposes the L5 door"
    l5 = {"id": "l5", "scale": "L5", "phase": "discover", "parent": "l4"}
    p.refused(p.add(l5), "launch data")
    p.write([{**d, "launch_data": {"usage": "Harbour: 41 swap requests in three weeks"}}
             if d["id"] == "l4" else d for d in p.diamonds])
    assert _proposed(root) == "door-l5:l4", "still proposed, now to open the L5"
    p.write(p.add(l5))
    assert _proposed(root) != "door-l5:l4", "and not again once the L5 is open"

    # And the L5 can itself move through its phases.
    for phase in ("define", "develop", "deliver"):
        p.write(p.moved("l5", phase))
    assert [d["phase"] for d in p.diamonds if d["scale"] == "L5"] == ["deliver"]
