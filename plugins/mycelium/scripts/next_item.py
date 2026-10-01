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
import contextlib
import datetime as _dt
import json
import os
import re
import subprocess
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
    import scale_locks as sl
except ImportError:  # a partial install: no door is proposed, and the ladder item still is
    sl = None
def _ld(d: dict) -> dict:
    """The L3's learning delivery (v0.296.0): scale_locks.delivery_of, which reads the exposure
    record; nothing when scale_locks is not installed (since v0.307.0 the old field is not read)."""
    return sl.delivery_of(d) if sl is not None else {}


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
SNOOZE_ASKED = "asked"  # the open-ended snooze: until the human rules again

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


def _plugin_version() -> str:
    """This release's version, from the manifest beside this script ("" if unreadable)."""
    try:
        man = Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json"
        return str(json.loads(man.read_text(encoding="utf-8")).get("version") or "")
    except (OSError, ValueError):
        return ""


def _settled(root: Path, st: dict) -> bool:
    """True when the stored item must not be offered again (v0.288.1). Every reader of the stored
    state goes through this, so the live picker's rules and the stored item's cannot drift.

    The dogfood repo's state was written on 2026-09-24 by 0.254.1 and never rewritten (session start
    writes it; a compact or a plugin update does not). Its item, fired:ht-046, was ruled in
    active.yml, which 0.287.1 taught the picker to honour; the readers checked only the ledger, so
    the prompt hook offered it twice on 2026-09-30 to messages that were not answers."""
    item_id = str(st.get("id") or "")
    if not item_id:
        return True
    current = _plugin_version()
    if current and st.get("plugin_version") != current:
        return True  # written by another release: its ids and rules may not exist in this one
    if _ruled_since(root, item_id, str(st.get("emitted_at") or "")):
        return True
    if item_id.startswith("fired:"):
        live, note = _fired_proposals(root)
        if not note and item_id not in {p["id"] for p in live}:
            return True  # ruled on the record, or gone from it
    return False


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


def same_sitting(prev: dict, item_id: str, session: str, today: str) -> bool:
    """One sitting = one session on one day (v0.250.1). A driver that resumes the session for
    every message (an Agent SDK app; the E2E harness) fires SessionStart:resume per message, and
    E2E run 20 showed the human the item twice per message. A resume on a LATER day is a new
    sitting: that is the re-entry moment the human line on resume exists for, and it counts toward
    escalation, since a long-lived session would otherwise never escalate (the ledger counts days
    for the same reason)."""
    return (prev.get("id") == item_id and prev.get("session") == session
            and prev.get("emitted_at") == today)


def carry(root: Path, prev: dict, item: dict, session: str, today: str) -> tuple[int, str]:
    """(sittings shown, first shown) for this item, counted since it was last answered.

    Answered = a ledger ruling on the id, OR (v0.250.2) the item's own action done since it was
    first shown: for a diamond-assessment item, the diamond assessed after `first_shown_at`. E2E
    run 21: an L3 moved discover -> develop in session 1, new evidence brought the same item back,
    and it was escalated as "unanswered for 3 sessions" in session 3. A false escalation is the
    cry-wolf the ladder exists to avoid (Breznitz 1984; Google SRE: every page actionable)."""
    item_id = item["id"]
    if prev.get("id") != item_id:
        return 1, today
    first = str(prev.get("first_shown") or prev.get("emitted_at") or today)
    if _ruled_since(root, item_id, first):
        return 1, today  # acknowledged: the ladder starts again
    done = str(item.get("assessed_at") or "")
    if done and done > str(prev.get("first_shown_at") or ""):
        return 1, today  # its action was taken after it was first shown: answered
    shown = int(prev.get("shown") or 1)
    return (shown if same_sitting(prev, item_id, session, today) else shown + 1), first


def claim_human(root: Path) -> str:
    """The human line, if the human has not been shown this item in this sitting; marks it shown.
    Used by session-start on resume and fork, so the Stop repeat does not say it a second time."""
    st = _read_state(root)
    if (not st.get("id") or st.get("_unreadable") or st.get("repeated_at_stop")
            or _settled(root, st)):
        return ""
    st["repeated_at_stop"] = True
    # An unwritable state still returns the line; at worst the Stop repeat says it once more.
    with contextlib.suppress(OSError):
        (root / STATE_REL).write_text(json.dumps(st, ensure_ascii=False))
    return str(st.get("text_human") or st.get("text") or "")


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
    # "asked" (v0.251.0): snoozed until the human rules again. The ledger report still lists it.
    return bool(su) and (su == SNOOZE_ASKED or str(su) >= today)


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
        # A proposal ruled on the record is settled (v0.287.1). diamond-assess tells the agent to
        # write `ruling:` and `ruled_at:` under a fired entry that does not choose a path, and
        # derive_closing_path keeps those keys; this picker never read them, so the dogfood L1
        # offered ht-046 as its top item for 13 days after it was ruled on 2026-09-16.
        if isinstance(f, dict) and f.get("proposal") and not f.get("ruling")
    ]
    return sorted(out, key=lambda r: r["since"]), ""


_CLOSED = {"complete", "completed", "killed", "parked", "archived", "retargeted"}


def _state_closed(d: dict) -> bool:
    """`state` closes a diamond as surely as `phase` (v0.287.2). The schema's `state` enum carries
    archived, parked and killed, and scale_locks.is_open reads both fields; the picker read phase
    only, so the dogfood L4, archived in place with `state: archived`, kept being offered its
    launch items."""
    return str(d.get("state") or "").lower() in _CLOSED
_NEXT = {"discover": "define", "define": "develop", "develop": "deliver", "deliver": "complete"}


def _can_move(d: dict, phase: str) -> bool:
    """Whether a diamond has a next move at all: open, not at its last phase, and not an L0 that
    records decisions, which does not move but records `review` (DL-1368 S2, v0.305.0)."""
    if phase in _CLOSED or phase not in _NEXT or _state_closed(d):
        return False
    return not (sl is not None and str(d.get("scale", "")).upper() == "L0" and sl.decisions_of(d))


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


def _product_files(root: Path) -> list[Path]:
    """What the product is made of: every file git sees outside `.claude/` and the evidence
    folders, committed or not. Outside a git repo there is nothing to read, so nothing wakes."""
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root,
                             capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return []  # SPEAKS: no wake is the old behaviour, the snooze holds as ruled
    if out.returncode != 0:
        return []
    evidence = {f.resolve() for f in _evidence_files(root)}
    names = [n for n in out.stdout.split("\0") if n and not n.startswith((".claude/", ".git/"))]
    return [f for f in (root / n for n in names) if f.is_file() and f.resolve() not in evidence]


#: A snooze "until asked" on a way into the ladder, or on the ladder itself, ends when the product
#: changes after it (v0.285.0). E2E relay L3-open and service run 10 on 0.283.0: the product was
#: being built outside the ladder, the founder snoozed the door "until asked", and Mycelium said
#: nothing for the rest of the run while the work went on.
WAKES_ON_WORK = ("door-", "unassessed", "target-l2:")


def _woken(root: Path, st: dict) -> dict[str, int]:
    """Items snoozed until asked whose product files changed after the ruling, not counting what
    the ruling session wrote itself: id -> how many files."""
    out: dict[str, int] = {}
    files: list[Path] | None = None
    for aid, x in st.items():
        if (x.get("snoozed_until") != SNOOZE_ASKED or not x.get("snooze_ts")
                or not str(aid).startswith(WAKES_ON_WORK)):
            continue
        try:
            cut = _dt.datetime.fromisoformat(str(x["snooze_ts"])).timestamp()
        except ValueError:
            continue
        files = _product_files(root) if files is None else files
        writer = _last_writer(root)
        n = sum(1 for f in files if f.stat().st_mtime > cut
                and writer.get(str(f.resolve())) != str(x.get("snooze_session") or ""))
        if n:
            out[str(aid)] = n
    return out


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
    state = _lock_state(root)
    evidence = dr.evidence_count(root) if dr else None
    out = []
    for d in doc.get("active_diamonds") or []:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        phase = _where(d)
        if not _can_move(d, phase):
            continue
        ruled = str(d.get("progression_ruled_at") or "")[:10]
        rec = rulings.get(str(d["id"])) or {}
        if dr and rec.get("ts") and rec.get("sig") == dr.signature(d):
            # New EVIDENCE since the recorded assessment (v0.251.0): a count of research notes and
            # canvas evidence sources, so an edit that adds no source does not re-propose the
            # diamond. Records written before 0.251.0 carry no count and use file times (0.250.0).
            if evidence is not None and isinstance(rec.get("evidence_n"), int):
                n = evidence - rec["evidence_n"]
                what = "new evidence entr" + ("y" if n == 1 else "ies")
            else:
                n = _landed_since(root, rec["ts"], str(rec.get("session") or ""))
                what = "evidence file(s) changed"
            if n <= 0:
                continue
            ruled = ruled or rec["ts"][:10]
            why = f"was last assessed {rec['ts'][:10]}, and {n} {what} since"
        elif ruled and ruled >= newest:
            continue  # typed date, no machine record: ruled on since the newest evidence
        else:
            why = (f"has never been assessed, so it has never moved from {phase}" if not ruled
                   else f"was last ruled on {ruled}, and evidence has landed since")
        scale = str(d.get("scale") or "").upper()
        text, hint, waits = _move_text(state, d, phase, why)
        out.append({"id": f"unassessed:{d['id']}", "diamond": d["id"],
                    "since": ruled or str(d.get("created") or today)[:10],
                    # A move that can happen now leads one that waits on the world (v0.276.0).
                    "rank": (0 if scale in ("L3", "L4", "L5") else 1, bool(waits), ruled or ""),
                    "text": text, "hint": hint,
                    "command": f"/mycelium:diamond-progress {d['id']}",
                    "assessed_at": rec.get("ts") if rec.get("sig") == (
                        dr.signature(d) if dr else None) else None})
    return sorted(out, key=lambda r: r["rank"])


def _lock_state(root: Path):
    try:
        return sl.State(str(root)) if sl else None
    except Exception:  # noqa: BLE001  SPEAKS: _door_item reads the same locks and reports them
        return None


def _move_text(state, d: dict, phase: str, why: str) -> tuple[str, str, bool]:
    """A ladder row's text, the hint that follows the list, and whether the move waits."""
    scale = str(d.get("scale") or "").upper()
    waits = _waits_on(state, d, f"{phase}->{_NEXT[phase]}")
    text = f"{d['id']} ({scale}) {why}. Its next transition is {phase} -> {_NEXT[phase]}."
    if waits:
        # Only the move waits (v0.276.1): E2E rung L4-open on 0.276.0 read "It waits on" as the
        # whole L3 waiting, snoozed it, and left a scorable test unscored for four sessions.
        text += f" That move waits on {waits}; scoring its test and its verdict do not."
    # The bar is drafted, not asked for (v0.276.0). E2E rung L4-define on 0.275.0: the L4 was
    # opened with no bar, its first assessment could only say needs-evidence, and two sessions
    # went on asking the founder to write a definition of done and a stance she had decided.
    hint = ("" if waits or scale not in ("L3", "L4", "L5") or d.get("definition_of_done")
            else f" {d['id']} has no bar yet: draft its `definition_of_done` (on an L4, its "
                 "`purpose_stance` too) from what the user has already decided, and put the "
                 "draft to them to confirm; do not ask them to write it.")
    return text, hint, bool(waits)


def _waits_on(state, d: dict, transition: str) -> str:
    """What a move waits on that no assessment can produce, or "" (v0.276.0). An L3 in Deliver
    cannot complete until its learning delivery has ended, and the pilot ending is the world's
    doing, not a ruling's. E2E rungs L4-define and L4-develop on 0.275.0: the L3's pilot notes
    arrived every session, so the L3 led the ladder, and the L4 whose next move was desk work sat
    under "Also waiting" until the budget ran out (1 of 3 reached develop). Founder, 2026-09-27:
    propose a move once what it needs is on record."""
    if state is None or str(d.get("scale") or "").upper() != "L3":
        return ""
    if transition == "deliver->complete":
        return "its learning delivery ending" if state.learning_delivery_end_missing(d) else ""
    return ""


LADDER_ID = "unassessed"
_SHIPPED = {"deliver", "complete", "completed"}


def _children(active: list[dict], parent: dict, scale: str) -> list[dict]:
    """Open diamonds at `scale` that name `parent` (by `parent`, or by the same `object_ref`)."""
    pid, ref = str(parent.get("id")), str(parent.get("object_ref") or "")
    return [d for d in active if str(d.get("scale", "")).upper() == scale
            and _where(d) not in _CLOSED
            and (str(d.get("parent") or d.get("parent_id") or "") == pid
                 or (ref and str(d.get("object_ref") or "") == ref))]


def _l4_launch_item(root: Path, today: str, st: dict, d: dict, did: str) -> dict | None:
    """What an L4 in Deliver needs on the way to its L5 (v0.282.0), in three steps.

    1. Nothing records it reaching its users: the founder's, to say when it does (`release-l4:`).
       E2E relay on 0.280.0: the L4 reached Deliver with the forum post on hold, and the item said
       "has shipped" and told the agent to record the release seven sessions running; the builder
       rightly declined, since nothing had gone out. Deliver is not released.
    2. Released, launch data not yet recorded: the agent's record work (`launch-data-l4:`, 0.275.1).
    3. The L5 lock holds: the L5 door, the founder's decision (`door-l5:`)."""
    missing = sl.can_open(str(root), "L5", parent=did)
    ready = not missing
    released = str(d.get("released_on") or "")[:10]
    data = sl._as_dict(d.get("launch_data"))  # noqa: SLF001 — the lock's own reader, not a copy
    recorded = (any(sl._filled(data.get(k)) for k in ("usage", "feedback", "metric_movement"))  # noqa: SLF001
                and sl.State.launch_after_release_missing(d, data) is None)
    if ready:
        iid, command = f"door-l5:{did}", "/mycelium:launch-tier"
        text = (f"{did} (L4) has shipped and its launch data is recorded: open the L5 market "
                "diamond on it.")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", released):
        iid, command = f"release-l4:{did}", "/mycelium:launch-tier"
        text = (f"{did} (L4) is in Deliver and nothing records it reaching its users. When it "
                "does, the day the first person outside the team has it, say so, and it is "
                "recorded as `released_on`. The launch data, and then an L5, follow from there.")
    elif recorded:
        # v0.287.2: released and its launch data recorded, and the L5 lock still does not hold for
        # another reason. The dogfood L4 (on an override, no L3 parent) was told to record launch
        # data it already carried, and the blocker the lock names was never shown.
        iid, command = f"l5-lock-l4:{did}", "/mycelium:diamond-assess"
        text = (f"{did} (L4) reached its users on {released} and its launch data is recorded, "
                "but the L5 lock does not hold yet: " + "; ".join(missing) + ". That is the next "
                "thing to produce before its launch opens an L5.")
    else:
        iid, command = f"launch-data-l4:{did}", "edit diamonds/active.yml"
        text = (f"{did} (L4) reached its users on {released}. On the L4 in "
                "diamonds/active.yml, record `launch_data: {usage | feedback | metric_movement, "
                "as_of: YYYY-MM-DD}` once people have used it, with `as_of` after the release; the "
                "L5 lock reads those fields and nothing else. A first market release then opens "
                "an L5.")
    if _blocked(st.get(iid, {}), today):
        return None
    item = {"id": iid, "diamond": did, "since": today, "command": command, "text": text,
            "why": "a released L4 is the L5's event"}
    if iid.startswith("launch-data-l4:"):
        # What the agent does, in its own words (v0.276.0).
        item["does"] = ("write `launch_data` yourself from the usage figures already in the "
                        "notes, saying what the figures count (page opens are not uses), then tell "
                        "the user what you recorded; if no note carries usage yet, say what is "
                        "still to come")
    return item


def _door_item(root: Path, today: str, st: dict) -> dict | None:
    """The L4 and L5 doors, proposed when they can open (v0.254.0); then the L1 to L3 doors.

    E2E runs 19-26: no run reached L4. Its only entrance was /preflight's offer when an L3 enters
    develop, which under test-first (0.253.0) comes before the test that raises the L3's evidence,
    so the lock could not hold then, and nothing offered the L4 again once it did. The L5's
    entrance, /launch-tier, was prompted by nothing when an L4 shipped. "Every diamond needs a way
    in; a documented route that never fires is none" (founder). Each door is proposed once its lock
    holds (L4) or once its L4 has shipped (L5, which starts with recording the launch data)."""
    p = root / ".claude" / "diamonds" / "active.yml"
    if sl is None or yaml is None or not p.exists():
        return None
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        active = [d for d in doc.get("active_diamonds") or []
                  if isinstance(d, dict) and d.get("id") and not _state_closed(d)]
        past = [d for k in ("completed_diamonds", "archived_diamonds") for d in doc.get(k) or []
                if isinstance(d, dict) and d.get("id")]
        past += [d for d in doc.get("active_diamonds") or []
                 if isinstance(d, dict) and d.get("id") and _state_closed(d)]
    except (yaml.YAMLError, OSError, AttributeError):
        return None  # SPEAKS: _fired_proposals reads the same file and reports it unreadable
    for d in active:
        scale = str(d.get("scale", "")).upper()
        phase = _where(d)
        did = str(d["id"])
        if scale == "L3" and phase in ("develop", "deliver") and not _children(active, d, "L4"):
            item = _l3_item(root, today, st, d, phase)
            if item:
                return item
        if scale == "L4" and phase in _SHIPPED and not _children(active, d, "L5"):
            item = _l4_launch_item(root, today, st, d, did)
            if item is None:
                continue
            return item
    return _entry_door(root, today, st, active, past)


def _l3_item(root: Path, today: str, st: dict, d: dict, phase: str) -> dict | None:
    """What an L3 in develop or deliver with no L4 needs next: a way on from a failed assumption
    (v0.263.0), its learning delivery, the verdict of a scored test (v0.260.0), or the L4 door once
    the lock holds."""
    did = str(d["id"])
    item = _pivot_item(root, today, st, d) \
        or _inconclusive_item(root, today, st, d) \
        or (_learning_delivery_item(root, today, st, d) if phase == "develop" else None) \
        or (_start_item(today, st, d) if phase == "deliver" else None) \
        or _verdict_item(root, today, st, d) \
        or _delivery_over_item(root, today, st, d)
    if item:
        return item
    iid = f"door-l4:{did}"
    if _blocked(st.get(iid, {}), today) or sl.can_open(str(root), "L4", parent=did):
        return None
    # The door names the audience it is the only way past (v0.267.0): right after a pass is when
    # a founder wants to launch, and E2E rung L4-open went public under the L3 at that moment.
    ld = _ld(d)
    who = str(ld.get("audience") or "").strip()
    beyond = (f" Its learning delivery reaches {who}. A release to everyone goes through the L4, "
              "which passes Security, Privacy and Service Quality for them: open it before the "
              "build reaches them. A bigger test audience stays in the L3, recorded as a change "
              "to its learning delivery with those gates re-run." if who else "")
    return {"id": iid, "diamond": did, "since": today, "command": "/mycelium:preflight",
            "text": f"{did} (L3) has delivered to learn, its verdict holds, and no L4 is open "
                    "on it: its increment can be delivered. Open an L4 on it, with a draft "
                    "`definition_of_done` and `purpose_stance` built from what the user has "
                    "already decided, for them to confirm." + beyond,
            "why": "the L4 lock holds and nothing is delivering the increment"}


def _start_item(today: str, st: dict, d: dict) -> dict | None:
    """An L3 in Deliver whose test has not started (v0.274.0). `exposures[].started` is the
    day the first person in the audience took part. E2E service world run 4: the L3 reached Deliver
    scoped to a pilot with three existing clients, then grew its client pack from about 4,100 to
    7,100 words over seven sessions while nobody was served; 0.273.0 caught a growing build only in
    develop. Starting is the founder's decision: it puts the test in front of people."""
    ld = _ld(d)
    if not ld.get("audience") or str(ld.get("started") or "").strip():
        return None
    did = str(d["id"])
    iid = f"start-l3:{did}"
    if _blocked(st.get(iid, {}), today):
        return None
    return {"id": iid, "diamond": did, "since": today,
            "command": f"/mycelium:diamond-progress {did}",
            "text": (f"{did} (L3) is in Deliver and its test has not started: nobody in its "
                     "audience has taken part. Start it, and record `exposures[].started` "
                     "with the date the first person took part, or say what blocks the start. "
                     "Build only what the start needs; anything else is the next test on the "
                     "tree or L4 work."),
            "why": "a learning delivery that never starts never reads out"}


def _inconclusive_item(root: Path, today: str, st: dict, d: dict) -> dict | None:
    """The way on from a test that read out inconclusive or partial (v0.268.0). Such a verdict is
    readable, so the verdict item stands down; it is not a failure, so the pivot item stays quiet;
    and the L4 stays shut. An underpowered beta or a noisy cohort was offered nothing at all
    (overfit audit, 2026-09-26). Three ways on, all in the L3."""
    did = str(d["id"])
    iid = f"rerun-l3:{did}"
    if _blocked(st.get(iid, {}), today):
        return None
    for sol in sl.State(str(root)).build_solutions(d):
        ra = sol.get("riskiest_assumption")
        said = str(ra.get("verdict") or "").strip().lower() if isinstance(ra, dict) else ""
        if said in ("inconclusive", "partial"):
            return {"id": iid, "diamond": did, "since": today,
                    "command": "/mycelium:assumption-test",
                    "text": (f"{did} (L3): the test of {sol.get('id', 'its solution')}'s riskiest "
                             f"assumption read out `{said}`. Choose one: run it again with a "
                             "changed sample or audience (a wider one is recorded on the learning "
                             "delivery, with its gates re-run); revise the assumption or the test "
                             "and go back to define; or stop the L3 with the reason."),
                    "why": "an inconclusive test is an outcome with a way on, not a dead end"}
    return None


def _pivot_item(root: Path, today: str, st: dict, d: dict) -> dict | None:
    """The way on from an L3 whose riskiest assumption failed its test (v0.263.0). The L4 lock says
    "pivot or stop in the L3, do not deliver it", and until 0.263.0 nothing else was offered: E2E
    run 53 recorded `invalidated` on the salt-and-leavening assumption and the next session started
    with no item at all. Every diamond needs a way in and out (founder); a failed test is an
    outcome, and it has three exits, all in the L3 or its L2."""
    did = str(d["id"])
    iid = f"pivot-l3:{did}"
    if _blocked(st.get(iid, {}), today):
        return None
    state = sl.State(str(root))
    failed = state.l3_failed(d)
    if not failed:
        return None
    fr = state.front_runner(d)
    if fr:
        text = (f'{did} (L3): its front runner {fr} failed its test ("{failed}"), so it does not '
                "go on to an L4. Choose the way on: take another idea from its set as the front "
                "runner, revise this one and name a new test (the L3 goes back to define), or, "
                "if none of its ideas can work, revise the L2's map and re-target (the L3 then "
                "closes as retargeted).")
    else:
        text = (f'{did} (L3): every idea in its set failed its test (first: "{failed}"): none '
                "works. Revise the L2's map with what the tests taught and re-target "
                "(/mycelium:ost-builder; the L3 closes as retargeted), or add a new idea to the "
                "set and test it.")
    return {"id": iid, "diamond": did, "since": today,
            "command": f"/mycelium:diamond-progress {did}", "text": text,
            "why": "a failed assumption is an outcome, and the L3 needs a way on from it"}


#: The verdict words the L4 lock reads, and the honest not-yet words (v0.265.0).
_READABLE_VERDICTS = ({"validated", "passed", "held"}
                      | {"invalidated", "failed", "falsified", "refuted"}
                      | {"untested", "inconclusive", "partial", "pending"})
_TEST_PATH = re.compile(r"[\w./-]*\.claude/evals/assumption-tests/[\w.-]+\.md")


def _front_matter(path: Path) -> dict:
    """The YAML header of an instrument file, or {} when it has none or cannot be read."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if yaml is None or not text.startswith("---"):
        return {}
    _, _, rest = text.partition("---")
    header, sep, _ = rest.partition("---")
    try:
        data = yaml.safe_load(header) if sep else None
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _delivery_ended_item(iid: str, today: str, d: dict, sol: dict) -> dict | None:
    """The delivery has run its course and no verdict is in (v0.268.0), wherever the result was
    kept: a gradebook, a CRM, a device-return sheet, not only a test file in Mycelium's folder.
    Until then the verdict item fired only on a scored file there (overfit audit, 2026-09-26)."""
    ld = _ld(d)
    until = str(ld.get("until") or "")[:10]
    if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", until) and until < today):
        return None
    did = str(d["id"])
    return {"id": iid, "diamond": did, "since": today, "command": "/mycelium:assumption-test",
            "text": (f"{did} (L3): its learning delivery ran until {until} and no verdict is "
                     f"recorded on {sol.get('id', 'its solution')}'s riskiest assumption. "
                     "Record `verdict: validated`, `invalidated` or `inconclusive` from wherever "
                     "the result was kept, with the reasoning in `verdict_note`."),
            "why": "a delivery that has ended owes its verdict"}


def _delivery_over_item(root: Path, today: str, st: dict, d: dict) -> dict | None:
    """A learning delivery past its `until` with no recorded end (v0.276.0). The id carries the
    date, so an extension makes a new item and a snooze of an earlier item never covers it. E2E
    service world run 5: the test read inconclusive, the re-run item was snoozed "until the first
    cohort's close is scored", no stranger ever joined, and the delivery ran past its last day with
    nothing asking; the builder wrote its own `closed:` block, which no lock reads, while the three
    clients carried on paying with no L4. Ending or carrying on is the founder's decision."""
    ld = _ld(d)
    until = str(ld.get("until") or "")[:10]
    if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", until) and until < today):
        return None
    missing = sl.State(str(root)).learning_delivery_end_missing(d)  # _verdict_item reads it first
    did = str(d["id"])
    iid = f"delivery-over-l3:{did}:{until}"
    if not missing or _blocked(st.get(iid, {}), today):
        return None
    return {"id": iid, "diamond": did, "since": today,
            "command": f"/mycelium:diamond-progress {did}",
            "text": (f"{did} (L3): its learning delivery ran until {until} and how it ended is "
                     "not recorded. If it no longer reaches its audience, record "
                     "`exposures[].ended: {how: withdrawn, on}`. If it carries on for "
                     "them, that is production: open an L4 on it and record `how: handed_to_l4`. "
                     "Or extend `until`, with the reason."),
            "why": "a learning delivery past its last day is production or over, and says which"}


def _verdict_item(root: Path, today: str, st: dict, d: dict) -> dict | None:
    """An L3 whose named test is scored and whose verdict is not recorded (v0.260.0). The L4 lock
    reads `riskiest_assumption.verdict`; a score written only into the test file and the decision
    log never reaches it, and nothing else was offered. E2E run 46: 4 of 5 testers returned against
    a bar of 3, the file said `status: scored`, and the next session started with no offer at
    all. Run 41 had the same shape. The verdict is on the BET the solution needs, whichever way
    its statement is worded: run 46's read \"testers will NOT come back\", so a literal reading
    of a pass is `invalidated`, which the lock reads as a failed assumption."""
    did = str(d["id"])
    iid = f"verdict-l3:{did}"
    if _blocked(st.get(iid, {}), today):
        return None
    state = sl.State(str(root))
    if state.l3_evidence(d) in sl.MEDIUM_OR_BETTER or state.l3_failed(d):
        return None
    for sol in state.build_solutions(d):
        ra = sol.get("riskiest_assumption")
        if not isinstance(ra, dict):
            continue
        said = str(ra.get("verdict") or "").strip()
        # A verdict the lock cannot read is no verdict (v0.265.0). E2E rung L4-open, 2026-09-26: the
        # builder recorded the pass as prose ("met on 2026-11-18 ... 4 of 5 testers came back"); the
        # L4 lock reads only its own words, stayed shut, and this item stood down because the field
        # was not empty.
        if said and said.lower() not in _READABLE_VERDICTS:
            sid = sol.get("id", "its solution")
            return {"id": iid, "diamond": did, "since": today,
                    "command": "/mycelium:assumption-test",
                    "text": (f"{did} (L3): the verdict on {sid}'s riskiest assumption is prose "
                             f'the L4 lock cannot read ("{said[:60]}"). Write '
                             "`verdict: validated` if the bet the solution needs held or "
                             "`invalidated` if it did not, and keep the reasoning in "
                             "`verdict_note`."),
                    "why": "a verdict the lock cannot read never reaches it"}
        if said and said.lower() not in ("pending", "untested"):
            continue
        ended = _delivery_ended_item(iid, today, d, sol) or _overdue_test_item(root, today, st, did,
                                                                              sol)
        if ended:
            return ended
        if said:
            continue
        item = _scored_file_item(root, iid, today, did, sol)
        if item:
            return item
    return None


def _overdue_test_item(root: Path, today: str, st: dict, did: str, sol: dict) -> dict | None:
    """The L3's test file is still live past its `score_by` (v0.276.1). E2E rung L4-open on
    0.276.0: 4 of 5 testers came back against a frozen bar of 3, the builder offered to write the
    result ("say the word") and did not, and nothing asked until the learning delivery ended four
    sessions later, past the budget. The verdict item fired only on a file already marked scored.
    Scoring against a frozen bar is Mycelium's record work, and so is saying the result is not in
    yet."""
    ra = sol.get("riskiest_assumption") if isinstance(sol.get("riskiest_assumption"), dict) else {}
    m = _TEST_PATH.search(str(ra.get("cheapest_test") or ""))
    if not m:
        return None
    path = root / m.group(0)[m.group(0).find(".claude/"):]
    head = _front_matter(path)
    due = str(head.get("score_by") or "")[:10]
    if str(head.get("status", "")).lower() != "live" or not (
            re.fullmatch(r"\d{4}-\d{2}-\d{2}", due) and due < today):
        return None
    iid = f"score-l3:{did}:{due}"
    if _blocked(st.get(iid, {}), today):
        return None
    rel = path.relative_to(root)
    return {"id": iid, "diamond": did, "since": today, "command": f"edit {rel}",
            "text": (f"{did} (L3): its test ({rel}) was due to be scored by {due} and is still "
                     "live, so no verdict can reach the L4 lock."),
            "does": ("score the test yourself against the bar it was frozen with, from the result "
                     "notes (write the result, set `status: scored`), then record the verdict on "
                     f"{sol.get('id', 'the solution')}'s riskiest assumption and tell the user; if "
                     "no result is in yet, set a new `score_by` and say why in an `amended:` line"),
            "why": "a test past its score date owes its score"}


def _scored_file_item(root: Path, iid: str, today: str, did: str, sol: dict) -> dict | None:
    """A test file in Mycelium's folder marked scored, with no verdict recorded (v0.260.0)."""
    ra = sol.get("riskiest_assumption") if isinstance(sol.get("riskiest_assumption"), dict) else {}
    m = _TEST_PATH.search(str(ra.get("cheapest_test") or ""))
    if not m:
        return None
    path = root / m.group(0)[m.group(0).find(".claude/"):]
    if str(_front_matter(path).get("status", "")).lower() != "scored":
        return None
    rel = path.relative_to(root)
    return {"id": iid, "diamond": did, "since": today,
            "command": "/mycelium:assumption-test",
            "text": (f"{did} (L3) has scored its test ({rel}) and no verdict is recorded "
                     f"on {sol.get('id', 'its solution')}'s riskiest assumption, so the L4 "
                     "lock cannot read the result. Record `verdict: validated` if the bet "
                     "the solution needs held, `invalidated` if it did not, whichever way "
                     "the statement is worded. A validated verdict from this learning "
                     "delivery is what opens the L4."),
            "why": "a scored test whose verdict never reaches the lock"}


def _learning_delivery_item(root: Path, today: str, st: dict, d: dict) -> dict | None:
    """The L3's own Deliver, proposed while its test waits on real use (v0.257.0). In 21 E2E runs
    one L3 ever reached Deliver (run 19); the rest stalled in develop, where nothing offered the
    move, and 0.256.0 routed the test through an L4 instead. The L3 delivers to LEARN: its test
    runs with a named, opted-in audience until a date, through Security, Privacy and Service
    Quality, and the verdict is what opens the L4."""
    did = str(d["id"])
    iid = f"deliver-l3:{did}"
    if _blocked(st.get(iid, {}), today):
        return None
    state = sl.State(str(root))
    if state.test_design_missing(d) or state.l3_failed(d):
        return None
    # v0.258.0: a pass from a test run outside the L3's Deliver no longer opens the L4, so
    # this item stays up after it, or nothing would be offered at all (E2E run 41).
    early = state.l3_evidence(d) in sl.MEDIUM_OR_BETTER
    need = [g.replace("_", " ").title() for g in ("security", "privacy", "service_quality")
            if state.gate_missing(d, g)]
    if state.learning_delivery_missing(d):
        need.append("its learning delivery as an exposure record (audience, until, channel)")
    text = (f"{did} (L3) has evidence from a test run before its Deliver, and that does not "
            "open the L4: the people it reached never went through Security, Privacy and "
            "Service Quality. Take the L3 to Deliver and run its learning delivery with a named "
            "audience who knows they are in it, until a date; a concierge or hand-run test "
            "counts. Its verdict is what opens the L4." if early else
            f"{did} (L3) has built what its test needs and the test has not run. Take the L3 to "
            "Deliver to run it with its audience: a named, opted-in group, until a date, by means "
            "that fit the product (for web software, infrastructure as code for an environment "
            "that can be torn down; for any product, a concierge or hand-run test). The verdict "
            "is what opens the L4. Before Deliver, its gate asks for one trial outside the team of "
            "what the delivery puts in front of people (a usability session with the prototype, a "
            "dry run of the service, a walkthrough of the lesson), with a named person and run "
            "with you; that trial is part of Develop, not a release.")
    if need:
        text += " Still needed: " + ", ".join(need) + "."
    # v0.273.0: the L3 builds only what its test needs to run. E2E service world run 3: this item
    # stood for sessions while the build grew to 8,500 words of client documents for a two-month,
    # hand-run pilot with three existing clients, each edge case a new question for the founder.
    text += (" Build only what the test needs to run; a question it raises that the test does not "
             "need is the next test on the tree (an assumption on the solution) or L4 work.")
    return {"id": iid, "diamond": did, "since": today,
            "command": f"/mycelium:diamond-progress {did}", "text": text,
            "why": "the test waits on real use, and the L3 delivers to learn"}


# The way into each scale below L4, deepest first (v0.255.0): the scale, the parent scale, the
# skill whose offer is that scale's entrance, and what the door says.
#: Since v0.301.0 (DL-1367; ruling C) an L2 opens on an outcome its L1 has set and an L3 on the
#: target its L2 has chosen, one per outcome and one per target; until then each opened on a record
#: (the opportunity that served the outcome best, the highest-ranked leaf) and only while nothing at
#: its scale was open.
_ENTRY_DOORS = (
    ("L3", "L2", "/mycelium:ost-builder",
     ("{pid} (L2) targets {ref} and no L3 works it: open an L3 on {ref} (`parent: {pid}`) "
      "with about three ideas for it, compared by testing their assumptions.")),
    ("L2", "L1", "/mycelium:ost-builder",
     ("{pid} (L1) has set the outcome {ref} and no L2 maps it: open an L2 on it "
      "(`object_ref: {ref}`), map its opportunities, and choose a target by comparing them.")),
    ("L1", "L0", "/mycelium:wardley-map",
     ("{pid} (L0) has its purpose stated and no L1 is open: open an L1 Strategy diamond on "
      "the first strategic decision, or record that none is open.")),
)


def _had_child(parent: dict, scale: str, diamonds: list[dict]) -> bool:
    """Whether any diamond at `scale`, open or finished, came from this parent."""
    pid, ref = str(parent.get("id")), str(parent.get("object_ref") or "")
    return any(str(d.get("scale", "")).upper() == scale
               and (str(d.get("parent") or d.get("parent_id") or "") == pid
                    or (ref and str(d.get("object_ref") or "") == ref)) for d in diamonds)


def _door_refs(state, scale: str, parent: dict) -> list[str]:
    """What a door at `scale` would open ON under this parent, and is not yet worked (v0.301.0):
    an L2 on each outcome with no live L2 mapping it; an L3 on the L2's target when no live L3
    works it; an L1 once, when none is open."""
    if scale == "L2":
        mapped = {state.l2_outcome(d) for d in state.live("L2")}
        ids = [str(r["id"]) for r in state.roots() if r.get("id")]
        if not ids:  # one outcome with no id: one L2 maps it
            return [] if state.live("L2") else ["the desired outcome"]
        # v0.304.0: under the L1 that set it. With no `set_by`, only a lone live L1 is
        # unambiguous; with several, _setter_item asks which (0.301.0 paired it with the first L1
        # whose lock held).
        pid, lone = str(parent.get("id")), len(state.live("L1")) == 1
        return [i for i in ids if i not in mapped
                and (state.outcome_setter(i) == pid or (not state.outcome_setter(i) and lone))]
    if scale == "L3":
        target = state.l2_target(parent)
        return [target] if target and state.l3_works(parent) is None else []
    return [] if state.live(scale) else [""]


def _setter_item(state, today: str, st: dict) -> dict | None:
    """AN OUTCOME NO L1 IS NAMED AS SETTING, WITH SEVERAL L1s LIVE (v0.304.0): which L1 set it
    is the founder's to say, and the L2 door waits on it rather than guessing a parent."""
    if len(state.live("L1")) <= 1:
        return None
    mapped = {state.l2_outcome(d) for d in state.live("L2")}
    for r in state.roots():
        oid = str(r.get("id") or "")
        if not oid or oid in mapped or state.outcome_setter(oid):
            continue
        iid = f"outcome-setter:{oid}"
        if _blocked(st.get(iid, {}), today):
            continue
        l1s = ", ".join(str(d.get("id")) for d in state.live("L1"))
        return {"id": iid, "diamond": oid, "since": today, "command": "/mycelium:ost-builder",
                "text": (f"The outcome {oid} has no L2 and does not say which L1 set it, and "
                         f"several are live ({l1s}). Say which, and record it as "
                         f"`desired_outcomes[].set_by`; its L2 then opens under that L1."),
                "why": "an L2 opens under the L1 that set its outcome"}
    return None


def _target_item(state, today: str, st: dict, l2: dict) -> dict | None:
    """An L2 with no target (v0.301.0, DL-1367): the choice is the L2's decision (`set_target`),
    by comparing sibling opportunities, never by a score (Torres p103-108)."""
    pid = str(l2["id"])
    iid = f"target-l2:{pid}"
    if state.l2_target(l2) or _blocked(st.get(iid, {}), today):
        return None
    outcome = state.l2_outcome(l2) or "its outcome"
    return {"id": iid, "diamond": pid, "since": today, "command": "/mycelium:ost-builder",
            "text": (f"{pid} (L2) maps {outcome} and has no target: compare its opportunities "
                     "(importance, how well served today, by judgment) and record the choice "
                     "on the L2 as `target: {opportunity, chosen_on, compared, why}`. It can "
                     "be re-chosen as the tests come in."),
            "why": "an L3 opens on the L2's target, and choosing it is the L2's decision"}


MIGRATE = f'python3 "{Path(__file__).resolve().parent / "migrate_phase.py"}"'


def _where(d: dict) -> str:
    """Where a diamond is (v0.305.0, stage 5b): read from its decision log by scale_locks.phase_of.
    Only a partial install with no scale_locks falls back to the recorded label."""
    if sl is not None:
        return sl.phase_of(d)
    return str(d.get("phase") or "discover").lower()


def _migrate_item(root: Path, today: str, st: dict) -> dict | None:
    """Diamonds recorded in a shape no longer read (v0.303.0, DL-1368 S3): the migration to the
    decision log, shown first and written on the user's yes. Offered last until v0.307.0, while
    the old shape was read as a fallback; since then it comes right after fired proposals, because
    every door and the ladder read only the new records and would ask again for a decision the
    old record already holds (an L2's target, an L3's front runner)."""
    iid = "migrate-phase:project"
    if sl is None or _blocked(st.get(iid, {}), today):
        return None
    try:
        state = sl.State(str(root))
    except (sl.UnreadableError, sl.CannotCheckError):
        return None  # SPEAKS: _fired_proposals and the ladder item report an unreadable file
    pending = _would_migrate(state)
    if not pending:
        return None
    return {"id": iid, "diamond": pending[0], "since": today, "owner": "agent",
            "command": f"{MIGRATE} --project-dir .",
            "text": (f"{len(pending)} diamond(s) ({', '.join(pending[:4])}) are recorded in a "
                     "shape Mycelium no longer reads (a phase, a `learning_delivery`, or an L2 or "
                     "L3 on one object). Run the migration's dry run, show what it would change, "
                     "and write it with `--write` on the user's yes."),
            "why": "since v0.306.0-0.307.0 those records are not read"}


def _would_migrate(state) -> list[str]:
    """The open diamonds the migration would change (v0.307.0): a recorded phase, a
    `learning_delivery`, or the old one-object L2/L3 shape, asked of the migration itself so the
    offer and the script cannot disagree about what is left."""
    try:
        import copy  # noqa: PLC0415 - only when the offer is computed

        import migrate_phase as mp  # noqa: PLC0415 - the migration's own reading
    except ImportError:
        return []
    doc = copy.deepcopy({"active_diamonds": [d for d in state.by_id.values() if state.is_open(d)]})
    before = {str(d.get("id")): copy.deepcopy(d) for d in doc["active_diamonds"]}
    mp.migrate(doc, state, "1970-01-01")
    return [i for i, d in ((str(x.get("id")), x) for x in doc["active_diamonds"]) if d != before[i]]


def _entry_door(root: Path, today: str, st: dict, active: list[dict],
                past: list[dict] | tuple = ()) -> dict | None:
    """The L1, L2 and L3 doors (v0.255.0). Each scale's entrance was an offer inside one skill
    (/wardley-map, /ost-builder, /ice-score), so a project that never ran that skill was never
    asked, and no test asserted any of the three fired. Founder, 2026-09-25, on the L4 and L5
    doors that had been documented and never fired: "a major mismatch from what I was promised".
    Proposed once the scale's lock holds and nothing at that scale is open; L1 to L3 are the way
    into strategy, opportunity and solution work, where L4 and L5 are one per increment."""
    def live(scale: str) -> list[dict]:
        return [d for d in active if str(d.get("scale", "")).upper() == scale
                and _where(d) not in _CLOSED]
    state = sl.State(str(root))
    for d in live("L2"):
        item = _target_item(state, today, st, d)
        if item:
            return item
    for scale, parent_scale, command, text in _ENTRY_DOORS:
        if scale == "L1" and live(scale):
            continue
        # A parent that never had a child at this scale comes first (v0.283.0). E2E service run 9:
        # two L2s could open an L3; the first in file order was the one whose opportunity was
        # already served (its L3 complete, its solution in production), the founder ruled that door
        # done, and the untried L2 the new L5 was about was never offered. Stable: file order holds
        # within each group.
        history = list(active) + list(past)
        for p in sorted(live(parent_scale), key=lambda x: _had_child(x, scale, history)):
            pid = str(p["id"])
            iid = f"door-{scale.lower()}:{pid}"
            refs = _door_refs(state, scale, p)
            if (not refs or _blocked(st.get(iid, {}), today)
                    or sl.can_open(str(root), scale, parent=pid)):
                continue
            return {"id": iid, "diamond": pid, "since": today, "command": command,
                    "text": text.format(pid=pid, ref=refs[0]),
                    "why": f"the {scale} lock holds and nothing works {refs[0] or scale} yet"}
    return _setter_item(state, today, st)


def _ladder_item(root: Path, today: str, st: dict) -> dict | None:
    """One item for every diamond that could move (v0.251.0). E2E run 21: one item per diamond
    rotated through L3, L0, L1 and L2 session after session, the human snoozed each in turn and
    asked for "until I ask", and the L3 move that go-live needed was buried with the rest. One item,
    delivering diamonds first, one ruling for the family. Per-diamond rulings from 0.250.x still
    hold for their diamond."""
    if _blocked(st.get(LADDER_ID, {}), today):
        return None
    rows = [u for u in _unassessed(root, today) if not _blocked(st.get(u["id"], {}), today)]
    if not rows:
        return None
    lead = rows[0]
    if len(rows) == 1:
        text = lead["text"]
    else:
        rest = ", ".join(f"{r['diamond']} ({r['text'].split('(', 1)[1].split(')', 1)[0]})"
                         for r in rows[1:])
        text = f"{lead['text']} Also waiting: {rest}."
    text += lead.get("hint", "")
    done = [str(r.get("assessed_at")) for r in rows if r.get("assessed_at")]
    return {"id": LADDER_ID, "diamond": lead["diamond"], "since": lead["since"], "text": text,
            "command": lead["command"], "assessed_at": max(done) if done else None,
            "why": "the path to a release moves only when a diamond is assessed"}


def _product_paths_item(root: Path, today: str, st: dict) -> dict | None:
    """Ask once where the product's own files live (v0.270.0). The delivery gate knows code by its
    extension; a service's documents, a course's lessons or a publication's chapters it can only
    know by where the project keeps them. E2E second world: a bookkeeping service wrote its whole
    client pack with only an L0 in discover and the gate never fired. Asked as soon as an L0
    exists, of every product type: `app/` for software, `pilot/` for a service, `[]` for code
    only."""
    iid = "product-paths"
    if _blocked(st.get(iid, {}), today):
        return None
    p = root / ".claude" / "diamonds" / "active.yml"
    if yaml is None or not p.exists():
        return None
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None  # SPEAKS: _fired_proposals reads the same file and reports it unreadable
    if not isinstance(doc, dict) or "product_paths" in doc:
        return None
    if not any(isinstance(d, dict) and str(d.get("scale", "")).upper() == "L0"
               for k in ("active_diamonds", "completed_diamonds") for d in doc.get(k) or []):
        return None
    return {"id": iid, "since": today, "command": "/mycelium:diamond-assess",
            "text": ("Say where this product's own files live, as `product_paths` at the top of "
                     ".claude/diamonds/active.yml: folders or patterns (`app/` for software, "
                     "`pilot/` for a service's documents, `course/` for lessons), or "
                     "`product_paths: []` if the product is code only. New files there are built "
                     "through the ladder, whatever their kind; code is gated either way."),
            "why": "the delivery gate cannot see a product it does not know the place of"}


def pick(root: Path, reminders: str, today: str) -> tuple[dict | None, str]:
    """The one item, and a note when something could not be read."""
    st, note = _ledger_state(root)
    woken = _woken(root, st)
    for aid in woken:
        st[aid] = {**st[aid], "snoozed_until": None}
    item, note = _pick_from(root, reminders, today, st, note)
    if item and item.get("id") in woken:
        item = {**item, "text": (f"Snoozed until asked; since then {woken[item['id']]} product "
                                 "file(s) changed, so it is asked again. " + item["text"])}
    return item, note


def _pick_from(root: Path, reminders: str, today: str, st: dict,
               note: str) -> tuple[dict | None, str]:
    ids = set(al.scan(reminders)) if al is not None else set()
    fired, fnote = _fired_proposals(root)
    note = "; ".join(x for x in (note, fnote) if x)
    # 1. fired proposals
    for f in fired:
        if not _blocked(st.get(f["id"], {}), today):
            return {**f, "why": "a named input on a closing path landed; the ruling is yours"}, note
    # 2. records in a shape no longer read, before anything that reads the new one (v0.307.0);
    #    where the product's own files live, while nobody has said (v0.270.0); then a door that
    #    now holds: an L4 on an L3 whose lock holds, an L5 on a shipped L4 (v0.254.0)
    door = (_migrate_item(root, today, st) or _product_paths_item(root, today, st)
            or _door_item(root, today, st))
    if door:
        return door, note
    # 3. diamonds whose phase nobody has assessed since the evidence changed (v0.249.0), as ONE
    #    item for the ladder (v0.251.0), so one ruling covers them and the delivering one leads
    ladder = _ladder_item(root, today, st)
    if ladder:
        return ladder, note
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


#: ITEMS THAT ARE THE AGENT'S TO DO, NOT THE HUMAN'S TO DECIDE (v0.272.0). Recording a test's
#: verdict against the bar it was frozen with is Mycelium's own record work; only a result the bar
#: leaves unclear needs the founder. E2E service world, 2026-09-26: the pilot met its frozen bar (5
#: of 6 month-ends on time, all three clients continuing), the verdict item was shown to the
#: founder as "Decide one: run | rule | snooze | drop" for three sessions, the builder said "until
#: you say, I'll leave it alone", and the L4 stayed locked on a verdict nobody wrote. Founder,
#: 2026-09-25: "The founder shouldn't care about the 'paperwork' mycelium has to build."
AGENT_OWNED = ("verdict-l3:", "launch-data-l4:", "score-l3:")


def agent_owned(item: dict) -> bool:
    owner = str(item.get("owner") or "")
    return owner == "agent" or str(item.get("id", "")).startswith(AGENT_OWNED)


def _shown_command(item: dict) -> str:
    """The command in the form the user types (v0.286.3): `/mycelium:x` on Claude Code,
    `$mycelium:x` on Codex CLI, whose users mention a skill with `$`. The hook commands in the Codex
    manifests carry MYCELIUM_RUNTIME=codex, and this line is rendered inside those hooks."""
    cmd = str(item.get("command") or "")
    if os.environ.get("MYCELIUM_RUNTIME") == "codex":
        return re.sub(r"(?<![\w$])/mycelium:", "$mycelium:", cmd)
    return cmd


def render_human(item: dict, limit: int = 240) -> str:
    """The systemMessage form: plain, no tags, bounded. A human reads it, a wrapper means nothing
    to them, and a canvas string cannot be allowed to fill the screen."""
    text = " ".join(str(item["text"]).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    if agent_owned(item):
        late = (f" Not done for {item['shown']} sessions since {item['first_shown']}; ask the "
                "tool to do it now.") if _escalated(item) else ""
        return (f"MYCELIUM IS RECORDING: {text} The tool does this and tells you the result; it "
                f"asks you only if the result needs your judgment.{late}")
    if _escalated(item):
        return (f"NEXT ITEM, unanswered for {item['shown']} sessions since {item['first_shown']}: "
                f"{text} Decide one: run `{_shown_command(item)}` | rule | snooze-until DATE or "
                "asked | drop. If the item is wrong, say so; drop records that.")
    return (f"NEXT ITEM: {text} run `{_shown_command(item)}` | rule | snooze-until DATE or asked "
            "| drop.")


def _escalated(item: dict) -> bool:
    return int(item.get("shown") or 1) >= ESCALATE_AT


# EVERY COMMAND WE SHOW CARRIES THIS PLUGIN'S OWN PATH (v0.258.0). E2E run 32: the item said
# `advisory_ledger.py rule ...` with no path, the agent ran `find ... | head -1`, got the copy in
# plugin cache 0.220.0 (37 versions old, no MYCELIUM_TODAY), and stamped the founder's answer with a
# date before the question, so the answer never counted and the item escalated for sessions after it
# was answered. Any real install keeps old versions in its cache.
LEDGER = f'python3 "{Path(__file__).resolve().parent / "advisory_ledger.py"}"'

# Which ruling fits which answer. Run 32: "not before Monday's demo ... ask me again after
# Wednesday" was recorded as a bare `keep`, and the condition 0.254.1 exists to carry was lost.
RULING_GUIDE = ('"not now, ask me after X" is `--ruling snooze --until asked --note "X"`; '
                'a date is `--until YYYY-MM-DD`; "this is wrong" is `--ruling drop`')


def render(item: dict) -> str:
    text = str(item["text"])
    if str(item.get("id", "")).startswith("fired:"):
        text = _untrusted(text)  # a proposal read back from active.yml is canvas content
    if agent_owned(item):
        late = (f", left undone for {item['shown']} sessions since {item['first_shown']}"
                if _escalated(item) else "")
        does = str(item.get("does") or (
            f"run `{item['command']}`, record the result against the bar the test was frozen "
            "with, then tell the user what it found; ask them only if the bar leaves the result "
            "unclear"))
        return f"NEXT ITEM{late} (YOURS TO DO NOW, not the user's to decide: {does}): {text}"
    head = "NEXT ITEM"
    if _escalated(item):
        head = (f"NEXT ITEM, unanswered for {item['shown']} sessions since {item['first_shown']} "
                "(put it to the user this session and record the answer)")
    if _escalated(item) and str(item.get("id", "")).startswith(("deliver-l3:", "start-l3:")):
        # v0.273.0: a build that grows while the test waits. The test lands small; what it cannot
        # answer is the next test on the tree (founder, 2026-09-26: "that's the ost working its
        # way"), not more build now.
        head += (" THE BUILD IS GROWING WHILE THE TEST WAITS: stop extending it. Name only what "
                 "the test still needs to run with its audience; record every other open question "
                 "as a next assumption on the solution (`assumptions:` in opportunities.yml) or as "
                 "L4 work; then propose the move to Deliver")
    # An item only its doing can answer is snoozed to a date, never until asked (v0.280.0): the
    # ledger refuses the latter, so the item must not offer it.
    dated = str(item.get("id", "")).startswith(getattr(al, "DONE_TO_BE_ANSWERED", ()) or ())
    until, label = ("DATE", "snooze-until DATE") if dated else ("DATE|asked",
                                                                 "snooze-until DATE or asked")
    return (
        f"{head}: {text} run `{item['command']}` | rule (say what you decide) | "
        f"{label} (`{LEDGER} rule --id {item['id']} "
        f'--ruling snooze --until {until} --note "..."`) | '
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


# A human answering the open item in plain words (v0.252.2). The human line offers these verbs,
# so they are what an answer uses. E2E run 22: the founder said "snooze it until 2026-10-26", the
# agent never recorded it, and the item escalated back to the human as "unanswered for 3 sessions".
_ANSWER = re.compile(
    r"\b(?:snooz\w*|drop (?:it|that|this|the (?:open )?item)|until (?:i|you) ask|until asked"
    r"|not now|park (?:it|that|this))\b", re.IGNORECASE)


def answer_line(root: Path, prompt: str) -> str:
    """When the prompt looks like the human's answer to the open item: which item, and the exact
    command that records it. The ladder only stops when an answer is RECORDED; an answer the agent
    does not write down is asked again, which is the cry-wolf the ladder exists to avoid."""
    st = _read_state(root)
    if not st.get("id") or st.get("_unreadable") or not _ANSWER.search(prompt or ""):
        return ""
    if _settled(root, st):
        return ""
    return (f"MYCELIUM: this prompt looks like the user's answer to the open next item "
            f"`{st['id']}` ({' '.join(str(st.get('text_human') or '').split())[:160]}). If it is, "
            f"record it now, in their words: `{LEDGER} rule --id {st['id']} --ruling "
            'snooze --until YYYY-MM-DD|asked --note "..."` (or `--ruling drop|keep|fix`). '
            f"{RULING_GUIDE}. An answer that is not recorded is asked again.")


def prompt_line(root: Path) -> str:
    """The escalated item for the agent, once per session, at the first prompt (v0.250.0).

    The session-start copy sits at the top of a long context and was read past for 16 sessions in
    E2E run 19. This puts the item beside the user's first request of the session, only once it
    has gone unanswered for ESCALATE_AT sessions, and asks for the one thing the ladder needs: the
    human's decision, recorded. Silent below the threshold, after a ruling, and on later prompts."""
    st = _read_state(root)
    # An agent's own item comes beside the first request at once (v0.277.0): the wait exists so a
    # human is not asked for a decision every session, and record work asks nothing of them. E2E
    # rung L5-open: the session-start copy said YOURS TO DO NOW twice and was read past both times.
    due = 1 if agent_owned(st) else ESCALATE_AT
    if not st.get("id") or int(st.get("shown") or 1) < due:
        return ""
    if st.get("prompt_line_session") == st.get("session"):
        return ""
    if _settled(root, st):
        return ""
    st["prompt_line_session"] = st.get("session")
    try:
        (root / STATE_REL).write_text(json.dumps(st, ensure_ascii=False))
    except OSError:
        return ""  # could not record it was said: stay quiet rather than repeat on every prompt
    if agent_owned(st):
        # An agent's item is done, not put to the user (v0.277.0). E2E rung L5-open on 0.276.0:
        # this line told the builder to "put this item to the user and ask them to decide" for
        # the launch record, the session state said YOURS TO DO NOW, and the builder asked the
        # founder to run, rule, snooze or drop it. Every agent-owned item since 0.272.0 met this.
        return (f"MYCELIUM OPEN ITEM, shown {st['shown']} session(s) since "
                f"{st.get('first_shown')}: when you have answered this prompt, do it now. It is "
                "yours, not the user's to decide; tell them what you recorded. The item: "
                f"{st.get('text', '')}")
    return (f"MYCELIUM OPEN ITEM, unanswered for {st['shown']} sessions since "
            f"{st.get('first_shown')}: when you have answered this prompt, put this item to the "
            "user and ask them to decide: run, rule, snooze until a date, or drop (drop if the "
            f"item is wrong). Record it with `{LEDGER} rule --id {st['id']} --ruling ...`: "
            f"{RULING_GUIDE}. The item: "
            f"{st.get('text_human') or st.get('text', '')}")


def _one_line(root: Path, *, claim: bool) -> int:
    """--claim-human (session start on resume) or --prompt-line (each user prompt)."""
    if claim:
        line = claim_human(root)
    else:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        prompt = _prompt_of(payload)
        line = "\n".join(x for x in (prompt_line(root), answer_line(root, prompt),
                                      conditions_line(root, _session_of(payload),
                                                      al.today_iso() if al else "")) if x)
    if line:
        print(line)
    return 0


CONDITIONS_SAID = Path(".claude") / "state" / "conditional-snoozes-said"


def conditions_line(root: Path, session: str, today: str) -> str:
    """Items snoozed "until asked" whose ruling names a condition, for the AGENT, once per sitting
    (v0.254.1). E2E run 27: the founder answered the L3 item "not now, ask after the backup-approver
    test design is frozen". The ledger holds a date or "asked", so it became "asked" with the
    condition in the note, and nothing would ever bring it back: "ask me after X" means the tool
    asks, and only the agent can tell when X has happened. This puts the condition where the agent
    reads it; the human is not shown it."""
    if al is None:
        return ""
    st, _ = _ledger_state(root)
    held = [(aid, x.get("snooze_note")) for aid, x in st.items()
            if x.get("snoozed_until") == SNOOZE_ASKED and x.get("snooze_note")]
    if not held:
        return ""
    sitting = f"{session}|{today}"
    path = root / CONDITIONS_SAID
    try:
        if path.read_text().strip() == sitting:
            return ""
    except OSError:
        pass  # never said this sitting: say it now
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sitting + "\n")
    rows = "; ".join(f"`{aid}`: {' '.join(str(n).split())[:160]}" for aid, n in held[:5])
    return ("MYCELIUM: items the user snoozed until a condition is met. When one is met, put the "
            f"item to them again (the next item's verbs): {rows}")


def _session_of(payload: str) -> str:
    try:
        d = json.loads(payload) if payload.strip() else {}
    except ValueError:
        return ""  # no payload: the sitting is keyed on the date alone
    return str(d.get("session_id") or "") if isinstance(d, dict) else ""


def _prompt_of(payload: str) -> str:
    """The prompt text from a UserPromptSubmit payload, or '' when there is none."""
    try:
        d = json.loads(payload) if payload.strip() else {}
    except ValueError:
        return ""  # no payload is not an answer: nothing to record
    return str(d.get("prompt") or "") if isinstance(d, dict) else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One proposal per boundary, with its verb attached.")
    ap.add_argument("--project-dir", type=Path, default=Path("."))
    ap.add_argument("--session", default="unknown")
    ap.add_argument("--today", default=(
        al.today_iso() if al is not None else _dt.datetime.now(tz=_dt.UTC).date().isoformat()))
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
        "--claim-human", action="store_true",
        help="print the human line if not yet shown this sitting, mark it shown, and exit",
    )
    ap.add_argument(
        "--prompt-line", action="store_true",
        help="print the escalated item for the agent once per session (UserPromptSubmit), and exit",
    )
    ap.add_argument(
        "--settled", action="store_true",
        help="print 'settled' or 'open' for the stored item (the Stop repeat's check), and exit",
    )
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    if args.settled:
        st = _read_state(root)
        print("open" if st.get("_unreadable") else ("settled" if _settled(root, st) else "open"))
        return 0
    if args.claim_human or args.prompt_line:
        return _one_line(root, claim=args.claim_human)
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
        item["shown"], item["first_shown"] = carry(root, prev, item, args.session, args.today)
        first_at = (str(prev.get("first_shown_at") or "") if item["shown"] > 1
                    or same_sitting(prev, item["id"], args.session, args.today) else "")
        item["first_shown_at"] = first_at or _dt.datetime.now(tz=_dt.UTC).isoformat()
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
                    "plugin_version": _plugin_version(),
                    "first_shown": item["first_shown"],
                    "first_shown_at": item["first_shown_at"],
                    "shown": item["shown"],
                    # the human has seen it this sitting (Stop repeat or resume line): keep that
                    "repeated_at_stop": bool(prev.get("repeated_at_stop")) and same_sitting(
                        prev, item["id"], args.session, args.today),
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
