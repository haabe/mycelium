#!/usr/bin/env bash
# tests/bash/test_git_pre_commit_hook.sh
# Coverage proof for scripts/git-pre-commit-example.sh — the commit-time guard on
# derived-token drift.
#
# WHAT THIS PROTECTS (dogfood 2026-09-20). A release commit set plugin.json to
# 0.228.0 while CLAUDE.md's canonical Version line stayed 0.227.3. Check 40 detects
# that state exactly, but Check 40 runs PRE-PUSH, and the working tree was repaired
# before the push — so the push passed 27/27 while the broken commit stayed in
# history permanently, where Check 26 then read it in every later session.
#
# The fixture builds a miniature framework repo in a tempdir so the real
# sync_derived.py resolves its REPO_ROOT (parents[3] of its own path) to the
# fixture rather than to the surrounding mycelium checkout.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/scripts/git-pre-commit-example.sh"

# Build a miniature framework tree, run the hook in it, echo "rc=<n>" plus output.
build_and_run() {
    local scenario="$1"
    local tmpdir
    tmpdir=$(mktemp -d)
    (
        cd "$tmpdir"
        case "$scenario" in
            consumer_project)
                # No plugins/mycelium/skills tree: a downstream project, not the
                # framework repo. The hook must get out of the way, not fail on the
                # absence of something that was never supposed to be there.
                printf '*Version 1.0.0 -- consumer\n' > CLAUDE.md
                ;;
            in_sync|drifted|missing_target)
                # sync_derived.py requires EVERY declared target to exist — it reads
                # each one — so the fixture builds the full set. Two skills, because
                # diamond-assess/SKILL.md is itself a skill-count target and also a
                # skill, and the count globs skills/*/SKILL.md.
                mkdir -p plugins/mycelium/scripts plugins/mycelium/.claude-plugin \
                         plugins/mycelium/skills/alpha plugins/mycelium/skills/diamond-assess \
                         .claude-plugin docs/skills docs/integrations
                cp "$REPO_ROOT/plugins/mycelium/scripts/sync_derived.py" \
                   plugins/mycelium/scripts/sync_derived.py
                printf '# SKILL alpha\n' > plugins/mycelium/skills/alpha/SKILL.md
                printf '# diamond-assess\n\nReads 2 skills.\n' \
                    > plugins/mycelium/skills/diamond-assess/SKILL.md
                printf '*Version 0.5.0 -- fixture\n\nShips 2 skills.\n' > CLAUDE.md
                for f in README.md docs/README.md docs/skills/README.md \
                         docs/skills/by-category.md docs/context-surface.md \
                         docs/architecture.md docs/integrations/opencode.md \
                         docs/integrations/codex.md docs/integrations/cursor.md; do
                    printf 'Ships 2 skills.\n' > "$f"
                done
                printf '**Version:** 0.5.0\n\nShips 2 skills.\n' > docs/ai-system-card.md
                printf '{\n  "description": "2 skills"\n}\n' > .claude-plugin/marketplace.json
                if [ "$scenario" = "drifted" ]; then
                    # THE REAL DEFECT, exactly as committed on 2026-09-20: a derived
                    # version ahead of the canonical one.
                    printf '{\n  "version": "0.6.0",\n  "description": "2 skills"\n}\n' \
                        > plugins/mycelium/.claude-plugin/plugin.json
                else
                    printf '{\n  "version": "0.5.0",\n  "description": "2 skills"\n}\n' \
                        > plugins/mycelium/.claude-plugin/plugin.json
                fi
                if [ "$scenario" = "missing_target" ]; then
                    # A declared target that is absent makes sync_derived raise, not
                    # report drift. The hook must not relabel that as a finding.
                    rm -f docs/ai-system-card.md
                fi
                ;;
            *)
                echo "unknown scenario: $scenario" >&2
                exit 1
                ;;
        esac
    )
    cd "$tmpdir"
    local out rc
    out=$(bash "$HOOK" 2>&1)
    rc=$?
    cd "$REPO_ROOT"
    rm -rf "$tmpdir"
    printf 'rc=%s\n%s\n' "$rc" "$out"
}

test_pre_commit_blocks_derived_version_drift() {
    local output
    output=$(build_and_run "drifted")
    assert_contains "$output" "rc=1" "blocks the commit"
    assert_contains "$output" "DRIFT FROM CANONICAL" "names the failure"
    assert_contains "$output" "sync_derived.py" "names the remediation command"
}

test_pre_commit_passes_when_derived_tokens_are_in_sync() {
    local output
    output=$(build_and_run "in_sync")
    assert_contains "$output" "rc=0" "allows the commit when nothing drifted"
    assert_not_contains "$output" "DRIFT FROM CANONICAL" "stays quiet on a clean tree"
}

test_pre_commit_is_inert_in_a_consumer_project() {
    # A downstream project has no plugins/mycelium/ tree of its own. The hook must
    # exit 0 rather than treating a legitimate absence as a finding — the fail-open
    # direction is correct HERE because there is genuinely nothing to derive.
    local output
    output=$(build_and_run "consumer_project")
    assert_contains "$output" "rc=0" "gets out of the way outside the framework repo"
}

test_pre_commit_does_not_relabel_a_crash_as_drift() {
    # A tool that cannot run has found nothing. sync_derived.py exits 1 both for
    # drift and for an unhandled exception, so the hook has to tell them apart or
    # it reports a broken script as a version finding. It still blocks — fail
    # closed — but it must say the invariant was NOT checked.
    local output
    output=$(build_and_run "missing_target")
    assert_contains "$output" "rc=1" "still blocks the commit (fail closed)"
    assert_contains "$output" "FAILED TO RUN" "names the real reason"
    assert_contains "$output" "NOT a drift finding" "refuses to dress a crash as a finding"
    assert_not_contains "$output" "DERIVED TOKENS DRIFT FROM CANONICAL" "does not claim drift"
}

echo "=== test_git_pre_commit_hook: commit-time derived-token guard ==="
run_test test_pre_commit_blocks_derived_version_drift
run_test test_pre_commit_passes_when_derived_tokens_are_in_sync
run_test test_pre_commit_is_inert_in_a_consumer_project
run_test test_pre_commit_does_not_relabel_a_crash_as_drift
report
