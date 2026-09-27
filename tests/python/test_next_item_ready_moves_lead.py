"""A move that can happen now leads one that waits on the world, and an item says what to do (v0.276.0).

E2E rungs on 0.275.0 and 0.275.1:
- L4-define and L4-develop: the L3's pilot notes arrived every session, so the L3 led the ladder
  though it could not complete before its pilot ended, and the L4 whose next move was desk work sat
  under "Also waiting" (L4-develop reached develop 1 of 3). The failed L4-define run also opened the
  L4 with no bar and spent two sessions asking the founder to write one she had already decided.
- L5-open: the launch-data item borrowed the verdict's instruction ("record the result against the
  bar the test was frozen with"), and the builder held the launch figures for two sessions asking
  "say the word". Founder, 2026-09-27: propose a move once what it needs is on record.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("next_item_ready", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)

TODAY = "2026-11-20"
L3_PILOT = """  - id: l3-a
    scale: L3
    phase: deliver
    learning_delivery:
      audience: five invited testers
      started: '2026-11-02'
"""
L3_NO_PILOT = """  - id: l3-a
    scale: L3
    phase: deliver
"""
L4 = """  - id: l4-a
    scale: L4
    phase: discover
    parent: l3-a
"""


def _project(tmp_path: Path, diamonds: str) -> Path:
    d = tmp_path / ".claude" / "diamonds"
    d.mkdir(parents=True)
    (d / "active.yml").write_text("product_paths: []\nactive_diamonds:\n" + diamonds)
    return tmp_path


def test_the_move_that_can_happen_now_leads(tmp_path):
    item = ni._ladder_item(_project(tmp_path, L3_PILOT + L4), TODAY, {})
    assert item["diamond"] == "l4-a", item["text"]
    assert "Also waiting: l3-a (L3)" in item["text"]
    rows = {r["diamond"]: r for r in ni._unassessed(tmp_path, TODAY)}
    assert "It waits on its learning delivery ending" in rows["l3-a"]["text"]
    assert "waits on" not in rows["l4-a"]["text"]


def test_control_an_l3_with_nothing_to_wait_on_keeps_its_place(tmp_path):
    """Planted defect: no learning delivery, so nothing outside a ruling blocks the L3's move;
    the order is the file's, and the L3 still leads."""
    item = ni._ladder_item(_project(tmp_path, L3_NO_PILOT + L4), TODAY, {})
    assert item["diamond"] == "l3-a", item["text"]


def test_a_bare_diamond_gets_its_bar_drafted_not_asked_for(tmp_path):
    item = ni._ladder_item(_project(tmp_path, L3_PILOT + L4), TODAY, {})
    assert "l4-a has no bar yet: draft its `definition_of_done`" in item["text"]
    assert "`purpose_stance`" in item["text"] and "do not ask them to write it" in item["text"]
    human = ni.render_human({**item, "shown": 1})
    assert "Also waiting: l3-a (L3)" in human, "the hint goes after the list the human reads"


def test_control_a_diamond_with_a_bar_gets_no_draft_hint(tmp_path):
    barred = L4 + "    definition_of_done:\n      outcome: 300 page opens by 31 December\n"
    item = ni._ladder_item(_project(tmp_path, L3_PILOT + barred), TODAY, {})
    assert item["diamond"] == "l4-a" and "no bar yet" not in item["text"]


def test_the_launch_record_says_what_to_write_not_what_to_score(tmp_path):
    shipped = L3_NO_PILOT + L4.replace("phase: discover", "phase: deliver")
    item = ni._door_item(_project(tmp_path, shipped), TODAY, {})
    assert item["id"] == "launch-data-l4:l4-a"
    agent = ni.render({**item, "shown": 3, "first_shown": "2026-11-18"})
    assert "YOURS TO DO NOW" in agent and "write the fields yourself" in agent
    assert "page opens are not uses" in agent
    assert "frozen with" not in agent, "a launch record has no frozen bar"


def test_control_the_verdict_keeps_its_own_instruction():
    verdict = {"id": "verdict-l3:l3-a", "text": "l3-a (L3): no verdict is recorded.",
               "command": "/mycelium:assumption-test", "shown": 1, "first_shown": TODAY}
    assert "record the result against the bar the test was frozen with" in ni.render(verdict)
