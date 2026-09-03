#!/usr/bin/env python3
"""Does a canvas file that CLAIMS to be assessed actually hold an assessment?

THE DEFECT THIS EXISTS FOR, MEASURED ON A CONSUMER 2026-09-03. Three canvas files sat at
their schema defaults while reading as live and recently validated:

  services.yml            15 of 15 principles `not-assessed`, for 103 days after a full
                          assessment had run and landed in the decision log instead.
  privacy-assessment.yml  7 of 7 principles `not-assessed`, empty evidence — and
                          `last_assessed: 2026-05-04`. A DATE ASSERTING AN ASSESSMENT THAT
                          NEVER LANDED.
  threat-model.yml        0 threats, 0 components, 0 security requirements.

All three carried a `_meta.last_validated` stamp set by a DIFFERENT skill that does write
canvas. So the freshness signal was live and pointed at the wrong thing: a staleness check
reading `_meta` saw a file validated two months ago, and the content beneath it was empty.

THE DISCRIMINATOR, AND IT IS THE WHOLE DESIGN. Other canvas files are also empty and SAY SO
in `_meta.applicability` — "L5 Market diamond canvas; populate when reached", "Schema-only
as of ...". Those are decisions and must never be flagged. AN EMPTY FILE THAT DECLARES
ITSELF EMPTY IS A DECISION; AN EMPTY FILE THAT DECLARES ITSELF FRESH IS A DEFECT. This
check fires only on the second.

WHY EXISTING CHECKS MISS IT. `check_evidence_landed.py` asks whether evidence reached the
canvas; a field at its schema default is not a MISSING record, it is a PRESENT record
saying `not-assessed`, which is indistinguishable from "assessed and found nothing" to
anything testing presence. Same absent-versus-negative confusion that made `confidence`
required on the diamond schema.

REPORT-ONLY unless --strict, per gate-remedy proportionality: a file can legitimately be
mid-assessment for a day, and failing a build over that teaches people to delete the stamp
rather than finish the assessment.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


#: (filename, human label, extractor) — extractor returns (assessed, total) over the
#: fields that carry the assessment. Registered explicitly rather than inferred: a wrong
#: guess about which field is "the assessment" would manufacture a finding, and this
#: project has logged two wrong-construction results that read as clean findings.
def _list_assessments(doc, key, field="assessment", default="not-assessed"):
    items = doc.get(key) or []
    if isinstance(items, dict):
        items = list(items.values())
    if not isinstance(items, list):
        return None
    total = len(items)
    done = sum(1 for x in items if isinstance(x, dict) and x.get(field) not in (None, "", default))
    return done, total


def _nonempty_list(doc, key):
    v = doc.get(key)
    if not isinstance(v, list):
        return None
    return (1 if v else 0), 1


REGISTRY = {
    "services.yml": ("Downe service quality", lambda d: _list_assessments(d, "principles")),
    "privacy-assessment.yml": ("Privacy by Design", lambda d: _list_assessments(d, "principles")),
    "threat-model.yml": ("STRIDE / OWASP threats", lambda d: _nonempty_list(d, "threats")),
}

#: A file whose `_meta.applicability` starts with one of these, or says it is not in use,
#: has DECLARED itself empty. That is a decision and is never a finding here.
def _declares_itself_empty(meta: dict) -> str | None:
    app = str(meta.get("applicability") or "")
    if not app:
        return None
    low = app.lower()
    if low.startswith("n/a") or "not actively used" in low or "schema-only" in low \
       or "populate when" in low or "not yet populated" in low:
        return app
    return None


def _freshness(doc: dict) -> tuple[str, str] | None:
    """The strongest claim this file makes about being current, and where it makes it."""
    meta = doc.get("_meta") or {}
    if doc.get("last_assessed"):
        return "last_assessed", str(doc["last_assessed"])
    if meta.get("last_validated"):
        return "_meta.last_validated", str(meta["last_validated"])
    return None


def resolve_canvas_dir(args) -> Path:
    """--canvas-dir wins; --root implies <root>/.claude/canvas; otherwise the cwd default."""
    if args.canvas_dir:
        return Path(args.canvas_dir)
    if args.root:
        return Path(args.root) / ".claude" / "canvas"
    return Path(".claude/canvas")


def report(buckets: dict) -> None:
    """Print every bucket, including the boring ones. A skip nobody sees is how a check
    comes to cover a fraction of its population while reporting clean."""
    print("Assessment landed (does a file claiming freshness actually hold an assessment?)")
    print("=" * 78)
    print(f"  {len(buckets['finding'])} claiming-fresh-but-empty · "
          f"{len(buckets['clean'])} assessed · {len(buckets['exempt'])} exempt · "
          f"{len(buckets['absent'])} not present\n")

    for fname, label, (done, total, (field, value)) in buckets["finding"]:
        print(f"  CLAIMS FRESH, HOLDS NOTHING  {fname}  ({label})")
        print(f"      {done} of {total} assessed, and `{field}` says {value}")
        print("      The gate that reads this file has no data. Run the owning skill, or")
        print("      declare the file empty in `_meta.applicability` — either is honest.\n")
    for fname, label, (done, total) in buckets["clean"]:
        print(f"  ok      {fname}: {done} of {total} assessed ({label})")
    for fname, _label, why in buckets["exempt"]:
        print(f"  exempt  {fname}: {why}")
    for fname in buckets["absent"]:
        print(f"  absent  {fname}: not present in this canvas")

    print("\nAN EMPTY FILE THAT DECLARES ITSELF EMPTY IS A DECISION. An empty file that carries")
    print("a freshness stamp is a defect — it reads as assessed to every check that looks at")
    print("dates, and the theory gate reading it gets nothing. Report-only unless --strict.")


def classify_file(path: Path, extract) -> tuple[str, object]:
    """One file -> (bucket, detail). Split out of main() so each bucket's REASON is
    stated in one place; main() only routes and prints. A verdict whose reason is
    computed inline three branches deep is one nobody re-reads."""
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        return "unparseable", exc

    meta = doc.get("_meta") or {}
    got = extract(doc)
    if got is None:
        return "exempt", "assessment field is not the shape this check registered"

    done, total = got
    if done or total == 0:
        return "clean", (done, total)

    declared = _declares_itself_empty(meta)
    if declared:
        return "exempt", f"declares itself empty: {declared[:70]}"

    fresh = _freshness(doc)
    if fresh:
        return "finding", (done, total, fresh)
    return "exempt", "empty and makes no freshness claim — nothing is being asserted"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None,
                    help="project root; --canvas-dir defaults to <root>/.claude/canvas. Accepted "
                         "so check_empty_input_honesty.py can aim this script at an empty tree — a "
                         "script it cannot aim at is recorded as untestable, not as clean.")
    ap.add_argument("--canvas-dir", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on findings instead of reporting only")
    args = ap.parse_args()

    d = resolve_canvas_dir(args)

    if not d.is_dir():
        print(f"assessment-landed: canvas dir not found: {d}", file=sys.stderr)
        return 2  # UNKNOWN is never a pass

    buckets: dict[str, list] = {"finding": [], "clean": [], "exempt": [], "absent": []}
    for fname, (label, extract) in sorted(REGISTRY.items()):
        p = d / fname
        if not p.exists():
            buckets["absent"].append(fname)
            continue
        bucket, detail = classify_file(p, extract)
        if bucket == "unparseable":
            print(f"assessment-landed: {fname} does not parse: {detail}", file=sys.stderr)
            return 2
        buckets[bucket].append((fname, label, detail))

    if len(buckets["absent"]) == len(REGISTRY):
        # An empty scan is UNKNOWN and UNKNOWN is never a pass. A canvas holding none of
        # these files has not been checked; reporting clean would be a success claim over
        # empty input, which is the class check_empty_input_honesty.py exists to forbid.
        print(f"assessment-landed: UNKNOWN — none of the {len(REGISTRY)} registered files "
              f"({', '.join(sorted(REGISTRY))}) exist in {d}. Nothing was checked.",
              file=sys.stderr)
        return 2

    report(buckets)
    return 1 if (buckets["finding"] and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
