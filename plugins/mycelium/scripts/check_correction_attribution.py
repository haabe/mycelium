#!/usr/bin/env python3
"""Who caught it? The escape rate of the correction loop, computed rather than recalled.

WHY (dogfood 2026-08-03). `/corrections-audit` computes this by hand. Its
headline — "87% of corrections are ai-generated; 62% were caught by the user,
only ~25% by a hook/evaluator/agent-self" — is the single most decision-relevant
number the loop produces, because it says whether the answer is more harness or
more context. It was last computed on 2026-06-25, and the entry itself says the
gap was "unchanged from the 2026-06-02 read". Two data points, six weeks apart,
both produced only because someone remembered to look.

This is defect-escape analysis, the standard quality measure: of the defects
that occurred, what fraction escaped the automated net. Nothing here is invented
— it automates a measure this project already defined and already acts on.

WHAT IT DOES NOT DO, stated because the number is easy to over-read:

  * It reports over the entries that CARRY an attribution, and prints the
    unattributed count beside it every time. At the time of writing 14 of 72
    entries are attributed, so a rate quoted without its denominator would be a
    claim about 19% of the corpus wearing the clothes of the whole. That is the
    exact failure this repo spent 2026-08-02/03 removing from its own checks.
  * It reads free prose ("caught by hook", "Caught by founder", "surfaced by
    user"), because that convention already emerged in 14 entries on its own. A
    structured field would be cleaner and would also invalidate every existing
    entry, so the parser meets the corpus where it is.
  * It cannot see corrections that were never logged. An escape rate over
    recorded defects is a floor.

Exit 0 always — this reports, it does not gate. A rate is an input to judgement,
not a pass/fail condition, and a gate on it would create an incentive to log
fewer user-caught mistakes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CORRECTIONS_REL = ".claude/memory/corrections.md"

#: corrections.md uses TWO entry formats, and reading only one is how this
#: script's own denominator went wrong (dogfood 2026-08-03, first run against a
#: freshly-appended log):
#:
#:   heading style  `## 2026-05-03 — thing that happened`
#:   bullet style   `- **Thing that happened (2026-05-03, some-class)**: ...`
#:
#: The bullet form is what recent entries actually use — 26 of them at the time
#: this was found, against 75 headings — and the parser matched only headings.
#: It then printed "measured over 14 of 74 entries" while the corpus was ~101,
#: which is a wrong denominator inside the script written to print honest
#: denominators. Five entries appended that morning, every one carrying an
#: explicit "Caught by ..." phrase, were invisible to it.
#:
#: Both patterns are matched now. A body runs to whichever entry starts next,
#: regardless of which form that one takes, so mixed files interleave correctly.
ENTRY_RE = re.compile(
    r"^#{2,3}\s+(\d{4}-\d{2}-\d{2})\b(.*)$"                 # heading style
    r"|"
    r"^- \*\*.*?\((\d{4}-\d{2}-\d{2})[,)].*$",              # bullet style
    re.MULTILINE,
)

#: The catcher vocabulary, in priority order. First match on an entry wins, so
#: the more specific patterns come first. Derived from the phrasings already in
#: the corpus rather than imposed on it.
CATCHERS: list[tuple[str, re.Pattern[str]]] = [
    ("hook_or_check", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by\s+"
        r"(the\s+)?(hook|check|ci|validator|test|sweep|guard|linter|script)", re.IGNORECASE)),
    ("review", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by\s+"
        r"(the\s+)?(review|reviewer|code.review|blind|adversar)", re.IGNORECASE)),
    ("agent_self", re.compile(
        r"(agent[- ]self[- ]caught|self[- ]caught|caught\s+by\s+(the\s+)?agent)", re.IGNORECASE)),
    ("user", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by\s+"
        r"(the\s+)?(user|founder|operator|human)", re.IGNORECASE)),
]


def _entries(text: str) -> list[tuple[str, str]]:
    """(date, body) per dated entry. Body runs to the next dated heading."""
    marks = list(ENTRY_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        # group(1) is the heading date, group(3) the bullet date; exactly one
        # of the two alternatives matched.
        date = m.group(1) or m.group(3)
        out.append((date, text[m.start():end]))
    return out


def classify(body: str) -> str | None:
    for name, pat in CATCHERS:
        if pat.search(body):
            return name
    return None


def scan(root: Path) -> dict:
    path = root / CORRECTIONS_REL
    if not path.is_file():
        return {"applicable": False, "reason": f"no {CORRECTIONS_REL}"}

    entries = _entries(path.read_text(errors="replace"))
    counts: dict[str, int] = {}
    unattributed: list[str] = []
    for date, body in entries:
        who = classify(body)
        if who is None:
            unattributed.append(date)
        else:
            counts[who] = counts.get(who, 0) + 1

    attributed = sum(counts.values())
    caught_by_us = counts.get("hook_or_check", 0) + counts.get("agent_self", 0)
    return {
        "applicable": True,
        "entries": len(entries),
        "attributed": attributed,
        "unattributed": len(unattributed),
        "by_catcher": counts,
        # The escape rate: of attributed defects, the share the automated net
        # and the agent itself did NOT catch.
        "escape_rate": (
            round(1 - caught_by_us / attributed, 3) if attributed else None
        ),
        "coverage": round(attributed / len(entries), 3) if entries else None,
        "unattributed_dates": unattributed[-12:],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Escape rate of the correction loop: who caught each mistake."
    )
    p.add_argument("--root", default=".", help="Project root (default: cwd).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    st = scan(Path(args.root).resolve())
    if args.json:
        print(json.dumps(st, indent=2))
        return 0

    if not st["applicable"]:
        print(f"Correction attribution: N/A — {st['reason']}. Nothing was "
              "measured, and nothing was supposed to be.")
        return 0

    if not st["entries"]:
        print("Correction attribution: N/A — corrections.md holds no dated "
              "entries yet.")
        return 0

    if not st["attributed"]:
        print(f"Correction attribution: NO RATE AVAILABLE. {st['entries']} "
              "entries, none carrying a catcher. Add 'caught by <user|hook|"
              "review|agent-self>' to entries as you write them — without it "
              "the loop cannot say whether the answer is more harness or more "
              "context, which is the only question it exists to answer.")
        return 0

    order = ["user", "hook_or_check", "review", "agent_self"]
    parts = ", ".join(
        f"{k.replace('_', '/')}: {st['by_catcher'][k]}"
        for k in order if k in st["by_catcher"]
    )
    print(f"Correction attribution: {parts}")
    print(f"  escape rate {st['escape_rate']:.0%} "
          f"(share NOT caught by a hook, check, or the agent itself)")
    # The denominator, every time, unprompted. A rate over 19% of the corpus
    # quoted without it is a claim about the whole wearing borrowed clothes.
    print(f"  measured over {st['attributed']} of {st['entries']} entries "
          f"({st['coverage']:.0%} coverage) — {st['unattributed']} carry no "
          f"catcher and are NOT in the rate above.")
    if st["unattributed"] > st["attributed"]:
        print("  COVERAGE IS BELOW HALF: treat the rate as indicative, not "
              "measured. The cheapest fix is one phrase per new entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
