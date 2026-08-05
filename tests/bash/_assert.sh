#!/usr/bin/env bash
# tests/bash/_assert.sh — shared assert/run helpers for Bash check tests.
# Source this from each test_check_<N>.sh.

_ASSERT_PASSED=0
_ASSERT_FAILED=0
_ASSERT_CURRENT=""

assert_eq() {
    local actual="$1"
    local expected="$2"
    local msg="${3:-equality}"
    if [ "$actual" = "$expected" ]; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: $msg"
    else
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: $msg" >&2
        echo "        expected: $expected" >&2
        echo "        actual:   $actual" >&2
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local msg="${3:-contains}"
    # NO PIPE. `echo "$haystack" | grep -qF` produced FALSE NEGATIVES on CI
    # (Linux/GNU) whenever the haystack was large: `grep -q` exits on first match
    # and closes the pipe, `echo` dies of SIGPIPE, and run.sh sets `set -o
    # pipefail` — so the pipeline returned non-zero even though the needle WAS
    # found, and this reported "not found".
    # CONFIRMED 2026-08-05 from the CI log of run 30983562763: three assertions in
    # test_canvas_health_check_defects.sh failed naming needles that exist exactly
    # once each in the target file, and each ✗ was immediately preceded by a
    # Broken-pipe line. Non-deterministic — it needs `echo` to still be writing
    # when grep exits — and it does not reproduce on macOS/BSD in 200 iterations,
    # which is why it read as a flaky CI check rather than a bug.
    # THE SAME DEFECT IN assert_not_contains BELOW IS WORSE AND WAS SILENT: there
    # a SIGPIPE sends control to the PASS branch, so a needle that IS present
    # reports ✓. This one at least made noise.
    if grep -qF -- "$needle" <<< "$haystack"; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: $msg"
    else
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: $msg (needle '$needle' not found)" >&2
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local msg="${3:-does not contain}"
    # NO PIPE — see the note in assert_contains. A here-string is not a pipeline,
    # so `set -o pipefail` cannot turn a SIGPIPE into a false verdict.
    if grep -qF -- "$needle" <<< "$haystack"; then
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: $msg (needle '$needle' WAS found)" >&2
    else
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: $msg"
    fi
}

run_test() {
    _ASSERT_CURRENT="$1"
    echo "  RUN: $1"
    "$1"
}

report() {
    echo ""
    echo "  ${_ASSERT_PASSED} passed, ${_ASSERT_FAILED} failed"
    if [ "$_ASSERT_FAILED" -gt 0 ]; then
        return 1
    fi
    return 0
}
