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
    - Parses but no shipped leaves    -> exit 0 with the `no-shipped-leaves` token, which
      is reported as N/A rather than as a pass over a population. "Nothing shipped yet"
      and "everything shipped is scored" are different facts.

Usage:
    check_leaf_lifecycle.py [--project-dir DIR] [--json]

Exit codes:
    0 — every shipped leaf carries ICE or a recorded exemption (or nothing to audit)
    1 — a shipped leaf carries neither
    2 — argument/input error
"""

import argparse
import json
import sys
from pathlib import Path

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


def audit(project_dir: Path):
    """Return (violations, checked, exempted). Raises on unparseable input."""
    opps = _load_opportunities(project_dir)
    if opps is None:
        return None, None, None

    violations, checked, exempted = [], 0, 0
    for opp in opps:
        if not isinstance(opp, dict):
            continue
        for leaf in opp.get("solutions") or []:
            verdict = _classify(leaf)
            if verdict is None:
                continue
            checked += 1
            if verdict == "exempt":
                exempted += 1
            elif verdict == "unscored":
                violations.append({
                    "id": str(leaf.get("id", "<no-id>")),
                    "status": str(leaf.get("status", "")),
                    "opportunity": str(opp.get("id", "<no-id>")),
                })
    return violations, checked, exempted


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
        violations, checked, exempted = audit(project_dir)
    except (RuntimeError, TypeError) as exc:
        print(f"check_leaf_lifecycle: ERROR — {exc}", file=sys.stderr)
        return 2

    if violations is None:
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

    if checked == 0:
        msg = ("no-shipped-leaves — the tree has no leaf with a shipped status. "
               "N/A, not a pass over a population.")
        print(json.dumps({"status": "n/a", "reason": msg}) if args.json
              else f"check_leaf_lifecycle: N/A — {msg}")
        return 0

    if args.json:
        print(json.dumps({
            "status": "violations" if violations else "ok",
            "violations": violations,
            "shipped_leaves": checked,
            "exempted": exempted,
        }, indent=2))
        return 1 if violations else 0

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
    else:
        print(
            f"check_leaf_lifecycle: OK — {checked} shipped leaf/leaves, "
            f"{exempted} exempted with a recorded reason."
        )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
