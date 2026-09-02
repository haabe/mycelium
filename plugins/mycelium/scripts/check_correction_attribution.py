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
from datetime import UTC, datetime
from pathlib import Path

# These scripts run three ways — as `python3 .../scripts/x.py` from any cwd,
# imported as a package, and loaded by file path from tests. Only the first puts
# this directory on sys.path, so put it there explicitly before the sibling
# import. See check_wiring_contract.py for the same idiom and why.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import _corrections_lib
except ImportError:  # invoked as a script, or loaded by file path
    import _corrections_lib

CORRECTIONS_REL = ".claude/memory/corrections.md"

#: What counts as an entry now lives in ONE place, shared with every other
#: counter. This script owned a local pattern from 2026-08-03 (when it learned
#: the bullet form) until 2026-08-09, and in that window two OTHER artifacts
#: counted the same file with two other patterns and got two other answers. The
#: local pattern was also still wrong in two ways nobody had looked for — it
#: stopped at `###` so `####` entries were invisible, and its date ended with
#: `\b` so `2026-08-02b` could not match. Neither would ever have surfaced from
#: reading this file alone. See `_corrections_lib` for the full account.

#: The catcher vocabulary, in priority order. First match on an entry wins, so
#: the more specific patterns come first. Derived from the phrasings already in
#: the corpus rather than imposed on it.
#: SEPARATOR WIDENED 2026-09-02 from `by\s+` to `by[^A-Za-z0-9]{0,6}`. The corpus writes
#: the field as `- **Caught by**: the founder`, which puts `**: ` between "by" and the
#: catcher, so `\s+` could not match and a compliant entry classified as None -- while the
#: PreToolUse guard simultaneously warned "no catcher named" against it. Measured on a
#: consumer corpus 2026-09-02: 3 of 10 entries using the bolded field form were affected,
#: and recovering them moved coverage 100 -> 103 of 250. Not wrong data; real data the
#: regex could not see. The bound is 6 rather than unlimited so "caught by" and a catcher
#: word in different clauses do not join up.
CATCHERS: list[tuple[str, re.Pattern[str]]] = [
    ("hook_or_check", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by[^A-Za-z0-9]{0,6}"
        r"(the\s+)?(hook|check|ci|validator|test|sweep|guard|linter|script)", re.IGNORECASE)),
    ("review", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by[^A-Za-z0-9]{0,6}"
        r"(the\s+)?(review|reviewer|code.review|blind|adversar)", re.IGNORECASE)),
    ("agent_self", re.compile(
        r"(agent[- ]self[- ]caught|self[- ]caught"
        r"|caught\s+by[^A-Za-z0-9]{0,6}(the\s+)?agent)", re.IGNORECASE)),
    ("user", re.compile(
        r"(caught|surfaced|found|detected|flagged)\s+by[^A-Za-z0-9]{0,6}"
        r"(the\s+)?(user|founder|operator|human)", re.IGNORECASE)),
]


def _entries(text: str) -> list[tuple[str, str]]:
    """(date, body) per dated entry. Body runs to the next entry of EITHER shape."""
    return _corrections_lib.entries(text)


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


#: Snapshot layout matches the existing metrics convention
#: (.claude/evals/metrics/<source>/<YYYY-MM-DD>.json) rather than inventing one,
#: so the corrections series is readable by whatever already reads the others.
SNAPSHOT_REL = ".claude/evals/metrics/corrections"
ADAPTER_VERSION = 1


def write_snapshot(root: Path, st: dict, snapshot_dir: Path | None = None) -> Path | None:
    """Append today's reading to the metrics series. Returns the path, or None.

    WHY A SERIES (dogfood 2026-08-03). The escape rate existed only as prose in
    hand-written TL;DR paragraphs — three readings across two months, each
    recomputed by someone who remembered to look, and the top-of-file count was
    stale by 46 entries when this was added. A rate whose trend cannot be
    computed answers the wrong question: the useful signal is not the level but
    whether the harness is catching more over time.

    REFUSES TO WRITE A RATE IT DOES NOT HAVE. When no entry carries a catcher
    there is no rate, and storing a null in a series is how a gap becomes a
    number later. Nothing is written in that case.

    Same-day re-runs OVERWRITE: a snapshot is a state-of-day reading, not an
    event log, so a second run on the same date corrects the first rather than
    double-counting it.
    """
    if not st.get("applicable") or not st.get("attributed"):
        return None
    target = snapshot_dir or (root / SNAPSHOT_REL)
    target.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    path = target / f"{now:%Y-%m-%d}.json"
    path.write_text(json.dumps({
        "pulled_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "corrections",
        "source_class": "process-quality",
        "target": str(root / CORRECTIONS_REL),
        "adapter_version": ADAPTER_VERSION,
        "fetch_status": "complete",
        "primary_counts": {
            "entries": st["entries"],
            "attributed": st["attributed"],
            "unattributed": st["unattributed"],
            **{f"caught_by_{k}": v for k, v in sorted(st["by_catcher"].items())},
        },
        "escape_rate": st["escape_rate"],
        "coverage": st["coverage"],
        "note": (
            "Escape rate = share of ATTRIBUTED corrections not caught by a hook, "
            "check, or the agent itself. Read it with `coverage`: a rate over a "
            "quarter of the corpus is indicative, not measured. The signal worth "
            "trending is caught_by_hook_or_check rising in absolute terms, not "
            "the ratio falling, which under-logging would also achieve."
        ),
    }, indent=2) + "\n")
    return path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Escape rate of the correction loop: who caught each mistake."
    )
    p.add_argument("--root", default=".", help="Project root (default: cwd).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    p.add_argument("--snapshot", nargs="?", const="", metavar="DIR",
                   help="Append this reading to the metrics series "
                        f"(default: {SNAPSHOT_REL}/<date>.json).")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    st = scan(root)
    # BEFORE the output branch, deliberately: v0.77.0 found five scripts
    # whose behaviour differed between --json and plain because the work
    # lived inside one arm of the branch.
    snapshot_path = None
    if args.snapshot is not None:
        snapshot_path = write_snapshot(
            root, st, Path(args.snapshot) if args.snapshot else None)
    if args.json:
        if snapshot_path:
            st = {**st, "snapshot": str(snapshot_path)}
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
