#!/usr/bin/env python3
"""Findings that name reachable people, and no task that reaches them.

WHY THIS EXISTS. On 2026-08-15 a dogfood hand-verification named SIX public
repos under the heading "TIER (a) - REAL EXTERNAL CONTACT EVIDENCED". They sat
for ELEVEN DAYS with zero mentions in human-tasks.yml. Every gate was green the
whole time, because every gate audits ARTEFACTS: staleness, orphaned refs,
pre-registration, unread surfaces. None of them asks whether a finding names
somebody who could simply be asked. "Ask them" never emerged as a path.

WHAT IT REPORTS. Per results file: how many external person-identifiers it
names, and how many of those appear anywhere in human-tasks.yml. A file naming
people with none of them actioned is the shape above.

REPORT-ONLY, DELIBERATELY, AND THIS IS NOT A PLACEHOLDER FOR A GATE.
The extractor has a KNOWN false-positive class: `owner/repo` in backticks also
matches API paths and namespaced identifiers (`search/code` was the live example
that stopped this shipping as a gate on 2026-08-26). Failing CI on that is worse
than the disease. The ratio is the signal; a human reads it.

WHAT IT IS NOT. It does NOT propose that every named identifier become a task -
the same 2026-08-15 file names 28 hand-classified CONTAMINANTS alongside the six
genuine cases, and a per-name gate would have demanded tasks for all of them.
The signal is the file-level ratio, not the individual name.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

IDENT_PATTERNS = [
    re.compile(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,80})"),
    re.compile(r"`([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,80})`"),
    re.compile(r"\bu/([A-Za-z0-9_-]{3,20})\b"),
]
# Paths and endpoints that look like owner/repo but name no one.
NOT_A_PERSON = re.compile(
    r"\.(py|js|ts|md|yml|yaml|json|sh|txt|html|css)$"
    r"|^(lib|src|docs|tests|scripts|plugins|api|search|repos|orgs|users|node_modules)/"
)


def identifiers(text: str) -> set[str]:
    found = set()
    for rx in IDENT_PATTERNS:
        for m in rx.finditer(text):
            value = m.group(0).replace("github.com/", "").strip("`")
            if not NOT_A_PERSON.search(value):
                found.add(value)
    return found


def scan(root: pathlib.Path) -> tuple[list[dict], int]:
    tasks_file = root / ".claude" / "canvas" / "human-tasks.yml"
    tasks = tasks_file.read_text() if tasks_file.is_file() else ""
    results = sorted((root / ".claude" / "evals" / "results").rglob("*.md"))
    rows = []
    for path in results:
        names = identifiers(path.read_text(errors="ignore"))
        if not names:
            continue
        actioned = {n for n in names if n in tasks}
        if len(actioned) < len(names):
            rows.append({
                "file": str(path.relative_to(root)),
                "named": len(names),
                "actioned": len(actioned),
                "sample": sorted(names - actioned)[:4],
            })
    return rows, len(results)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root)

    rows, scanned = scan(root)
    if scanned == 0:
        # ZERO INPUTS IS NOT A PASS. An empty scan is UNKNOWN.
        print("named-people scan: UNKNOWN - 0 results files. The scan root did not resolve, "
              "so this is NOT a clean result.")
        return 1

    if not rows:
        print(f"named-people scan: every named person in {scanned} results "
              "file(s) appears in a task.")
        return 0

    print("FINDINGS THAT NAME PEOPLE AND HAVE NO TASK THAT REACHES THEM "
          f"({len(rows)} file(s)):")
    for r in rows:
        print(f"  {r['file']}")
        unactioned = r["named"] - r["actioned"]
        print(f"     {r['named']} named, {r['actioned']} in a task, {unactioned} not")
        print(f"     e.g. {', '.join(r['sample'])}")
    print("\n  Reported, not failed. The extractor also matches some namespaced paths, so read")
    print("  the file before acting. A finding that names a reachable person is a different KIND")
    print("  of finding from one that names a file: only one of them has a next action.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
