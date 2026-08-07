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

# SCOPE: this gate is about THIS PROJECT, so the target must be INSIDE it.
#
# Everything below reads discovery state from $PROJECT_DIR — active.yml, purpose.yml,
# the skip-ack. Without a containment test the TRIGGER is session-scoped while the
# STATE is project-scoped, so a write to a file the project does not own is judged by
# a different project's discovery. Found 2026-08-07: a Cowork session rooted in a
# Mycelium project blocked a write to ~/Cowork Workspace/personal-os/evals/*.sh, which
# has no relationship to any diamond, purpose or canvas. Reproduced with both arms.
#
# This is the other half of the 2026-07-26 fix below. That one made the EXEMPTION
# project-relative and left the trigger session-scoped; this closes the asymmetry.
#
# The skip-ack is NOT the remedy for that case and must not be used as one: it lives
# at $PROJECT_DIR/.claude/state/ and is permanent, so acking an out-of-project write
# would silence the gate forever for a project that never came up, and would record a
# decision the user was never asked to make.
#
# Resolution is physical (pwd -P) on both sides so symlinks and ".." cannot walk out
# of the root and still compare as inside. The target does not exist yet by
# definition, so we resolve its nearest EXISTING ancestor — Write may create parents.
_nearest_existing_dir() {
  local d="$1"
  while [ -n "$d" ] && [ "$d" != "/" ] && [ ! -d "$d" ]; do
    d="$(dirname "$d")"
  done
  printf '%s' "$d"
}
_real_dir() { (cd "$1" 2>/dev/null && pwd -P); }

PROJECT_REAL="$(_real_dir "$PROJECT_DIR")"
TARGET_REAL="$(_real_dir "$(_nearest_existing_dir "$(dirname "$FILE_PATH")")")"

# Unresolvable project root: allow. The gate cannot read its own state either, so
# blocking would mean judging a file against discovery state it could not load. This
# errs toward allow, consistent with the stated narrow scope and the friction-wall
# risk — a missed scaffold is recoverable, a wall on an unrelated file is not.
[ -n "$PROJECT_REAL" ] || exit 0
[ -n "$TARGET_REAL" ] || exit 0
case "$TARGET_REAL" in
  "$PROJECT_REAL") ;;
  "$PROJECT_REAL"/*) ;;
  *) exit 0;;
esac

# Never gate framework/project state or documentation.
#
# The .claude/ test is deliberately PROJECT-RELATIVE. Matching `*/.claude/*`
# against the absolute path exempted any project that merely lives underneath a
# `.claude` ancestor directory — e.g. a workspace at ~/.claude/jobs/<id>/work —
# so every source write in such a tree escaped the gate. Found 2026-07-26 by
# tripping it with a probe workspace under ~/.claude/; unlikely for real user
# projects, but the exemption was wider than its intent by construction.
REL_PATH="${FILE_PATH#"$PROJECT_DIR"/}"
case "$REL_PATH" in
  .claude/*|*/.claude/*) exit 0;;
esac
case "$FILE_PATH" in
  *.md|*.txt) exit 0;;
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
