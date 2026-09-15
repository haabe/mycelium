#!/usr/bin/env python3
"""check_merge_markers.py — a claim of novelty must say what it was checked against.

WHY THIS EXISTS (dogfood 2026-09-14, founder ruling: "If it exists and is still broken, it isn't
strict enough"). A 77-source literature sweep proposed, as "the one original mechanism nobody
has tested", having the user name what they were about to build before the tool runs — which
`skills/interview/SKILL.md` has shipped all along as its first question. The sweep read 77
sources and never opened the product. The operating contract's read-before-recommend rule was
injected at that session's start and was not consulted; a fourth prose restatement of it was
proposed as the fix and killed by the founder in one sentence. This is the mechanism instead.

WHAT IT CHECKS. A canvas entry whose prose claims that a mechanism, idea or feature is
original, untested, or built by nobody (see NOVELTY) must carry, on the same entry, a marker
saying what the claim was checked against and when: `checked_skills: YYYY-MM-DD` (the
product's own skills and engine) or `checked_against: <surface>` with a date. The marker is
the reviewed-marker pattern this framework already ships (`stale_prose_reviewed`,
`handles_checked`, `reply_not_owed`): a judgement made machine-readable. The check never
judges whether the claim is TRUE; it asks whether anyone looked.

WHAT IT DOES NOT CHECK, stated because the candidate's own bar demands it. (1) The
co-presence rule from the same candidate — a conclusion about what works must cite both the
local record and the literature — is not built; "concludes about what works" has no lexical
shape that would hold under a 5% false-positive bar, and the read-set half of it shipped as
0.198.0. (2) The decision log is not scanned: it is append-only prose, and flagging a
year of historical entries would train the reader to skim the one that matters. (3) Market
claims ("nobody has built a tool that...") are a claim about the landscape, not about this
product, and `checked_against: landscape` is the honest marker for them; the NOVELTY phrases
are narrowed to mechanism-shaped claims so that most market prose does not fire.

Measured before shipping on the dogfood canvas (2026-09-15): 12 sentences across 5 canvases
matched the broad phrase list; 4 matched the narrowed one, 3 of them the exact sub-instance
the founder caught. Report-only, exit 1 under --strict only.

Exit codes: 0 clean or advisory; 1 --strict with findings; 2 precondition (no canvas dir).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

NOVELTY = re.compile(
    r"\b(?:untested (?:anywhere|mechanism|idea)|original(?:,| and)? (?:cheap,? )?(?:untested )?"
    r"(?:mechanism|idea)|nobody has (?:built|tested|tried|shipped) (?:it|this|that|one|a)|"
    r"no (?:tool|framework|product) (?:does|has|ships) this|(?:the )?first (?:tool|framework) to\b|"
    r"not (?:built|tested|tried) anywhere|never been (?:built|shipped) (?:anywhere|before))",
    re.IGNORECASE,
)
MARKERS = ("checked_skills", "checked_against")
_MAX_DEPTH = 14
_QUOTE = 120


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() if not isinstance(v, dict | list) for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node if not isinstance(v, dict | list) for s in _strings(v)]
    return []


def _marked(node: dict) -> bool:
    return any(node.get(k) for k in MARKERS)


def _visit(node: dict, canvas: str, here: str, state: dict) -> None:
    own = " ".join(_strings(node))
    m = NOVELTY.search(own)
    if not m:
        return
    if _marked(node):
        state["marked"] += 1
    else:
        lo = max(0, m.start() - 40)
        state["out"].append((canvas, here, own[lo:lo + _QUOTE].replace("\n", " ")))


def _walk(node, canvas: str, label: str, state: dict, depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        here = str(node.get("id") or label)
        _visit(node, canvas, here, state)
        for k, v in node.items():
            if isinstance(v, dict | list):
                _walk(v, canvas, f"{here}.{k}", state, depth + 1)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, canvas, f"{label}[{i}]", state, depth + 1)


def findings(canvas_dir: Path) -> tuple[list[tuple[str, str, str]], int]:
    """(unmarked novelty claims as (canvas, entry, excerpt), entries with a marker)."""
    state: dict = {"out": [], "marked": 0}
    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue  # parse failures belong to validate_canvas
        _walk(doc, path.stem, path.stem, state)
    return state["out"], state["marked"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    ap.add_argument("--strict", action="store_true", help="exit 1 on an unmarked claim")
    args = ap.parse_args(argv)
    canvas_dir = Path(args.canvas_dir)
    if not canvas_dir.is_dir():
        print(f"merge-markers: NOT A PASS — no canvas dir at {canvas_dir}. Nothing was checked.")
        return 2
    out, marked = findings(canvas_dir)
    print("Merge markers (does a claim of novelty say what it was checked against?)")
    print("=" * 68)
    print(f"  {len(out)} unmarked novelty claim(s); {marked} entr(ies) carry a marker")
    for canvas, entry, excerpt in out:
        print(f"  UNMARKED [{canvas}] {entry}: ...{excerpt}...")
    if out:
        print("  A claim that something is original or untested is a claim about a SEARCH. Add\n"
              "  `checked_skills: YYYY-MM-DD` after reading the product's own skills and engine,\n"
              "  or `checked_against: <surface>` naming what was read. The check does not judge\n"
              "  the claim; it asks whether anyone looked before making it.")
    return 1 if (args.strict and out) else 0


if __name__ == "__main__":
    sys.exit(main())
