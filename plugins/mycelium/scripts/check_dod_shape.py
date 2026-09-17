#!/usr/bin/env python3
"""How big is each diamond's Definition of Done, and how much of it is the bar?

WHY THIS EXISTS. A Definition of Done is the sentence its owner steers by. Every check the
framework ran on it read PRESENCE and KEY SHAPE: is there an outcome, is there a signal. None
read size, and none told the bar apart from the record of how the bar has been scored.

MEASURED 2026-09-16 on the dogfood L1. `diamond-assess` step 7c asked the founder to state
the Definition of Done from memory before it was read back. Answer: "I honestly don't
remember the dod." The record was 76,904 characters; `kill_criterion` alone was 59,229 across
21 sub-keys, 17 of them dated update notes. Every sweep result and every ruling had been
appended where the reader who scores the kill looks, so the bar was about 7k of prose inside
a 77k field. Presence checks read that as satisfied. The human was the only check that could
notice, and only by failing to answer.

MEASURED AGAIN 2026-09-17, after the dated notes had been moved to a `log[]` list: the log
was 49k and the bar (outcome, signal, threshold, kill_criterion) was still 21k, against 750
characters for the same project's L0. Moving the log out is necessary and is not the same as
making the bar short. That is why this prints BOTH numbers.

WHAT IT REPORTS, per diamond:
  bar    outcome + signal + threshold + kill_criterion + measure + kind
  log    definition_of_done.log[]
  other  everything else under definition_of_done
and one structural finding, LOG-AS-KEYS: a dated key name under definition_of_done outside
the log (`state_2026_09_01:`), which is a log entry written as a field. That one is a defect
by the key-shape convention, whatever the sizes are. Dated keys INSIDE a log entry are left
to the key-shape guard.

WHAT IT DELIBERATELY DOES NOT DO. It sets no threshold on size and never warns on one. How
long a bar can be before its owner cannot state it is not known: the sample is three diamonds
in one project, one recall failure, and no recall success on record. A number invented here
would be obeyed as if it had been measured. The sizes are printed next to the recall question
so the human who just failed or passed it can see them; that is the experiment that would
set a threshold, and this is its instrument.

Exit 0 always, 2 when the file is missing or unreadable. Read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

BAR_KEYS = ("outcome", "signal", "threshold", "kill_criterion", "measure", "kind")
LOG_KEY = "log"
_DATED_KEY = re.compile(r"(?:^|_)20\d{2}_?\d{2}_?\d{2}(?:_|$)")


def _size(value) -> int:
    """Characters a reader has to get through: strings as written, structures as dumped."""
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return len(yaml.safe_dump(value, allow_unicode=True, width=10**6, sort_keys=False))


def _dated_keys(node, path: str = "definition_of_done") -> list[str]:
    """Paths of dated key names at any depth. Lists are walked; their items are not keys."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if _DATED_KEY.search(str(key)):
                found.append(here)
            found.extend(_dated_keys(value, here))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_dated_keys(item, f"{path}[{i}]"))
    return found


# A BAR THAT CANNOT STAY IN LIMBO (v0.227.0). On 2026-09-17 the dogfood L1 bar was audited as a
# decision procedure and could stay open six ways at once while every check was green: no state
# in which it was done, "otherwise the bet continues", a kill needing 5 of the next 5 replies.
# Research the same day gave nine criteria. The founder ruled to ship the two that had caught
# defects: the bar says what happens when its date passes and the default is STOP, and someone
# who did not write it resolved invented cases with it before it was accepted (the author's own
# mechanical checks had passed four broken drafts; a blind reader found the defect in each).
# ADVISORY, like everything in this script: findings are reported, nothing blocks.
_CATCH_ALL = re.compile(r"\b(anything else|otherwise|else|in every other case)\b", re.IGNORECASE)
_CONTINUES = re.compile(r"\bcontinu", re.IGNORECASE)
_ENDS = re.compile(r"\b(stop|re-?pitch|ends?|new bar|kill|close[sd]?)\b", re.IGNORECASE)


def _expiry_text(dod: dict, kc: dict) -> str:
    """What the bar says happens at its date: `on_expiry`, or the catch-all line of `branches`."""
    if kc.get("on_expiry"):
        return str(kc["on_expiry"])
    branches = dod.get("branches")
    last = branches[-1] if isinstance(branches, list) and branches else None
    if isinstance(last, dict) and _CATCH_ALL.search(str(last.get("when") or "")):
        return str(last.get("then") or "")
    return ""


def limbo_findings(dod: dict) -> list[str]:
    kc = dod.get("kill_criterion")
    if not isinstance(kc, dict):
        return []  # a stub bar at birth: no date to pass yet, so nothing here applies
    out = []
    if not kc.get("date"):
        out.append("NO-DATE")
    expiry = _expiry_text(dod, kc)
    if not expiry:
        out.append("NO-EXPIRY")
    elif _CONTINUES.search(expiry) and not _ENDS.search(expiry):
        out.append("CONTINUES-BY-DEFAULT")
    reader = dod.get("reader_test")
    if not isinstance(reader, dict):
        out.append("NOT-READ")
    elif reader.get("resolved") != reader.get("cases"):
        out.append("READER-STUCK")
    return out


LIMBO_WORDS = {
    "NO-DATE": "the kill criterion has no date, so the bar can never expire",
    "NO-EXPIRY": ("nothing says what happens when the date passes: add kill_criterion.on_expiry, "
                  "or end `branches` with an 'anything else' line"),
    "CONTINUES-BY-DEFAULT": ("at its date the bar continues; the default has to be stop or "
                             "re-pitch with a new written date, or it never ends"),
    "NOT-READ": ("no reader_test: nobody who did not write this bar has resolved invented cases "
                 "with it (see /mycelium:define-done)"),
    "READER-STUCK": "the reader could not resolve every case; the words they asked about fail",
}


def measure(diamond: dict) -> dict | None:
    """Sizes for one diamond, or None when it carries no Definition of Done mapping."""
    dod = diamond.get("definition_of_done")
    if not isinstance(dod, dict):
        return None
    bar = sum(_size(dod.get(k)) for k in BAR_KEYS)
    log = _size(dod.get(LOG_KEY))
    other = sum(_size(v) for k, v in dod.items() if k not in BAR_KEYS and k != LOG_KEY)
    entries = dod.get(LOG_KEY)
    return {
        "id": str(diamond.get("id", "?")),
        "scale": str(diamond.get("scale", "?")),
        "bar": bar,
        "log": log,
        "other": other,
        "total": bar + log + other,
        "log_entries": len(entries) if isinstance(entries, list) else 0,
        "limbo": limbo_findings(dod),
        # The log subtree is skipped: a dated key INSIDE a log entry is the key-shape
        # guard's finding, not an update that was written as a field of the bar.
        "log_as_keys": _dated_keys({k: v for k, v in dod.items() if k != LOG_KEY}),
    }


def load(path: Path) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    diamonds = doc.get("active_diamonds") if isinstance(doc, dict) else None
    return [d for d in diamonds if isinstance(d, dict)] if isinstance(diamonds, list) else []


def render(rows: list[dict]) -> str:
    if not rows:
        return "dod-shape: no diamond carries a definition_of_done mapping."
    out = [("dod-shape: characters per diamond. bar = outcome+signal+threshold+kill_criterion"
            "+measure+kind; log = definition_of_done.log[].")]
    for r in rows:
        out.append(f"  {r['id']} ({r['scale']}): bar {r['bar']:,} | log {r['log']:,} in "
                   f"{r['log_entries']} entr{'y' if r['log_entries'] == 1 else 'ies'} | "
                   f"other {r['other']:,} | total {r['total']:,}")
        if r["log_as_keys"]:
            shown = ", ".join(r["log_as_keys"][:3]) + (" ..." if len(r["log_as_keys"]) > 3 else "")  # noqa: PLR2004
            out.append(f"    LOG-AS-KEYS: {len(r['log_as_keys'])} dated key name(s) ({shown}). "
                       "A dated update is an entry under definition_of_done.log[] "
                       "({date, text}), not a new field.")
        out.extend(f"    {code} (advisory): {LIMBO_WORDS[code]}." for code in r["limbo"])
    out.append("  No size threshold is applied: how long a bar can be before its owner cannot "
               "state it has not been measured. Read these beside the recall question.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--diamonds", default=".claude/diamonds/active.yml")
    ap.add_argument("--diamond-id", default=None, help="report one diamond only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.diamonds)
    if not path.is_file():
        print(f"dod-shape: {path} not found", file=sys.stderr)
        return 2
    try:
        diamonds = load(path)
    except (OSError, yaml.YAMLError) as exc:
        print(f"dod-shape: {path} could not be read: {exc}", file=sys.stderr)
        return 2

    rows = [m for d in diamonds
            if (args.diamond_id is None or str(d.get("id")) == args.diamond_id)
            and (m := measure(d)) is not None]
    print(json.dumps(rows, indent=2) if args.json else render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
