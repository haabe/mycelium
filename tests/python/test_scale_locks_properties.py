"""Properties of the entry locks that no single example pins (E2E study, 2026-09-26).

The walkthrough proves the ladder on one path; metamorphic checks prove the verdicts do not depend on
things that should not matter. Reordering the diamonds, the opportunities or their solutions, or
adding a parked diamond elsewhere, must never change whether a scale may open or which diamonds hold.
A lock whose verdict moves with list order would pass the walkthrough and fail a real project whose
agent happened to write its YAML in another order.
"""
from __future__ import annotations

import random

import yaml
from test_scale_locks import (
    OUTCOME,
    PURPOSE,
    _delivered,
    _l3,
    _project,
    _sol_opps,
    sl,
)

TRIALS = 20


def _verdicts(p: str) -> tuple:
    rows = sl.report(p)[0]
    return (tuple(sorted((r[0], r[1], tuple(r[2]), r[3]) for r in rows)),
            tuple(sl.can_open(p, "L4", parent="l3-a")),
            tuple(sl.can_open(p, "L5", parent="l4-a")))


def _world(tmp_path, delivered: bool):
    other = {"id": "opp-002", "name": "Rota changes are lost", "status": "open",
             "evidence": {"source_class": "external_human", "evidence_type": "anecdotal"},
             "solutions": [{"id": "sol-009", "name": "A change log"}]}
    opps = _sol_opps(riskiest_assumption={"statement": "a backup approves",
                                          "cheapest_test": "concierge for two weeks at Harbour",
                                          "verdict": "validated"})
    opps["opportunities"].append(other)
    opps["opportunities"][0]["solutions"].append({"id": "sol-002", "name": "A second approver"})
    l3 = _delivered() if delivered else _l3("anecdotal")
    l4 = {"id": "l4-a", "scale": "L4", "phase": "deliver", "parent": "l3-a",
          "launch_data": {"usage": "3 sites used it daily"}}
    return opps, [l3, l4]


def _shuffled(tmp_path, opps: dict, diamonds: list[dict], rng: random.Random, n: int) -> str:
    opps = yaml.safe_load(yaml.safe_dump(opps))
    rng.shuffle(opps["opportunities"])
    for o in opps["opportunities"]:
        rng.shuffle(o.get("solutions") or [])
    ds = list(diamonds)
    rng.shuffle(ds)
    return _project(tmp_path / f"t{n}", purpose=PURPOSE, opps={**OUTCOME, **opps}, diamonds=ds)


def test_lock_verdicts_do_not_depend_on_list_order(tmp_path):
    for delivered in (True, False):
        opps, diamonds = _world(tmp_path, delivered)
        ref = _verdicts(_project(tmp_path / f"ref{delivered}", purpose=PURPOSE,
                                 opps={**OUTCOME, **opps}, diamonds=diamonds))
        rng = random.Random(20260926)  # noqa: S311 - a seeded order for fixtures, not a secret
        for n in range(TRIALS):
            assert _verdicts(_shuffled(tmp_path / str(delivered), opps, diamonds, rng, n)) == ref, n


def test_a_parked_diamond_elsewhere_changes_no_verdict(tmp_path):
    opps, diamonds = _world(tmp_path, delivered=True)
    ref = _verdicts(_project(tmp_path / "ref", purpose=PURPOSE, opps={**OUTCOME, **opps},
                             diamonds=diamonds))
    parked = {"id": "l3-parked", "scale": "L3", "phase": "define", "object_ref": "sol-009",
              "status": "parked"}
    got = _verdicts(_project(tmp_path / "more", purpose=PURPOSE, opps={**OUTCOME, **opps},
                             diamonds=[*diamonds, parked]))
    assert (got[1], got[2]) == (ref[1], ref[2]), "the L4 and L5 locks of l3-a/l4-a do not move"


def test_the_properties_can_fail(tmp_path):
    """Control: the same comparison sees a change that DOES matter (the learning delivery)."""
    opps, delivered = _world(tmp_path, delivered=True)
    _, undelivered = _world(tmp_path, delivered=False)
    a = _verdicts(_project(tmp_path / "a", purpose=PURPOSE, opps={**OUTCOME, **opps}, diamonds=delivered))
    b = _verdicts(_project(tmp_path / "b", purpose=PURPOSE, opps={**OUTCOME, **opps}, diamonds=undelivered))
    assert a[1] != b[1]
