#!/usr/bin/env bash
# tests/bash/test_check_26.sh
# G-V12 coverage proof for Check 26: material framework changes require a version bump.
#
# Check 26 reads git history. The fixture builds a fresh git repo at test
# runtime from template files in fixtures/check_26/_templates/ to avoid
# nested-git-dir confusion with the surrounding mycelium repo.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/fixtures/check_26/_templates"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# Build a fresh git repo in a tempdir, populate it per scenario, run the
# check, and return its output. Cleans up the tempdir on return.
build_and_run() {
    local scenario="$1"
    local tmpdir
    tmpdir=$(mktemp -d)
    (
        cd "$tmpdir"
        git init --quiet
        git config user.email "fixture@test.local"
        git config user.name "Fixture"

        case "$scenario" in
            material_change_no_bump)
                # Initial commit: CLAUDE.md at v0.1.0.
                cp "$TEMPLATES_DIR/claude_md_initial.md" CLAUDE.md
                git add CLAUDE.md
                git commit --quiet -m "initial"
                # Material change (skill addition) WITHOUT a version bump.
                mkdir -p plugins/mycelium/skills/foo
                cp "$TEMPLATES_DIR/material_change.md" plugins/mycelium/skills/foo/SKILL.md
                git add plugins/mycelium/skills/foo/SKILL.md
                git commit --quiet -m "add skill without bumping version"
                ;;
            head_bumped_no_pending)
                # Initial commit at v0.1.0, then a bump commit. No material
                # changes since the bump. Should pass.
                cp "$TEMPLATES_DIR/claude_md_initial.md" CLAUDE.md
                git add CLAUDE.md
                git commit --quiet -m "initial"
                cp "$TEMPLATES_DIR/claude_md_bumped.md" CLAUDE.md
                git add CLAUDE.md
                git commit --quiet -m "bump to 0.2.0"
                ;;
            *)
                echo "unknown scenario: $scenario" >&2
                exit 1
                ;;
        esac
    )
    cd "$tmpdir"
    local out
    out=$(check_version_bump_discipline 2>&1)
    cd "$REPO_ROOT"
    rm -rf "$tmpdir"
    echo "$out"
}

test_check_26_flags_material_change_without_bump() {
    local output
    output=$(build_and_run "material_change_no_bump")
    assert_contains "$output" "FAIL: Version-bump discipline" "flags the missing version bump"
    assert_contains "$output" "material framework file" "explains the failure"
    assert_contains "$output" "0.1.0" "names the current (un-bumped) version"
}

test_check_26_passes_head_bumped_no_pending() {
    local output
    output=$(build_and_run "head_bumped_no_pending")
    assert_contains "$output" "PASS: Version-bump check" "passes when HEAD bumped the version"
    assert_contains "$output" "0.2.0" "reports the bumped version"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_26: Check 26 (version-bump discipline) ==="
run_test test_check_26_flags_material_change_without_bump
run_test test_check_26_passes_head_bumped_no_pending
report
