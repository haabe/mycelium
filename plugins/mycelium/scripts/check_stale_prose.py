#!/usr/bin/env python3
"""check_stale_prose.py — a record's prose must not outlive the field beside it.

THE GAP THIS CLOSES, AND IT IS NOT THE ONE THE ABSENCE-CLAIM GUARD COVERS.

v0.101.0 made the absence-claim guard fire on OBLIGATIONS and ROLE CLAIMS, because
both rot. That guard inspects a claim at the moment it is WRITTEN. It has nothing to
say about a claim that was TRUE when written and quietly stopped being true when a
sibling field moved underneath it.

FOUND IN DOGFOOD 2026-08-07 — four instances in a single session, all in the files
the project uses to remember things, none caught by any check:

    ht-060.objective        "TWO THINGS, AND THE FIRST IS OWED TODAY. (1) Reply to
                            Frida's 2026-08-02 message."
                            ...while its own touch_log, two entries below, recorded
                            the reply sent that same day and the obligation
                            discharged. It advertised a live obligation to a real
                            person for five days.

    active-metrics.yml      last_pulled_at bumped to today while the comment beside
                            it still described the PREVIOUS pull, by number.

    ht-055.why_still_open   "the metrics pull ... has not run" — falsified by the
                            pull, rewritten, then the rewrite ("the reach half is
                            structurally unavailable") was falsified twenty minutes
                            later by a browser read. Both true when written.

The shape is identical every time: A FIELD UPDATES, THE SENTENCE BESIDE IT DOES NOT.
An obligation rots more expensively than an absence because acting on a stale one
contacts a real person (v0.101.0). A stale NOT-DONE claim rots the same way in the
other direction: it makes work look outstanding that is finished, and it is read by
the next session as current state.

WHY THIS IS A SCRIPT AND NOT A validate-template.sh CHECK — the same reason
check_leaf_lifecycle.py is. validate-template.sh runs in the FRAMEWORK repo, whose
canvas carries none of these records; they live in CONSUMER canvases. A check written
there would report nothing-to-audit forever and read green, which is the built-not-wired
class committed inside a fix for it. Surfaced ADVISORY via session-start instead.

ADVISORY, NOT BLOCKING. Both rules are heuristics over prose. A false positive costs a
sentence of reading; blocking a session on one would be worse than the defect.

Exit 0 always (advisory). Findings go to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Rule A — temporal deixis with no anchoring date. "OWED TODAY" is wrong tomorrow;
# "as of today (2026-08-07)" is not, because the reader can see when "today" was.
_DEIXIS = re.compile(
    r"\b(owed\s+today|due\s+today|as\s+of\s+today|as\s+of\s+now|today'?s\s+(?:read|pull|run|score)"
    r"|is\s+owed\s+today|owed\s+now|by\s+today)\b",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")

# Rule B — a NOT-DONE assertion. Only flagged when the same record also carries a
# DONE marker, so the rule needs both halves and does not fire on honest open work.
_NOT_DONE = re.compile(
    r"\b(has\s+not\s+(?:yet\s+)?run|have\s+not\s+(?:yet\s+)?run|not\s+yet\s+run"
    r"|has\s+not\s+been\s+sent|not\s+yet\s+sent|is\s+owed|reply\s+not\s+yet"
    r"|still\s+awaiting|not\s+yet\s+scored|has\s+not\s+landed|not\s+yet\s+captured)\b",
    re.IGNORECASE,
)
# `direction: outbound` was in this set and it is NOT a done-marker: an outbound touch
# means something was SENT, not that the specific outstanding thing was DONE. It made
# every task with any outbound entry look reconciled, and the negative control caught
# it — "question posted, no reply" is honest open work and was being flagged.
_DONE_MARKER = re.compile(
    r"\b(DISCHARGED|reply\s+sent|sent\s+the\s+same\s+day|completed_at"
    r"|SATISFIED|has\s+now\s+run|CAPTURED)\b",
    re.IGNORECASE,
)


# Rule B is FIELD-AWARE on purpose. A first cut asked only "does this record contain
# both a not-done phrase and a done marker", and on real canvases that fires on almost
# every mature record — they run hundreds of lines and carry many sub-narratives. 14
# hits on the motivating repo, most of them noise. An advisory that cries wolf gets
# tuned out, which is the same failure as one that reports green.
#
# The real signature is narrower and is what every confirmed instance looked like:
# a FRAMING field (what this record says it is) asserts not-done, while a LOG field
# (what actually happened) records it done.
_FRAMING_FIELDS = ("objective", "why_still_open", "key_findings", "summary",
                   "note", "status_note", "next_step", "read_discipline")
_LOG_FIELDS = ("touch_log", "completed_at", "outcome", "evidence_logged_to",
               "closure_note", "sent_at", "live_at")
_FIELD_RE = re.compile(r"^(\s{2,})([a-z_][a-z0-9_]*):", re.MULTILINE)

# A record that is FINISHED. Rule B's whole premise -- a framing field says not-done
# while a log field says done -- is EXPECTED and CORRECT here: a completed task's
# objective legitimately describes what it was FOR, in the past tense of intent.
# Dogfood 2026-08-07: 4 of the 7 candidates on the consumer canvas were exactly this,
# and the only way to "fix" them would have been to rewrite finished records so an
# advisory would stop talking -- destroying provenance to satisfy a metric, which is
# the Goodhart failure this checker's own docstring warns about.
# RULE A IS DELIBERATELY NOT SKIPPED. An unanchored "today" is wrong the day after it
# is written whatever the record's status, and one of the three real finds that day
# was a bare "due today" inside a COMPLETED task's log.
_TERMINAL_STATUS = re.compile(
    r"^\s{2,}status:\s*[\"']?(completed|cancelled|abandoned)\b",
    re.MULTILINE | re.IGNORECASE,
)

# An explicit reconciliation in the framing field: a human already squared the two.
_RESOLVED = re.compile(
    r"\b(DISCHARGED|now\s+satisfied|is\s+SATISFIED|was\s+discharged|no\s+longer\s+owed"
    r"|has\s+now\s+run|NOW\s+MEASURED|both\s+halves\s+are\s+now)\b",
    re.IGNORECASE,
)


def _inside_quotes(text: str, pos: int) -> bool:
    """True if `pos` sits inside a quoted span. Counts straight and curly doubles."""
    before = text[:pos]
    return (before.count('"') - before.count('\\"')) % 2 == 1 or \
           (before.count("“") > before.count("”"))


def split_fields(chunk: str) -> dict[str, str]:
    """Field split that respects nesting depth.

    A flat next-field-mark split does NOT work here and the failure is silent: a
    nested list field like `touch_log:` has children (`date:`, `direction:`, `note:`)
    that a flat split reads as sibling fields. `touch_log` then captures only the
    bytes before its first child, the discharge text never reaches the log side, and
    `note:` — a framing name — drags log prose into the framing bucket.

    Verified by the case that motivated the whole check: with a flat split, the
    pre-fix ht-060 (objective "IS OWED TODAY", touch_log recording the reply sent and
    the obligation discharged) produced NO finding. A checker that misses its own
    motivating instance is decoration.

    So: a field owns everything down to the next line indented at or above its own
    depth, children included.
    """
    marks = list(_FIELD_RE.finditer(chunk))
    if not marks:
        return {}
    # ONLY TOP-LEVEL FIELDS ARE CLASSIFIED. `note` is both a record-level framing
    # field and a child key inside every touch_log entry, so classifying children
    # dragged log prose ("REPLY-OWED DISCHARGED") into the framing bucket and the
    # resolution-suppressor then silenced the very instance this check exists for.
    # Third bug in this checker, all three found by running it against the real
    # pre-fix record rather than a fixture.
    top = min(len(m.group(1)) for m in marks)
    fields: dict[str, str] = {}
    for i, m in enumerate(marks):
        depth = len(m.group(1))
        end = len(chunk)
        for later in marks[i + 1:]:
            if len(later.group(1)) <= depth:
                end = later.start()
                break
        if depth == top:
            fields.setdefault(m.group(2), "")
            fields[m.group(2)] += chunk[m.start():end]
    return fields


def scan_text(text: str) -> list[tuple[str, str]]:
    """Return (rule, evidence) findings for one record's text."""
    out: list[tuple[str, str]] = []

    for m in _DEIXIS.finditer(text):
        window = text[max(0, m.start() - 120): m.end() + 120]
        if not _ISO_DATE.search(window):
            out.append(("A/unanchored-deixis", m.group(0).strip()))

    # Rule B does not apply to finished records. See _TERMINAL_STATUS.
    if _TERMINAL_STATUS.search(text):
        return out

    fields = split_fields(text)
    framing = " ".join(v for k, v in fields.items() if k in _FRAMING_FIELDS)
    logs = " ".join(v for k, v in fields.items() if k in _LOG_FIELDS)
    dm = _DONE_MARKER.search(logs)
    if not dm:
        return out

    for nd in _NOT_DONE.finditer(framing):
        # A record that DOCUMENTS a fixed instance quotes the stale phrase. Without
        # this the check flags its own repair notes forever, and an advisory that
        # nags about correctly-reconciled records is one the reader learns to skip.
        # Found immediately: the fixed ht-060 was re-flagged on the sentence
        # `The objective kept reading "THE FIRST IS OWED TODAY" until 2026-08-07`.
        if _inside_quotes(framing, nd.start()):
            continue
        # An explicit reconciliation in the framing field means a human already
        # squared the two. Do not ask twice.
        if _RESOLVED.search(framing):
            continue
        out.append(("B/framing-says-not-done-log-says-done",
                    f"{nd.group(0)!r} in a framing field, {dm.group(0)!r} in a log field"))
        break

    return out


def iter_records(path: Path):
    """Yield (record_id, text) per top-level record, falling back to whole-file.

    Deliberately text-based rather than YAML-parsed: the active-metrics.yml instance
    lived in a COMMENT, which a YAML parse discards. A checker that cannot see the
    comment cannot see one of the four cases that motivated it.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable or non-UTF-8 file: skip it rather than abort the scan. Narrowed
        # from a blind `except Exception` per ruff BLE001 — a bug in this module should
        # surface, not be swallowed as "file unreadable".
        return
    chunks = re.split(r"\n(?=\s*-\s+id:\s*)", raw)
    for chunk in chunks:
        m = re.search(r"id:\s*([A-Za-z0-9_-]+)", chunk)
        yield (m.group(1) if m else path.name), chunk


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    # --project-dir and --json exist to match the session-start advisory contract that
    # check_leaf_lifecycle.py already uses. Same shape, so the hook wiring is uniform.
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

    # EMPTY-INPUT HONESTY. Caught by check_empty_input_honesty.py while building this:
    # the first cut exited 0 over an empty repository, reporting "no stale-prose
    # candidates across 0 files". A check that looked at nothing and reports success is
    # indistinguishable from one that works, and reads green forever — the precise
    # failure this checker was written to catch, committed inside the checker. Refuse
    # instead, naming what was not verified.
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
        # Report the scanned count even when clean, so "nothing found" is
        # distinguishable from "nothing looked at" (empty-input honesty).
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
            print(f"OK: no stale-prose candidates across {len(targets)} canvas/state file(s).")
        return 0

    print(f"ADVISORY: {len(findings)} stale-prose candidate(s). "
          "Prose that was true when written can stop being true when a sibling field moves.")
    for rel, rec_id, rule, evidence in findings:
        print(f"  {rel} [{rec_id}] {rule}: {evidence}")
    print("\nRule A — a temporal word with no date beside it is wrong the day after it is written.")
    print("Rule B — a not-done claim in a record that also records the thing done.")
    print("Both are heuristics. Read the record; if the prose is still true, leave it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
