#!/usr/bin/env python3
"""Does a stored ICE aggregate match the algorithm the framework actually documents?

THE RULE SINCE 0.319.0. `skills/ice-score/SKILL.md` says, and `docs/errata.md` A7 records:
**ICE is Impact x Confidence x Ease**, as Gilad defines it. *Evidence-Guided*, ch. 3: *"A fourth
value holds the ICE score, which is simply the three values multiplied together"*. So a stored
aggregate must be the PRODUCT of the three factors stored beside it.

THE RULE BEFORE, AND WHY THIS SCRIPT ONCE CHECKED THE OPPOSITE. From v0.238.0 to 0.318.x it made
sure an aggregate was the AVERAGE, because 0.229.0 (errata A1) had moved the skill to Ellis's
arithmetic: *"those ratings are averaged to provide an aggregate score for each idea"* (`Hacking
Growth`, ch. 4). A1 was right about Ellis and silent about Gilad, whose Confidence Meter the same
skill uses and who multiplies. The maintainer chose Gilad's version on 2026-10-11 (product ideas
scored on evidence), and this check turned with the skill.

WHY THIS EXISTS (v0.238.0), unchanged. The erratum ended with an instruction to consumers --
*"re-check decisions that turned on them"* -- and nothing checked whether anyone did. Measured on
the dogfood canvas the day this was written: **14 of 14 verifiable aggregates were products, zero
were averages**, three releases after the erratum shipped. The correction was authored, released,
and never reached the data it was about. A rule about arithmetic needs a reader of the arithmetic.

WHAT IT DOES NOT DO, AND THAT IS THE DESIGN. It does not rewrite canvas data and must never be made
to. Re-scoring a leaf whose decision already closed is the backfill this framework forbids elsewhere
in plain words (`check_leaf_lifecycle`: *"a block written now cannot restore that sequence; it only
makes a past decision look compliant"*). An aggregate on a shipped leaf is the honest record of how
that call was actually made, whichever rule was in force: a product from before 0.229.0, an average
from 0.229.0 to 0.318.x. So the aggregates that are NOT the product when the baseline is taken are
recorded as a BASELINE, each with the value it carried, and the check fails only on one that appears
or changes afterwards -- the same shape as `check_evidence_landing` and `check_fail_open`, and for
the same reason: a red gate on a number nobody may move trains its reader to ignore it.

A BASELINE WRITTEN BEFORE 0.319.0 lists the aggregates that were product-shaped under the earlier
rule. Those are products, which is now the documented arithmetic, so they need no baseline; what
needs one is the averages written since. Until `--write-baseline` has been run once under this
rule the check CANNOT tell an average written before the rule changed from one written after it,
and it says exactly that (exit 2): nothing is reported as a failure and nothing as a pass. The
earlier list is carried over into the new file unread, because it is a record.

WHY IT CANNOT JUST RECOMPUTE AND COMPARE. Real canvases carry the block in several shapes at once.
Measured on the dogfood canvas: SEVEN distinct shapes across 26 entries. The factor keys are
`impact/confidence/ease` or the abbreviated `i/c/e`; the aggregate is `total` or `score`; some
entries carry an aggregate with NO factors at all (nothing to verify against); and some are frozen
review artifacts marked `advisory: true` recording a *blind re-derivation* alongside the original,
deliberately under a different key. A checker that assumed one shape would report most of a real
corpus as broken, which is how a check gets switched off.

ROUNDING. With Gilad's meter the Confidence is a decimal (1.96, 0.61), so a product is one too, and
he writes that *"the decimal point doesn't really matter; these are not exact numbers"*
(*Evidence-Guided*, ch. 4). A stored aggregate therefore matches when it is the product rounded to
the precision it was written with: 16, 15.7 and 15.68 all match 4 x 1.96 x 2.

EXIT: 0 clean or baseline-only; 1 on a new or changed aggregate that is not the product of its
factors; 2 on a usage error, or when it cannot assess (aggregates that are not the product exist
and no baseline under the 0.319.0 rule says which of them were already there).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _state_dir

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

#: The floor of the comparison. An aggregate written with fewer decimals is compared at the
#: precision it was written with (see `_matches`).
TOLERANCE = 0.01

#: The release that made the product the documented arithmetic. Printed, and written into the
#: baseline so a reader of that file knows which rule it was taken under.
RULE_SINCE = "0.319.0"

#: Where the baseline keeps the aggregates that were not the product when it was taken:
#: `{identifier: [value, ...]}`. A baseline without this key was written before RULE_SINCE.
BASELINE_KEY = "not_product"

#: The key a baseline written from v0.238.0 to 0.318.x used for the aggregates that were products
#: under the average rule. Carried over on rewrite and never read: it is a record of that adoption.
LEGACY_KEY = "product_shaped"


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
            return v, k
    return None, None


def _decimals(value) -> int:
    """How many decimals the aggregate was written with: 0 for 448 or 448.0, 2 at most."""
    if isinstance(value, int):
        return 0
    text = repr(float(value))
    if "e" in text.lower() or "." not in text:
        return 2
    fraction = text.split(".")[1]
    return 0 if fraction == "0" else min(len(fraction), 2)


def _matches(agg, target: float) -> bool:
    """True when `agg` is `target` rounded to the precision `agg` was written with."""
    tolerance = max(TOLERANCE, 0.5 * 10 ** -_decimals(agg))
    return abs(float(agg) - target) <= tolerance + 1e-9


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
    """Split into the product (correct), not the product, and unverifiable.

    `not_product` rows are dicts: ident, agg, product, mean, kind, advisory. `kind` is `average`
    when the stored value is the mean of the factors (the 0.229.0 to 0.318.x rule) and `other`
    when it is neither the product nor the mean. A value that is both (1, 1, 1) is the product.
    """
    correct, not_product, unverifiable = [], [], []
    for name, leaf_id, key, block in found:
        agg, _agg_key = _aggregate(block)
        fac = _factors(block)
        ident = f"{name}:{leaf_id}:{key}"
        if agg is None:
            continue  # no aggregate stored: nothing is being asserted
        if fac is None:
            unverifiable.append((ident, float(agg)))
            continue
        i, c, e = fac
        product = i * c * e
        mean = (i + c + e) / 3
        if _matches(agg, product):
            correct.append(ident)
            continue
        not_product.append({
            "ident": ident,
            "agg": float(agg),
            "product": round(product, 2),
            "mean": round(mean, 2),
            "kind": "average" if _matches(agg, mean) else "other",
            "advisory": block.get("advisory") is True,
        })
    return correct, not_product, unverifiable


def _read_baseline(path: Path):
    """(document, state). state: absent | unreadable | before-rule | current.

    An unreadable file is a STATE the caller prints ("the baseline file could not be read"),
    never an empty baseline: read as empty it would report every recorded aggregate as new.
    """
    doc, state = {}, "absent"
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            state = "before-rule"
        except (json.JSONDecodeError, OSError):
            state = "unreadable"
    if not isinstance(doc, dict):
        doc, state = {}, "unreadable"
    if isinstance(doc.get(BASELINE_KEY), dict):
        state = "current"
    return doc, state


def _recorded(base: dict, ident: str, agg: float) -> bool:
    """Is this aggregate in the baseline WITH THE VALUE IT CARRIED? A changed value is not."""
    values = base.get(ident)
    if not isinstance(values, list):
        return False
    return any(isinstance(v, (int, float)) and abs(float(v) - agg) < TOLERANCE for v in values)


def _describe(row: dict) -> str:
    shape = ("the stored value is the average" if row["kind"] == "average"
             else f"neither that nor the average, {row['mean']}")
    flag = "  [advisory re-derivation]" if row["advisory"] else ""
    return (f"{row['ident']}: stored {row['agg']}, Impact x Confidence x Ease is "
            f"{row['product']} ({shape}){flag}")


def _write_baseline(path: Path, not_product, previous: dict, state: str) -> int:
    recorded: dict = {}
    for row in not_product:
        recorded.setdefault(row["ident"], []).append(row["agg"])
    doc = {
        "_comment": "ICE aggregates that were NOT the product of their factors when this "
                    f"baseline was taken under the {RULE_SINCE} rule (ICE = Impact x Confidence "
                    "x Ease, Gilad), each with the value it carried. Averages written from "
                    "0.229.0 to 0.318.x are the usual case. These are NOT to be rewritten: an "
                    "aggregate on a closed decision records how that call was actually made. "
                    "The list may shrink as leaves are legitimately re-scored; it must never "
                    f"grow. `{LEGACY_KEY}`, when present, is the list a baseline written before "
                    f"{RULE_SINCE} kept under the average rule; it is carried over as a record "
                    "and nothing reads it.",
        "rule": "product",
        "rule_since": RULE_SINCE,
        BASELINE_KEY: {ident: sorted(values) for ident, values in sorted(recorded.items())},
    }
    if isinstance(previous.get(LEGACY_KEY), list):
        doc[LEGACY_KEY] = previous[LEGACY_KEY]
    _state_dir.prepare(path)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"check_ice_aggregate: baseline written under the {RULE_SINCE} rule — "
          f"{len(not_product)} aggregate(s) that are not the product of their factors recorded "
          "as history, with their values.")
    if state == "current":
        old = previous.get(BASELINE_KEY) or {}
        grown = [row for row in not_product if not _recorded(old, row["ident"], row["agg"])]
        if grown:
            print(f"  WARNING: this baseline GREW by {len(grown)} aggregate(s) the previous one "
                  "did not hold with these values. A baseline is meant to shrink. If these were "
                  "scored after the rule changed, the score is what needs fixing:")
            for row in grown:
                print(f"    {_describe(row)}")
    return 0


def _report_cannot_assess(not_product, state: str) -> int:
    reason = {
        "absent": "no baseline exists",
        "unreadable": "the baseline file could not be read",
        "before-rule": f"the baseline was written before {RULE_SINCE} (it lists the aggregates "
                       "that were products under the average rule, which need no baseline now)",
    }[state]
    print(f"\nCANNOT ASSESS: {len(not_product)} ICE aggregate(s) are not the product of their "
          f"factors, and {reason}, so nothing says which of them were written before the rule "
          f"changed in {RULE_SINCE}.")
    for row in not_product:
        print(f"    {_describe(row)}")
    print("\nNOTHING HERE IS REPORTED AS A FAILURE, AND THIS IS NOT A PASS.")
    print(f"  Written before this project took {RULE_SINCE}: they are history. Run this script")
    print("  once with --write-baseline. Do NOT re-score them; an average on a closed decision is")
    print("  the honest record of how that call was made.")
    print("  Written after: fix that score first (`/mycelium:ice-score` multiplies), then write")
    print("  the baseline. Recording a new mistake as history is the one wrong use of the flag.")
    return 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the aggregates that are not the product, with their values, "
                         "as the baseline")
    args = ap.parse_args(argv)

    root = Path(args.project_dir).resolve()
    if not (root / ".claude" / "canvas").is_dir():
        print(f"check_ice_aggregate: N/A — no .claude/canvas under {root}. "
              "Nothing was scanned, and that is not a pass.")
        return 0

    baseline_path = root / ".claude" / "evals" / "ice-aggregate-baseline.json"
    found = collect(root)
    correct, not_product, unverifiable = classify(found)
    previous, state = _read_baseline(baseline_path)

    if args.write_baseline:
        return _write_baseline(baseline_path, not_product, previous, state)

    averages = sum(1 for row in not_product if row["kind"] == "average")
    print(f"ICE aggregate check (ICE = Impact x Confidence x Ease, Gilad; the rule since "
          f"{RULE_SINCE})")
    print("=" * 62)
    print(f"  {len(found)} ICE block(s); {len(correct)} the product of their factors, "
          f"{averages} average-shaped, {len(not_product) - averages} neither, "
          f"{len(unverifiable)} unverifiable")

    if unverifiable:
        print("\n  UNVERIFIABLE — an aggregate is stored but the factors are not, so"
              " nothing can be recomputed. Not a failure and not a pass: the number"
              " cannot be checked at all.")
        for ident, agg in unverifiable:
            print(f"    {ident}  = {agg}")

    if state != "current":
        if not_product:
            return _report_cannot_assess(not_product, state)
        print("\nOK: every ICE aggregate that can be recomputed is the product of its factors.")
        print(f"  No baseline under the {RULE_SINCE} rule exists and none is needed yet: there is")
        print("  no aggregate to record as history.")
        _print_limits()
        return 0

    return _report_against_baseline(not_product, previous[BASELINE_KEY])


def _report_against_baseline(not_product, base: dict) -> int:
    """The adopted case: fail on an aggregate the baseline does not hold as it stands."""
    new = [row for row in not_product if row["ident"] not in base]
    changed = [row for row in not_product
               if row["ident"] in base and not _recorded(base, row["ident"], row["agg"])]
    held = len(not_product) - len(new) - len(changed)
    recorded_n = sum(len(v) for v in base.values() if isinstance(v, list))

    if recorded_n:
        print(f"\n  baseline: {recorded_n} recorded as history, {recorded_n - held} since "
              f"re-scored or removed, {held} still carrying the value they had.")
        print("  Those are NOT to be rewritten. An average on a closed decision is the honest"
              " record of how that call was made; re-scoring it now would only make it look"
              " compliant.")

    if new or changed:
        print(f"\nFAIL: {len(new) + len(changed)} ICE aggregate(s) are not the PRODUCT of their"
              " factors and are not in the baseline as they stand — so they were written or"
              " changed after the baseline was taken.")
        for row in new:
            print(f"    {_describe(row)}  [new]")
        for row in changed:
            was = ", ".join(str(v) for v in base.get(row["ident"]) or [])
            print(f"    {_describe(row)}  [changed; the baseline holds {was}]")
        print("\nFix the SCORE, not the baseline. `/mycelium:ice-score` multiplies Impact,"
              " Confidence and Ease; if this came from a hand calculation or from the average"
              f" the skill used before {RULE_SINCE}, redo it as the product. Adding these to the"
              " baseline would record a new mistake as history, which is the one use of"
              " --write-baseline that is wrong.")
        return 1

    print("\nOK: no ICE aggregate that is not the product of its factors has appeared or changed"
          " since the baseline.")
    _print_limits()
    return 0


def _print_limits() -> None:
    print("WHAT THIS DOES NOT MEAN: that the scores are good. It checks one arithmetic identity.")
    print("Whether Impact, Confidence and Ease were honestly assessed is not visible from here —")
    print("and a flat Ease column across a corpus is the usual sign that they were not.")


if __name__ == "__main__":
    sys.exit(main())
