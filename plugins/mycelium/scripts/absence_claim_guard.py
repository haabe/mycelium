#!/usr/bin/env python3
"""Warn when an absence-shaped claim is written into a durable evidence surface.

WHY THIS EXISTS (dogfood 2026-08-04). In one session, five findings took the
same shape: a narrow read promoted to a broad claim without the promotion being
noticed. Two of them were written into the canvas and pushed before being caught:

  - "no need covers vocabulary ... so his signal has nowhere to go" — false.
    `opp-005` exists for exactly that, plus two ID'd evidence items, a named
    failure mode in purpose.yml and a segment constraint in scenarios.yml. The
    search had covered ONE file; the claim was about the repo.
  - "the signals exist and were never routed" — half false, and the acted-on
    half was the wrong one.

Every catch came from re-reading, prompted by the operator. No check caught any
of them. Per the Lopopolo reframe this project runs on — every interaction is a
failure of the harness to provide enough context, so fix one layer up — a
correction that recurs against an existing note needs a mechanism. There was
already an auto-memory rule about absence claims. It did not fire, because notes
are read at session start and decay; this fires at the write.

WHAT IT CANNOT DO, STATED FIRST because a guard that overstates its reach is
worse than none. It cannot verify a search happened, cannot check a claim is
true, and cannot compare the claim's scope against the search's scope — the case
that actually caused the 2026-08-04 error. The sentence that did the damage
carried a citation ("checked all eleven statements") and was still wrong,
because eleven statements is one file and the claim was about the project. So a
guard that merely demanded a citation would have PASSED the instance that
motivated it. That is why the warning text is about scope matching rather than
about citing, and why the claim-shape trigger is deliberately wider than the
citation suppressor.

WHAT IT DOES. On a Write/Edit into a `.claude/` evidence surface (canvas, memory,
harness, evals, diamonds), it looks for assertive absence — universal negatives
about a collection: "no need covers", "nothing checks", "never routed", "nowhere
to go", "does not exist", "zero sources". When one appears WITHOUT a named search
scope in the same sentence, it says so, at the moment the claim becomes durable.

IT WARNS, IT DOES NOT BLOCK, for the same reason shell_safety_guard does not:
absence claims are frequently correct and necessary — "no consumer has asked for
this" is a real and valuable finding, and this project's canvas is full of them
doing honest work. A guard that blocks real work gets disabled, which is how a
guard dies. The teeth are in the timing, not the veto: it quotes the sentence
back at the moment it is being made permanent.

Contract: exit 0 silent = nothing to say. exit 0 + JSON additionalContext = warn.
Never denies. Fails open on unparseable input.
"""

from __future__ import annotations

import json
import re
import sys

#: Only durable evidence surfaces. Framework source, tests and scratch files are
#: full of legitimate absence prose ("no matches", "does not exist") and warning
#: on those would train the reader to ignore this.
_WATCHED_PATH = re.compile(r"/\.claude/(canvas|memory|harness|evals|diamonds)/")

#: The same surfaces as they appear inside a shell command, where the path is
#: usually relative (`.claude/memory/corrections.md`) rather than absolute.
_SURFACE = (r"(?P<path>[\w./~$-]*\.claude/"
            r"(?:canvas|memory|harness|evals|diamonds)/[\w./-]+)")

#: Shell constructs that put text into one of those files. Separate patterns
#: rather than one alternation, because a named group cannot repeat in a single
#: expression. `cp`/`mv` are deliberately absent: they move bytes that exist
#: elsewhere, so the command carries no prose to scan.
_SHELL_WRITE = [
    re.compile(r">>?\s*['\"]?" + _SURFACE),                       # cat >> f, echo > f
    re.compile(r"\btee\b\s+(?:-a\s+)?['\"]?" + _SURFACE),         # | tee -a f
    re.compile(r"\bsed\b[^|;]*?-i[^|;]*?['\"]?" + _SURFACE),      # sed -i ... f
]

#: Assertive universal negatives about a COLLECTION. Each noun/verb list is kept
#: tight on purpose: "no product training" and "nothing ships wrong" are ordinary
#: prose from this project's own canvas and must not fire, so the nouns are
#: artefact words and the verbs are search-result words.
_ABSENCE = [
    # "no X covers/exists/reaches ..." and "no X in <collection>".
    #
    # THE VERB IS LOAD-BEARING, and calibration against 88,939 real sentences is
    # what put it there. A bare `no <artefact-noun>` fired on ledger prose —
    # "No confidence gate moved", "no skill or framework change applied", "NO
    # evidence entry drafted" — which are records of what a SESSION DID, not
    # claims about what EXISTS. Those are always true when written and need no
    # search behind them. The claim this guard is for is about the state of the
    # corpus, so it must reach for an existence or coverage verb, or place
    # itself inside a collection.
    re.compile(r"\bno\s+(?:\w+\s+){0,2}"
               r"(?:entry|entries|need|needs|opportunit(?:y|ies)|source|sources|"
               r"check|checks|test|tests|rule|rules|mechanism|mechanisms|gate|"
               r"gates|skill|skills|hook|hooks|signal|signals|evidence|instance|"
               r"instances|record|records)\s+"
               r"(?:covers?|exists?|checks?|tracks?|measures?|reaches?|names?|"
               r"mentions?|addresses|catches|gates?|enforces?|writes?|reads?|"
               # PAST TENSE, and its absence was a live hole. "No check caught
               # any of them" — a sentence from the corrections entry that
               # motivated this guard — matched nothing, because the list had
               # `catches` and not `caught`. Found by running the hook
               # end-to-end on a real sentence instead of a synthetic one; the
               # 56 fixture tests all used present tense and all passed.
               r"covered|existed|checked|tracked|measured|reached|named|"
               r"mentioned|caught|gated|enforced|"
               r"in\b|anywhere\b|across\b)", re.IGNORECASE),
    re.compile(r"\bnothing\s+(?:in\b|that\b|here\b|checks\b|covers\b|reads\b|"
               r"gates\b|enforces\b|measures\b|tracks\b|catches\b|surfaces\b|"
               r"caught\b|covered\b|tracked\b|measured\b|enforced\b)",
               re.IGNORECASE),
    re.compile(r"\b(?:has|have|had|was|were|is|are)\s+never\s+"
               r"(?:been\s+)?(?:reached|routed|ran|run|fired|logged|captured|"
               r"surfaced|checked|measured|read|asked|raised|recorded)\b",
               re.IGNORECASE),
    re.compile(r"\bnowhere\s+to\s+go\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+exist\b|\bdo\s+not\s+exist\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are)\s+not\s+covered\b", re.IGNORECASE),
    re.compile(r"\bzero\s+(?:\w+\s+){0,2}"
               r"(?:source|sources|need|needs|entries|entry|instances|"
               r"evidence|records)\b", re.IGNORECASE),
    re.compile(r"\bnobody\s+(?:read|audited|asked|checked|looked|noticed|ran)\b",
               re.IGNORECASE),
]

#: A named search scope. Deliberately NARROWER than what would satisfy a careful
#: reader: a bare "checked all eleven statements" counts here, and on 2026-08-04
#: that exact phrase accompanied a false claim. Suppression means "the author
#: showed their work", not "the claim is sound" — which is why the warning text
#: leads with scope matching rather than with citing.
_SCOPE = re.compile(
    r"\*\.(?:ya?ml|md|py|json)"                      # a glob
    r"|\b(?:grep|rg|ripgrep|ag)\b"                   # a search tool
    r"|\b[\w./-]+\.(?:ya?ml|md|py|json)\b"           # a named file
    r"|\bchecked\s+(?:all|every|each)\b"
    r"|\bsearched\b|\bverified\s+across\b|\bmeasured\s+across\b"
    r"|\bacross\s+(?:all\s+)?(?:\d+|the\s+\w+)\b",
    re.IGNORECASE,
)

#: Sentence-ish split. Keeps the scope test local: a citation three paragraphs
#: away does not ground this claim, and treating a whole canvas entry as one
#: context made every absence claim in it look cited.
#:
#: SEMICOLONS AND COLONS ARE DELIBERATELY NOT BREAKS. They were, in the first
#: draft, and that split "searched the canvas; nothing in it tracks this" into a
#: citation and an orphaned claim — then warned on the orphan. Attaching evidence
#: to an assertion with a colon or semicolon is exactly how this is written in
#: practice, so breaking there punishes the phrasing the guard is asking for.
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")

#: How much of an offending sentence to quote back, and how many to quote. The
#: warning has to fit in front of the agent without becoming the thing it skims:
#: enough to recognise the sentence, not enough to re-read the write.
_QUOTE_CHARS = 220
_QUOTE_MAX = 3

_MESSAGE = (
    "MYCELIUM ABSENCE-CLAIM WARNING (the write still proceeds):\n"
    "  An assertive absence is being recorded to a durable evidence surface, "
    "with no search named in the same sentence:\n{quoted}\n"
    "  State WHAT WAS SEARCHED, in the sentence, and check the claim's scope "
    "does not exceed it. Naming a search is not sufficient: on 2026-08-04 a "
    'claim carrying "checked all eleven statements" was still wrong, because '
    "eleven statements is ONE FILE and the claim was about the repo. The "
    "concern it declared missing had its own opportunity, two ID'd evidence "
    "items, a named failure mode and a segment constraint.\n"
    "  This is a warning, not a block. Absence findings are often correct and "
    "valuable. See corrections.md 2026-08-04 — fifth instance in one session, "
    "every one caught by re-reading and none by any check."
)


def findings(text: str) -> list[str]:
    """Absence-shaped sentences that name no search. Empty means nothing to say."""
    out: list[str] = []
    for sentence in _SENTENCE.split(text):
        s = sentence.strip()
        if not s or _SCOPE.search(s):
            continue
        if any(p.search(s) for p in _ABSENCE):
            out.append(s if len(s) <= _QUOTE_CHARS
                       else s[:_QUOTE_CHARS - 3] + "...")
    return out


def _payload_text(tool_name: str, tool_input: dict) -> str:
    """The prose actually being written, per tool. Unknown tools contribute none.

    MultiEdit is handled because the hook matcher it registers under is
    `Write|Edit|MultiEdit`. Reading only the first two would have shipped a guard
    that is silent on a third of the writes it is invoked for — a gap invisible
    from the manifest, which lists the hook as covering all three.
    """
    if tool_name == "Write":
        v = tool_input.get("content")
    elif tool_name == "Edit":
        v = tool_input.get("new_string")
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return ""
        return "\n".join(e.get("new_string", "") for e in edits
                         if isinstance(e, dict) and isinstance(e.get("new_string"), str))
    else:
        return ""
    return v if isinstance(v, str) else ""


def shell_findings(command: str) -> list[str]:
    """Absence claims inside a shell command that writes to an evidence surface.

    WHY THIS HALF EXISTS (added v0.84.0, one release after the tool half). The
    first version watched Write/Edit/MultiEdit only, and its own commit message
    said it "fires at the write". It did not. Every correction appended during
    the session that produced it went in as `cat >> .claude/memory/corrections.md
    <<'EOF'`, and no PreToolUse write matcher sees a heredoc. A guard blind to
    the way its author actually writes is the documented-not-operational failure
    this project audits others for, so the reach is closed rather than noted.

    THE TARGET PATH IS STRIPPED BEFORE SCANNING, which is not fussiness. The
    scope suppressor counts a named file as showing your work, and the write
    target IS a named file — so `echo "No entry covers x." >> .claude/memory/
    corrections.md` would suppress itself on the strength of its own
    destination. Removing the target first is what makes the one-liner case
    work at all.
    """
    targets = [m.group("path") for p in _SHELL_WRITE for m in p.finditer(command)]
    if not targets:
        return []
    text = command
    for t in targets:
        text = text.replace(t, " ")
    return findings(text)


#: Shell tool names across the three runtimes. Cursor calls it `Shell`, not
#: `Bash` — reading only `Bash` would register the hook there and have it no-op,
#: the same dead-registration class v0.83.0 fixed in the manifests themselves.
_SHELL_TOOLS = ("Bash", "Shell", "shell")


def hits_for(payload: dict) -> list[str]:
    """Findings for one hook payload, whichever half of the guard applies."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []

    tool_name = payload.get("tool_name") or ""
    if tool_name in _SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            return []
        return shell_findings(command)

    path = tool_input.get("file_path")
    if not isinstance(path, str) or not _WATCHED_PATH.search(path):
        return []
    text = _payload_text(tool_name, tool_input)
    return findings(text) if text.strip() else []


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:                      # noqa: BLE001 — must never break a write
        return 0

    hits = hits_for(payload)
    if not hits:
        return 0

    quoted = "\n".join(f"    > {h}" for h in hits[:_QUOTE_MAX])
    if len(hits) > _QUOTE_MAX:
        quoted += f"\n    ... and {len(hits) - _QUOTE_MAX} more in this write."
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": _MESSAGE.format(quoted=quoted),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
