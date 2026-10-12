#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium PreToolUse gate
# Lightweight check before code changes. Exit 0 = allow, Exit 2 = block.
#
# Layer 1 of Mycelium's 6-layer enforcement architecture.
# Fires on every Write/Edit/MultiEdit to source code, and on every shell command.
#
# Checks:
# 1. Preflight stamp freshness (corrections.md read recently)
# 2. Corrections.md not stale since last preflight
# 3. A secret typed into a shell command (G-S1 ENFORCED), and since 0.323.0 a scan of what a
#    `git commit` or `git push` would take. A write is no longer scanned. A scan that cannot
#    run refuses (0.319.1).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Stamp path: per-user + per-project under $TMPDIR. The old shared
# /tmp/mycelium-preflight-stamp was world-predictable — any local user could
# pre-create or symlink it (clobber / privacy) and two projects/users on one
# box collided on a single stamp. preflight.sh derives this identically.
_stamp_uid=$(id -u 2>/dev/null || echo 0)
_stamp_phash=$(printf '%s' "$PROJECT_DIR" | { md5 2>/dev/null || md5sum 2>/dev/null; } | tr -cd '0-9a-f' | cut -c1-12)
STAMP_FILE="${TMPDIR:-/tmp}/mycelium-preflight-stamp-${_stamp_uid}-${_stamp_phash:-0}"

# Parse tool input from stdin. Single python spawn (not two) emits tool_name
# and file_path NUL-separated — this hook is on the Write/Edit hot path, so we
# avoid paying a second interpreter startup per edit. NUL separation keeps it
# correct even if a path contained a newline. On parse failure both vars stay
# empty (same fallback as before).
# shellcheck disable=SC2034  # INPUT is read by hi_read_input in the sourced library
INPUT=$(cat)
HI_LIB="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input_read.sh"
# shellcheck source=/dev/null
. "$HI_LIB"
hi_read_input
if [ -n "$HI_BAD" ]; then
  hi_deny "Mycelium gate: refused, tool input is not the documented shape ($HI_BAD). A guard that cannot read the call does not guess (adversarial pass 2026-09-11)."
fi

# CHECK 0: guard state is human-owned. A write to the file that switches a blocking hook off asks
# the person; the agent cannot answer for them (adversarial pass 2026-09-11, every off-switch was
# agent-writable). MYCELIUM_GUARD_STATE_EDIT=1 in the human's own shell skips the ask.
if [ "${MYCELIUM_GUARD_STATE_EDIT:-}" != "1" ]; then
  while IFS=$'\t' read -r target _exists _size; do
    case "$target" in
      GUARD:*) hi_ask "Mycelium gate: ${target#GUARD:} switches a blocking hook off, and this tool call writes it. A person decides that, not the agent. Approve if you asked for it; set MYCELIUM_GUARD_STATE_EDIT=1 in your own shell for setup work.";;
    esac
  done <<< "$HI_TARGETS"
fi

# Which targets do the checks below apply to? Every real path inside the project, `.claude/`
# included, except Mycelium's own state folder; and every shell command.
SCAN=0
while IFS=$'\t' read -r target _exists _size; do
  case "$target" in
    ""|OUTSIDE:*|GUARD:*|OPAQUE:*) ;;
    .claude/state/*) ;;
    *) SCAN=1;;
  esac
done <<< "$HI_TARGETS"
[ "$HI_TOOL" = "Bash" ] && SCAN=1
[ "$SCAN" = "1" ] || exit 0

# ============================================================
# CHECK 1: a secret typed into a shell command (G-S1)
# ============================================================
# SINCE 0.323.0 A WRITE IS NOT SCANNED. Until then this check ran on the content of every file
# write, with the short list in scripts/_secret_patterns.sh. Replayed 2026-10-12: an unquoted
# KEY=value passed, an env file was treated like source code, and nothing looked at what was
# staged. The maintainer's direction: "Don't let passwords into the repo", at the commit, with an
# established scanner. So the agent may now write a key into a file, an env file being where one
# belongs, and may not commit or push one (CHECK 1b below, scripts/commit_scan.py). The write-time
# scan was removed in the same release that added the commit scan, never before it.
# What stays here is the text of a shell command: a key typed on a command line ends up in logs
# and transcripts whatever happens to the repository.
CONTENT=""
[ "$HI_TOOL" = "Bash" ] && CONTENT="$HI_CONTENT"

if [ -n "$CONTENT" ]; then
  # shellcheck source=/dev/null
  . "$(dirname "${BASH_SOURCE[0]}")/../scripts/_secret_patterns.sh" 2>/dev/null || SECRET_PATTERNS=()
  if [ "${#SECRET_PATTERNS[@]}" -eq 0 ]; then
    hi_deny "GUARDRAIL G-S1: the secret scan could not run, so this command is refused. Nothing was detected; Mycelium's own list of patterns could not be read (scripts/_secret_patterns.sh). A scan that cannot look cannot say the command holds no credential. This is a fault in the install, not in the command: it belongs at github.com/haabe/mycelium/issues."
  fi

  # A SCAN THAT CANNOT RUN IS A REFUSAL, NOT A PASS (0.319.1).
  # grep has three answers: 0 a line matched, 1 none did, 2 or more "I could not run this" (a
  # pattern this grep rejects, no grep on PATH). Until 0.319.1 each pattern ran as
  # `printf ... | grep -qE "$PATTERN" 2>/dev/null` inside an `if`, which reads the last two as
  # one and threw grep's own complaint away. A scan that never ran therefore passed everything,
  # credentials included, and said nothing.
  # Now each pattern's status is read on its own: PIPESTATUS[1] is grep's, whatever printf did
  # and whether or not pipefail is ever set here. `-c` so grep reads the whole content (no closed
  # pipe) and what it prints is a count, or with 2>&1 its own words when it fails.
  # The refusal says the scan failed and how. It is NOT the "potential secret" refusal: nothing
  # was detected, and telling the agent to hunt for a credential that may not be there would
  # send it the wrong way.
  SCAN_N=0
  for PATTERN in "${SECRET_PATTERNS[@]}"; do
    SCAN_N=$((SCAN_N + 1))
    SCAN_SAID=$(printf '%s\n' "$CONTENT" | grep -cE -- "$PATTERN" 2>&1; exit "${PIPESTATUS[1]}")
    SCAN_RC=$?
    if [ "$SCAN_RC" -ge 2 ]; then
      SCAN_SAID=${SCAN_SAID%%$'\n'*}
      hi_deny "GUARDRAIL G-S1: the secret scan could not run, so this command is refused. Nothing was detected in it; the scan itself failed: grep exited $SCAN_RC on pattern $SCAN_N of ${#SECRET_PATTERNS[@]} (${SCAN_SAID:-it said nothing}). A scan that cannot read the command cannot say it holds no credential, and until 0.319.1 a failed scan passed everything. This is a fault in the machine's grep or in Mycelium's patterns, not in the command: the person can check that grep -E works on the PATH the hooks run with; if it does, the fault is in Mycelium's patterns and belongs at github.com/haabe/mycelium/issues."
    fi
    if [ "$SCAN_RC" -eq 0 ]; then
      # Output JSON for Claude with deny decision; the refusal goes to the denial ledger (0.316.0)
      # shellcheck source=/dev/null
      . "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null && mycelium_record_denial
      cat << 'DENY_EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "GUARDRAIL G-S1 VIOLATION: Potential secret/credential detected in this shell command. A value typed on a command line ends up in logs and transcripts. Read it from an environment variable or a file the command names instead, and if the value is real, tell the person it should be replaced."
  }
}
DENY_EOF
      exit 0
    fi
  done
fi

# ============================================================
# CHECK 1b: what is committed and what is pushed (v0.323.0)
# ============================================================
# scripts/commit_scan.py says why and how. It answers with a deny, with a once-a-session note that
# no scanner is installed, or with nothing. A helper that cannot run is a refusal, like a scan
# that cannot run. The note is printed at the very end, after the checks below have passed.
SCAN_NOTE=""
case "$CONTENT" in
  *git*commit*|*git*push*)
    CS_OUT=$(printf '%s' "$INPUT" | python3 "$(dirname "${BASH_SOURCE[0]}")/../scripts/commit_scan.py" --pre --project-dir "$PROJECT_DIR" 2>/dev/null)
    CS_RC=$?
    case "$CS_OUT" in
      *'"permissionDecision": "deny"'*)
        # shellcheck source=/dev/null
        . "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null && mycelium_record_denial
        printf '%s\n' "$CS_OUT"
        exit 0;;
    esac
    if [ "$CS_RC" -ne 0 ]; then
      hi_deny "Mycelium commit scan: the secret scan could not run, so this command is refused. Nothing was found; the helper that scans what is committed and pushed exited $CS_RC. A scan that cannot look cannot say there is no secret. Tell the person: they can commit or push from their own terminal."
    fi
    SCAN_NOTE="$CS_OUT";;
esac

# ============================================================
# CHECK 2: Preflight stamp freshness
# ============================================================
NEEDS_RENEWAL=0
if [ ! -f "$STAMP_FILE" ]; then
  NEEDS_RENEWAL=1
else
  STAMP_MOD=$(stat -f %m "$STAMP_FILE" 2>/dev/null || stat -c %Y "$STAMP_FILE" 2>/dev/null || echo 0)
  STAMP_AGE=$(( $(date +%s) - STAMP_MOD ))
  if [ "$STAMP_AGE" -gt 14400 ]; then
    NEEDS_RENEWAL=1
  fi
fi

# A BLOCK LEAVES A LINE (v0.204.0). gate.sh exits 2 on a stale preflight stamp or a changed
# corrections hash, mid-session, on every source write, and until now wrote nothing anywhere
# when it did: no log, no session id, no count. The one human complaint on record about
# "too many gates" (plugin 0.23.4) predates every hook that was checked when it was ruled
# on, and this is the hook that fires repeatedly mid-flow; whether it fires on real users
# was unmeasurable for the same reason discovery-gate's was. One JSON line per block to
# .claude/state/gate-block-log.jsonl (gitignored with the rest of state/), read by
# check_hook_delivery.py. Best effort: a log that cannot be written never changes the verdict.
_gate_block_log() {  # $1 reason
  local dir="$PROJECT_DIR/.claude/state"
  mkdir -p "$dir" 2>/dev/null || return 0
  printf '%s' "$INPUT" | python3 -c '
import json, sys, datetime
reason = sys.argv[1]
try:
    sid = (json.load(sys.stdin) or {}).get("session_id", "")
except Exception:
    sid = ""
ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
print(json.dumps({"ts": ts, "hook": "gate.sh", "reason": reason, "session_id": sid}))
' "$1" >> "$dir/gate-block-log.jsonl" 2>/dev/null || true
  # Every caller exits 2 next, so this is a refusal: it goes to the denial ledger (0.316.0).
  # shellcheck source=/dev/null
  . "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null && mycelium_record_denial
}

if [ "$NEEDS_RENEWAL" -eq 1 ]; then
  # Preflight resolution — prefer plugin path (post-0.20.x), fall back to legacy.
  # Mirrors framework-guard.sh: plugin installs have no .claude/hooks/ tree, so
  # the hardcoded legacy path silently no-op'd (2>/dev/null swallowed the missing
  # file) and preflight never ran for plugin users.
  PREFLIGHT=""
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/hooks/preflight.sh" ]; then
    PREFLIGHT="${CLAUDE_PLUGIN_ROOT}/hooks/preflight.sh"
  elif [ -f "$_MYCELIUM_ROOT/hooks/preflight.sh" ]; then
    PREFLIGHT="$_MYCELIUM_ROOT/hooks/preflight.sh"
  fi
  if [ -n "$PREFLIGHT" ]; then
    # Preflight's own lines stay off this hook's stdout (v0.322.3): a PreToolUse hook answers in
    # JSON or not at all, and a runtime that parses stdout must not be handed a sentence. It was
    # harmless while this branch only ran where CLAUDE_PLUGIN_ROOT is set; since 0.322.3 the gate
    # finds its own preflight on every runtime. What the gate needs from it is the stamp.
    bash "$PREFLIGHT" >/dev/null 2>&1 || {
      _gate_block_log "stale-stamp"
      echo '{"message": "Mycelium preflight required. Read corrections.md and run validation before code changes."}' >&2
      exit 2
    }
  fi
fi

# ============================================================
# CHECK 3: Corrections.md hash consistency
# ============================================================
if [ -f "$CORRECTIONS_FILE" ] && [ -f "$STAMP_FILE" ]; then
  if command -v md5 &>/dev/null; then
    CURRENT_HASH=$(md5 -q "$CORRECTIONS_FILE")
  elif command -v md5sum &>/dev/null; then
    CURRENT_HASH=$(md5sum "$CORRECTIONS_FILE" | cut -d' ' -f1)
  else
    CURRENT_HASH="unknown"
  fi

  STAMP_HASH=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["corrections_hash"])' "$STAMP_FILE" 2>/dev/null || echo "")

  if [ "$CURRENT_HASH" != "unknown" ] && [ -n "$STAMP_HASH" ] && [ "$CURRENT_HASH" != "$STAMP_HASH" ]; then
    _gate_block_log "corrections-hash"
    echo '{"message": "corrections.md changed since last preflight. Re-read corrections and re-run preflight."}' >&2
    rm -f "$STAMP_FILE"
    exit 2
  fi
fi

[ -n "$SCAN_NOTE" ] && printf '%s\n' "$SCAN_NOTE"
exit 0
