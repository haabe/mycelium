#!/usr/bin/env python3
"""advisory_ledger.py — every advisory counts whether anything follows; mutes itself otherwise.

WHY THIS EXISTS (dogfood, 2026-09-09, opp-006 sol-006d). The session-start hook computes some twenty
advisories and emits them in one block. Nothing records whether the named remedy ever happens, so a
check that has fired daily for a month with no response is indistinguishable from one acted on every
time. Measured the night it was designed: "BVSSH health check is 32 days overdue" and "AI tool
metrics are 101 days old" had fired at every session start for as long as their numbers say, and
the BVSSH
assessment that finally ran rated Measurement amber for the THIRD consecutive time on exactly this.
The evidence behind the design is in the dogfood research file for 2026-09-09: every reminder is
paid for by the reader who does not act on it (Damgaard and Gravert 2018), false alarms cause
disuse of the whole system (Parasuraman and Riley 1997), fatigue is measured as a sustained decay in
response to
APPROPRIATE alerts (Ray-Wilson 2026), and the products that survive mute by instance or mute
themselves first. This repo's own rule since 2026-08-11: a muted check looks like coverage.

WHAT IT MEASURES, and what it does not. It does not know what remedy a human took. It knows whether
the CONDITION CLEARED: an advisory present at one session start and absent at the next was acted on,
or the world moved; present again with the same or a larger count, it was not. That is the k8s
reading of "did the remedy happen" (re-derive, compare), it needs no per-check detector, and it is
honest about the two shapes it cannot see: an advisory whose remedy is "read it and leave it" never
clears (the check must honour a reviewed marker, which is the check's job), and an awareness-only
line (the corrections count) is not an advisory and is not counted.

THREE VERBS.
  settle  — reads this session's advisory text on stdin, records which advisories are present (by a
            signature registry below, with a count where the text carries one), settles the previous
            session's advisories as cleared / still_firing, applies mutes, and prints the text back
            with muted advisories replaced by one line each. On ANY failure it prints the original
            text plus one line saying the ledger could not run: the hook must never go quiet because
            its ledger did.
  report  — per advisory: sessions seen, cleared, still firing, clear rate, current firing streak in
            distinct days, muted since, ruling. For canvas-health, so Measurement can cite a number.
  rule    — records a human ruling on a muted advisory: keep (unmute, reset the streak), fix (stay
            muted until the condition clears on its own), drop (never show again; the report still
            lists it as dropped so the silence is visible).

THE MUTE RULE. An advisory still firing on MUTE_DAYS distinct calendar days in a row with no
clearing between them is muted: the hook shows one line ("fired on N days since DATE, nothing
followed; muted
until you rule: keep / fix / drop") instead of the advisory. Muting is a request for a ruling, not a
deletion; the report keeps counting. The threshold is in distinct DAYS, not sessions, because a busy
day opens many sessions and would otherwise mute a check the same afternoon it first fired.

STATE. `.claude/state/advisory-ledger.jsonl`, append-only events:
  {"kind":"seen","session":S,"date":D,"ids":{id:count|null}}
  {"kind":"settled","session":S,"date":D,"results":{id:"cleared"|"still_firing"}}
  {"kind":"muted","id":I,"date":D,"streak_days":N,"since":D0}
  {"kind":"ruled","id":I,"date":D,"ruling":"keep"|"fix"|"drop","note":...}

SPEAKS. A ledger line that does not parse is reported and skipped, never silently discarded; a
missing project directory prints N/A and exits 0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

LEDGER_REL = Path(".claude") / "state" / "advisory-ledger.jsonl"
MUTE_DAYS = 7
RULINGS = ("keep", "fix", "drop", "snooze")

#: (id, regex). A regex with a `count` group carries a number whose DECREASE reads as cleared. Ages
#: ("N days overdue", "N days old") are deliberately NOT count groups: they rise while unaddressed.
#: Ordered so that the more specific pattern wins where two could match.
SIGNATURES: list[tuple[str, str]] = [
    ("state-file-broken", r"STATE-FILE BROKEN"),
    ("bvssh-never-assessed", r"BVSSH health has never been assessed"),
    ("bvssh-overdue", r"BVSSH health check is \d+ days overdue"),
    ("bvssh-orphan-assessments", r"BVSSH assessment\(s\) .{0,200}? NOT in bvssh-health"),
    (
        "cycle-record-owed",
        r"(?P<count>\d+) minor releases have shipped since the last recorded cycle",
    ),
    ("cycle-record-unmeasurable", r"Work-recording check could not measure here"),
    ("cycle-never-recorded", r"No cycle has ever been recorded here"),
    (
        "corrections-to-cluster",
        r"(?P<count>\d+) correction\(s\) logged since the last cluster instance",
    ),
    ("shipped-leaves-no-ice", r"(?P<count>\d+) shipped solution leaf/leaves carry no ICE"),
    ("decided-leaves-no-four-risks", r"(?P<count>\d+) solution leaf/leaves passed a decision"),
    ("published-source-dead", r"(?P<count>\d+) published record/records name a source file"),
    ("published-missing-fields", r"Published record\(s\) missing an address"),
    ("stale-prose", r"(?P<count>\d+) record\(s\) carry prose that may have outlived"),
    ("unchecked-handle", r"(?P<count>\d+) record\(s\) cite a public handle as external evidence"),
    ("source-class-fidelity", r"(?P<count>\d+) evidence source\(s\) are labelled external_human"),
    ("reply-owed", r"REPLY OWED on (?P<count>\d+) task"),
    ("read-due", r"READ DUE on (?P<count>\d+) task"),
    ("evidence-never-landed", r"EVIDENCE NEVER LANDED on (?P<count>\d+)"),
    ("evidence-landing-regressed", r"EVIDENCE LANDING REGRESSED"),
    ("idle-opportunities", r"IDLE OPPORTUNITIES — (?P<count>\d+) open node"),
    ("runnable-never-run", r"RUNNABLE, NEVER RUN — (?P<count>\d+) live instrument"),
    ("delivery-metrics-stale", r"Delivery metrics are \d+ days old"),
    ("ai-tool-metrics-stale", r"AI tool metrics are \d+ days old"),
    ("metrics-never-measured", r"metrics have never been measured"),
    ("external-evidence-all-desk", r"All \d+ evidence sources are desk-derived"),
    ("external-evidence-thin", r"External evidence is thin \((?P<count>\d+)/\d+"),
    ("open-human-tasks", r"You have (?P<count>\d+) OPEN human task"),
    ("assumption-test-counter", r"Assumption-test '[^']+' is on session"),
    ("memory-poisoning-watch", r"POISONING WATCH"),
    ("cross-repo-activity", r"\[canvas IDs: "),
    ("diamonds-no-dod", r"(?P<count>\d+) diamond\(s\) have no outcome Definition of Done"),
    ("outcome-check-due", r"(?P<count>\d+) shipped diamond\(s\) due an outcome-check"),
    (
        "outcome-signal-no-measure",
        r"(?P<count>\d+) shipped diamond\(s\) have a signal but no measure",
    ),
    (
        "outcome-measure-no-completed-at",
        r"(?P<count>\d+) shipped diamond\(s\) have a measure but no completed_at",
    ),
    ("brownfield-entry", r"BROWNFIELD ENTRY:"),
]
_COMPILED = [(i, re.compile(p)) for i, p in SIGNATURES]


# ---------------------------------------------------------------- parsing


def scan(text: str) -> dict[str, int | None]:
    """Advisory ids present in the text, with a count where the signature carries one."""
    found: dict[str, int | None] = {}
    for aid, rx in _COMPILED:
        m = rx.search(text)
        if m:
            c = m.groupdict().get("count")
            found[aid] = int(c) if c is not None else None
    return found


def _spans(text: str) -> list[tuple[str, int]]:
    """(id, start offset) for each signature found, sorted by position; segments run to the next."""
    out = []
    for aid, rx in _COMPILED:
        m = rx.search(text)
        if m:
            out.append((aid, m.start()))
    return sorted(out, key=lambda t: t[1])


def replace_segments(text: str, replacements: dict[str, str]) -> str:
    """Replace the segment belonging to each id in `replacements` with its line. A segment runs from
    the signature match to the next signature match (or the end); text before the first signature
    is untouched. Best effort by construction: an advisory whose signature is unknown stays with the
    segment before it, and is reported as unregistered by `report`."""
    spans = _spans(text)
    if not spans:
        return text
    pieces = [text[: spans[0][1]]]
    for i, (aid, start) in enumerate(spans):
        end = spans[i + 1][1] if i + 1 < len(spans) else len(text)
        seg = text[start:end]
        pieces.append(replacements[aid] + " " if aid in replacements else seg)
    return "".join(pieces)


# ---------------------------------------------------------------- ledger io


def ledger_path(root: Path) -> Path:
    return root / LEDGER_REL


def read_events(path: Path) -> tuple[list[dict], list[str]]:
    """Events plus one problem string per line that did not parse. Never silently drops a line."""
    events, problems = [], []
    if not path.exists():
        return events, problems
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {n}: {e}")
            continue
        if not isinstance(ev, dict) or "kind" not in ev:
            problems.append(f"line {n}: not an event object")
            continue
        events.append(ev)
    return events, problems


def append_events(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- state derivation


def state(events: list[dict]) -> dict[str, dict]:  # noqa: C901, PLR0912 — one pass, four event kinds
    """Per-advisory derived state from the event stream, in order."""
    st: dict[str, dict] = {}

    def s(aid):
        return st.setdefault(
            aid,
            {
                "seen": 0,
                "cleared": 0,
                "still_firing": 0,
                "streak_days": [],
                "muted_since": None,
                "snoozed_until": None,
                "ruling": None,
                "first_seen": None,
                "last_seen": None,
                "last_count": None,
            },
        )

    for ev in events:
        k = ev.get("kind")
        if k == "seen":
            for aid, c in (ev.get("ids") or {}).items():
                x = s(aid)
                x["seen"] += 1
                x["first_seen"] = x["first_seen"] or ev.get("date")
                x["last_seen"] = ev.get("date")
                x["last_count"] = c
                d = ev.get("date")
                if d and (not x["streak_days"] or x["streak_days"][-1] != d):
                    x["streak_days"].append(d)
        elif k == "settled":
            for aid, r in (ev.get("results") or {}).items():
                x = s(aid)
                if r == "cleared":
                    x["cleared"] += 1
                    x["streak_days"] = []
                    if x["ruling"] == "fix":
                        x["muted_since"] = None
                        x["ruling"] = None
                else:
                    x["still_firing"] += 1
        elif k == "muted":
            x = s(ev.get("id"))
            x["muted_since"] = ev.get("since") or ev.get("date")
        elif k == "ruled":
            x = s(ev.get("id"))
            r = ev.get("ruling")
            x["ruling"] = r
            if r == "snooze":
                x["snoozed_until"] = ev.get("until")
                x["ruling"] = None
            if r == "keep":
                x["muted_since"] = None
                x["streak_days"] = []
                x["ruling"] = None
    return st


def last_seen_event(events: list[dict]) -> dict | None:
    for ev in reversed(events):
        if ev.get("kind") == "seen":
            return ev
    return None


# ---------------------------------------------------------------- verbs


def settle(root: Path, session: str, text: str, today: str) -> tuple[str, list[dict], list[str]]:  # noqa: C901 — one pass over present ids
    """Returns (text to emit, events appended, notes). Pure apart from the ledger append."""
    path = ledger_path(root)
    events, problems = read_events(path)
    notes = [f"advisory ledger: {p}" for p in problems]
    present = scan(text)
    new_events: list[dict] = []

    prev = last_seen_event(events)
    if prev and prev.get("session") != session:
        results = {}
        for aid, c0 in (prev.get("ids") or {}).items():
            if aid not in present:
                results[aid] = "cleared"
            else:
                c1 = present[aid]
                results[aid] = (
                    "cleared" if (c0 is not None and c1 is not None and c1 < c0) else "still_firing"
                )
        if results:
            new_events.append(
                {"kind": "settled", "session": session, "date": today, "results": results}
            )
    elif prev and prev.get("session") == session:
        notes.append("advisory ledger: same session seen twice; not settled against itself")

    new_events.append({"kind": "seen", "session": session, "date": today, "ids": present})

    st = state(events + new_events)
    replacements: dict[str, str] = {}
    for aid in present:
        x = st[aid]
        if x["ruling"] == "drop":
            replacements[aid] = ""
            continue
        if x.get("snoozed_until") and str(x["snoozed_until"]) >= today:
            replacements[aid] = ""  # snoozed: silent until the date; the report still counts it
            continue
        if x["muted_since"] is None and len(x["streak_days"]) >= MUTE_DAYS:
            since = x["streak_days"][0]
            new_events.append(
                {
                    "kind": "muted",
                    "id": aid,
                    "date": today,
                    "streak_days": len(x["streak_days"]),
                    "since": since,
                }
            )
            x["muted_since"] = since
        if x["muted_since"] is not None:
            n = len(x["streak_days"])
            replacements[aid] = (
                f"MUTED ADVISORY {aid}: fired on {n} day(s) since {x['muted_since']}, nothing "
                f"followed; muted until you rule (advisory_ledger.py rule --id {aid} "
                f"--ruling keep|fix|drop)."
            )

    append_events(path, new_events)
    out = replace_segments(text, replacements) if replacements else text
    return out, new_events, notes


def _snoozed_label(x: dict) -> str:
    return f"snoozed until {x['snoozed_until']}" if x.get("snoozed_until") else "-"


def report_lines(root: Path) -> list[str]:
    path = ledger_path(root)
    events, problems = read_events(path)
    lines = []
    if not events and not problems:
        rel = path.relative_to(root)
        return [f"advisory ledger: N/A — no ledger at {rel}; nothing has been recorded yet"]
    lines.extend(f"advisory ledger: {p} (skipped, not discarded)" for p in problems)
    st = state(events)
    sessions = sum(1 for e in events if e.get("kind") == "seen")
    lines.append(f"advisory ledger: {sessions} session(s) recorded, {len(st)} advisory id(s) seen")
    lines.append(
        "id | seen | cleared | still_firing | clear_rate | streak_days | muted_since | ruling"
    )
    for aid, x in sorted(st.items(), key=lambda kv: (-len(kv[1]["streak_days"]), kv[0])):
        settled = x["cleared"] + x["still_firing"]
        rate = f"{x['cleared'] / settled:.2f}" if settled else "-"
        lines.append(
            f"{aid} | {x['seen']} | {x['cleared']} | {x['still_firing']} | {rate} | "
            f"{len(x['streak_days'])} | {x['muted_since'] or '-'} | "
            f"{x['ruling'] or _snoozed_label(x)}"
        )
    firing = [a for a, x in st.items() if len(x["streak_days"]) >= MUTE_DAYS]
    if firing:
        lines.append(
            f"{len(firing)} advisory id(s) at or past the {MUTE_DAYS}-day mute threshold: "
            + ", ".join(sorted(firing))
        )
    return lines


def rule(  # noqa: PLR0913, PLR0917 — a CLI verb with one argument per flag
    root: Path, aid: str, ruling: str, note: str, today: str, until: str = ""
) -> str:
    if ruling not in RULINGS:
        return f"advisory ledger: ruling must be one of {', '.join(RULINGS)}"
    if ruling == "snooze" and not until:
        return "advisory ledger: snooze needs --until YYYY-MM-DD"
    ev = {"kind": "ruled", "id": aid, "date": today, "ruling": ruling, "note": note}
    if until:
        ev["until"] = until
    append_events(ledger_path(root), [ev])
    tail = f" until {until}" if until else ""
    return f"advisory ledger: {aid} ruled {ruling}{tail} on {today}"


# ---------------------------------------------------------------- cli


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Count whether anything follows an advisory; mute what nothing follows."
    )
    ap.add_argument("verb", choices=("settle", "report", "rule"))
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--session", default="")
    ap.add_argument("--today", default=datetime.now(tz=UTC).date().isoformat())
    ap.add_argument("--id", default="")
    ap.add_argument("--ruling", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--until", default="", help="for --ruling snooze: silent until this date")
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()

    if args.verb == "settle":
        text = sys.stdin.read()
        if not (root / ".claude").is_dir():
            print(text, end="")
            print(
                f"\nadvisory ledger: N/A — no .claude directory under {root}; "
                "text passed through unrecorded.",
                end="",
            )
            return 0
        try:
            out, _, notes = settle(root, args.session or "unknown", text, args.today)
        except Exception as e:  # noqa: BLE001 — SPEAKS: the hook never goes quiet because its ledger did
            print(text, end="")
            print(
                f"\nadvisory ledger could not run ({type(e).__name__}: {e}); "
                "advisories passed through unrecorded.",
                end="",
            )
            return 0
        print(out, end="")
        for n in notes:
            print("\n" + n, end="")
        return 0
    if args.verb == "report":
        for line in report_lines(root):
            print(line)
        return 0
    if not args.id or not args.ruling:
        print("advisory ledger: rule needs --id and --ruling keep|fix|drop")
        return 2
    print(rule(root, args.id, args.ruling, args.note, args.today, args.until))
    return 0


if __name__ == "__main__":
    sys.exit(main())
