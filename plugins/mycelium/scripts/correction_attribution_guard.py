#!/usr/bin/env python3
"""Warn when a new corrections.md entry is written without naming who caught it.

WHY THIS EXISTS (dogfood 2026-08-20, found by `/mycelium:corrections-audit`).

`engine/agent-operating-contract.md` line 57 states, as a HARD RULE, that every
entry written to `.claude/memory/corrections.md` names its catcher. It was made
hard on 2026-08-03 precisely BECAUSE it had been advisory and 72 of 100 entries
carried no catcher.

MEASURED SEVENTEEN DAYS LATER: 15 of 91 entries (16%) carry a catcher — LOWER
than the 29% the rule scored while it was still advisory. Hardening the wording
moved the number down.

THE SHAPE IS BIMODAL, AND THAT IS THE DESIGN INPUT. 2026-08-03: 9 of 11.
2026-08-08: 8 of 9. Every other day at or near zero — 08-04: 0/13, 08-17: 0/5,
08-18: 0/14, 08-19: 0/4, 08-20: 0/5. The rule is obeyed on the days the agent is
working ON the attribution machinery and ignored on every ordinary day. It is
followed when it is the topic and invisible when it is the constraint. A 16%
average describes no day that actually happened.

So the failure is not comprehension and not intent. It is TIMING: the contract is
read once at session start and the write happens hundreds of turns later. This
fires at the write. Same reasoning, same shape, and the same existence proof as
`absence_claim_guard.py`, which fired twice on 2026-08-16 and changed what got
written both times.

IT WATCHES BASH, AND THAT IS NOT AN AFTERTHOUGHT. The five unattributed entries
of 2026-08-20 were appended with `cat >> corrections.md` inside a Bash call. A
PreToolUse guard registered only on Write|Edit|MultiEdit would have missed every
one of them — it would have shipped green against the exact corpus that motivated
it, which is this project's `fail-open-on-absent-input` cluster wearing a
different hat. corrections.md is 540 KB; nobody rewrites it with Write, and the
heredoc append is the normal path, not an edge case.

WHAT IT CANNOT DO, STATED BEFORE WHAT IT CAN.

  * It cannot tell whether the catcher named is TRUE. "Caught by hook" costs four
    words and buys a green. The rule it enforces is falsifiable only by a human
    who was there, and this guard makes no attempt at that.
  * It cannot see an entry appended by a path it does not watch — a different
    tool, an editor outside the session, a script invoked at one remove.
  * ON A Bash CALL IT READS THE COMMAND TEXT, NOT THE FILE THAT RESULTS. Found by
    running a wiring probe on 2026-08-21: a command that merely MENTIONS the path
    after a `>>` and contains a date heading fires the warning, even when nothing
    is written. This is the fail-safe direction — a spurious warning on a probe
    costs a sentence, a missed warning costs an unattributed entry — and it is
    not fixable at PreToolUse, where the file does not yet exist in its new form.
    Stated because a limitation discovered through use and left undocumented is
    the thing this docstring's opening promise is against.
  * It cannot fire on the 147 existing unattributed entries. Those are NOT
    backfillable: who caught a mistake six weeks ago is not recoverable by
    inference, and a guessed catcher corrupts the only number this loop produces.
    The guard is deliberately blind to everything already written.

WHY IT WARNS RATHER THAN DENIES, and the question is left open rather than
settled. A deny is defensible here in a way it is not for absence claims: the
check is mechanical, the vocabulary is closed, and compliance costs four words.
Against that, 147 existing entries carry no catcher, so any edit touching one for
an unrelated reason would be blocked by a naive rule — which is why this fires
ONLY on text containing a NEW entry heading, never on edits to existing prose.
Shipping deny on top of that, unmeasured, would be the same unmeasured
optimisation this project keeps catching itself in. **The escalation criterion
is stated here instead, so it is falsifiable rather than open-ended**: if the
share of new entries carrying a catcher has not cleared 80% one month after this
ships, warning is the wrong lever and this should become a deny — and if it HAS
cleared it, the deny would have bought nothing. Either way the number decides,
not the next person's appetite for stricter rules.

THE ONE THING IT MUST NOT BE is a second copy of the catcher vocabulary. A guard
enforcing a rule with its own private definition of compliance, drifting from the
script that scores it, would be an instance of
`documented-rule-diverges-from-enforcement` created inside the fix for an
instance of `documented-rule-diverges-from-enforcement`. The vocabulary is
imported from `check_correction_attribution.py`, which owns it.

Contract: exit 0 silent = nothing to say. exit 0 + JSON additionalContext = warn.
Never denies. Fails open on unparseable input, a missing sibling, or anything
unexpected — a guard that breaks a write gets deleted.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import _corrections_lib
    from check_correction_attribution import classify
except Exception:                          # noqa: BLE001 — never break a write
    _corrections_lib = None                # type: ignore[assignment]
    classify = None                        # type: ignore[assignment]

#: The one file this guard is about. Matched on the tail so it works for absolute
#: paths, repo-relative paths, and `~/...` alike.
_TARGET = re.compile(r"\.claude/memory/corrections\.md$")

#: The same tail, unanchored, for finding the file inside a shell command.
_TARGET_IN_CMD = r"[\w./~$-]*\.claude/memory/corrections\.md"

#: Shell shapes that append or rewrite. Mirrors absence_claim_guard's list — the
#: heredoc append is the one that matters and is covered by the first pattern.
_SHELL_WRITE = [
    re.compile(r">>?\s*['\"]?" + _TARGET_IN_CMD),
    re.compile(r"\btee\b\s+(?:-a\s+)?['\"]?" + _TARGET_IN_CMD),
    re.compile(r"\bsed\b[^|;]*?-i[^|;]*?['\"]?" + _TARGET_IN_CMD),
]

_SHELL_TOOLS = ("Bash", "Shell", "shell")

#: Quote at most this many offending headings; the rest are counted.
_QUOTE_MAX = 3

_MESSAGE = (
    "MYCELIUM — corrections entry with no catcher named.\n\n"
    "{quoted}\n\n"
    "The operating contract states this as a HARD RULE: every entry says who "
    "caught it, in the entry, when you write it. Add one phrase — `caught by "
    "user` / `caught by hook` / `caught by review` / `self-caught`.\n\n"
    "It is not paperwork. It feeds `check_correction_attribution.py`, whose only "
    "job is to answer whether the fix is MORE HARNESS or MORE CONTEXT. An "
    "unattributed entry is invisible to that question, and the rate now rests on "
    "under a quarter of the corpus.\n\n"
    "Attribution is reliable at the moment of logging and guesswork afterwards, "
    "which is why this fires here and why the backlog is NOT backfillable."
)


def _entry_bodies(text: str) -> list[tuple[str, str]]:
    """(date, body) for entries whose HEADING appears in this text.

    Only new entries. A write that edits prose inside an existing entry carries
    no heading and is deliberately invisible here — 147 entries predate the rule
    and must not be flagged every time one is touched.
    """
    if _corrections_lib is None:
        return []
    try:
        return _corrections_lib.entries(text)
    except Exception:                      # noqa: BLE001
        return []


def findings(text: str) -> list[str]:
    """Heading lines of new entries in `text` that name no catcher."""
    if classify is None:
        return []
    out = []
    for date, body in _entry_bodies(text):
        try:
            if classify(body):
                continue
        except Exception:                  # noqa: BLE001, S112 — a classifier
            # failure must not block a write, and there is nothing to log to:
            # stdout is the hook's protocol channel.
            continue
        head = body.strip().splitlines()[0] if body.strip() else date
        out.append(head[:160])
    return out


def _payload_text(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Write":
        return str(tool_input.get("content") or "")
    if tool_name == "Edit":
        return str(tool_input.get("new_string") or "")
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if isinstance(edits, list):
            return "\n".join(
                str(e.get("new_string") or "") for e in edits if isinstance(e, dict))
    return ""


def shell_findings(command: str) -> list[str]:
    """Findings for a Bash command that appends to or rewrites corrections.md."""
    if not any(p.search(command) for p in _SHELL_WRITE):
        return []
    return findings(command)


def hits_for(payload: dict) -> list[str]:
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
    if not isinstance(path, str) or not _TARGET.search(path):
        return []
    text = _payload_text(tool_name, tool_input)
    return findings(text) if text.strip() else []


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:                      # noqa: BLE001 — must never break a write
        return 0

    try:
        hits = hits_for(payload)
    except Exception:                      # noqa: BLE001
        return 0
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
