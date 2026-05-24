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
    if echo "$haystack" | grep -qF -- "$needle"; then
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
    if echo "$haystack" | grep -qF -- "$needle"; then
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
