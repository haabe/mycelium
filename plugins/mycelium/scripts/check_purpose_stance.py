#!/usr/bin/env python3
"""check_purpose_stance.py — does a proposed sub-element contradict the product's own definition?

THE GAP THIS CLOSES (dogfood 2026-08-22/23). A project states a `why`, a `how` and a
`what`, and **nothing below ever checks a proposed sub-element against them**. Measured
in plugin 0.119.0: two scripts opened `purpose.yml` and neither read those fields; four
hooks checked whether the file EXISTED or had CHANGED; `theory-gates.md` named nine
theorists and not Sinek, whose model is the shape of the file. The founder's words: *"if
I can't trust that the outcome of the why/how/what is used to guide anything below, I
believe drifting from the goal is guaranteed."*

TWO EXAMPLES THAT BOUND THE DESIGN, both the founder's:
  * healthcare app — *why* users deserve care without anxiety about their data, *how* accessible and
    secure. A solution storing data unencrypted CONTRADICTS it.
  * microblog — *what* anonymous users post short emoji strings, *why* unknown. A solution requiring
    login CONTRADICTS it.

The second is why this cannot key off `ethical_boundaries` or a typed constraint field: anonymity is
not an ethical boundary, it is the `what`, and "because unknown reason" has no
category at all. **The
constraint is whatever the user wrote.** It also cannot key off those fields for a duller reason:
`/mycelium:start` populates only why/how/what, so anything else is absent in a fresh project.

WHAT THIS CHECKS, AND WHAT IT REFUSES TO CHECK. It never asks whether a solution
SERVES the purpose —
that is the judgement class third-party benchmarks measure frontier models at 39-77% on, and a
checker that accurate on its own subject is a second opinion wearing a gate's clothes. It asks
whether a stance was DECLARED, whether the declaration carries a reason, and whether a declared
contradiction was overridden by a human. **Silence is the failure being caught, not wrongness.**

WHAT IT READS. Two files: every solution in `opportunities.yml`, and every diamond in
`diamonds/active.yml`. **The diamond half was specified from day one and implemented in
0.123.0** — for one release the wiring doc said stances go on "solutions AND DIAMONDS
ENTERING DEVELOP OR DELIVER" while this script opened only the first file. `diamond-progress`
was already calling it `--strict` at exactly those transitions, so the gate ran, read the
solutions, found them clean and returned green **without ever opening `active.yml`**. A
BLOCK-tier check that cannot see the artifact it guards is the blind-green defect this
framework exists to catch, and it was sitting inside the checker.

THE THREE WAYS THIS COULD ROT, and the tests that stop them:

  1. IT FIRES ON PROJECTS THAT NEVER OPTED IN. Every project predating this field would drown in
     warnings for a defect it did not introduce. Absent `purpose_properties` means silence, always.
  2. IT ACCEPTS A QUALITY ADJECTIVE AS BINDING. Measured 2026-08-23 by blind subagent: "accessible
     and secure" yields NO checkable property, because every candidate solution
     claims to satisfy it.
     A binding property with nothing that could contradict it produces a stance field answered
     `preserves` by every solution forever — populated, green, and meaningless. That is this
     mechanism's own failure mode reintroduced at its entry point, so it is checked FIRST.
  3. AN AGENT CLEARS ITS OWN CONTRADICTION. Founder, deciding the override rule: *"I don't think an
     agent should override this."* Without a human actor on the override, an agent could declare a
     contradiction and clear it in the same run, and the mechanism nullifies itself while every
     record looks complete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

VERDICTS = ("preserves", "not_applicable", "contradicts")


def purpose_hash(purpose: dict) -> str:
    """Hash of the governing fields. A mismatch means every stance below is superseded.

    Normalised so that reformatting (indentation, list order in `how`) does not read as a change of
    intent, while any edit to the words does.
    """
    parts = [
        json.dumps(purpose.get(key), sort_keys=True, ensure_ascii=False, default=str)
        for key in ("why", "how", "what")
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _load(path: Path):
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError):
        return None  # parse failures belong to the fail-loud pass, not here


def _iter_solutions(opportunities: dict):
    """Every solution in the tree, with the opportunity that owns it."""
    for opp in opportunities.get("opportunities") or []:
        if not isinstance(opp, dict):
            continue
        for sol in opp.get("solutions") or []:
            if isinstance(sol, dict):
                yield opp.get("id", "<no id>"), sol


BLOCKING_PHASES = ("develop", "deliver")


def _iter_diamonds(diamonds: dict):
    """Every diamond in active.yml. Shape mirrors _iter_solutions deliberately."""
    for dm in diamonds.get("active_diamonds") or []:
        if isinstance(dm, dict):
            yield dm


def _diamond_stance_findings(diamonds_path: Path, binding: list[dict],
                             grandfathered: set,
                             diamond_id: str | None = None) -> tuple[list[str], list[str]]:
    """Diamonds, against every binding property. Returns (blocking, advisory).

    THE GAP THIS CLOSES (dogfood 2026-08-23). The wiring doc has said since the day this
    mechanism shipped that stances go on "solutions (`sol-*`) AND DIAMONDS ENTERING
    DEVELOP OR DELIVER", and named three firing points for them: 4 and 5 at the phase
    transitions (BLOCK) and 7 in the validator (WARN, never fail). Only the solution half
    was ever implemented. So `diamond-progress` was already invoking this script with
    `--strict` at exactly those transitions, and the script it called could not open
    `active.yml` — it read the solutions, found them clean, and returned green.
    **A BLOCK-tier gate that runs, passes, and cannot see the event it guards.** That is
    the blind-green defect this framework exists to catch, sitting inside the checker.

    Measured on the dogfood canvas the day it was found: 0 of 4 diamonds carried a stance,
    and none were grandfathered — the 53-entry exemption list is solution IDs only. The
    founder's question that surfaced it was whether an L1 outcome re-specified eight days
    BEFORE the current why/what still fits them. Nothing could answer it.

    TWO TIERS, AND THE SPLIT IS THE SPEC'S, NOT THIS FUNCTION'S:
      * BLOCKING — phase is Develop or Deliver. Firing points 4 and 5. This is where a
        thing becomes real, and where the doc says blocking is earned.
      * ADVISORY — any other phase, when the diamond carries a `definition_of_done`.
        Firing point 7, "WARN, never fail". A definition of done written against a
        superseded purpose is the drift this whole mechanism exists to surface, and it
        is readable long before the diamond transitions. It must never fail a build:
        downstream projects predate the field, same reasoning as every other WARN here.

    PARKED DIAMONDS ARE NEVER BLOCKING. A parked diamond is not transitioning, and this
    script is invoked as a whole-canvas sweep — so blocking on one would fail an unrelated
    diamond's transition for a diamond nobody is moving. It still reports advisory.

    NEITHER IS ANY DIAMOND EXCEPT THE ONE BEING MOVED, when `diamond_id` is given.
    Firing points 4 and 5 are transitions — "L2 -> L3", "L3 -> L4" — so the thing they
    block is THIS transition, not the canvas. Without the scope, moving a diamond out of
    Discover would fail on a DIFFERENT diamond's missing stance, which is collateral: the
    builder is told to stop for a reason that has nothing to do with the step they took.
    The doc's own warning against blocking too early ("turns exploration into paperwork,
    which is the L0 friction already recorded against this framework") applies exactly
    here. Every other diamond still reports, at the never-fail tier.
    """
    diamonds = _load(diamonds_path)
    if not isinstance(diamonds, dict):
        return [], []
    ids = [p.get("id") for p in binding]
    blocking: list[str] = []
    advisory: list[str] = []
    for dm in _iter_diamonds(diamonds):
        did = dm.get("id", "<no id>")
        if did in grandfathered:
            continue
        phase = str(dm.get("phase") or "").strip().lower()
        parked = str(dm.get("state") or "").strip().lower() == "parked"
        is_blocking = (
            phase in BLOCKING_PHASES
            and not parked
            and (diamond_id is None or did == diamond_id)
        )
        out = blocking if is_blocking else advisory
        stance = dm.get("purpose_stance")
        if not isinstance(stance, dict):
            if not is_blocking and not dm.get("definition_of_done"):
                continue  # nothing to drift yet: no bar written, not in a real phase
            where = f"phase {phase or '<unset>'}{', parked' if parked else ''}"
            out.append(
                f"{did} (diamond, {where}): no purpose_stance against {len(ids)} binding "
                f"propert{'y' if len(ids) == 1 else 'ies'} "
                f"({', '.join(str(i) for i in ids)}). Silence is the finding — the "
                f"diamond's definition of done may be fine, but nothing says so."
            )
            continue
        for pid in ids:
            out.extend(_one_stance(did, pid, stance.get(pid)))
    return blocking, advisory


def _property_findings(pp: dict) -> tuple[list[str], list[dict]]:
    """Findings about the property list itself, and the binding subset.

    Checked FIRST because a binding property nothing can contradict is worse than no
    property at all: it produces a stance answered `preserves` by every solution
    forever. Measured 2026-08-23 by blind subagent — "accessible and secure" yields no
    checkable property, because every candidate solution claims to satisfy it.
    """
    out: list[str] = []
    binding: list[dict] = []
    for prop in pp.get("properties") or []:
        if not isinstance(prop, dict) or not prop.get("binding"):
            continue
        binding.append(prop)
        if not prop.get("contradicted_by") and not prop.get("aspiration_reason"):
            out.append(
                f"purpose_properties {prop.get('id', '<no id>')} "
                f"({prop.get('property')!r}): marked binding with nothing that could "
                f"contradict it. Quality adjectives ('secure', 'accessible') yield no "
                f"checkable property — every solution claims to satisfy them. Name what "
                f"a violation looks like, or record it as an aspiration."
            )
    return out, binding


def _list_findings(pp: dict, purpose: dict) -> list[str]:
    """Staleness and confirmation: the anti-drift half, and it needs no judgement."""
    out: list[str] = []
    recorded = pp.get("derived_from_hash")
    if recorded and recorded != purpose_hash(purpose):
        out.append(
            "purpose_properties: derived_from_hash does not match the current "
            "why/how/what. The list was derived from a superseded purpose, so every "
            "stance below it is superseded too. Re-derive with "
            "/mycelium:purpose-properties before trusting any stance."
        )
    if pp.get("confirmed_by") != "human":
        out.append(
            "purpose_properties: confirmed_by is not 'human'. Extraction is "
            "agent-proposed and human-confirmed by design — an unconfirmed list is the "
            "framework's own words standing in for the builder's."
        )
    return out


def _one_stance(sid: str, pid: str, entry) -> list[str]:
    """Findings for a single property's stance on a single solution."""
    if entry is None:
        return [f"{sid}: purpose_stance says nothing about {pid}."]
    if not isinstance(entry, dict):
        return [f"{sid}: purpose_stance[{pid}] is not an object with a verdict and note."]
    verdict = entry.get("verdict")
    if verdict not in VERDICTS:
        return [f"{sid}: purpose_stance[{pid}] verdict {verdict!r} is not one of {VERDICTS}."]
    out = []
    if not entry.get("note"):
        out.append(
            f"{sid}: purpose_stance[{pid}] is {verdict!r} with no note. A null must be a "
            f"claim with an author, including 'not_applicable' — otherwise the field "
            f"fills with whatever makes the record look complete."
        )
    if verdict == "contradicts":
        override = entry.get("override")
        if not isinstance(override, dict) or not override.get("human"):
            out.append(
                f"{sid}: purpose_stance[{pid}] declares a CONTRADICTION with no human "
                f"override. An agent may not clear this. Record who accepted the "
                f"trade-off and the decision-log entry carrying it, or change the solution."
            )
    return out


def _stance_findings(canvas_dir: Path, binding: list[dict],
                     grandfathered: set) -> list[str]:
    """Every solution, against every binding property. Silence is the finding.

    EXCEPT for solutions that existed when the property list was derived. A solution
    written before the properties existed could not have declared a stance against
    them, and flagging it says nothing about the work — it says the project adopted
    the mechanism. Measured on the dogfood canvas 2026-08-23: retrofitting there would
    have produced 53 solutions x 8 binding properties = 424 findings on day one, on the
    only project then able to adopt. A check that floods on adoption is one nobody
    adopts.

    The exemption is an explicit recorded LIST, not a date comparison: only 10 of those
    53 solutions carried any date at all, so an inference would have silently exempted
    the wrong 43.
    """
    opportunities = _load(canvas_dir / "opportunities.yml")
    if not isinstance(opportunities, dict):
        return []
    ids = [p.get("id") for p in binding]
    out: list[str] = []
    for opp_id, sol in _iter_solutions(opportunities):
        sid = sol.get("id", "<no id>")
        if sid in grandfathered:
            continue
        stance = sol.get("purpose_stance")
        if not isinstance(stance, dict):
            out.append(
                f"{sid} (under {opp_id}): no purpose_stance against {len(ids)} binding "
                f"propert{'y' if len(ids) == 1 else 'ies'} "
                f"({', '.join(str(i) for i in ids)}). Silence is the finding — the "
                f"solution may be fine, but nothing says so."
            )
            continue
        for pid in ids:
            out.extend(_one_stance(sid, pid, stance.get(pid)))
    return out


def default_diamonds_path(canvas_dir: Path) -> Path:
    """`.claude/canvas` -> `.claude/diamonds/active.yml`, the layout /mycelium:setup creates."""
    return canvas_dir.parent / "diamonds" / "active.yml"


def purpose_stance_findings(canvas_dir: Path, diamonds_file: Path | None = None,
                            include_advisory: bool = True,
                            diamond_id: str | None = None) -> list[str]:
    """Return findings. Empty means nothing to report OR the project never opted in.

    `include_advisory=False` drops the never-fail tier (firing point 7) so a caller in
    --strict mode can block on 4 and 5 alone. The validator keeps the default and treats
    everything as WARN, which is the contract it already had.
    """
    purpose_path = canvas_dir / "purpose.yml"
    if not purpose_path.exists():
        return []
    purpose = _load(purpose_path)
    if not isinstance(purpose, dict):
        return []

    pp = purpose.get("purpose_properties")
    if not isinstance(pp, dict) or not pp.get("properties"):
        return []  # ADOPTION PATH: never opted in, stay silent. See rot-mode 1.

    out, binding = _property_findings(pp)
    out.extend(_list_findings(pp, purpose))
    if binding:
        grandfathered = set(pp.get("grandfathered") or [])
        out.extend(_stance_findings(canvas_dir, binding, grandfathered))
        dpath = diamonds_file or default_diamonds_path(canvas_dir)
        blocking, advisory = _diamond_stance_findings(
            dpath, binding, grandfathered, diamond_id)
        out.extend(blocking)
        if include_advisory:
            out.extend(advisory)
    return out


def _grandfathered_count(canvas_dir: Path) -> int:
    """How many solutions are exempt. Reported every run, never silently."""
    purpose = _load(canvas_dir / "purpose.yml")
    if not isinstance(purpose, dict):
        return 0
    pp = purpose.get("purpose_properties")
    if not isinstance(pp, dict):
        return 0
    return len(pp.get("grandfathered") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    ap.add_argument(
        "--diamonds-file",
        default=None,
        help="active.yml to read diamonds from. Defaults to <canvas-dir>/../diamonds/active.yml.",
    )
    ap.add_argument(
        "--diamond-id",
        default=None,
        help="the diamond being transitioned. Scopes the BLOCK tier to it, so a "
        "transition is never failed by a different diamond's missing stance. Omit for a "
        "whole-canvas sweep, where every Develop/Deliver diamond is blocking-eligible.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on findings. Use at a transition (L2->L3, L3->L4); advisory mode "
        "is for the validator, where a hard failure would break older projects.",
    )
    args = ap.parse_args()

    canvas_dir = Path(args.canvas_dir)
    diamonds_file = Path(args.diamonds_file) if args.diamonds_file else None
    findings = purpose_stance_findings(canvas_dir, diamonds_file,
                                       diamond_id=args.diamond_id)
    # The exit code follows the SPEC'S OWN TIERS, not the printed list: firing point 7 is
    # "WARN, never fail", so an advisory finding is shown and never blocks. Recomputing
    # without it is what keeps a coverage warning from becoming a surprise CI failure.
    blocking = (purpose_stance_findings(canvas_dir, diamonds_file, include_advisory=False,
                                        diamond_id=args.diamond_id)
                if args.strict else findings)
    n_exempt = _grandfathered_count(canvas_dir)
    if n_exempt:
        # Said out loud every run: an exemption nobody sees is an exemption that
        # quietly becomes the permanent state of the canvas.
        print(f"purpose-stance: {n_exempt} solution(s) grandfathered at derivation "
              f"— not checked, and never will be until someone backfills them")
    if not findings:
        print("purpose-stance: OK (or not in use)")
        return 0
    blocking_set = set(blocking)
    for f in findings:
        tier = "FAIL" if (args.strict and f in blocking_set) else "WARN"
        print(f"  {tier}: {f}")
    return 1 if (args.strict and blocking) else 0


if __name__ == "__main__":
    sys.exit(main())
