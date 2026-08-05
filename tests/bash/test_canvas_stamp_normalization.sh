#!/usr/bin/env bash
# Regression tests for the v0.89.0 canvas-stamp normalization.
#
# TWO DEFECTS, FOUND BY ASKING WHAT ACTUALLY READS THESE FIELDS.
#
# 1. `last_updated` DUPLICATED GIT. It recorded when a file last changed — which
#    git already records authoritatively — so the copy could only drift from the
#    original, silently. On the dogfood repo 10 of 26 canvases carried a stale
#    one. No code anywhere in the plugin read it: five schema declarations, three
#    prose files, and the scaffold that wrote it. The fix is removal, not a
#    freshness check, because policing a duplicate institutionalises the defect.
#
# 2. canvas-health CONTRADICTED ITSELF ON STALENESS. Step 3 flagged
#    `_meta.last_validated` older than a flat 30 days; step 7 applied the
#    differentiated horizons in engine/evidence-decay.md. The flat 30 was the
#    only staleness number in the skill grounded in nothing, and it flagged 20 of
#    25 dogfood canvases — including a strategic file validated 46 days earlier
#    against a 180-day horizon. A check firing on 80% of a corpus trains its
#    reader to skip it.
#
# `_meta.last_validated` SURVIVES both changes on purpose: it records when a
# human confirmed the content, which git cannot know.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$REPO_ROOT/plugins/mycelium"
source "$(dirname "${BASH_SOURCE[0]}")/_assert.sh"

echo "canvas stamp normalization"
echo "======================================================"

# --- 1. last_updated is gone from canvas + diamond top-level schemas ---------
for s in gist north-star opportunities scenarios; do
  f="$PLUGIN/schemas/canvas/$s.schema.json"
  got="$(python3 -c "import json;print('last_updated' in json.load(open('$f')).get('properties',{}))")"
  assert_eq "$got" "False" "$s.schema.json no longer declares top-level last_updated"
done

got="$(python3 -c "import json;print('last_updated' in json.load(open('$PLUGIN/schemas/diamonds/active.schema.json')).get('properties',{}))")"
assert_eq "$got" "False" "active.schema.json no longer declares top-level last_updated"

got="$(python3 -c "import json;print('_meta' in json.load(open('$PLUGIN/schemas/diamonds/active.schema.json')).get('properties',{}))")"
assert_eq "$got" "True" "active.schema.json declares _meta instead"

# The PER-DIAMOND timestamp is a different field and must survive — it tracks a
# diamond's own state change, not the file's currency.
got="$(python3 -c "
import json;d=json.load(open('$PLUGIN/schemas/diamonds/active.schema.json'))
defs=d.get('\$defs',{}) or d.get('definitions',{})
print('last_updated' in json.dumps(defs.get('diamond',{})))")"
assert_eq "$got" "True" "per-diamond \$defs.diamond.last_updated is untouched"

# --- 2. Removal must not break existing canvases -----------------------------
# Every touched schema must keep additionalProperties permissive, or a user's
# canvas that still carries last_updated would fail validation on upgrade.
for f in "$PLUGIN"/schemas/canvas/{gist,north-star,opportunities,scenarios}.schema.json \
         "$PLUGIN"/schemas/diamonds/active.schema.json; do
  got="$(python3 -c "import json;print(json.load(open('$f')).get('additionalProperties', True) is not False)")"
  assert_eq "$got" "True" "$(basename "$f") stays permissive (upgrade-safe)"
done

# --- 3. The scaffold writes the new field, not the old one -------------------
setup="$PLUGIN/skills/setup/SKILL.md"
grep -q "^last_updated: null" "$setup" \
  && assert_eq "found" "absent" "setup scaffold must not write last_updated" \
  || assert_eq "absent" "absent" "setup scaffold no longer writes last_updated"
assert_contains "$(cat "$setup")" "last_validated: null" "setup scaffold writes _meta.last_validated"

# --- 4. The render spec has no fallback, and forbids a machine substitute ----
rc="$PLUGIN/engine/render-conventions.md"
grep -q 'Top-level `last_updated:` field as fallback' "$rc" \
  && assert_eq "found" "absent" "render spec must not keep the last_updated fallback" \
  || assert_eq "absent" "absent" "render spec dropped the last_updated fallback"
assert_contains "$(cat "$rc")" "never substitute" "render spec forbids substituting mtime/wall-clock for a missing stamp"

# --- 5. The staleness rule is category-based, not flat 30 -------------------
ch="$PLUGIN/skills/canvas-health/SKILL.md"
grep -q "Flag \`last_validated\` older than 30 days" "$ch" \
  && assert_eq "found" "absent" "canvas-health must not keep the flat 30-day rule" \
  || assert_eq "absent" "absent" "canvas-health dropped the flat 30-day rule"
assert_contains "$(cat "$ch")" "evidence-decay.md" "canvas-health step 3 cites the decay table"

ed="$PLUGIN/engine/evidence-decay.md"
assert_contains "$(cat "$ed")" "Which threshold applies to which canvas file" "decay doc carries the canvas->category mapping"
assert_contains "$(cat "$ed")" "purpose.yml" "mapping names the strategic canvases"
# The fallback for an unlisted file must be the median, not the strictest value:
# an unclassified file is unclassified, not urgent.
assert_contains "$(cat "$ed")" "falls back to **90 days**" "unlisted files fall back to 90d, not 30d"

echo "------------------------------------------------------"
report
