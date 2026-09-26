"""A next item says whose it is (v0.272.0).

E2E service world, 2026-09-26: the pilot met the bar its test was frozen with, and the verdict item
was put to the founder for three sessions as "Decide one: run | rule | snooze | drop". The builder
left it for the founder, nobody wrote the verdict, and the L4 stayed locked. Recording a verdict
against a frozen bar is Mycelium's record work; a decision (a door, a release, a pivot) is the
founder's.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "next_item_owner", ROOT / "plugins" / "mycelium" / "scripts" / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)

VERDICT = {"id": "verdict-l3:dia-004", "text": "dia-004 (L3): its learning delivery ran until "
           "2026-11-10 and no verdict is recorded.", "command": "/mycelium:assumption-test",
           "shown": 3, "first_shown": "2026-12-02"}
DOOR = {"id": "door-l4:dia-004", "text": "dia-004 (L3) has delivered to learn. Open an L4 on it.",
        "command": "/mycelium:preflight", "shown": 3, "first_shown": "2026-12-02"}


def test_a_verdict_is_the_agents_to_record():
    agent = ni.render(VERDICT)
    assert "YOURS TO DO NOW" in agent and "frozen with" in agent
    assert "put it to the user" not in agent and "rule (say what you decide)" not in agent
    human = ni.render_human(VERDICT)
    assert human.startswith("MYCELIUM IS RECORDING") and "Decide one" not in human
    assert "ask the tool to do it now" in human, "an overdue one says so, to the right party"


def test_a_door_stays_the_founders_decision():
    """Control: a real decision keeps its menu for the human."""
    assert "put it to the user" in ni.render(DOOR)
    assert "Decide one" in ni.render_human(DOOR)
    assert not ni.agent_owned(DOOR) and ni.agent_owned(VERDICT)


DELIVER = {"id": "deliver-l3:dia-004", "text": "dia-004 (L3) has built what its test needs.",
           "command": "/mycelium:diamond-progress dia-004", "shown": 3, "first_shown": "2026-10-05"}


def test_an_overdue_learning_delivery_cuts_the_build_to_the_test():
    """v0.273.0, E2E service world run 3: the build grew for sessions while the test waited. Once
    the item is overdue, the agent is told to stop extending the build and send the rest to the
    tree; a fresh item and a door do not carry it."""
    overdue = ni.render(DELIVER)
    assert "THE BUILD IS GROWING WHILE THE TEST WAITS" in overdue
    assert "next assumption on the solution" in overdue and "L4 work" in overdue
    assert "put it to the user" in overdue, "the move to Deliver stays the founder's decision"
    assert "BUILD IS GROWING" not in ni.render({**DELIVER, "shown": 1})
    assert "BUILD IS GROWING" not in ni.render(DOOR)
