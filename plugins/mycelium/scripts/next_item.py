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
try:
    import diamond_rulings as dr
except ImportError:  # a partial install: _unassessed falls back to the typed ruling date
    dr = None

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
LOG_REL = Path(".claude") / "state" / "next-item-log.jsonl"

# THE LADDER (v0.250.0). E2E run 19: the agent had the same next item in its context for 16
# sessions and never acted, and the human line said the same words every session. Nothing
# counted, so nothing escalated. What the evidence says, and what each rung takes from it:
#   - identical repetition decays after the SECOND showing (Anderson et al., CHI 2015; each repeat
#     of one clinical alert cut acceptance odds ~30%, Ancker 2017), so a repeat carries new facts,
#     how long and how often it has gone unanswered, never the same words;
#   - an escalation ladder stops on acknowledgement (PagerDuty escalation policies), so ANY ruling
#     on the id resets the count, and an item re-escalates only if it goes unanswered again;
#   - an explicit choice beats a glance and a hard stop harms (Bravo-Lillo, SOUPS 2014; Carroll,
#     QJE 2009; Strom 2010), so past the threshold the item asks for a decision and blocks nothing;
#   - boundaries, not mid-task (Iqbal & Bailey, CHI 2008; dogfood 2026-09-09 F4), so the agent's
#     copy arrives once, at the first prompt of a session, beside the request;
#   - an LLM agent does not habituate across sessions (fresh context each time); it ranks a line at
#     the top of a long context below the request (Liu et al., TACL 2024). So the agent's rung is
#     placement and an instruction to put the item to the human. That part is a HYPOTHESIS: no
#     study covers it, and the E2E harness is where it is measured.
# ESCALATE_AT = 3: the first showing after the second, where the decay is measured. A judgement,
# not a finding; next-item-log.jsonl records shown-count per item so it can be tuned on response.
ESCALATE_AT = 3


def _ruled_since(root: Path, item_id: str, since: str) -> bool:
    """True if the ledger holds a ruling on this id on or after `since` (an acknowledgement)."""
    try:
        lines = (root / ".claude" / "state" / "advisory-ledger.jsonl").read_text().splitlines()
    except OSError:
        return False  # no ledger: nothing was ruled, which is what the count then shows
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if (isinstance(ev, dict) and ev.get("kind") == "ruled" and ev.get("id") == item_id
                and str(ev.get("date", "")) >= since):
            return True
    return False


def carry(root: Path, prev: dict, item_id: str, session: str, today: str) -> tuple[int, str]:
    """(sessions shown, first shown) for this item, counted since its last ruling."""
    if prev.get("id") != item_id:
        return 1, today
    first = str(prev.get("first_shown") or prev.get("emitted_at") or today)
    if _ruled_since(root, item_id, first):
        return 1, today  # acknowledged: the ladder starts again
    shown = int(prev.get("shown") or 1)
    return (shown if prev.get("session") == session else shown + 1), first


def _log_leave(root: Path, prev: dict, today: str) -> None:
    """When the item changes, record how the old one left and after how many showings, so the
    response rate per item can be read (Ray-Wilson et al., JAMIA 2026: fatigue is a sustained fall
    in response, and it can only be seen if response is recorded)."""
    if not prev.get("id"):
        return
    first = str(prev.get("first_shown") or prev.get("emitted_at") or today)
    row = {"id": prev["id"], "first_shown": first, "shown": int(prev.get("shown") or 1),
           "left": today, "outcome": "ruled" if _ruled_since(root, prev["id"], first) else "left"}
    try:
        with (root / LOG_REL).open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        return  # the item itself is unaffected; only the response record misses one row


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


_EVIDENCE = (".claude/canvas/*.yml", "research/**/*")


def _evidence_files(root: Path) -> list[Path]:
    return [f for pat in _EVIDENCE for f in root.glob(pat) if f.is_file()]


def _newest_evidence(root: Path) -> str:
    """The newest date any canvas file or research note was written (YYYY-MM-DD), or ''."""
    stamps = [f.stat().st_mtime for f in _evidence_files(root)]
    return (_dt.datetime.fromtimestamp(max(stamps), tz=_dt.UTC).date().isoformat()
            if stamps else "")


def _last_writer(root: Path) -> dict[str, str]:
    """file path -> the session that last wrote it, from hooks/change-log.sh's record."""
    out: dict[str, str] = {}
    try:
        lines = (root / ".claude" / "state" / "change-log.jsonl").read_text().splitlines()
    except OSError:
        return out  # no record: every file counts as evidence, the conservative reading
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("file_path"):
            out[str(Path(e["file_path"]).resolve())] = str(e.get("session_id") or "")
    return out


def _landed_since(root: Path, ts: str, session: str) -> int:
    """Evidence files written after machine time `ts`, not counting what the ruling session wrote
    itself (the agent that ruled had those in front of it). v0.250.0."""
    try:
        cut = _dt.datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return 0
    writer = _last_writer(root)
    return sum(1 for f in _evidence_files(root)
               if f.stat().st_mtime > cut and writer.get(str(f.resolve())) != session)


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
    rulings = dr.load(root) if dr else {}
    out = []
    for d in doc.get("active_diamonds") or []:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        phase = str(d.get("phase") or "discover").lower()
        if phase in _CLOSED or phase not in _NEXT:
            continue
        ruled = str(d.get("progression_ruled_at") or "")[:10]
        rec = rulings.get(str(d["id"])) or {}
        if dr and rec.get("ts") and rec.get("sig") == dr.signature(d):
            # Machine clock against machine clock (v0.250.0): the recorded time of the last
            # assessment, and files written after it by anyone but the session that made it.
            n = _landed_since(root, rec["ts"], str(rec.get("session") or ""))
            if not n:
                continue
            ruled = ruled or rec["ts"][:10]
            why = f"was last assessed {rec['ts'][:10]}, and {n} evidence file(s) changed since"
        elif ruled and ruled >= newest:
            continue  # typed date, no machine record: ruled on since the newest evidence
        else:
            why = (f"has never been assessed, so it has never moved from {phase}" if not ruled
                   else f"was last ruled on {ruled}, and evidence has landed since")
        scale = str(d.get("scale") or "").upper()
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
    if _escalated(item):
        return (f"NEXT ITEM, unanswered for {item['shown']} sessions since {item['first_shown']}: "
                f"{text} Decide one: run `{item['command']}` | rule | snooze-until DATE | drop. "
                "If the item is wrong, say so; drop records that.")
    return f"NEXT ITEM: {text} run `{item['command']}` | rule | snooze-until DATE | drop."


def _escalated(item: dict) -> bool:
    return int(item.get("shown") or 1) >= ESCALATE_AT


def render(item: dict) -> str:
    text = str(item["text"])
    if str(item.get("id", "")).startswith("fired:"):
        text = _untrusted(text)  # a proposal read back from active.yml is canvas content
    head = "NEXT ITEM"
    if _escalated(item):
        head = (f"NEXT ITEM, unanswered for {item['shown']} sessions since {item['first_shown']} "
                "(put it to the user this session and record the answer)")
    return (
        f"{head}: {text} run `{item['command']}` | rule (say what you decide) | "
        f"snooze-until DATE (`advisory_ledger.py rule --id {item['id']} "
        "--ruling snooze --until DATE`) | "
        f"drop (`--ruling drop`)."
    )


def _read_state(root: Path) -> dict:
    p = root / STATE_REL
    if not p.exists():
        return {}  # no item emitted yet: the count starts at 1, which is correct
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # SPEAKS: main() prints this, so a count that restarts is said, not silent
        return {"_unreadable": f"{type(exc).__name__}"}
    return st if isinstance(st, dict) else {"_unreadable": "not a JSON object"}


def prompt_line(root: Path) -> str:
    """The escalated item for the agent, once per session, at the first prompt (v0.250.0).

    The session-start copy sits at the top of a long context and was read past for 16 sessions in
    E2E run 19. This puts the item beside the user's first request of the session, only once it
    has gone unanswered for ESCALATE_AT sessions, and asks for the one thing the ladder needs: the
    human's decision, recorded. Silent below the threshold, after a ruling, and on later prompts."""
    st = _read_state(root)
    if not st.get("id") or int(st.get("shown") or 1) < ESCALATE_AT:
        return ""
    if st.get("prompt_line_session") == st.get("session"):
        return ""
    if _ruled_since(root, str(st["id"]), str(st.get("emitted_at") or "")):
        return ""
    st["prompt_line_session"] = st.get("session")
    try:
        (root / STATE_REL).write_text(json.dumps(st, ensure_ascii=False))
    except OSError:
        return ""  # could not record it was said: stay quiet rather than repeat on every prompt
    return (f"MYCELIUM OPEN ITEM, unanswered for {st['shown']} sessions since "
            f"{st.get('first_shown')}: when you have answered this prompt, put this item to the "
            "user and ask them to decide: run, rule, snooze until a date, or drop (drop if the "
            f"item is wrong). Record a ruling with `advisory_ledger.py rule --id {st['id']} "
            "--ruling keep|fix|drop|snooze`. The item: "
            f"{st.get('text_human') or st.get('text', '')}")


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
    ap.add_argument(
        "--prompt-line", action="store_true",
        help="print the escalated item for the agent once per session (UserPromptSubmit), and exit",
    )
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    if args.prompt_line:
        line = prompt_line(root)
        if line:
            print(line)
        return 0
    reminders = sys.stdin.read() if not sys.stdin.isatty() else ""
    item, note = pick(root, reminders, args.today)
    if note:
        print(
            f"next-item: {note}"
        )  # stdout: the hook drops stderr, and an unread source must be said
    prev = _read_state(root) if args.write_state else {}
    if prev.get("_unreadable"):
        print(f"next-item: {STATE_REL} unreadable ({prev['_unreadable']}); the unanswered count "
              "restarted at 1, so this item's escalation starts again")
        prev = {}
    if item is None:
        if prev:
            _log_leave(root, prev, args.today)
            (root / STATE_REL).unlink(missing_ok=True)
        return 0
    if args.write_state:
        if prev.get("id") and prev.get("id") != item["id"]:
            _log_leave(root, prev, args.today)
        item["shown"], item["first_shown"] = carry(root, prev, item["id"], args.session, args.today)
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
                    "first_shown": item["first_shown"],
                    "shown": item["shown"],
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
