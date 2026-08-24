#!/usr/bin/env python3
"""read_before_research_guard.py — the canvas already answered this, and better.

THE GAP, found by the i-productified dogfood project 2026-08-24 and REPRODUCED here.
Mycelium has a read-before-WRITE rule and had no read-before-RESEARCH rule:

    grep -rl "Preflight: Read target canvas" skills/   -> 24 skills
    grep -rniE "grep the canvas|before searching|before web" \
         skills/ engine/ harness/ scripts/ hooks/       -> 0 real hits

(The two `hooks/` hits are incidental prose, not a rule. The reporting project
flagged that its own grep covered three directories; `scripts/`, `hooks/` and the
consumer `CLAUDE.md` were checked here and the finding survives all three.)

TWO FAILURES IN ONE SESSION, THE SECOND AFTER THE LESSON WAS WRITTEN DOWN.
  1. ~6 web searches and 4 fetches to reconstruct a holding company's ownership and
     a contact's position in it. All of it was already in `human-tasks.yml` from a
     brreg sweep three weeks earlier — including a worked-out implication for the
     named contact that was BETTER than what the searches produced.
  2. MINUTES LATER, in the same turn, having just logged instance 1 with the
     prevention rule "grep the canvas before web-searching", the agent recommended a
     company as "a genuine find" — a company `purpose.yml` records the founder
     arguing against on ethical grounds, whose rebrand he had called greenwashing.
     He had to hand his own recorded position back to the agent.

WHY THE WRITE-SIDE PREFLIGHT DOES NOT COVER IT. That one protects DATA INTEGRITY:
do not clobber what you have not read. This is a different failure. The write is
fine, the file is fine, the validator passes. What is lost is that RESEARCH
CONDUCTED WITHOUT THE CANVAS IS ANALYSIS WITHOUT THE CONSTRAINTS THE CANVAS ALREADY
RECORDED — quarantine entries, values gates, prior judgements, source caveats.

**THIS IS NOT A TOKEN-EFFICIENCY CHECK. IT IS A CONSTRAINT-LOSS CHECK.** Instance 1
cost tokens and lost a better answer. Instance 2 lost a DECISION: the founder had
already ruled on that company, and the agent handed it back to him as a discovery.
**The canvas is not a cache. It is a record of judgements already made.**

WHY A HOOK AND NOT A LINE IN THE SKILLS. Instance 2 happened AFTER the prose rule
existed, in the same turn, written by the same agent. "Add a line to the skills" is
therefore ALREADY FALSIFIED, and this repo has the precedent: `check_reply_owed.py`
was extracted because the same rule lived in prose and in a hook — "one rule, two
implementations, and only one of them could be executed." It also dissolves the
which-skills question: instance 2 happened in ordinary conversation, inside no skill.

TIER: WARN, NEVER BLOCK, FAIL OPEN. Modelled on `absence-claim-guard`. A guard that
blocks real work gets disabled, and searching for something the canvas mentions is
frequently correct — the canvas names hundreds of companies and people.

**IT WILL BE NOISY HERE AND THAT IS PLANNED FOR, NOT DISCOVERED LATER.** Every firing
is logged to `.claude/state/read-before-research-log.jsonl`. The tier and any
narrowing are to be set by the MEASURED action rate, exactly as the absence-claim
guard's were — and `opportunities.yml#sol-048a` already commits this project to
retiring a guard whose action rate stays near zero. If that is this one, retire it.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# Proper-noun-ish tokens and quoted phrases from the QUERY, not from the user turn.
# The query is what the agent is about to do: short, already distilled, and available
# at the exact moment of failure. The user turn is noisy and can be many turns back —
# instance 1's brreg sweep was three weeks earlier and nothing in that turn named it.
_CAP = re.compile(r"\b[A-ZÆØÅ][\wÆØÅæøå'\u2019-]{3,}\b")
_QUOTED = re.compile(r"[\"“]([^\"”]{4,60})[\"”]")

# Words that are capitalised in a query without naming an entity the canvas has a
# JUDGEMENT about. Deliberately short: over-filtering here reintroduces the gap, and
# the log is the instrument for tuning this, not intuition.
_STOP = {
    "What", "When", "Where", "Which", "Who", "Why", "How", "Does", "Should",
    "The", "This", "That", "There", "Their", "Then", "With", "From", "Into",
    "About", "After", "Before", "Http", "Https", "Search", "Latest", "Best",
}


def _canvas_files(project_dir: Path):
    return sorted((project_dir / ".claude" / "canvas").glob("*.yml"))


def candidates(query: str):
    """Entity-shaped tokens from a query string. Order-preserving, de-duplicated."""
    found, seen = [], set()
    for phrase in _QUOTED.findall(query or ""):
        key = phrase.strip().lower()
        if key and key not in seen:
            seen.add(key)
            found.append(phrase.strip())
    for tok in _CAP.findall(query or ""):
        if tok in _STOP:
            continue
        if tok.lower() in seen:
            continue
        seen.add(tok.lower())
        found.append(tok)
    return found


def search_canvas(project_dir: Path, terms, per_term=2, cap=3):
    """Return [(term, file, lineno, line)] for terms the canvas already mentions."""
    files = _canvas_files(project_dir)
    if not files:
        return []
    hits = []
    lowered = [(t, t.lower()) for t in terms]
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for term, low in lowered:
            n = 0
            for i, line in enumerate(lines, 1):
                if low in line.lower():
                    hits.append((term, path.name, i, line.strip()[:160]))
                    n += 1
                    if n >= per_term:
                        break
            if len(hits) >= cap:
                return hits[:cap]
    return hits[:cap]


def _query_from(payload):
    """The searched string, whatever the tool called it."""
    ti = payload.get("tool_input") or {}
    for key in ("query", "url", "prompt", "q", "search"):
        val = ti.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _log(project_dir: Path, tool: str, terms, hits):
    """Every firing, so the tier is set by a measured action rate rather than taste."""
    try:
        state = project_dir / ".claude" / "state"
        state.mkdir(parents=True, exist_ok=True)
        rec = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "hook": "read-before-research-guard",
            "tool": tool,
            "terms": terms[:6],
            "hits": [{"term": t, "file": f, "line": n} for t, f, n, _ in hits],
        }
        with (state / "read-before-research-log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # advisory hook: logging must never cost the user their search


def build_message(hits):
    lines = [
        "MYCELIUM READ-BEFORE-RESEARCH WARNING (the search still runs):",
        "  You are about to search externally for something the canvas ALREADY records:",
    ]
    for term, fname, no, text in hits:
        lines.append(f"    {term} -> .claude/canvas/{fname}:{no}")
        lines.append(f"        {text}")
    lines += [
        "  READ THOSE FIRST. This is not about saving tokens. Research conducted without",
        "  the canvas is analysis without the constraints the canvas already recorded —",
        "  quarantine entries, values gates, prior judgements, source caveats.",
        "  THE CANVAS IS NOT A CACHE. IT IS A RECORD OF JUDGEMENTS ALREADY MADE. On",
        "  2026-08-24 an agent recommended a company as 'a genuine find' that the canvas",
        "  recorded the founder rejecting on ethical grounds — he had to hand his own",
        "  position back. That is the failure this exists for, not the wasted searches.",
        "  Frequently you will have read them already, or the match will be incidental.",
        "  Proceed; this never blocks.",
    ]
    return "\n".join(lines)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # fail open: a malformed payload must not cost the user their search
    if not isinstance(payload, dict):
        return 0

    query = _query_from(payload)
    if not query:
        return 0

    project_dir = Path(payload.get("cwd") or ".")
    terms = candidates(query)
    if not terms:
        return 0

    hits = search_canvas(project_dir, terms)
    if not hits:
        return 0

    _log(project_dir, str(payload.get("tool_name", "")), terms, hits)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": build_message(hits),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
