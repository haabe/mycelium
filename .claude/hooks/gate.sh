#!/bin/bash
# Mycelium PreToolUse gate
# Lightweight check before code changes. Exit 0 = allow, Exit 2 = block.
#
# Adapted from n-trax's gate.sh pattern.
# Gates source code edits behind preflight validation.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STAMP_FILE="/tmp/mycelium-preflight-stamp"
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Parse tool input to get file path
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json;d=json.load(sys.stdin);ti=d.get("tool_input",{});print(ti.get("file_path",ti.get("file","")))' 2>/dev/null || echo "")

# Always allow .claude/ edits (config/harness/canvas changes)
case "$FILE_PATH" in *".claude/"*) exit 0;; esac

# Only gate source code paths (src/, scripts/, tests/, lib/, app/)
case "$FILE_PATH" in
  *"/src/"*|*"/scripts/"*|*"/tests/"*|*"/test/"*|*"/lib/"*|*"/app/"*|*"/pages/"*|*"/components/"*) ;;
  *) exit 0;;
esac

# Check if preflight stamp exists and is fresh (4 hour expiry)
NEEDS_RENEWAL=0
if [ ! -f "$STAMP_FILE" ]; then
  NEEDS_RENEWAL=1
else
  # Check age (macOS and Linux compatible)
  STAMP_MOD=$(stat -f %m "$STAMP_FILE" 2>/dev/null || stat -c %Y "$STAMP_FILE" 2>/dev/null || echo 0)
  STAMP_AGE=$(( $(date +%s) - STAMP_MOD ))
  if [ "$STAMP_AGE" -gt 14400 ]; then
    NEEDS_RENEWAL=1
  fi
fi

# Auto-renew stamp if needed
if [ "$NEEDS_RENEWAL" -eq 1 ]; then
  bash "$PROJECT_DIR/.claude/hooks/preflight.sh" 2>/dev/null || {
    echo '{"message": "Mycelium preflight required. Read corrections.md and run validation before code changes."}' >&2
    exit 2
  }
fi

# Check if corrections.md has changed since last preflight
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
    echo '{"message": "corrections.md changed since last preflight. Re-read corrections and re-run preflight."}' >&2
    rm -f "$STAMP_FILE"
    exit 2
  fi
fi

exit 0
