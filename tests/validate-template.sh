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
    local claude_version
    claude_version=$(grep "Version [0-9]" CLAUDE.md | head -1 | sed 's/.*Version //' | sed 's/ .*//')

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

    # Count gate sections; engine/theory-gates.md uses "### N. <Gate name>" or similar.
    local actual_count
    actual_count=$(grep -cE '^### [0-9]+\.|^## Gate |^### Gate ' "$gates_file" || echo "0")

    if [ "$actual_count" -gt 0 ]; then
        pass "$gates_file defines $actual_count gates (canonical source)"
    else
        fail "$gates_file defines no gates (heading patterns '### N.' / '## Gate' / '### Gate' not found)"
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
    local hardcoded_dir_count
    hardcoded_dir_count=$( { grep -E '\.claude/(engine|skills|hooks|domains|orchestration|schemas|optimization|auto-dogfood)/?[ "$]' "$upgrade" 2>/dev/null \
        | grep -vE '^\s*#' \
        | grep -vE 'parse_manifest\.py' \
        || true; } | wc -l | tr -d ' ')

    if [ "$hardcoded_dir_count" -le "0" ]; then
        pass "upgrade.sh contains no hardcoded framework-directory literals (drift-free)"
    elif [ "$hardcoded_dir_count" -le "3" ]; then
        warn "upgrade.sh contains $hardcoded_dir_count hardcoded framework-directory literal(s) — review for drift candidates"
    else
        fail "upgrade.sh contains $hardcoded_dir_count hardcoded framework-directory literals — refactor to manifest-driven"
        echo "    Use: VAR=\$(python3 plugins/mycelium/scripts/parse_manifest.py <key>); for x in \$VAR; do ...; done"
    fi

    # Drift detector for top-level files: same pattern.
    local hardcoded_top_count
    hardcoded_top_count=$( { grep -E '\b(CLAUDE\.md|README\.md|AGENTS\.md|CONTRIBUTORS\.md|LICENSE)\b' "$upgrade" 2>/dev/null \
        | grep -vE '^\s*#' \
        | grep -vE 'parse_manifest\.py' \
        | grep -vE '\$TEMP_DIR' \
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
        # Documented ignore choices:
        # D = docstrings (we have prose docs, not numpy/google style)
        # ANN = type annotations (intentionally untyped — stdlib-only hooks)
        # COM = trailing comma (style choice)
        # T20 = print() (CLI scripts use print legitimately)
        # S603/S607 = subprocess (we use subprocess intentionally in tests)
        # EM/TRY003 = error message rules (over-prescriptive for our scope)
        # FBT = boolean trap (some legitimate uses)
        # PTH = pathlib over os.path (mixed-style is fine)
        # INP001 = implicit namespace package (sys.path-injected modules
        #          are correct; no __init__.py needed for the hook's import path)
        local ruff_ignores="D,ANN,COM,T20,S603,S607,EM,TRY003,FBT,PTH,INP001"

        local ruff_count
        ruff_count=$( { ruff check plugins/mycelium/scripts/*.py \
            --select=ALL \
            --ignore="$ruff_ignores" \
            2>/dev/null || true; } | grep -oE "Found [0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0")

        # Baseline: post-cleanup-cycle target is 0 errors on cleanly-refactored
        # files (_manifest_lib, framework_guard, parse_manifest). Other
        # pre-existing files (validate_canvas, scope_check) carry historical
        # tech debt that's out of scope for the current cycle — tracked
        # separately. The threshold here is per-file-grouping:
        #   - cleanup-cycle files: target 0 errors (FAIL on regression)
        #   - pre-existing files: warn if increases (don't block)
        local cleanup_files=(
            "plugins/mycelium/scripts/_manifest_lib.py"
            "plugins/mycelium/scripts/framework_guard.py"
            "plugins/mycelium/scripts/parse_manifest.py"
        )
        local cleanup_errors
        cleanup_errors=$( { ruff check "${cleanup_files[@]}" \
            --select=ALL \
            --ignore="$ruff_ignores" \
            2>/dev/null || true; } | grep -oE "Found [0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0")

        if [ "$cleanup_errors" -eq "0" ]; then
            pass "ruff: 0 errors on cleanup-cycle files (_manifest_lib, framework_guard, parse_manifest)"
        elif [ "$cleanup_errors" -le "5" ]; then
            warn "ruff: $cleanup_errors error(s) on cleanup-cycle files — review for drift"
        else
            fail "ruff: $cleanup_errors error(s) on cleanup-cycle files — exceeds drift threshold"
        fi

        # Pre-existing files: informational only
        if [ "$ruff_count" -gt "0" ]; then
            warn "ruff: $ruff_count total errors across all plugins/mycelium/scripts/*.py (includes pre-existing tech debt; cleanup target tracks the cleanup-cycle subset only)"
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
check_four_risks_when_active() {
    section "Check 32: Four-Risks levels required on active-diamond opportunities (F8)"

    local opps_file=".claude/canvas/opportunities.yml"

    if [ ! -f "$opps_file" ]; then
        info "canvas/opportunities.yml absent — Check 32 N/A"
        return
    fi

    local result
    result=$(python3 - "$opps_file" <<'PY'
import re
import sys
from pathlib import Path

opps_path = sys.argv[1]

# Best-effort YAML parse via PyYAML if available, regex fallback otherwise.
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
    # Regex fallback: split on top-level "  - id:" markers
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
    print("OK: No opportunities to check")
    sys.exit(0)
if not missing_per_opp:
    print(f"OK: All {total} opportunity entries have Four-Risks levels populated")
    sys.exit(0)

# WARN — diamond-progress step 2 reads these levels and passes vacuously when
# absent. Multi-team magnification: one team's incomplete evidence becomes
# another team's "validated" gate-pass. Populate via /mycelium:assumption-test
# or /mycelium:ice-score before progressing the diamond into Develop/Deliver.
print(f"WARN: {len(missing_per_opp)} of {total} opportunity entries missing Four-Risks levels (vacuous-pass risk in /mycelium:diamond-progress):")
for ref, miss in sorted(missing_per_opp.items()):
    print(f"  - {ref}: missing {', '.join(miss)}")
sys.exit(1)
PY
    )
    local rc=$?
    if [ $rc -eq 0 ]; then
        pass "$result"
    else
        printf "  %s\n" "$result"
        WARN=$((WARN + 1))
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
# RUN ALL CHECKS
# ============================================================

echo "Mycelium Template Structural Integrity Validation"
echo "================================================="

check_yaml_parsing
check_canvas_count_readme_body
check_canvas_count_readme_dir
check_canvas_in_readme_table
check_canvas_in_update_mapping
check_skill_count_readme
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
check_canvas_write_preflight
check_four_risks_when_active

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
