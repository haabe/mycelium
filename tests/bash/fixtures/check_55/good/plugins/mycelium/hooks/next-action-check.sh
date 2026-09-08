#!/bin/bash
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
# LIMITS, stated rather than implied. (1) Scope is SKILL runs, detected from the
# transcript as a tool_use named "Skill" whose skill starts with "mycelium:".
# Gate blocks (PreToolUse denies) are not detected in this version; their own
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
import json, sys, re

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

if last_text and re.search(r"(?im)^\s*(\*\*)?next:", last_text):
    sys.exit(0)

reason = (
    "Mycelium next-action check (Downe P10, hooks/next-action-check.sh): this turn ran /%s "
    "and the last message names no next action. End the turn with exactly one line, "
    "'Next: <one action>' (a skill to run, a question to answer, or 'Next: nothing until <event>'). "
    "One line, then stop." % ran_skill
)
print(json.dumps({"decision": "block", "reason": reason}))
PY
exit 0
