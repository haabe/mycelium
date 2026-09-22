#!/usr/bin/env python3
"""Is a Cynefin classification older than the evidence underneath it?

WHY THIS EXISTS (v0.242.0). The Cynefin gate is Required at exactly ONE transition —
Define→Develop — at every scale. So a domain is classified once per diamond and nothing ever
re-runs it. That is fine for a classification that cannot go stale, and Cynefin is not one:
**the domain drives METHOD selection.** Clear routes to best practice, Complicated to expert
analysis, Complex to probe-sense-respond, Chaotic to act-sense-respond, Confused to stopping
until you know where you are. A node classified Complicated on three interviews, then given
twenty more that show irreducible uncertainty, is still routed to expert analysis — **the wrong
method, applied confidently, on current data.** That is a product defect, not a bookkeeping one.

Founder framing, 2026-09-22: *"the cynefin wherever it fits and whenever data changes so that
the cynefin classification light change."*

WHY THE FIX WAS A TIMESTAMP BEFORE IT WAS A CHECK. `cynefin_domain` was a bare string enum. It
carried no date and no reference to what it rested on, so "has the data changed since?" was not
a question anything could ask. v0.242.0 added `cynefin_classified_at` and `cynefin_basis` as
siblings; this compares the first against the evidence dates beneath the same node.

WHAT IT DOES NOT DO. It never re-classifies. Deciding which domain a thing is in is judgement —
that is `/mycelium:cynefin-classify`'s job and a human's. This only asks whether the judgement
predates the evidence, which is decidable. A STALE row is a prompt to re-run the skill, never a
verdict that the old domain was wrong: evidence can land and leave a classification correct.

EXIT: 0 clean; 1 on a stale classification; 2 when there is no canvas to read, because nothing
was examined and a green there is indistinguishable from a working check.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Canvas files that carry `cynefin_domain` per the shipped schemas.
CANVAS = ("opportunities.yml", "services.yml")

#: Keys whose value is a date marking when a piece of evidence was captured. A classification
#: older than any of these, under the same node, was made without seeing it.
EVIDENCE_DATES = ("captured_at", "validated_at", "observed_at", "as_of", "date")

#: How many undated rows to print before summarising. A wall of 75 identical lines is a wall
#: a reader scrolls past, which is how a real finding gets skipped.
MAX_LISTED = 10


#: Dates that were present but unreadable. NOT a silent drop: an unparseable evidence date
#: that is discarded quietly makes a node read as CURRENT when the check simply could not see
#: what was under it — the fail-open shape `check_fail_open.py` blocked this file's first push
#: for. Every unreadable value lands here and is reported.
UNREADABLE: list[tuple[str, str]] = []


def _parse(value, where: str = "") -> _dt.date | None:
    """Parse a date, RECORDING anything present-but-unreadable rather than dropping it.

    Returning None for `None` is correct — the field is absent, and absence is handled
    explicitly as UNCHECKABLE. Returning None for the string "last spring" is NOT: it
    silently removes evidence from the comparison and the node then looks current."""
    if isinstance(value, _dt.date):
        return value
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        if value not in (None, "", []):
            UNREADABLE.append((where, repr(value)[:60]))
        return None
    text = value.strip().split("T")[0]
    try:
        return _dt.date.fromisoformat(text)
    except ValueError:
        UNREADABLE.append((where, value.strip()[:60]))
        return None


def _evidence_dates(node) -> list[_dt.date]:
    """Every evidence date anywhere beneath this node."""
    out: list[_dt.date] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in EVIDENCE_DATES:
                parsed = _parse(value, key)
                if parsed:
                    out.append(parsed)
            else:
                out.extend(_evidence_dates(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_evidence_dates(item))
    return out


def _walk(node, path: str, found: list):
    if isinstance(node, dict):
        if "cynefin_domain" in node and node.get("cynefin_domain"):
            found.append({
                "id": node.get("id") or path,
                "domain": node["cynefin_domain"],
                "classified_at": _parse(node.get("cynefin_classified_at"),
                                        f"{node.get('id') or path}.cynefin_classified_at"),
                "basis": (node.get("cynefin_basis") or "").strip(),
                "evidence": _evidence_dates(node),
            })
        for key, value in node.items():
            _walk(value, f"{path}.{key}" if path else key, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, path, found)


def collect(root: Path) -> list:
    found: list = []
    canvas = root / ".claude" / "canvas"
    for name in CANVAS:
        path = canvas / name
        if not path.exists():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        _walk(doc, name, found)
    return found


@dataclass
class Buckets:
    """One scan's classifications, split. A single object rather than seven positional
    parameters: the reporting function had grown past what a caller can pass safely."""

    stale: list = field(default_factory=list)
    uncheckable: list = field(default_factory=list)
    basisless: list = field(default_factory=list)
    fresh: list = field(default_factory=list)


def _bucket(found: list) -> Buckets:
    """Split classifications into stale / uncheckable / basisless / fresh.

    Extracted from `main` so the judgement (which bucket) is separate from the reporting
    (what to print) and the CLI (what was asked for). `main` had grown to 19 branches, and
    the complexity limit was encoding a real readability problem rather than a style rule."""
    b = Buckets()
    for item in found:
        if item["classified_at"] is None:
            b.uncheckable.append(item)
            continue
        newer = [d for d in item["evidence"] if d > item["classified_at"]]
        if newer:
            item["newest"] = max(newer)
            item["newer_count"] = len(newer)
            b.stale.append(item)
        else:
            b.fresh.append(item)
        if not item["basis"]:
            b.basisless.append(item)
    return b


def _write_baseline(path: Path, undated_ids: list) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "_comment": "Cynefin classifications carrying no date when this check was adopted. "
                    "NOT to be backfilled — inventing a classification date is fabrication. "
                    "Each is retired by RE-CLASSIFYING the node, which writes a real date. "
                    "The list may shrink; it must never grow.",
        "undated": undated_ids}, indent=2) + "\n", encoding="utf-8")
    print(f"check_cynefin_freshness: baseline written — {len(undated_ids)} undated "
          "classification(s) recorded at adoption.")
    return 0


def _print_uncheckable(buckets, new_undated: list, base: list, undated_ids: list) -> None:
    """The undated section, lifted out of `_report` for the complexity limit — which was
    flagging a real problem: one function doing four unrelated print jobs.

    REWRITTEN BY HAND after a scripted guard-inversion left the whole body unreachable
    behind an early `return`, so the check reported 75 uncheckable classifications and
    printed none of them. A silent section under a green summary is the exact failure this
    file exists to catch, produced while refactoring the file that catches it."""
    if not buckets.uncheckable:
        return
    print("\n  UNCHECKABLE — classified with no `cynefin_classified_at`, so staleness cannot")
    print("  be computed. NOT a pass: absent is not the same as current.")
    if base:
        retired = len(base) - len([item for item in base if item in undated_ids])
        print(f"  {len(base)} baselined at adoption, {retired} since re-classified, "
              f"{len(new_undated)} NEW.")
    new_ids = {i["id"] for i in new_undated}
    for item in buckets.uncheckable[:MAX_LISTED]:
        mark = "  [NEW]" if item["id"] in new_ids else ""
        print(f"    {item['id']}: {item['domain']}{mark}")
    if len(buckets.uncheckable) > MAX_LISTED:
        print(f"    … and {len(buckets.uncheckable) - MAX_LISTED} more")


def _report(b: Buckets, new_undated: list, base: list, undated_ids: list):
    """Print every bucket; return an exit code, or None to fall through to the OK path.
    Separated from `main` so argument handling, judgement and reporting are three
    functions rather than one nineteen-branch block."""
    _print_uncheckable(b, new_undated, base, undated_ids)
    if b.basisless:
        print("\n  NO BASIS — `cynefin_basis` empty. The domain cannot be re-argued when the data")
        print("  changes; a later reader can only accept or discard it.")
        for item in b.basisless:
            print(f"    {item['id']}: {item['domain']}")

    if new_undated and base:
        print(f"\nFAIL: {len(new_undated)} classification(s) written since adoption carry no")
        print("`cynefin_classified_at`. A new classification must record when it was made —")
        print("that is free at the moment of classifying and impossible afterwards.")
        for item in new_undated:
            print(f"    {item['id']}: {item['domain']}")
        return 1

    if b.stale:
        print(f"\nFAIL: {len(b.stale)} classification(s) predate evidence beneath them.")
        for item in b.stale:
            print(f"    {item['id']}: {item['domain']} classified {item['classified_at']}, "
                  f"{item['newer_count']} evidence item(s) since, newest {item['newest']}")
        print("\nRe-run `/mycelium:cynefin-classify` on these nodes. **A stale row is a prompt,")
        print("not a verdict**: evidence can land and leave the domain unchanged. What is not")
        print("acceptable is routing work by a classification that has never seen the data.")
        return 1


    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the currently-undated classifications as the baseline")
    args = ap.parse_args(argv)
    root = Path(args.project_dir).resolve()

    if not (root / ".claude" / "canvas").is_dir():
        print(f"check_cynefin_freshness: PRECONDITION FAILED — no .claude/canvas under {root}. "
              "NOTHING WAS EXAMINED: no classification has been compared to anything.",
              file=sys.stderr)
        return 2

    found = collect(root)
    b = _bucket(found)

    print("Cynefin freshness (a domain drives METHOD, so a stale one routes work wrongly)")
    print("=" * 74)
    print(f"  {len(found)} classification(s): {len(b.fresh)} current, {len(b.stale)} stale, "
          f"{len(b.uncheckable)} uncheckable")

    # BASELINE, and the reason is the same one that shaped check_evidence_landing.
    # Failing on every undated classification would force a project to backfill dates nobody
    # knows — inventing a classification date is exactly the fabrication this framework
    # refuses elsewhere. So the undated set at adoption is recorded, and the check fails only
    # on a classification that appears or changes AFTERWARDS. The list may shrink as nodes are
    # legitimately re-classified; it must never grow.
    baseline_path = root / ".claude" / "evals" / "cynefin-freshness-baseline.json"
    undated_ids = sorted(i["id"] for i in b.uncheckable)
    if args.write_baseline:
        return _write_baseline(baseline_path, undated_ids)

    base = []
    if baseline_path.exists():
        try:
            base = json.loads(baseline_path.read_text(encoding="utf-8")).get("undated", [])
        except (json.JSONDecodeError, OSError):
            base = []
    new_undated = [i for i in b.uncheckable if i["id"] not in base]

    rc = _report(b, new_undated, base, undated_ids)
    if rc is not None:
        return rc

    if UNREADABLE:
        print(f"\nFAIL: {len(UNREADABLE)} date value(s) were present but unreadable, so the")
        print("comparison ran on less evidence than the canvas actually holds. A node whose")
        print("evidence date cannot be parsed would otherwise read as CURRENT.")
        for where, raw in UNREADABLE[:MAX_LISTED]:
            print(f"    {where}: {raw}")
        return 1

    print("\nOK: no classification predates the evidence beneath it.")
    print("WHAT THIS DOES NOT MEAN: that any domain is correct. It compares dates; whether a")
    print("thing is Complex or Complicated is judgement this check never makes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
