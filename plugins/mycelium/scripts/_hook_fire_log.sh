#!/usr/bin/env bash
# _hook_fire_log.sh — one shared way for a hook to record that it fired.
#
# WHY THIS EXISTS (2026-09-21). `check_retirement_candidates.py` decides whether a mechanism
# still earns its place from two facts: did it fire in the window, and does anything read it.
# For 10 of 25 shipped hooks it could answer NEITHER, because those hooks wrote no record at
# all — so 40% of the hook surface sat outside the only instrument that asks whether a
# mechanism should still exist. Four of the ten are BLOCKING hooks: mechanisms that can refuse
# a user's tool call, with no measurement of how often they do.
#
# The framework only grows. At 0.180.4 it carried 61 skills and 23 gates with none ever
# retired. A hook that cannot be measured can never be retired AND can never be defended; it
# just accumulates. The fix is a record, never retirement — this file makes the record cheap
# enough that "it was fiddly" stops being the reason a hook has none.
#
# WHY A SHARED HELPER RATHER THAN TEN LOGGERS. Every hook that already logs rolled its own
# (gate.sh, post-write-nudge.sh, read-log.sh, ...), which is ten chances to get the atomicity,
# the failure mode, or the privacy rule subtly different — in a codebase that already shares
# `_hook_input.sh`, `_hook_input_read.sh` and `_corrections_lib.py` for exactly this reason.
# Shared behaviour belongs in one place in a system this size.
#
# THE CALL SITE PASSES THE PATH, AND THAT IS DELIBERATE, NOT CLUMSY.
# `check_retirement_candidates.py` finds a hook's state file by regexing
# `\.claude/state/<name>.jsonl` out of the hook's source (and out of any `scripts/` helper it
# calls). A helper that COMPUTED the filename from $0 would be invisible to it — the literal
# has to appear somewhere the regex can see. And a single shared log file would be worse than
# none: the check reads a file's NEWEST row, so one file for all hooks would report every hook
# as having fired whenever any hook did. One file per hook, literal at the call site.
#
# USAGE, from a hook:
#     . "${CLAUDE_PLUGIN_ROOT}/scripts/_hook_fire_log.sh"
#     mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked" "src/new_file.py"
#
#   $1  path, relative to the project root — MUST be a literal (see above)
#   $2  outcome, short and closed-vocabulary: fired | blocked | allowed | skipped | noop
#   $3  optional detail. NEVER a prompt, a file's contents, or a user's words — see below.
#
# WHAT MUST NOT GO IN A ROW. Per the 2026-09-04 security review (DL-1262) that shaped the
# existing state logs: no prompt text, no file contents, no user words. The discovery-trigger
# log records a DIGEST and a length of its matching sentence rather than the sentence, and
# that is the standard here. A path or a rule name is fine; the thing the user typed is not.
#
# BEST EFFORT, ALWAYS. A log that cannot be written must never change a hook's verdict —
# a gate that starts failing because a disk is full would be a far worse defect than a
# missing row. Every failure path returns 0.

mycelium_log_fire() {  # $1 relative path, $2 outcome, $3 optional detail
  [ -n "${1:-}" ] || return 0
  local rel="$1" outcome="${2:-fired}" detail="${3:-}"
  local root="${PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}"
  local target="$root/$rel"
  mkdir -p "$(dirname "$target")" 2>/dev/null || return 0

  local py=""
  for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { py="$c"; break; }; done
  if [ -z "$py" ]; then
    # No interpreter: still leave a line rather than nothing, so the mtime alone
    # answers "did this ever fire". The check falls back to mtime for non-jsonl.
    printf '{"ts":"%s","hook":"%s","outcome":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" "$(basename "${BASH_SOURCE[1]:-unknown}")" \
      "$outcome" >> "$target" 2>/dev/null || true
    return 0
  fi

  # A blocked outcome is a refusal, so it also goes to the denial ledger (0.316.0, below).
  case "$outcome" in blocked*) mycelium_record_denial ;; esac

  MYC_HOOK="$(basename "${BASH_SOURCE[1]:-unknown}")" \
  MYC_OUTCOME="$outcome" MYC_DETAIL="$detail" MYC_SID="${MYCELIUM_SESSION_ID:-}" \
  "$py" - >> "$target" 2>/dev/null <<'PY' || true
import datetime, json, os
ts = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
row = {"ts": ts, "hook": os.environ.get("MYC_HOOK", ""),
       "outcome": os.environ.get("MYC_OUTCOME", "")}
d = os.environ.get("MYC_DETAIL") or ""
if d:
    # Truncated on purpose: a detail field is a label, not a transcript.
    row["detail"] = d[:200]
s = os.environ.get("MYC_SID") or ""
if s:
    row["session_id"] = s
print(json.dumps(row))
PY
  return 0
}

# ---------------------------------------------------------------------------------------------
# THE DENIAL LEDGER (0.316.0): which tool calls a Mycelium gate refused, by tool_use_id.
#
# WHY. Claude Code 2.1.287 shipped Mods, in-process plugin hooks, and a mod's `tool.check`
# handler "can also approve a call that a `PreToolUse` hook outside managed settings blocked"
# (code.claude.com/docs/en/plugins/mods/events). Mycelium's gates are exactly such hooks. A gate
# refuses, a mod approves, the call runs, and every fire log above still says "blocked": the
# record says the gate held when it did not. The fire logs answer "how often does this gate
# refuse"; nothing answered "did the refusal hold". gate-override-check.sh (PostToolUse) asks
# that question of every call that ran, against this ledger: a call that RAN with a tool_use_id
# a gate REFUSED was approved by something other than Mycelium.
#
# WHY ONE LEDGER AND NOT THE PER-HOOK FIRE LOGS. The question is per call, not per hook, and it
# is asked on every tool call that runs, so it must be one cheap lookup. The path is a literal
# here, in a sourced .sh library, on purpose: check_retirement_candidates.py follows only
# scripts/*.py helpers, so this ledger is not mistaken for any one hook's fire log.
#
# A ROW holds the time, the tool_use_id, the refusing hook's file name and the session id. No
# tool input, no content: the same rule as the fire logs (DL-1262).
#
# HOW A GATE RECORDS. Three ways, matching the three ways the gates refuse:
#   - mycelium_log_fire with an outcome starting "blocked" records it (above);
#   - hi_deny in _hook_input_read.sh records it;
#   - a gate that passes a Python helper's verdict through calls mycelium_note_refusal with the
#     helper's stdout and exit status.
# tests/python/test_gate_override_check.py holds every refusing hook to one of the three.
#
# BEST EFFORT, like the fire log: a ledger that cannot be written never changes a verdict.
_MYC_DENIAL_LEDGER=".claude/state/denied-calls.jsonl"

mycelium_record_denial() {  # reads $INPUT, the hook's raw stdin JSON
  [ -n "${INPUT:-}" ] || return 0
  local root="${PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}" py=""
  for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { py="$c"; break; }; done
  [ -n "$py" ] || return 0
  mkdir -p "$root/.claude/state" 2>/dev/null || return 0
  # $0, not BASH_SOURCE: hi_deny calls this from a library, and the refusing hook is the script
  # bash was started with. The input goes on stdin: a Write's content can exceed an env var.
  local row
  row=$(printf '%s' "$INPUT" | MYC_HOOK="$(basename "$0")" MYC_SID="${MYCELIUM_SESSION_ID:-}" \
    "$py" -c '
import datetime, json, os, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tid = data.get("tool_use_id") if isinstance(data, dict) else None
if not isinstance(tid, str) or not tid or len(tid) > 128:
    sys.exit(0)
row = {"ts": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
       "tool_use_id": tid, "hook": os.environ.get("MYC_HOOK", "")}
sid = os.environ.get("MYC_SID") or data.get("session_id") or ""
if isinstance(sid, str) and sid:
    row["session_id"] = sid
print(json.dumps(row))
' 2>/dev/null) || return 0
  # Appended only when there is a row, so a call with no id never creates an empty ledger.
  [ -n "$row" ] && printf '%s\n' "$row" >> "$root/$_MYC_DENIAL_LEDGER" 2>/dev/null
  return 0
}

mycelium_note_refusal() {  # $1 a gate helper's stdout, $2 its exit status; records a refusal
  if [ "${2:-0}" = "2" ] || printf '%s' "${1:-}" | grep -Eq '"permissionDecision"[[:space:]]*:[[:space:]]*"deny"'; then
    mycelium_record_denial
  fi
  return 0
}

mycelium_denied_by() {  # $1 tool_use_id; prints the hooks that refused that call, space-separated
  local root="${PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}" id="${1:-}"
  local ledger="$root/$_MYC_DENIAL_LEDGER"
  [ -n "$id" ] && [ -f "$ledger" ] || return 0
  # The tail is enough: a call runs within seconds of its refusal, and the ledger only grows.
  tail -n 2000 "$ledger" 2>/dev/null | grep -F "\"$id\"" | MYC_ID="$id" python3 -c '
import json, os, sys
want, hooks = os.environ["MYC_ID"], []
for line in sys.stdin:
    try:
        row = json.loads(line)
    except Exception:
        continue
    if row.get("tool_use_id") == want and row.get("hook") and row["hook"] not in hooks:
        hooks.append(row["hook"])
print(" ".join(hooks))
' 2>/dev/null || true
}

mycelium_denial_ledger() {  # prints the ledger's absolute path (callers keep the literal out of their source)
  printf '%s/%s\n' "${PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}" "$_MYC_DENIAL_LEDGER"
}
