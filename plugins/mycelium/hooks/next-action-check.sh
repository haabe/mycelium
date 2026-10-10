#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_state_ignore.sh" 2>/dev/null || true  # .claude/state never lacks its ignore file (v0.318.0)
# Mycelium Stop check: a framework turn ends on one next action (Downe P10).
#
# WHY THIS EXISTS. A cohort tester named the stall moment on 2026-05-31: "the
# framework goes quiet and you're not sure what to run next." v0.31.1 fixed one
# such moment (the post-build nudge). This is the general case, and it has
# teeth because a warning here would be the advisory tier the framework already
# measures as skipped, including by the agent that wrote it.
#
# WHAT IT DOES. On Stop, if a Mycelium skill ran in this turn and the agent's
# last message carries no line beginning "Next:", it returns
# {"decision":"block","reason":...} so the agent finishes the turn with exactly
# one next action. It says nothing on turns where no framework skill ran: an
# ordinary answer is not a framework state and needs no "Next:" line.
#
# THE NEXT LINE CITES ITS TRIGGER (0.311.0). Contract rule 4 asks for the trigger
# of a non-trivial move as "(per: <source>)". As prose it appeared in 3 of 12
# sessions on the dogfood project, twice measured (xai-check 2026-09-14 and
# 2026-10-03). The Next: line is the turn's one recommended move, so the hook now
# also blocks a Next: line with no "(per ...)" on it, once, like the missing line.
#
# LIMITS, stated rather than implied. (1) Scope is SKILL runs: a tool_use named
# "Skill" whose skill starts with "mycelium:", or (since 0.311.0) a slash command
# the person typed, "<command-name>/mycelium:...". Meta entries in the transcript
# (a command's skill body, injected reminders) do not start a new turn. Gate blocks (PreToolUse denies) are not detected in this version; their own
# reason strings are the surface for a next action and are a separate change.
# (2) Fail-open on any read failure: no transcript, unparseable JSON, a runtime
# that does not pass transcript_path (Cursor, Codex). A fail-open check is a
# known class in this framework; it is chosen here because a Stop hook that
# blocked on its own errors would trap the session, and the validator (Check
# 55) verifies the wiring rather than the runtime. (3) stop_hook_active is
# honoured: when this hook has already blocked once in the turn, it exits 0,
# so a message that still lacks the line after one correction is let through
# rather than looped.
#
# PERSON OVERRIDE. MYCELIUM_NEXT_ACTION_CHECK=off disables it. The contract is
# "unskippable by the agent, deliberately overridable by the person"; an
# environment variable is the person's lever, not the agent's.

if [ "${MYCELIUM_NEXT_ACTION_CHECK:-on}" = "off" ]; then
  exit 0
fi

INPUT=$(cat)
[ -n "$INPUT" ] || exit 0

python3 - "$INPUT" <<'PY'
import json, os, sys, re

try:
    d = json.loads(sys.argv[1])
except Exception:
    # speaks: a check that cannot look must say so (anti-pattern #9)
    print(json.dumps({"systemMessage": "Mycelium next-action check did not run this turn: hook input was not JSON."}))
    sys.exit(0)

if d.get("stop_hook_active"):
    sys.exit(0)

path = d.get("transcript_path")
if not path:
    sys.exit(0)

try:
    lines = open(path, encoding="utf-8").read().splitlines()
except Exception:
    # speaks: a silent exit here is indistinguishable from "looked and found the line"
    print(json.dumps({"systemMessage": "Mycelium next-action check did not run this turn: transcript at transcript_path could not be read."}))
    sys.exit(0)

# A skill the PERSON invoked arrives as a slash command in their message, not as a Skill
# tool_use; until 0.311.0 those turns were never checked (found in dogfood 2026-10-03, where
# /mycelium:diamond-progress and /mycelium:xai-check both closed with no Next: line).
CMD = re.compile(r"<command-name>/(mycelium:[\w-]+)</command-name>")
cmd_skill = None

# Walk the transcript to the last HUMAN turn (a user entry whose content is
# prose, not a tool_result), then look at what the assistant did after it.
turn = []
for raw in lines:
    try:
        e = json.loads(raw)
    except Exception:
        continue
    t = e.get("type")
    if t == "user":
        # A meta entry (a slash command's skill body, an injected reminder) is not the person
        # speaking; treating it as a new human turn hid the command that started the turn (0.311.0).
        if e.get("isMeta"):
            continue
        msg = e.get("message", {})
        c = msg.get("content")
        human = False
        if isinstance(c, str):
            human = True
        elif isinstance(c, list):
            human = any(isinstance(b, dict) and b.get("type") == "text" for b in c) and not any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
        if human:
            turn = []
            text = c if isinstance(c, str) else " ".join(
                b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            m = CMD.search(text)
            cmd_skill = m.group(1) if m else None
        continue
    if t == "assistant":
        turn.append(e)

ran_skill = None
last_text = None
for e in turn:
    for b in e.get("message", {}).get("content", []) or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use" and b.get("name") == "Skill":
            s = str((b.get("input") or {}).get("skill", ""))
            if s.startswith("mycelium:"):
                ran_skill = s
        if b.get("type") == "text" and b.get("text", "").strip():
            last_text = b["text"]

ran_skill = ran_skill or cmd_skill
if not ran_skill:
    sys.exit(0)

# The docs say the transcript is written asynchronously and may lag the current
# turn, and that hooks needing the final assistant text should read
# last_assistant_message instead. Skill detection still comes from the
# transcript (the tool_use happened earlier in the turn, so it is usually
# flushed); the closing text comes from the field when present.
lam = d.get("last_assistant_message")
if isinstance(lam, str) and lam.strip():
    last_text = lam

NEXT = re.compile(r"(?im)^\s*(\*\*)?next:.*$")
PER = re.compile(r"\(per[:\s][^)]+\)", re.I)
outcome = "blocked"
next_line = NEXT.search(last_text or "")
if next_line:
    # Contract rule 4 asks for the trigger of a non-trivial move as (per: <source>). Measured on
    # the dogfood project at 3 sessions in 12 on 2026-09-14 and again on 2026-10-03 while the rule
    # was prose only (xai-check, Stage 3). The Next: line IS the turn's one recommended move, so the
    # citation is required there and nowhere else (0.311.0).
    if PER.search(next_line.group(0)):
        sys.exit(0)
    outcome = "blocked-no-per"
    reason = (
        "Mycelium next-action check (contract rule 4, hooks/next-action-check.sh): this turn ran "
        "/%s and its Next: line does not say what it rests on. Add the trigger on that line as "
        "'(per: <source>)': a canvas field, a decision-log entry, a gate, a corrections entry or "
        "what the person said. One line, then stop." % ran_skill
    )

if outcome == "blocked":
    reason = (
        "Mycelium next-action check (Downe P10, hooks/next-action-check.sh): this turn ran /%s "
        "and the last message names no next action. End the turn with exactly one line, "
        "'Next: <one action> (per: <source>)' (a skill to run, a question to answer, or "
        "'Next: nothing until <event>'), with what it rests on. One line, then stop." % ran_skill
    )
# One line per block to .claude/state/next-action-check-fires.jsonl (v0.234.0). A Stop hook
# that can refuse to end a turn and keeps no record cannot be measured, so it can never be
# retired and never defended. Records the skill that triggered it, never the turn text.
try:
    import datetime
    _d = os.path.join(os.environ.get("PROJECT_DIR")
                      or os.environ.get("CLAUDE_PROJECT_DIR") or ".", ".claude/state")
    os.makedirs(_d, exist_ok=True)
    _ts = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
    with open(os.path.join(_d, "next-action-check-fires.jsonl"), "a", encoding="utf-8") as _fh:
        _fh.write(json.dumps({"ts": _ts, "hook": "next-action-check.sh",
                              "outcome": outcome, "detail": ran_skill}) + "\n")
except OSError:
    pass
print(json.dumps({"decision": "block", "reason": reason}))
PY
exit 0
