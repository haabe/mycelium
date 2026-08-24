#!/usr/bin/env python3
"""check_leaf_lifecycle.py — a shipped solution leaf must carry the score it was chosen on.

THE LEAF-SIDE HALF OF CHECK 38, AND THE GAP BETWEEN THEM IS WHERE A REAL DEFECT LIVED.

    Check 38 requires non-zero ICE on a product-leaf CYCLE RECORD.
    Nothing required it on the LEAF.

So a leaf could ship with the selection gate bypassed, and the only consequence
was silence — because in a tree whose opportunities all roll up to the framework,
no product-leaf cycle could ever open to trip Check 38 anyway.

FOUND IN DOGFOOD 2026-08-06 (opp-036), after the founder pushed back on a claim
that "0 product-leaf cycles" was purely structural. Seven shipped leaves carried
no ICE at all, four of them documenting their own drift in their own status text:

    sol-023a  status: SHIPPED-BEFORE-SCORING
    sol-008a  "shipped — was `open` for two months after shipping"
    sol-009b  "verified in code, not inferred from the canvas"
    sol-023b  "shipped-in-a-different-form"

WHY IT MATTERS LATER RATHER THAN NOW — the structural zero MASKS the wiring zero.
If the leaf lifecycle does not fire for framework leaves today, it will not fire
for product leaves tomorrow, and on that day the bypass starts eating the
ICE-calibration dimension that product-leaf cycles exist to feed. Dormant paths
need just-in-time-placed teeth.

WHY THIS IS A SCRIPT AND NOT A validate-template.sh CHECK — it was first written
as Check 54 and that was WRONG. `validate-template.sh` runs in the FRAMEWORK repo,
whose canvas has no shipped leaves; the leaves live in CONSUMER canvases. The
check would have run forever against the one tree where its finding cannot occur,
reporting "nothing to audit" and reading green. That is the built-not-wired class,
committed inside the fix for a wiring failure. Shipping it as a plugin script means
it reaches the canvas that actually has the data.

THE SECOND HALF, ADDED 2026-08-24: FOUR RISKS PAST A DECISION POINT.
    `theory-gates.md` says each solution leaf "should have a `four_risks` block", and
    `/ice-score` states the harder rule: "ICE without Four Risks is ungrounded estimation."
    The 2026-08-23 rule census counted 19 of 54 leaves carrying one and read that as a
    sprawling backlog. Recounted 2026-08-24, split by status, it is three different things:
    24 still `candidate` (pre-decision, where the rule says SHOULD and a filled block on a
    leaf that may never be pursued is the filler trap), 4 closed (nothing to assess), and
    **7 that passed a decision point with no risk evaluation at all.** Those 7 are the finding,
    and counting the population hid them.

    WHY THE TWO HALVES USE DIFFERENT POPULATIONS, stated because it looks like an
    inconsistency: the ICE half keys on SHIPPED because ICE is the precondition for a
    product-leaf cycle (Check 38). The four-risks half keys on SHIPPED **or VALIDATED**
    because the rule it enforces is about passing a decision, and `validated` is a decision.
    Founder ruling 2026-08-24. Widening the ICE half to match was considered and refused —
    that would change a shipped mechanism's behaviour under cover of adding a new one.

    AND IT DOES NOT ASK FOR A BACKFILL. Founder ruling, same day: flag, do not backfill.
    Row 1 of the census says "no scoring without risk evaluation FIRST"; a block written
    today cannot restore the sequence, it only makes a past decision look compliant. Same
    objection this project already accepted for the fifteen empty cycle records. **The flag
    is the honest state, and it is advisory.**

DELIBERATELY NARROW
    It asserts ONE mechanical thing: a leaf claiming shipped carries the score its
    selection was supposed to rest on. It does NOT try to detect a leaf that shipped
    without its status being updated — that needs fuzzy cross-referencing against a
    changelog, and a guesser that got it wrong would corrupt the canvas it exists to
    protect. `sol-008a` sat wrong for two months and this check would not have caught
    it. Named here so the gap is out of scope rather than silently unhandled.

ESCAPE HATCH
    An `ice_exempt:` field with a reason satisfies the check. A leaf can legitimately
    ship unscored — emergent, trivial, or forced by circumstance. What it cannot do is
    ship unscored SILENTLY. The exemption is a sentence someone had to write.

ABSENT-INPUT DISCIPLINE (anti-pattern #9)
    - No opportunities.yml            -> exit 0, SKIP. Nothing to audit.
    - Unparseable                     -> exit 2, LOUD. Malformed must not read as empty.
    - Parses, no decision-point leaves -> exit 0 with `no-decision-point-leaves`, which
      is reported as N/A rather than as a pass over a population. "Nothing shipped yet"
      and "everything shipped is scored" are different facts.

Usage:
    check_leaf_lifecycle.py [--project-dir DIR] [--json]

Exit codes:
    0 — every shipped leaf carries ICE, and every decision-point leaf carries four_risks
        (or a recorded exemption for either; or nothing to audit)
    1 — a shipped leaf carries neither ICE nor an exemption, OR a decision-point leaf
        carries neither four_risks nor an exemption
    2 — argument/input error
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is framework-wide
    print("check_leaf_lifecycle: PyYAML is required", file=sys.stderr)
    sys.exit(2)

# Shipped-variants observed in the wild. Substring match on purpose: the canvas
# carries `shipped`, `partially_shipped`, `shipped-in-a-different-form` and
# `SHIPPED-BEFORE-SCORING`, and an exact-match list would silently miss the next
# variant someone invents — which is how this class of gap opens in the first place.
SHIPPED_MARKER = "shipped"

# Decision-point statuses for the FOUR RISKS half. Shipped-variants plus `validated`:
# a validated leaf passed a decision, which is what the rule is about. `candidate`,
# `proposed` and `open` are deliberately absent — pre-decision, and the rule says SHOULD.
# `discarded` / `rejected_*` are absent too: nothing was invested, so there is nothing a
# risk assessment would have protected. Founder ruling 2026-08-24.
DECISION_POINT_EXTRA = ("validated",)


def _is_decision_point(status: str) -> bool:
    low = status.lower()
    return SHIPPED_MARKER in low or any(m in low for m in DECISION_POINT_EXTRA)


def _load_opportunities(project_dir: Path):
    """Return the opportunity list, or None when the canvas is absent."""
    path = project_dir / ".claude" / "canvas" / "opportunities.yml"
    if not path.is_file():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"opportunities.yml is not parseable: {exc}") from exc
    if not isinstance(doc, dict):
        raise TypeError("opportunities.yml did not parse to a mapping")
    opps = doc.get("opportunities") or doc.get("opportunity_tree") or []
    if not isinstance(opps, list):
        raise TypeError("opportunities.yml#opportunities is not a list")
    return opps


class _Tally:
    """One half's running counts. Extracted so `audit` stays under the complexity
    policy after the second half landed — two identical accumulate-and-branch blocks
    inline is what pushed it over."""

    def __init__(self):
        self.violations, self.checked, self.exempted = [], 0, 0

    def add(self, verdict, fail_token, leaf, opp):
        if verdict is None:
            return
        self.checked += 1
        if verdict == "exempt":
            self.exempted += 1
        elif verdict == fail_token:
            self.violations.append({
                "id": str(leaf.get("id", "<no-id>")),
                "status": str(leaf.get("status", "")),
                "opportunity": str(opp.get("id", "<no-id>")),
            })


class LeafAudit(NamedTuple):
    """Both halves. Named rather than a 6-tuple so a caller cannot swap two counts."""
    ice_violations: list
    ice_checked: int
    ice_exempted: int
    fr_violations: list
    fr_checked: int
    fr_exempted: int


def audit(project_dir: Path):
    """Return (violations, checked, exempted). Raises on unparseable input."""
    opps = _load_opportunities(project_dir)
    if opps is None:
        return None

    ice, fr = _Tally(), _Tally()
    for opp in opps:
        if not isinstance(opp, dict):
            continue
        for leaf in opp.get("solutions") or []:
            ice.add(_classify(leaf), "unscored", leaf, opp)
            fr.add(_classify_four_risks(leaf), "unassessed", leaf, opp)
    return LeafAudit(ice.violations, ice.checked, ice.exempted,
                     fr.violations, fr.checked, fr.exempted)


def _classify_four_risks(leaf):
    """None if not past a decision point, else 'exempt' | 'assessed' | 'unassessed'.

    An empty `four_risks:` counts as UNASSESSED, not as present. A key with nothing
    under it is the filler trap the census exists to catch, and treating it as a pass
    would make this check certify the exact shape it was written to find.
    """
    if not isinstance(leaf, dict):
        return None
    if not _is_decision_point(str(leaf.get("status", ""))):
        return None
    if leaf.get("four_risks_exempt"):
        return "exempt"
    fr = leaf.get("four_risks")
    if isinstance(fr, dict) and any(str(v).strip() for v in fr.values()):
        return "assessed"
    return "unassessed"


def _classify(leaf):
    """None if not a shipped leaf, else 'exempt' | 'scored' | 'unscored'."""
    if not isinstance(leaf, dict):
        return None
    if SHIPPED_MARKER not in str(leaf.get("status", "")).lower():
        return None
    if leaf.get("ice_exempt"):
        return "exempt"
    ice = leaf.get("ice_score")
    total = ice.get("total", 0) if isinstance(ice, dict) else 0
    try:
        total_i = int(total or 0)
    except (TypeError, ValueError):
        total_i = 0
    return "scored" if total_i else "unscored"


def _report_ice(violations, checked, exempted):
    """Human-readable ICE half. Extracted from main() when the second half landed."""
    if violations:
        print(
            f"check_leaf_lifecycle: FAIL — {len(violations)} of {checked} shipped "
            f"leaf/leaves carry no ICE and no exemption."
        )
        for v in violations:
            print(f"    {v['id']:<12} status={v['status']!r}  (under {v['opportunity']})")
        print(
            "  A leaf's ICE is the prediction its selection rested on, and it is the\n"
            "  precondition for a product-leaf cycle (Check 38). Either backfill via\n"
            "  /mycelium:ice-score, or add\n"
            "  `ice_exempt:` with a reason. A leaf may ship unscored; it may not do so silently."
        )
    elif checked:
        print(
            f"check_leaf_lifecycle: OK — {checked} shipped leaf/leaves, "
            f"{exempted} exempted with a recorded reason."
        )


def _report_four_risks(violations, checked, exempted):
    """Human-readable four-risks half. The wording is deliberately anti-backfill."""
    if violations:
        print(
            f"check_leaf_lifecycle: FAIL — {len(violations)} of {checked} "
            f"decision-point leaf/leaves carry no four_risks and no exemption."
        )
        for v in violations:
            print(f"    {v['id']:<12} status={v['status']!r}  (under {v['opportunity']})")
        print(
            "  These passed a decision — shipped or validated — with no risk evaluation.\n"
            "  DO NOT BACKFILL TO SILENCE THIS. The rule is 'no scoring without risk\n"
            "  evaluation FIRST', and a block written now cannot restore that sequence;\n"
            "  it only makes a past decision look compliant. The flag IS the honest state.\n"
            "  Use `four_risks_exempt:` with a reason only when the leaf genuinely did not\n"
            "  need one. Leaves still `candidate` are not counted: the rule says SHOULD, and\n"
            "  a filled block on a leaf that may never be pursued is the filler trap."
        )
    elif checked:
        print(
            f"check_leaf_lifecycle: OK — {checked} decision-point leaf/leaves carry "
            f"four_risks, {exempted} exempted with a recorded reason."
        )


def _handle_nothing_to_audit(result, args, project_dir):
    """Exit code when there is nothing to audit, else None. Extracted from main()
    to keep it under the complexity policy once the second half landed.

    The two cases are DIFFERENT FACTS and must not collapse into one: a missing
    canvas is a broken precondition (exit 2), a canvas with no decision-point leaf
    is N/A (exit 0). "Nothing shipped yet" and "everything shipped is assessed" are
    not the same claim.
    """
    if result is None:
        # PRECONDITION FAILURE (exit 2), not a pass — the third time in one day
        # that check_empty_input_honesty.py caught a script of mine returning 0
        # over an empty tree. `opportunities.yml` is a required canvas file; its
        # absence means the tree is broken or the path is wrong, not that this
        # project opted out of having an OST.
        msg = (f"cannot audit: no .claude/canvas/opportunities.yml under {project_dir}. "
               f"That is a required canvas file, so its absence means a broken tree or a "
               f"wrong --project-dir. NOTHING WAS AUDITED — this is not a pass.")
        if args.json:
            print(json.dumps({"status": "precondition-failed", "reason": msg}))
        else:
            print(f"check_leaf_lifecycle: ERROR — {msg}", file=sys.stderr)
        return 2

    if result.ice_checked == 0 and result.fr_checked == 0:
        msg = ("no-decision-point-leaves — the tree has no leaf that has shipped or been "
               "validated. N/A, not a pass over a population.")
        print(json.dumps({"status": "n/a", "reason": msg}) if args.json
              else f"check_leaf_lifecycle: N/A — {msg}")
        return 0
    return None


def _emit_json(result, failed):
    """Machine-readable output.

    `violations` KEEPS MEANING THE ICE HALF. The session-start hook reads that key and
    prints an ICE sentence from its length; repurposing it would have made a
    four-risks-only finding render as "0 shipped leaves carry no ICE".
    """
    print(json.dumps({
        "status": "violations" if failed else "ok",
        "violations": result.ice_violations,
        "shipped_leaves": result.ice_checked,
        "exempted": result.ice_exempted,
        "four_risks_violations": result.fr_violations,
        "decision_point_leaves": result.fr_checked,
        "four_risks_exempted": result.fr_exempted,
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a shipped solution leaf carries no ICE and no recorded exemption."
    )
    parser.add_argument(
        "--project-dir", "--root", dest="project_dir", default=".",
        help="project root holding .claude/canvas (default: cwd)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"check_leaf_lifecycle: not a directory: {project_dir}", file=sys.stderr)
        return 2

    try:
        result = audit(project_dir)
    except (RuntimeError, TypeError) as exc:
        print(f"check_leaf_lifecycle: ERROR — {exc}", file=sys.stderr)
        return 2

    early = _handle_nothing_to_audit(result, args, project_dir)
    if early is not None:
        return early

    violations, checked, exempted = result.ice_violations, result.ice_checked, result.ice_exempted
    fr_violations, fr_checked, fr_exempted = (
        result.fr_violations, result.fr_checked, result.fr_exempted)

    failed = bool(violations or fr_violations)
    if args.json:
        _emit_json(result, failed)
    else:
        _report_ice(violations, checked, exempted)
        _report_four_risks(fr_violations, fr_checked, fr_exempted)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
