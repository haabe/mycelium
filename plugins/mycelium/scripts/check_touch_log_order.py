#!/usr/bin/env python3
"""Fail when any touch_log is not in ASCENDING date order.

WHY THIS EXISTS. On 2026-08-18, asked which channel two overdue outreach tasks lived
on, the agent read `touch_log[-1]` as "the most recent touch" and reported that the
founder had owed both people a reply for 45 days. Both replies had in fact been sent on
2026-08-01 — the newest entry sat FIRST in those two lists, because at some point a
touch was prepended rather than appended. The founder was one confirmation away from
apologising twice for messages he had already sent.

THE FILE ITSELF WAS THE TRAP. Of 39 touch_logs carrying two or more dated entries,
23 ran oldest-first, 1 ran newest-first, and 5 were unsorted in ways that made the
last entry meaningless. With no convention, no read of "what happened most recently"
could be trusted, and nothing anywhere checked.

THE FIX IS THE CONVENTION, NOT A WARNING TO BE CAREFUL. Ascending was chosen because
23 of 28 sorted lists already were, and because the natural write action — appending a
new touch to the end — produces it. With this check standing, `touch_log[-1]` IS the
most recent touch, so the intuitive read is the correct one instead of a coin flip.

Equal dates are fine and keep their relative order: several touches land on one day and
the file has no time field to break the tie.

BLOCKING, like the duplicate-key check beside it and for the same reason: this is not a
judgement you can disagree with. An out-of-order log does not look wrong to any reader
or any parser — it silently returns the wrong answer to a question people actually ask
of this file, which is "what happened last, and does anyone owe anyone a reply?"
"""
import argparse
import os
import pathlib
import re
import sys

import yaml

ROOTS = [".claude/canvas", ".claude/diamonds", ".claude/harness"]
# Consumer-relative by design: this runs in the USER's project, where canvas
# state lives under .claude/. --root repoints the scan for a caller that runs
# from elsewhere (CI checks out into a subdirectory).
MIN_DATES_TO_COMPARE = 2  # one date cannot be out of order with itself
DATEISH = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def entry_date(e):
    """First ISO date on the entry's `date` field, or None if it carries no date."""
    if not isinstance(e, dict):
        return None
    raw = e.get("date")
    if raw is None:
        return None
    m = DATEISH.match(str(raw).strip().strip('"'))
    return m.group(1) if m else None


def walk(node, path, out):
    """Find every `touch_log` list anywhere in the document, at any nesting depth."""
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{path}.{k}" if path else str(k)
            if k == "touch_log" and isinstance(v, list):
                out.append((here, node.get("id") or path, v))
            walk(v, here, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", out)


def check(path):
    problems = []
    try:
        doc = yaml.safe_load(pathlib.Path(path).read_text())
    except yaml.YAMLError as e:
        return [f"{path}: unparseable ({e.__class__.__name__})"]
    logs = []
    walk(doc, "", logs)
    for _, owner, entries in logs:
        dates = [d for d in (entry_date(e) for e in entries) if d]
        undated = len(entries) - len(dates)
        if undated:
            problems.append(f"{path}: {owner}: {undated} touch_log entr(y/ies) with no usable date")
        if len(dates) >= MIN_DATES_TO_COMPARE and dates != sorted(dates):
            problems.append(
                f"{path}: {owner}: touch_log is not ascending by date -> {dates}\n"
                f"    Newest touch must be LAST. Append new touches to the end of the list."
            )
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".",
                    help="project root to scan from; ROOTS are resolved relative to it")
    args = ap.parse_args(argv)

    base = pathlib.Path(args.root)
    files, problems = [], []
    for root in ROOTS:
        files.extend(sorted((base / root).rglob("*.yml")))
    for f in files:
        problems.extend(check(str(f)))
    if problems:
        print("touch_log order: FAIL", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("\n  Ascending order is what makes touch_log[-1] mean 'most recent'.",
              file=sys.stderr)
        print("  See corrections.md 2026-08-18 (reported two replies as unsent).", file=sys.stderr)
        return 1
    # ZERO INPUTS IS NOT A PASS. Added 2026-08-25 after CI run 32860858081 reported
    # "touch_log order: ... across 0 file(s)" and exited 0 — green because the scan root did not
    # resolve from the workspace root, so it looked at nothing and said so in words nobody
    # read. An empty scan is UNKNOWN, and UNKNOWN is never OK.
    if not files:
        print("touch_log order: UNKNOWN - scanned 0 files. The scan root did not resolve, so this "
              "is NOT a clean result.")
        print("  cwd=" + os.getcwd())
        return 1
    print(f"touch_log order: ascending across {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
