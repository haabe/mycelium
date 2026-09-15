#!/usr/bin/env python3
"""Is each entry in the OST actually an OPPORTUNITY, or is it a maintenance ticket?

WHY THIS EXISTS. `validate_canvas.py` checks that the tree is WELL-CONNECTED: the root
exists, is named, is not duplicated, and every `rolls_up_to` resolves. Until 0.215.0 nothing
checked that a node is the right KIND of thing. A framework-maintenance finding with a
correctly resolving pointer passed every gate the framework has.

MEASURED 2026-09-02 on the dogfood canvas: 52 of 66 entries had accumulated under an
`off_north_star` root over several months. Mean opportunity-shape 0.88 of 3; 25% named a
human subject. Not one gate fired in that whole period. The only thing that ever noticed was
the founder looking at a rendered tree and saying it felt wrong. THE HUMAN WAS THE CHECK, and
that is the defect this closes; not the 52 entries, which are a symptom.

Torres's rule is the standard: "phrase as user needs, not solutions -- 'Users need to know
their payment succeeded'."

WHAT THIS IS NOT, AND THE DISTINCTION IS LOAD-BEARING. This is a LEXICAL proxy, and the
dogfood project has measured lexical detectors as scoring poorly (the absence-claim guard
fired 29 times lifetime and caught none of four confirmed errors on its worst day). So it is
deliberately NOT a gate and MUST NOT become one: it does not block a write, and a low score is
not a verdict. It produces a TRIAGE LIST for a human to rule on, in batches. A lexical
detector used as a gate would relocate real opportunities out of the tree, which is worse
than the drift. `validate_canvas.py` carries one COVERAGE line from `summarise`, never a WARN.

THE PROTOTYPE KILLED ITS AUTHOR'S PROPOSAL BEFORE THE FOUNDER HAD TO. The agent had argued
the 39 low-shape framework entries should be evicted; the first run measured both roots at
47% scoring <=1, identical, so low shape justified evicting a third of the root treated as
the healthy control. After 34 names were rewritten as user needs (descriptions untouched):
framework mean 1.52 -> 2.02, adoption 1.87 -> 2.07, and all 14 residual entries were missing
the SOLUTION LEAF, the one marker rewording cannot touch.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

#: Torres need-language, matched against the NAME, case-insensitively.
NEED_PATTERNS = [
    r"\bneeds? to\b", r"\bis trying to\b", r"\bwants? to\b", r"\bTHE NEED\b",
    r"\bso (?:that )?they can\b", r"\bcannot \w+", r"\bcan't \w+", r"\bhas no way to\b",
    r"\bstruggles? to\b", r"\bunable to\b",
    # Same convention in a form the first list missed ("needs a surface" is "needs to have
    # a surface"); added 2026-09-02 as a false-negative fix, verified against opp-012.
    r"\bneeds? (?:a|an|the)\b",
]

#: A human subject: the entry is about a PERSON, not a mechanism.
SUBJECT_PATTERNS = [
    r"\ba builder\b", r"\ba reader\b", r"\ban evaluator\b", r"\busers?\b", r"\bsomeone\b",
    r"\bthe maintainer\b", r"\ba new user\b", r"\ba founder\b", r"\ba developer\b",
    r"\ba team\b", r"\ban adopter\b", r"\bpeople\b", r"\ba stranger\b", r"\ba newcomer\b",
    r"\ba maintainer\b", r"\bbuilders\b", r"\ba skill author\b", r"\ban author\b",
]
LOW = 1
NAME_WIDTH = 58


def score(opp: dict) -> tuple[int, list[str]]:
    """0-3, plus which markers were absent.

    THE PHRASING MARKERS ARE SCORED ON THE NAME ALONE, AND THIS WAS A CORRECTION. Against
    name + description the human-subject marker matched 72 of 73 (saturated, discriminating
    nothing) because descriptions mention people even when the entry is named after a
    mechanism. The name is the node: `ost-render` labels each node with it and a reader of
    the tree sees nothing else. The solution leaf is an entry-level fact, not a phrasing one.
    """
    text = str(opp.get("name", ""))
    missing = []
    n = 0
    if any(re.search(p, text, re.IGNORECASE) for p in NEED_PATTERNS):
        n += 1
    else:
        missing.append("no need-language")
    if any(re.search(p, text, re.IGNORECASE) for p in SUBJECT_PATTERNS):
        n += 1
    else:
        missing.append("no human subject")
    if opp.get("solutions"):
        n += 1
    else:
        missing.append("no solution leaf")
    return n, missing


def by_root(path: Path) -> dict[str, list[tuple[str, str, int, list[str]]]]:
    data = yaml.safe_load(path.read_text()) or {}
    opps = data.get("opportunities") if isinstance(data, dict) else None
    out: dict[str, list] = {}
    for opp in opps or []:
        if not isinstance(opp, dict):
            continue
        s, missing = score(opp)
        out.setdefault(str(opp.get("rolls_up_to") or "(untagged)"), []).append(
            (str(opp.get("id", "?")), str(opp.get("name", "?")), s, missing))
    return out


def summarise(path: Path) -> str:
    """One line for the validator's COVERAGE tier; empty when there are no opportunities."""
    roots = by_root(path)
    total = sum(len(r) for r in roots.values())
    if not total:
        return ""
    parts = []
    for rt in sorted(roots):
        rows = roots[rt]
        low = sum(1 for r in rows if r[2] <= LOW)
        mean = sum(r[2] for r in rows) / len(rows)
        parts.append(f"{rt}: n={len(rows)} mean={mean:.2f} <=1: {low}")
    return ("; ".join(parts)
            + " (a low score is a question, not a verdict; check_opportunity_shape.py)")


def report(path: Path) -> int:
    roots = by_root(path)
    total = sum(len(r) for r in roots.values())
    print("Opportunity-shape (is each OST node a user need, or a maintenance ticket?)")
    print("=" * 78)
    if not total:
        print("  NOT A PASS: opportunities.yml holds no opportunities, so nothing was scored.")
        return 1
    print("Markers: need-language | human subject | has a solution leaf.  Score 0-3.\n")
    low_total = 0
    for rt in sorted(roots):
        rows = sorted(roots[rt], key=lambda r: (r[2], r[0]))
        mean = sum(r[2] for r in rows) / len(rows)
        low = [r for r in rows if r[2] <= LOW]
        low_total += len(low)
        print(f"  root {rt!r}: n={len(rows)}  mean={mean:.2f}  "
              f"scoring <=1: {len(low)} ({100 * len(low) / len(rows):.0f}%)")
    print(f"\n  {low_total} of {total} entries score <=1 and are candidates for triage.\n")
    for rt in sorted(roots):
        rows = [r for r in sorted(roots[rt], key=lambda r: (r[2], r[0])) if r[2] <= LOW]
        if not rows:
            continue
        print(f"  --- root {rt!r} ---")
        for oid, name, s, missing in rows:
            print(f"  [{s}/3]  {oid}  {name[:NAME_WIDTH]}")
            print(f"          {', '.join(missing)}")
        print()
    print("A LOW SCORE IS NOT A VERDICT. This is a lexical proxy, and lexical detectors")
    print("score poorly in this project's own measurements. Each row is a question for a")
    print("human: is this a user need (rewrite it as one), or is it framework maintenance")
    print("(it belongs in harness/upstream-candidates.yml)? Rule in batches, never in bulk.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    args = ap.parse_args()
    path = Path(args.canvas_dir) / "opportunities.yml"
    if not path.exists():
        print(f"opportunity-shape: {path} not found", file=sys.stderr)
        return 2
    return report(path)


if __name__ == "__main__":
    raise SystemExit(main())
