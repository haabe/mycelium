#!/bin/bash
# Mycelium PostToolUse nudge
# Layer 2: Context-aware reminders after code changes.
# Fires on every Write/Edit/MultiEdit success.
#
# Returns additionalContext tailored to the type of file modified:
# - UI files -> accessibility + error states
# - API/route files -> input validation
# - All source -> validation suite reminder

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json;d=json.load(sys.stdin);ti=d.get("tool_input",{});print(ti.get("file_path",ti.get("file","")))' 2>/dev/null || echo "")

# Skip .claude/ files
case "$FILE_PATH" in *".claude/"*) exit 0;; esac

# Build context-aware nudge
NUDGE=""

# Detect UI files
case "$FILE_PATH" in
  *.tsx|*.jsx|*.vue|*.svelte|*.html|*.css|*.scss)
    NUDGE="UI code changed. Remember: semantic HTML, ARIA labels, keyboard navigation, color contrast (WCAG 2.1 AA). Design error/empty/loading states (Downe P10). Run /a11y-check before completing."
    ;;
esac

# Detect API/route/server files
case "$FILE_PATH" in
  */api/*|*/routes/*|*/server/*|*/controllers/*|*/handlers/*|*middleware*)
    NUDGE="${NUDGE:+$NUDGE }API/server code changed. Verify: input validation on ALL external inputs, parameterized queries, auth checks, no secrets in response/logs (OWASP). Run /security-review before completing."
    ;;
esac

# Detect test files (positive reinforcement, no nagging)
case "$FILE_PATH" in
  *.test.*|*.spec.*|*__tests__/*)
    NUDGE="Tests updated. Good."
    ;;
esac

# Default nudge for any source code
if [ -z "$NUDGE" ]; then
  case "$FILE_PATH" in
    */src/*|*/lib/*|*/app/*|*/scripts/*|*/server/*)
      NUDGE="Code changed. Run validation suite before committing."
      ;;
  esac
fi

# Return as additionalContext if we have something
if [ -n "$NUDGE" ]; then
  python3 -c "
import json, sys
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PostToolUse',
        'additionalContext': sys.argv[1]
    }
}))
" "$NUDGE"
fi

exit 0
