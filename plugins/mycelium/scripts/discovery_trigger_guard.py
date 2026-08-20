#!/usr/bin/env python3
"""Notice when the author states a fact about people nobody asked.

WHAT THIS IS
------------
A UserPromptSubmit advisory. When the author says something whose truth depends
on other people's wants or behaviour -- "users want X", "people won't bother",
"they'd probably pay for it" -- that claim is an ASSUMPTION until someone
outside the room says otherwise. The author usually knows this and is moving
fast anyway; the point of a hook is that it does not depend on remembering.

PROVENANCE
----------
Founder design, 2026-08-20, recorded at opportunities.yml#opp-051 sol-051h in
the dogfood project. His words: during the building process the author "posts
something that requires discovery ... The user might not be aware that this
requires discovery in the post." Every other route into discovery in this
framework is INVOKED -- /assumption-test, /user-interview, /handoff all wait to
be called. A tool gated on the author knowing to call it misses exactly the case
where the author does not know.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does NOT propose a study. The first response to an unvalidated claim is to
TYPE it, not to test it -- typing costs seconds, is always correct, and cannot
become a nag. Escalation to a method is a second step, and the framework has no
verified method-routing yet (opp-051 sol-051c/g are candidates, not built).

It does NOT block, ever. It fails open on every error path.

It does NOT fire on the author's own experience ("I want", "I keep forgetting"),
on reported evidence ("the support lead said users want X"), or on claims typed as
assumptions. Those are, respectively, legitimate internal_stakeholder evidence,
already-grounded, and already-honest.

THE MEASUREMENT IS PART OF THE SHIP
-----------------------------------
Every fire is appended to .claude/state/discovery-trigger-log.jsonl. This exists
because opportunities.yml#sol-048a establishes the rule this guard must live
under: a guard whose ACTION RATE stays near zero is narrowed or retired, not
left running. Shipping the trigger without the instrument would make that rule
unenforceable for this hook specifically. The log records what fired, not the
prompt -- enough to compute a rate, not enough to be a transcript.

Contract: exit 0 silent = nothing to say. exit 0 + JSON additionalContext =
advise. Never denies.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# --- Who the claim is about -------------------------------------------------
# Third parties only. Deliberately excludes first person: an author's report of
# his own experience is internal_stakeholder evidence, which this framework
# already accepts and types honestly.
_SUBJECT = (
    r"(?:the\s+)?(?:our\s+|my\s+|most\s+|some\s+|many\s+|all\s+)?"
    r"(?:users?|customers?|clients?|people|folks|devs?|developers?|engineers?|"
    r"teams?|founders?|builders?|buyers?|readers?|players?|participants?|"
    r"audience|everyone|everybody|nobody|no\s+one)"
)

# --- What is being claimed about them ---------------------------------------
# Preference, disposition or future behaviour. Present-tense observable facts
# ("users are on Windows") are NOT here: those are checkable without discovery.
_PREDICATE = (
    r"(?:want|wants|need|needs|expect|expects|prefer|prefers|love|loves|"
    r"hate|hates|like|likes|care\s+about|don'?t\s+care|"
    r"will\s+(?:use|pay|buy|churn|bother|switch|adopt)|"
    r"would\s+(?:use|pay|buy|switch|adopt|love|want|prefer)|"
    r"won'?t\s+\w+|wouldn'?t\s+\w+|"
    r"struggle\s+with|are\s+frustrated|get\s+confused|find\s+it\s+\w+|"
    r"are\s+looking\s+for|don'?t\s+understand|never\s+\w+|always\s+\w+)"
)

_CLAIM = re.compile(rf"\b{_SUBJECT}\s+{_PREDICATE}", re.IGNORECASE)

# "they/them" is too loose on its own -- it corefers to anything. Only counted
# with an explicitly dispositional modal, where the sentence is a claim about
# behaviour rather than a reference back to a named thing.
_PRONOUN_CLAIM = re.compile(
    r"\bthey(?:'d|\s+would|\s+will|\s+won'?t|\s+wouldn'?t)\s+"
    r"(?:use|pay|buy|want|need|love|prefer|switch|adopt|bother|care)\b",
    re.IGNORECASE,
)

# --- Suppressors ------------------------------------------------------------
# Anything here means the claim is already grounded, already typed, or is the
# author talking about himself. A guard that fires on honest work gets disabled.
_GROUNDED = re.compile(
    r"\b(?:said|says|told|reported|recorded|answered|replied|wrote|quoted|"
    r"observed|watched|measured|logged|"
    r"interview(?:s|ed|ing)?|survey(?:s|ed)?|"
    # NOTE the trailing \d+ rather than \d: with a single \d the closing \b
    # lands BETWEEN digits of "ht-064" and never matches, so every evidence-id
    # reference leaked through. Caught by the calibration test, 2026-08-20.
    r"according\s+to|evidence|data\s+shows?|"
    r"(?:ht|comp|opp|sol|cr)-\d+|"
    r"assum(?:e|ed|ption|ptions)|hypothes(?:is|ise|ized|es)|"
    r"guess(?:ing)?|unvalidated|speculation|my\s+prior|"
    r"i\s+(?:think|believe|suspect|reckon))\b",
    re.IGNORECASE,
)

# Questions about people are not claims about them. "what do users want?" is
# the right instinct, not a lapse.
_INTERROGATIVE = re.compile(
    r"^\s*(?:what|who|how|why|when|where|do|does|did|is|are|should|could|can)\b",
    re.IGNORECASE,
)

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")
# Below this, a fragment is punctuation or a stray word, not a claim.
_MIN_SENTENCE_CHARS = 8
_QUOTE_CHARS = 160
_QUOTE_MAX = 2

_MESSAGE = """MYCELIUM — a claim about people, and nobody outside the room has said it yet:
{quoted}
That is an ASSUMPTION until someone outside says otherwise. Two cheap moves, in
order of cost:

  1. TYPE IT. Record it as an assumption with a source class
     (internal_stakeholder if it is your own domain knowledge — that is
     legitimate evidence, it just is not external). Costs seconds. Always correct.
  2. TEST IT. Only if the decision it feeds is worth a conversation. Ask about a
     PAST specific instance, not a future hypothetical.

If you cannot reach those people at all, TYPE IT AND FLAG THE GAP — that is a
finding, not a failure. Do not let this become homework you cannot do.

Advisory only. Say so and carry on if the claim is already grounded somewhere."""


def _claim_sentences(text: str) -> list[str]:
    """Sentences making an unhedged claim about other people's dispositions."""
    out: list[str] = []
    for raw in _SENTENCE.split(text or ""):
        s = raw.strip()
        if not s or len(s) < _MIN_SENTENCE_CHARS:
            continue
        if _GROUNDED.search(s) or _INTERROGATIVE.match(s):
            continue
        if _CLAIM.search(s) or _PRONOUN_CLAIM.search(s):
            out.append(s if len(s) <= _QUOTE_CHARS else s[: _QUOTE_CHARS - 1] + "…")
    return out


def _log(hits: list[str]) -> None:
    """Append one line per fire so the action rate is computable later.

    Records WHAT fired, never the prompt. Silent on every failure — an
    instrument that breaks a session is worse than an instrument with a gap.
    """
    try:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "state"
        root.mkdir(parents=True, exist_ok=True)
        row = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "hook": "discovery-trigger-guard",
            "fires": len(hits),
            "first_match": hits[0][:120],
        }
        with (root / "discovery-trigger-log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001, S110 — never break a prompt over telemetry
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — must never break a prompt
        return 0

    text = payload.get("prompt") or ""
    if not isinstance(text, str):
        return 0

    hits = _claim_sentences(text)
    if not hits:
        return 0

    _log(hits)

    quoted = "\n".join(f"    > {h}" for h in hits[:_QUOTE_MAX])
    if len(hits) > _QUOTE_MAX:
        quoted += f"\n    ... and {len(hits) - _QUOTE_MAX} more in this prompt."
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _MESSAGE.format(quoted=quoted),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
