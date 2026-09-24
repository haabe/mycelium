#!/bin/bash
# Mycelium PostToolUse: check a written canvas or diamonds file against its schema (v0.250.0).
#
# A reminder to run the validator is not the validator. The E2E happy path wrote an invalid
# privacy-assessment.yml after the post-write nudge had said "validate with validate_canvas.py";
# nothing named the error until the end of the turn. This runs the schema check on the file just
# written and returns the exact errors to the agent. Logic lives in scripts/canvas_write_check.py.
#
# Never blocks a write, never exits non-zero: the file is already on disk, and the job here is to
# say what is wrong with it. Without PyYAML/jsonschema it says once per session that it could not
# run. Each time it speaks it records one row (outcome only, no file contents) for the retirement
# instrument.

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
OUT=$(python3 "$PLUGIN_ROOT/scripts/canvas_write_check.py" 2>/dev/null)
if [ -n "$OUT" ]; then
  printf '%s\n' "$OUT"
  . "$PLUGIN_ROOT/scripts/_hook_fire_log.sh" 2>/dev/null || true
  case "$OUT" in
    *'"decision"'*) OUTCOME="fired" ;;
    *) OUTCOME="skipped" ;;
  esac
  mycelium_log_fire ".claude/state/canvas-schema-check-fires.jsonl" "$OUTCOME" 2>/dev/null || true
fi
exit 0
