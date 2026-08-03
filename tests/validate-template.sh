#!/usr/bin/env bash
# Mycelium Template Structural Integrity Validation
#
# Validates that the boilerplate's interconnected files are internally consistent.
# Run before committing changes to the Mycelium template.
#
# Usage: bash tests/validate-template.sh
# Exit code: 0 = all checks pass, 1 = failures detected
#
# Compatible with macOS (BSD) and Linux (GNU) grep/sed.

set -euo pipefail

# Navigate to repo root (script may be called from anywhere).
# Validator lives at <repo>/tests/validate-template.sh post-2026-05-09 legacy
# cleanup; REPO_ROOT is one level up. Previously two levels up (legacy
# location was <repo>/.claude/tests/validate-template.sh).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- Skills tree detection (plugin form vs legacy) ---
# As of v0.20.x, skills live at plugins/mycelium/skills/ (plugin canonical).
# Legacy .claude/skills/ is preserved during transition until the canonical
# 0.20.0 bump on merge to main. Validator targets the canonical tree first;
# if both exist it also runs a parity check (see Check 27).
PLUGIN_SKILLS="plugins/mycelium/skills"
LEGACY_SKILLS=".claude/skills"  # legacy form removed from upstream 2026-05-09; kept as docstring + parity fallback
if [ -d "$PLUGIN_SKILLS" ]; then
    SKILLS_DIR="$PLUGIN_SKILLS"
    SKILLS_FORM="plugin"
elif [ -d "$LEGACY_SKILLS" ]; then
    SKILLS_DIR="$LEGACY_SKILLS"
    SKILLS_FORM="legacy"
else
    echo "FATAL: no skills directory found (looked in $PLUGIN_SKILLS and $LEGACY_SKILLS)" >&2
    exit 2
fi

# --- Counters and helpers ---

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

section() { echo ""; echo "--- $1 ---"; }

# Portable number extraction: extract first number from a matching line
# Usage: extract_number "pattern" "file"
# Returns the first number found on the first matching line
extract_number() {
    local pattern="$1"
    local file="$2"
    grep "$pattern" "$file" 2>/dev/null | head -1 | sed 's/[^0-9]*//' | sed 's/[^0-9].*//' || echo "0"
}

# --- YAML parsing detection ---

YAML_CMD=""
detect_yaml_parser() {
    if python3 -c "import yaml" 2>/dev/null; then
        YAML_CMD="python3"
    elif ruby -ryaml -e "true" 2>/dev/null; then
        YAML_CMD="ruby"
    else
        YAML_CMD=""
    fi
}

validate_yaml_file() {
    local file="$1"
    if [ "$YAML_CMD" = "python3" ]; then
        python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null
    elif [ "$YAML_CMD" = "ruby" ]; then
        ruby -ryaml -e "YAML.safe_load(File.read('$file'))" 2>/dev/null
    fi
}

# ============================================================
# CHECK 1: All canvas YAML files parse correctly
# ============================================================
check_yaml_parsing() {
    section "Check 1: YAML parsing"
    detect_yaml_parser

    if [ -z "$YAML_CMD" ]; then
        warn "No YAML parser available (need python3+pyyaml or ruby). Skipping YAML validation."
        return
    fi

    local yaml_errors=0
    for file in .claude/canvas/*.yml; do
        if ! validate_yaml_file "$file"; then
            fail "YAML parse error: $file"
            yaml_errors=$((yaml_errors + 1))
        fi
    done

    if [ "$yaml_errors" -eq 0 ]; then
        pass "All canvas YAML files parse correctly ($YAML_CMD)"
    fi
}

# ============================================================
# CHECK 2: Canvas file count in README body matches disk
# (Deprecated 2026-05-08 docs split: README no longer enumerates canvas files;
#  canonical mapping is canvas-update SKILL.md, validated by Check 5.)
# ============================================================
check_canvas_count_readme_body() {
    section "Check 2: Canvas count (README body)"
    pass "Deprecated by 2026-05-08 docs split; canvas-list authority is canvas-update SKILL.md (Check 5)"
}

# ============================================================
# CHECK 3: Canvas file count in README directory structure
# (Deprecated 2026-05-08: README no longer carries a directory structure section.)
# ============================================================
check_canvas_count_readme_dir() {
    section "Check 3: Canvas count (README directory structure)"
    pass "Deprecated by 2026-05-08 docs split; canvas-list authority is canvas-update SKILL.md (Check 5)"
}

# ============================================================
# CHECK 4: Every canvas file on disk appears in README table
# (Deprecated 2026-05-08: README no longer enumerates canvas files; covered by Check 5.)
# ============================================================
check_canvas_in_readme_table() {
    section "Check 4: Canvas files in README table"
    pass "Deprecated by 2026-05-08 docs split; canvas-list authority is canvas-update SKILL.md (Check 5)"
}

# ============================================================
# CHECK 5: Every canvas file appears in canvas-update mapping
# ============================================================
check_canvas_in_update_mapping() {
    section "Check 5: Canvas files in canvas-update SKILL.md mapping"

    local mapping_file="$SKILLS_DIR/canvas-update/SKILL.md"
    if [ ! -f "$mapping_file" ]; then
        fail "canvas-update SKILL.md not found"
        return
    fi

    local missing=0
    for file in .claude/canvas/*.yml; do
        local basename
        basename=$(basename "$file")
        if ! grep -q "$basename" "$mapping_file"; then
            warn "Canvas file $basename not in canvas-update mapping (agent may not know to update it)"
            missing=$((missing + 1))
        fi
    done

    if [ "$missing" -eq 0 ]; then
        pass "All canvas files appear in canvas-update mapping"
    fi
}

# ============================================================
# CHECK 6: Skill count in docs/skills/README.md matches directories on disk
# (As of 2026-05-08 docs split: skill index moved from README to docs/skills/README.md.
#  Stub state — page contains "is forthcoming" — passes informational; Phase 2 fills.)
# ============================================================
check_skill_count_readme() {
    section "Check 6: Skill count (docs/skills/README.md)"

    local disk_count
    disk_count=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    local skills_doc="docs/skills/README.md"

    if [ ! -f "$skills_doc" ]; then
        fail "$skills_doc not found"
        return
    fi

    if grep -q "is forthcoming" "$skills_doc"; then
        pass "$skills_doc is a Phase 1 stub; Phase 2 will write the $disk_count-skill index"
        return
    fi

    # Match: "(N skills)" or "all N skills" or "N-skill index" or "the N skills"
    local doc_count
    doc_count=$(grep -oE '(\(|all |the )[0-9]+(-| )?skill' "$skills_doc" | head -1 | grep -oE '[0-9]+' || echo "0")

    if [ -z "$doc_count" ] || [ "$doc_count" = "0" ]; then
        fail "Could not find skill count in $skills_doc"
    elif [ "$doc_count" -eq "$disk_count" ]; then
        pass "$skills_doc skill count ($doc_count) matches disk ($disk_count)"
    else
        fail "$skills_doc says $doc_count skills, but $disk_count directories exist on disk"
    fi
}

# ============================================================
# CHECK 6b: Skill count in docs/skills/by-category.md matches directories on disk
# (Added v0.40.4: by-category.md drifted to "49 skills" while README templated "54".
#  Same eval as Check 6 because by-category is the alternate index — same scope, same drift risk.
#  sync_derived.py's SKILL_COUNT_FILES now templates this page, so going forward both pages
#  are kept in sync mechanically; this check is the validator-side belt to that script's suspenders.)
# ============================================================
check_skill_count_by_category() {
    section "Check 6b: Skill count (docs/skills/by-category.md)"

    local disk_count
    disk_count=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    local skills_doc="docs/skills/by-category.md"

    if [ ! -f "$skills_doc" ]; then
        fail "$skills_doc not found"
        return
    fi

    if grep -q "is forthcoming" "$skills_doc"; then
        pass "$skills_doc is a Phase 1 stub; Phase 2 will write the $disk_count-skill index"
        return
    fi

    # Match: "(N skills)" or "all N skills" or "N-skill index" or "the N skills" or "Same N skills" or "of the same N skills"
    local doc_count
    doc_count=$(grep -oE '(\(|all |the |Same |of the same )[0-9]+(-| )?skill' "$skills_doc" | head -1 | grep -oE '[0-9]+' || echo "0")

    if [ -z "$doc_count" ] || [ "$doc_count" = "0" ]; then
        fail "Could not find skill count in $skills_doc"
    elif [ "$doc_count" -eq "$disk_count" ]; then
        pass "$skills_doc skill count ($doc_count) matches disk ($disk_count)"
    else
        fail "$skills_doc says $doc_count skills, but $disk_count directories exist on disk"
    fi
}

# ============================================================
# CHECK 7: Skill count in CLAUDE.md matches directories on disk
# ============================================================
check_skill_count_claude() {
    section "Check 7: Skill count (CLAUDE.md)"

    local disk_count
    disk_count=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

    # Match: "All 38 skills are auto-discovered" (v0.11.0+) or "All 38 skills:" (pre-v0.11.0)
    local claude_count
    claude_count=$(grep -E "All [0-9]+ skills" CLAUDE.md | head -1 | sed 's/.*All //' | sed 's/ skills.*//' || echo "0")

    if [ -z "$claude_count" ] || [ "$claude_count" = "0" ]; then
        fail "Could not find skill count in CLAUDE.md"
    elif [ "$claude_count" -eq "$disk_count" ]; then
        pass "CLAUDE.md skill count ($claude_count) matches disk ($disk_count)"
    else
        fail "CLAUDE.md says $claude_count skills, but $disk_count directories exist on disk"
    fi
}

# ============================================================
# CHECK 8: Every skill directory has valid SKILL.md frontmatter
# ============================================================
check_skill_frontmatter() {
    section "Check 8: Skill SKILL.md frontmatter"

    local issues=0
    for dir in "$SKILLS_DIR"/*/; do
        local skill_name
        skill_name=$(basename "$dir")
        local skill_file="$dir/SKILL.md"

        if [ ! -f "$skill_file" ]; then
            fail "Skill directory $skill_name has no SKILL.md"
            issues=$((issues + 1))
            continue
        fi

        if ! head -20 "$skill_file" | grep -q "^name:"; then
            fail "Skill $skill_name SKILL.md missing 'name:' in frontmatter"
            issues=$((issues + 1))
        fi

        if ! head -20 "$skill_file" | grep -q "^description:"; then
            fail "Skill $skill_name SKILL.md missing 'description:' in frontmatter"
            issues=$((issues + 1))
        fi
    done

    if [ "$issues" -eq 0 ]; then
        pass "All skill directories have valid SKILL.md frontmatter"
    fi
}

# ============================================================
# CHECK 9: Skills are discoverable (auto-discovery or listed)
# ============================================================
check_skills_in_claude_md() {
    section "Check 9: Skills discoverable from CLAUDE.md"

    # v0.11.0+: skills are auto-discovered from SKILL.md frontmatter.
    # CLAUDE.md declares this with "auto-discovered". Path reference accepts
    # either legacy (.claude/skills/) or plugin (plugins/mycelium/skills/) form
    # during the v0.20.x transition.
    if grep -q "auto-discovered" CLAUDE.md; then
        if grep -qE "\.claude/skills/|plugins/mycelium/skills/" CLAUDE.md; then
            pass "CLAUDE.md declares skills as auto-discovered (form: $SKILLS_FORM)"
        else
            fail "CLAUDE.md says auto-discovered but doesn't reference a skills directory path"
        fi
    else
        # Fallback: check individual skill references (pre-v0.11.0 behavior)
        local missing=0
        for dir in "$SKILLS_DIR"/*/; do
            local skill_name
            skill_name=$(basename "$dir")
            if ! grep -q "/$skill_name" CLAUDE.md; then
                fail "Skill $skill_name not referenced in CLAUDE.md"
                missing=$((missing + 1))
            fi
        done
        if [ "$missing" -eq 0 ]; then
            pass "All skill directories are listed in CLAUDE.md"
        fi
    fi
}

# ============================================================
# CHECK 10: Version consistency between CLAUDE.md and README.md
# ============================================================
check_version_consistency() {
    section "Check 10: Version consistency"

    # CLAUDE.md: "*Version 0.7.0 --"
    # -m1 + ^\*Version anchor stops grep after the canonical first match and
    # avoids SIGPIPE on closed-pipe under set -o pipefail (CI is Linux-strict;
    # macOS is more lenient). Mirrors Check 26's grep shape.
    local claude_version
    claude_version=$(grep -m1 "^\*Version [0-9]" CLAUDE.md | sed 's/^\*Version //' | sed 's/ .*//')

    # README.md: "*v0.7.0*" (optional — simplified README may omit version)
    local readme_version
    readme_version=$(grep '\*v[0-9]' README.md 2>/dev/null | head -1 | sed 's/.*\*v//' | sed 's/\*.*//' || true)

    if [ -z "$claude_version" ]; then
        fail "Could not find version in CLAUDE.md"
    elif [ -z "$readme_version" ]; then
        pass "Version in CLAUDE.md (v$claude_version), README omits version (acceptable)"
    elif [ "$claude_version" = "$readme_version" ]; then
        pass "Version consistent: v$claude_version in both CLAUDE.md and README.md"
    else
        fail "Version mismatch: CLAUDE.md says $claude_version, README.md says $readme_version"
    fi
}

# ============================================================
# CHECK 11: Anti-pattern count in README matches actual headings
# ============================================================
check_antipattern_count() {
    section "Check 11: Anti-pattern count"

    local ap_file="plugins/mycelium/harness/anti-patterns.md"
    if [ ! -f "$ap_file" ]; then
        fail "anti-patterns.md not found"
        return
    fi

    # Count all ### N. headings across all sections (numbering restarts per section)
    local actual_count
    actual_count=$(grep -cE '^### [0-9]+\.' "$ap_file")

    # README: "NN known failure modes" (optional — simplified README may omit)
    local readme_count
    readme_count=$(grep "known failure modes" README.md | sed 's/.*-- //' | sed 's/ known.*//' || echo "0")

    if [ -z "$readme_count" ] || [ "$readme_count" = "0" ]; then
        pass "Anti-pattern count not in README (simplified README), $actual_count exist on disk"
    elif [ "$readme_count" -eq "$actual_count" ]; then
        pass "Anti-pattern count ($readme_count) matches actual headings ($actual_count)"
    else
        fail "README says $readme_count anti-patterns, but $actual_count numbered headings exist"
    fi
}

# ============================================================
# CHECK 12: Theory gate count — canonical authority is engine/theory-gates.md
# (As of 2026-05-08 docs split: README no longer carries the gate table;
#  canonical source is plugins/mycelium/engine/theory-gates.md.)
# ============================================================
check_gate_count() {
    section "Check 12: Theory gate count"

    local gates_file="plugins/mycelium/engine/theory-gates.md"
    if [ ! -f "$gates_file" ]; then
        fail "$gates_file not found (canonical theory gate source missing)"
        return
    fi

    # Canonical count = numbered gate *definitions* only ("### N. <name>").
    # Deliberately NOT matching "## Gate Structure" / "## Gate Definitions" section
    # headings — that loose alternation historically inflated the count to 15,
    # which leaked verbatim into plugin.json and seeded a 12/13/15 split that
    # persisted from v0.23.7 to v0.34.0 (root-cause: decision-log 2026-05-31).
    local canonical
    canonical=$(grep -cE '^### [0-9]+\. ' "$gates_file" || true)

    if [ "$canonical" -eq 0 ]; then
        fail "$gates_file defines no gates (no '### N. <name>' heading found)"
        return
    fi

    # Derive-and-compare: every headline surface stating a TOTAL gate count must
    # equal the canonical definition count. This is the gate-count analogue of
    # Check 6/7 for skills; its absence is exactly why hand-washes kept landing on
    # different numbers. The Nth gate (Explainability/XAI) is conditional (L3-L5,
    # AI products only) but still counts toward the documented total, so the
    # CLAUDE.md transition-roster MENU lists all of them. Per-scale BASELINE
    # tables ("L3 = all 12 gates") legitimately exclude the conditional gate and
    # are NOT checked here — they are a different semantic.
    local mismatch=0

    # JSON marketing surfaces carry a "<N> theory gates" / "<N> gates" token.
    local surface stated
    for surface in \
        "plugins/mycelium/.claude-plugin/plugin.json" \
        ".claude-plugin/marketplace.json"; do
        [ -f "$surface" ] || continue
        stated=$(grep -oE '[0-9]+ (theory )?gates' "$surface" | head -1 | grep -oE '^[0-9]+' || true)
        [ -z "$stated" ] && continue
        if [ "$stated" -ne "$canonical" ]; then
            fail "$surface states $stated gates but $gates_file defines $canonical"
            mismatch=1
        fi
    done

    # CLAUDE.md states the roster as a NAMED LIST, not a count: compare its length.
    if [ -f "CLAUDE.md" ]; then
        local roster_line roster_count
        roster_line=$(grep -E 'must pass applicable gates from:' CLAUDE.md | head -1 || true)
        if [ -n "$roster_line" ]; then
            roster_count=$(echo "$roster_line" | sed -E 's/.*from: //; s/\..*//' | tr ',' '\n' | grep -cE '[A-Za-z]' || true)
            if [ "$roster_count" -ne "$canonical" ]; then
                fail "CLAUDE.md gate roster lists $roster_count names but $gates_file defines $canonical"
                mismatch=1
            fi
        fi
    fi

    if [ "$mismatch" -eq 0 ]; then
        pass "$gates_file defines $canonical gates; all headline surfaces agree"
    fi
}

# ============================================================
# CHECK 13: Theory count claim vs theories.md table rows
# (As of 2026-05-08 docs split: theories table moved to docs/theories.md.
#  Stub state passes informational; Phase 2 fills mechanism-mapped table.)
# ============================================================
check_theory_count() {
    section "Check 13: Theory count"

    local theories_doc="docs/theories.md"

    # README "30+ established frameworks" or "30+ frameworks" — either form is valid.
    local claimed
    claimed=$(grep -oE '[0-9]+\+ established' README.md | head -1 | sed 's/+.*//' || echo "0")
    if [ -z "$claimed" ] || [ "$claimed" = "0" ]; then
        claimed=$(grep -oE '[0-9]+\+ frameworks' README.md | head -1 | sed 's/+.*//' || echo "0")
    fi

    if [ ! -f "$theories_doc" ]; then
        fail "$theories_doc not found"
        return
    fi

    if grep -q "is forthcoming" "$theories_doc"; then
        pass "$theories_doc is a Phase 1 stub; README claims ${claimed}+ frameworks; Phase 2 fills the mechanism-mapped table"
        return
    fi

    local actual_count
    actual_count=$(grep -cE '^\| [A-Za-z0-9]' "$theories_doc" || echo "0")

    if [ "$claimed" = "0" ]; then
        if [ "$actual_count" -gt 0 ]; then
            pass "$theories_doc has $actual_count theory rows (README does not state a count)"
        else
            fail "$theories_doc has no theory rows"
        fi
    elif [ "$actual_count" -ge "$claimed" ]; then
        pass "Theory claim (${claimed}+) satisfied by $actual_count rows in $theories_doc"
    elif grep -q "and more" "$theories_doc"; then
        pass "Theory claim (${claimed}+), $theories_doc shows $actual_count rows + '... and more'"
    else
        fail "README claims ${claimed}+ theories, but only $actual_count rows in $theories_doc"
    fi
}

check_agents_md() {
    section "Check 14: AGENTS.md router discipline"

    if [ ! -f AGENTS.md ]; then
        fail "AGENTS.md not found at repo root"
        return
    fi
    pass "AGENTS.md exists at repo root"

    # Required sections (router structure)
    if grep -q "^## What's available" AGENTS.md; then
        pass "AGENTS.md contains 'What's available' surface table"
    else
        fail "AGENTS.md missing required '## What's available' section"
    fi

    if grep -q "^## Minimal path" AGENTS.md; then
        pass "AGENTS.md contains 'Minimal path' section"
    else
        fail "AGENTS.md missing required '## Minimal path' section"
    fi

    # Router-not-content discipline: AGENTS.md must NOT contain rule statements.
    # The boundary: rules ("MUST", "always do X", "never do Y") belong in
    # CLAUDE.md / harness/ / engine/, not AGENTS.md. AGENTS.md only routes.
    # Allow these strings inside code/markdown table cells (they may appear in
    # quoted file paths or capability descriptions); only flag them as bare
    # imperatives at the start of a line.
    local rule_lines
    rule_lines=$( { grep -E '^[^|`]*\b(MUST|must always|never)\b' AGENTS.md 2>/dev/null || true; } | wc -l | tr -d ' ')
    if [ "$rule_lines" -eq "0" ]; then
        pass "AGENTS.md contains no bare rule statements (router discipline held)"
    else
        warn "AGENTS.md contains $rule_lines line(s) with rule keywords — verify router-not-content"
    fi

    # Length discipline: keep AGENTS.md compact (router, not full guide).
    # Soft cap was 80 pre-plugin-form (2026-05-08); raised to 120 on
    # 2026-05-09 to accommodate plugin-form cross-agent operating models
    # (Codex/Cursor/Aider/Copilot per-class guidance, examples, tab-
    # completion + natural-language invocation notes). If AGENTS.md
    # accumulates further past 120, that's a real "split into sub-docs"
    # signal — file separate references and link from AGENTS.md.
    local line_count
    line_count=$(wc -l < AGENTS.md | tr -d ' ')
    if [ "$line_count" -le 120 ]; then
        pass "AGENTS.md within length cap ($line_count / 120 lines)"
    else
        warn "AGENTS.md exceeds 120-line soft cap ($line_count lines) — likely accumulating content; consider splitting into sub-docs"
    fi
}

check_untrusted_content_wrapping() {
    section "Check 15: Untrusted-content wrapping in skills handling user input"

    # Two-part detector for the prompt-injection-defense convention
    # (plugins/mycelium/harness/security-trust.md#prompt-injection-defense-for-user-supplied-content).
    #
    # Part A: curated list of skills KNOWN to receive user-supplied content
    #         and feed it into model context. Each MUST acknowledge the
    #         wrapping convention. Tier: NUDGE-WARN (rollout in progress).
    # Part B: heuristic detector for NEW skills outside the curated list that
    #         show strong user-content-handling signals — prompts a review-
    #         and-add-to-list decision rather than an automatic warning.
    #
    # Why curated, not pure heuristic: keyword-heuristic detection produced 21
    # false positives in the original audit (workflow skills that mention
    # "interview" or "purpose.yml" without actually interpolating user content
    # into model prompts). Curated list is honest about what's actually at risk.

    # Part A: curated at-risk skills (per audit 2026-05-03, Q3 deep dive;
    # extended 2026-05-04 with the three skills the heuristic surfaced after
    # /xai-check shipped — they all persist user-supplied content into canvas
    # / state files which feed future agent context; extended 2026-05-09 with
    # setup + migrate-from-legacy after the plugin-form pivot — they handle
    # AGENTS.md template content + interactive migration confirmations
    # respectively, both lower-risk than the canvas-write skills but worth
    # acknowledging the wrapping convention).
    local at_risk_skills=(
        "interview"
        "user-interview"
        "mocked-persona-interview"
        "handoff"
        "log-evidence"
        "ost-builder"
        "user-needs-map"
        "jtbd-map"
        "threat-model"
        "security-review"
        "assumption-test"
        "canvas-update"
        "metrics-pull"
        "metrics-detect"
        "setup"
        "migrate-from-legacy"
    )

    local wrapping_pattern='untrusted_user_content|untrusted-content|prompt-injection-defense|security-trust\.md#prompt-injection'
    local missing=()

    for skill in "${at_risk_skills[@]}"; do
        local f="$SKILLS_DIR/${skill}/SKILL.md"
        if [ ! -f "$f" ]; then
            warn "Curated at-risk skill missing: $skill"
            continue
        fi
        if ! grep -qE "$wrapping_pattern" "$f" 2>/dev/null; then
            missing+=("$skill")
        fi
    done

    if [ "${#missing[@]}" -eq "0" ]; then
        pass "All ${#at_risk_skills[@]} curated at-risk skills acknowledge the wrapping convention"
    else
        warn "${#missing[@]} of ${#at_risk_skills[@]} at-risk skills lack wrapping acknowledgment:"
        for skill in "${missing[@]}"; do
            echo "    - $skill"
        done
        echo "    See plugins/mycelium/harness/security-trust.md#prompt-injection-defense-for-user-supplied-content"
    fi

    # Part B: secondary heuristic — new skills outside the curated list that
    # show strong user-content-handling signals (interactive collection patterns)
    local strong_signal='ask the user|ask user.{0,5}:|conduct.{0,15}interview|record.{0,10}answer|raw.{0,10}transcript|user[- ]supplied|user[- ]provided'
    local at_risk_lookup=" ${at_risk_skills[*]} "

    local candidates=()
    while IFS= read -r f; do
        local skill
        skill=$(basename "$(dirname "$f")")
        # Skip skills already on the curated list
        if [[ "$at_risk_lookup" == *" $skill "* ]]; then
            continue
        fi
        if grep -qiE "$strong_signal" "$f" 2>/dev/null; then
            candidates+=("$skill")
        fi
    done < <(find "$SKILLS_DIR" -name "SKILL.md" -type f 2>/dev/null)

    if [ "${#candidates[@]}" -gt "0" ]; then
        warn "${#candidates[@]} new skill(s) show strong user-content-handling signal — review and add to curated list if at-risk:"
        for skill in "${candidates[@]}"; do
            echo "    - $skill"
        done
    fi
}

check_upgrade_manifest_driven() {
    section "Check 16: upgrade.sh is manifest-driven (no hardcoded list drift)"

    # Guards against the recurring drift pattern documented in corrections.md:
    #   2026-04-28: harness/ list hardcoded in upgrade.sh, drifted from manifest
    #   2026-05-03: top_level list hardcoded in upgrade.sh, missed AGENTS.md
    # Same root cause both times — fix-one-list-at-a-time without generalizing.
    # The manifest-driven rewrite (upgrade.sh refactor 2026-05-03) closed this
    # by reading framework lists from manifest.yml via parse_manifest.py.
    # This check ensures the refactor stays intact: upgrade.sh must call
    # parse_manifest.py for each canonical list AND must not contain
    # hardcoded loops over the same patterns.

    local upgrade="plugins/mycelium/scripts/upgrade.sh"
    if [ ! -f "$upgrade" ]; then
        warn "upgrade.sh not found; skipping Check 16"
        return
    fi

    # Required manifest keys that upgrade.sh must call parse_manifest.py for.
    # Add a key here when manifest.yml grows a new framework list section.
    local required_keys=(
        "top_level"
        "directories"
        "single_files"
        "harness_framework"
        "preserved_dir_readmes"
        "evals_replace"
    )

    local missing=()
    for key in "${required_keys[@]}"; do
        if ! grep -qE "parse_manifest\.py $key\b" "$upgrade" 2>/dev/null; then
            missing+=("$key")
        fi
    done

    if [ "${#missing[@]}" -eq "0" ]; then
        pass "upgrade.sh calls parse_manifest.py for all ${#required_keys[@]} required lists"
    else
        fail "upgrade.sh missing parse_manifest.py call for: ${missing[*]}"
        echo "    See .claude/memory/corrections.md 2026-05-03 'upgrade.sh top_level list missed AGENTS.md'"
    fi

    # Drift detector: count hardcoded framework directory literals in upgrade.sh.
    # After the manifest-driven rewrite, these literals should be near-zero
    # (only references in comments are acceptable). A spike indicates someone
    # re-introduced a hardcoded loop.
    #
    # Allowlist convention (2026-05-24): intentional literals (e.g., the legacy-
    # tree detection guard at upgrade.sh line ~100, which checks for upstream
    # framework files that no longer ship — a structural-by-design check, not
    # drift) may carry an end-of-line marker `# check-16-allowlist: <reason>`
    # to exempt them. Reason MUST be present; bare marker without rationale
    # does not exempt.
    local hardcoded_dir_count
    hardcoded_dir_count=$( { grep -E '\.claude/(engine|skills|hooks|domains|orchestration|schemas|optimization|auto-dogfood)/?[ "$]' "$upgrade" 2>/dev/null \
        | grep -vE '^\s*#' \
        | grep -vE 'parse_manifest\.py' \
        | grep -vE '# check-16-allowlist:\s*\S' \
        || true; } | wc -l | tr -d ' ')

    if [ "$hardcoded_dir_count" -le "0" ]; then
        pass "upgrade.sh contains no hardcoded framework-directory literals (drift-free)"
    elif [ "$hardcoded_dir_count" -le "3" ]; then
        warn "upgrade.sh contains $hardcoded_dir_count hardcoded framework-directory literal(s) — review for drift candidates"
    else
        fail "upgrade.sh contains $hardcoded_dir_count hardcoded framework-directory literals — refactor to manifest-driven"
        echo "    Use: VAR=\$(python3 plugins/mycelium/scripts/parse_manifest.py <key>); for x in \$VAR; do ...; done"
    fi

    # Drift detector for top-level files: same pattern + allowlist marker.
    local hardcoded_top_count
    hardcoded_top_count=$( { grep -E '\b(CLAUDE\.md|README\.md|AGENTS\.md|CONTRIBUTORS\.md|LICENSE)\b' "$upgrade" 2>/dev/null \
        | grep -vE '^\s*#' \
        | grep -vE 'parse_manifest\.py' \
        | grep -vE '\$TEMP_DIR' \
        | grep -vE '# check-16-allowlist:\s*\S' \
        || true; } | wc -l | tr -d ' ')

    if [ "$hardcoded_top_count" -le "0" ]; then
        pass "upgrade.sh contains no hardcoded top-level filename literals"
    elif [ "$hardcoded_top_count" -le "2" ]; then
        warn "upgrade.sh contains $hardcoded_top_count hardcoded top-level filename literal(s) — review"
    else
        fail "upgrade.sh contains $hardcoded_top_count hardcoded top-level filename literals — refactor to manifest-driven"
    fi
}

check_version_bump_discipline() {
    section "Check 26: Material framework changes require a version bump"

    # 5th instance of "documented rule diverges from enforcement" cluster
    # (corrections.md 2026-05-04). Cross-project signal: another dogfood
    # project's agent saw "0.15.1 → 0.15.1, 42 files refreshed" — the upgrade
    # signal was wasted because version stayed pinned across substantive
    # framework changes. This check enforces semver discipline at the harness
    # layer rather than relying on convention.
    #
    # Definition of "material framework change": any modification to skills,
    # engine docs, harness files, hooks, scripts, jit-tooling docs, top-level
    # CLAUDE.md/AGENTS.md, or docs/ since the last commit that changed the
    # Version line in CLAUDE.md.
    #
    # Coverage proof: at the moment of writing (2026-05-04), this check
    # immediately FAILS on the upstream working tree because the session
    # shipped G-V12, /xai-check, ai-system-card, warnings ingestor, etc.
    # without bumping past 0.15.1. Bumping to 0.16.0 in the same commit makes
    # it pass — that round-trip is the proof that the check catches the
    # known-bad case.

    if ! command -v git >/dev/null 2>&1 || ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        info "git not available — skipping version-bump discipline check"
        return
    fi

    local curr_version
    curr_version=$(grep -m1 "^\*Version " CLAUDE.md 2>/dev/null | sed 's/.*Version //' | sed 's/[ —].*//')
    if [ -z "$curr_version" ]; then
        warn "Could not read current Version line from CLAUDE.md"
        return
    fi

    # Find the last commit that changed the Version line (-G regex match).
    local last_version_commit
    last_version_commit=$(git log -1 --pretty=format:%H -G "^\*Version " -- CLAUDE.md 2>/dev/null)
    if [ -z "$last_version_commit" ]; then
        info "No prior version-bumping commit found — skipping (initial commit?)"
        return
    fi

    local head_commit
    head_commit=$(git rev-parse HEAD 2>/dev/null)

    # Material paths watched (kept as a single list for both committed and
    # uncommitted diffs).
    local material_paths=(
        "plugins/mycelium/skills"
        "plugins/mycelium/engine"
        "plugins/mycelium/harness"
        "plugins/mycelium/hooks"
        "plugins/mycelium/scripts"
        "plugins/mycelium/jit-tooling"
        "plugins/mycelium/schemas"
        "plugins/mycelium/domains"
        "plugins/mycelium/orchestration"
        "plugins/mycelium/.claude-plugin/plugin.json"
        "plugins/mycelium/.claude-plugin/marketplace.json"
        ".claude-plugin/marketplace.json"
        "tests"
        "CLAUDE.md"
        "AGENTS.md"
        "README.md"
        "docs"
    )

    # Count committed material changes since the last version-line edit.
    local committed_count=0
    if [ "$last_version_commit" != "$head_commit" ]; then
        committed_count=$(git diff --name-only "$last_version_commit"..HEAD -- "${material_paths[@]}" 2>/dev/null | wc -l | tr -d ' ')
    fi

    # Count uncommitted material changes in the working tree (post-bump edits).
    local uncommitted_count
    uncommitted_count=$(git diff --name-only HEAD -- "${material_paths[@]}" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$committed_count" -gt 0 ]; then
        # FAIL: committed material changes without a version bump. Hard stop —
        # the canonical error this check exists to catch.
        fail "Version-bump discipline: $committed_count material framework file(s) committed since the last version bump (currently $curr_version). Bump CLAUDE.md Version line per plugins/mycelium/engine/version-discipline.md (semver: new skill/feature → minor; backwards-incompatible → major; doc-only → patch)."
    elif [ "$uncommitted_count" -gt 0 ] && [ "$last_version_commit" = "$head_commit" ]; then
        # WARN: HEAD bumped the version, but new material edits are pending.
        # Either fold into HEAD (commit --amend before push) or expect to
        # bump again at the next commit. Catches the post-bump-mid-session edit case.
        warn "Version-bump check: HEAD bumped to $curr_version, but $uncommitted_count uncommitted material file(s) waiting. Fold into HEAD (amend before push) or bump again at the next commit."
    elif [ "$uncommitted_count" -gt 0 ]; then
        # FAIL: uncommitted material changes AND HEAD didn't bump — the next
        # commit must either bump or be a non-material edit.
        fail "Version-bump discipline: $uncommitted_count material framework file(s) uncommitted with no version bump in HEAD (currently $curr_version). Bump CLAUDE.md before committing, per plugins/mycelium/engine/version-discipline.md."
    elif [ "$last_version_commit" = "$head_commit" ]; then
        pass "Version-bump check: HEAD commit changed the Version line ($curr_version), no pending material changes"
    else
        pass "Version-bump check: no material changes since last bump (version $curr_version)"
    fi
}

check_code_quality() {
    section "Check 17: Python + Bash code-quality regression"

    # Guards against the L4 cleanup gap surfaced 2026-05-03: framework code
    # shipped without DoD discipline accumulated 54 ruff findings, 1 DRY
    # violation, 1 KISS violation, 0 unit tests. The L4 cleanup cycle
    # (D1-D6) brought everything to the cleanliness standard the framework
    # itself preaches in engineering-principles.md and definition-of-done.
    # This check ensures the standard is preserved going forward.
    #
    # Both tools are optional — gracefully skipped if not installed (so the
    # check never blocks downstream Mycelium projects that don't have
    # them in their dev env). Install via: pip install -r requirements-ci.txt

    # ----- Python: ruff -----
    if ! command -v ruff >/dev/null 2>&1; then
        warn "ruff not installed — skipping Python lint check (install via requirements-ci.txt)"
    else
        # POLICY LIVES IN ruff.toml — NOT HERE (v0.61.0).
        #
        # This block used to carry its own `--select=ALL --ignore=<11 rules>`
        # string. Nothing else on disk read it, so `ruff check` in an editor used
        # ruff's DEFAULT selection and said "All checks passed" while CI reported
        # 35 errors against a selection that existed only in this file. Same
        # defect class as the wiring bugs of this release: a specification kept
        # where nothing reads it. Now `ruff check` is invoked with NO flags, so it
        # resolves ruff.toml exactly as a contributor's editor and pre-commit do,
        # and the three cannot disagree.
        #
        # Gate is 0, repo-wide, and FAILS. The previous shape — FAIL on a
        # hand-listed 3-file "cleanup-cycle" subset, WARN on everything else —
        # was the enumerate-the-scope anti-pattern: nothing ever added a new file
        # to that list, so every script written after it was ungated (this
        # release's own check_wiring.py included). A repo at 0 needs no list.
        # Check 17's standing invariant is that it never BLOCKS a downstream
        # project for a missing file — so the policy requirement is scoped to the
        # framework repo (identified by plugins/mycelium/). A consumer project is
        # not obliged to adopt Mycelium's lint policy, and failing them for it
        # would be the framework imposing house style on someone else's repo.
        # VERSION-MATCH GUARD (added after PR #17 CI). `select = ["ALL"]` makes the
        # ruff VERSION part of the policy: a newer ruff enables rules that did not
        # exist when the tree was cleaned, so an unpinned spec means local and CI
        # disagree about what "clean" is. That is precisely what happened —
        # local 0.15.12 said 0 errors, CI resolved `ruff>=0.1.0` to 0.16.0 and said
        # 59. Compare the installed version against the pin and fail LOUDLY on
        # divergence, rather than letting two environments hold two policies.
        # Framework repo only, per Check 17's never-block-a-consumer invariant.
        if [ -d "plugins/mycelium" ] && [ -f "requirements-ci.txt" ]; then
            local ruff_pin ruff_have
            # `|| true` is LOAD-BEARING on both lines. The script runs under
            # `set -euo pipefail`, and a no-match grep exits 1 — so without it the
            # substitution aborts check_code_quality mid-check precisely when the
            # spec is UNPINNED, which is the condition this guard exists to detect.
            # The guard would have failed open on its own subject: it reported
            # nothing rather than "not pinned", the same fail-open shape as the six
            # findings this release fixes. Caught by the negative-control probe
            # before merge, not by reading the code.
            ruff_pin=$(grep -oE '^ruff==[0-9][0-9.]*' requirements-ci.txt | head -1 | cut -d= -f3 || true)
            ruff_have=$(ruff --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
            if [ -z "$ruff_pin" ]; then
                fail "ruff is not pinned in requirements-ci.txt. ruff.toml selects ALL, so the version IS the policy — an unbounded spec lets CI and local disagree about what 'clean' means (PR #17: 0 vs 59 errors)."
            elif [ -n "$ruff_have" ] && [ "$ruff_pin" != "$ruff_have" ]; then
                fail "ruff version divergence: installed $ruff_have, pinned $ruff_pin. With select=ALL these are DIFFERENT policies. Install the pin (pip install -r requirements-ci.txt), or bump the pin deliberately and triage the newly-firing rules."
            else
                pass "ruff version matches the pin ($ruff_pin) — one policy, not two"
            fi
        fi

        if [ ! -f "ruff.toml" ]; then
            if [ -d "plugins/mycelium" ]; then
                fail "ruff.toml missing in the framework repo — the lint policy must be declared on disk, not inside this script"
            else
                info "ruff: no ruff.toml in this project — lint policy is the project's own call (skipped)"
            fi
        else
            local ruff_out ruff_count
            ruff_out=$( { ruff check . 2>/dev/null || true; } )
            ruff_count=$(printf '%s' "$ruff_out" | grep -oE "Found [0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0")
            ruff_count=${ruff_count:-0}

            if [ "$ruff_count" -eq "0" ]; then
                pass "ruff: 0 errors repo-wide under the declared policy (ruff.toml)"
            else
                fail "ruff: $ruff_count error(s) under ruff.toml. Fix them, or change the policy in ruff.toml with a stated reason — do not re-introduce a tolerated-debt baseline."
            fi
        fi
    fi

    # ----- Bash: shellcheck -----
    # Pre-existing warnings as of 2026-05-03: 3 (gate.sh:19, session-start.sh:8/46).
    # These are documented historical tech debt outside the cleanup cycle scope.
    # Threshold tracks REGRESSIONS above that baseline.
    local SHELLCHECK_BASELINE=3
    if ! command -v shellcheck >/dev/null 2>&1; then
        warn "shellcheck not installed — skipping Bash lint check (install via requirements-ci.txt)"
    else
        local sc_files=()
        for f in plugins/mycelium/scripts/*.sh plugins/mycelium/hooks/*.sh tests/*.sh; do
            [ -f "$f" ] && sc_files+=("$f")
        done

        local sc_warnings
        sc_warnings=$( { shellcheck -S warning "${sc_files[@]}" 2>/dev/null || true; } | grep -cE "^In " || true)

        if [ "$sc_warnings" -le "$SHELLCHECK_BASELINE" ]; then
            pass "shellcheck: $sc_warnings warning(s) — at-or-below baseline ($SHELLCHECK_BASELINE)"
        else
            fail "shellcheck: $sc_warnings warnings — regression above baseline ($SHELLCHECK_BASELINE). Pre-existing tech debt is in gate.sh and session-start.sh; new warnings should be addressed."
        fi
    fi

    # ----- Pytest -----
    if ! command -v pytest >/dev/null 2>&1; then
        warn "pytest not installed — skipping unit-test execution (install via requirements-ci.txt)"
    elif [ ! -d "tests/python" ]; then
        warn "pytest tests directory missing — skipping"
    else
        if pytest tests/python/ -q --tb=no >/dev/null 2>&1; then
            local test_count
            test_count=$(pytest tests/python/ --collect-only -q 2>/dev/null | tail -1 | grep -oE "[0-9]+ tests?" | head -1)
            pass "pytest: all tests pass${test_count:+ ($test_count)}"
        else
            fail "pytest: tests failing — run 'pytest tests/python/ -v' for details"
        fi
    fi

    # ----- Bash check tests (tests/bash) — G-V12 coverage proofs -----
    # Convention established 2026-05-23 with Check 30 as worked example.
    # Future Bash checks should ship with fixture tests per tests/bash/README.md.
    #
    # On failure: capture run.sh output and print failing assertions inline.
    # Previously suppressed output silently, making CI failures impossible to
    # diagnose without local replication (silent-skip pattern, parallel to
    # validate_canvas.py fail-loud refactor shipped v0.25.1). Surfaced
    # 2026-05-24 when bash tests passed locally on macOS+BSD but failed on
    # CI's Linux+GNU runner — silent stdout/stderr swallowing forced
    # diagnostic-by-environment-replication rather than read-the-log.
    if [ ! -d "tests/bash" ]; then
        warn "tests/bash directory missing — skipping Bash check tests"
    elif [ ! -f "tests/bash/run.sh" ]; then
        warn "tests/bash/run.sh missing — skipping Bash check tests"
    else
        # NOTE: must use `if VAR=$(cmd); then` shape, not bare assignment
        # capture, because `set -e` (top of file) aborts on a non-zero
        # command-substitution exit in a plain assignment. The if-guard
        # form lets the else branch run for diagnosis. Same pattern the
        # pytest block above uses correctly; my first v0.26.2 attempt
        # used bare assignment and the diagnostic code never executed.
        local bash_test_output
        if bash_test_output=$(bash tests/bash/run.sh 2>&1); then
            local bash_test_count
            bash_test_count=$(find tests/bash -maxdepth 1 -name "test_*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')
            pass "bash check tests: all pass (${bash_test_count} test file(s))"
        else
            fail "bash check tests: failures (see diagnostic below)"
            # Print raw output (capped) for diagnosis. Earlier attempts used a
            # regex filter on ✓/✗ but Linux grep with default LANG=C does not
            # match multi-byte UTF-8 — produced empty-looking diagnostics on
            # CI even when tests had visible ✗ markers. `|| true` tolerates
            # expected SIGPIPE from head's early close (pipefail + set -e
            # would otherwise abort the validator mid-diagnostic).
            { echo "$bash_test_output" | head -200 | sed 's/^/    /'; } || true
        fi
    fi
}

# ============================================================
# CHECK 27: Skills-tree parity (plugin vs legacy during transition)
# ============================================================
check_skills_tree_parity() {
    section "Check 27: Skills-tree parity (plugin vs legacy)"

    if [ ! -d "$PLUGIN_SKILLS" ] || [ ! -d "$LEGACY_SKILLS" ]; then
        info "Only one skills tree present (form: $SKILLS_FORM) — parity check N/A"
        return
    fi

    local plugin_count legacy_count
    plugin_count=$(find "$PLUGIN_SKILLS" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    legacy_count=$(find "$LEGACY_SKILLS" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

    if [ "$plugin_count" != "$legacy_count" ]; then
        warn "Skill count diverges: plugin=$plugin_count, legacy=$legacy_count (legacy may be drifting; clean up at canonical 0.20.0 bump)"
    else
        pass "Skill count matches across trees ($plugin_count each)"
    fi

    # Set diff: which skill names differ
    local plugin_names legacy_names
    plugin_names=$(find "$PLUGIN_SKILLS" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
    legacy_names=$(find "$LEGACY_SKILLS" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)

    local plugin_only legacy_only
    plugin_only=$(comm -23 <(echo "$plugin_names") <(echo "$legacy_names"))
    legacy_only=$(comm -13 <(echo "$plugin_names") <(echo "$legacy_names"))

    if [ -n "$plugin_only" ]; then
        warn "Skills only in plugin tree (not mirrored to legacy): $(echo "$plugin_only" | tr '\n' ' ')"
    fi
    if [ -n "$legacy_only" ]; then
        warn "Skills only in legacy tree (not mirrored to plugin): $(echo "$legacy_only" | tr '\n' ' ')"
    fi
    if [ -z "$plugin_only" ] && [ -z "$legacy_only" ]; then
        pass "Skill name set matches across trees"
    fi
}

# Helper: info-level (not pass/fail/warn) — for diagnostic context.
info() { echo "  INFO: $1"; }

# ============================================================
# CHECK 30: plugin.json version tracks CLAUDE.md leading version line
# ============================================================
# Coupled-field sync enforcement (added 2026-05-09 after 0.21.0 shipped
# without bumping plugin.json — same drift class as 0.20.x dogfood B2,
# but at MINOR-bump rather than PATCH-bump scale). Check 26 watches
# plugin.json as a material path; this check enforces the field-level
# invariant that plugin.json#version === leading "Version X.Y.Z" in
# CLAUDE.md. Without it, ship a CLAUDE.md bump and forget plugin.json,
# users running /plugin list see a stale version.
# ============================================================
# CHECK 31: Canvas-writing skills carry Read-before-Write preflight (anti-pattern #7 instance #5)
# ============================================================
# Per CLAUDE.md "Canvas writes — Read before Write (HARD RULE)" and
# corrections.md 2026-05-09 (anti-pattern #7 instance #5). Every SKILL.md
# that mentions Update/Write/Append against .claude/canvas/*.yml must
# carry a Preflight block telling the agent to use the Read tool on
# the target file BEFORE Write. Without this, agents conflate `head`
# via Bash with the `Read` tool and waste ~14k tokens on a Write-fail
# → Read → re-Write loop.
#
# The marker is "## Preflight: Read target canvas file" — a uniform
# heading inserted into every canvas-writing skill 2026-05-09.
check_canvas_write_preflight() {
    section "Check 31: Canvas-write Preflight presence (anti-pattern #7 instance #5)"

    local skills_dir="$SKILLS_DIR"
    if [ ! -d "$skills_dir" ]; then
        info "Skills dir absent — Check 31 N/A"
        return
    fi

    local marker="## Preflight: Read target canvas file"
    local missing_count=0
    local missing_list=""
    local checked=0

    # Find SKILL.md files that mention canvas writes (Update/Write/Append .claude/canvas/*.yml)
    while IFS= read -r skill; do
        checked=$((checked + 1))
        if ! grep -q "$marker" "$skill"; then
            missing_count=$((missing_count + 1))
            missing_list="${missing_list}"$'\n'"  - ${skill#"$skills_dir"/}"
        fi
    done < <(grep -lE "(Update|Write|Append).*canvas/[a-z-]+\.yml" "$skills_dir"/*/SKILL.md 2>/dev/null)

    if [ "$missing_count" -eq 0 ]; then
        pass "All $checked canvas-writing skills carry the Read-before-Write Preflight block"
    else
        printf "  WARN: %d canvas-writing skill(s) missing Preflight block:%s\n" "$missing_count" "$missing_list"
        WARN=$((WARN + 1))
    fi
}

# ============================================================
# CHECK 32: Four-Risks levels populated when opportunity is referenced
# by an active diamond
# ============================================================
# Per the 2026-05-09 team-topologies dogfood (F8): /mycelium:diamond-progress
# step 2 reads value/usability/feasibility/viability levels from
# opportunities.yml before evaluating other gates. When those levels are
# absent, the check vacuously passes — a false-negative gate. Multi-team
# operation magnifies this: one team's incomplete evidence becomes another
# team's "validated" gate-passage.
#
# This check enforces the schema-required-when-active rule that
# diamond-progress's prose discipline relies on. WARN initially (not FAIL)
# to absorb existing under-populated state without breaking CI; flip to FAIL
# after 2-3 weeks of clean runs per the validator's documented graduation
# pattern.
# Check 33: Plugin tree must not contain unconsented personal identifiers.
#
# Personal first names in plugins/mycelium/** ship to every downstream user
# via the plugin marketplace. Consent state for each named individual lives
# in a registry kept OUTSIDE this public repo — storing it in the public
# repo would be self-defeating (the registry contains the very names whose
# private-channel attribution it tracks).
#
# Registry path: $MYCELIUM_ATTRIBUTION_REGISTRY env var. Fails-open if
# unset or pointing at a missing file. Expected unset on:
#   - fresh maintainer clones (point at your roadmap/private repo)
#   - CI runners that don't check out private companion repos
#   - downstream user environments (Check 33 is maintainer-side only;
#     tests/ doesn't ship via the plugin, only plugins/mycelium/ does)
#
# Canonical location for haabe's setup is the private companion repo at
# haabe/mycelium-roadmap (e.g.,
# ../mycelium-roadmap/.claude/memory/attribution-registry.yml) — but no
# repo name is hardcoded here so the same check works for forks or
# alternate layouts.
#
# WARN-only initially per the framework's observability-before-enforcement
# discipline; graduates to FAIL once existing pre-disclosure leaks are
# addressed.
#
# Surfaced 2026-05-14 in-session: a generic-framed first-run observer
# nonetheless drifted into plugins/mycelium/harness/anti-patterns.md via the
# graduation chain (corrections.md entry referenced by name when the anti-
# pattern entry was graduated). The lived-friction attribution mechanism
# itself was the leak vector — generic capture at point-of-friction does not
# guarantee generic carry-through when downstream framework files cite their
# trigger sources.
check_plugin_identifier_leak() {
    section "Check 33: Plugin tree contains no unconsented personal identifiers"

    local registry="${MYCELIUM_ATTRIBUTION_REGISTRY:-}"
    if [ -z "$registry" ] || [ ! -f "$registry" ]; then
        # Fail-open behavior diverges by context (graduated v0.23.22 after
        # named-attribution-leak recurrence #3, 2026-05-15):
        #   - CI runs: INFO (CI runners legitimately can't reach the private
        #     companion repo where the registry lives; check is maintainer-side).
        #   - Local maintainer dev IN THE FRAMEWORK REPO: WARN (registry should
        #     be configured; missing-registry is the leak vector).
        #   - Downstream user / non-self-host project: INFO (check is maintainer-
        #     side, not user-side; downstream users don't have a cohort registry
        #     concern).
        if [ -n "${CI:-}${GITHUB_ACTIONS:-}" ]; then
            info "Attribution registry absent — Check 33 N/A in CI (registry lives in private companion repo, not available to CI runners)"
            return
        fi
        # Framework-self-host detection (same convention used by
        # engine/cycle-learning.md framework-on-framework exemption):
        # plugin manifest + CLAUDE.md beginning with "# Mycelium:".
        if [ -f "plugins/mycelium/.claude-plugin/plugin.json" ] && \
           head -1 CLAUDE.md 2>/dev/null | grep -q "^# Mycelium:"; then
            warn "Check 33: attribution registry absent in framework-self-host context — leak detection NOT running"
            echo "    Set MYCELIUM_ATTRIBUTION_REGISTRY to your private registry path before editing the public framework tree." >&2
            echo "    Canonical location: ../mycelium-roadmap/.claude/memory/attribution-registry.yml (or your fork's equivalent)." >&2
            echo "    Without the registry, named-attribution leaks into plugins/mycelium/ will not be caught locally — see corrections.md 2026-05-15 for the recurrence-#3 incident." >&2
            return
        fi
        info "Attribution registry absent — Check 33 N/A (set MYCELIUM_ATTRIBUTION_REGISTRY to a registry file outside this repo to enable)"
        return
    fi

    local flagged
    set +e
    flagged=$(python3 - "$registry" <<'PY' 2>/dev/null
import sys
import yaml
try:
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f) or {}
    names = [
        p["name"] for p in data.get("people", [])
        if p.get("consent") in ("generic_only", "unknown")
    ]
    print("\n".join(names))
except Exception as e:
    sys.stderr.write(f"registry parse error: {e}\n")
    sys.exit(1)
PY
)
    local rc=$?
    set -e

    if [ "$rc" -ne 0 ]; then
        fail "Check 33: attribution-registry.yml parse error — fix syntax or remove file to disable check"
        return
    fi

    if [ -z "$flagged" ]; then
        pass "Check 33: no flagged identifiers in registry (all entries are consent=public_ok)"
        return
    fi

    # Scope expanded v0.23.23 after named-attribution-leak recurrence-#3
    # (corrections.md 2026-05-15): the prior scope was `plugins/mycelium/`
    # only, justified as "plugin tree is what ships via marketplace." But
    # docs/, CLAUDE.md, README.md, .claude/memory/ are all publicly visible
    # on GitHub even though they don't ship via the plugin — and the v0.23.21
    # leak hit exactly those paths. Public-visibility scope is the right
    # boundary, not plugin-distribution scope.
    #
    # Excludes: .git/, node_modules/, .gitignored paths. Doesn't try to
    # exclude per-file gitignore status (too expensive for a pre-push gate);
    # uses path-based exclusion only.
    local scan_paths=(
        "plugins/mycelium/"
        "CLAUDE.md"
        "README.md"
        "AGENTS.md"
        "CONTRIBUTORS.md"
        "docs/"
        ".claude/memory/corrections.md"
        ".claude/memory/patterns.md"
        ".claude/memory/cluster-instances.md"
        ".claude/canvas/"
        ".claude/harness/"
        ".claude/engine/"
        "tests/"
    )

    local total_hits=0
    local hit_detail=""
    while IFS= read -r name; do
        [ -z "$name" ] && continue
        local matches=""
        for path in "${scan_paths[@]}"; do
            [ ! -e "$path" ] && continue
            local found
            found=$(grep -rEn "\b${name}\b" "$path" \
                --include="*.md" --include="*.yml" --include="*.yaml" \
                --include="*.json" --include="*.py" --include="*.sh" \
                2>/dev/null || true)
            if [ -n "$found" ]; then
                matches="${matches}${matches:+$'\n'}${found}"
            fi
        done
        if [ -n "$matches" ]; then
            local n
            n=$(echo "$matches" | wc -l | tr -d ' ')
            total_hits=$((total_hits + n))
            hit_detail+=$'\n'"  '${name}' (${n} leak[s]):"
            while IFS= read -r m; do
                hit_detail+=$'\n'"    ${m}"
            done <<< "$matches"
        fi
    done <<< "$flagged"

    if [ "$total_hits" -eq 0 ]; then
        pass "Check 33: 0 leaks in public-visibility scope (all flagged names absent from publicly-visible paths)"
    else
        # FAIL behavior graduated v0.23.23 from prior WARN-only state.
        # Pre-disclosure leaks are now cleaned up; subsequent leaks should
        # block the validator run rather than slip through as warnings.
        fail "Check 33: ${total_hits} leak(s) — flagged identifiers in publicly-visible content${hit_detail}"
        echo "    Action: regenericize occurrences OR escalate consent in ${registry}."
    fi
}

# Check 34: CLAUDE.md must contain at most one version entry.
#
# Convention: CLAUDE.md frontmatter carries only the *current* release's
# changelog entry; full history lives in docs/changelog.md. When a new
# version is bumped, the prior entry is migrated to docs/changelog.md
# rather than accumulating in CLAUDE.md.
#
# Detection: count lines matching `^\*Version [0-9]` (the leading-italic-
# asterisk + literal "Version" + version number that opens each entry).
# More than 1 means a prior entry wasn't migrated.
#
# Graduated 2026-05-14 after 5 consecutive in-session violations (v0.23.10
# → v0.23.14, each new prose entry prepended without migrating the prior).
# The agent forgot once at v0.23.10 then carried the wrong pattern forward
# four more times by reading the just-written file as canonical example.
# Anti-pattern #7 at the meta layer (consistency-as-evidence: validation
# passing on commit N treated as evidence commit N-1 was correct).
# Mechanism beats vigilance for cross-session pattern adherence.
check_claudemd_single_version_entry() {
    section "Check 34: CLAUDE.md contains at most one version entry (deferred-entries migrated to changelog)"

    if [ ! -f CLAUDE.md ]; then
        info "CLAUDE.md absent — Check 34 N/A"
        return
    fi

    local count
    count=$(grep -cE '^\*Version [0-9]' CLAUDE.md 2>/dev/null || echo 0)

    if [ "$count" -le 1 ]; then
        pass "Check 34: $count version entry in CLAUDE.md (≤1, discipline holding)"
    else
        fail "Check 34: $count version entries in CLAUDE.md (should be ≤1). Migrate older entries to docs/changelog.md per the established convention. The latest entry stays; prior entries move."
    fi
}

check_four_risks_when_active() {
    section "Check 32: Four-Risks levels required on active-diamond opportunities (F8)"

    local opps_file=".claude/canvas/opportunities.yml"

    if [ ! -f "$opps_file" ]; then
        info "canvas/opportunities.yml absent — Check 32 N/A"
        return
    fi

    # set -euo pipefail at top of file would abort the script when the
    # python3 invocation exits 1 to signal a WARN (which the wrapper logic
    # below is intended to convert to WARN, not FAIL). Temporarily disable
    # errexit around the rc capture so the wrapper actually runs.
    local result rc
    set +e
    result=$(python3 - "$opps_file" <<'PY'
import re
import sys
from pathlib import Path

opps_path = sys.argv[1]
try:
    import yaml  # type: ignore
    use_yaml = True
except ImportError:
    use_yaml = False

text = Path(opps_path).read_text()

def has_levels(opp_obj):
    missing = []
    for risk in ("value", "usability", "feasibility", "viability"):
        block = opp_obj.get(risk) or {}
        level = block.get("level") if isinstance(block, dict) else None
        if level in (None, "", "TBD", "tbd"):
            missing.append(risk)
    return missing

missing_per_opp = {}
total = 0

if use_yaml:
    try:
        opps = yaml.safe_load(text) or {}
    except Exception:
        opps = None
    if isinstance(opps, dict):
        for o in opps.get("opportunities") or []:
            if not isinstance(o, dict) or not o.get("id"):
                continue
            total += 1
            m = has_levels(o)
            if m:
                missing_per_opp[o["id"]] = m
else:
    for m_block in re.finditer(r"(?:^|\n)\s*-\s*id:\s*([\w-]+)\b(.*?)(?=\n\s*-\s*id:|\Z)", text, re.DOTALL):
        opp_id, block = m_block.group(1), m_block.group(2)
        if not opp_id.startswith("opp-"):
            continue
        total += 1
        miss = []
        for risk in ("value", "usability", "feasibility", "viability"):
            if not re.search(rf"\n\s+{risk}:\s*\n\s+level:\s*[^\s\n]", block):
                miss.append(risk)
        if miss:
            missing_per_opp[opp_id] = miss

if total == 0:
    print("No opportunities to check")
    sys.exit(0)
if not missing_per_opp:
    print(f"All {total} opportunity entries have Four-Risks levels populated")
    sys.exit(0)

print(f"{len(missing_per_opp)} of {total} opportunity entries missing Four-Risks levels (vacuous-pass risk in /mycelium:diamond-progress):")
for ref, miss in sorted(missing_per_opp.items()):
    print(f"  - {ref}: missing {', '.join(miss)}")
sys.exit(1)
PY
    )
    rc=$?
    set -e
    if [ $rc -eq 0 ]; then
        pass "$result"
    else
        warn "$result"
    fi
}

check_plugin_json_version_sync() {
    section "Check 30: plugin.json#version tracks CLAUDE.md Version line"

    local claude_md="CLAUDE.md"
    local plugin_json="plugins/mycelium/.claude-plugin/plugin.json"

    if [ ! -f "$claude_md" ] || [ ! -f "$plugin_json" ]; then
        info "Either CLAUDE.md or plugin.json absent — Check 30 N/A"
        return
    fi

    local claude_version plugin_version
    claude_version=$(grep -m1 "^\*Version " "$claude_md" 2>/dev/null | sed -E 's/^\*Version ([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
    plugin_version=$(grep -m1 '"version":' "$plugin_json" 2>/dev/null | sed 's/.*"version":[ ]*"//' | sed 's/".*//')

    if [ -z "$claude_version" ]; then
        fail "Could not read Version line from CLAUDE.md"
        return
    fi
    if [ -z "$plugin_version" ]; then
        fail "Could not read version field from $plugin_json"
        return
    fi

    if [ "$claude_version" = "$plugin_version" ]; then
        pass "plugin.json#version matches CLAUDE.md ($claude_version)"
    else
        fail "Version drift: CLAUDE.md=$claude_version, plugin.json=$plugin_version. Sync plugin.json to match."
    fi
}

# ============================================================
# CHECK 29: Stale-state-read pattern scan (anti-pattern #8)
# ============================================================
# Per harness/anti-patterns.md #8 "Stale State Read" (graduated 2026-05-09).
# Scans plugin scripts that read state files (manifest.yml, settings.json,
# canvas YAML) for the failure mode: hardcoded local-path default without an
# explicit-source argv override. The worked example is parse_manifest.py's
# `--manifest=<path>` parameter — every state-reading script should follow
# the same shape so upgrade/sync flows can pass the upstream/temp-dir copy.
#
# This check is informational at WARN level until the pattern is fully
# enforceable. It surfaces candidate scripts; manual review confirms whether
# the script actually needs the override (some scripts read state that's
# never replaced mid-run, e.g., truly-static config).
check_stale_state_read_pattern() {
    section "Check 29: Stale-state-read pattern scan (anti-pattern #8)"

    local scripts_dir="plugins/mycelium/scripts"
    if [ ! -d "$scripts_dir" ]; then
        info "Plugin scripts dir absent — Check 29 N/A"
        return
    fi

    # Heuristic: find Python scripts that resolve a state file via
    # `Path(__file__)...` AND lack an explicit-source override mechanism.
    # Override mechanisms recognized: argparse / sys.argv / --manifest /
    # --source / --config (CLI-arg pattern), OR os.environ / os.getenv
    # (env-var pattern, e.g. CLAUDE_PROJECT_DIR / CLAUDE_PLUGIN_ROOT).
    # Both pattern + missing-override flag the script; either alone is fine.
    local candidates=()
    while IFS= read -r f; do
        if grep -qE "Path\(__file__\)" "$f" 2>/dev/null && \
           grep -qE "(manifest|settings|state|canvas).*\.ya?ml|\.json" "$f" 2>/dev/null && \
           ! grep -qE "argparse|sys\.argv|--manifest|--source|--config|os\.environ|os\.getenv" "$f" 2>/dev/null; then
            candidates+=("$f")
        fi
    done < <(find "$scripts_dir" -name "*.py" -type f 2>/dev/null)

    if [ "${#candidates[@]}" -eq 0 ]; then
        pass "No stale-state-read pattern candidates detected in $scripts_dir"
    else
        warn "${#candidates[@]} script(s) match the stale-state-read heuristic (review manually):"
        for f in "${candidates[@]}"; do
            echo "    - $f"
        done
        echo "    Per anti-pattern #8: state-reading scripts should accept --source=<path>"
        echo "    or equivalent. Worked example: parse_manifest.py --manifest=<path>."
    fi
}

# ============================================================
# CHECK 28: Manifest dual-source byte-match (transition artifact)
# ============================================================
# .claude/manifest.yml is deprecated as of v0.20.15 in favour of
# plugins/mycelium/manifest.yml (canonical). While both files exist,
# they MUST byte-match — drift between them would cause subtle bugs
# in --migrate-to-plugin (which reads via parse_manifest.py from
# plugin-local) vs legacy upgrade.sh (which reads from .claude/).
# Removed when .claude/manifest.yml is deleted in v0.21.0 / 2026-06-09.
check_manifest_byte_match() {
    section "Check 28: Manifest dual-source byte-match (transition artifact)"

    local legacy="./.claude/manifest.yml"
    local canonical="./plugins/mycelium/manifest.yml"

    if [ ! -f "$canonical" ]; then
        fail "Canonical manifest missing: $canonical"
        return
    fi

    if [ ! -f "$legacy" ]; then
        info "Legacy manifest absent — Check 28 N/A (transition complete; remove this check)"
        return
    fi

    if cmp -s "$legacy" "$canonical"; then
        pass "Manifest dual-source byte-matches (legacy + canonical agree)"
    else
        fail "Manifest dual-source DRIFT: $legacy != $canonical. Sync the legacy copy from canonical, or run: cp $canonical $legacy"
    fi
}

# ============================================================
# CHECK 35: tests/bash/fixtures — no empty directories
# ============================================================
# Empty fixture directories cause silent test-skip failures in CI: git does
# not track empty dirs, so a locally-passing test setup ships as a CI failure
# ("fixture not found"). Recurred twice in 24h on 2026-05-24 (v0.26.4
# check_12/check_14 empty dirs; v0.26.7 check_27 empty dir + 17 .gitkeep
# defensive sweep). This check makes the failure mode loud at validation
# time instead of at CI time. Every fixture dir must either contain a real
# fixture file OR a .gitkeep placeholder.
check_no_empty_fixture_dirs() {
    section "Check 35: tests/bash/fixtures — no empty directories"

    local fixtures_dir="tests/bash/fixtures"
    if [ ! -d "$fixtures_dir" ]; then
        info "tests/bash/fixtures absent — Check 35 N/A"
        return
    fi

    local empty_dirs
    empty_dirs=$(find "$fixtures_dir" -type d -empty 2>/dev/null | sort)

    if [ -z "$empty_dirs" ]; then
        pass "Check 35: 0 empty directories under $fixtures_dir"
    else
        local n
        n=$(echo "$empty_dirs" | wc -l | tr -d ' ')
        fail "Check 35: ${n} empty directory(ies) under $fixtures_dir (git will silently omit these; CI will fail with fixture-not-found):"
        while IFS= read -r d; do
            echo "    - $d"
        done <<< "$empty_dirs"
        echo "    Fix: populate with a fixture file, OR add '.gitkeep' if the empty state IS the fixture (e.g., 'directory missing' negative test)."
    fi
}

# ============================================================
# CHECK 36: CLAUDE.md line-count ceiling (dispatcher-size ratchet)
# ============================================================
# CLAUDE.md is always loaded into the agent's context, so its size is a
# standing cost on every session. The /optimize-claudemd target is ~150 lines:
# CLAUDE.md should be a DISPATCHER (rule + grep vocabulary + pointer), with
# rationale / research citations / incident history relocated to sub-files.
#
# This check enforces a RATCHET, not a hard 150:
#   - FAIL if line count exceeds CLAUDEMD_MAX_LINES (the ceiling). The ceiling
#     starts at the current size so existing debt does not block commits, but
#     the file cannot GROW past it. The rule: the ceiling only ever ratchets
#     DOWN (lower it as the dispatcher refactor lands); never raise it to pass.
#   - WARN if line count is within the ceiling but over CLAUDEMD_TARGET_LINES
#     (the ~150 goal) — a visible, non-blocking reminder to keep trimming.
#   - PASS at or under the target.
#
# Both bounds are env-overridable so the G-V12 fixture test can exercise all
# three tiers with tiny fixtures (see tests/bash/test_check_36.sh).
#
# Graduated 2026-05-30 (v0.31.8) — maintainer-directed, after CLAUDE.md drifted
# to 248 lines (~100 over target) with no mechanical guard against regrowth.
# Ratcheted DOWN to 200 on 2026-05-30 (v0.31.9) after the dispatcher relocation
# (Communication-Rules rationale → harness/communication-rules.md; Diamond/
# Self-Learning/Canvas-history detail → pointers). ~200 is the behavioral floor:
# the remaining lines are always-on rules + the L0–L5 scales table, which must
# stay resident and cannot move to a load-on-demand sub-file. The 150 target is
# retained as the aspirational marker (WARN band), not a reachable floor here.
check_claudemd_size_ceiling() {
    section "Check 36: CLAUDE.md line-count ceiling (dispatcher-size ratchet)"

    if [ ! -f CLAUDE.md ]; then
        info "CLAUDE.md absent — Check 36 N/A"
        return
    fi

    local ceiling target lines
    ceiling="${CLAUDEMD_MAX_LINES:-200}"
    target="${CLAUDEMD_TARGET_LINES:-150}"
    lines=$(wc -l < CLAUDE.md | tr -d ' ')

    if [ "$lines" -gt "$ceiling" ]; then
        fail "Check 36: CLAUDE.md is ${lines} lines, over the ${ceiling}-line ceiling. CLAUDE.md is a dispatcher — relocate rationale/research/history to a sub-file and leave a pointer (run /optimize-claudemd). The ceiling ratchets DOWN only; never raise it to pass."
    elif [ "$lines" -gt "$target" ]; then
        warn "Check 36: CLAUDE.md is ${lines} lines — within the ${ceiling}-line ceiling but over the ${target}-line target. Trend toward ${target} via the dispatcher pattern, and lower the ceiling as you do."
    else
        pass "Check 36: CLAUDE.md is ${lines} lines (≤ ${target}-line target)."
    fi
}

# ============================================================
# CHECK 37: G-V12 meta-check — every CI check ships a fixture test
# ============================================================
# G-V12 ("every check that flags a problem ships with a test demonstrating it
# does") was enforced only by convention + the Pre-Ship checklist. It drifted:
# the 2026-05-30 deep-dive audit found Check 16 and Check 17 had no
# tests/bash/test_check_<N>.sh. This meta-check makes the gap mechanical —
# it cross-references every `section "Check N:` declaration against the
# tests/bash/ fixture files and FAILs on any uncovered check. Self-applying:
# Check 37 itself ships tests/bash/test_check_37.sh.
#
# Combined/deprecated test files (e.g. test_check_2_3_4_deprecated.sh) count as
# coverage for every number in their filename. The EXEMPT list is for checks
# that are structurally un-fixturable; keep it empty unless truly necessary and
# document the reason inline — an exemption is a coverage hole by another name.
check_gv12_test_coverage() {
    section "Check 37: G-V12 — every CI check ships a fixture test"

    local checks_file="tests/validate-template.sh"
    local tests_dir="tests/bash"
    if [ ! -f "$checks_file" ] || [ ! -d "$tests_dir" ]; then
        info "Check 37: validator or tests/bash missing in cwd — N/A"
        return
    fi

    local required covered
    required=$(grep -oE 'section "Check [0-9]+' "$checks_file" | grep -oE '[0-9]+' | sort -un)
    covered=$(for f in "$tests_dir"/test_check_*.sh; do
        [ -f "$f" ] || continue
        basename "$f" | grep -oE '[0-9]+'
    done | sort -un)

    # Space-separated list of check numbers exempt from the fixture-test rule.
    # Currently empty by design.
    local exempt=""

    local missing=() n
    for n in $required; do
        case " $exempt " in *" $n "*) continue ;; esac
        if ! echo "$covered" | grep -qx "$n"; then
            missing+=("$n")
        fi
    done

    local total
    total=$(echo "$required" | wc -w | tr -d ' ')
    if [ "${#missing[@]}" -eq 0 ]; then
        pass "Check 37: all ${total} declared checks have a tests/bash fixture test (G-V12 holds)"
    else
        fail "Check 37: checks missing a tests/bash/test_check_<N>.sh: ${missing[*]}. Add the fixture test per tests/bash/README.md (G-V12)."
    fi
}

# ------------------------------------------------------------
# Check 38: cycle_class discipline — product-leaf cycles must carry non-zero ICE.
#
# Closes the dark-cell leak surfaced by /mycelium:framework-health on the
# roadmap dogfood repo 2026-06-02: all 6 cycles in cycle-history.yml carried
# ice_score: {i:0, c:0, e:0} with a prose comment ("not formally scored —
# emerged mid-session" / "narrative-prediction work" / etc.), making the
# confidence-calibration dimension permanently unmeasurable.
#
# The fix surfaces two intents in the schema: meta-dogfood and observation
# cycles legitimately have no ICE (no tradeoff was scored); product-leaf
# cycles must — they shipped an OST solution leaf, and ICE is the
# pre-shipment prediction whose calibration is the whole point.
#
# Detection: walk cycle-history.yml, find entries with cycle_class: product-leaf
# and predicted.ice_score.total == 0. Either the cycle is mis-classed
# (should be meta-dogfood/observation) or /mycelium:ice-score was skipped
# at opp-selection — see skills/ice-score/SKILL.md gate.
check_cycle_class_ice_required() {
    section "Check 38: product-leaf cycles must carry non-zero ICE"

    local cycle_file=".claude/canvas/cycle-history.yml"
    if [ ! -f "$cycle_file" ]; then
        info "Check 38: $cycle_file absent — N/A"
        return
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        warn "Check 38: python3 unavailable; skipping cycle_class audit"
        return
    fi

    local result
    result=$(python3 - "$cycle_file" <<'PY'
import sys
try:
    import yaml
except ImportError:
    print("SKIP: PyYAML unavailable")
    sys.exit(0)

with open(sys.argv[1]) as f:
    try:
        doc = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"PARSE_ERROR: {e}")
        sys.exit(0)

cycles = doc.get("cycles") or []
violations = []
unclassed = []
for c in cycles:
    if not isinstance(c, dict):
        continue
    cid = c.get("cycle_id", "<no-id>")
    klass = c.get("cycle_class")
    if klass is None:
        unclassed.append(cid)
        continue
    if klass != "product-leaf":
        continue
    ice = (c.get("predicted") or {}).get("ice_score") or {}
    total = ice.get("total", 0) or 0
    try:
        total_i = int(total)
    except (TypeError, ValueError):
        total_i = 0
    if total_i == 0:
        violations.append(cid)

if violations:
    print(f"FAIL: {','.join(violations)}")
elif unclassed:
    print(f"WARN: {','.join(unclassed)}")
else:
    print("OK")
PY
)

    case "$result" in
        OK)
            pass "Check 38: all product-leaf cycles carry non-zero ICE"
            ;;
        SKIP:*)
            warn "Check 38: ${result#SKIP: }"
            ;;
        PARSE_ERROR:*)
            warn "Check 38: ${result#PARSE_ERROR: }"
            ;;
        WARN:*)
            warn "Check 38: cycles missing cycle_class (treat as legacy; add classification): ${result#WARN: }. See engine/cycle-learning.md#cycle-class."
            ;;
        FAIL:*)
            fail "Check 38: product-leaf cycles with zero ICE: ${result#FAIL: }. Either re-class as meta-dogfood/observation (no tradeoff was scored) OR backfill ICE via /mycelium:ice-score with reconstructed_post_hoc: true. See engine/cycle-learning.md#cycle-class."
            ;;
        *)
            warn "Check 38: unexpected result: $result"
            ;;
    esac
}

# ------------------------------------------------------------
# Check 39: rendering-spec docs carry STRICT or illustrative marker.
#
# Promotes Rule 4 of engine/consistency-check-spec.md from spec to mechanism.
# Closes the doc-vs-rendering subclass of the
# documented-rule-diverges-from-enforcement cluster. Historical instance:
# wayfinding.md pre-0.16.4 (instance 7 in the cluster log) — the doc showed
# a template, the agent improvised on rendering, the fix tightened the doc
# with a STRICT marker. Without a check, the next rendering-spec doc that
# ships can drop the marker silently and the same failure surface returns.
#
# In-scope detection: engine docs that contain BOTH "Template" AND
# "Render"/"render" anywhere in the body. Either a STRICT-marker line
# ("STRICT — reproduce…") OR an explicit "illustrative" disclaimer
# satisfies the check. Out-of-scope docs (general engine docs that
# happen to mention either word) are not flagged.
#
# Promotion provenance: framework-health 2026-06-02 (roadmap dogfood).
# Single-rule, single-subclass graduation; the broader cluster remains
# at spec status per consistency-check-spec.md Promotion bar.
check_rendering_spec_strict_marker() {
    section "Check 39: rendering-spec docs carry STRICT or illustrative marker (Rule 4)"

    local engine_dir="plugins/mycelium/engine"
    if [ ! -d "$engine_dir" ]; then
        engine_dir=".claude/engine"
    fi
    if [ ! -d "$engine_dir" ]; then
        info "Check 39: engine dir absent — N/A"
        return
    fi

    local violations=() doc in_scope_count=0
    while IFS= read -r doc; do
        if grep -q "Template" "$doc" 2>/dev/null && grep -qE "(Render|render)" "$doc" 2>/dev/null; then
            in_scope_count=$((in_scope_count + 1))
            if ! grep -qE "STRICT|illustrative" "$doc" 2>/dev/null; then
                violations+=("$doc")
            fi
        fi
    done < <(find "$engine_dir" -maxdepth 2 -name "*.md" -type f 2>/dev/null)

    if [ "$in_scope_count" -eq 0 ]; then
        info "Check 39: no rendering-spec docs in scope — N/A"
        return
    fi

    if [ "${#violations[@]}" -eq 0 ]; then
        pass "Check 39: all ${in_scope_count} rendering-spec doc(s) carry STRICT or illustrative marker (Rule 4 of consistency-check-spec.md)"
    else
        fail "Check 39: rendering-spec docs missing STRICT/illustrative marker: ${violations[*]}. Add 'STRICT — reproduce literally' OR a documented 'illustrative' disclaimer per engine/consistency-check-spec.md Rule 4."
    fi
}

# ============================================================
# CHECK 42: Postflight Verify-After-Write preamble on multi-field-canvas-writing skills
# ============================================================
#
# Anti-pattern #7 Stage 2a sub-shape (6) graduation (v0.39.18).
# Symmetric to Check 41 (Read-before-Recommend Preflight) and Check 31
# (Read-before-Write Preflight). Three checks now enforce the
# read/write/verify discipline on the corresponding skill surfaces.
#
# v0.39.18 shipped narrow (2 skills: dora-check, xai-check — dora-check
# produced AP#7 instance #18). v0.44.0 EXPANDS the enforced surface to the
# full mechanically-identified population: every skill whose SKILL.md carries
# a MANDATORY multi-field canvas write (grep `MANDATORY` ∧ a `…canvas/*.yml`
# write directive). The trigger was AP#7 instance #19 (2026-06-05) firing in
# /retrospective — a multi-field-canvas-writing skill the v0.39.18 surface did
# NOT cover. The original-author Stage 2b candidates (threat-model,
# regulatory-review, service-check, canvas-update) remain open: they do not
# currently carry a MANDATORY multi-field canvas write and are not yet in scope.
check_postflight_verify_after_write_preamble() {
    section "Check 42: Postflight Verify-After-Write preamble on multi-field-canvas-writing skills (anti-pattern #7 Stage 2a v0.39.18; surface expanded v0.44.0)"

    local skills_dir="$SKILLS_DIR"
    if [ ! -d "$skills_dir" ]; then
        info "Skills dir absent — Check 42 N/A"
        return
    fi

    local marker="## Postflight: Verify-After-Write"
    # v0.39.18: dora-check, xai-check. v0.44.0 +retrospective (#19) + the rest of
    # the MANDATORY multi-field-canvas-write population (cynefin-classify,
    # canvas-health, launch-tier, wardley-map, team-shape).
    local surface_skills=("dora-check" "xai-check" "retrospective" "canvas-health" "cynefin-classify" "launch-tier" "wardley-map" "team-shape")
    local missing_count=0
    local missing_list=""
    local checked=0

    for skill in "${surface_skills[@]}"; do
        local skill_path="$skills_dir/$skill/SKILL.md"
        if [ ! -f "$skill_path" ]; then
            continue
        fi
        checked=$((checked + 1))
        if ! grep -q "$marker" "$skill_path"; then
            missing_count=$((missing_count + 1))
            missing_list="${missing_list}"$'\n'"  - $skill/SKILL.md"
        fi
    done

    if [ "$missing_count" -eq 0 ]; then
        pass "Check 42: all $checked multi-field-canvas-writing skills carry the Postflight Verify-After-Write block"
    else
        fail "Check 42: $missing_count multi-field-canvas-writing skill(s) missing Postflight Verify-After-Write block:${missing_list}. Add the '$marker' section per anti-pattern #7 Stage 2a v0.39.18 graduation."
    fi
}

# ============================================================
# CHECK 41: Read-before-Recommend preamble on gate-narrating skills
# ============================================================
#
# Anti-pattern #7 conversational/gate-narration sub-shape graduation
# (v0.39.16). The Communication Rule lives in CLAUDE.md; this check
# enforces that the two gate-narrating skills founder named in
# corrections.md L52 (2026-06-02 cluster-instances.md instance #17)
# carry the canonical Preflight block, parallel to Check 31's
# Read-before-Write enforcement on canvas-writing skills.
#
# Scope is deliberately narrow this graduation: diamond-assess and
# diamond-progress only. Sub-shapes deferred to next graduation
# (cross-repo state, consent-state, cross-file completeness) need
# different surfaces — hooks or registry diffs, not skill preambles.
check_read_before_recommend_preamble() {
    section "Check 41: Read-before-Recommend preamble on gate-narrating skills (anti-pattern #7 graduation v0.39.16)"

    local skills_dir="$SKILLS_DIR"
    if [ ! -d "$skills_dir" ]; then
        info "Skills dir absent — Check 41 N/A"
        return
    fi

    local marker="## Preflight: Read-before-Recommend"
    local surface_skills=("diamond-assess" "diamond-progress")
    local missing_count=0
    local missing_list=""
    local checked=0

    for skill in "${surface_skills[@]}"; do
        local skill_path="$skills_dir/$skill/SKILL.md"
        if [ ! -f "$skill_path" ]; then
            continue
        fi
        checked=$((checked + 1))
        if ! grep -q "$marker" "$skill_path"; then
            missing_count=$((missing_count + 1))
            missing_list="${missing_list}"$'\n'"  - $skill/SKILL.md"
        fi
    done

    if [ "$missing_count" -eq 0 ]; then
        pass "Check 41: all $checked gate-narrating skills carry the Read-before-Recommend Preflight block"
    else
        fail "Check 41: $missing_count gate-narrating skill(s) missing Read-before-Recommend Preflight block:${missing_list}. Add the '$marker' section per anti-pattern #7 v0.39.16 graduation."
    fi
}

# ============================================================
# CHECK 40: sync_derived.py --check — mechanically-derived tokens in sync
# ============================================================
#
# Wraps `plugins/mycelium/scripts/sync_derived.py --check` as a pre-push gate.
# The script already exists and is idempotent; it just wasn't being called
# anywhere automatically, so version + skill-count tokens in docs/ai-system-card.md
# (and four other files) routinely drifted across framework releases.
#
# Worked failure (2026-06-05): docs/ai-system-card.md §1 Version sat at 0.38.0
# across six framework bumps (v0.38.1 → v0.39.13) without anyone running
# sync_derived.py. Caught by the operator asking "why is the system card
# stale" during a /mycelium:xai-check Stage 4 re-audit. The system card is
# the published transparency artifact; a stale version on it is a live
# honesty problem, not just untidy (per sync_derived.py's own header comment).
#
# This check gates that drift pre-push. Remediation when it fails:
# `python3 plugins/mycelium/scripts/sync_derived.py` (no --check) refreshes
# the tokens. Substantive content (audit date, eval status, last-updated
# stamp) is not in sync_derived's scope — that's covered by canvas-health
# 9b sub-check for system-card content freshness.
check_sync_derived_drift() {
    section "Check 40: docs/ai-system-card.md + cross-file mechanical tokens in sync (sync_derived.py --check)"

    local sync_script="plugins/mycelium/scripts/sync_derived.py"
    if [ ! -f "$sync_script" ]; then
        info "Check 40: $sync_script absent — N/A"
        return
    fi

    local output rc
    output=$(python3 "$sync_script" --check 2>&1)
    rc=$?

    if [ "$rc" -eq 0 ]; then
        pass "Check 40: mechanical tokens in sync — $(echo "$output" | head -1)"
    else
        fail "Check 40: sync_derived --check reports drift. Remediation: \`python3 $sync_script\` (no --check) refreshes tokens. $output"
    fi
}

# ============================================================
# CHECK 43: Identifier-exposure declaration on render-fleet skills
# ============================================================
#
# Render-fleet specialists (skill name ends in `-render`) and the
# dispatcher (skill name == `render`) emit canvas/state into human-
# audience artifacts. The consent-state-change-skip cluster (anti-
# pattern #7 sub-shape, instance #15, 2026-06-02) demonstrated that
# unchecked identifier rendering becomes a privacy incident. Per
# `engine/render-conventions.md#hard-rule-consent--privacy-gate`,
# every render skill MUST declare `identifier_exposure: YES|NONE|MIXED`
# in frontmatter AND carry a `## Identifier exposure` body section.
#
# This check enforces frontmatter presence + value validity. Body-
# section consistency is prose discipline reviewed at promotion.
check_render_identifier_exposure_declaration() {
    section "Check 43: Identifier-exposure declaration on render-fleet skills (engine/render-conventions.md HARD RULE)"

    local skills_dir="$SKILLS_DIR"
    if [ ! -d "$skills_dir" ]; then
        info "Skills dir absent — Check 43 N/A"
        return
    fi

    local missing_frontmatter_count=0
    local missing_frontmatter_list=""
    local missing_body_count=0
    local missing_body_list=""
    local invalid_value_count=0
    local invalid_value_list=""
    local checked=0

    # Detection: name pattern `*-render` OR exactly `render`.
    # Walk every subdirectory in the skills tree.
    for skill_dir in "$skills_dir"/*/; do
        local skill_name
        skill_name="$(basename "$skill_dir")"
        case "$skill_name" in
            *-render|render)
                ;;
            *)
                continue
                ;;
        esac

        local skill_path="$skill_dir/SKILL.md"
        if [ ! -f "$skill_path" ]; then
            continue
        fi
        checked=$((checked + 1))

        # Frontmatter check: look for `identifier_exposure: "YES"|"NONE"|"MIXED"`
        # in the metadata block. Tolerate quoted or unquoted values.
        local value
        value="$(grep -E "^[[:space:]]*identifier_exposure:[[:space:]]*\"?(YES|NONE|MIXED)\"?[[:space:]]*$" "$skill_path" | head -1 || true)"

        if [ -z "$value" ]; then
            # Either missing entirely, or invalid value.
            if grep -qE "^[[:space:]]*identifier_exposure:" "$skill_path"; then
                invalid_value_count=$((invalid_value_count + 1))
                invalid_value_list="${invalid_value_list}"$'\n'"  - $skill_name/SKILL.md"
            else
                missing_frontmatter_count=$((missing_frontmatter_count + 1))
                missing_frontmatter_list="${missing_frontmatter_list}"$'\n'"  - $skill_name/SKILL.md"
            fi
        fi

        # Body section check: `## Identifier exposure`
        if ! grep -qE "^## Identifier exposure" "$skill_path"; then
            missing_body_count=$((missing_body_count + 1))
            missing_body_list="${missing_body_list}"$'\n'"  - $skill_name/SKILL.md"
        fi
    done

    local total_failures=$((missing_frontmatter_count + missing_body_count + invalid_value_count))

    if [ "$total_failures" -eq 0 ]; then
        pass "Check 43: all $checked render-fleet skill(s) carry identifier_exposure frontmatter + ## Identifier exposure body section"
        return
    fi

    local msg="Check 43: render-fleet identifier-exposure declaration failures:"
    if [ "$missing_frontmatter_count" -gt 0 ]; then
        msg="${msg}"$'\n'"  ${missing_frontmatter_count} skill(s) missing 'identifier_exposure:' frontmatter:${missing_frontmatter_list}"
    fi
    if [ "$invalid_value_count" -gt 0 ]; then
        msg="${msg}"$'\n'"  ${invalid_value_count} skill(s) with invalid identifier_exposure value (must be YES, NONE, or MIXED):${invalid_value_list}"
    fi
    if [ "$missing_body_count" -gt 0 ]; then
        msg="${msg}"$'\n'"  ${missing_body_count} skill(s) missing '## Identifier exposure' body section:${missing_body_list}"
    fi
    msg="${msg}"$'\n'"  See engine/render-conventions.md HARD RULE: Consent + privacy gate."
    fail "$msg"
}

# ============================================================
# CHECK 44: Hooks registration — script existence + cross-surface parity
# ============================================================
#
# Per-rule promotion of consistency-check-spec.md Rule 5 (hook-claim
# cross-reference), narrowed to its mechanizable core: (a) every hook
# script a hooks*.json registers must exist on disk; (b) every
# enforcement hook registered in hooks.json (Claude Code, the reference
# surface) must also be registered in hooks.codex.json and
# hooks.cursor.json, unless the divergence is in the documented
# allowlist below.
#
# Historical instance covered: 2026-06-12 gap analysis found
# autonomous-evidence-guard.sh registered in hooks.json (v0.42.0) but
# absent from BOTH alternate-surface JSONs — Codex/Cursor users had
# zero autonomous evidence-integrity enforcement for the exact
# fabrication class the guard exists to block (decision-log
# 2026-06-12). This check makes that divergence class mechanical.
#
# Documented divergence allowlist (runtime differences, not drift):
#   - reflexion-gate.sh missing from codex: Codex has no native
#     PostToolUseFailure; codex-postfailure-shim.sh wraps it (see
#     hooks.codex.json _description).
#   - codex-postfailure-shim.sh present only on codex: it IS the
#     divergence mechanism.
check_hooks_registration_parity() {
    section "Check 44: hooks registration — script existence + cross-surface parity (Rule 5 per-rule promotion)"

    local hooks_dir="plugins/mycelium/hooks"
    if [ ! -d "$hooks_dir" ]; then
        info "Hooks dir absent — Check 44 N/A"
        return
    fi

    local violations
    violations=$(python3 - "$hooks_dir" <<'PYEOF'
import json, re, sys
from pathlib import Path

hooks_dir = Path(sys.argv[1])
SURFACES = ["hooks.json", "hooks.codex.json", "hooks.cursor.json"]
# Divergences that are documented runtime differences, not drift.
ALLOW_MISSING = {
    "hooks.codex.json": {"reflexion-gate.sh"},   # no native PostToolUseFailure; shim wraps it
    "hooks.cursor.json": set(),
}
ALLOW_EXTRA = {
    "hooks.codex.json": {"codex-postfailure-shim.sh"},  # the divergence mechanism itself
    "hooks.cursor.json": set(),
}
script_re = re.compile(r"/hooks/([A-Za-z0-9._-]+\.sh)")

def registered(path: Path) -> set[str]:
    try:
        text = path.read_text()
        json.loads(text)  # must be valid JSON
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{path.name}: unreadable or invalid JSON ({exc})")
        return set()
    return set(script_re.findall(text))

sets = {}
for name in SURFACES:
    p = hooks_dir / name
    if not p.exists():
        print(f"{name}: file missing from {hooks_dir}")
        continue
    scripts = registered(p)
    sets[name] = scripts
    for s in sorted(scripts):
        if not (hooks_dir / s).exists():
            print(f"{name} registers {s} but {hooks_dir}/{s} does not exist")

baseline = sets.get("hooks.json")
if baseline:
    for alt in ("hooks.codex.json", "hooks.cursor.json"):
        if alt not in sets:
            continue
        missing = baseline - sets[alt] - ALLOW_MISSING[alt]
        extra = sets[alt] - baseline - ALLOW_EXTRA[alt]
        for s in sorted(missing):
            print(f"{alt} missing {s} (registered in hooks.json; not in divergence allowlist)")
        for s in sorted(extra):
            print(f"{alt} registers {s} not in hooks.json (undocumented extra)")
PYEOF
)

    if [ -z "$violations" ]; then
        local n
        n=$(grep -c "" <<<"$(python3 -c "
import re, pathlib
t = pathlib.Path('$hooks_dir/hooks.json').read_text()
print('\n'.join(sorted(set(re.findall(r'/hooks/([A-Za-z0-9._-]+\.sh)', t)))))
")")
        pass "Check 44: all 3 hooks JSONs valid; every registered script exists; cross-surface parity holds ($n hooks on the reference surface)"
    else
        fail "Check 44: hooks registration violations:"$'\n'"$(echo "$violations" | sed 's/^/  - /')"$'\n'"  Fix the registration or add a documented divergence to the Check 44 allowlist (with the runtime reason)."
    fi
}

# ============================================================
# CHECK 45: Chat-UX axiom markers on graduated output templates
# ============================================================
#
# Graduation of the /framework-health 4e chat-UX audit per its stated path:
# "if the same skill is flagged across two assessments, promote to a
# mechanical tests/bash check." Trigger fired 2026-06-12 (assessments
# 2026-06-05 + 2026-06-12, temporally independent, templates unedited
# between): Hick's-Law set re-flagged 3/3, Von Restorff set 2/3
# (canvas-health self-resolved via its verdict line).
#
# Enforcement is marker-presence (same pattern as Checks 41/42): each
# graduated skill's SKILL.md must carry the axiom lead-in its template
# fix introduced. New skills are NOT in scope — 4e keeps auditing the
# full surface heuristically; a skill joins this list only by the
# two-assessment graduation path.
check_chat_ux_axiom_markers() {
    section "Check 45: chat-UX axiom markers on graduated output templates (4e graduation 2026-06-12)"

    local skills_dir="$SKILLS_DIR"
    if [ ! -d "$skills_dir" ]; then
        info "Skills dir absent — Check 45 N/A"
        return
    fi

    # skill:marker pairs. Hick set leads with a recommendation; Von Restorff
    # set leads with a verdict.
    local pairs=(
        "canvas-update:Lead with the recommendation"
        "ost-builder:Lead with the recommendation"
        "ice-score:Lead with the recommendation"
        "bvssh-check:Lead with the verdict"
        "dora-check:Lead with the verdict"
    )
    local missing_count=0
    local missing_list=""
    local checked=0

    for pair in "${pairs[@]}"; do
        local skill="${pair%%:*}"
        local marker="${pair#*:}"
        local skill_path="$skills_dir/$skill/SKILL.md"
        if [ ! -f "$skill_path" ]; then
            continue
        fi
        checked=$((checked + 1))
        if ! grep -q "$marker" "$skill_path"; then
            missing_count=$((missing_count + 1))
            missing_list="${missing_list}"$'\n'"  - $skill/SKILL.md (expected: \"$marker\")"
        fi
    done

    if [ "$missing_count" -eq 0 ]; then
        pass "Check 45: all $checked graduated skill(s) carry their chat-UX axiom marker (Hick recommend-lead / Von Restorff verdict-lead)"
    else
        fail "Check 45: $missing_count graduated skill(s) missing chat-UX axiom marker:${missing_list}. Per harness/design-principles.md + the 4e graduation path (framework-health 2026-06-05 + 2026-06-12)."
    fi
}

# ============================================================
# CHECK 46: install-command marketplace ref is canonical
# ============================================================
# Graduation of the recurring "documented rule diverges from enforcement" /
# doc-drift class (2026-07-04 Show-HN readiness review). 53 skill SKILL.md
# frontmatter notes shipped the slash marketplace ref (mycelium@haabe/mycelium)
# while the marketplace is named haabe-mycelium (dash) in
# .claude-plugin/marketplace.json — the slash form resolves to a nonexistent
# marketplace and fails on paste, and it hid in per-skill frontmatter while the
# user-facing install docs were correct. This check asserts every
# `plugin install mycelium@<ref>` (across *.md + *.json) uses the marketplace
# `name` from the manifest. Historical docs/changelog.md and test fixtures are
# exempt (they legitimately quote non-canonical refs while describing the bug).
check_install_command_canonical() {
    section "Check 46: install-command marketplace ref is canonical"

    local mkt_file=".claude-plugin/marketplace.json"
    if [ ! -f "$mkt_file" ]; then
        info "Check 46: $mkt_file absent — N/A"
        return
    fi

    local mkt
    mkt=$(grep -m1 '"name"' "$mkt_file" | sed 's/.*"name"[[:space:]]*:[[:space:]]*"//' | sed 's/".*//')
    if [ -z "$mkt" ]; then
        warn "Check 46: could not read marketplace name from $mkt_file"
        return
    fi

    local offenders
    # Ref char class excludes '.' and '/' deliberately: a marketplace name is
    # [A-Za-z0-9_-], so stopping at '.' lets the correct ref be recognised even
    # when a sentence-ending period follows it in frontmatter, and stopping at
    # '/' truncates the bad slash ref (haabe/mycelium -> "haabe") so it still
    # fails the canonical-name match.
    offenders=$(grep -rEn "plugin install mycelium@[A-Za-z0-9_-]+" . \
        --include='*.md' --include='*.json' \
        --exclude-dir=tests --exclude-dir=.git 2>/dev/null \
        | grep -v "changelog.md:" \
        | grep -vE "plugin install mycelium@${mkt}([^A-Za-z0-9_-]|$)" || true)

    if [ -z "$offenders" ]; then
        pass "Check 46: all 'plugin install mycelium@' refs use marketplace name '$mkt'"
    else
        local n
        n=$(printf '%s\n' "$offenders" | grep -c .)
        fail "Check 46: $n install-command ref(s) do not use marketplace name '$mkt' from $mkt_file (canonical: mycelium@$mkt). First: $(printf '%s\n' "$offenders" | head -1)"
    fi
}

# ============================================================
# CHECK 47: plugin-form operating contract is wired
# ============================================================
# Dogfood-driven (2026-07-25). The v0.20.0 plugin migration left the operating
# manual (Communication Rules + Mandatory Protocols) at repo-root CLAUDE.md,
# OUTSIDE plugins/mycelium/ — so it was never packaged, and the legacy degit
# templating that delivered it to each project was removed in 0.20.14 with
# nothing to replace it. Plugin-form consumers ran without the always-on rules
# for ~2.5 months; the framework repo never noticed because its own sessions
# load root CLAUDE.md natively. v0.58.0 fix: rules extracted to a single
# canonical engine/agent-operating-contract.md, injected by session-start.sh,
# referenced (not restated) by CLAUDE.md. This check keeps that wiring intact.
check_operating_contract_wiring() {
    section "Check 47: plugin-form operating contract is wired (present + injected + referenced + plugin-path-clean)"

    local contract="plugins/mycelium/engine/agent-operating-contract.md"
    local hook="plugins/mycelium/hooks/session-start.sh"
    local claudemd="CLAUDE.md"

    if [ ! -f "$contract" ]; then
        fail "Check 47: operating contract missing at $contract — plugin-form sessions get no always-on rules (regression of the v0.20.0 migration gap)."
        return
    fi
    if [ ! -f "$hook" ] || ! grep -q "agent-operating-contract" "$hook"; then
        fail "Check 47: SessionStart hook ($hook) does not inject agent-operating-contract — the contract is packaged but never reaches a session."
        return
    fi
    if [ ! -f "$claudemd" ] || ! grep -q "agent-operating-contract" "$claudemd"; then
        fail "Check 47: $claudemd does not reference agent-operating-contract — the extract-and-reference wiring is broken (rules may have drifted back inline)."
        return
    fi
    # Framework references in the contract MUST resolve via \${CLAUDE_PLUGIN_ROOT}
    # (or a logical name), never a legacy .claude/ framework path. Project-state
    # paths (.claude/canvas, .claude/memory, .claude/diamonds, decision-log) are
    # legitimately project-local and exempt.
    local legacy
    legacy=$(grep -nE '\.claude/(engine|harness/guardrails|harness/communication|harness/design|domains|skills|orchestration|jit-tooling)' "$contract" || true)
    if [ -n "$legacy" ]; then
        fail "Check 47: operating contract references legacy .claude/ FRAMEWORK paths (must resolve via \${CLAUDE_PLUGIN_ROOT} in plugin form). First: $(printf '%s\n' "$legacy" | head -1)"
        return
    fi

    pass "Check 47: operating contract present, injected by SessionStart, referenced by CLAUDE.md, and free of legacy framework paths"
}

# ============================================================
# Check 48: a release that CORRECTS an earlier release owes a corrections entry
# ============================================================
#
# Scope: THIS REPO ONLY, deliberately. The general principle ("when you fix
# your own recent fix, capture the learning") applies to everyone, but the
# detector assumes a versioned-release workflow with a dated changelog —
# which most Mycelium consumers, who build products rather than framework
# releases, do not have. Shipping a consumer-facing check that can never fire
# is how promise-registry rows accumulate. So this lives in the repo-only
# validator, not in plugins/mycelium/scripts/.
#
# Why it exists: v0.57.3 -> v0.57.4 -> v0.57.5 shipped a fix, an over-reach,
# and a retraction (v0.57.5's own heading reads "corrects v0.57.4"). The git
# history proved a mistake had been made and diagnosed — and no corrections.md
# entry was written in either repo. There is no judgement call left to skip
# once a changelog says a release corrects an earlier one, which is exactly
# what makes it mechanizable rather than another prose rule (the sibling
# lesson from v0.59.0's BVSSH orphan: prose in a notes field did not hold).
#
# Tier: WARN, per the framework's start-at-WARN convention for new checks
# (see scripts/check_gated_by.py header). Promote to FAIL once the backlog it
# surfaces is cleared and a full-history inventory is clean.
#
# Deliberately NARROW: "completes" is NOT a trigger. Completing earlier work
# is follow-through, not a mistake. Only corrects/reverts/supersedes count.
check_self_correcting_release_capture() {
    section "Check 48: releases that correct an earlier release carry a corrections entry (WARN tier)"

    local changelog="docs/changelog.md"
    local corrections=".claude/memory/corrections.md"
    local window_days=14

    if [ ! -f "$changelog" ]; then
        pass "Check 48: no $changelog — nothing to check"
        return
    fi
    if [ ! -f "$corrections" ]; then
        warn "Check 48: $changelog exists but $corrections does not — self-correcting releases cannot be captured anywhere."
        return
    fi

    local result
    result=$(python3 - "$changelog" "$corrections" "$window_days" <<'PY'
import re, sys
from datetime import date, timedelta

changelog, corrections, window = sys.argv[1], sys.argv[2], int(sys.argv[3])
text = open(changelog, encoding="utf-8", errors="replace").read()

# "corrects v0.57.4" / "reverts v0.1.2" / "supersedes v2.0.0".
# "completes" is intentionally excluded: follow-through is not a mistake.
TRIGGER = re.compile(r"\b(corrects|reverts|supersedes)\s+v\d+\.\d+\.\d+", re.I)
DATE = re.compile(r"\*\*(\d{4}-\d{2}-\d{2})\.")

# Section = a `## vX.Y.Z` heading plus everything up to the next one.
sections = re.split(r"(?m)^(?=## v\d+\.\d+\.\d+)", text)

entry_dates = set()
for m in re.finditer(r"(?m)^#{2,4}\s*(\d{4}-\d{2}-\d{2})", open(corrections, encoding="utf-8", errors="replace").read()):
    try:
        entry_dates.add(date.fromisoformat(m.group(1)))
    except ValueError:
        pass

uncaptured = []
for sec in sections:
    head = sec.split("\n", 1)[0]
    vm = re.match(r"## (v\d+\.\d+\.\d+)", head)
    if not vm or not TRIGGER.search(sec):
        continue
    dm = DATE.search(sec)
    if not dm:
        continue  # undated section: cannot evaluate a window, skip rather than guess
    try:
        rel = date.fromisoformat(dm.group(1))
    except ValueError:
        continue
    if not any(abs((d - rel).days) <= window for d in entry_dates):
        uncaptured.append(f"{vm.group(1)} ({rel.isoformat()})")

print("|".join(uncaptured))
PY
) || result=""

    if [ -z "$result" ]; then
        pass "Check 48: every self-correcting release has a corrections entry within ${window_days} days"
        return
    fi

    warn "Check 48: release(s) correcting an earlier release with no corrections.md entry within ${window_days} days: ${result//|/, }. The changelog already states a mistake was diagnosed; capture the learning in $corrections."
}

# ============================================================
# Check 49: receipts case frontmatter carries a canonical contributor
# ============================================================
#
# Scope: THIS REPO ONLY, same reasoning as Check 48. `docs/receipts/cases/` is
# Mycelium's own evidence base; consumers build products and have no receipts
# tree, so a shipped check could never fire for them.
#
# Why it exists: the `contributor` field had no canonical form and nothing
# validated it. Across 26 cases it drifted into 15 distinct spellings for 8
# people — the founder alone appeared 7 ways ("Håvard Bartnes (founder)",
# "(founder dogfood)", "(founder self-dogfood)", "(founder, dogfood-session
# catch)", ...). Every parenthetical carried real session context, so the
# values were informative and unusable at the same time: by-contributor.md
# silently under-listed contributors for two months because grouping on a
# free-text field cannot group. Normalised 2026-07-30 into `contributor` (the
# canonical join key to CONTRIBUTORS.md) plus optional `contributor_note` (the
# context). This check keeps it that way — a one-time cleanup with no guard is
# how SKILL_COUNT_FILES restaled twice.
# Check 50: theories.md claims must name artifacts that actually exist
# ---------------------------------------------------------------------------
# WHY THIS EXISTS (2026-08-02 theory-fidelity audit). theories.md is the file
# that says what the framework claims to implement, and every claim ends in an
# "Implemented as:" line naming gates, skills and files. NOTHING verified those
# names. The audit found gate 10 cited as "Delivery Health" — a section heading
# in jit-tooling/definition-of-done.md, not a gate; the gate is "DORA / Delivery
# Metrics". It also found a Wardley "NUDGE at Develop->Deliver" that exists
# nowhere in the tree.
#
# A theory claim naming an artifact that does not exist is worse than no claim:
# it reads as evidence the theory was operationalised, and docs/theories.md is
# the file a skeptical reader opens first.
#
# SCOPE, stated so the check is not mistaken for more than it is: this verifies
# that named artifacts EXIST. It cannot verify they behave as described — the
# same audit found adaptive-thresholds.md documenting a gate removed a month
# earlier, and a fabricated Hoskins element surviving in leaf-lifecycle.md, and
# neither is reachable by name-matching.
# Check 51: shipped-delivery evidence must have a delivery diamond
# ---------------------------------------------------------------------------
# WHY THIS EXISTS (dogfood 2026-08-02). The dogfood repo's dora-metrics.yml was
# fully populated and classified ELITE -- ~4 deploys/day, lead time in minutes,
# 0% strict change-failure rate -- with 11 launched cycles and 71 plugin
# releases. Its active.yml held two diamonds: L0 and L1. No L2, no L3, no L4.
#
# So the canvas said the project was stuck in discovery while the product
# shipped continuously at the top DORA band. "Stuck since May" was true of the
# canvas and false of the work, and it went unnoticed for months because nothing
# compared the two records.
#
# GENERALISES BEYOND DOGFOOD, which is the reason this is a check and not a note:
# every brownfield adoption produces this shape. /mycelium:adopt exists for "the
# code came first" -- a repo with years of delivery history, tests and CI gets a
# fresh canvas that can only speak about L0/L1. Without this check, the framework
# tells a shipping team it has not started.
#
# Direction matters: delivery evidence WITHOUT a delivery diamond is the defect.
# A delivery diamond without metrics yet is simply early, and passes.
check_scenario_legacy_model() {
    section "Check 53: scenarios migrated off the pre-2026-07-01 4-block model"

    if [ ! -f ".claude/canvas/scenarios.yml" ]; then
        info "Check 53: no .claude/canvas/scenarios.yml -- N/A"
        return
    fi

    local result rc
    set +e
    result=$(python3 - <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    # EXIT 3, NOT 0 (code review 2026-08-03). 0 is the PASS path in every bash
    # tail below, so a machine without PyYAML printed green for checks that never
    # opened a YAML file — including Check 53, whose entire reason for existing is
    # that unmigrated data sat green for a month.
    print("SKIP:pyyaml unavailable"); sys.exit(3)

try:
    doc = yaml.safe_load(Path(".claude/canvas/scenarios.yml").read_text()) or {}
except Exception as e:
    print(f"scenarios.yml did not parse: {e}"); sys.exit(1)

problems = []
checked = 0
for s in (doc.get("scenarios") or []):
    if not isinstance(s, dict):
        continue
    sid = s.get("id", "<no id>")
    status = str(s.get("status", "")).lower()
    if status == "archived":
        continue                      # history may keep the old shape
    # Counted AFTER the archived skip (code review 2026-08-03). Incrementing
    # first meant a project that archived all its scenarios got
    # "all 7 non-archived scenario(s) use Motivation/Persona/Simulation" while
    # zero were examined, and the N/A branch never fired because the counter
    # was non-zero. A pass over an empty live population, in the check written
    # because unmigrated data sat green.
    checked += 1
    if "motive" in s and "motivation" not in s:
        problems.append(
            f"{sid}: carries `motive` and no `motivation`. Rename it — "
            f"`motivation` is the Hoskins element; `motive` is the superseded name."
        )
    if "means" in s:
        problems.append(
            f"{sid}: carries `means`. \"Means\" is NOT a Hoskins element — the model "
            f"has THREE (Motivation, Persona, Simulation). How the persona meets "
            f"existing tools lives INSIDE the simulation; fold it to "
            f"`simulation.context` and delete the block."
        )

if not checked:
    # N/A, not a refusal. This differs deliberately from the empty-input rule the
    # fitness functions follow: there, an empty population means the check could
    # not SEE the thing it guards. Here it means the project has not written any
    # scenarios yet, which is a legitimate early state and the shipped template's
    # normal condition. Migration pressure applies to scenarios that exist.
    print("NA:scenarios.yml holds no scenarios yet")
    sys.exit(0)
if problems:
    print("\n".join(problems))
    sys.exit(1)
print(f"OK:{checked}")
sys.exit(0)
PY
)
    rc=$?
    set -e

    if [ "$rc" -eq 3 ]; then
        info "Check 53: ${result#SKIP:} -- SKIPPED, not passed"
    elif [ "$rc" -ne 0 ]; then
        fail "Check 53: scenarios still on the superseded 4-block model"
        echo "$result" | sed 's/^/    /'
        echo "    The schema TOLERATES these fields so historical files keep validating."
        echo "    Tolerance is not permission: without this check a corrected model can sit"
        echo "    unmigrated indefinitely, which is exactly what happened for a month."
    elif [ "${result#NA:}" != "$result" ]; then
        info "Check 53: ${result#NA:} -- N/A (nothing to migrate; not a pass over a population)"
    else
        pass "Check 53: all ${result#OK:} non-archived scenario(s) use Motivation/Persona/Simulation (archived ones may keep the legacy shape)"
    fi
}

check_canonical_field_location() {
    section "Check 52: one fact, one field name"

    if [ ! -d ".claude/canvas" ]; then
        info "Check 52: no .claude/canvas -- N/A"
        return
    fi

    local result rc
    set +e
    result=$(python3 - <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    # EXIT 3, NOT 0 (code review 2026-08-03). 0 is the PASS path in every bash
    # tail below, so a machine without PyYAML printed green for checks that never
    # opened a YAML file — including Check 53, whose entire reason for existing is
    # that unmigrated data sat green for a month.
    print("SKIP:pyyaml unavailable"); sys.exit(3)

PARSE_ERRORS = []


def load(p):
    q = Path(p)
    if not q.exists():
        return {}
    try:
        return yaml.safe_load(q.read_text()) or {}
    except Exception as e:
        # NOT `return {}` (code review 2026-08-03). Swallowing the error made an
        # unparseable canvas indistinguishable from an empty one, so a corrupt
        # file — the state MOST likely to hold the drift these checks hunt —
        # produced an unqualified PASS.
        PARSE_ERRORS.append(f"{p}: {e}")
        return {}

problems = []

# (1) confidence in two places on one opportunity.
for o in (load(".claude/canvas/opportunities.yml").get("opportunities") or []):
    if not isinstance(o, dict):
        continue
    top = o.get("confidence")
    prov = (o.get("provenance") or {}).get("confidence") if isinstance(o.get("provenance"), dict) else None
    if top is not None and prov is not None:
        agree = "agree" if top == prov else f"DISAGREE ({top} vs {prov})"
        problems.append(
            f"{o.get('id', o.get('name', '?'))}: confidence at BOTH top level and "
            f"provenance -- {agree}. provenance is schema-canonical (it is the required "
            f"object); the top-level field is an unvalidated extra property."
        )

# (2) two names for one completion date.
for t_ in (load(".claude/canvas/human-tasks.yml").get("pending_tasks") or []):
    if not isinstance(t_, dict):
        continue
    a, b = t_.get("closed_at"), t_.get("completed_at")
    if a is not None and b is not None and str(a) != str(b):
        problems.append(
            f"{t_.get('id', '?')}: closed_at={a!r} and completed_at={b!r} disagree. "
            f"They name the same event."
        )

# (3) two four_risks shapes in one file. Mixing is what breaks structured readers;
#     a project consistently on either shape is fine and is NOT flagged.
shapes = {}
for o in (load(".claude/canvas/opportunities.yml").get("opportunities") or []):
    for s in (o.get("solutions") or []) if isinstance(o, dict) else []:
        fr = s.get("four_risks") if isinstance(s, dict) else None
        if not isinstance(fr, dict):
            continue
        for dim, v in fr.items():
            if not isinstance(v, dict):
                continue
            if "risk_level" in v:
                shapes.setdefault("risk_level", []).append(f"{s.get('id')}.{dim}")
            elif "level" in v:
                shapes.setdefault("level", []).append(f"{s.get('id')}.{dim}")
if len(shapes) > 1:
    detail = "; ".join(f"{k}: {len(v)} dims e.g. {v[0]}" for k, v in sorted(shapes.items()))
    problems.append(
        f"four_risks uses TWO key shapes in one canvas -- {detail}. "
        f"Pick one so a structured reader sees every dimension."
    )

if PARSE_ERRORS:
    print("UNPARSEABLE (nothing was compared in these files):")
    print("\n".join("  " + e for e in PARSE_ERRORS))
if problems:
    print("\n".join(problems))
if PARSE_ERRORS or problems:
    sys.exit(1)
sys.exit(0)
PY
)
    rc=$?
    set -e

    if [ "$rc" -eq 3 ]; then
        info "Check 52: ${result#SKIP:} -- SKIPPED, not passed"
    elif [ "$rc" -ne 0 ]; then
        fail "Check 52: the same fact is recorded under two field names"
        echo "$result" | sed 's/^/    /'
        echo "    Readers disagree depending on which field they happen to read, and"
        echo "    schema validation cannot see it -- both fields are individually valid."
    else
        pass "Check 52: no duplicate-location fields (scope: opportunity confidence, task completion date, four_risks key shape -- NOT a general consistency check)"
    fi
}

check_delivery_diamond_reconciliation() {
    section "Check 51: shipped-delivery evidence has a delivery diamond"

    if [ ! -f ".claude/diamonds/active.yml" ]; then
        info "Check 51: no .claude/diamonds/active.yml -- N/A"
        return
    fi

    local result rc
    set +e
    result=$(python3 - <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    # EXIT 3, NOT 0 (code review 2026-08-03). 0 is the PASS path in every bash
    # tail below, so a machine without PyYAML printed green for checks that never
    # opened a YAML file — including Check 53, whose entire reason for existing is
    # that unmigrated data sat green for a month.
    print("SKIP:pyyaml unavailable"); sys.exit(3)

PARSE_ERRORS = []


def load(p):
    q = Path(p)
    if not q.exists():
        return {}
    try:
        return yaml.safe_load(q.read_text()) or {}
    except Exception as e:
        # NOT `return {}` (code review 2026-08-03). Swallowing the error made an
        # unparseable canvas indistinguishable from an empty one, so a corrupt
        # file — the state MOST likely to hold the drift these checks hunt —
        # produced an unqualified PASS.
        PARSE_ERRORS.append(f"{p}: {e}")
        return {}

diamonds = load(".claude/diamonds/active.yml").get("active_diamonds") or []
delivery_scales = {"L4", "L5"}
have = [d.get("id") for d in diamonds
        if isinstance(d, dict) and str(d.get("scale", "")).upper() in delivery_scales]

evidence = []
dora = load(".claude/canvas/dora-metrics.yml")
cls = dora.get("overall_classification")
if cls not in (None, "", "TBD", "n/a"):
    evidence.append(f"dora-metrics.yml overall_classification={cls!r}")

cycles = load(".claude/canvas/cycle-history.yml").get("cycles") or []
launched = [c for c in cycles if isinstance(c, dict) and c.get("terminal_state") == "launched"]
shipped = [c for c in cycles if isinstance(c, dict) and c.get("artifacts_shipped")]
if launched:
    evidence.append(f"cycle-history.yml has {len(launched)} launched cycle(s)")
if shipped:
    evidence.append(f"cycle-history.yml has {len(shipped)} cycle(s) with artifacts_shipped")

if not evidence:
    print("no shipped-delivery evidence recorded -- nothing to reconcile")
    sys.exit(0)
if have:
    print(f"delivery evidence reconciled against diamond(s): {', '.join(have)}")
    sys.exit(0)

print("Delivery evidence exists but NO diamond is at L4/L5:")
for e in evidence:
    print(f"  - {e}")
print("The canvas is reporting a discovery-stage project while the product ships.")
print("Spawn a delivery diamond (retrofit is fine -- mark it) or explain the absence.")
sys.exit(1)
PY
)
    rc=$?
    set -e

    if [ "$rc" -eq 3 ]; then
        info "Check 51: ${result#SKIP:} -- SKIPPED, not passed"
    elif [ $rc -eq 0 ]; then
        pass "Check 51: $result"
    else
        fail "Check 51: $result"
    fi
}

check_theory_claim_artifacts() {
    section "Check 50: theories.md claims name artifacts that exist"

    local theories="docs/theories.md"
    local gates="plugins/mycelium/engine/theory-gates.md"

    if [ ! -f "$theories" ]; then
        info "Check 50: $theories absent — N/A"
        return
    fi

    local result rc
    set +e
    result=$(python3 - "$theories" "$gates" <<'PY'
import re, sys
from pathlib import Path

theories = Path(sys.argv[1]).read_text()
gates_path = Path(sys.argv[2])
gates_text = gates_path.read_text() if gates_path.exists() else ""

problems = []

# 1. every "gate N (Name)" must match a "### N. <Name> Gate" heading
gate_headings = {}
for m in re.finditer(r"^### (\d+)\.\s+(.+?)\s*$", gates_text, re.M):
    gate_headings[m.group(1)] = m.group(2).strip()

# Correction notes QUOTE the old wrong citation, so blank quoted spans first:
# documenting a fix must not permanently re-trip the check that prompted it.
# PER-LINE, AND ONLY ON LINES THAT LOOK LIKE CORRECTION NOTES (review 2026-08-03).
# This blanked every `"..."` span across the WHOLE file in one pass, which is
# delimiter pairing, not correction-note detection: a single unpaired quote — an
# inch mark, a stray quote in a code sample, a smart-quote mismatch — inverts
# which half of the file is scanned, hiding every live citation between it and
# the next quote while EXPOSING the historical one. theories.md already holds 29
# quoted spans. The check would then print "N gates cross-checked" while the
# miscited gate right below the inch mark was never examined — shipping exactly
# the gate-10 defect it was written to catch.
CORRECTION_HINT = re.compile(r"correct|superseded|withdrawn|formerly|was cited|no longer", re.I)
scan_lines = []
for line in theories.splitlines():
    if line.count('"') % 2 == 0 and CORRECTION_HINT.search(line):
        line = re.sub(r'"[^"]*"', lambda q: " " * len(q.group(0)), line)
    scan_lines.append(line)
scan = "\n".join(scan_lines)
citations_checked = 0
for m in re.finditer(r"gate (\d+) \(([^)]+)\)", scan, re.I):
    citations_checked += 1
    num, claimed = m.group(1), m.group(2).strip()
    actual = gate_headings.get(num)
    if actual is None:
        problems.append(f"theories.md cites gate {num} ({claimed}) — no '### {num}.' heading in theory-gates.md")
        continue
    # claimed name must appear in the real heading (case/punctuation tolerant)
    norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
    if norm(claimed) not in norm(actual) and norm(actual.replace(" Gate", "")) not in norm(claimed):
        problems.append(f"theories.md calls gate {num} '{claimed}'; theory-gates.md calls it '{actual}'")

# 2. every backticked path in an "Implemented as:" line must exist
paths_checked = 0
for line in theories.splitlines():
    if "Implemented as:" not in line:
        continue
    tail = line.split("Implemented as:", 1)[1]
    for ref in re.findall(r"`([^`]+)`", tail):
        ref = ref.strip()
        if ref.startswith("/"):          # skill invocation, not a path
            continue
        if "/" not in ref and not ref.endswith((".md", ".yml")):
            continue
        paths_checked += 1
        cands = [Path(ref), Path("plugins/mycelium")/ref, Path("plugins/mycelium/engine")/ref,
                 Path(".claude")/ref, Path("docs")/ref]
        if not any(c.exists() for c in cands):
            problems.append(f"theories.md 'Implemented as:' names `{ref}` — not found")

if problems:
    print("\n".join(problems))
    sys.exit(1)
# DENOMINATOR IS WHAT THIS CHECK VERIFIED (review 2026-08-03). It used to report
# len(gate_headings) — a count of headings in the OTHER file — so a citation regex
# that stopped matching printed a large, reassuring green over zero comparisons.
# That is the verify_citations shape, in the check written to catch it.
if not citations_checked and not paths_checked:
    print("NA:theories.md yielded 0 gate citations and 0 Implemented-as paths")
    sys.exit(0)
print(f"OK:{citations_checked} gate citation(s) and {paths_checked} "
      f"Implemented-as path(s) verified against {len(gate_headings)} gate heading(s)")
PY
)
    rc=$?
    set -e

    if [ "$rc" -eq 3 ]; then
        info "Check 50: ${result#SKIP:} -- SKIPPED, not passed"
    elif [ "$rc" -ne 0 ]; then
        fail "Check 50: theory claims name artifacts that do not exist:
$result"
    elif [ "${result#NA:}" != "$result" ]; then
        info "Check 50: ${result#NA:} -- N/A (nothing to cross-check)"
    else
        pass "Check 50: ${result#OK:}"
    fi
}

check_receipt_contributor_canonical() {
    section "Check 49: receipts case frontmatter carries a canonical contributor"

    local cases_dir="docs/receipts/cases"
    if [ ! -d "$cases_dir" ]; then
        info "Check 49: no $cases_dir — N/A"
        return
    fi

    local offenders=() f val
    for f in "$cases_dir"/*.md; do
        [ -f "$f" ] || continue
        val=$(grep -m1 '^contributor:' "$f" | sed 's/^contributor:[[:space:]]*//; s/[[:space:]]*$//')
        if [ -z "$val" ]; then
            offenders+=("$(basename "$f"): missing contributor field")
        elif printf '%s' "$val" | grep -q '('; then
            offenders+=("$(basename "$f"): '$val' — move the parenthetical to contributor_note")
        fi
    done

    if [ "${#offenders[@]}" -eq 0 ]; then
        local n
        n=$(ls -1 "$cases_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
        pass "Check 49: all ${n} receipts cases carry a canonical contributor"
    else
        local o
        for o in "${offenders[@]}"; do
            echo "      $o"
        done
        fail "Check 49: ${#offenders[@]} case(s) with a non-canonical contributor — grouping on a free-text field cannot group"
    fi
}

# ============================================================
# RUN ALL CHECKS
# ============================================================
#
# Sourcing guard: this block runs only when the script is invoked directly,
# not when sourced. Sourcing the script defines all the helpers + check_*
# functions for use in tests/bash/test_check_<N>.sh. Per G-V12, every
# Bash check should have a fixture test asserting it flags its target
# failure mode; tests source this script, cd to a fixture project, and
# invoke the relevant check function in isolation.
#
# See `tests/bash/README.md` for the testing convention.

if [ "${BASH_SOURCE[0]:-$0}" != "${0}" ]; then
    return 0 2>/dev/null || true
fi

echo "Mycelium Template Structural Integrity Validation"
echo "================================================="

check_yaml_parsing
check_canvas_count_readme_body
check_canvas_count_readme_dir
check_canvas_in_readme_table
check_canvas_in_update_mapping
check_skill_count_readme
check_skill_count_by_category
check_skill_count_claude
check_skill_frontmatter
check_skills_in_claude_md
check_version_consistency
check_antipattern_count
check_gate_count
check_theory_count
check_agents_md
check_untrusted_content_wrapping
check_upgrade_manifest_driven
check_version_bump_discipline
check_code_quality
check_skills_tree_parity
check_manifest_byte_match
check_stale_state_read_pattern
check_plugin_json_version_sync
check_install_command_canonical
check_operating_contract_wiring
check_self_correcting_release_capture
check_canvas_write_preflight
check_four_risks_when_active
check_plugin_identifier_leak
check_claudemd_single_version_entry
check_no_empty_fixture_dirs
check_claudemd_size_ceiling
check_cycle_class_ice_required
check_rendering_spec_strict_marker
check_sync_derived_drift
check_read_before_recommend_preamble
check_postflight_verify_after_write_preamble
check_render_identifier_exposure_declaration






check_hooks_registration_parity
check_chat_ux_axiom_markers
check_gv12_test_coverage
check_receipt_contributor_canonical
check_theory_claim_artifacts
check_delivery_diamond_reconciliation
check_canonical_field_location
check_scenario_legacy_model

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "================================================="
echo "Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "================================================="

if [ "$FAIL" -gt 0 ]; then
    echo "VALIDATION FAILED"
    exit 1
else
    echo "VALIDATION PASSED"
    exit 0
fi
