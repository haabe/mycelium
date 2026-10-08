#!/usr/bin/env bash
# tests/bash/test_check_56.sh
# G-V12 coverage proof for Check 56: the skills that read other people's language cite
# engine/reading-for-meaning.md, and the doc still states its two load-bearing rules.
# Fixture trees are built in a temp dir, one per case, from the check's own skill list.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

SKILLS=(jtbd-map user-interview assumption-test user-needs-map ost-builder log-evidence wardley-map handoff metrics-pull devils-advocate)

build_tree() {  # $1 dir; $2 skill to leave without the pointer (or ""); $3 "norule" to strip the doc's rules
    local d="$1" skip="$2" mode="${3:-}"
    mkdir -p "$d/plugins/mycelium/engine"
    if [ "$mode" = "norule" ]; then
        printf '# Reading for meaning\nRead carefully.\n' > "$d/plugins/mycelium/engine/reading-for-meaning.md"
    else
        printf '# Reading for meaning\nA keyword search is a finder, never a counter.\nNever conclude absence from a word match.\n' \
            > "$d/plugins/mycelium/engine/reading-for-meaning.md"
    fi
    local s
    for s in "${SKILLS[@]}"; do
        mkdir -p "$d/plugins/mycelium/skills/$s"
        if [ "$s" = "$skip" ]; then
            printf '# %s\nListen for the words.\n' "$s" > "$d/plugins/mycelium/skills/$s/SKILL.md"
        else
            printf '# %s\nSee `${CLAUDE_PLUGIN_ROOT}/engine/reading-for-meaning.md`.\n' "$s" > "$d/plugins/mycelium/skills/$s/SKILL.md"
        fi
    done
}

capture() {  # $1 tree dir
    cd "$1" || return
    local out
    out=$(check_reading_for_meaning_wiring 2>&1)
    cd "$REPO_ROOT" || return
    echo "$out"
}

test_check_56_passes_when_every_skill_cites_the_rule() {
    local tmp; tmp=$(mktemp -d); build_tree "$tmp" ""
    local output; output=$(capture "$tmp")
    rm -rf "$tmp"
    assert_contains "$output" "PASS: Check 56" "passes when the doc states its rules and all listed skills cite it"
    assert_not_contains "$output" "FAIL" "does not flag the good tree"
}

test_check_56_flags_a_skill_that_lost_its_pointer() {
    local tmp; tmp=$(mktemp -d); build_tree "$tmp" "ost-builder"
    local output; output=$(capture "$tmp")
    rm -rf "$tmp"
    assert_contains "$output" "FAIL: Check 56" "flags a language-reading skill with no pointer to the rule"
    assert_contains "$output" "ost-builder" "names the skill that lost it"
}

test_check_56_flags_a_doc_that_lost_its_rules() {
    local tmp; tmp=$(mktemp -d); build_tree "$tmp" "" "norule"
    local output; output=$(capture "$tmp")
    rm -rf "$tmp"
    assert_contains "$output" "FAIL: Check 56" "flags the doc when its load-bearing rules are gone"
    assert_contains "$output" "finder, never a counter" "names the rule that is missing"
}

test_check_56_flags_a_missing_doc() {
    local tmp; tmp=$(mktemp -d); build_tree "$tmp" ""
    rm -f "$tmp/plugins/mycelium/engine/reading-for-meaning.md"
    local output; output=$(capture "$tmp")
    rm -rf "$tmp"
    assert_contains "$output" "FAIL: Check 56" "flags skills pointing at a doc that does not exist"
}

echo "=== test_check_56: Check 56 (reading-for-meaning wiring) ==="
run_test test_check_56_passes_when_every_skill_cites_the_rule
run_test test_check_56_flags_a_skill_that_lost_its_pointer
run_test test_check_56_flags_a_doc_that_lost_its_rules
run_test test_check_56_flags_a_missing_doc
report
