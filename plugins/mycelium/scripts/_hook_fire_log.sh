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
