#!/usr/bin/env python3
"""Does a stored ICE aggregate match the algorithm the framework actually documents?

WHY THIS EXISTS (v0.238.0). `skills/ice-score/SKILL.md` says, and `docs/errata.md` A1 records as a
corrected shipped error: **ICE is the AVERAGE of Impact, Confidence and Ease**, not the product.
Ellis, `Hacking Growth`: *"those ratings are averaged to provide an aggregate score for each idea"*.
The erratum ends with an instruction to consumers -- *"re-check decisions that turned on them"* --
and nothing checked whether anyone did. Measured on the dogfood canvas the day this was written:
**14 of 14 verifiable aggregates were products, zero were averages**, three releases after the
erratum shipped. The correction was authored, released, and never reached the data it was about.

WHAT IT DOES NOT DO, AND THAT IS THE DESIGN. It does not rewrite canvas data and must never be made
to. Re-scoring a leaf whose decision already closed is the backfill this framework forbids elsewhere
in plain words (`check_leaf_lifecycle`: *"a block written now cannot restore that sequence; it only
makes a past decision look compliant"*). A product-shaped aggregate on a shipped leaf is the honest
record of how that call was actually made. So the corpus present at adoption is recorded as a
BASELINE and the check fails only on aggregates that appear or change afterwards -- the same
shape as `check_evidence_landing` and `check_fail_open`, and for the same reason: a red gate on
a number nobody may move trains its reader to ignore it.

WHY IT CANNOT JUST RECOMPUTE AND COMPARE. Real canvases carry the block in several shapes at once.
Measured on the dogfood canvas: SEVEN distinct shapes across 26 entries. The factor keys are
`impact/confidence/ease` or the abbreviated `i/c/e`; the aggregate is `total` or `score`; some
entries carry an aggregate with NO factors at all (nothing to verify against); and some are frozen
review artifacts marked `advisory: true` recording a *blind re-derivation* alongside the original,
deliberately under a different key. A checker that assumed one shape would report most of a real
corpus as broken, which is how a check gets switched off.

EXIT: 0 clean or baseline-only; 1 on a new or changed product-shaped aggregate; 2 on usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

#: Canvas files that carry ICE. Not every project has all of them.
CANVAS = ("opportunities.yml", "gist.yml", "archived-solutions.yml")

#: The block may live under either key. They are NOT synonyms on a real canvas -- one project uses
#: `ice_score` for the original score and `ice` for a later blind re-derivation -- so both are read
#: and neither is rewritten into the other.
ICE_KEYS = ("ice", "ice_score")

#: Factor names, long form and the abbreviated form found in practice.
FACTORS = (("impact", "confidence", "ease"), ("i", "c", "e"))

#: The aggregate itself.
AGG_KEYS = ("total", "score")

#: Aggregates equal to the product are what the erratum is about. Anything else -- a mean, a
#: weighted figure, a hand-set number -- is not this check's business; it only asserts that a value
#: which IS the product is not silently presented as an Ellis ICE.
TOLERANCE = 0.01


def _factors(block: dict):
    """Return (i, c, e) if the block carries a full factor triple, else None."""
    for keys in FACTORS:
        vals = [block.get(k) for k in keys]
        if all(isinstance(v, (int, float)) for v in vals):
            return tuple(float(v) for v in vals)
    return None


def _aggregate(block: dict):
    for k in AGG_KEYS:
        v = block.get(k)
        if isinstance(v, (int, float)):
            return float(v), k
    return None, None


def _walk(node, leaf_id, out, key_path=""):
    if isinstance(node, dict):
        leaf_id = node.get("id", leaf_id)
        for k, v in node.items():
            if k in ICE_KEYS and isinstance(v, dict):
                out.append((leaf_id, k, v))
            _walk(v, leaf_id, out, f"{key_path}.{k}")
    elif isinstance(node, list):
        for item in node:
            _walk(item, leaf_id, out, key_path)


def collect(root: Path):
    """Every ICE dict block on the canvas, as (file, leaf_id, key, block)."""
    found = []
    canvas_dir = root / ".claude" / "canvas"
    for name in CANVAS:
        path = canvas_dir / name
        if not path.exists():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        blocks: list = []
        _walk(doc, None, blocks)
        for leaf_id, key, block in blocks:
            found.append((name, leaf_id, key, block))
    return found


def classify(found):
    """Split into product-shaped, correct, and unverifiable."""
    products, correct, unverifiable = [], [], []
    for name, leaf_id, key, block in found:
        agg, _agg_key = _aggregate(block)
        fac = _factors(block)
        ident = f"{name}:{leaf_id}:{key}"
        if agg is None:
            continue  # no aggregate stored: nothing is being asserted
        if fac is None:
            unverifiable.append((ident, agg))
            continue
        i, c, e = fac
        mean = (i + c + e) / 3
        if abs(agg - i * c * e) < TOLERANCE and abs(agg - mean) >= TOLERANCE:
            products.append((ident, agg, round(mean, 2), block.get("advisory") is True))
        elif abs(agg - mean) < TOLERANCE:
            correct.append(ident)
        else:
            unverifiable.append((ident, agg))
    return products, correct, unverifiable


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current product-shaped set as the baseline")
    args = ap.parse_args(argv)

    root = Path(args.project_dir).resolve()
    if not (root / ".claude" / "canvas").is_dir():
        print(f"check_ice_aggregate: N/A — no .claude/canvas under {root}. "
              "Nothing was scanned, and that is not a pass.")
        return 0

    baseline_path = root / ".claude" / "evals" / "ice-aggregate-baseline.json"
    found = collect(root)
    products, correct, unverifiable = classify(found)
    product_ids = sorted(p[0] for p in products)

    if args.write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(
            {"_comment": "ICE aggregates that were product-shaped when check_ice_aggregate was "
                         "adopted. Errata A1: Ellis averages. These are NOT to be rewritten — a "
                         "product on a closed decision records how that call was actually made. "
                         "The list may shrink as leaves are legitimately re-scored; it must never "
                         "grow.",
             "product_shaped": product_ids}, indent=2) + "\n", encoding="utf-8")
        print(f"check_ice_aggregate: baseline written — {len(product_ids)} product-shaped "
              f"aggregate(s) recorded at adoption.")
        return 0

    base = []
    if baseline_path.exists():
        try:
            base = json.loads(baseline_path.read_text(encoding="utf-8")).get("product_shaped", [])
        except (json.JSONDecodeError, OSError):
            base = []

    new = [p for p in products if p[0] not in base]
    retired = [b for b in base if b not in product_ids]

    print("ICE aggregate check (errata A1: Ellis AVERAGES, never multiplies)")
    print("=" * 62)
    print(f"  {len(found)} ICE block(s); {len(correct)} correct, {len(products)} product-shaped, "
          f"{len(unverifiable)} unverifiable")

    if unverifiable:
        print("\n  UNVERIFIABLE — an aggregate is stored but the factors are not, so"
              " nothing can be recomputed. Not a failure and not a pass: the number"
              " cannot be checked at all.")
        for ident, agg in unverifiable:
            print(f"    {ident}  = {agg}")

    if base:
        print(f"\n  baseline: {len(base)} recorded at adoption, {len(retired)} since re-scored, "
              f"{len(base) - len(retired)} still carrying the pre-errata value.")
        print("  Those are NOT to be rewritten. A product on a closed decision is the honest"
              " record of how that call was made; re-scoring it now would only make it look"
              " compliant.")

    if new:
        print(f"\nFAIL: {len(new)} ICE aggregate(s) are the PRODUCT of their factors and are"
              " not in the baseline — so they were written or changed after this check"
              " was adopted.")
        for ident, agg, mean, advisory in new:
            flag = "  [advisory re-derivation]" if advisory else ""
            print(f"    {ident}: stored {agg}, Ellis mean would be {mean}{flag}")
        print("\nFix the SCORE, not the baseline. `/mycelium:ice-score` averages; if this"
              " came from a hand calculation, redo it as the mean. Adding these to the"
              " baseline would record a new mistake as history, which is the one use of"
              " --write-baseline that is wrong.")
        return 1

    print("\nOK: no ICE aggregate has become product-shaped since the baseline.")
    print("WHAT THIS DOES NOT MEAN: that the scores are good. It checks one arithmetic identity.")
    print("Whether Impact, Confidence and Ease were honestly assessed is not visible from here —")
    print("and a flat Ease column across a corpus is the usual sign that they were not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
