#!/usr/bin/env python3
"""next_item.py — one proposal per boundary, with its verb attached.

WHY THIS EXISTS (dogfood 2026-09-10, opp-006 sol-006f, ruled "build now"). The session-start hook
emitted every advisory it computed in one block, eleven in one line on the dogfood canvas, to the
agent only. The 2026-09-09 discovery's F4 and F6: boundary-timed single items are engaged with (52%
at workflow boundaries against 62% dismissed mid-task; 45 s to read against 101 s), and every
unanswered line is paid for by the reader who does not act on it. The products that work attach the
verb to the item (incident.io buttons; Linear Triage accept / duplicate / decline / snooze).
Founder, the same day: "inexperienced builders can't be asking for tasks they don't know should be
happening", so the item carries the exact command, not a hint.

WHAT IT DOES. Given the assembled advisory text and the project, picks ONE item and prints it as
JSON: an id, one sentence, the command that does it, and the fixed verb set. Priority, in order:
  1. a parked CLOSING PATH FIRED proposal (a named input landed; the ruling is on the human's desk)
  2. a muted advisory awaiting a ruling (the ledger asked; nothing answered)
  3. an advisory with a mapped command, OLDEST FIRING STREAK FIRST (the ledger's streak start)
Items ruled `drop`, or `snooze` with a date still ahead, are skipped. Nothing qualifying prints
nothing, and the hook says nothing; silence is the correct output for a clean canvas.

THE VERBS. run (the command), rule (a human ruling where the item is a proposal), snooze-until DATE
(`advisory_ledger.py rule --id <id> --ruling snooze --until DATE`), drop (`--ruling drop`). The
agent-facing advisory block is unchanged; this is the one line for the human, and the hook emits it
as a `systemMessage` on resume and fork, which is the re-entry moment the record names (Alex,
ht-057: "after a long gap, I'd want Mycelium to very quickly tell me where I am ... and what I
should probably do next").

STATE. `.claude/state/next-item.json`: the item last emitted, when, by which session, and whether
the Stop hook has repeated it once. Read by hooks/next-item-repeat.sh.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # spoken by _fired_proposals: fired proposals are then reported as unread
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import advisory_ledger as al
except ImportError:  # spoken by _ledger_state: streaks and rulings are then reported as unread
    al = None

#: advisory id -> (one-sentence item, command). Ids are advisory_ledger.py signature ids.
COMMANDS: dict[str, tuple[str, str]] = {
    "bvssh-overdue": ("The BVSSH health check is overdue.", "/mycelium:bvssh-check"),
    "bvssh-never-assessed": ("BVSSH health has never been assessed.", "/mycelium:bvssh-check"),
    "bvssh-orphan-assessments": (
        "BVSSH assessments sit in the log and not on the canvas.",
        "/mycelium:bvssh-check",
    ),
    "delivery-metrics-stale": ("Delivery metrics are stale.", "/mycelium:metrics-pull"),
    "ai-tool-metrics-stale": ("AI-tool metrics are stale.", "/mycelium:metrics-pull"),
    "metrics-never-measured": (
        "Delivery metrics have never been measured.",
        "/mycelium:dora-check",
    ),
    "open-human-tasks": ("Open human tasks are waiting on a read.", "/mycelium:log-evidence"),
    "reply-owed": ("Someone wrote and has not been answered.", "/mycelium:log-evidence"),
    "read-due": (
        "A pre-registered read fell due and is not recorded on its task.",
        "/mycelium:log-evidence",
    ),
    "corrections-to-cluster": (
        "Corrections have not been read against the cluster catalogue.",
        "/mycelium:corrections-audit",
    ),
    "decided-leaves-no-four-risks": (
        "Decided leaves carry no four-risks block.",
        "/mycelium:ost-builder",
    ),
    "shipped-leaves-no-ice": ("Shipped leaves carry no ICE score.", "/mycelium:ice-score"),
    "idle-opportunities": ("Open opportunities have no reader.", "/mycelium:canvas-health"),
    "runnable-never-run": (
        "A designed test can run from disk and never has.",
        "/mycelium:assumption-test",
    ),
    "diamonds-no-dod": ("A diamond has no outcome Definition of Done.", "/mycelium:define-done"),
    "outcome-check-due": ("A shipped diamond is due its outcome check.", "/mycelium:metrics-pull"),
    "outcome-signal-no-measure": (
        "A shipped diamond has a signal but no measure.",
        "/mycelium:define-done",
    ),
    "evidence-never-landed": (
        "Completed tasks have findings that never reached the canvas.",
        "/mycelium:log-evidence",
    ),
    "evidence-landing-regressed": (
        "Evidence landing regressed against the baseline.",
        "/mycelium:canvas-health",
    ),
    "stale-prose": (
        "A record carries prose that may have outlived the field beside it.",
        "/mycelium:canvas-health",
    ),
    "unchecked-handle": (
        "A public handle is cited as evidence with no note that anyone checked it.",
        "/mycelium:canvas-health",
    ),
    "source-class-fidelity": (
        "An evidence source is labelled external_human against its own text.",
        "/mycelium:canvas-health",
    ),
    "published-source-dead": (
        "A published record names a source file that is gone.",
        "/mycelium:canvas-health",
    ),
    "cycle-record-owed": ("Releases shipped with no cycle record.", "/mycelium:retrospective"),
    "cycle-never-recorded": ("No cycle has ever been recorded.", "/mycelium:retrospective"),
    "external-evidence-thin": ("External evidence is thin.", "/mycelium:handoff"),
    "external-evidence-all-desk": ("Every evidence source is desk-derived.", "/mycelium:handoff"),
    "brownfield-entry": ("This project has code and no discovery state.", "/mycelium:adopt"),
}
VERBS = ("run", "rule", "snooze-until", "drop")
STATE_REL = Path(".claude") / "state" / "next-item.json"


def _ledger_state(root: Path):
    """The advisory ledger's derived state, or {} when the ledger module is unavailable."""
    if al is None:
        return {}, "advisory ledger module unavailable; streaks and rulings unread"
    events, problems = al.read_events(al.ledger_path(root))
    return al.state(events), ("; ".join(problems) if problems else "")


def _blocked(x: dict, today: str) -> bool:
    if not x:
        return False
    if x.get("ruling") == "drop":
        return True
    su = x.get("snoozed_until")
    return bool(su) and str(su) >= today


def _fired_proposals(root: Path) -> tuple[list[dict], str]:
    """Parked CLOSING PATH FIRED proposals on any diamond, oldest first; and a note when the
    diamonds file could not be read, so an unread proposal is never mistaken for none."""
    p = root / ".claude" / "diamonds" / "active.yml"
    if not p.exists():
        return [], ""
    if yaml is None:
        return [], "PyYAML unavailable; fired closing-path proposals unread"
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:
        return [], f"diamonds/active.yml unreadable ({type(e).__name__}); fired proposals unread"
    out = [
        {
            "id": f"fired:{f.get('id')}",
            "diamond": d.get("id"),
            "since": str(f.get("noticed_at") or ""),
            "text": str(f["proposal"]),
            "command": f"/mycelium:diamond-progress {d.get('id')}",
        }
        for key in ("active_diamonds", "diamonds")
        for d in (doc.get(key) or [])
        if isinstance(d, dict)
        for f in ((d.get("closes_on") or {}).get("fired") or [])
        if isinstance(f, dict) and f.get("proposal")
    ]
    return sorted(out, key=lambda r: r["since"]), ""


_CLOSED = {"complete", "completed", "killed", "parked", "archived"}
_NEXT = {"discover": "define", "define": "develop", "develop": "deliver", "deliver": "complete"}


def _newest_evidence(root: Path) -> str:
    """The newest date any canvas file or research note was written (YYYY-MM-DD), or ''."""
    stamps = [f.stat().st_mtime for pat in (".claude/canvas/*.yml", "research/**/*")
              for f in root.glob(pat) if f.is_file()]
    return (_dt.datetime.fromtimestamp(max(stamps), tz=_dt.UTC).date().isoformat()
            if stamps else "")


def _unassessed(root: Path, today: str) -> list[dict]:
    """Open diamonds whose phase nobody has assessed: never ruled on, or ruled on before the newest
    evidence landed (v0.249.0). E2E run 18, the first happy-path run built to test Mycelium's own
    behaviour: four diamonds sat in discover for three sessions with no ruling while research notes
    arrived every session, and nothing in Mycelium proposed the step that moves them. Only a FIRED
    closing path was ever proposed, so a diamond moved only if the driver remembered to move it.
    Delivering diamonds (L3 and up) come first: they carry the path to a release."""
    p = root / ".claude" / "diamonds" / "active.yml"
    if yaml is None or not p.exists():
        return []
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return []  # SPEAKS: _fired_proposals reads the same file and reports it unreadable
    newest = _newest_evidence(root)
    out = []
    for d in doc.get("active_diamonds") or []:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        phase = str(d.get("phase") or "discover").lower()
        if phase in _CLOSED or phase not in _NEXT:
            continue
        ruled = str(d.get("progression_ruled_at") or "")[:10]
        if ruled and ruled >= newest:
            continue  # ruled on since the newest evidence: nothing new to assess
        scale = str(d.get("scale") or "").upper()
        why = (f"has never been assessed, so it has never moved from {phase}" if not ruled
               else f"was last ruled on {ruled}, and evidence has landed since")
        out.append({"id": f"unassessed:{d['id']}", "diamond": d["id"],
                    "since": ruled or str(d.get("created") or today)[:10],
                    "rank": (0 if scale in ("L3", "L4", "L5") else 1, ruled or ""),
                    "text": f"{d['id']} ({scale}) {why}. Its next transition is "
                            f"{phase} -> {_NEXT[phase]}.",
                    "command": f"/mycelium:diamond-progress {d['id']}"})
    return sorted(out, key=lambda r: r["rank"])


def pick(root: Path, reminders: str, today: str) -> tuple[dict | None, str]:
    """The one item, and a note when something could not be read."""
    st, note = _ledger_state(root)
    ids = set(al.scan(reminders)) if al is not None else set()
    fired, fnote = _fired_proposals(root)
    note = "; ".join(x for x in (note, fnote) if x)
    # 1. fired proposals
    for f in fired:
        if not _blocked(st.get(f["id"], {}), today):
            return {**f, "why": "a named input on a closing path landed; the ruling is yours"}, note
    # 2. a diamond whose phase nobody has assessed since the evidence changed (v0.249.0)
    for u in _unassessed(root, today):
        if not _blocked(st.get(u["id"], {}), today):
            item = {k: v for k, v in u.items() if k != "rank"}
            why = "the path to a release moves only when a diamond is assessed"
            return {**item, "why": why}, note
    # 3. muted advisories awaiting a ruling
    muted = [
        (x.get("muted_since") or "", aid)
        for aid, x in st.items()
        if x.get("muted_since") and not _blocked(x, today)
    ]
    for since, aid in sorted(muted):
        text, cmd = COMMANDS.get(
            aid, (f"Advisory {aid} is muted and awaits a ruling.", "/mycelium:canvas-health")
        )
        return {
            "id": aid,
            "since": since,
            "text": f"{text} It has been muted since {since} with no ruling.",
            "command": cmd,
            "why": "muted; the ledger asked for a ruling and none was recorded",
        }, note
    # 4. present advisories with a command, oldest streak first
    cands = []
    for aid in ids:
        if aid not in COMMANDS or _blocked(st.get(aid, {}), today):
            continue
        x = st.get(aid) or {}
        since = (x.get("streak_days") or [today])[0]
        cands.append((since, aid))
    for since, aid in sorted(cands):
        text, cmd = COMMANDS[aid]
        days = (
            max(0, (_dt.date.fromisoformat(today) - _dt.date.fromisoformat(since)).days)
            if since
            else 0
        )
        return {
            "id": aid,
            "since": since,
            "text": text
            + (f" It has fired on session starts since {since} ({days} day(s))." if days else ""),
            "command": cmd,
            "why": "the oldest advisory with a command",
        }, note
    return None, note


_UT_OPEN, _UT_CLOSE = "<untrusted_user_content>", "</untrusted_user_content>"


def _untrusted(text: str) -> str:
    """Canvas-derived prose reaches the agent as DATA, never as instruction (security review
    DL-1262, finding 1). Same escaping session-start.sh applies to task objectives: a closing
    tag inside the text cannot end the wrapper early."""
    return _UT_OPEN + text.replace(_UT_CLOSE, "</untrusted_user_content_ESCAPED>") + _UT_CLOSE


def render_human(item: dict, limit: int = 240) -> str:
    """The systemMessage form: plain, no tags, bounded. A human reads it, a wrapper means nothing
    to them, and a canvas string cannot be allowed to fill the screen."""
    text = " ".join(str(item["text"]).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return f"NEXT ITEM: {text} run `{item['command']}` | rule | snooze-until DATE | drop."


def render(item: dict) -> str:
    text = str(item["text"])
    if str(item.get("id", "")).startswith("fired:"):
        text = _untrusted(text)  # a proposal read back from active.yml is canvas content
    return (
        f"NEXT ITEM: {text} run `{item['command']}` | rule (say what you decide) | "
        f"snooze-until DATE (`advisory_ledger.py rule --id {item['id']} "
        "--ruling snooze --until DATE`) | "
        f"drop (`--ruling drop`)."
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One proposal per boundary, with its verb attached.")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--session", default="unknown")
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    ap.add_argument(
        "--write-state",
        action="store_true",
        help="record the emitted item in .claude/state/next-item.json",
    )
    ap.add_argument(
        "--json", action="store_true", help="print the item as JSON instead of the one line"
    )
    ap.add_argument(
        "--human", action="store_true", help="also print the plain, bounded systemMessage form"
    )
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    reminders = sys.stdin.read() if not sys.stdin.isatty() else ""
    item, note = pick(root, reminders, args.today)
    if note:
        print(
            f"next-item: {note}"
        )  # stdout: the hook drops stderr, and an unread source must be said
    if item is None:
        return 0
    if args.write_state:
        p = root / STATE_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "id": item["id"],
                    "text": render(item),
                    "text_human": render_human(item),
                    "session": args.session,
                    "emitted_at": args.today,
                    "repeated_at_stop": False,
                },
                ensure_ascii=False,
            )
        )
    print(json.dumps(item, ensure_ascii=False) if args.json else render(item))
    if args.human:
        print(render_human(item))
    return 0


if __name__ == "__main__":
    sys.exit(main())
