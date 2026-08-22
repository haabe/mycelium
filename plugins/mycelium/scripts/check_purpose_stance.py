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
            "stance below it is superseded too. Re-derive before trusting any stance."
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


def _stance_findings(canvas_dir: Path, binding: list[dict]) -> list[str]:
    """Every solution, against every binding property. Silence is the finding."""
    opportunities = _load(canvas_dir / "opportunities.yml")
    if not isinstance(opportunities, dict):
        return []
    ids = [p.get("id") for p in binding]
    out: list[str] = []
    for opp_id, sol in _iter_solutions(opportunities):
        sid = sol.get("id", "<no id>")
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


def purpose_stance_findings(canvas_dir: Path) -> list[str]:
    """Return findings. Empty means nothing to report OR the project never opted in."""
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
        out.extend(_stance_findings(canvas_dir, binding))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on findings. Use at a transition (L2->L3, L3->L4); advisory mode "
        "is for the validator, where a hard failure would break older projects.",
    )
    args = ap.parse_args()

    findings = purpose_stance_findings(Path(args.canvas_dir))
    if not findings:
        print("purpose-stance: OK (or not in use)")
        return 0
    for f in findings:
        print(f"  {'FAIL' if args.strict else 'WARN'}: {f}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
