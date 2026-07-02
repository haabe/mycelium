#!/bin/bash
# Mycelium discovery gate (PreToolUse, Write only)
#
# Blocks scaffolding NEW source files in a project where discovery has never
# been engaged — no active diamond, no populated purpose.yml — and the user
# has not explicitly acknowledged skipping discovery.
#
# Provenance: the deliver-framed-opening routing gap. A confident "build me
# X" first message on an empty workspace led the agent to scaffold code with
# zero discovery behind it — observed in founder dogfood (2026-06-08/09) and
# mechanically reproduced by the roadmap auto-dogfood battery (2026-07-02:
# both runs of the bad-path scenario wrote source files to the turn cap).
# Router-discipline prose alone did not hold; this gate is the teeth.
#
# Scope is deliberately NARROW (the friction-wall risk is real):
#   - Fires ONLY on the Write tool (Edit/MultiEdit never blocked — brownfield
#     work on existing code is untouched).
#   - Fires ONLY when the target file does not exist yet (new-file scaffolds).
#   - Fires ONLY for source/infra-shaped files (extension + basename lists).
#   - Fires ONLY when discovery has never been engaged: no diamond entry in
#     active.yml AND no populated canvas/purpose.yml.
#   - Escape hatch: .claude/state/discovery-skip-ack — written AFTER the user
#     explicitly declines discovery (record the date + the user's own words).
#     One conversation per project, then the gate is silent forever.
#
# Exit 0 = allow, Exit 2 = block (stderr is shown to the agent).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

INPUT=$(cat)
TOOL_NAME=""
FILE_PATH=""
{ IFS= read -r -d '' TOOL_NAME; IFS= read -r -d '' FILE_PATH; } < <(
  printf '%s' "$INPUT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
ti = d.get("tool_input", {})
sys.stdout.write(d.get("tool_name", "") + "\0" + ti.get("file_path", ti.get("file", "")) + "\0")
' 2>/dev/null
) || true

# Only the Write tool scaffolds new files; Edit/MultiEdit require an existing
# file and are always brownfield-legitimate.
[ "$TOOL_NAME" = "Write" ] || exit 0
[ -n "$FILE_PATH" ] || exit 0

# Resolve relative paths against the project root so existence checks work.
case "$FILE_PATH" in
  /*) ;;
  *)  FILE_PATH="$PROJECT_DIR/$FILE_PATH" ;;
esac

# Never gate framework/project state or documentation.
case "$FILE_PATH" in
  *"/.claude/"*|*.md|*.txt) exit 0;;
esac

# Only new files — an existing target means brownfield work in flight.
[ -e "$FILE_PATH" ] && exit 0

# Source/infra-shaped? Basename allowlist first (covers extensionless infra
# and docker-compose.yml, which the extension list deliberately omits — *.yml
# is canvas/config territory), then source extensions.
BASENAME="${FILE_PATH##*/}"
GATED=0
case "$BASENAME" in
  Dockerfile*|docker-compose*|Makefile|requirements.txt|pyproject.toml|package.json|Cargo.toml|go.mod) GATED=1;;
esac
if [ "$GATED" = "0" ]; then
  case "$FILE_PATH" in
    *.py|*.js|*.ts|*.tsx|*.jsx|*.mjs|*.go|*.rs|*.java|*.rb|*.php|*.c|*.cc|*.cpp|*.h|*.hpp|*.cs|*.swift|*.kt|*.scala|*.sql|*.sh) GATED=1;;
  esac
fi
[ "$GATED" = "1" ] || exit 0

# Escape hatch: the user already declined discovery, on the record.
[ -f "$PROJECT_DIR/.claude/state/discovery-skip-ack" ] && exit 0

# Discovery engaged? Any diamond entry in active.yml, or a populated
# purpose.yml (>100 bytes distinguishes real content from an empty stub).
ACTIVE_FILE="$PROJECT_DIR/.claude/diamonds/active.yml"
PURPOSE_FILE="$PROJECT_DIR/.claude/canvas/purpose.yml"
if [ -f "$ACTIVE_FILE" ] && grep -qE '^[[:space:]]*-[[:space:]]*(id|scale):' "$ACTIVE_FILE" 2>/dev/null; then
  exit 0
fi
# >60 bytes: the auto-generated empty stub is ~44 bytes; any real one-line
# purpose statement clears 60 comfortably.
if [ -f "$PURPOSE_FILE" ] && [ "$(wc -c < "$PURPOSE_FILE" 2>/dev/null || echo 0)" -gt 60 ]; then
  exit 0
fi

cat >&2 <<EOF
Mycelium discovery gate: this project has no discovery state yet (no active
diamond, no populated purpose.yml), and you are about to scaffold a new
source file ($BASENAME). Building on an unexamined idea is the framework's
most consistently observed failure mode — do NOT silently proceed.

Instead:
1. Offer the user the ~10-minute discovery brief first: /mycelium:start
   (it captures what they want to change, for whom, and the riskiest
   assumption — THEN building starts on the same footing).
2. If the user EXPLICITLY declines and wants to build without discovery,
   record that choice: write .claude/state/discovery-skip-ack containing
   the date and the user's own words, then retry. The gate stays silent
   for this project afterwards.

Do not write the ack file on your own judgment — it records the USER's
decision, not yours.
EOF
exit 2
