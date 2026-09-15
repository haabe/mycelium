#!/usr/bin/env python3
"""Content in key position defeats every field-level mechanism.

THE GAP THIS CLOSES (founder ruling, 2026-08-31). A canvas key that carries a date or an
entity id in its NAME — `scope_correction_2026_08_27`, `ht_010_status`,
`GOODHART_INVERSION_FOUND_2026_08_23` — is not a field. It is a sentence wearing a field's
clothes, and it is invisible to everything that reasons about fields:

  * `check_field_wiring.py` cannot ask whether it has a consumer: a key used once is
    indistinguishable from a typo, and the 66 one-off promise-shaped keys measured that day
    were nearly all of this form.
  * No schema can declare it, so `additionalProperties: true` is the only thing keeping the
    canvas valid — the schema is not describing the file any more.
  * Nothing can sort, filter or age them. A date in a value can be compared; a date in a key
    can only be grepped, which is why `horizon_set_2026_08_28` never becomes overdue.

MEASURED at the ruling: 527 such keys across 8 canvases, 226 in human-tasks.yml alone.

TWO CHECKS, TWO QUESTIONS, ONE KEY (ruled 2026-09-15). `check_field_wiring.py` skips a key
used once (`_MIN_USES = 2`: "a key used once is an annotation, not a field") and this check
flags it. Both are right, because they ask different things: field-wiring asks whether a
FIELD has a consumer, and a one-off cannot be a field; this check asks whether a KEY is
carrying content, and a one-off dated key is the purest case of exactly that. A key that
field-wiring ignores and this check flags is not a disagreement to reconcile; it is a
sentence in key position, which is the defect.

THE FOUNDER'S WORDS: content like this belongs in VALUES, not in key names.

  # instead of
  scope_correction_2026_08_27: "the sweep restates the thesis"
  # write
  notes:
    - date: 2026-08-27
      kind: scope_correction
      note: "the sweep restates the thesis"

REPORT ONLY BY DEFAULT, and that is a deliberate proportionality call rather than timidity —
see the founder's own note on gate-remedy proportionality (opp-072: triggers are
floss-shaped, remedies are root-canal). 527 pre-existing keys cannot all be a build failure
on the day the rule is written. `--strict` fails only on keys ABSENT from the baseline, so
the cost of the new pattern falls on new writing. Seed the baseline with --write-baseline.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

#: A date anywhere in a key name: 2026_08_27, 2026-08-27, 20260827, or a bare _2026 suffix.
DATE_IN_KEY = re.compile(r"(19|20)\d{2}[_-]?\d{2}[_-]?\d{2}|_(19|20)\d{2}(_|$)")
#: A canvas entity id in a key name: ht_010, comp-107, opp_038.
#: A canvas entity id in a key name: ht_010, comp-107, opp_038. The trailing guard is
#: `(?!\d)` and NOT `\b`: an underscore is a word character, so `\b` never matches
#: between `ht_010` and `_status` — which silently under-counted the population on the
#: first real run and was caught only by this module's own test.
ENTITY_IN_KEY = re.compile(r"(^|[^a-z0-9])(ht|comp|opp|sol|pp|need|cyc|dl|jtbd)[_-]\d{2,4}(?!\d)",
                           re.IGNORECASE)

#: Recursion ceiling walking a canvas. Deep enough for every shipped canvas, finite so a
#: pathological nesting cannot hang the gate.
_MAX_DEPTH = 12

#: How many NEW keys to name before summarising. Naming a few makes the report actionable;
#: naming hundreds is how a check gets scrolled past.
_NAME_LIMIT = 25

BASELINE_REL = "harness/key-shape-baseline.yml"


def offending(node, canvas: str, out: list[tuple[str, str]], depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        for key, val in node.items():
            if isinstance(key, str) and (DATE_IN_KEY.search(key) or ENTITY_IN_KEY.search(key)):
                out.append((canvas, key))
            offending(val, canvas, out, depth + 1)
    elif isinstance(node, list):
        for val in node:
            offending(val, canvas, out, depth + 1)


def scan(canvas_dir: Path) -> list[tuple[str, str]]:
    """Every canvas file, and the diamonds beside them.

    Diamonds were not scanned until v0.203.0, and the gap was found by walking into it: an
    agent wrote `perspective_conflict_check_2026_09_02` into `diamonds/active.yml` minutes
    after this check had caught two identical keys in two canvas files (dogfood 2026-09-02).
    The third would have baselined silently. Diamond keys are reported as `diamonds/<stem>`
    so a baseline seeded before v0.203.0 shows them as NEW once, which is the honest reading.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            offending(yaml.safe_load(path.read_text()), path.stem, found)
        except (yaml.YAMLError, OSError):
            continue  # parse failures belong to validate_canvas, not here
    diamonds = canvas_dir.parent / "diamonds"
    if diamonds.is_dir():
        for path in sorted(diamonds.glob("*.yml")):
            try:
                offending(yaml.safe_load(path.read_text()), f"diamonds/{path.stem}", found)
            except (yaml.YAMLError, OSError):
                continue
    return found


#: v0.212.0. Across 2,512 distinct dogfood keys, 36 stems carried more than one spelling and 95
#: keys were absorbed by them (founder, 2026-09-02: "similar-looking keys that probably should
#: be the same key"). Three shapes: a dated twin beside a live field (`status` plus
#: `status_2026_08_05`), a concept that exists only in dated form (`reply_sent_2026_08_03`, never
#: `reply_sent`), and casing-only twins. Two of the three entity-scoped copies found were already
#: stale (`ht_010_status: in_progress` beside `status: abandoned`). Nothing compared a key
#: against its own near-twin. This report groups spellings by stem using the two regexes above,
#: ranks the fixable case (a plain spelling exists) first, and compares an entity-scoped twin's
#: value against the plain field on the same object.
_CASING_SPLIT = re.compile(r"[-\s]+")
#: Strip a full date (with an optional trailing letter suffix) before the bare-year form, so
#: `status_2026_08_05` stems to `status`, not `status08_05`: DATE_IN_KEY's second alternative
#: starts one character earlier and would win the substitution.
_FULL_DATE = re.compile(r"_?(19|20)\d{2}[_-]?\d{2}[_-]?\d{2}[a-z]?")
_SPELLINGS_SHOWN = 5


def stem_of(key: str) -> str:
    """Normalise a key to its stem: strip dates and entity ids, casefold, hyphens to underscores."""
    s = _FULL_DATE.sub("", key)
    s = DATE_IN_KEY.sub("", s)
    s = ENTITY_IN_KEY.sub(lambda m: m.group(1), s)
    s = _CASING_SPLIT.sub("_", s.lower())
    return re.sub(r"_+", "_", s).strip("_")


def _is_twin(key: str) -> bool:
    return bool(ENTITY_IN_KEY.search(key) or DATE_IN_KEY.search(key))


def _divergence(node: dict, key: str, val, canvas: str, here: str) -> str | None:
    plain = stem_of(key)
    if plain == key or plain not in node:
        return None
    other = node[plain]
    if isinstance(other, dict | list) or isinstance(val, dict | list) or other == val:
        return None
    return (f"{canvas}: {here} carries `{plain}: {other}` and `{key}: {val}` — the twin "
            f"disagrees with the field it copies")


def _collect_stems(node, canvas: str, label: str, state: dict, depth: int = 0) -> None:
    """Walk one canvas; `state` holds `spellings` (stem -> set of keys) and `divergences`."""
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        here = str(node.get("id") or label)
        for key, val in node.items():
            if not isinstance(key, str):
                continue
            state["spellings"].setdefault(stem_of(key), set()).add(key)
            if _is_twin(key):
                d = _divergence(node, key, val, canvas, here)
                if d:
                    state["divergences"].append(d)
            _collect_stems(val, canvas, f"{here}.{key}", state, depth + 1)
    elif isinstance(node, list):
        for i, val in enumerate(node):
            _collect_stems(val, canvas, f"{label}[{i}]", state, depth + 1)


def stem_collisions(canvas_dir: Path) -> tuple[list[tuple[str, bool, list[str]]], list[str]]:
    """(collisions, divergences).

    collisions: (stem, plain_exists, spellings) for every stem with more than one spelling,
    fixable-first (a plain spelling exists to fold the twins into).
    divergences: an entity-scoped or dated twin (`ht_010_status`) on the same object as the
    plain field (`status`) whose values differ — a snapshot wearing a current-state name.
    """
    state: dict = {"spellings": {}, "divergences": []}
    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            _collect_stems(yaml.safe_load(path.read_text()), path.stem, path.stem, state)
        except (yaml.YAMLError, OSError):
            continue
    out = [(stem, stem in names, sorted(names))
           for stem, names in state["spellings"].items() if len(names) > 1 and stem]
    out.sort(key=lambda t: (not t[1], -len(t[2]), t[0]))
    return out, state["divergences"]


def _report_stem_collisions(canvas_dir: Path) -> None:
    collisions, divergences = stem_collisions(canvas_dir)
    if not collisions and not divergences:
        return
    fixable = [c for c in collisions if c[1]]
    print(f"\nStem collisions (one concept, several spellings): {len(collisions)} stem(s), "
          f"{sum(len(c[2]) for c in collisions)} keys; {len(fixable)} have a plain spelling to "
          f"fold into, {len(collisions) - len(fixable)} exist only in dated or scoped form")
    for stem, plain, names in collisions[:_NAME_LIMIT]:
        kind = "FOLD   " if plain else "MISSING"
        more = " ..." if len(names) > _SPELLINGS_SHOWN else ""
        print(f"  {kind} {stem}: {', '.join(names[:_SPELLINGS_SHOWN])}{more}")
    if len(collisions) > _NAME_LIMIT:
        print(f"  ... and {len(collisions) - _NAME_LIMIT} more")
    for d in divergences:
        print(f"  DIVERGE {d}")
    print("  FOLD: move the twins' values into the plain field as dated list entries.\n"
          "  MISSING: the field was never created; create it and fold. DIVERGE: two names for\n"
          "  one state disagree; the plain field is what every reader uses, the twin is stale.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    ap.add_argument("--baseline", default=None,
                    help=f"defaults to <canvas-dir>/../{BASELINE_REL}")
    ap.add_argument("--write-baseline", action="store_true",
                    help="seed the baseline from what is on disk now, once")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on a key that is NOT in the baseline")
    args = ap.parse_args()

    canvas_dir = Path(args.canvas_dir)
    if not canvas_dir.is_dir():
        print(f"key-shape: NOT A PASS — no canvas dir at {canvas_dir}. Nothing was checked.")
        return 1
    found = scan(canvas_dir)
    base_path = Path(args.baseline) if args.baseline else canvas_dir.parent / BASELINE_REL

    if args.write_baseline:
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_text(yaml.safe_dump(
            {"note": "Keys carrying a date or entity id in their NAME, as of seeding. "
                     "Content in key position; the remedy is to move it into values. "
                     "Present so the RULE costs new writing, not a 527-key rewrite.",
             "keys": sorted({f"{c}:{k}" for c, k in found})}, sort_keys=False))
        print(f"key-shape: baseline seeded with {len({f'{c}:{k}' for c,k in found})} key(s) "
              f"at {base_path}")
        return 0

    baseline = set()
    if base_path.exists():
        doc = yaml.safe_load(base_path.read_text()) or {}
        baseline = set(doc.get("keys") or [])
    new = sorted({f"{c}:{k}" for c, k in found} - baseline)

    print("Key-shape scan (is content sitting in a key name?)")
    print("=" * 60)
    print(f"  {len({f'{c}:{k}' for c,k in found})} key(s) carry a date or entity id in the name"
          f"; {len(baseline)} baselined, {len(new)} NEW")
    if not new:
        print("\n  No NEW content-in-key. A date in a VALUE can be compared and can go overdue;\n"
              "  a date in a KEY can only be grepped, which is why such a key never fires.")
        _report_stem_collisions(canvas_dir)
        return 0
    print(f"\n  {len(new)} NEW:")
    for item in new[:_NAME_LIMIT]:
        print(f"    {item}")
    if len(new) > _NAME_LIMIT:
        print(f"    ... and {len(new) - _NAME_LIMIT} more")
    print("\n  Move it into a value. Instead of `thing_happened_2026_08_27: <text>`, write a\n"
          "  list entry with `date:` and `note:` keys — then it can be sorted, aged and read\n"
          "  by something other than grep.")
    _report_stem_collisions(canvas_dir)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
