#!/bin/bash
# Mycelium preflight validation
# Creates a stamp file that the gate.sh checks before allowing code edits.
# This ensures corrections.md has been read and basic system health verified.

# Resolve the project dir. Prefer $CLAUDE_PROJECT_DIR (the Claude Code CLI sets
# it), but fall back to walking up from $PWD to find a .claude/ dir when it is
# unset. Some runtimes (e.g. Claude Cowork) do not provision CLAUDE_PROJECT_DIR,
# which made the bare ".-fallback resolve against the wrong directory and report
# "Memory not yet initialized" on every turn of an already-initialized project
# (Cowork dogfood F1, 2026-06-19). When the env var IS set we trust it verbatim,
# so CLI behaviour is unchanged.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  _d="$PWD"
  while [ -n "$_d" ] && [ "$_d" != "/" ]; do
    if [ -d "$_d/.claude" ]; then PROJECT_DIR="$_d"; break; fi
    _d="$(dirname "$_d")"
  done
  PROJECT_DIR="${PROJECT_DIR:-.}"
fi
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Stamp path: per-user + per-project under $TMPDIR — must match gate.sh exactly.
# See gate.sh for rationale (world-predictable shared /tmp path was the bug).
_stamp_uid=$(id -u 2>/dev/null || echo 0)
_stamp_phash=$(printf '%s' "$PROJECT_DIR" | { md5 2>/dev/null || md5sum 2>/dev/null; } | tr -cd '0-9a-f' | cut -c1-12)
STAMP_FILE="${TMPDIR:-/tmp}/mycelium-preflight-stamp-${_stamp_uid}-${_stamp_phash:-0}"

# Calculate corrections hash
CORRECTIONS_HASH="none"
if [ -f "$CORRECTIONS_FILE" ]; then
  if command -v md5 &>/dev/null; then
    CORRECTIONS_HASH=$(md5 -q "$CORRECTIONS_FILE")
  elif command -v md5sum &>/dev/null; then
    CORRECTIONS_HASH=$(md5sum "$CORRECTIONS_FILE" | cut -d' ' -f1)
  fi
fi

# Count corrections
#
# THIS NUMBER IS PRINTED INTO EVERY SESSION'S CONTEXT, before any work starts,
# which makes it the most-read quantity the framework produces and the one it
# was least careful about. Until 2026-08-09 the pattern here was `^### `, and it
# was wrong in both directions at once: it missed `##` and `####` entries, it
# missed the entire bullet form `- **Title (DATE, class)**:` that most recent
# entries use, and it counted section headings like `### Prevention rule` as
# corrections. Measured on the dogfood repo that day it said 100 against a real
# corpus of 141, and the gap had widened from 30 the day before — it degrades
# with use, because the invisible form is the one people write now.
#
# THE PATTERN BELOW MUST STAY EQUIVALENT TO `ENTRY_RE` in
# `scripts/_corrections_lib.py`. Bash cannot import it, so the equivalence is
# held by a test rather than by a shared symbol:
# `tests/python/test_correction_count_agreement.py` runs THIS hook against
# `tests/fixtures/corrections/mixed.md` and compares the banner it prints to the
# library's count. Change one without the other and that test fails.
CORRECTIONS_COUNT=0
if [ -f "$CORRECTIONS_FILE" ]; then
  # grep -c prints "0" AND exits 1 on no matches, so `|| echo 0` would append a
  # second "0" → "0\n0" → "integer expected" in the -eq test below. Use `|| true`
  # (grep already prints the count) and normalize to a bare integer.
  CORRECTIONS_COUNT=$(grep -cE '^#{2,4}[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}|^-[[:space:]]+\*\*[^*]*\([0-9]{4}-[0-9]{2}-[0-9]{2}[a-z]?[,)][^*]*\*\*' "$CORRECTIONS_FILE" 2>/dev/null || true)
  CORRECTIONS_COUNT=${CORRECTIONS_COUNT//[^0-9]/}
  CORRECTIONS_COUNT=${CORRECTIONS_COUNT:-0}
fi

# Write stamp (0600 — only the owner can read/clobber it)
rm -f "$STAMP_FILE"
( umask 077; cat > "$STAMP_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "corrections_hash": "$CORRECTIONS_HASH",
  "corrections_count": $CORRECTIONS_COUNT,
  "project_dir": "$PROJECT_DIR"
}
EOF
)

# Disambiguate "memory not yet initialized" from "memory has zero entries"
# from "memory has N entries" — bare "0 corrections" reads as a possible
# counting failure to first-run users (per opp-001).
if [ ! -f "$CORRECTIONS_FILE" ]; then
  echo "Mycelium preflight complete. Memory not yet initialized — run /mycelium:setup if this is a fresh install."
elif [ "$CORRECTIONS_COUNT" -eq 0 ]; then
  echo "Mycelium preflight complete. Memory is empty (no corrections logged yet)."
else
  echo "Mycelium preflight complete. $CORRECTIONS_COUNT corrections in memory."
fi
exit 0
