#!/usr/bin/env python3
"""Surface climatic predictions that are due, overdue, or were never really at risk.

WHAT THIS GUARDS. `/mycelium:wardley-map` gained a Climate step in v0.95.0 that
emits dated predictions into `landscape.yml#climatic_predictions`. Predictions are
the only part of a Wardley map that can be WRONG — positions cannot be — so they
are the part worth protecting, and they fail in a specific way: nobody scores them.

The failure is not dishonesty. Scoring is boring and mapping is interesting, so an
unscored pile grows quietly until the record means nothing, and the project keeps
experiencing predictable things as news. The dogfood instance that motivated this:
a project watched two of its own lead terms genericise within 24 hours, treated
each as a discovery, and had no mechanism that would have said "you predicted
this". Both were predictable from a pattern the skill did not yet encode.

The Climate step tells the agent to score due predictions FIRST, which handles the
case where someone runs a mapping pass. This script handles the case where nobody
does — it runs from `/mycelium:canvas-health`, which is periodic and does not
depend on anyone feeling like mapping.

WHAT IT REPORTS, and the third one is the point:
  1. DUE / OVERDUE — `status: open` with a `due` date in the past.
  2. UNDATED — an entry with no `due`. A prediction with no date is an opinion;
     it can never be overdue, so it can never be scored, so it is free to be right
     forever. Schema requires `due`, but a schema-less or hand-edited canvas can
     still carry one, and the silent-forever case is exactly what needs surfacing.
  3. NEVER-REFUTED RECORD — if a corpus has scored predictions and NONE are
     `refuted` or `unscoreable`, say so. A forecasting record that has never been
     wrong was not at risk, and a record not at risk is measuring nothing. This is
     advisory and is NOT an error: a young corpus legitimately has few scores. It
     is reported so the reader asks the question, because the failure it points at
     (predictions written soft enough to always hold) is invisible from inside.

Exit codes:
    0  nothing due, nothing undated
    1  at least one prediction is due, overdue, or undated
    2  the check itself could not run

Python stdlib only, so it runs in any consumer regardless of environment.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

# The five patterns the Climate step enumerates. Kept here so the coverage report
# names a pattern that produced nothing — an unused pattern is one nobody applied,
# not one that had nothing to say.
PATTERNS = (
    "everything-evolves",
    "characteristics-change",
    "no-choice-over-evolution",
    "commoditisation-genericisation",
    "inertia",
)

SCORED = ("held", "refuted", "unscoreable")


def _load_predictions(landscape: Path) -> tuple[list[dict], bool, str | None]:
    """Return (predictions, map_exists, error).

    `map_exists` is True when landscape.yml holds components — i.e. somebody has
    actually mapped something. It is the difference between the two silences:

      - No landscape at all: there is NOTHING TO CHECK. This returns an error and
        the caller exits 2 (UNKNOWN), never 0. An earlier draft returned a clean 0
        here with "none recorded — nothing to score", reasoning that flagging a
        fresh project would make the check noise on day one. `check_empty_input_
        honesty.py` rejected that on the first run, correctly: a check that reports
        a pass over an empty repository has verified nothing and said everything is
        fine, which is the exact blind-green shape (opp-023) this project audits
        others for. The rationalisation was persuasive, which is why the guard is a
        mechanism and not a habit.

      - A map WITH components and NO predictions: that is a real finding, not a
        silence. It means Step 7 (Assess Climate) did not run — someone mapped
        positions and emitted nothing that could turn out wrong. That is precisely
        the state this whole release exists to end, and it was invisible until the
        empty-input guard forced the distinction.
    """
    if not landscape.is_file():
        return [], False, f"no landscape.yml at {landscape} — nothing to check"
    try:
        import yaml  # noqa: PLC0415 — optional dep; absence must not crash the check
    except ImportError:
        return [], False, "PyYAML unavailable"
    try:
        data = yaml.safe_load(landscape.read_text()) or {}
    except Exception as exc:  # noqa: BLE001 — any parse failure is UNKNOWN, not clean
        return [], False, f"could not parse {landscape.name}: {exc}"
    if not isinstance(data, dict):
        return [], False, f"{landscape.name} is not a mapping — nothing to check"
    map_exists = bool(data.get("components"))
    preds = data.get("climatic_predictions") or []
    if not isinstance(preds, list):
        return [], map_exists, "climatic_predictions is not a list"
    return [p for p in preds if isinstance(p, dict)], map_exists, None


def _parse_date(value) -> _dt.date | None:
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def analyse(preds: list[dict], today: _dt.date) -> dict:
    due, undated, scored, refuted = [], [], [], []
    seen_patterns = set()

    for p in preds:
        pattern = p.get("pattern")
        if pattern:
            seen_patterns.add(str(pattern))
        status = str(p.get("status", "")).lower()

        if status in SCORED:
            scored.append(p)
            if status in ("refuted", "unscoreable"):
                refuted.append(p)
            continue

        # status is open (or missing, which is treated as open — an entry with no
        # status has not been settled, and defaulting it to settled would be the
        # absent-read-as-negative failure this framework removes elsewhere).
        when = _parse_date(p.get("due"))
        if when is None:
            undated.append(p)
        elif when <= today:
            due.append((p, (today - when).days))

    return {
        "due": due,
        "undated": undated,
        "scored": scored,
        "refuted": refuted,
        "unused_patterns": [x for x in PATTERNS if x not in seen_patterns],
        "total": len(preds),
    }


def _report(res: dict) -> None:
    for p, overdue_by in sorted(res["due"], key=lambda t: -t[1]):
        word = "OVERDUE" if overdue_by > 0 else "DUE"
        by = f" by {overdue_by}d" if overdue_by > 0 else ""
        print(
            f"  {word}{by}: {p.get('id', '?')} [{p.get('pattern', '?')}] "
            f"due {p.get('due')} — {str(p.get('prediction', ''))[:110]}"
        )
    for p in res["undated"]:
        print(
            f"  UNDATED: {p.get('id', '?')} [{p.get('pattern', '?')}] has no `due` — "
            f"it can never be overdue, so it can never be scored."
        )

    if res["scored"] and not res["refuted"]:
        print(
            f"  NOTE (advisory, not an error): {len(res['scored'])} prediction(s) scored, "
            f"NONE refuted or unscoreable. A forecasting record that has never been wrong "
            f"was not at risk. Worth asking whether the predictions are written soft enough "
            f"to always hold."
        )
    if res["unused_patterns"] and res["total"]:
        print(
            f"  COVERAGE: no prediction has ever come from: "
            f"{', '.join(res['unused_patterns'])}. An unused pattern is one nobody "
            f"applied, not one with nothing to say."
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="project root containing .claude/")
    ap.add_argument("--today", default=None, help="ISO date override (testing)")
    args = ap.parse_args()

    # tz-aware per DTZ011: a due-date check that silently uses the machine's
    # local notion of today will disagree with itself across timezones, and the
    # disagreement shows up as a prediction being overdue on one machine and not
    # another. UTC is the one clock every consumer shares.
    today = (
        _parse_date(args.today)
        if args.today
        else _dt.datetime.now(tz=_dt.UTC).date()
    )
    if today is None:
        print("UNKNOWN: --today is not an ISO date", file=sys.stderr)
        return 2

    landscape = Path(args.root) / ".claude" / "canvas" / "landscape.yml"
    preds, map_exists, err = _load_predictions(landscape)
    if err:
        # UNKNOWN, never "clean". A check that cannot run must not report a pass —
        # that is the fail-open shape logged repeatedly in this project's history.
        print(f"UNKNOWN: {err}", file=sys.stderr)
        return 2

    if not preds:
        if map_exists:
            # A map exists and predicts nothing. Step 7 did not run.
            print(
                "Climatic predictions: NONE, but landscape.yml holds components. "
                "A map was built and Step 7 (Assess Climate) emitted nothing — so "
                "nothing on this map can turn out to be wrong. Run "
                "/mycelium:wardley-map and apply the five climatic patterns."
            )
            return 1
        print("UNKNOWN: landscape.yml holds no components — nothing to check", file=sys.stderr)
        return 2

    res = analyse(preds, today)
    if not res["due"] and not res["undated"]:
        print(
            f"Climatic predictions: {res['total']} recorded, "
            f"{len(res['scored'])} scored, none due."
        )
        _report(res)  # advisory notes still worth printing on a clean run
        return 0

    print(
        f"Climatic predictions: {len(res['due'])} due/overdue, "
        f"{len(res['undated'])} undated, of {res['total']} recorded."
    )
    _report(res)
    return 1


if __name__ == "__main__":
    sys.exit(main())
