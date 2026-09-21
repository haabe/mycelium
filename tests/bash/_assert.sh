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

assert_stdout_json_or_text() {
    # A hook's stdout must be empty, plain text that does not open with a brace,
    # or a JSON object that parses. Claude Code 2.1.248 stopped treating
    # brace-led stdout that is not valid JSON as plain text and reports it as a
    # hook error, so a hand-interpolated object with a stray quote or newline now
    # breaks the hook instead of degrading it. NO PIPE: see assert_contains.
    local out="$1"
    local msg="${2:-stdout is empty, plain text, or valid JSON}"
    local trimmed="${out#"${out%%[![:space:]]*}"}"
    if [ -z "$trimmed" ] || [ "${trimmed:0:1}" != "{" ]; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: $msg"
    elif python3 -c 'import json,sys; json.loads(sys.stdin.read())' <<< "$out" 2>/dev/null; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: $msg"
    else
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: $msg (brace-led stdout does not parse as JSON)" >&2
        echo "        stdout: ${out:0:200}" >&2
    fi
}

run_test() {
    _ASSERT_CURRENT="$1"
    echo "  RUN: $1"
    local _before_f="$_ASSERT_FAILED" _before_p="$_ASSERT_PASSED"
    "$1"
    local _rc=$?
    # A TEST BODY THAT DIES MUST NOT REPORT GREEN (v0.234.1).
    # `run_test` used to call the function and discard its status, so a body that
    # exited early -- a typo'd assertion name (`command not found`, 127), an unset
    # variable under `set -u`, a helper that exited -- recorded nothing, and every
    # assertion after the death silently did not run. Found 2026-09-21 by writing
    # `assert_equals` where this harness provides `assert_eq`: the suite printed
    # "7 passed, 0 failed" with one assertion never executed. That is the same
    # false-green class these tests exist to catch, living in the thing that runs them.
    if [ "$_rc" -ne 0 ] && [ "$_ASSERT_FAILED" -eq "$_before_f" ]; then
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        printf '    \xe2\x9c\x97 %s: TEST BODY EXITED %s WITHOUT AN ASSERTION FAILING\n' "$1" "$_rc"
        printf '        Assertions after that point did not run. A crashed test is not a passing test.\n'
    fi
    # A TEST THAT ASSERTS NOTHING IS AN EMPTY CHECK, and an empty check that reports
    # green is worse than no check: it occupies the slot where a real one would go.
    if [ "$_rc" -eq 0 ] \
       && [ "$_ASSERT_FAILED" -eq "$_before_f" ] && [ "$_ASSERT_PASSED" -eq "$_before_p" ]; then
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        printf '    \xe2\x9c\x97 %s: RAN AND ASSERTED NOTHING\n' "$1"
        printf '        Zero assertions executed. Either assert something or delete the test.\n'
    fi
}

report() {
    echo ""
    echo "  ${_ASSERT_PASSED} passed, ${_ASSERT_FAILED} failed"
    if [ "$_ASSERT_FAILED" -gt 0 ]; then
        return 1
    fi
    return 0
}
