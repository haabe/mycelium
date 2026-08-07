#!/usr/bin/env python3
"""check_source_authenticity.py — a handle is not a person until someone checked.

THE GAP THIS CLOSES, AND NO EXISTING TIER COVERS IT.

The evidence tiers (`external_data`, `external_human`, `internal_simulated`,
`speculation`) grade evidence by WHERE IT CAME FROM. `external_human` means a human
outside the team said it. NOTHING ANYWHERE CHECKS WHETHER IT WAS A HUMAN. The tier
encodes provenance and is silent on authenticity, and in a public channel those are
different questions.

FOUND IN DOGFOOD 2026-08-07, mining r/buildinpublic for switch-from evidence:

    An account stating a discovery heuristic was logged as a second practitioner
    "arriving independently" at a conclusion the framework already held. The profile:
    nine months old, 10 comment karma, and every comment across three subs running one
    template -- an affirming clause, then a suggestion opening "I'd". It appeared THREE
    TIMES in one afternoon across two threads. Counted naively, ONE templated account
    would have entered the canvas as THREE CONVERGENT STRANGERS.

    A second account, posting a first-person founder story, had 26 post karma and ZERO
    comment karma, with the same story reskinned across five subs, each version pivoting
    to a different product placement. The sub's own members had already noticed: the
    highest-scored comment in that thread, at nearly double the post, was an accusation
    of fabrication.

WHY THIS FAILURE MODE IS WORSE THAN NOISE, AND WHY IT GETS A CHECK RATHER THAN A NUDGE.
Synthetic accounts restate standard, sensible heuristics fluently. So the contamination
does not arrive as garbage -- it arrives AGREEING WITH THE FRAMEWORK'S OWN THEORY, in
the evidence class the framework weights most heavily. Agreement is nearly free to
manufacture; disagreement carrying receipts is not. A harness that weights
convergence-across-strangers without ever asking whether the strangers are people has a
hole exactly where it is most confident.

TWO RULES, both narrow on purpose:

    A. An entry marked `external_human` (or `external_data`) cites a public-channel
       HANDLE and carries no authenticity note anywhere in the record.

    B. The same, but the record ALSO claims CONVERGENCE or INDEPENDENT arrival. Higher
       severity: rule A costs a mislabelled quote, rule B costs a confidence move built
       on a count that may be one account wearing several names.

WHAT AN AUTHENTICITY NOTE LOOKS LIKE -- any of: whether the account replies to people,
account age or karma, persona continuity, whether the history is inspectable, or an
explicit withdrawal/discount. The cheapest test first, learned from a channel native
rather than invented here: DOES THE OP REPLY. It is free, it runs on the page already
open, and it separated every account checked on 2026-08-07.

WHY THIS IS A SCRIPT AND NOT A validate-template.sh CHECK -- same reason
check_stale_prose.py and check_leaf_lifecycle.py are. validate-template.sh runs in the
FRAMEWORK repo, whose canvas carries no mined external evidence at all. A check written
there would report nothing-to-audit forever and read green, which is the built-not-wired
class committed inside a fix for it (the v0.100.0 lesson). Surfaced ADVISORY via
session-start instead.

ADVISORY, NOT BLOCKING. Both rules are heuristics over prose. A false positive costs a
sentence of reading. Blocking a session over one would be worse than the defect, and an
advisory that cries wolf gets tuned out -- which is the same failure as one that reports
green (the check_stale_prose.py lesson: a first cut firing on 14 records is noise, not
coverage).

Exit 0 when it ran; exit 2 when there was nothing to scan. Findings go to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

# A claim that the evidence came from outside. These are the tiers whose whole meaning
# is "someone external said this", so they are the ones authenticity bears on.
# `internal_simulated` and `speculation` are deliberately absent: nobody is claimed.
_EXTERNAL_TIER = re.compile(
    r"\bsource_class:\s*[\"']?(external_human|external_data)\b"
    r"|\bEVIDENCE\s+CLASS:\s*[^\n]*\bexternal_(human|data)\b",
    re.IGNORECASE,
)

# A public-channel handle. Deliberately NARROW: a real name ("Brooks Talley") is not a
# handle and is not flagged, because a named person the founder actually corresponded
# with is a different evidence situation and this check has nothing useful to say there.
#   u/Name, /u/Name  -- reddit
#   /user/Name       -- reddit profile URLs
#   @name            -- HN, X, Slack, Discord; guarded against email domains, and
#                       against PACKAGE SCOPES via the trailing-hyphen lookahead.
#                       Found by running against a live canvas: `@haabe-mycelium` is a
#                       plugin marketplace name and was being read as a person.
_HANDLE = re.compile(
    r"(?:(?<![\w/])/?u/[A-Za-z0-9_-]{3,})"
    r"|(?:/user/[A-Za-z0-9_-]{3,})"
    r"|(?:(?<![\w.@])@[A-Za-z0-9_]{3,}\b(?!-))"
)
# r/subreddit is a place, not a person. Matched only to be excluded from _HANDLE hits
# that overlap it, since `u/` and `r/` sit side by side in this kind of prose.
_SUBREDDIT = re.compile(r"(?<![\w/])/?r/[A-Za-z0-9_]{2,}")

# Evidence that SOMEONE LOOKED. Generous by design: the cost of missing a real check is
# a nag on a record that already did the work, and that is how advisories get ignored.
_AUTHENTICITY_NOTE = re.compile(
    r"\b(OP[- ]replies?|replies?\s+to\s+(?:every|nearly every|people)"
    r"|profile\s+(?:checked|load|read)|account(?:s)?\s+(?:checked|was\s+checked)"
    r"|authenticity\s+(?:checked|test)|CHECKED\s+AND\s+CREDIBLE"
    r"|persona\s+continuity|comment\s+karma|post\s+karma"
    r"|not\s+inspectable|uninspectable|unverifiable"
    r"|WITHDRAWN|DISCOUNTED|templated|returns?\s+to\s+threads?"
    r"|count\s+accounts,?\s+not\s+comments)\b",
    re.IGNORECASE,
)

# A claim that several independent people arrived at the same place. This is the class
# that is cheapest to fake and that this framework weights most heavily, hence rule B.
_CONVERGENCE = re.compile(
    r"\b(convergen(?:ce|t)|arrived?\s+at\s+it\s+independently|independent(?:ly)?\s+"
    r"(?:sighting|arrival|voices?|practitioners?)|second\s+sighting"
    r"|N\s*=\s*[2-9]|n=[2-9]|\b[2-9]\s+(?:strangers|voices|practitioners|independent))\b",
    re.IGNORECASE,
)


# Shortest string treated as a name fragment when deriving self-handles. Two-letter
# fragments ("de", "van") match too much to be safe exclusions.
_MIN_NAME_FRAGMENT = 3
# Handles listed in a finding before eliding the rest. Enough to recognise the record.
_HANDLES_SHOWN = 4
# Rule B needs a real plurality of ACCOUNTS, not of mentions.
_MIN_CONVERGENCE_ACCOUNTS = 2


def _fold(s: str) -> str:
    """Lowercase and strip diacritics.

    Found by running against a live canvas: git config carried "Håvard" while the canvas
    prose wrote "@Havard". Without folding, the self-exclusion silently missed and the
    maintainer was told to go and verify their own account.
    """
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(c))


def _self_handles() -> set[str]:
    """The project's OWN identity, which is never external evidence about anyone.

    Found by running against a live canvas: records that quote inbound Slack messages
    carry `@<founder>` mentions written by OTHER people. The handle is real and the
    people are real, but the handle names the reader, not a source. Flagging it sends
    the maintainer to check their own account.

    Derived from git config rather than configured, so it costs the adopter nothing and
    degrades to "no exclusions" when git is absent. Never fails the scan.
    """
    out: set[str] = set()
    for key in ("user.name", "user.email"):
        try:
            r = subprocess.run(["git", "config", "--get", key],
                               capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        val = _fold((r.stdout or "").strip())
        if not val:
            continue
        if "@" in val:
            val = val.split("@", 1)[0]
        for part in re.split(r"[.\s_-]+", val):
            if len(part) >= _MIN_NAME_FRAGMENT:
                out.add(part)
    return out


def distinct_handles(text: str) -> list[str]:
    """Handles present, deduplicated, with subreddit names removed.

    Deduplication is the point, not a tidiness measure. The 2026-08-07 failure was one
    account quoted from three threads reading as three voices; a check that counted
    OCCURRENCES rather than ACCOUNTS would have agreed with the mistake it exists to
    catch.
    """
    subs = {m.group(0).lstrip("/").lower() for m in _SUBREDDIT.finditer(text)}
    mine = _self_handles()
    out: list[str] = []
    for m in _HANDLE.finditer(text):
        raw = m.group(0)
        norm = _fold(raw.lstrip("/").lstrip("@"))
        norm = norm.removeprefix("user/").removeprefix("u/")
        if f"r/{norm}" in subs or norm in mine:
            continue
        if norm not in out:
            out.append(norm)
    return out


def scan_text(text: str) -> list[tuple[str, str]]:
    """Return (rule, evidence) findings for one record's text."""
    if not _EXTERNAL_TIER.search(text):
        return []
    handles = distinct_handles(text)
    if not handles:
        # An external claim with no handle is a named person, an org, or a metric.
        # Authenticity of a public account is not the question there.
        return []
    if _AUTHENTICITY_NOTE.search(text):
        return []

    shown = ", ".join(handles[:_HANDLES_SHOWN]) + ("..." if len(handles) > _HANDLES_SHOWN else "")
    # Rule B needs TWO OR MORE distinct accounts. A convergence claim resting on a
    # single handle is not a convergence-across-strangers claim, and firing rule B on
    # one account overstates what the record actually did. It still gets rule A.
    if len(handles) >= _MIN_CONVERGENCE_ACCOUNTS and _CONVERGENCE.search(text):
        return [("B/convergence-claimed-authors-unchecked",
                 (f"{len(handles)} handle(s) ({shown}) support a convergence claim, "
                  "none checked"))]
    return [("A/external-human-author-unchecked",
             f"{len(handles)} handle(s) ({shown}) cited as external evidence, none checked")]


def iter_records(path: Path):
    """Yield (record_id, text) per top-level record, falling back to whole-file.

    Text-based rather than YAML-parsed, for the same reason check_stale_prose.py is:
    findings of this kind live in long prose blocks and comments, and a parse that
    discards comments cannot see them.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable or non-UTF-8: skip the file rather than abort the scan. Narrowed
        # from a blind `except Exception` per ruff BLE001 -- a bug in this module should
        # surface rather than be swallowed as "file unreadable".
        return
    chunks = re.split(r"\n(?=\s*-\s+id:\s*)|\n(?=[a-z_]+_20\d{2}_\d{2}_\d{2}:)", raw)
    for chunk in chunks:
        m = re.search(r"id:\s*([A-Za-z0-9_-]+)|^([a-z_]+):", chunk, re.MULTILINE)
        label = (m.group(1) or m.group(2)) if m else path.name
        yield label, chunk


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    # --project-dir and --json match the session-start advisory contract that
    # check_leaf_lifecycle.py and check_stale_prose.py already use. Same shape, so the
    # hook wiring stays uniform.
    ap.add_argument("--project-dir", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet-when-clean", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_dir or args.root)
    targets = sorted((root / ".claude").rglob("*.yml"))
    findings: list[tuple[str, str, str, str]] = []

    for f in targets:
        rel = f.relative_to(root)
        for rec_id, text in iter_records(f):
            for rule, evidence in scan_text(text):
                findings.append((str(rel), rec_id, rule, evidence))

    # EMPTY-INPUT HONESTY. check_empty_input_honesty.py caught check_stale_prose.py
    # exiting 0 over an empty repository on 2026-08-07, reporting "no candidates across
    # 0 files" -- a green that is indistinguishable from a working pass and is never
    # true. Refuse instead, naming what was not verified.
    if not targets:
        msg = (f"PRECONDITION NOT MET: no .yml files found under {root}/.claude/. "
               "Nothing was verified. This is not a clean result.")
        if args.json:
            print(json.dumps({"status": "precondition_not_met", "files_scanned": 0,
                              "reason": msg, "violations": []}))
        else:
            print(msg, file=sys.stderr)
        return 2

    if args.json:
        # Report the scanned count even when clean, so "nothing found" stays
        # distinguishable from "nothing looked at".
        print(json.dumps({
            "status": "violations" if findings else "ok",
            "files_scanned": len(targets),
            "violations": [
                {"file": f, "record": r, "rule": rule, "evidence": ev}
                for f, r, rule, ev in findings
            ],
        }))
        return 0

    if not findings:
        if not args.quiet_when_clean:
            print(f"OK: no unchecked external authors across {len(targets)} canvas/state file(s).")
        return 0

    print(f"ADVISORY: {len(findings)} record(s) cite a public handle as external evidence "
          "without a note that anyone checked the account.")
    for rel, rec_id, rule, evidence in findings:
        print(f"  {rel} [{rec_id}] {rule}: {evidence}")
    print("\nRule A -- a handle is a claim about a person, not a person.")
    print("Rule B -- convergence across strangers is the cheapest evidence class to fake "
          "and the one this framework weights most heavily.")
    print("Cheapest test first, and it is free: DOES THE OP REPLY. Then persona continuity, "
          "then whether the account returns to threads, then age and karma.")
    print("Count ACCOUNTS, not comments. Both rules are heuristics; if the record already "
          "did the work in words this misses, leave it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
