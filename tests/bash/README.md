# tests/bash — Bash check fixture tests

**Purpose**: G-V12 coverage proof for `tests/validate-template.sh` checks. Every Bash check should have an intentionally-broken fixture and a test that asserts the check flags it.

**Status as of 2026-05-23**: Convention established with Check 30 as worked example. 7+ pre-existing Bash checks lack fixture tests — see the workload estimate in `.claude/memory/corrections.md` 2026-05-23 entry on `bash-check-without-fixture-test` cluster.

## Convention

### Layout

```
tests/bash/
├── README.md              ← this file
├── _assert.sh             ← shared assert/run helpers
├── run.sh                 ← discovery + execution; runs all test_*.sh
├── test_check_<N>.sh      ← one file per Bash check
└── fixtures/
    └── check_<N>/
        ├── <scenario_a>/  ← project-shaped fixture for one scenario
        └── <scenario_b>/
```

### Test file shape

```bash
#!/usr/bin/env bash
# tests/bash/test_check_<N>.sh
# G-V12 coverage proof for Check <N>: <one-line description>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_<N>"

test_<scenario_name>() {
    # Set up fixture (copy or generate)
    # Invoke check (via sourcing the validator or running it black-box)
    # Assert expected pass/fail
}

run_test test_<scenario_name>
report
```

### Invoking a Bash check in isolation

The validator's check functions are defined as bash functions. They can be invoked individually after sourcing the script, **but only if the validator is sourcing-friendly** — its "run all checks" block must be guarded by `if [[ "${BASH_SOURCE[0]:-$0}" == "${0}" ]]; then ... fi` so sourcing doesn't trigger a full run.

This guard was added 2026-05-23 as part of establishing this convention. Pre-existing checks now work with this pattern. Future checks should be tested the same way.

For Check 30 (a self-contained pure-string check), the test runs the check function against a fixture project tree by `cd`'ing to the fixture and sourcing the validator.

For checks that depend on more of the project state (e.g., Check 8 which reads SKILL.md frontmatter across 49 skills), the fixture would need a more complete project tree, OR the check itself should be refactored to accept a project-root argument so a minimal fixture suffices. Refactor decisions are check-by-check.

## Running

```bash
bash tests/bash/run.sh                 # all bash tests
bash tests/bash/test_check_30.sh       # individual test
```

Invoked from `tests/validate-template.sh` Check 17 alongside `pytest tests/python/`.

## G-V12 promotion bar

Every new Bash check graduated in `validate-template.sh` ships with:
1. A fixture project (intentionally violating the check)
2. A test asserting the check flags the fixture
3. (Optional but recommended) A second fixture in the passing state, with a test asserting the check passes

The framework's prior 7+ Bash check graduations (Checks 26, 28, 29, 30, 31, 32, 33, 34) shipped without fixture tests. This is documented as the `bash-check-without-fixture-test` cluster instance; retroactive fixture sweep is evidence-gated (graduates when prior-instance cost crosses a threshold) rather than time-gated.

## Theory grounding

Same as `tests/python/`: G-V12 from `engine/consistency-check-spec.md`. "If a check flags a problem, prove it does — don't trust historical fire instances as coverage." Pearl (interventional vs observational); Ohno (jidoka — build the test that catches the failure).
