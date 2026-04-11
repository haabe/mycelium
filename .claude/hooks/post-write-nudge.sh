#!/bin/bash
# Mycelium PostToolUse nudge
# Layer 2: Context-aware reminders after code changes.
# Fires on every Write/Edit/MultiEdit success.
#
# Nudges by file type:
# - Canvas files (.claude/canvas/*.yml) -> suggest the relevant skill (v0.10)
# - Research synthesis files (.claude/memory/*research*, *synthesis*, *brief*)
#     -> suggest /devils-advocate (dogfood G3, v0.10)
# - UI files -> accessibility + error states
# - API/route files -> input validation
# - All source -> validation suite reminder

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json;d=json.load(sys.stdin);ti=d.get("tool_input",{});print(ti.get("file_path",ti.get("file","")))' 2>/dev/null || echo "")

# Normalize path: ensure leading / so patterns match consistently
case "$FILE_PATH" in
  /*) ;; # already absolute
  *)  FILE_PATH="/$FILE_PATH" ;;
esac

# Build context-aware nudge
NUDGE=""

# ============================================================
# v0.10: Canvas file skill auto-suggest
# ============================================================
# When the agent edits a canvas file, suggest the skill that maps to it.
# Addresses dogfood T1 (skill bloat — only 2 of 35 skills used).
# Surfaces skills at the point of need, not just at SessionStart.
case "$FILE_PATH" in
  *".claude/canvas/opportunities.yml"|*".claude/canvas/opportunities.yml"*)
    NUDGE="Opportunity Solution Tree edited. Consider /ost-builder for the structured OST discipline (Torres). Remember: opportunities come from research, never from brainstorming."
    ;;
  *".claude/canvas/user-needs.yml"*)
    NUDGE="User needs canvas edited. Consider /user-needs-map for Allen's methodology (needs independent of solutions). Every need entry needs provenance (evidence_type, sources) — see schema."
    ;;
  *".claude/canvas/landscape.yml"*)
    NUDGE="Wardley map edited. Consider /wardley-map for the structured mapping workflow. Components need provenance — strategic positioning carries weight."
    ;;
  *".claude/canvas/threat-model.yml"*)
    NUDGE="Threat model edited. Consider /threat-model for STRIDE walkthrough (OWASP). Each threat entry needs provenance — distinguish hypothetical from observed."
    ;;
  *".claude/canvas/jobs-to-be-done.yml"*)
    NUDGE="JTBD canvas edited. Consider /jtbd-map — functional, emotional, and social dimensions all need interview backing (Christensen). Don't map jobs from assumptions."
    ;;
  *".claude/canvas/gist.yml"*)
    NUDGE="GIST canvas edited. Consider /gist-plan for the goals/ideas/steps/tasks hierarchy (Gilad). Tag each step with MoSCoW priority."
    ;;
  *".claude/canvas/services.yml"*)
    NUDGE="Services canvas edited. Consider /service-check for Downe's 15 Good Services principles — required REVIEW gate for user-facing work."
    ;;
  *".claude/canvas/go-to-market.yml"*)
    NUDGE="Go-to-market canvas edited. Consider /launch-tier for Lauchengco's Loved framework. Buyer personas and competitive intelligence need provenance."
    ;;
  *".claude/canvas/dora-metrics.yml"*)
    NUDGE="DORA metrics canvas edited. Consider /dora-check for Forsgren's four + APEX metrics. Remember Loop 3 cadence: per delivery cycle."
    ;;
  *".claude/canvas/content-metrics.yml"*)
    NUDGE="Content metrics canvas edited. Consider /dora-check (auto-routes to content assessment). Track publication cadence, revision rate, engagement."
    ;;
  *".claude/canvas/ai-tool-metrics.yml"*)
    NUDGE="AI tool metrics canvas edited. Consider /dora-check (auto-routes to AI assessment). Track eval scores, safety, bias assessment."
    ;;
  *".claude/canvas/service-metrics.yml"*)
    NUDGE="Service metrics canvas edited. Consider /dora-check (auto-routes to service assessment). Track client throughput, satisfaction, repeatability."
    ;;
  *".claude/canvas/human-tasks.yml"*)
    NUDGE="Human tasks canvas edited. Pending tasks? Run /log-evidence when offline work is complete."
    ;;
  *".claude/canvas/bvssh-health.yml"*)
    NUDGE="BVSSH canvas edited. Consider /bvssh-check for the five dimensions assessment (Smart). CALMS culture section supplements DORA."
    ;;
  *".claude/canvas/team-shape.yml"*)
    NUDGE="Team shape canvas edited. Consider /team-shape for Team Topologies assessment (Skelton). Check cognitive load and interaction modes."
    ;;
  *".claude/canvas/privacy-assessment.yml"*)
    NUDGE="Privacy assessment edited. Consider /privacy-check for Privacy by Design (Cavoukian) + GDPR alignment. Required REVIEW gate for data-handling products."
    ;;
  *".claude/canvas/trust-signals.yml"*)
    NUDGE="Trust signals canvas edited. Consider /launch-tier (which covers trust architecture at L5)."
    ;;
  *".claude/canvas/north-star.yml"*)
    NUDGE="North star canvas edited. This is a strategic update — should a decision log entry capture why the metric or targets changed?"
    ;;
  *".claude/canvas/purpose.yml"*)
    NUDGE="Purpose canvas edited. Changes to L0 purpose are rare — verify this isn't a subtle pivot that should trigger /diamond-progress pivot instead."
    ;;
  *".claude/canvas/bounded-contexts.yml"*)
    NUDGE="Bounded contexts canvas edited (DDD). Consider /team-shape — Conway's Law says team boundaries should align with context boundaries."
    ;;
  *".claude/canvas/value-stream.yml"*)
    NUDGE="Value stream canvas edited. Consider /dora-check — VSM is most useful when APEX or DORA metrics indicate a bottleneck shift."
    ;;
esac

# v0.11.1: Canvas schema validation nudge (dogfood G5)
# Remind to validate canvas files against JSON schemas after edits.
if [ -n "$NUDGE" ]; then
  case "$FILE_PATH" in
    *".claude/canvas/"*.yml)
      BASENAME=$(basename "$FILE_PATH" .yml)
      SCHEMA_FILE="$PROJECT_DIR/.claude/schemas/canvas/${BASENAME}.schema.json"
      if [ -f "$SCHEMA_FILE" ]; then
        NUDGE="${NUDGE} Schema exists at schemas/canvas/${BASENAME}.schema.json — validate with validate_canvas.py."
      fi
      ;;
  esac
fi

# ============================================================
# v0.10: Research synthesis nudge (dogfood G3)
# ============================================================
# When the agent writes a research brief / synthesis / summary to memory,
# prompt for /devils-advocate on the synthesis itself.
# Addresses dogfood finding G3: "Synthesis-bias-check isn't a gate."
if [ -z "$NUDGE" ]; then
  case "$FILE_PATH" in
    *".claude/memory/"*research*|*".claude/memory/"*synthesis*|*".claude/memory/"*brief*|*".claude/memory/"*interview*)
      NUDGE="Research/synthesis memory file written. Before treating recommendations as actionable, run /devils-advocate on the SYNTHESIS (not just the original assumptions). Synthesis is exactly where agents over-anchor on source material framing. (Dogfood G3)"
      ;;
  esac
fi

# ============================================================
# Skip other .claude/ files (framework internals, no nudge needed)
# ============================================================
if [ -z "$NUDGE" ]; then
  case "$FILE_PATH" in
    *".claude/"*)
      exit 0
      ;;
  esac
fi

# ============================================================
# Existing source code detection (unchanged from v0.8.x)
# ============================================================

# Detect UI files
case "$FILE_PATH" in
  *.tsx|*.jsx|*.vue|*.svelte|*.html|*.css|*.scss)
    NUDGE="${NUDGE:+$NUDGE }UI code changed. Remember: semantic HTML, ARIA labels, keyboard navigation, color contrast (WCAG 2.1 AA). Design error/empty/loading states (Downe P10). Run /a11y-check before completing."
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
