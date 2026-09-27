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
    assert "That move waits on its learning delivery ending" in rows["l3-a"]["text"]
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


OVER = """  - id: l3-a
    scale: L3
    phase: deliver
    riskiest_assumption: {verdict: inconclusive}
    learning_delivery:
      audience: three paying clients who opted in
      started: '2026-10-17'
      until: '2027-06-03'
"""


def test_a_delivery_past_its_last_day_asks_how_it_ended(tmp_path):
    """E2E service world run 5: the re-run item was snoozed until a cohort that never came, and
    the delivery ran a month past its last day with no item; the builder wrote its own `closed:`
    block while the clients carried on paying with no L4."""
    root = _project(tmp_path, OVER + "      closed: {outcome: no one came}\n")
    snoozed = {"rerun-l3:l3-a": {"until": "asked"}}
    item = ni._door_item(root, "2027-07-08", snoozed)
    assert item["id"] == "delivery-over-l3:l3-a:2027-06-03", item
    assert "`learning_delivery.ended: {how: withdrawn, on}`" in item["text"]
    assert "that is production: open an L4" in item["text"]
    assert not ni.agent_owned(item), "ending or carrying on is the founder's decision"


def test_control_an_ended_or_running_delivery_asks_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2027-07-08")  # the lock's own clock
    ended = OVER + "      ended: {how: withdrawn, on: '2027-06-04'}\n"
    assert ni._delivery_over_item(_project(tmp_path / "a", ended), "2027-07-08", {},
                                  _l3(tmp_path / "a")) is None
    assert ni._delivery_over_item(_project(tmp_path / "b", OVER), "2027-05-01", {},
                                  _l3(tmp_path / "b")) is None, "before its last day"


def test_an_extension_is_a_new_item_not_the_snoozed_one(tmp_path):
    root = _project(tmp_path, OVER.replace("2027-06-03", "2027-07-01"))
    snoozed = {"delivery-over-l3:l3-a:2027-06-03": {"until": "asked"}}
    item = ni._delivery_over_item(root, "2027-07-08", snoozed, _l3(root))
    assert item and item["id"].endswith(":2027-07-01")


def _l3(root: Path) -> dict:
    import yaml
    doc = yaml.safe_load((root / ".claude" / "diamonds" / "active.yml").read_text())
    return doc["active_diamonds"][0]


TEST_REL = ".claude/evals/assumption-tests/2026-10-01-return-use.md"


def _l3_with_test(tmp_path: Path, status: str, score_by: str) -> tuple[Path, dict]:
    root = _project(tmp_path, L3_PILOT)
    f = root / TEST_REL
    f.parent.mkdir(parents=True)
    f.write_text(f"---\ntype: assumption-test\nstatus: {status}\nscore_by: {score_by}\n---\n")
    sol = {"id": "sol-001", "riskiest_assumption": {"cheapest_test": TEST_REL}}
    return root, sol


def test_a_test_past_its_score_date_is_scored_by_the_agent(tmp_path):
    """E2E rung L4-open on 0.276.0: 4 of 5 came back against a bar of 3, the builder offered to
    write it and did not, and nothing asked until the delivery ended, past the budget."""
    root, sol = _l3_with_test(tmp_path, "live", "2026-10-30")
    item = ni._overdue_test_item(root, "2026-11-18", {}, "l3-a", sol)
    assert item["id"] == "score-l3:l3-a:2026-10-30" and ni.agent_owned(item)
    agent = ni.render({**item, "shown": 1, "first_shown": "2026-11-18"})
    assert "score the test yourself" in agent and "new `score_by`" in agent
    assert ni.render_human(item).startswith("MYCELIUM IS RECORDING")


def test_control_a_test_not_yet_due_or_already_scored_asks_nothing(tmp_path):
    root, sol = _l3_with_test(tmp_path / "a", "live", "2026-12-01")
    assert ni._overdue_test_item(root, "2026-11-18", {}, "l3-a", sol) is None, "not yet due"
    root, sol = _l3_with_test(tmp_path / "b", "scored", "2026-10-30")
    assert ni._overdue_test_item(root, "2026-11-18", {}, "l3-a", sol) is None, "scored item's job"


def test_the_waiting_move_does_not_stop_the_verdict(tmp_path):
    """0.276.0 said "It waits on its learning delivery ending"; the builder snoozed the L3."""
    rows = {r["diamond"]: r for r in ni._unassessed(_project(tmp_path, L3_PILOT + L4), TODAY)}
    assert "scoring its test and its verdict do not" in rows["l3-a"]["text"]
