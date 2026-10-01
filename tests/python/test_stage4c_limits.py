"""The limits and the re-target (v0.302.0, phase migration stage 4c; DL-1367 R2, R3).

One live L2 per outcome and one open L3 per target, checked when a diamond opens. An L2 that
re-targets closes the L3 on its old target in the same write, as `retargeted`. An L3 ended by its
state (killed, archived, retargeted) says how its learning delivery ended, as a completion does.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))
import scale_locks as sl

PURPOSE = {"why": "Swaps are approved in one place so nobody relays them by hand",
           "who": {"description": "Shift leads at cafes with 2-10 sites"}}
EVIDENCE = {"evidence_type": "anecdotal", "evidence_sources": ["founder story: three relays"]}
OPPS = {"desired_outcomes": [{"id": "out-a", "metric": "swaps approved without a call",
                              "north_star_input_ref": "swaps settled in the app"}],
        "opportunities": [{"id": f"opp-{n}", "status": "open", "rolls_up_to": "out-a",
                           "provenance": EVIDENCE, "solutions": [{"id": f"s{n}"}]}
                          for n in (1, 2)]}
TOP = [{"id": "l0", "scale": "L0", "phase": "define"},
       {"id": "l1", "scale": "L1", "phase": "develop", "object_ref": "lead with cafes"}]
L2 = {"id": "l2", "scale": "L2", "phase": "define", "parent": "l1", "object_ref": "out-a",
      "target": {"opportunity": "opp-1", "chosen_on": "2026-10-01"}}
L3 = {"id": "l3", "scale": "L3", "phase": "develop", "parent": "l2", "object_ref": "opp-1"}


def _root(tmp_path: Path, diamonds: list[dict]) -> str:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True)
    (c / "diamonds").mkdir(parents=True)
    for name, doc in {"purpose.yml": PURPOSE, "opportunities.yml": OPPS,
                      "north-star.yml": {"metric": {"name": "swaps settled per week"}},
                      "landscape.yml": {"components": [{"id": "c1", "name": "chat"}]}}.items():
        (c / "canvas" / name).write_text(yaml.safe_dump(doc))
    (c / "diamonds" / "active.yml").write_text(yaml.safe_dump({"active_diamonds": TOP + diamonds}))
    return str(tmp_path)


def _write(root: str, diamonds: list[dict]) -> list[str]:
    after = yaml.safe_dump({"active_diamonds": TOP + diamonds})
    before = (Path(root) / ".claude" / "diamonds" / "active.yml").read_text()
    return sl.violations_between(root, before, after)


def test_a_second_l2_on_the_same_outcome_is_refused(tmp_path):
    root = _root(tmp_path, [L2])
    out = _write(root, [L2, {**L2, "id": "l2b", "target": "opp-2"}])
    assert any("one L2 per outcome" in x and "out-a" in x for x in out), out


def test_a_second_l3_on_the_same_target_is_refused(tmp_path):
    root = _root(tmp_path, [L2, L3])
    out = _write(root, [L2, L3, {**L3, "id": "l3b", "phase": "discover"}])
    assert any("one L3 per target" in x for x in out), out
    control = _root(tmp_path / "c", [L2])
    assert not any("one L3 per target" in x
                   for x in _write(control, [L2, {**L3, "phase": "discover"}])), "the first opens"


def test_retargeting_closes_the_l3_on_the_old_target(tmp_path):
    root = _root(tmp_path, [L2, L3])
    moved = {**L2, "target": {"opportunity": "opp-2", "chosen_on": "2026-10-09"},
             "targets": [L2["target"]]}
    out = _write(root, [moved, L3])
    assert any("no longer targets" in x and "retargeted" in x for x in out), out
    assert not any("no longer targets" in x
                   for x in _write(root, [moved, {**L3, "state": "retargeted"}])), "closed with it"


def test_an_l3_ended_by_its_state_says_how_its_delivery_ended(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    delivering = {**L3, "phase": "deliver", "exposures": [{
        "recorded_at": "2026-10-01", "audience": "two shift leads", "until": "2026-11-01",
        "channel": "by hand"}]}
    root = _root(tmp_path, [L2, delivering])
    out = _write(root, [L2, {**delivering, "state": "killed"}])
    assert any("ends as `killed`" in x for x in out), out
    ended = {**delivering, "state": "killed", "exposures": [{
        **delivering["exposures"][0], "ended": {"how": "withdrawn", "on": "2026-10-02"}}]}
    assert not any("ends as" in x for x in _write(root, [L2, ended]))
    assert not any("ends as" in x for x in _write(root, [L2, {**delivering, "state": "parked"}])), \
        "parked is a pause"
