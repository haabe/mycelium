"""Entry locks between diamond scales (v0.245.0): each scale opens on what its parent established.

Founder model, 2026-09-24: *"all scales have a natural lock per se. It might be unwise to build a
strategy unless you have a purpose. It would be unwise to start looking into opportunities without
knowing who to reach doing what (L0+L1). And so on."* Three releases had opened every door
regardless of the parent, so every scale could open at once.

Scenario-per-guardpost: for each lock, the state that holds it and the state one artefact short of
it; then the hook (only ADDED diamonds are judged), the user's override, the delivery question the
code gate asks, and the one fail-open (PyYAML absent), which must say so.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins" / "mycelium" / "scripts" / "scale_locks.py"
_spec = importlib.util.spec_from_file_location("scale_locks", SCRIPT)
sl = importlib.util.module_from_spec(_spec)
sys.modules["scale_locks"] = sl
_spec.loader.exec_module(sl)

PURPOSE = {"why": "Swaps are approved in one place so nobody relays them by hand",
           "who": {"description": "Shift leads at cafes with 2-10 sites"}}
OUTCOME = {"desired_outcome": {"metric": "share of swaps approved without a phone call"}}
OPP = {"id": "opp-001", "name": "Approver is off", "status": "open",
       "provenance": {"evidence_type": "anecdotal",
                      "evidence_sources": ["founder story: Tom off, three swaps relayed by phone"]},
       "solutions": [{"id": "sol-001", "name": "Backup approver"}]}


def _project(tmp_path: Path, purpose=None, opps=None, diamonds=None, ack=None) -> str:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True, exist_ok=True)
    (c / "diamonds").mkdir(parents=True, exist_ok=True)
    (c / "state").mkdir(parents=True, exist_ok=True)
    if purpose is not None:
        (c / "canvas" / "purpose.yml").write_text(yaml.safe_dump(purpose))
    if opps is not None:
        (c / "canvas" / "opportunities.yml").write_text(yaml.safe_dump(opps))
    (c / "diamonds" / "active.yml").write_text(yaml.safe_dump({"active_diamonds": diamonds or []}))
    if ack is not None:
        (c / "state" / "scale-lock-ack").write_text(ack)
    return str(tmp_path)


def _full_opps(**opp_changes):
    return {**OUTCOME, "opportunities": [{**OPP, **opp_changes}]}


# ---------------------------------------------------------------- L1 and L2


def test_l1_needs_a_purpose_and_who(tmp_path):
    assert sl.can_open(_project(tmp_path, purpose=PURPOSE), "L1") == []
    miss = sl.can_open(_project(tmp_path, purpose={"why": PURPOSE["why"]}), "L1")
    assert len(miss) == 1 and "`who`" in miss[0]


def test_a_who_holding_only_bookkeeping_is_empty(tmp_path):
    p = _project(tmp_path, purpose={"why": PURPOSE["why"], "who": {"validated": False}})
    assert any("`who`" in m for m in sl.can_open(p, "L1"))


def test_l2_needs_a_desired_outcome(tmp_path):
    assert sl.can_open(_project(tmp_path, purpose=PURPOSE, opps=OUTCOME), "L2") == []
    miss = sl.can_open(_project(tmp_path, purpose=PURPOSE, opps={}), "L2")
    assert miss and "desired outcome" in miss[0]


def test_l2_accepts_one_of_several_roots(tmp_path):
    opps = {"desired_outcomes": [{"id": "adoption", "metric": "weekly active sites"}]}
    assert sl.can_open(_project(tmp_path, purpose=PURPOSE, opps=opps), "L2") == []


# ---------------------------------------------------------------- L3


def test_l3_opens_on_a_target_opportunity_with_evidence(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps())
    assert sl.can_open(p, "L3", object_ref="sol-001") == []
    assert sl.can_open(p, "L3", object_ref="opp-001") == []


def test_l3_without_a_target_is_locked(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps())
    assert any("object_ref" in m for m in sl.can_open(p, "L3"))


def test_l3_on_a_speculative_opportunity_is_locked(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE,
                 opps=_full_opps(provenance={"evidence_type": "speculation"}))
    assert any("evidence behind the opportunity" in m for m in sl.can_open(p, "L3", object_ref="opp-001"))


def test_l3_on_a_closed_opportunity_is_locked(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(status="discarded"))
    assert any("open opportunity" in m for m in sl.can_open(p, "L3", object_ref="opp-001"))


def test_l3_reads_its_l2_parents_target(tmp_path):
    l2 = {"id": "l2-a", "scale": "L2", "phase": "develop", "object_ref": "opp-001"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[l2])
    assert sl.can_open(p, "L3", parent="l2-a") == []


def test_l3_with_several_roots_must_name_its_root(tmp_path):
    opps = {"desired_outcomes": [{"id": "a", "metric": "m1 grows"}, {"id": "b", "metric": "m2 grows"}],
            "opportunities": [OPP]}
    p = _project(tmp_path, purpose=PURPOSE, opps=opps)
    assert any("rolls_up_to" in m for m in sl.can_open(p, "L3", object_ref="opp-001"))


def test_l3_lock_includes_the_locks_above_it(tmp_path):
    p = _project(tmp_path, purpose={}, opps={"opportunities": [OPP]})
    miss = sl.can_open(p, "L3", object_ref="opp-001")
    assert any("purpose statement" in m for m in miss)
    assert any("desired outcome" in m for m in miss)


# ---------------------------------------------------------------- L4 and L5


def _l3(evidence="anecdotal"):
    return {"id": "l3-a", "scale": "L3", "phase": "develop", "object_ref": "sol-001",
            "evidence_type": evidence}


def test_l4_needs_its_l3_at_medium_confidence(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3("data-supported")])
    assert sl.can_open(p, "L4", parent="l3-a") == []
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3("anecdotal")])
    assert any("medium confidence" in m for m in sl.can_open(p, "L4", parent="l3-a"))


def test_l4_finds_its_l3_by_object_ref(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3("test-validated")])
    assert sl.can_open(p, "L4", object_ref="sol-001, swap request + single approval") == []


def test_l4_with_no_l3_is_locked(tmp_path):
    """The dogfood shape: an L4 whose parent is the L1, with no L3 between."""
    l1 = {"id": "l1-s", "scale": "L1", "phase": "develop"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[l1])
    assert any("the L3 it delivers" in m for m in sl.can_open(p, "L4", parent="l1-s"))


def test_l5_needs_a_shipped_l4_and_launch_data(tmp_path):
    l4 = {"id": "l4-a", "scale": "L4", "phase": "deliver", "parent": "l3-a"}
    base = [_l3("data-supported"), l4]
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=base)
    miss = sl.can_open(p, "L5", parent="l4-a")
    assert len(miss) == 1 and "launch data" in miss[0]
    l5 = {"id": "l5-m", "scale": "L5", "phase": "discover", "parent": "l4-a",
          "launch_data": {"usage": "3 sites used it daily for two weeks"},
          "pmf": {"band": "not-yet-measurable"}}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[*base, l5])
    assert sl.report(p)[0][-1] == ("l5-m", "L5", [], True)


def test_l5_from_an_unshipped_l4_is_locked(tmp_path):
    l4 = {"id": "l4-a", "scale": "L4", "phase": "develop", "parent": "l3-a"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3("data-supported"), l4])
    assert any("shipped" in m for m in sl.can_open(p, "L5", parent="l4-a"))


def test_a_parent_loop_is_reported_not_recursed(tmp_path):
    a = {"id": "a", "scale": "L4", "phase": "develop", "parent": "b"}
    b = {"id": "b", "scale": "L3", "phase": "develop", "parent": "a"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[a, b])
    assert sl.report(p)[0]  # terminates


# ---------------------------------------------------------------- delivery, the code gate's question


def test_code_needs_an_l3_whose_chain_holds(tmp_path):
    """The run-9 shape: /mycelium:start leaves a purpose; an L3 opened on it builds on a guess."""
    bare = {"id": "l3-x", "scale": "L3", "phase": "discover"}
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[bare])
    ok, why = sl.delivery_state(p)
    assert not ok and "desired outcome" in why
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3()])
    assert sl.delivery_state(p)[0]


def test_code_with_no_delivery_diamond_is_refused(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[{"id": "l0", "scale": "L0", "phase": "discover"}])
    ok, why = sl.delivery_state(p)
    assert not ok and "no diamond that delivers" in why


def test_a_completed_l3_does_not_carry_code(tmp_path):
    done = {**_l3(), "phase": "complete"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[done])
    assert not sl.delivery_state(p)[0]


def test_the_users_ack_overrides_one_diamond(tmp_path):
    bare = {"id": "l3-x", "scale": "L3", "phase": "discover"}
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[bare],
                 ack="l3-x L3 2026-09-24 user: prototype now, I will fill the tree after\n")
    assert sl.delivery_state(p)[0]
    row = sl.report(p)[0][0]
    assert row[3] is True and row[2]  # overridden, and still names what is missing


# ---------------------------------------------------------------- the hook: only ADDED diamonds


def _write(content: str, path=".claude/diamonds/active.yml"):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def test_hook_blocks_adding_a_locked_diamond(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE)
    new = yaml.safe_dump({"active_diamonds": [{"id": "l3-x", "scale": "L3", "phase": "discover"}]})
    out = sl.new_diamond_violations(p, _write(new))
    assert len(out) == 1 and "l3-x (L3) cannot open yet" in out[0]


def test_hook_never_rejudges_a_diamond_already_in_the_file(tmp_path):
    """Opened under older rules: editing its phase is never blocked here (--check reports it)."""
    old = {"id": "l4-old", "scale": "L4", "phase": "develop", "parent": "l1"}
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[old])
    new = yaml.safe_dump({"active_diamonds": [{**old, "phase": "deliver"}]})
    assert sl.new_diamond_violations(p, _write(new)) == []


def test_hook_applies_an_edit_before_judging(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps=OUTCOME)
    before = (tmp_path / ".claude/diamonds/active.yml").read_text()
    after_tail = "- id: l2-a\n  scale: L2\n  phase: discover\n"
    edit = {"tool_name": "Edit", "tool_input": {
        "file_path": str(tmp_path / ".claude/diamonds/active.yml"),
        "old_string": before, "new_string": "active_diamonds:\n" + after_tail}}
    assert sl.new_diamond_violations(p, edit) == []  # L2 lock holds: purpose + outcome


def test_hook_ignores_other_files(tmp_path):
    p = _project(tmp_path)
    assert sl.new_diamond_violations(p, _write("x: 1", path="src/app.py")) == []


def test_cli_hook_exit_2_and_names_the_ack(tmp_path, monkeypatch, capsys):
    p = _project(tmp_path, purpose=PURPOSE)
    new = yaml.safe_dump({"active_diamonds": [{"id": "l2-a", "scale": "L2", "phase": "discover"}]})
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(_write(new))))
    assert sl.main(["--project-dir", p, "--hook"]) == 2
    err = capsys.readouterr().err
    assert "desired outcome" in err and "scale-lock-ack" in err


# ---------------------------------------------------------------- cli and the fail-open


def test_cli_can_open_and_check_exit_codes(tmp_path, capsys):
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[{"id": "l2", "scale": "L2", "phase": "discover"}])
    assert sl.main(["--project-dir", p, "--can-open", "L1"]) == 0
    assert sl.main(["--project-dir", p, "--can-open", "L2"]) == 1
    assert sl.main(["--project-dir", p, "--can-open", "L9"]) == 2
    assert sl.main(["--project-dir", p, "--check"]) == 1
    assert "LOCKED" in capsys.readouterr().out


def test_an_unparseable_state_file_locks_and_says_why(tmp_path, capsys):
    p = _project(tmp_path, purpose=PURPOSE)
    (tmp_path / ".claude/diamonds/active.yml").write_text("active_diamonds: [unclosed\n")
    assert sl.main(["--project-dir", p, "--delivery-state"]) == 1
    assert "does not parse" in capsys.readouterr().out


def test_without_pyyaml_the_locks_say_they_are_unchecked(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sl, "yaml", None)
    assert sl.main(["--project-dir", str(tmp_path), "--delivery-state"]) == 3
    assert "not checked" in capsys.readouterr().out


@pytest.mark.parametrize("scale", ["L0", "L1", "L2", "L3", "L4", "L5"])
def test_every_scale_has_a_lock_answer(tmp_path, scale):
    assert isinstance(sl.can_open(_project(tmp_path), scale), list)


# ---------------------------------------------------------------- adversarial review, 2026-09-24


def test_l1_accepts_the_who_the_interview_actually_writes(tmp_path):
    """4 of 8 real E2E purposes had no `who`; one wrote `target_users`. The lock must not send the
    agent back to the interview it just ran."""
    p = _project(tmp_path, purpose={"why": PURPOSE["why"], "target_users": "cafe shift leads"})
    assert sl.can_open(p, "L1") == []


def test_a_string_desired_outcome_counts(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE, opps={"desired_outcome": "swaps approved in one place"})
    assert sl.can_open(p, "L2") == []


def test_evidence_needs_a_named_source(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE,
                 opps=_full_opps(provenance={"evidence_type": "anecdotal"}))
    assert any("source of its" in m for m in sl.can_open(p, "L3", object_ref="opp-001"))


def test_l5_door_opens_on_launch_data_written_to_the_l4(tmp_path):
    """The door runs --can-open L5 --parent <l4> BEFORE the L5 exists, so the data it needs must be
    readable from the L4 whose release it is."""
    l4 = {"id": "l4-a", "scale": "L4", "phase": "deliver", "parent": "l3-a",
          "launch_data": {"feedback": "two leads asked for it at the third site"}}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[_l3("data-supported"), l4])
    assert sl.can_open(p, "L5", parent="l4-a") == []


def test_a_closed_opportunity_relocks_nothing_already_open(tmp_path):
    """SPEED: an L3's opportunity is `addressed` once it ships. That must not lock the open L3 or
    stop its L4; the open-opportunity check is an entry check."""
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(status="addressed"),
                 diamonds=[_l3("data-supported")])
    assert sl.delivery_state(p)[0]
    assert any("open opportunity" in m for m in sl.can_open(p, "L3", object_ref="opp-001"))


def test_a_killed_or_archived_l3_is_no_parent(tmp_path):
    dead = {**_l3("data-supported"), "phase": "killed"}
    l4 = {"id": "l4-a", "scale": "L4", "phase": "develop", "parent": "l3-a"}
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[dead, l4])
    assert not sl.delivery_state(p)[0]


def test_ack_counts_only_a_well_formed_line_for_that_id_and_scale(tmp_path):
    bare = {"id": "anyway", "scale": "L3", "phase": "discover"}
    loose = '2026-09-24 d7: the user said "open it anyway"\n'
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[bare], ack=loose)
    assert not sl.delivery_state(p)[0]
    assert sl.report(p)[1], "an ignored ack line is reported, not silently dropped"
    p = _project(tmp_path, purpose=PURPOSE, diamonds=[bare], ack="anyway L2 2026-09-24 user: ok\n")
    assert not sl.delivery_state(p)[0], "an ack for another scale does not carry over"


def test_odd_references_and_shapes_do_not_crash(tmp_path):
    l3 = {"id": "l3-a", "scale": "L3", "phase": "develop", "object_ref": ", sol-001",
          "evidence_type": "data-supported"}
    l4 = {"id": "l4-a", "scale": "L4", "phase": "develop", "object_ref": ", sol-001"}
    p = _project(tmp_path, purpose=PURPOSE, opps={"opportunities": "not a list"}, diamonds=[l3, l4])
    assert isinstance(sl.report(p)[0], list)
    l3["object_ref"] = "opportunities.yml#sol-001"
    l4["object_ref"] = "sol-001"
    p = _project(tmp_path, purpose=PURPOSE, opps=_full_opps(), diamonds=[l3, l4])
    assert sl.delivery_state(p)[0], "`#` is parsed the same way on both sides"


@pytest.mark.parametrize("path", [".claude/diamonds/ACTIVE.yml", ".claude/Diamonds/active.yml",
                                  ".claude/diamonds/./active.yml"])
def test_hook_path_spellings_are_the_same_file(tmp_path, path):
    p = _project(tmp_path, purpose=PURPOSE)
    new = yaml.safe_dump({"active_diamonds": [{"id": "l3-x", "scale": "L3", "phase": "discover"}]})
    assert sl.new_diamond_violations(p, _write(new, path=str(tmp_path / path))), path


def test_hook_judges_a_rescaled_or_revived_or_scaleless_diamond(tmp_path):
    old = [{"id": "d1", "scale": "L0", "phase": "discover"}]
    p = _project(tmp_path, purpose=PURPOSE, diamonds=old)
    rescaled = yaml.safe_dump({"active_diamonds": [{"id": "d1", "scale": "L3", "phase": "discover"}]})
    assert sl.new_diamond_violations(p, _write(rescaled)), "rescaling opens a new scale"
    scaleless = yaml.safe_dump({"active_diamonds": [*old, {"id": "d2", "phase": "discover"}]})
    assert sl.new_diamond_violations(p, _write(scaleless)), "a diamond with no scale holds nothing"


def test_hook_refuses_an_unparseable_proposal_and_judges_a_repair(tmp_path, monkeypatch, capsys):
    p = _project(tmp_path, purpose=PURPOSE)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(_write("a: [broken"))))
    assert sl.main(["--project-dir", p, "--hook"]) == 2
    assert "does not parse" in capsys.readouterr().err
    (tmp_path / ".claude/diamonds/active.yml").write_text("a: [broken")
    repair = yaml.safe_dump({"active_diamonds": [{"id": "l3-x", "scale": "L3", "phase": "discover"}]})
    assert sl.new_diamond_violations(p, _write(repair)), "a repair write is judged whole"


def test_hook_reads_a_move_onto_the_diamonds_file(tmp_path):
    p = _project(tmp_path, purpose=PURPOSE)
    staged = tmp_path / "staged.yml"
    staged.write_text(yaml.safe_dump({"active_diamonds": [{"id": "l3-x", "scale": "L3"}]}))
    move = {"tool_name": "mcp__filesystem__move_file",
            "tool_input": {"source": str(staged),
                           "destination": str(tmp_path / ".claude/diamonds/active.yml")}}
    assert sl.new_diamond_violations(p, move)
