#!/usr/bin/env bash
# Mycelium Template Structural Integrity Validation
#
# Validates that the boilerplate's interconnected files are internally consistent.
# Run before committing changes to the Mycelium template.
#
# Usage: bash .claude/tests/validate-template.sh
# Exit code: 0 = all checks pass, 1 = failures detected
#
# Compatible with macOS (BSD) and Linux (GNU) grep/sed.

set -euo pipefail

# Navigate to repo root (script may be called from anywhere)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

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
# ============================================================
check_canvas_count_readme_body() {
    section "Check 2: Canvas count (README body)"

    local disk_count
    disk_count=$(find .claude/canvas -name '*.yml' | wc -l | tr -d ' ')

    # Try two patterns:
    # v0.13+: "N more canvas files" in abbreviated table
    # Pre-v0.13: "-- N structured YAML files"
    local readme_count
    local more_count
    more_count=$(grep -oE '[0-9]+ more canvas files' README.md | head -1 | sed 's/ more.*//' || echo "0")

    if [ "$more_count" != "0" ]; then
        # Count listed canvas files in the table (lines with backtick-quoted .yml filenames)
        local listed_count
        listed_count=$(grep -cE '`[a-z-]+\.yml`' README.md || echo "0")
        readme_count=$((listed_count + more_count))
    else
        readme_count=$(grep "structured YAML files" README.md | sed 's/.*-- //' | sed 's/ structured.*//' || echo "0")
    fi

    if [ -z "$readme_count" ] || [ "$readme_count" = "0" ]; then
        fail "Could not find canvas count in README body"
    elif [ "$readme_count" -eq "$disk_count" ]; then
        pass "README body canvas count ($readme_count) matches disk ($disk_count)"
    else
        fail "README body says $readme_count canvas files, but $disk_count exist on disk"
    fi
}

# ============================================================
# CHECK 3: Canvas file count in README directory structure
# ============================================================
check_canvas_count_readme_dir() {
    section "Check 3: Canvas count (README directory structure)"

    local disk_count
    disk_count=$(find .claude/canvas -name '*.yml' | wc -l | tr -d ' ')

    # Match: "canvas/                    # 17 YAML source-of-truth files"
    local dir_count
    dir_count=$(grep "canvas/.*# .*YAML" README.md | sed 's/.*# //' | sed 's/ YAML.*//' || echo "0")

    if [ -z "$dir_count" ] || [ "$dir_count" = "0" ]; then
        # README may not have a directory structure section (v0.13+ simplified README)
        pass "README directory structure section not present (simplified README)"
    elif [ "$dir_count" -eq "$disk_count" ]; then
        pass "README directory structure canvas count ($dir_count) matches disk ($disk_count)"
    else
        fail "README directory structure says $dir_count, but $disk_count exist on disk"
    fi
}

# ============================================================
# CHECK 4: Every canvas file on disk appears in README table
# ============================================================
check_canvas_in_readme_table() {
    section "Check 4: Canvas files in README table"

    # README may use an abbreviated table with "N more canvas files".
    # In that case, check that listed + more = total on disk.
    if grep -q "more canvas files" README.md; then
        local more_count
        more_count=$(grep -oE '[0-9]+ more canvas files' README.md | head -1 | sed 's/ more.*//')
        local listed_count
        listed_count=$(grep -cE '`[a-z-]+\.yml`' README.md || echo "0")
        local disk_count
        disk_count=$(find .claude/canvas -name '*.yml' | wc -l | tr -d ' ')
        local total=$((listed_count + more_count))

        if [ "$total" -eq "$disk_count" ]; then
            pass "Canvas table: $listed_count listed + $more_count more = $disk_count on disk"
        else
            fail "Canvas table: $listed_count listed + $more_count more = $total, but $disk_count on disk"
        fi
    else
        # Full listing mode: every file must appear
        local missing=0
        for file in .claude/canvas/*.yml; do
            local basename
            basename=$(basename "$file")
            if ! grep -q "$basename" README.md; then
                fail "Canvas file $basename not listed in README.md"
                missing=$((missing + 1))
            fi
        done

        if [ "$missing" -eq 0 ]; then
            pass "All canvas files appear in README table"
        fi
    fi
}

# ============================================================
# CHECK 5: Every canvas file appears in canvas-update mapping
# ============================================================
check_canvas_in_update_mapping() {
    section "Check 5: Canvas files in canvas-update SKILL.md mapping"

    local mapping_file=".claude/skills/canvas-update/SKILL.md"
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
# CHECK 6: Skill count in README matches directories on disk
# ============================================================
check_skill_count_readme() {
    section "Check 6: Skill count (README)"

    local disk_count
    disk_count=$(find .claude/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

    # Match: "## Skills Reference (35 skills)"
    local readme_count
    readme_count=$(grep "Skills Reference" README.md | sed 's/.*(\([0-9]*\) skills).*/\1/' || echo "0")

    if [ -z "$readme_count" ] || [ "$readme_count" = "0" ]; then
        fail "Could not find skill count in README"
    elif [ "$readme_count" -eq "$disk_count" ]; then
        pass "README skill count ($readme_count) matches disk ($disk_count)"
    else
        fail "README says $readme_count skills, but $disk_count directories exist on disk"
    fi
}

# ============================================================
# CHECK 7: Skill count in CLAUDE.md matches directories on disk
# ============================================================
check_skill_count_claude() {
    section "Check 7: Skill count (CLAUDE.md)"

    local disk_count
    disk_count=$(find .claude/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

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
    for dir in .claude/skills/*/; do
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
    # CLAUDE.md declares this with "auto-discovered" and points to .claude/skills/.
    # Check that the auto-discovery declaration exists OR that all skills are individually listed.
    if grep -q "auto-discovered" CLAUDE.md; then
        # Verify CLAUDE.md points to the skills directory
        if grep -q ".claude/skills/" CLAUDE.md; then
            pass "CLAUDE.md declares skills as auto-discovered from .claude/skills/"
        else
            fail "CLAUDE.md says auto-discovered but doesn't reference .claude/skills/ path"
        fi
    else
        # Fallback: check individual skill references (pre-v0.11.0 behavior)
        local missing=0
        for dir in .claude/skills/*/; do
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

    local ap_file=".claude/harness/anti-patterns.md"
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
# CHECK 12: Theory gate count in README matches table rows
# ============================================================
check_gate_count() {
    section "Check 12: Theory gate count"

    # Count data rows in the gate table (exclude header "| Gate |" and separator "|-")
    local actual_count
    actual_count=$(sed -n '/### Theory Gates/,/^##/p' README.md | grep -E '^\| [A-Za-z0-9]' | grep -vcE '^\| Gate \|' || echo "0")

    # README may have "### Theory Gates (12 gates)" or just "### Theory Gates"
    local readme_count
    readme_count=$(grep -oE '\([0-9]+ gates\)' README.md 2>/dev/null | head -1 | sed 's/[^0-9]//g' || true)
    readme_count="${readme_count:-0}"

    if [ -z "$readme_count" ] || [ "$readme_count" = "0" ]; then
        # No explicit count in heading — just verify the table has rows
        if [ "$actual_count" -gt 0 ]; then
            pass "Theory gate table has $actual_count rows (no explicit count in heading)"
        else
            fail "Theory gate table has no rows"
        fi
    elif [ "$readme_count" -eq "$actual_count" ]; then
        pass "Theory gate count ($readme_count) matches table rows ($actual_count)"
    else
        fail "README says $readme_count gates, but $actual_count rows in gate table"
    fi
}

# ============================================================
# CHECK 13: Theory count claim vs actual table rows
# ============================================================
check_theory_count() {
    section "Check 13: Theory count"

    # README: "30+ established product frameworks" or "35+ established frameworks"
    local claimed
    claimed=$(grep -oE '[0-9]+\+ established' README.md | head -1 | sed 's/+.*//' || echo "0")

    # Count data rows in the theories table (exclude header rows and separator "|-")
    # Try both "## Theories & Frameworks Integrated" and "## Theories" section headers
    local actual_count
    actual_count=$(sed -n '/## Theories/,/^## /p' README.md | grep -E '^\| [A-Za-z0-9]' | grep -vcE '^\| Theory' || echo "0")

    if [ -z "$claimed" ] || [ "$claimed" = "0" ]; then
        fail "Could not find theory count claim in README"
    elif [ "$actual_count" -ge "$claimed" ]; then
        pass "Theory claim ($claimed+) satisfied by $actual_count table rows"
    else
        # The table may use "... and more" for brevity — check for that
        if grep -q "and more" README.md; then
            pass "Theory claim ($claimed+), table shows $actual_count rows + '... and more'"
        else
            fail "README claims $claimed+ theories, but only $actual_count rows in table"
        fi
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
