#!/usr/bin/env bash
# scripts/_hook_input_read.sh — sourced by the blocking shell gates (0.196.0). A library, not a hook.
#
# One reading of the tool call, from scripts/_hook_input.py: every path key, resolved to its real
# place inside the project (`..`, symlinks, case), MultiEdit edits included in the content, Bash
# write targets scanned. Sets:
#   HI_TOOL      tool name
#   HI_TARGETS   one line per target: "<rel|OUTSIDE:real|GUARD:name|OPAQUE:label>\t<exists>\t<size>"
#   HI_CONTENT   everything the tool would write (for Bash: the command)
#   HI_BAD       non-empty when the input is not the documented shape (callers deny)
# Requires INPUT (the raw stdin JSON), PROJECT_DIR and CLAUDE_PLUGIN_ROOT (or a legacy tree).
# shellcheck disable=SC2034  # the HI_* variables are read by the sourcing gate, not here
hi_read_input() {
  # The helper is this library's sibling; resolve it by this file's own location first. CI has
  # no CLAUDE_PLUGIN_ROOT (0.196.0 went red there on every gate suite while green locally).
  local here helper=""
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$here/_hook_input.py" ]; then
    helper="$here/_hook_input.py"
  elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/_hook_input.py" ]; then
    helper="${CLAUDE_PLUGIN_ROOT}/scripts/_hook_input.py"
  elif [ -f "$PROJECT_DIR/.claude/scripts/_hook_input.py" ]; then
    helper="$PROJECT_DIR/.claude/scripts/_hook_input.py"
  fi
  HI_TOOL=""; HI_TARGETS=""; HI_CONTENT=""; HI_BAD=""
  if [ -z "$helper" ]; then
    HI_BAD="_hook_input.py not found under CLAUDE_PLUGIN_ROOT or .claude/scripts"
    return 0
  fi
  local out rc
  out="$(printf '%s' "$INPUT" | python3 "$helper" --project-dir "$PROJECT_DIR" 2>/dev/null)"; rc=$?
  if [ "$rc" -eq 3 ]; then HI_BAD="${out#BADINPUT:}"; return 0; fi
  if [ "$rc" -ne 0 ]; then HI_BAD="_hook_input.py exited $rc"; return 0; fi
  local line phase=targets first=1
  HI_TARGETS=""; HI_CONTENT=""
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$first" = "1" ]; then HI_TOOL="$line"; first=0; continue; fi
    if [ "$phase" = "targets" ]; then
      if [ "$line" = "---CONTENT---" ]; then phase=content; continue; fi
      HI_TARGETS="${HI_TARGETS}${HI_TARGETS:+$'\n'}${line}"
    else
      HI_CONTENT="${HI_CONTENT}${HI_CONTENT:+$'\n'}${line}"
    fi
  done <<< "$out"
}

hi_deny() {  # $1 reason
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":sys.argv[1]}}))' "$1"
  exit 0
}

hi_ask() {  # $1 reason
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":sys.argv[1]}}))' "$1"
  exit 0
}

hi_discovery_engaged() {  # exit 0 if a real purpose or an active diamond exists
  local here helper
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  helper="$here/_hook_input.py"
  [ -f "$helper" ] || helper="${CLAUDE_PLUGIN_ROOT:-}/scripts/_hook_input.py"
  [ -f "$helper" ] || helper="$PROJECT_DIR/.claude/scripts/_hook_input.py"
  python3 "$helper" --project-dir "$PROJECT_DIR" --discovery-state 2>/dev/null
}
