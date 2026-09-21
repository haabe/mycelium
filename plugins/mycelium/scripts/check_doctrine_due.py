#!/usr/bin/env python3
"""check_doctrine_due.py — is a doctrine retrospective due, per its own firing condition?

WHY THIS EXISTS (dogfood, 2026-09-21). v0.231.0 gave the doctrine retrospective a firing
condition — due when `doctrine.yml#last_reviewed` is absent or older than the newest
`completed_at` in `diamonds/active.yml#completed_diamonds` — and wired the producer
(`/retrospective`) to the consumer (`/wardley-map`). **Nothing evaluated the condition.**
It lived as prose inside a skill, so it fired only when someone happened to open that skill,
which is the same "runs when a person remembers" shape the condition was written to replace.
A condition with no evaluator is a condition that reads as satisfied.

Every comparable due-concept in this framework already has an evaluator wired into
session-start — `check_reply_owed.py`, `check_reads_due.py`, the advisory ledger. This is that,
for doctrine, deliberately in the same one-advisory-line shape so session-start and the ledger
pick it up without a second rule to diverge from.

TWO REASONS IT CAN BE DUE, and both are reported:
  1. A diamond completed after the last doctrine review (or there has never been one).
     Wardley's producer is a retrospective: "look for what has changed and always ask why?"
  2. A climate prediction is past its horizon and still unscored. An unscored prediction is
     not a held one, and a register that only ever grows predictions is a wish list.

Output: one "DOCTRINE RETROSPECTIVE DUE: ..." line when due, "OK: ..." otherwise. **Exit 0 in
both cases** — this is an advisory, not a gate. A file that cannot be read is said out loud and
never silently counted as "nothing due".
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

import yaml

_UNSCORED = {None, "", "unscored"}


def _load(path: Path) -> tuple[object, str | None]:
    """(document, error). A missing file is not an error; an unreadable one is."""
    if not path.is_file():
        return None, None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except (OSError, yaml.YAMLError) as exc:
        return None, f"{path.name}: {exc}"


def newest_completion(diamonds_doc: object) -> tuple[str | None, int]:
    """(newest completed_at, how many completed diamonds were seen)."""
    if not isinstance(diamonds_doc, dict):
        return None, 0
    rows = diamonds_doc.get("completed_diamonds") or []
    if not isinstance(rows, list):
        return None, 0
    dates = [
        str(r.get("completed_at"))
        for r in rows
        if isinstance(r, dict) and r.get("completed_at")
    ]
    return (max(dates) if dates else None), len(rows)


def overdue_predictions(doctrine_doc: object, today: str) -> list[str]:
    """Climate entries whose horizon has passed with no outcome recorded."""
    if not isinstance(doctrine_doc, dict):
        return []
    rows = doctrine_doc.get("climate") or []
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        horizon = r.get("horizon")
        if not horizon or str(horizon) > today:
            continue
        if r.get("outcome") in _UNSCORED:
            out.append(str(r.get("id") or "<unnamed>"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    args = ap.parse_args(argv)

    root = Path(args.project_dir)
    diamonds_doc, d_err = _load(root / ".claude/diamonds/active.yml")
    doctrine_doc, c_err = _load(root / ".claude/canvas/doctrine.yml")

    # SAY IT, DO NOT SWALLOW IT. An unreadable register is the one case where
    # "nothing due" and "could not look" are indistinguishable from the outside.
    for err in (d_err, c_err):
        if err:
            print(f"UNREADABLE (doctrine due-check did NOT run): {err}")
            return 0

    newest, n_completed = newest_completion(diamonds_doc)
    last_reviewed = None
    if isinstance(doctrine_doc, dict):
        last_reviewed = doctrine_doc.get("last_reviewed")
    last_reviewed = str(last_reviewed) if last_reviewed else None

    reasons = []
    if newest and (last_reviewed is None or last_reviewed < newest):
        since = "never reviewed" if last_reviewed is None else f"last reviewed {last_reviewed}"
        reasons.append(f"a diamond completed {newest} ({since})")
    stale = overdue_predictions(doctrine_doc, args.today)
    if stale:
        reasons.append(
            f"{len(stale)} climate prediction(s) past horizon and unscored: {', '.join(stale[:5])}"
        )

    if reasons:
        print(
            "DOCTRINE RETROSPECTIVE DUE: "
            + "; ".join(reasons)
            + ". Run /mycelium:retrospective's doctrine step — ask what changed and why, add any "
            "doctrine with the incident behind it, score due climate predictions (`unclear` is a "
            "real answer), then stamp `last_reviewed`. An empty register after a review is a "
            "legitimate outcome; write the stamp anyway or this fires forever."
        )
        return 0

    if not n_completed:
        print(
            "OK: no diamond has entered completed_diamonds yet, so the doctrine trigger cannot "
            "fire. This is NOT 'doctrine is current' — nothing has been reviewable."
        )
        return 0

    print(
        f"OK: doctrine reviewed {last_reviewed}, newest completion {newest} "
        f"({n_completed} completed diamond(s)); no climate prediction past horizon."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
