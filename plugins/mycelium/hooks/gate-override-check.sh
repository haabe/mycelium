#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_state_ignore.sh" 2>/dev/null || true  # .claude/state never lacks its ignore file (v0.318.0)
# gate-override-check.sh — PostToolUse (v0.316.0). Did a Mycelium refusal hold?
#
# WHY THIS EXISTS. Claude Code 2.1.287 shipped Mods, in-process plugin hooks, and the docs say a
# mod's `tool.check` handler "can also approve a call that a `PreToolUse` hook outside managed
# settings blocked" (code.claude.com/docs/en/plugins/mods/events). Every Mycelium gate is such a
# hook. So a gate can refuse, another extension can approve, the call can run, and every Mycelium
# record still says the gate held: the fire logs count the refusal and nothing ever asks whether
# it held. Two outside benchmarks in the same week (a TDD gate and a boundary-guard pack, both on
# Claude Code) found the defensible value of a gate on an agent is the independent record of what
# happened; an overruled refusal makes that record false. Surfaced in the dogfood landscape sweep
# 2026-10-07 (upstream candidate gate-denial-overruled-by-a-mod-goes-unrecorded).
#
# WHAT IT DOES. A call that reaches PostToolUse RAN. If its tool_use_id is in the denial ledger
# (.claude/state, written by the gates through scripts/_hook_fire_log.sh), a Mycelium gate refused
# it and something else let it through. Then this hook (1) logs the override with the refusing
# hooks, and (2) tells the person and the agent, because the person is the one who can remove or
# confine what overruled it, and the agent must not report the refusal as having held.
#
# WHAT IT DOES NOT DO. It cannot undo the call (it already ran) and it does not name the mod:
# PostToolUse input says nothing about who approved. A permission prompt the person answered
# "yes" to is NOT an override: gates that ask (ask, not deny) never write to the ledger.
#
# COST. This runs after every gated tool call, so the common path spawns no interpreter: no
# ledger, or no tool_use_id from this input in the ledger, exits in the shell. Python runs only
# when a candidate id matches, to read the real top-level tool_use_id (a Write's content can
# contain a string that looks like one).
#
# Advisory: exit 0 always.

set -u
# shellcheck disable=SC2034  # read by mycelium_denial_ledger / mycelium_denied_by in the sourced library
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
# shellcheck source=../scripts/_hook_fire_log.sh
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null || exit 0
LEDGER="$(mycelium_denial_ledger)"
[ -f "$LEDGER" ] || exit 0

# Cheap prefilter: any tool_use_id-shaped token in the input that the ledger also holds.
HIT=0
while IFS= read -r tok; do
  [ -n "$tok" ] || continue
  if grep -qF "\"$tok\"" "$LEDGER" 2>/dev/null; then HIT=1; break; fi
done <<< "$(printf '%s' "$INPUT" | grep -oE 'toolu_[A-Za-z0-9_-]{6,120}' | sort -u)"
[ "$HIT" = "1" ] || exit 0

IFS=$'\t' read -r TOOL_ID TOOL_NAME <<< "$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("!unreadable\t")  # spoken below: an id a gate refused is in an input that cannot be read
    sys.exit(0)
d = d if isinstance(d, dict) else {}
t, n = d.get("tool_use_id"), d.get("tool_name")
if not isinstance(t, str) or not t:
    sys.exit(0)  # no id: a leading tab would let read hand the tool name to TOOL_ID
print((t if isinstance(t, str) else "") + "\t" + (n if isinstance(n, str) else ""))
' 2>/dev/null)"
[ -n "${TOOL_ID:-}" ] || exit 0
if [ "$TOOL_ID" = "!unreadable" ]; then
  # Not silent (anti-pattern #9): a refused id is in this input and the input cannot be parsed, so
  # whether that refusal held is unknown. Say so rather than report nothing.
  mycelium_log_fire ".claude/state/gate-override-fires.jsonl" "unreadable" 2>/dev/null || true
  printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "Mycelium gate override check: this tool call ran, its input names a call a Mycelium gate refused, and the input could not be parsed, so whether that refusal held is unknown. Do not report the refusal as having held without checking."}}'
  exit 0
fi
HOOKS=$(mycelium_denied_by "$TOOL_ID")
[ -n "$HOOKS" ] || exit 0

mycelium_log_fire ".claude/state/gate-override-fires.jsonl" "overridden" "$HOOKS" 2>/dev/null || true

python3 -c '
import json, sys
hooks, tool = sys.argv[1], sys.argv[2] or "a tool call"
user = (f"Mycelium: {hooks} refused this {tool} call, and it ran anyway. Something other than "
        "Mycelium approved it after the refusal, most likely a Claude Code mod (a mod can approve "
        "a call a plugin hook denied). Mycelium logged the refusal; for this call that log is "
        "wrong, and this message is the correction. If you did not mean to overrule Mycelium, "
        "disable the mod that approves tool calls. An organisation can stop that kind of mod "
        "with allowManagedModsOnly, or register Mycelium'"'"'s hooks in managed settings, which a "
        "mod cannot overrule.")
agent = (f"Mycelium gate override: {hooks} REFUSED this {tool} call (see that hook'"'"'s reason "
         "earlier in this turn) and the call ran anyway, because another extension approved it. "
         "Do not report the refusal as having held, and do not treat what the gate protects as "
         "satisfied. Tell the user the gate was overruled and ask whether they want this change "
         "kept.")
print(json.dumps({"systemMessage": user,
                  "hookSpecificOutput": {"hookEventName": "PostToolUse",
                                         "additionalContext": agent}}))
' "$HOOKS" "${TOOL_NAME:-}" 2>/dev/null || true
exit 0
