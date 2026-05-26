# Changelog

**Audience**: operators upgrading + practitioners tracking what changed.
**Time to read**: 10 min.
**Last updated**: 2026-05-26.

The live version is in [CLAUDE.md](../CLAUDE.md) first-line frontmatter — that is canonical. This page is the human-readable summary log.

## v0.30.0 — Cursor 1.7+ and Codex CLI hook adapters

**2026-05-26. Attribution: cursor-codex-hook-adapters.**

Two new runtime adapters land alongside Claude Code (primary) and opencode (extended, deferred): **Cursor 1.7+** and **OpenAI Codex CLI**. Both upstream hook systems are near-supersets of Claude Code's, so Mycelium's twelve hook scripts run unmodified on both runtimes.

**Cursor 1.7+**
- Exports `CLAUDE_PROJECT_DIR` as an env alias — explicit upstream signal that Claude Code scripts should run unmodified.
- Ships native `postToolUseFailure` (the very event opencode lacks). Full reflexion-gate coverage.
- Event names are camelCase (`preToolUse` vs Claude's `PreToolUse`); stdin field names (`tool_name`, `tool_input`, `file_path`, `cwd`, `command`) are identical to Claude Code.
- `UserPromptSubmit` ≡ Cursor's `beforeSubmitPrompt`.
- Adapter: `plugins/mycelium/hooks/hooks.cursor.json` with `failClosed: true` on safety-critical hooks.

**OpenAI Codex CLI**
- Deliberately clones Claude Code's PascalCase event vocabulary — `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`, `PreCompact`, etc.
- Stdin field names align byte-for-byte with Claude Code.
- One gap: no native `PostToolUseFailure`. Failures still surface in `PostToolUse` with the error captured in `tool_response`.
- Adapter: `plugins/mycelium/hooks/hooks.codex.json` plus `codex-postfailure-shim.sh` — a 25-line stdin filter that inspects `tool_response` for `success: false / error / exit_code != 0 / is_error` and delegates to `reflexion-gate.sh` only on failure. Mechanically equivalent to a native failure event for Mycelium's purposes.
- Codex does not auto-export `CLAUDE_PROJECT_DIR`; shell-level export required (documented in integration page).

**Docs**: `docs/integrations/cursor.md` and `docs/integrations/codex.md` mirror the opencode.md structure with honest gap labeling.

**Honesty caveat**: claim that adapters work end-to-end is **consistency-only** — verified against upstream hook docs as of 2026-05-26 but no live runtime test executed yet. Integration pages invite PR-based receipts per anti-pattern #7 discipline.

**Calibration**: opencode adapter remains deferred behind 3 upstream issues (#27899/#27900/#27901). Cursor and Codex have those primitives natively, so both ports are trivial — ~1 session each, scripts reused verbatim.

**MINOR per version-discipline**: new feature surface (two new hook configs + shim + two integration docs); backward-compatible (additive; no existing hook config touched; Claude Code remains primary runtime).

---

## v0.29.0 — Metrics-pull anomaly → devils-advocate auto-chain

**2026-05-25. Attribution: metrics-pull-anomaly-devils-advocate-chain.**

First compound-dogfood mechanism shipping framework-side after an architectural sharpening session: **framework hosts primitives, roadmap composes them into operations**; framework-side mechanisms must pass the **universal-product-model test** (does this serve any adopter regardless of what product they're building?).

Of six compound-exercise candidates surfaced in the session, only #4 passes the test:
- ✅ **#4 anomaly → devils-advocate** — framework-side (universal evidence-discipline value)
- ❌ #2 compound retrospective — roadmap-side (composes framework skills on Mycelium-team cadence)
- ❌ #3 scrape watch — roadmap-side (targets `haabe/mycelium` specifically)
- ❌ #5 cohort-of-one friction walk — roadmap-side (Mycelium-team measurement)
- ❌ #6 trio-coverage on commits — roadmap-side (generalized trio-coverage already lives as a theory gate; my version was framework-team-specific)

**Shipped**: new **Step 10** in `/mycelium:metrics-pull` SKILL.md. When the combined report flags an anomaly with an *inferred explanation* (prose like "Plausible drivers (Unverified):", "Possible cause:", "Likely driver:"), the skill automatically follows `/mycelium:devils-advocate` Technique 4 (Attribution-vs-Consistency Check) against each inference **before presenting the report to the user**.

For each inferred explanation, Step 10 produces:
- A one-sentence restate of the inference
- Per-evidence labels: `cleanly-attributed | consistency-only | unrelated`
- An `evidence_status` field: `verified | consistency_only | unverified`
- Generated contrarian reads (≥1 alternative explanation fitting the same data)
- A recommendation: accept-as-verified | downgrade-to-Unverified | escalate | discard

If any inference is `consistency_only` AND the user is about to append a candidate evidence entry (Step 8) referencing it, Step 10 prompts explicitly: "Append as Unverified in canvas, OR investigate further, OR drop?" No silent canvas-write of consistency-only inferences framed as established cause.

**Skip cleanly** if the report flagged no anomalies, or if all anomalies are raw observations without inferred explanation (Technique 4 challenges *explanations*, not *observations* — honest "X happened, no idea why" is fine).

**Auto-tracks**: if `.claude/memory/cluster-instances.md` has a `consistency-as-evidence` cluster section (graduated 2026-05-09), Step 10 appends one entry per downgrade to the cluster's instance log. Automates the AP#7 sub-(g) accounting that today's session had to do manually for the Google-ratio inference and 5-24 unique-cloner spike.

**Universal-product-model fit**: the AP#7 sub-(g) risk (anchoring on a single inference without contrarian examination) applies to any Mycelium adopter writing evidence to canvas from metric data — whether the product is SaaS, course, AI tool, or service. Not Mycelium-team-specific. No dogfood-mode toggle needed.

**MINOR per version-discipline**: new feature surface on existing skill (Step 10 added); backward-compatible (additive; existing Steps 1-9 unchanged).

## v0.28.0 — Skill framework-dependency frontmatter

**2026-05-25. Attribution: skill-framework-dependency-frontmatter.**

Triggered by investigating an unexplained Google referrer signal in `/metrics-pull` #36/#37 (13:1 visits/unique persisted 2 consecutive days). Hunt surfaced **`majiayu000/claude-skill-registry`** (336 stars, MIT, actively maintained): a Chinese-language Claude Code skills aggregator that has scraped all 49 Mycelium skills as separate registry entries with names like `setup-haabe-mycelium`, `interview-haabe-mycelium`, `four-risks-haabe-mycelium`, indexed across three Google-visible surfaces (GitHub repo + `skills-registry-web.vercel.app` + `majiayu000.github.io/claude-skill-registry/`).

**The registry behaves responsibly**: source_url, repo, and author preserved verbatim; original SKILL.md content + frontmatter intact; license conservatively classified as `NOASSERTION / distribution: restricted` because the crawler missed the LICENSE file at repo root (Mycelium's MIT license lives in `plugins/mycelium/`). The conservative classification actively discourages downstream redistribution.

**The remaining risk**: a user finding e.g. `four-risks-haabe-mycelium` via Google and running it standalone gets a skill that assumes canvas + gates + harness it cannot find. Most skills will partial-fail gracefully but the misfire will read as "Mycelium is broken" to someone who never installed the framework.

**Shipped**: two fields under `metadata:` in every SKILL.md:

```yaml
metadata:
  framework_dependency: "mycelium"
  framework_dependency_note: "This skill is designed to run within the Mycelium framework (https://github.com/haabe/mycelium). Standalone use will skip the canvas state, theory gates, and harness behavior the skill assumes. Install: /plugin install mycelium@haabe/mycelium."
```

**Properties**:
- Invisible to in-framework users (Claude Code does not render `metadata:` as user-facing text).
- Machine-readable for any scraper/registry consumer.
- Propagates wherever the frontmatter goes (the registry preserves frontmatter; see `audit_category_quality.py --include-frontmatter`).
- Spec-compliant per agentskills.io (custom fields under `metadata:` are spec-allowed; same pattern as the v0.23.36 `instruction_budget` migration).

**Mechanical sweep**: 49 files modified in one pass, no body content changed. 45 skills had a pre-existing `metadata:` block (fields appended); 4 skills had no `metadata:` block (fresh one added). All 49 frontmatters re-parse via PyYAML post-edit.

**MINOR per version-discipline**: new feature surface on skill metadata (framework-dependency declaration); backward-compatible.

## v0.27.0 — Check 35: empty-fixture-dir prospective guard

**2026-05-24. Attribution: empty-fixture-dir-check.**

Today's silent-skip cascade twice (v0.26.4 + v0.26.7) hit the same root: empty fixture directories vanish from git, surface as fixture-not-found failures on CI. The `.gitkeep` sweeps closed both incidents reactively. **v0.27.0 closes the failure mode prospectively.**

**New Check 35** in `tests/validate-template.sh`:

```
tests/bash/fixtures/ — no empty directories
```

Every fixture directory must contain a real fixture file OR an explicit `.gitkeep`. Empty dirs FAIL the validator (loud) instead of silently shipping to CI (mysterious fixture-not-found).

**G-V12 coverage**: `tests/bash/test_check_35.sh` with three cases (flags empty dir, passes when `.gitkeep` present, N/A when fixtures dir absent). Empty-dir failure-case fixture is materialized at test time via `mkdir` (committing the empty state IS the bug under test).

**Bash test count**: 23 → 24 files.

**MINOR per version-discipline**: new validator check + new feature surface; backward-compatible (additive — pre-existing fixture dirs already have content or `.gitkeep` from the v0.26.7 sweep).

## v0.26.7 — Empty fixture dir sweep (test_check_27 + defensive)

**2026-05-24. Attribution: empty-fixture-dir-sweep.**

v0.26.6's dropped-filter raw-output diagnostic finally showed the actual failure:

```
✗ test_passes_match: passes when skill set matches (needle 'PASS' not found)
✗ test_flags_divergence: warns on divergence (needle 'WARN' not found)
✗ test_flags_divergence: names the plugin-only skill (needle 'skill_b' not found)
```

test_check_27 (skills-tree parity) fixture directories were entirely empty (`tests/bash/fixtures/check_27/match/.claude/skills/skill_a/`, etc.) — git doesn't track empty dirs, so on CI checkout the entire check_27 fixture tree was missing.

Same root cause as v0.26.4 (`.gitkeep` discipline) but different fixtures. **Defensive sweep**: `find tests/bash/fixtures/ -type d -empty -exec touch {}/.gitkeep \;` — added 17 `.gitkeep` files across check_6/7/8/9/27 fixtures.

test_check_27 now passes on CI. check_6/7/8/9 also get latent-safety even though they happened to pass CI in v0.26.6 (likely via permissive `find` behavior on missing paths + assertion-shape coincidence — investigating further would be diagnostic-yak-shaving; defensive coverage is the right move).

### Pattern note for future fixture authoring

Empty directory tracking is **the** persistent git footgun. Any fixture representing "directory exists but is empty" or "subdirectories exist with no files of their own" needs `.gitkeep`. Recommended pre-commit hook candidate: `find tests/bash/fixtures/ -type d -empty -not -path '*/.git/*'` — flag empty fixture dirs as a discipline check. Not shipping that today; carry-forward for next validator-hardening window.

### Bump rationale

PATCH per `engine/version-discipline.md` — test-fixture sweep; backward-compatible. v0.26.6 entry migrated to docs/changelog.md per Check 34.

## v0.26.6 — Locale-UTF8 grep blindness in diagnostic filter (6th silent-skip variant)

**2026-05-24. Attribution: locale-utf8-grep-blind.**

v0.26.5 fixed SIGPIPE but CI diagnostic STILL showed only RUN: + === lines — no ✓ / ✗ / "N passed" summary lines. **Linux CI's default `LANG=C` makes GNU grep byte-blind to multi-byte UTF-8 sequences**, so the filter regex `^.{0,8}(RUN: |✗|✓|=== |[0-9]+ passed)` silently dropped all assertion lines containing ✓ or ✗ characters.

The filter was hiding the very signal it was designed to surface. macOS BSD grep handles UTF-8 by default; Linux GNU grep does not without explicit locale setup. Local testing never showed the bug.

**Fix**: drop the filter entirely; print raw bash test output (capped at 200 lines). More verbose, but actually surfaces what failed.

**Silent-skip cluster instance count now at 6 in 24 hours** — every fix uncovered the next layer:

| # | Variant | Surfaced via | Fix |
|---|---|---|---|
| 1 | validate_canvas.py silent-pass on schemaless YAML | post-/canvas-health investigation | v0.25.1 |
| 2 | validate-template.sh silent-suppression of bash output | CI red after bash sweep | v0.26.3 |
| 3 | git silent-omission of empty fixture dirs | v0.26.3 diagnostic visible | v0.26.4 |
| 4 | bare `VAR=$(cmd)` under `set -e` silently aborting | first v0.26.2 attempt failed CI same way | v0.26.3 if-then-else |
| 5 | diagnostic-print pipeline's own SIGPIPE | v0.26.4 fix triggered abort | v0.26.5 \|\| true |
| 6 | **THIS**: GNU grep byte-blind to UTF-8 under LANG=C | v0.26.5 diagnostic still missing ✓/✗ lines | drop filter |

Pattern shape: **every diagnostic surface is itself a potential silent-skip surface** at the next layer. Defensive design discipline: diagnostic-only code paths should be maximally robust to environment quirks (locale, signals, exit codes, missing tools). Use raw output + cap; avoid clever filters that depend on environment behavior.

### Bump rationale

PATCH per `engine/version-discipline.md` — validator diagnostic-display fix; backward-compatible. v0.26.5 entry migrated to docs/changelog.md per Check 34.

## v0.26.5 — Diagnostic-pipeline SIGPIPE (4th silent-skip variant in 24h)

**2026-05-24. Attribution: diagnostic-pipeline-sigpipe.**

The v0.26.3 diagnostic surface was working but its print pipeline `... | head -60 | sed 's/^/    /'` triggered SIGPIPE on CI when output exceeded 60 lines. `pipefail` + `set -e` at top of validate-template.sh aborted the validator MID-DIAGNOSTIC, hiding the actual test results AND aborting subsequent checks. **The diagnostic-fix needed its own diagnostic-fix** — same shape as the meta-pattern this whole sequence targets.

Bash tests in fact ALL PASS on CI (verified by counting "X passed, 0 failed" lines in the truncated diagnostic output). The false-FAIL was the validator's diagnostic-print pipeline catching its own SIGPIPE.

**Fix**: `{ ...pipeline... } || true` so the expected SIGPIPE from `head -60` early-close doesn't propagate through pipefail.

### Silent-skip variants tally for 2026-05-24

This is the 5th silent-skip-class fix in 24 hours, all sub-shapes of `documented-rule-diverges-from-enforcement`:

| # | Variant | Fix |
|---|---|---|
| 1 | validate_canvas.py silent-pass on schemaless YAML errors | v0.25.1 fail-loud refactor |
| 2 | validate-template.sh silent-suppression of bash-test output | v0.26.3 capture + diagnostic-print |
| 3 | git silent-omission of empty fixture dirs | v0.26.4 `.gitkeep` discipline |
| 4 | v0.26.2 bare `VAR=$(cmd)` under `set -e` silently aborting diagnostic block | v0.26.3 if-then-else shape |
| 5 | **THIS** — diagnostic-print pipeline's own SIGPIPE silently aborting validator | `\|\| true` to tolerate expected SIGPIPE |

Each was uncovered by the previous fix's diagnostic. The diagnostic-loop value of each fix compounded the next-layer signal — what would have been a multi-day opaque-CI cycle was compressed to ~1.5 hours via successive fail-loud surfaces.

**Meta-pattern observation**: building diagnostic surfaces is structurally adversarial to `set -e` + `pipefail` discipline. Each new diagnostic-capture pattern introduces opportunities for the diagnostic itself to abort the script. Defensive `|| true` on diagnostic-only pipelines (where the print is best-effort, not load-bearing) is the discipline.

### Bump rationale

PATCH per `engine/version-discipline.md` — validator-internal robustness fix; backward-compatible. v0.26.4 entry migrated to docs/changelog.md per Check 34.

## v0.26.4 — Empty fixture directories not git-tracked (CI-only failure)

**2026-05-24. Attribution: git-doesnt-track-empty-dirs.**

The v0.26.3 fix made the bash-test diagnostic visible in CI. First visible diagnostic surfaced the actual cross-environment failure:

```
✗ test_flags_missing: flags missing file (needle 'FAIL' not found)
✗ test_check_14_flags_missing_file: flags absent file (needle 'FAIL: AGENTS.md not found' not found)
```

**Root cause**: `tests/bash/fixtures/check_12/missing/` and `tests/bash/fixtures/check_14/missing_file/` are intentionally-empty fixture directories representing the "file absent" scenarios for those checks. **Git does not track empty directories** — they existed locally on macOS but did not appear on CI checkout. Test scripts use `cd $FIXTURES_DIR/$1` under `set +e`, so cd into non-existent dir silently succeeded (well, didn't abort), and `check_X` ran against whatever CWD happened to be at the time. Different output than fixtures intended → assertions failed only on CI.

**Fix**: add `.gitkeep` files to both directories.

**Diagnostic-loop value**: this is exactly what the v0.26.3 fail-loud surface was designed to surface. Without it, the cycle would have been: push → CI fails opaquely → guess → push → CI fails opaquely → repeat. With it: push → CI fails with specific test names + needles → root-cause-clear → ship fix.

**Worth noting structurally**: this is the **third** silent-skip-class fix in 24 hours:
- v0.25.1: validate_canvas.py silent-pass on YAML errors for schemaless files
- v0.26.3: validate-template.sh silent-suppression of bash-test output on failure
- v0.26.4: git silent-omission of empty directories (no fix to git; mitigation via `.gitkeep` discipline)

Same cluster shape: `documented-rule-diverges-from-enforcement` sub-shape **silent-skip-on-failure** at successive layers (canvas-validator → validator-output-suppression → version-control-state-management).

### Bump rationale

PATCH per `engine/version-discipline.md` — test-fixture infrastructure fix; closes CI-environment compatibility gap. Backward-compatible. v0.26.3 entry migrated to docs/changelog.md per Check 34.

## v0.26.3 — Bash-test CI diagnostic surface (silent-skip → fail-loud, take 2) + ruff cleanup

**2026-05-24. Attribution: silent-skip-fail-loud + ruff-cleanup.**

### (1) Bash-test CI diagnostic surface — corrected take

Same shape as v0.25.1 validate_canvas fail-loud refactor, applied to Check 17's bash-test sub-check.

**The gap**: Check 17 was suppressing `tests/bash/run.sh` output with `>/dev/null 2>&1` and only reporting `FAIL: bash check tests: failures — run 'bash tests/bash/run.sh' for details`. Useless in CI where there's no shell to "run the command in." Surfaced 2026-05-24 when v0.26.1 bash sweep passed locally (macOS+BSD) but failed CI (Linux+GNU).

**v0.26.2 broken attempt** (not a real release; never re-pushed clean): used bare variable assignment `bash_test_output=$(bash tests/bash/run.sh 2>&1)` to capture output. `set -e` at top of validate-template.sh aborts on non-zero command-substitution exit in plain assignment, so the diagnostic block never ran — CI failed identically to v0.26.1.

**v0.26.3 corrected fix**: use `if VAR=$(cmd); then ... else ... fi` shape — same pattern the pytest sub-check already uses correctly under `set -e`. Diagnostic block now reachable on failure; filtered to RUN:/✗/✓/===/Npassed lines; capped at 60 lines to prevent log flooding.

Closes a documented-rule-diverges-from-enforcement instance candidate (validator-says-FAIL-but-cannot-show-why) — parallel to v0.25.1's validator-tolerance-vs-parser-strictness instance 14 graduation.

### (2) Ruff strict-mode cleanup

Two pre-existing ruff strict-mode errors in `validate_canvas.py` introduced by today's earlier refactors (v0.25.1 fail-loud + v0.25.2 collect_trace_graph signature change):

- **RUF013** PEP 484 implicit Optional on `def collect_trace_graph(canvas_dir: Path = None)` → `canvas_dir: Path | None = None`.
- **PERF203** try-in-loop in `validate_all_yaml_parses()` → `# noqa: PERF203` on the except line with rationale comment. **Per-file isolation IS the required design** (each canvas file needs independent error handling so one parse failure doesn't crash the loop AND the error must be attributed to the specific file). Moving the try/except outside the loop would lose both properties. Performance overhead acceptable at ~25-file canvas scale.

Ruff strict mode now clean (was 2 → 0).

### Self-noted: v0.26.2 instance of validator-says-FAIL-but-cannot-show-why

The original v0.26.2 attempt was itself an instance of the very pattern it tried to fix — the diagnostic block didn't run because `set -e` aborted before it. Caught by reading the actual CI log (HEAD's Post Run actions/checkout shows the script exited immediately after "PASS: pytest" with no further validator output). Same dynamic the silent-skip pattern this fix targets: error condition detected but diagnostic information swallowed by environment behavior.

### Bump rationale

PATCH per `engine/version-discipline.md` — bug fix on validator behavior + tech-debt cleanup; closes diagnostic gap; no new feature surfaces. Backward-compatible. v0.26.1 entry migrated to docs/changelog.md per Check 34. v0.26.2 not preserved as standalone changelog entry — broken-attempt, never functional.

## v0.26.1 — Bash-check fixture-test sweep complete (Phase 2-5; cluster fully graduated)

**2026-05-24. Attribution: silent-skip-fail-loud.** Same shape as v0.25.1 validate_canvas fail-loud refactor, applied to Check 17's bash-test sub-check.

### The diagnostic gap

Check 17's bash-test sub-check was suppressing `tests/bash/run.sh` output with `>/dev/null 2>&1` and only reporting:
> FAIL: bash check tests: failures — run 'bash tests/bash/run.sh' for details

That's useless in CI — there's no shell to "run the command in." Diagnosis required either SSH-into-CI or commit-and-watch-and-iterate.

**Surfaced 2026-05-24** when v0.26.1 bash sweep passed locally (macOS+BSD) but failed CI (Linux+GNU). Local-vs-CI environment divergence is exactly when the diagnostic output matters most.

### Fix

Capture `run.sh` output to a variable; print failing assertions inline on failure. Single check-block edit; backward-compatible.

```bash
local bash_test_output
bash_test_output=$(bash tests/bash/run.sh 2>&1)
local bash_test_rc=$?
if [ "$bash_test_rc" -eq 0 ]; then
    pass "bash check tests: all pass (${bash_test_count} test file(s))"
else
    fail "bash check tests: failures (rc=$bash_test_rc)"
    echo "$bash_test_output" | grep -E "^.{0,8}(RUN: |✗|✓|=== |[0-9]+ passed)" | head -60 | sed 's/^/    /'
fi
```

### Same shape, different surface

v0.25.1: validate_canvas.py silently passed YAML errors on schemaless files. Fixed by adding fail-loud YAML-parse check upfront.

v0.26.2 (this): validate-template.sh silently suppressed bash-test output on failure. Fixed by capturing + printing on failure.

Both are instances of the **silent-skip-on-failure** pattern in validators — error condition is detected but the diagnostic information is swallowed. Both close a documented-rule-diverges-from-enforcement instance candidate (validator-says-FAIL-but-cannot-show-why).

### Bump rationale

PATCH per `engine/version-discipline.md` — bug fix on validator behavior; closes diagnostic gap; no new feature surfaces. Backward-compatible. v0.26.1 entry migrated to docs/changelog.md per Check 34.

## v0.26.1 — Bash-check fixture-test sweep complete (Phase 2-5; cluster fully graduated)

**2026-05-24. Attribution: backlog-discharge-driven (Phase 2-5 sweep).** User flagged that at today's velocity, the bash-check-without-fixture-test backlog was doable today. Sweep executed in ~2h actual (vs original 12-17h estimate; vs morning-revised 3-5h estimate after convention-reuse compression). Cluster now fully graduated — every Check in `tests/validate-template.sh` has G-V12 fixture-test backing.

### Coverage shipped this sweep

14 new fixture test files (bash tests 9 → 23):

| Check | Behavior tested | Fixtures |
|---|---|---|
| 1 | YAML parsing across `.claude/canvas/*.yml` | broken_yaml, clean |
| 2 + 3 + 4 (shared) | Deprecation-pass behaviour after 2026-05-08 docs split | (no fixtures; degenerate-pass) |
| 5 | Every canvas file in canvas-update SKILL.md mapping | missing_canvas_in_mapping, all_present, missing_mapping_file |
| 6 | Skill count in `docs/skills/README.md` vs disk | match, mismatch, stub |
| 7 | Skill count in CLAUDE.md vs disk | match, mismatch |
| 8 | Skill SKILL.md frontmatter (name + description) | valid, missing_name, missing_skill_md |
| 9 | Skills auto-discoverable from CLAUDE.md | auto_discovered, missing_path |
| 10 | Version consistency CLAUDE.md vs README.md | match, mismatch, no_readme_version |
| 11 | Anti-pattern count CLAUDE.md/README vs disk | match, mismatch, no_readme_count |
| 12 | theory-gates.md defines gates | valid, empty, missing |
| 13 | Theory count vs README "NN+ frameworks" claim | stub, missing_doc |
| 14 | AGENTS.md router discipline | missing_file, missing_sections, valid |
| 15 | Untrusted-content wrapping convention (curated list + heuristic) | compliant, missing_wrapping, heuristic_candidate |
| 27 | Skills-tree parity (plugin vs legacy) | match, diverge |

### Infrastructure improvement

`tests/bash/_assert.sh`: `grep -qF -- "$needle"` end-of-options sentinel. Without it, needles starting with `-` (like `- interview` for list-item assertions) triggered grep usage errors. Surfaced during Check 15 test draft; fixed once for all future tests.

### Convention reuse validated

Phase 1 (8 tests, 1.5h actual vs 4.5-6.5h estimate) demonstrated ~4× compression via convention reuse. Phase 2-5 (15 tests, 2h actual vs 3-5h estimate) extended the pattern with cross-reference SKILLS_DIR-override sub-pattern (Checks 5-13 share canvas/skills shape; Check 27 extends to plugin/legacy parallel). Per-check time averaged ~10 min after the shared-pattern batch took hold.

### Cluster fully graduated

`documented-rule-diverges-from-enforcement`-adjacent cluster `bash-check-without-fixture-test` is now at full coverage: every Bash Check has fixture test demonstrating it flags its target failure mode. Cluster instance log can record `graduation_status: complete`.

### Bump rationale

PATCH per `engine/version-discipline.md` — retroactive fixture coverage + test-infrastructure micro-fix; closes documented gap; no new feature surfaces. Backward-compatible. v0.26.0 entry migrated to docs/changelog.md per Check 34.

## v0.26.0 — Backlog-discharge bundle: Check 16 allowlist + BVSSH env-var override + Reliability SLOs

**2026-05-24. Attribution: backlog-discharge-driven.** Three shortest-backlog items closed in one bundle, per user instruction.

### (1) Check 16 allowlist convention

`Check 16: upgrade.sh is manifest-driven (no hardcoded list drift)` previously WARNed on `upgrade.sh:100` — a legacy-tree detection guard that's structural-by-design (it checks for upstream framework files that no longer ship as part of the plugin migration flow), not drift. The WARN has been a persistent low-priority finding since v0.20.x.

**Convention shipped**: end-of-line marker `# check-16-allowlist: <reason>` exempts intentional hardcoded literals. Validator's grep chain in Check 16 now respects the marker; reason MUST be present (regex `# check-16-allowlist:\s*\S` requires non-whitespace after the colon). Bare marker without rationale does not exempt.

**Applied**: upgrade.sh line 100 carries marker with reason "intentional legacy-tree detection guard for migration path." Check 16 now reports clean — "no hardcoded framework-directory literals (drift-free)."

### (2) BVSSH session-start hook env-var override

`MYCELIUM_BVSSH_CANVAS` env var added to `plugins/mycelium/hooks/session-start.sh`. Default behavior unchanged (scans `$PROJECT_DIR/.claude/canvas/bvssh-health.yml`); override path takes precedence when set.

**Closes instance 12** of `documented-rule-diverges-from-enforcement` cluster — the hook was reporting "BVSSH health has never been assessed" in framework-self-host context because the assessment canvas lives in the roadmap repo (sibling-path), not in the framework's own `.claude/canvas/`. Same convention pattern as `MYCELIUM_ATTRIBUTION_REGISTRY` (Check 33 in validate-template.sh).

**Verified**: with env var pointed at roadmap canvas, BVSSH-never-assessed reminder GONE (hook sees the roadmap's 6 assessments, latest 2026-05-23 within 30-day cadence → no reminder fires).

### (3) Reliability SLI/SLO definitions (roadmap dora-metrics.yml)

Three explicit SLIs/SLOs defined in `dora-metrics.yml#reliability.slis_slos`:

| SLI | SLO | Current | Classification |
|---|---|---|---|
| rel-001: validate-template.sh exit-0 rate on main | ≥99% over rolling 30d | 100% | elite |
| rel-002: pytest pass rate on main | ≥99% over rolling 30d | 100% | elite |
| rel-003: upgrade.sh successful-sync rate (legacy install path) | ≥95% over rolling 30d | unmeasured | unmeasured |

**Closes Improvement #1 from 2026-05-04 /dora-check** ("Reliability is the only DORA metric not at Elite, and only because SLIs/SLOs aren't defined. Not a real reliability problem; a measurement gap.").

DORA `overall_classification` updated: 4 metrics fully Elite + Reliability at 2-of-3 Elite SLOs (1 unmeasured). Honest framing: Reliability is no longer "unassessed measurement gap" — it has defined SLOs, 2 measured at threshold, 1 awaiting infrastructure.

rel-003 deferred: requires upgrade.sh to write a timestamped sync-log. Lower SLO threshold (95% vs 99%) reflects legacy-install-path role — code path serves downgrade-from-plugin or fresh-degit users, not the canonical plugin-form workflow. Plugin form is canonical post-v0.20.x; legacy path usage decreasing per landscape evolution.

### Bump rationale

MINOR per `engine/version-discipline.md` — new allowlist convention surface (Check 16) + new hook env-var override convention (BVSSH). Backward-compatible: markers + env vars are additive; existing prose/state continues to work; existing checks unchanged on files without markers. No schema changes. v0.25.2 entry migrated to docs/changelog.md per Check 34.

## v0.25.2 — README zone-shaping clarification + Verify-before-propagate X-URL extension

**2026-05-24. Attribution: scoping-carry-forward-driven.** Two small clarifications shipped together.

### (1) README "What it feels like" — zone-shaping mechanisms made explicit

Carry-forward from 2026-05-23 Hashimoto-zone scoping decision (roadmap decision-log). That decision declined to add explicit "zone" classification to Mycelium's gate model on the grounds that **project_type adaptations + phase-scoped guardrails + the explicit out-of-scope statement in README** together ALREADY ARE the zone-shaping mechanism Mycelium offers. Adding an explicit "zone" concept would have been over-engineering plus a gameable surface.

The decision flagged a documentation gap: readers couldn't see the existing mechanism as zone-shaping without explicit framing. This release closes that gap with one sentence in README "What it feels like" naming all three:

> Gate intensity adapts via three mechanisms already in the framework: **project type** (`solo_hobby` thresholds lighter than `team_enterprise`), **phase** (Discover-phase gates lighter than Deliver-phase), and the explicit out-of-scope bounds in "Who it's not for" above. Regen-cheap exploratory scaffolding usually belongs in the out-of-scope set, not under a lighter Mycelium gate path — sibling tools fit those use cases directly.

### (2) Verify-before-propagate convention extended for X/Twitter URLs

Empirical finding from 2026-05-24's four scoping/positioning verifications: WebFetch returns HTTP 402 on x.com and most Nitter mirrors (xcancel.com 503, nitter.privacydev.net refused, nitter.net empty under WebFetch). **Playwright with full-browser rendering succeeds where lighter fetchers don't** — extracts `.tweet-content` text + reply chains via JS evaluation.

Convention extension: for X URLs specifically, attempt playwright → nitter.net before defaulting to `Per user:` summary. Sequence: `mcp__playwright__browser_navigate` → `mcp__playwright__browser_evaluate` to pull tweet content. If Nitter returns empty (some mirrors degrade), accept `Per user:` or ask for paste.

Also documented (Cited: roadmap decision-log 2026-05-24 benchmark): agent-browser CLI was installed and tested as a lighter alternative; while it works for renderable pages with semantic markup (agent-browser.dev = 5KB compact snapshot), it returns empty body on Nitter pages. Not a drop-in replacement for the X-verification surface. Keep playwright as primary; agent-browser available for general-web verification when needed.

### Bump rationale

PATCH per `engine/version-discipline.md` — doc clarifications + convention surface extension. No new behavior or schema changes. Backward-compatible. v0.25.1 entry migrated to docs/changelog.md per Check 34.

## v0.25.1 — validate_canvas.py fail-loud refactor (cluster instance 14 graduation)

**2026-05-23. Attribution: lived-friction-triggered + self-audit-driven.** Closes cluster instance 14 of `documented-rule-diverges-from-enforcement` (new sub-shape: `validator-tolerance-vs-parser-strictness`).

### Trigger

Post-/canvas-health investigation surfaced two real silent-skip surfaces in `validate_canvas.py`:

- **Schema-layer silent pass**: `validate_canvas_against_schema` returns `[]` (no errors) when no schema exists for a canvas file (line 135-137). So YAML parse errors on schemaless files like `north-star.yml`, `bvssh-health.yml`, `gist.yml` (12 of 25 canvas files lack schemas) never surface as FAIL.
- **Trace-walk silent skip**: `collect_trace_graph` warns to stderr then continues on YAML parse failure (line 212-218). Warning is the only signal; doesn't affect exit code.

**Combined effect**: a canvas file with broken YAML + no schema produces "Canvas validation: PASS" with a stderr warning. The warning is the only signal.

**Witnessed same session**: north-star.yml shipped broken at commit `f06634d` (today's /metrics-pull #35 commit — metric_trend entry was inserted into goodhart_check's scope, breaking YAML at line 153). Undetected until validate_canvas.py refactor investigation. Fixed at roadmap commit `32e8acc`.

**Bonus finding (separate concern)**: validate_canvas.py silently defaulted to cwd's `.claude/canvas` when positional argv was ignored. Session-long "Canvas validation: PASS" reports were running against FRAMEWORK canvas while user intent was ROADMAP canvas. This is what masked the roadmap-side YAML break entirely.

### Shipped

1. **`validate_all_yaml_parses()` function in `validate_canvas.py`** — runs first in main(); unconditionally parses every `.yml` in canvas_dir; collects parse errors before schema validation + trace walk. Surfaces all parse errors regardless of schema presence.

2. **Positional argv handling**: `python3 validate_canvas.py [canvas_dir]` now works. argv overrides cwd default. CLAUDE_PROJECT_DIR env var still respected.

3. **G-V12 fixture test** at `tests/bash/test_validate_canvas_fail_loud.sh`:
   - `broken_yaml` fixture (invalid `**Update` at column 3 — same shape as the landscape.yml comp-027 + north-star.yml issues)
   - `clean` fixture (parseable)
   - 6 assertions (file named, validation failed, exit 1 on broken; PASS reported, no error flag, exit 0 on clean)
   - First-try pass

4. **`collect_trace_graph(canvas_dir=None)`** signature — accepts canvas_dir argument with module-level CANVAS_DIR as backward-compatible default for existing pytest fixtures.

5. **Pre-flight inventory pass** against both repo canvas dirs confirmed 0 pre-existing breaks (50 files scanned: 25 framework + 25 roadmap). Refactor ships clean — no CI breakage from previously-hidden issues.

### Cluster instance 14 graduation

Same-session graduation from candidate → mechanism:
- Discovered: post-/canvas-health investigation 2026-05-23 late
- Inventoried: 50 files scanned, 0 pre-existing breaks
- Refactored: ~50 min single session
- Tested: G-V12 fixture covered
- Shipped: this release

The cluster's `documented-rule-diverges-from-enforcement` instance count is now 14. Spec at `engine/consistency-check-spec.md` should consider whether this sub-shape (`validator-tolerance-vs-parser-strictness`) warrants a sibling detection rule in the canonical 6-rule catalog; deferred to next consistency-check-spec.md update.

### Bump rationale

PATCH per `engine/version-discipline.md` — bug fix on validator behavior (documented intent: fail loud on YAML errors; actual behavior pre-refactor: silent pass on schemaless files). Backward-compatible: positional argv is additive; CLAUDE_PROJECT_DIR + cwd defaulting unchanged. No new feature surfaces. v0.25.0 entry migrated to docs/changelog.md per Check 34.

## v0.25.0 — `Verify-before-propagate:` Communication Rule (AP#7 sub-class b + e mechanism layer)

**2026-05-23. Attribution: corrections-audit-driven.** /mycelium:corrections-audit run at session end across 30 framework + 30 roadmap corrections (60 cross-repo) surfaced the load-bearing finding: 87% ai-generated, ≥10 of those user-detected post-publication — confirming harness-detection-gap as the dominant pattern. Today's session alone added 4+ AP#7 instances (sub-classes c, e×3, g + temporal-binarization variant) ALL caught by user or hook, NOT by agent pre-publication.

Two AP#7 sub-classes had **unshipped graduation candidates**:
- **(b) conversational** — flagged 2026-05-09; still unshipped 2 weeks later
- **(e) subagent-output-verification** — graduated to anti-pattern only; surface limited to subagent claims; today's EXE001 instance hit it on validator wrapper text (a NEW surface)

This release is the next mechanism layer for both. Same shape as `Gated by:` convention shipped earlier today: output-convention with grep-detectable post-publish check, aligned with AP#7 graduation philosophy ("make interpolation visible, don't try to eliminate it" — Grice/Sperber-Wilson).

### `Verify-before-propagate:` Communication Rule

Added to CLAUDE.md Communication Rules. Every claim propagation from an external source (subagent, validator wrapper text, tool result paraphrase, dialog assertion, ranked-list summary) must include one of:
- `Verified: ran [tool]` — agent actually ran the underlying tool
- `Cited: [source]` — agent traced the claim to its source
- `Per [speaker/tool]:` — agent attributes the claim without claiming verification (signals reported-not-confirmed)
- `Unverified` — agent explicitly acknowledges propagating without verification (surfaces the trust-gap)

Without any of these forms, the inferential link from "claim someone made" to "I will act on this" is invisible. Convention is grep-detectable.

**Trigger instances that drove the ship**:
- 2026-05-23 EXE001 instance: agent reported "all 3 warnings pre-existing tech debt" by reading validator's wrapper text without running ruff. Drill-down revealed the EXE001 was on `check_gated_by.py` shipped same commit ~1 hour earlier.
- 2026-05-11 subagent-output-verification instance (cluster instance #9): agent accepted subagent's claim about Mycelium files without grep-verifying.
- 2026-05-09 conversational instance (cluster instance #7): agent confirmed founder's "two installs" claim without challenging evidence source; a named user's direct message contradicted both readings.

Same instance shape, different surfaces. Convention covers all three.

### Anti-patterns.md #7 sub-class (e) broadened

`subagent-output-verification` → `trust-without-verification`. Covers ANY tool/wrapper/dialog claim the agent didn't independently verify, not just subagent claims. Sub-class definition + remedy text updated to reflect the new surface.

### Cluster-instances.md instance count

`consistency-as-evidence` bumped 8+ → 12+ to reflect today's four new instances (sub-classes c, e×3, g + temporal-binarization variant). Sub-class distribution narrative updated to note the verify-before-propagate convention ships as next mechanism layer.

### Bump rationale

MINOR per `engine/version-discipline.md`: new Communication Rule surface, backward-compatible (existing prose without verify-form continues to work; convention applies prospectively + retroactively-greppable for future enforcement). No new files, no schema changes; doc + harness extension. Mechanism-graduation script for `Verify-before-propagate:` enforcement deferred (parallel to `check_gated_by.py` stub status — graduation criterion: 2nd post-convention hard-violation instance).

### Devil's advocate

The graduation philosophy explicitly states AP#7 is "almost impossible to fully avoid." This convention may shift the failure surface elsewhere rather than reduce total rate. Counter-test: observe AP#7 instance count over the next ~10 sessions; if rate drops, convention is load-bearing; if rate stays the same, the philosophy is right and additional mechanism layers will be asymptotic. The next 10 sessions ARE the validation. Shipping the convention without conviction-of-effectiveness is the right call per the philosophy — making the interpolation visible doesn't require certainty that it will eliminate the interpolation.

## v0.24.1 — chmod fix for v0.24.0's `check_gated_by.py` (self-audit-driven)

**2026-05-23. Attribution: self-audit-driven.** Post-ship cleanup of v0.24.0.

`check_gated_by.py` shipped in v0.24.0 with a shebang (`#!/usr/bin/env python3`) but without executable mode. Ruff EXE001 fires on this combination ("Shebang is present but file is not executable"). The validator surfaced the regression as one of three WARNs.

**Self-audit failure that delayed the catch**: when user asked "what are the 3 warnings?" agent reported "all three pre-existing tech debt" by reading the validator's wrapper text in Check 17's output ("includes pre-existing tech debt; cleanup target tracks the cleanup-cycle subset only") rather than running `ruff` to inspect the actual finding. Drill-down on follow-up question "what of these 3 warnings are worth working through?" revealed the EXE001 was on `check_gated_by.py` — shipped in the same v0.24.0 commit ~1 hour earlier. The "pre-existing" claim was false; the regression was self-introduced.

**Same shape as anti-pattern #7 sub-class (e)** subagent-output-verification (cluster instance #9, 2026-05-11) — trust-without-verification applied to validator wrapper text instead of subagent claims. Sub-class needs re-definition to cover "any tool output containing a wrapper claim the agent didn't independently verify." Logged to corrections.md + cluster-instances.md.

**Fix**: `chmod +x plugins/mycelium/scripts/check_gated_by.py`. Ruff now clean.

**Backlog items surfaced in same triage** (NOT acted on):
- **Check 16 hardcoded literal in `upgrade.sh:100`**: intentional migration-detection guard; Check 16 lacks an allowlist marker convention for intentional literals. Backlog: design allowlist or comment-marker convention.
- **Check 32: 10/10 framework opportunities lack Four-Risks levels**: real opportunities, predate F8 graduation (2026-05-09). Requires per-opp Torres four-risks assessment (90-150 min + user judgment). NOT placeholder-populated — would defeat Check 32's vacuous-pass detection (exactly the failure it exists to catch).

**Bump rationale**: PATCH per `engine/version-discipline.md` — file-mode bug fix on a script in `plugins/mycelium/scripts/` (material path per Check 26). No content changes, no new features. v0.24.0 entry migrated to docs/changelog.md per Check 34.

## v0.24.0 — `Gated by:` convention + bash check fixture-test infrastructure + AP#7 sub-class extension

**2026-05-23. Attribution: lived-friction-triggered + self-audit-driven.** Saturday session that started as a `/bvssh-check` on l0-purpose and surfaced two structural discipline gaps the framework was carrying. Three feature surfaces shipped in a single coherent unit.

### (1) `Gated by:` Communication Rule

Added to CLAUDE.md Communication Rules: every deferral, threshold, or date-based recommendation must explicitly name its unblock event. Format: `Gated by: [event] — [interventional|observational]`, or canvas `ON HOLD (pending X)`, or natural prose ("Wait for X before Y", "deferred pending X"). All three forms are equivalent; the convention closes the implicit-causal-link surface that the existing prose convention was already partly covering, without retroactively breaking well-formed existing instances.

**Trigger**: a BVSSH-on-l0-purpose recommendation that said "Defer to ≥2026-05-31" for three items that were actually evidence-gated, not capacity-gated. User-detected. The deferral date was *consistent with* the likely unblock window (post-surgery synthesis) without being the *cause* of unblock. Pre-Ship #9 (graduated 2026-05-04) ran and didn't catch — the check pattern-matches on explicit X→Y→Z chains, not on implicit causal links between dates and unblock events.

**Same-turn recurrence**: agent committed the same failure mode in its own scope-pushback paragraph within minutes of shipping the convention. Confirmed the convention must apply to ALL deferral statements including pushback, not just user-facing recommendations.

**Graduation philosophy** (load-bearing, established 2026-05-09, reaffirmed today): AP#7-class failures are almost impossible to eliminate — humans don't write or tell absolutely everything (Grice maxim of quantity; Sperber & Wilson relevance theory). Mechanism class for this cluster is "make the interpolation visible," not "stop interpolating." Output conventions are the right shape; pre-publish checks of subtle inference are not.

**Companion artifact**: `plugins/mycelium/scripts/check_gated_by.py` shipped as un-wired DRAFT stub with full design notes. Graduation criterion to wire into validation: 2nd post-convention hard-violation instance. Avoids gold-plating (mechanism without evidence) per the cluster's own discipline.

### (2) `tests/bash/` fixture-test convention + 8 worked examples

The framework's G-V12 promotion bar ("every check that flags a problem ships with a test demonstrating it does") had been honored for Python scripts (135 pytest tests, 100% script coverage) but missed for Bash checks in `tests/validate-template.sh` (7 graduated-since-G-V12 checks shipped without fixture tests; coverage proof was implicit from "the check fired in the historical instance that triggered graduation" — consistency-only evidence, exactly the AP#7 sub-class e shape applied to test design).

**Cluster surfaced 2026-05-23**: `bash-check-without-fixture-test`, 7 instances (Checks 26, 28, 29, 31, 32, 33, 34), graduated `pattern` same day. The framework discipline diverged from how Bash check graduations actually happened.

**Convention shipped**:
- **Sourcing guard** in `tests/validate-template.sh` so check_* functions can be invoked individually
- `tests/bash/_assert.sh` — shared assert/run helpers
- `tests/bash/run.sh` — discovery + execution runner over `test_*.sh`
- `tests/bash/README.md` — convention doc
- `tests/bash/fixtures/check_<N>/<scenario>/` — fixture project trees per check
- Wired into Check 17 alongside pytest; framework validation now reports "bash check tests: all pass (N test file(s))"

**Phase 1 complete in same session**: all 7 post-G-V12 Bash checks now have fixture tests. Originally estimated 4.5-6.5h; actual time ~1.5h thanks to convention reuse (each subsequent fixture took 15-25 min once the pattern was established). Check 26 (version-bump discipline) was hardest — runtime git-repo construction in tempdir, worked first try. Check 33 (named-attribution leak) required env-var-pointed fixture registry, also worked first try.

**Phases 2-5 remaining** (~12-17h): retroactive coverage of 22 pre-G-V12 Bash checks (Checks 1-25 excluding 17, 26, 27). Lower priority — these pre-date G-V12 and have implicit production stress-test history. Deferred to next post-surgery work window.

### (3) Anti-pattern #7 sub-class catalog + cluster ports

`harness/anti-patterns.md` entry #7 (*Consistency-as-Evidence*) extended with the full sub-class catalog (a-g, NEW: g = implicit-causal-link with temporal-binarization variant) and the graduation philosophy paragraph that was previously buried in roadmap-private corrections.

`cluster-instances.md` (framework, public) ported from roadmap-private:
- `consistency-as-evidence` cluster (8+ instances, sub-class summary table, graduation philosophy)
- `subagent-simulation-misses-lived-friction` cluster (2 instances)

Plus `documented-rule-diverges-from-enforcement` extended to 13 instances with two new sub-shape candidates:
- **hook-vs-canvas-distribution** (instance 12): session-start hook claimed BVSSH never assessed; scans framework-local canvas only, blind to roadmap-side state where 5 prior assessments exist.
- **canvas-state-vs-reality-drift** (instance 13): ht task `status` field showed stale `pending` while external-channel activity had moved testers to receive-mode 9 days earlier. No back-flow mechanism from external channels to canvas.

### Side findings

- **Test-fixture authoring lesson** (logged inline in the Check 29 fixture): test fixtures cannot describe the failure mode in prose if the check uses keyword grep — the prose can satisfy the negated pattern and produce a false-clean fixture. One-off fixture-design quirk, not corrections.md-worthy.
- **Named-attribution leak caught at the mechanism layer**: a cluster-instances.md row included two generic_only names; Check 33 caught pre-push, fixed in-session. Mechanism worked at the layer the agent rule should have. Auto-memory `agent_frida_slip_pattern.md` updated 5x→6x with broadened name-set.

### Bump rationale

MINOR per `engine/version-discipline.md`: three new feature surfaces (testing convention + Communication Rule + script stub), backward-compatible (existing prose gate-naming forms accepted by the new convention; pre-existing checks still callable directly or via sourcing). Not PATCH because of the new feature surfaces; not MAJOR because nothing breaks.

## v0.23.43 — `/canvas-health` action-flag timeout check (v0.23.42 follow-up)

**2026-05-23. Attribution: lived-friction-triggered.** Closes the v0.23.42 meta-finding from the router-discipline scenario re-run.

**Background**: the v0.23.42 router-discipline subagent re-run surfaced this: `canvas-guidance.yml#action_flags.transitions.timeout_handling` (added 2026-05-03) states "Surface as a stale flagged item via /canvas-health (existing staleness machinery applies)." But `/canvas-health` SKILL.md had NO scanner for ON HOLD markers with calendar dates. The convention pointed at a downstream skill that didn't implement what was claimed.

**Same shape as v0.23.42's instance 10** (auto-dogfood orchestrator bypassing SKILL.md). Two `documented-rule-diverges-from-enforcement` instances surfaced in the same session, in different sub-systems. Recorded as instance 11 of the cluster; cluster catalog + instance log updated.

**Fix**: Step 9c added to `plugins/mycelium/skills/canvas-health/SKILL.md`. The new step:
- Scans canvas YAML files for ON HOLD markers with parenthetical calendar dates (`YYYY-MM-DD`, "Month DD", etc.).
- Parses each date and compares to today.
- Future dates: no flag (correctly waiting).
- Past dates <30 days: warning, suggest checking whether awaited evidence has arrived.
- Past dates ≥30 days: escalation, suggest re-evaluating whether the condition is still relevant.
- Does NOT auto-transition any marker. Maintainer decides.
- Explicitly acknowledges the check is incomplete without evidence inspection.

**Concrete instances this would now surface in the roadmap repo's purpose.yml** (if `/canvas-health` were run there): two items reference "Juniors.dev May 7 validation" (Cutler entry + three-voices-convergence entry). Both are at +16 days past (warning, not escalation). Items remain correctly ON HOLD because the awaited usage-validation hasn't arrived; the 16-day past-date is consistent.

**Recursive note worth flagging**: this is the second instance of `documented-rule-diverges-from-enforcement` graduated to mechanism in the SAME SESSION. The cluster's substrate has more surface area than the spec's 5-rule taxonomy currently catches. A Rule 7 candidate ("convention promise → downstream-skill implementation cross-reference") may be warranted if a 12th instance surfaces.

**Atomic-commit rule** (per v0.23.35) applied: CLAUDE.md + plugin.json + changelog + canvas-health/SKILL.md + consistency-check-spec.md + cluster-instances.md in one commit. SKILL.md doc-only addition; no schema/behaviour change.

## v0.23.42 — Framework-health + corrections-audit cycle (scheduled-discipline)

**2026-05-23. Attribution: scheduled-discipline.** `/mycelium:framework-health` + `/mycelium:corrections-audit` cycle. Four mechanical actions landed atomically.

**1. `engine/consistency-check-spec.md`** — added 10th cluster instance + Rule 6 candidate. Today's deep dive surfaced a new subclass of `documented-rule-diverges-from-enforcement`: `test-driver-vs-source-of-truth`. Auto-dogfood orchestrator's hardcoded `_<skill>_task()` prompts bypass framework SKILL.md — three v0.23.39/40/41 SKILL.md edits had zero auto-dogfood effect. The roadmap repo's `check_skill_prompt_drift.py` (~200 LOC) already implements the candidate detection rule for this subclass — counts toward the spec's ≥3-validated-rules promotion bar.

**2. `.claude/memory/corrections.md`** — Detection_origin field backfilled across all 25 corrections in the 90-day window per audit Step 4b discipline. Distribution: evaluator 9, agent_self 7, external_review 4, user 3, hook 1, eval_runner 1. Confirms harness coverage is healthy (most catches are mechanical, not user-dependent) — not a user-detection-gap situation despite 88% ai-generated Origin rate.

**3. `.claude/memory/cluster-instances.md`** — `documented-rule-diverges-from-enforcement` cluster instance count 9 → 10 with full instance-log entry for today's auto-dogfood finding.

**4. README.md "How Mycelium got smarter" highlights rotated** — added 2026-05-20 Edith-Mari book-project case (first non-developer user signal). Replaced 2026-04 macos-can-i-open. The framework-health 4c check flagged 4 newer receipts cases not yet on README; Edith-Mari was the highest narrative significance (first non-developer user pressure-test, drove the wayfinding-at-phase-transitions correction).

**Additionally (no commit changes)**: re-ran `agents-md-router-discipline.yml` (Step 2b deferred design-verification scenario). PASSED against the 2026-05-03 baseline. Subagent classified ON HOLD correctly, cited `canvas-guidance.yml#action_flags`, DID NOT complain about decision authority gap (closed by the action_flags convention shipped between baseline and re-run). Design improved, not just model. One new finding surfaced: timeout_handling case where named-date passed without evidence-resolution warrants a `/canvas-health` route. Worth a follow-up but not blocking.

**Atomic-commit rule** (per v0.23.35) applied: CLAUDE.md + plugin.json + changelog + engine/consistency-check-spec.md + memory/cluster-instances.md + memory/corrections.md + README.md in one commit. No schema, skill, or behaviour change.

## v0.23.41 — `/interview` decision-log salience fix (v0.23.40 follow-up)

**2026-05-23. Attribution: lived-friction-triggered.** Continuation of v0.23.40. Diagnostic --keep-workdir run revealed the agent IS reading the v0.23.40 SKILL.md (confirmed via the roadmap orchestrator's new --plugin-dir flag bypassing user-level plugin cache) but still NOT writing the decision-log entry. Selective instruction-following.

**Two contributing causes diagnosed**:
1. Decision-log bullet was LAST in the Step 2 list and verbose (5+ sub-bullets), giving it low salience vs the short canvas-write bullets.
2. "After the Interview" section had a competing decision-log instruction; agent may have been deferring to that (which often isn't reached within the journey budget).

**Fix**:
- (a) Hoist decision-log write to FIRST position in Step 2 list. Label "(1 of 4)" — mechanical visibility of the complete required set.
- (b) Numbers in all four bullets: "(1 of 4)" through "(4 of 4)". Decision-log + purpose.yml + jobs-to-be-done.yml + active.yml.
- (c) Update Step 2 framing from "side-effect canvas writes" to "Hard requirement: all FOUR files below must be written before Step 3."
- (d) Update "After the Interview" section's Decision Log Entry to explicitly say "EXTEND Step 2's minimal entry, do NOT write a duplicate."

**Combined v0.23.39/40/41 effect on cold-start brief**: the four-file artifact set (purpose, JTBD, diamond, decision-log) is now structurally enforced at Step 2 with mechanical numbering. Verification re-run pending in roadmap auto-dogfood.

**Atomic-commit rule** (per v0.23.35) applied.

## v0.23.40 — `/interview` decision-log gap fix (v0.23.39 follow-up)

**2026-05-22. Attribution: lived-friction-triggered.** Continuation of v0.23.39. The post-v0.23.39 verification re-run surfaced a second gap: `decision_log_entries: None` after the brief — brief flow's Step 2 wrote three canvas files (purpose.yml, jobs-to-be-done.yml, active.yml) but did not write a decision-log entry.

**Root cause**: the existing decision-log instruction lived in the "After the Interview: What Happens Next" section of the SKILL.md, reachable only when the user takes specific depth-menu paths after the brief. Users who stop after the brief (or whose journey is short — e.g., automated dogfood tests with `rounds: 3`) get no decision-log entry.

**Why this is a real issue**: the interview IS the most foundational decision in the project lifecycle. It should write its own log entry at the point of writing the canvas, not in a downstream section that may not be reached. Failing the auto-dogfood `decision_log_contains` check is just the visible symptom; the deeper consequence is that brief-only-onboarded users have NO decision audit trail at all.

**Fix**: Step 2 of brief flow now appends a minimal decision-log entry alongside the canvas writes. Format includes Decision, Theory, Evidence, Confidence, Why_not_alternatives (N/A for first interview). The "After the Interview" section's deeper entry can extend/replace the minimal one when the user reaches it via depth menu.

**Combined v0.23.39 + v0.23.40 effect**: the cold-start brief flow now structurally produces ALL four artifacts (purpose, JTBD, diamond, decision-log) needed for downstream skills + auto-dogfood verification, regardless of whether the user takes a depth-menu path after the brief.

**Atomic-commit rule** (per v0.23.35) applied.

## v0.23.39 — `/interview` cold-start gap fix (Phase 3c finding)

**2026-05-22. Attribution: lived-friction-triggered.** Auto-dogfood Phase 3c (roadmap-private, see roadmap repo) surfaced a real framework gap: the `onboarding-solo-cold-start.yml` scenario (non-developer persona, empty canvas) failed 3/6 criteria at 50% score. The brief flow ("10-min first value" path) was not creating `jobs-to-be-done.yml` AND was creating the L0 diamond with phase variants that broke downstream evaluator checks.

**Fix in Step 2 of the brief flow** (`/mycelium:interview` SKILL.md):
1. Now also writes a stub `.claude/canvas/jobs-to-be-done.yml` with full JTBD structural shape (functional populated from Q1+Q2; emotional, social, hiring, firing, opportunity_score as placeholders for `/mycelium:jtbd-map` enrichment).
2. Explicitly specifies `scale: L0, phase: discover` (lowercase per active.yml schema convention) when creating the L0 Purpose diamond.

**Why this matters**: the brief flow's "10-min first value" promise was structurally incomplete — downstream skills that consume `jobs-to-be-done.yml` couldn't find the file; the auto-dogfood evaluator's `jtbd_mapped` and `diamond_created` checks correctly flagged this. Validates Known Issue #7 from the original April 2026 LEARNING-STRATEGY.md ("No onboarding scenario") — the gap was real, the scenario surfaced it, the fix closes it.

**Particularly relevant for**: the Edith-Mari first-non-developer-user signal logged 2026-05-20. The cold-start path for non-developer users is the path Mycelium has been positioning around; demonstrably had measurable gaps before this fix.

**Atomic-commit rule** (per v0.23.35) applied: CLAUDE.md + plugin.json + changelog + interview SKILL.md in one commit. No schema change, no new skill, no theory change.

**Verification**: re-run of `onboarding-solo-cold-start.yml` post-fix in roadmap repo's auto-dogfood (see roadmap commit for results).

## v0.23.38 — Manifest sync after Check 28 catch (v0.23.37 follow-up)

**2026-05-22. Attribution: maintenance-housekeeping.** v0.23.37 commit was caught by Check 28 (manifest dual-source byte-match) — the two manifests had different rationale comments in their `auto-dogfood` removal block. Resolved by syncing `.claude/manifest.yml` from canonical `plugins/mycelium/manifest.yml` per the validator's remediation hint.

**Pattern recognized**: same shape as the v0.23.34 sync-trap that originated the atomic-commit rule (v0.23.35). The previous trap was plugin.json vs CLAUDE.md (caught by Check 30 + Check 26 chain). This trap is `.claude/manifest.yml` vs `plugins/mycelium/manifest.yml` (caught by Check 28). Both are "I edited two files with different content where the discipline says they must match."

**Lesson for the rule**: when editing both `.claude/manifest.yml` and `plugins/mycelium/manifest.yml`, ALWAYS sync the legacy copy from the canonical AFTER editing the canonical, never compose two independent edits. The legacy copy is a transition artifact pending v0.21.0 / 2026-06-09 removal.

**Worth flagging for corrections.md graduation review** (sister to the v0.23.35 plugin.json sync-lag): "manifest dual-source MUST sync byte-identically" — already enforced by Check 28; the agent-workflow needs to internalize the file-pair coupling.

## v0.23.37 — Auto-dogfood architectural decision: roadmap-private

**2026-05-22. Attribution: maintenance-housekeeping.** Framework cleanup closing dead-end references to `.claude/auto-dogfood/` (deleted in legacy cleanup commit `a5cabd3`, ~April 2026) and re-routing the reinstatement target.

**Original deletion-commit assumption** (incorrect): if auto-dogfood is reinstated, it ships in plugin form (`plugins/mycelium/auto-dogfood/`) as framework-shared infrastructure.

**Updated decision 2026-05-22**: auto-dogfood reinstates as **roadmap-private tooling** at `mycelium-roadmap/.claude/auto-dogfood/`, NOT framework code. Founder direction: at this stage no other Mycelium operator plausibly runs full-session auto-dogfood; the 19-scenario battery + orchestrator + persona-simulator are founder-internal validation tooling. Maintaining the orchestrator with public-API surface burden is over-engineering for a single-operator use case.

**Framework cleanup landed**:
- `plugins/mycelium/manifest.yml` — removed `.claude/auto-dogfood/` entry; replaced with rationale comment.
- `.claude/manifest.yml` — same.
- `plugins/mycelium/engine/dogfood-mode.md` — reference text now points at roadmap-repo location with full context.
- `.claude/evals/dogfood-reports/README.md` — same.

**Full rebuild plan** (~580 lines, 10 sections): `mycelium-roadmap/.claude/auto-dogfood/REBUILD-PLAN.md`. Includes industry-state synthesis (Anthropic + OpenAI + LangChain harness literature), current Mycelium audit (14 change-vectors since deletion), 5-phase rollout, institutional knowledge preservation (deleted `LEARNING-STRATEGY.md` verbatim), and all 5 open questions answered.

**Promotion trigger** (re-evaluate if/when this changes): a second Mycelium operator wanting their own auto-dogfood promotes the orchestrator (not the scenarios) back to framework via `plugins/mycelium/auto-dogfood/`. Default assumption: doesn't happen in the next 6 months.

**Atomic-commit rule** (per v0.23.35): CLAUDE.md + plugin.json + changelog + 2 manifests + 2 doc references in one commit. No skill behaviour change, no schema change, no new skill, no theory change.

## v0.23.36 — agentskills.io spec compliance: instruction_budget migration

**2026-05-22. Attribution: maintenance-housekeeping.** YAML-only frontmatter migration across 45 SKILL.md files (4 skills never had the field). `instruction_budget` moved from top-level frontmatter to `metadata.instruction_budget` per the agentskills.io spec's "custom fields belong under `metadata:` namespace" rule.

**Background**: comp-028 audit in roadmap landscape.yml (2026-05-22) verified Mycelium against the agentskills.io spec. Two of three fields (`name`, `description`) were on-spec. The third (`instruction_budget`) was at top-level frontmatter, which the spec disallows — custom fields belong under the `metadata` namespace. This migration closes the tech-debt finding.

**Scope of change**:
- 45 SKILL.md files: `instruction_budget: N` → `metadata:\n  instruction_budget: "N"` (string-quoted under metadata namespace).
- 1 prose doc (`plugins/mycelium/harness/context-management.md`) updated to reference the new location.
- Zero code references existed. Grep across `*.py`, `*.sh`, `*.md`, `*.json` found only the prose doc above and the SKILL.md files themselves. No validators currently enforce the field; no runtime routes off it.

**Verification**:
- Python YAML-validation pass: all 49 SKILL.md files parse cleanly post-migration. 45 have `metadata.instruction_budget`; 4 have no budget (unchanged).
- No top-level `instruction_budget` remains in any SKILL.md.

**Atomic-commit rule applied per v0.23.35**: CLAUDE.md + plugin.json + changelog + 45 SKILL.md + context-management.md in a single commit. Decision-log entry skipped because this is mechanical migration with no decision-class content (no contrastive alternatives to record; the choice was: align to the spec we already cite).

**Cross-reference**: parallel landing of Anthropic + OpenAI harness article primary-source verification recorded in `mycelium-roadmap/.claude/canvas/purpose.yml` — extends the 2026-05-22 entry's `verification_update_2026_05_22` block with verbatim quotes from "Effective harnesses for long-running agents", "Harness design for long-running application development", "Harness engineering: leveraging Codex in an agent-first world", and "Building an AI-Native Engineering Team." Closes the source-verification flag from this morning's deep-dive entry.

**Re-entry trigger**: if a Check 35-class validator is later added to enforce "no custom top-level frontmatter fields outside the agentskills.io spec set", this migration's completeness is the precondition.

## v0.23.35 — Workflow graduation: atomic-commit rule for version bumps

**2026-05-22. Attribution: lived-friction-triggered.** Three observed misses earlier today (0.23.31 / 0.23.32 / 0.23.33 all failed to sync `plugins/mycelium/.claude-plugin/plugin.json` alongside the CLAUDE.md Version line) plus one plumbing resolution (0.23.34) graduate the pattern to a documented workflow rule.

**New rule** in `plugins/mycelium/engine/version-discipline.md :: Coordinated commit — files that must move together`: every Version-line bump is an ATOMIC operation across these files, in the same commit, never as fix-ups:

1. `CLAUDE.md` (Version line — canonical source)
2. `plugins/mycelium/.claude-plugin/plugin.json` (`version` field — Check 30 enforces)
3. `docs/changelog.md` (new version section)
4. `.claude/harness/decision-log.md` (for decision-bearing patches; most are)

**Why the workflow gap was structural**, not just memory failure: a fix-up commit that touches `plugin.json` alone triggers Check 26 (plugin.json is material → changing it requires its own version bump → infinite regress). Only escape: bundle all version-bump files atomically. The validators (Check 30 + Check 26) were already in place and catching the drift at push-time; the agent-workflow side of the loop was open.

**Full incident log** in `.claude/memory/corrections.md` (TL;DR + full entry dated 2026-05-22). Placed there so future agents reading corrections.md at task-start internalize the rule BEFORE composing the first version-bump commit of any session.

**Theory citation**: Hashimoto — engineer out recurrence. Gilad — evidence-guided graduation (three validator catches in one session without an agent-side rule = the gap is real). Same shape as the 5th-instance "documented rule diverges from enforcement" graduation that created `version-discipline.md` itself.

## v0.23.34 — Plumbing-only: plugin.json sync trap resolved (audit-trail)

**2026-05-22. Attribution: dogfood-audit-trail.** No theory, skill, or schema change. Validator Check 30 caught plugin.json version drift after the 0.23.31/0.23.32/0.23.33 patch sequence today missed syncing plugin.json alongside CLAUDE.md. Initial fix-up commit then chained Check 26 (plugin.json is a material framework file; changing it without a version bump is itself a discipline violation). Resolution: bump CLAUDE.md + plugin.json + changelog in a single coordinated commit at 0.23.34.

**Worth flagging for corrections.md graduation review** (3rd-4th observed instance of this sync-lag class): the validator mechanism is working (Check 30 catches the drift) but the agent-workflow has not yet internalized that `plugin.json` sync belongs in the SAME commit as the `CLAUDE.md` Version-line bump, not as a fix-up. Until the workflow internalizes this, multi-bump sessions will keep tripping the catch-22 between Check 30 (sync required) and Check 26 (changing material files requires version bump).

## v0.23.33 — "Comprehension Debt" concept surveyed (Shopify/BVP, audit-trail)

**2026-05-22. Attribution: dogfood-audit-trail.** Surveyed Bessemer Venture Partners "Inside Shopify's AI-First Engineering Playbook" (Atlas editorial series). Article surfaces a Shopify-internal concept worth borrowing into Mycelium's vocabulary: **Comprehension Debt** — engineers must understand systems "2-3 layers below" their working layer; *learning cannot be abdicated to AI, only toil*. The distinction *abdicate toil ≠ abdicate learning* is sharper than anything currently in Mycelium's corrections.md, anti-patterns catalog, or status-translations vocabulary. It's the operational mechanism behind Cagan's "amplify thinking, don't abdicate it" and Mycelium's own "agent earns the right to write code" framing.

Concept attributed to Farhan Thawar (VP-Eng Shopify) in a Bessemer interview. Same Bessemer piece is also the source for the fourth independent "harness" vocabulary voice this month (Thawar: "If you don't figure out how to harness the agents in 2026, you'll be behind"), and the Lütke/Evans Goodhart-contradiction repeat pattern ("shipped more code in three weeks than the decade before" — identical speech-act to the Evans claim Evans himself critiqued two days earlier).

**Parked, not implemented.** Same parking pattern as v0.23.31 (ODI) and v0.23.32 (Friedman). Five alternatives considered and rejected: graduate to anti-patterns (wrong shelf — Comprehension Debt is a positive discipline, not a failure pattern); graduate to corrections.md (not yet observed as a Mycelium-internal failure mode); extend status-translations to surface toil/learning question (premature surface change); adopt as theory citation in CLAUDE.md L0-L1 roster (single editorial, no research base behind it); do nothing (rejected — future-self should know it was considered).

**Re-entry trigger**: a real Mycelium user articulating "I let the agent do the work but didn't understand it" as a felt problem in a correction or session log. At that point the demand-pull justifies graduation; until then, framework adds no surface area.

**Cross-references** (same survey produced multi-canvas effects in the roadmap repo):
- `mycelium-roadmap/.claude/canvas/purpose.yml` — new market_signal entry 2026-05-22 capturing the Thawar/Lütke quotes, harness-vocabulary fourth voice, and Lütke/Evans Goodhart-repeat pattern.
- `mycelium-roadmap/.claude/canvas/landscape.yml` — comp-025 ("100x org school") extended with Shopify custom-built operationalization vs Evans genesis-stage rhetoric divergence; confidence bumped 0.55 → 0.62 on now-multi-actor evidence.

Decision-log entry `2026-05-22 - "Comprehension Debt" concept surveyed and parked` records the contrastive `why_not_alternatives` and confidence calibration.

## v0.23.32 — Vitaly Friedman AI UX patterns surveyed (external corroboration, audit-trail)

**2026-05-22. Attribution: dogfood-audit-trail.** Surveyed Vitaly Friedman's Maven course "Design Patterns For AI Products In 2026" (June 2026 cohort, $995). External-corroboration class — no new theory adopted, three existing Mycelium disciplines gain independent UX-authority citation:

1. **"Avoid confidence scores (false precision)"** — corroborates `status-translations.md`'s discipline of translating internal confidence floats (0.7) into plain-language presentation ("Moderate — based on 2 user interviews"). Friedman frames this as a UX trust pattern; Mycelium derived it from Liao/Doshi-Velez/Lanham XAI literature. Independent paths to the same rule.
2. **Consensus Meter pattern** — surfacing agreement/disagreement across parallel AI outputs corroborates the value of an explicit dissent UI in `/fan-out` fan-in. Currently Mycelium produces narrative comparison; a consensus/dissent primitive is future UX work, not new mechanism.
3. **Capability Awareness pattern** — users not knowing what the framework can/can't do. `/interview` and `/setup` surface this implicitly via skill discovery + theory citation. Friedman makes the gap explicit; worth noting in `/usability-check` as a Mycelium-internal-UX consideration.

**Rejected**: course-specific UX patterns (Quiet vs Visible AI, daemons, style lenses, precision/temperature knobs, prompt strength indicator, task builder) — these are end-user-product affordances, not methodology primitives. Adding them to a process framework would be a category error. The Trust-Value-Effort triangle was also rejected as a parallel-heuristic to BVSSH — BVSSH already covers the strategic layer; T-V-E is too thin to graduate into the L0–L5 theory roster.

Course not purchased. Public material (Maven course page, free preview lesson "Designing For Trust and Confidence In AI Products", PUSH UX 2025 talk archive) was sufficient for the corroboration determination. The auth-walled Google Doc referenced by the user was visible only as title — body content not extracted.

**Re-entry trigger**: if a Mycelium user designing an end-user AI product asks for UX-layer guidance, point them at Friedman's free preview lesson rather than building UX patterns into Mycelium itself.

Decision-log entry `2026-05-22 - Vitaly Friedman ... surveyed` records the contrastive `why_not_alternatives` (buy-course, graduate-patterns, adopt-T-V-E, re-debate-Quiet-vs-Visible, do-nothing).

## v0.23.31 — ODI surveyed and parked (audit-trail)

**2026-05-22. Attribution: dogfood-audit-trail.** Deep-dive survey of Ulwick's Outcome-Driven Innovation (ODI) against Mycelium's existing L0–L2 theory roster (Christensen JTBD, Allen User Needs Mapping, Torres CDH/OST, Ellis/Gilad ICE).

**Three gaps surfaced**: (1) no quantitative opportunity scoring at the *need* layer — `/ice-score` scores solutions, nothing scores needs against Importance/Satisfaction; (2) no Desired Outcome Statement (DOS) format discipline on need writing — Allen and Christensen both permit free-form, both can drift solution-coupled; (3) no Universal Job Map (Ulwick's 8-step decomposition) in `/jtbd-map`, which often surfaces under-served Prepare/Monitor/Modify steps that incumbents miss.

**Three integration candidates drafted, none shipped**: DOS-format extension to `/user-needs-map`; new `opportunity-score` skill applying `Importance + max(Importance−Satisfaction, 0)` at the need layer; optional 8-step job map step in `/jtbd-map`.

**Parked, not implemented.** User instruction was "log, don't act." YAGNI / demand-pulled discipline applied to the framework's own elaboration — no primitives ship until a real user pulls them. Christensen JTBD retained at L0 (functional/emotional/social lens is structurally better for B2C and identity-laden products than ODI's functional-only bias). Full ODI surveys (n=60–180) rejected as disproportionate for current solo/dogfood user shape; the right cadence here is still Torres continuous discovery, not Ulwick survey methodology.

**Re-entry triggers** (recorded so future-self knows when to un-park):
- Real user reports need-layer prioritization friction that `/ice-score` doesn't solve, OR
- A Mycelium-using product graduates to Tier-3+ launch with a stable, segmentable user base — at which point Cynefin shifts Complex → Complicated and ODI's analyze-mode strengths become applicable.

Decision-log entry `2026-05-22 - ODI primitives surveyed, integration parked` records the contrastive `why_not_alternatives` (full adoption, replace-Christensen, add-to-landscape, do-nothing, implement-now) and confidence calibration. Search decision-log for "ODI" before re-surveying.

## v0.23.30 — First BVSSH baseline assessment (audit-trail)

**2026-05-20. Attribution: dogfood-audit-trail.** `/mycelium:bvssh-check` invoked addressing the SessionStart-hook flag "BVSSH health has never been assessed." First baseline.

Result: **8 of 10 cells green, 2 amber.** Both ambers reflect the same underlying fact: validation-class outcomes (Hoskins, Bentes, Edith-Mari, Lars, plus DORA/Fowler/arxiv vocabulary anchors) are accumulating fast, while the North Star metric "products successfully shipped using Mycelium" remains at 0. Cohort signal (ht-014/15 testing started this week) is the next plausible mover.

CALMS culture all-green except Measurement-outcome (infrastructure healthy — DORA/APEX + daily GitHub pulls + Goodhart counter-metrics — but the thing being measured hasn't moved). The discipline of marking Measurement amber on outcome rather than green on infrastructure is itself the BVSSH check working: don't substitute measurement maturity for outcome movement.

Recommended actions:
- Don't manufacture green on Value. The amber is honest.
- Solo SPOF risk on the founder documented in ai-system-card §6 but unaddressed long-term. Not today; tracked.
- Quarterly cadence for next BVSSH assessment.

Full assessment in `.claude/harness/decision-log.md`. Reversibility: assessment-class entries are immutable by decision-log convention; next assessment supersedes via reference.

PATCH per version-discipline: decision-log entry + version line + changelog; no schema, skill, or behaviour change.

## v0.23.29 — Diamond assessment 2026-05-20 logged (audit-trail)

**2026-05-20. Attribution: dogfood-audit-trail.** `/mycelium:diamond-assess` invoked following yesterday's Edith-Mari user-test signal. Assessment logged to `.claude/harness/decision-log.md` with the full cognitive-forcing → read-before-claim → why-not-alternatives → anti-pattern-scan → reversibility structure.

**L0 Purpose**: confidence 0.61 → 0.63. Half-weight increment absorbing Edith-Mari's behavior-validation signal. L0 stays in Develop — Develop→Deliver needs density beyond a single half-weight signal.

**L1 Strategy**: held at 0.24. The 2026-05-12 devils-advocate rule ("no further L1 increments from positioning-only signals until ≥1 behavior-validation lands") was framed for arms-length validation. Edith-Mari is relationship-class, not arms-length — counts as half-weight behavior-validation but does not satisfy the L1 movement prerequisite. Arms-length cohort signal (ht-014/ht-015) remains the gate.

**Canvas-health items addressed in the same cycle**: `active.yml` refreshed (8-day staleness closed); `purpose.yml _meta.last_validated` refreshed (9-day staleness closed); landscape.yml staleness flagged but left for next pass (content is current; timestamp-only drift).

PATCH per version-discipline: decision-log entry + version line + changelog; no schema, skill, or behaviour change. Two consecutive PATCHes (0.23.28 + 0.23.29) on the same day reflect substantive cycle work (receipt + assessment) — version-discipline is designed to support this cadence at the bottom of the semver tree.

## v0.23.28 — First non-developer user signal (Edith-Mari Pedersen Bartnes book project)

**2026-05-20. Attribution: user-detected.** First non-developer user to test Mycelium end-to-end. Edith-Mari Pedersen Bartnes ran `/mycelium:start` on her book project (content_publication product-type) on 2026-05-20, reaching the assumption-test stage in ~10–15 minutes.

**Strongest positive emotional signal to date.** Brief synthesis produced a near-tears recognition moment ("captured and presented well, even though it was her own words"). Assumption test left her feeling that the framework and agent "really saw her" and what she was trying to achieve with her book. Validates the brief-synthesis-as-identity-mirror hypothesis at the affective layer for non-developer users on non-software product types.

**Five friction items surfaced**, one graduating to corrections.md:

1. Repo bootstrap confusion (creating initial files/folders before `/mycelium:start` could run) — pre-Mycelium friction; non-dev users hit it first.
2. Claude Code save/update file prompts confused her — host-runtime UX, not a Mycelium issue per se but invisible to Mycelium's UX considerations until now.
3. Long save-structure output confused her about what was important — signal-vs-noise issue for non-tech-savvy readers.
4. Chat scroll auto-bounce — when she scrolled up to answer an earlier question, the window scrolled back down. Host-runtime UX issue. She self-solved by asking the agent to repeat the question.
5. **"You are here" wayfinding gap at the assumption-test → deep-dive-interview transition.** Graduated to corrections.md — orientation mechanism previously covered initial flow only; recurs at phase transitions. Correction extends the surface to fire at every transition with explicit non-developer-user rationale.

A calming moment also worth noting: she became visibly less nervous once she realised she was talking to an AI rather than a human. The same warmth in the brief that produced the recognition moment had been producing social-presence pressure before the AI-ness clicked. One property, two effects — worth holding both in mind for future flow design.

**Attribution**: Edith-Mari gave explicit consent for public attribution on 2026-05-20. Attribution-registry (in the private roadmap repo) updated: consent: public_ok. Full receipt at `docs/receipts/cases/2026-05-20-edith-mari-book-project.md`; CONTRIBUTORS.md adds v0.23.28 cycle credit.

PATCH per version-discipline: new receipt + corrections entry + CONTRIBUTORS entry + version line + this changelog entry; no schema, skill, or behaviour change.

## v0.23.27 — README adds "Where it sits in the field" — harness engineering vocabulary anchors

**2026-05-20. Attribution: external-validation-triggered.** Documentation-only release surfacing the recently-named "harness engineering" practice on the README.

Two canonical anchors emerged in spring 2026:
- **2026-04-02**: Birgitta Böckeler / Martin Fowler / Thoughtworks article "Harness engineering for coding agent users" — practitioner thought-leadership canonical anchor on martinfowler.com
- **2026-05-18**: Ning et al. arxiv 2605.18747 "Code as Agent Harness" — 42-author academic survey

Both name "harness engineering" with explicit feedforward / feedback / computational / inferential taxonomy. Mycelium implements a worked example of this taxonomy on a markdown + canvas-YAML + validator substrate. README adds a 3-sentence "Where it sits in the field" section between "What it is in 5 lines" and "Who it's for" — date-anchored citation, no claim of endorsement, explicit acknowledgement that the family of mechanisms is consensus-forming while Mycelium's substrate and specific gating discipline remain its own design.

The positioning claim is time-bound. Re-check schedule lives in the roadmap repo at `.claude/memory/positioning-claim-recheck-harness-engineering.md` with hard checks at 2026-08-19 (3-month) and 2026-11-19 (6-month), plus soft triggers for new arxiv papers, Thoughtworks Technology Radar listings, Doppler-team follow-ups, and industry tools branding "self-improving" features. The discipline this monitors is anti-pattern #7 (Consistency-as-Evidence) applied to positioning claims that age — preventing the founder-keeps-citing-a-stale-claim failure mode.

PATCH per version-discipline: README addition only; no schema, skill, or behaviour change.

## v0.23.26 — opencode integration doc + README rotation (self-hosted positioning)

**2026-05-16. Attribution: external-validation-triggered.** Documentation-only release surfacing Mycelium-on-opencode as an honest user option.

**`docs/integrations/opencode.md`** — first user-facing doc on running Mycelium with opencode + local Ollama. Frames the option for users feeling pressure from Claude Code's pricing model (a visible 2026 trend toward self-hosted AI development workflow). Honest about what works (substrate, skills, validators, MCP, instructions via AGENTS.md/CLAUDE.md fallback) and what doesn't (Read-before-Edit not runtime-enforced, `tool.execute.after` success-only, `tui.prompt.append` silent in headless). Includes setup steps for opencode + `opencode-agent-skills` plugin + Ollama, plus a model-size guidance table (4B–8B not recommended, 14B–32B sweet spot for self-hosted, 70B+ matches Claude-on-Claude-Code discipline level). Links to the three upstream issues filed today (anomalyco/opencode #27899, #27900, #27901).

**README rotation**: tic-tac-toe (oldest, narrowest case study from 2026-04) rotates off "How Mycelium got smarter" highlights; `2026-05-09-consistency-as-evidence-graduation` rotates on (5-instance pattern graduated to anti-pattern #7 with ambient self-check — better demonstrates current verification discipline). README "Who it's for" section gains a pointer to the new opencode doc for users wanting self-hosted setups.

PATCH per version-discipline: new doc + README updates only; no schema, skill, or behaviour change.

## v0.23.25 — Phase 0 substrate audit receipt + Check-26 scope correction

**2026-05-16. Attribution: lived-friction-triggered.** Documentation-only release closing the opencode-port arc's same-day work.

**Phase 0 substrate-neutralization audit** (`docs/receipts/cases/2026-05-16-phase0-substrate-audit.md`): read-only Explore-subagent sweep of 37 substrate files (CLAUDE.md, `.claude/memory/`, `.claude/harness/`, `.claude/engine/`, `docs/`, AGENTS.md, README.md). Four coupling categories surveyed:
- Cat A (tool-surface references): 13 load-bearing findings, concentrated in CLAUDE.md + corrections.md. Read-before-Write rule is the single highest-coupling item.
- Cat B (Claude Code primitive names): hook events, slash-command namespace, auto-memory path. 11 of 13 already labelled "Claude-Code-specific" in AGENTS.md.
- Cat C (paths): `.claude/` referenced 203 times. Treated as location convention, not semantics.
- Cat D (vocabulary/framing): AGENTS.md already documents "framework vs plugin" distinction sharply.

Headline finding: substrate-neutralization claim is verifiable; coupling is visible and documented, not hidden. Three rewrites queued at ~4.5 hours total effort, deferred until either opencode adapter becomes demand-pulled or a quiet maintainer block opens post-Juniors.dev cohort signal.

**Check-26 scope correction** (`.claude/memory/corrections.md`): second same-session trip on the same root cause — `docs/receipts/cases/*.md` files ARE counted as material framework changes by Check 26, contrary to my prior mental model. New rule: bump version pre-emptively when adding any file outside obvious exclusion zones, rather than guessing at what Check 26 treats as material.

PATCH per version-discipline: audit receipt + corrections entry only; no schema, skill, or behaviour change.

## v0.23.24 — opencode port feasibility arc; two delivery patterns graduated; first real decision-log entries

**2026-05-16. Attribution: external-validation-triggered.** Documentation-only release capturing a two-step verification of a potential Mycelium → opencode port.

**Phase 0 — desk + static + binary inspection** estimated a ~1–3 day adapter and flagged three runtime unknowns: whether `tui.prompt.append` mutates the outbound prompt, whether `tool.execute.after` carries a failure signal, whether Read-before-Edit is runtime-enforced.

**Phase 1 — headless runtime test** against opencode 1.15.1 with local Ollama (llama3.1:8b 32k-ctx) overturned all three:

- `tui.prompt.append` is silent in `opencode run` (TUI-scoped only; no documented headless equivalent).
- `tool.execute.after` is success-only — a failed `read` of a nonexistent file fires `before` but never `after`. Errors reach the message stream, not the hook stream.
- Read-before-Edit is **prompt-level only** — the precondition string is in the LLM-facing tool description, not the runtime code path. A clean edit succeeded on a fresh session with no prior read. The Phase 0 binary-inspection conclusion that the precondition was "mechanically enforced" was wrong.

Adapter cost estimate inverts to ~1–2 weeks; PR deferred indefinitely. Substrate-neutralization discipline (canvas + memory + harness + validators as harness-neutral source-of-truth) kept regardless — free option value either way.

**Two delivery patterns graduated** to `patterns.md`:

1. **Don't infer runtime enforcement from schema/description strings.** Binary strings prove what the agent is told, not what the runtime enforces. To reach enforcement evidence: construct the condition the schema warns against, run it against the runtime, observe.
2. **Symmetric API names don't imply symmetric semantics.** `before`/`after` pairs promise temporal ordering, not population symmetry. Any reflexion/cleanup logic depending on "for every X.before I get X.after" must be runtime-verified.

Both are structural twins of anti-pattern #7 (consistency-as-evidence) applied to the framework's own analysis of host runtimes.

**Decision-log gains its first two entries**: "Adopt two-lane harness path (Claude Code + opencode)" at confidence 0.55, immediately superseded by "Re-scope opencode adapter post-Phase-1" at confidence 0.32 — both 2026-05-16, second references the first per the decision-log's immutability convention.

**Two receipts** under `docs/receipts/cases/`: `2026-05-16-opencode-port-feasibility.md` (Phase 0) and `2026-05-16-opencode-phase1-runtime.md` (Phase 1, includes the meta-correction that the Phase 0 binary-inspection conclusion was wrong).

PATCH per version-discipline: documentation + decision-log + memory additions only; no schema change, no skill change, no behavior change for downstream users.

## v0.23.23 — Check 33 scope expansion + WARN→FAIL graduation + pre-disclosure cleanup (mechanism complete)

**2026-05-15. Attribution: lived-friction-triggered.** Three-part graduation closing the named-attribution mechanism stack:

**Part 1 — Check 33 scope expansion**:

Prior scope was `plugins/mycelium/` only, justified as "plugin-marketplace-distribution boundary." But `docs/`, `CLAUDE.md`, `README.md`, `.claude/memory/` are all publicly visible on GitHub even though they don't ship via the plugin — and the v0.23.21 leak hit exactly those paths. Public-visibility scope is the correct boundary, not plugin-distribution scope. New scan paths:

- `plugins/mycelium/` (kept)
- `CLAUDE.md`, `README.md`, `AGENTS.md`, `CONTRIBUTORS.md` (top-level docs)
- `docs/` (recursive)
- `.claude/memory/{corrections,patterns,cluster-instances}.md` (project memory)
- `.claude/canvas/` (canvas state — gitignored in this repo per framework-on-framework exemption, but covered for forks that don't gitignore it)
- `.claude/harness/`, `.claude/engine/` (legacy paths for non-plugin installs)
- `tests/` (catches leaks in test fixtures and validator scripts themselves)

**Part 2 — WARN→FAIL graduation**:

When the registry IS present and Check 33 finds leaks, the check now exits 1 instead of warning. Graduation criterion ("pre-disclosure leaks addressed") satisfied by Part 3.

Layer 1 from v0.23.22 preserved: missing-registry behavior is still INFO in CI, WARN-loud in framework-self-host local context.

**Part 3 — Pre-disclosure cleanup**:

15 leaks regenericized across 4 files:
- `docs/changelog.md` — 3 spots (v0.23.13 title, v0.23.10 entry text, v0.18.x entry text). Title now reads "Cohort-attribution leak fix" instead of the prior cohort-participant-named version. Historical-accuracy preservation: git history retains the original text; only the working-tree state is regenericized.
- `docs/receipts/cases/2026-05-09-consistency-as-evidence-graduation.md` — 1 spot (verbosity-adaptation memo example regenericized).
- `.claude/memory/patterns.md` — 1 spot (named cohort-participant "fork" attribution → generic "audience-attendee fork from a cohort participant" phrasing).
- `.claude/memory/corrections.md` — 6 spots across multiple entries (the 2026-05-14 Check 33 introduction entry, the 2026-05-14 limit:1 cost-framing entry, the 2026-05-14 recurrence-flag entry, and today's 2026-05-15 recurrence-#3 entry).

**Registry update** (in private roadmap repo):

Two cohort participants (ht-014, ht-015) added to the attribution registry as `consent: generic_only`. The prior registry only flagged the ht-012 participant; the two newly-active cohort members were not yet tracked, so Check 33 wouldn't have caught their names had they leaked. Now tracked.

**Validator state after this PATCH**:

```
Check 33: 0 leaks in public-visibility scope (all flagged names absent from publicly-visible paths)
```

Mechanism complete: registry-driven detection + expanded scope + fail-on-leak + cleaned baseline.

**Sequential 4-version arc**:

The named-attribution-leak class has driven four PATCH cycles in two days, each closing a gap exposed by the previous:
- **v0.23.20** — pre-push hook for canvas validation (shipped the hook infrastructure)
- **v0.23.21** — cohort-log-driven friction fixes + in-band leak regenericize after founder pre-push catch
- **v0.23.22** — Layer 1 (Check 33 local fail-loud) + Layer 2 (pre-push runs both validators) — mechanical gates replacing cognitive ones
- **v0.23.23** — scope expansion + WARN→FAIL + cleanup — mechanism completion

Each version satisfies the Hashimoto principle: detect a discipline gap → engineer a mechanism that catches it → verify the mechanism by walking through the next failure attempt. The recurrence count for this class started at 3; one more recurrence (a fourth instance) would now be caught at edit-time by the expanded Check 33 running through the pre-push hook before reaching `origin/main`.

PATCH per version-discipline: validator behavior change + content regenericize; no schema change, no skill change, no behavior change for downstream users.

## v0.23.22 — Layer 1 + Layer 2: Check 33 context-aware fail-loud + pre-push hook runs both validators

**2026-05-15. Attribution: lived-friction-triggered.** Three documented graduations had not prevented recurrence of the named-attribution-leak class (v0.23.13 initial → v0.23.14 commit-message-as-public-surface → v0.23.21 working-tree-leak, all logged in `.claude/memory/corrections.md`). The auto-memory rule was a cognitive gate; cognitive gates degrade across long sessions. This PATCH replaces cognitive gates with mechanical ones at two layers.

**Layer 1 — Check 33 context-aware fail-loud**:

The validator's named-attribution-registry check (`tests/validate-template.sh` Check 33) previously fail-opened uniformly when `$MYCELIUM_ATTRIBUTION_REGISTRY` was absent. The fail-open was intentional for CI (CI runners legitimately can't reach the private companion repo where the registry lives) but undifferentiated from local-dev — which is exactly where edits happen and where the registry SHOULD be configured.

New behavior:
- `$CI` or `$GITHUB_ACTIONS` set → INFO (unchanged; CI fail-open preserved).
- Framework-self-host detected (`plugins/mycelium/.claude-plugin/plugin.json` exists AND `CLAUDE.md` starts with `# Mycelium:`) AND registry absent → **WARN with explicit setup guidance** (was INFO). Surfaces the missing-registry state at the moment of every local validator run.
- Downstream user / non-self-host project → INFO (check is maintainer-side; downstream users don't have a cohort registry concern).

Framework-self-host detection uses the same convention as the v0.23.16 framework-on-framework exemption — no new mechanism, just reusing the established marker.

**Layer 2 — pre-push hook runs both validators**:

The pre-push hook script (`plugins/mycelium/scripts/git-pre-push-example.sh`, shipped v0.23.20) previously ran only `validate_canvas.py`. v0.23.21's leak passed the canvas validator (schema was clean) and would have reached `origin/main` if the founder hadn't caught it manually in commit-message review.

New behavior:
- Hook still runs `validate_canvas.py` first (existing canvas-schema check).
- If `tests/validate-template.sh` exists in the repo (or `.claude/tests/validate-template.sh` for legacy), the hook now runs it too. This surfaces Check 33 (named-attribution scan) and the other 33 structural-integrity checks at push-time as a backstop.
- Downstream user projects don't ship `tests/` — they skip this branch gracefully (the hook detects absence and exits 0 from that branch).

Both repos (`mycelium`, `mycelium-roadmap`) have their local `.git/hooks/pre-push` updated to the new version. Per-clone state, not in git, dogfooding only.

**What this PATCH does NOT do**:
- Does NOT clean up the 3 pre-existing leaks already on `origin` from older versions (v0.23.13 title, v0.23.10 entry, v0.18.x entry naming a cohort participant). Separate regenericize PATCH candidate.
- Does NOT graduate Check 33 leak detection from WARN to FAIL when registry IS present and leaks are found. Depends on the pre-existing-leak cleanup landing first.
- Does NOT add a PostToolUse hook for edit-time interception (Layer 3 from the 2026-05-15 deep-dive). Held until Layer 1 + Layer 2 prove insufficient against future recurrence.

**Theory connection**:

This is the Hashimoto principle applied recursively. Each prior graduation (registry move, CI fail-open documentation, auto-memory rule) was a partial mechanism. The auto-memory rule failed because cognitive gates degrade. Layer 1 + Layer 2 are mechanical gates that fire on every validator run and every push, not on agent vigilance. Per the framework's own discipline (graduated v0.23.16): the corrections-to-mechanism pipeline only counts when the mechanism is *engineered*, not memorized.

PATCH per version-discipline: validator behavior change + hook script extension; no schema change, no skill change, no behavior change for downstream users beyond the (correctly-shaped) push-time backstop.

## v0.23.21 — ht-012 cohort-log driven: Q1 constraint visibility, time-budget expectation, phase-index narration discipline; opp-010 logged; named-attribution leak regenericized

**2026-05-15. Attribution: cohort-log-triggered (ht-012).** Mechanism audit against the first cautious-learner cohort log (ht-012 partial_findings 2026-05-10/12, private roadmap repo) surfaced 7 partial-shipped frictions and 1 unmapped one. Three closed this PATCH, one promoted to opp-010.

**Privacy correction layered into this PATCH**: initial draft of this version named the cohort participant explicitly across 5 working-tree files (CLAUDE.md version line, this changelog entry, two SKILL.md discipline-note attributions, opp-010 description) plus 2 already-pushed entries (opp-009 evidence in commit 43989ae). Recurrence of the v0.23.13 named-attribution-leak class. User caught pre-push; regenericized in this same PATCH. Generic-only attribution discipline holds in the public framework repo per the cohort-attribution-boundary rule; named attribution stays in the private roadmap repo where disclosure-ack covers generic-framed friction flow only. Correction logged separately in framework `corrections.md`.

**Closed by this version**:

- **f4** (Q1 single-sentence constraint mis-read as rhetorical politeness; user wrote 2–3 sentences before discovering the limit was hard). Fix: format spec now appears as a bolded mechanical prefix (`**(one sentence, hard limit)**`) before the question text, not as a prose prefix (`"In one sentence, X?"`) that can be parsed as politeness register. Discipline rule added to `/interview` SKILL.md: format specs must be bolded/parenthesized, not prose.

- **f5** (user expected a time-budget question per stale README mental model; spent time re-reading skills/README to confirm she hadn't misunderstood). Fix: `/interview` Universal Brief Flow intro line now explicitly states no time-budget question at brief stage — "depth and time-cost are chosen after the brief, when you have data to choose." Aligns user expectation with current Universal Brief Flow behavior; resolves the cross-skill consistency drift between `/interview` (no time-budget) and `/mycelium:preflight` (time-budget IS asked, but for L4 delivery scoping, not L0 brief).

- **f9** (internal "Phase 6" vocabulary leaked into user-facing prompts during diamond inspection). Fix: narration-discipline rule added to both `/interview` SKILL.md and `/mycelium:diamond-assess` SKILL.md — Phase-N indices are internal skill structure and MUST NOT be narrated to users; L0–L5 diamond scales are framework-external vocabulary and ARE narratable.

**Promoted to opportunity (not shipped this PATCH)**:

- **f2** (per-file permission prompts during `/mycelium:start` with no upfront preview list; verbatim user quote in the source language preserved in private roadmap canvas — not surfaced here). Logged as **opp-010** with `evidence_type: data-supported` (schema enum; underlying class is behavior-validated per the cohort-log) and `confidence: 0.55`. **First framework-repo opportunity with real-user-research provenance** — opp-001 through opp-007 are anecdotal/N=1 partial-graduations; opp-008/009 are framework-on-framework conversational discovery (anecdotal). opp-010 is real cohort-log evidence and satisfies Torres CDH "from research, not brainstorming" rule cleanly.

  Implementation deferred pending wider cohort triangulation. Suggested shape (in opp-010 notes): add a Step 0 to `/mycelium:start` that enumerates the files/directories `setup` will create and presents them as a flat list with a single "Proceed?" prompt before per-file Claude Code permission prompts arrive. Doesn't bypass Claude Code's per-action model, but aligns user expectation with system behavior — addresses the worst part of the friction (uncertainty about scope mid-install).

**ht-012 cohort-log audit scoreboard after this PATCH**:

| Status | Count | Friction points |
|---|---|---|
| Closed | 5 | f4, f5, f6 (prior), f9, f10 (prior) |
| Partial | 4 | f1, f3, f7, f8 |
| Open as opp (deferred) | 1 | f2 → opp-010 |

5/10 frictions now fully closed. The framework cycle 0.23.16–0.23.21 has moved the cohort-log signal from 2/10 closed → 5/10 closed in two days, with the remaining four flagged for triangulation when wider cohort logs land.

**What did NOT change**: no schema change, no validator change, no new skill, no hook change. Three SKILL.md prompt-copy edits + one new opp entry. PATCH per version-discipline.

## v0.23.20 — Canvas-validation pre-push integration (capability, not auto-install)

**2026-05-15. Attribution: lived-friction-triggered.** Two CI failures on 2026-05-15 (commits 43989ae, 483dd86) — schema violations in `opp-009.trace.upstream` that the local template validator didn't catch because canvas-schema validation is a separate tool (`validate_canvas.py`) that wasn't run before push. Recurrence of "I ran one of two validators" pattern.

**What changed**:
- New reference script: `plugins/mycelium/scripts/git-pre-push-example.sh`. Resolves `validate_canvas.py` via `$CLAUDE_PLUGIN_ROOT` (with legacy fallbacks), checks `.claude/canvas/` exists, runs the validator, blocks the push with a clear error and bypass hint if it fails. Self-skips gracefully when validator or canvas dir is absent.
- Docs section in `docs/contributing/README.md`: how to wire `validate_canvas.py` into existing hook tooling (husky/lefthook/pre-commit/plain bash/GitHub Actions), plus opt-in install command for the reference hook.

**What did NOT change**:
- No plugin installer modification. Mycelium does **not** install hooks for plugin users — `.git/hooks/` is per-clone state, and most projects have or will have their own hook pipeline. The shipped pattern is *library, not framework*: provide the capability, let users integrate it.
- No PostToolUse hook (Option B from v0.23.19 deferred candidate). Pre-push catches the same class one loop later at lower implementation cost; PostToolUse remains future work if pre-push proves insufficient.
- No schema change, no skill change, no validator change.

**Sequencing notes**:

Three discussion rounds collapsed to this smaller correct shape after user pushback ("Won't the users set up their own pre-commit scripts for their project?"). The earlier proposals (Option A doc-only / Option B PostToolUse / pre-push hook auto-install) all overstepped Mycelium's seam: the framework provides discipline scaffolding, not hook-pipeline management for user repos. Original framing was scope-creep; current framing is the right boundary.

**Dogfooding**:

Local pre-push hook installed in `/Users/bartnes/Repos/mycelium/.git/hooks/pre-push` and `/Users/bartnes/Repos/mycelium-roadmap/.git/hooks/pre-push` as part of shipping this version. Per-clone state, not in git. Catches my own failures going forward; would have caught both 2026-05-15 CI failures locally.

**Watched for**:
- Recurrence of "ran one validator, missed the other" pattern on canvas edits. Pre-push hook makes the second validator non-skippable for the cohort that installs it.
- False-positive rate. If `validate_canvas.py` becomes too slow as canvas grows, pre-push pain compounds. Currently ~1s on 25-file canvas; acceptable. Calibration trigger: >5s.

PATCH per version-discipline: new reference artifact + docs section; no schema change, no skill change, no behavior change for downstream users beyond capability discoverability.

## v0.23.19 — Canvas-write Preflight: ID-scan discipline (graduated from comp-010 collision)

**2026-05-15. Attribution: lived-friction-triggered.** On 2026-05-14, the agent (this assistant) added `comp-010 "Harness engineering"` to `mycelium-roadmap/.claude/canvas/landscape.yml` without scanning the existing ID space. `comp-010` was already taken (Anthropic Outcomes, added 2026-05-07). Duplicate persisted ~24 hours in the working tree and on GitHub, caught only when adding a subsequent component (`comp-013 Semantic Anchors`) forced an ID-space scan.

**Detection mechanism already existed**: `validate_canvas.py` lines 230-239 do per-file ID uniqueness with explicit list-not-set discipline (corrections.md 2026-05-04). The check would have fired. It didn't, because the validator only ran in the framework repo's CI — not against the roadmap repo where the canvas data lives.

**Gap was enforcement timing, not detection.** Three graduation candidates identified:
- (A) Doc-only — extend the Preflight rule to require ID-scan before adding ID-bearing entries. Cheapest. Ships with the framework.
- (B) PostToolUse hook — extend `post-write-nudge.sh` to run `validate_canvas.py` against `.claude/canvas/` on canvas Edits. Mechanically enforced. Adds runtime cost.
- (C) Both A and B (belt-and-suspenders).

**v0.23.19 ships A.** B deferred to v0.23.20 candidate pending validator-runtime calibration as canvas grows. Sequencing them avoids bundling unrelated risk surfaces.

**Rule addition** to the Preflight (canonical block in CLAUDE.md + 22 canvas-writing SKILL.md files, byte-identical via script):

> **ID-bearing entries — scan the ID space before assigning.** When adding a new component, opportunity, solution, or any other ID-bearing entry to a canvas file, run `grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u` first and pick the next free integer.

**Classification**: kin to anti-pattern #8 (Stale State Read) — agent reads enough of the file to satisfy the Edit check but not enough to see existing ID assignments. The v0.23.18 `limit:1` discipline made it easier (fewer tokens) to do the Edit check at minimum cost — and easier to miss the broader context needed for ID allocation. Sharpening pays for the cheap shortcut.

**Worked example** logged in roadmap-repo `.claude/memory/corrections.md` (2026-05-15 entry, commit 2cdfb42). Recurrence count: 1; structural failure shape ≥4 (anti-pattern #8 family).

**Check 31 unchanged**: matches on the `## Preflight: Read target canvas file` heading; rule body sharpened underneath. No validator change.

PATCH — doc-only sharpening of an existing discipline; no schema change, no behavior change for downstream users beyond the new convention prose.

## v0.23.18 — Read-before-Write: limit:1 discipline for Edit (~10–50k tokens/session saved)

**2026-05-14. Attribution: lived-friction-triggered.** The v0.23.x Preflight discipline correctly solved the surface-confusion failure (Bash `head` ≠ Read tool, anti-pattern #7 instance #5, 2026-05-09) but introduced a second-order cost: the agent over-applied "Read before Write" as "full Read before every Edit." With canvas files at 800+ lines (~20k tokens each), per-Edit full-Reads were dominating session token cost — meaningful on Pro-tier sessions where the 5h window already strains under Mycelium's load.

**Mechanism**: Claude Code's read-state tracking is per file, not per byte. `Read(limit:1)` registers the file at ~50 tokens and unblocks subsequent `Edit` calls anywhere in it. Verified experimentally 2026-05-14 (Read line 1 of a 5-line file, then Edited line 3 successfully).

**Rule sharpening**:
- **`Edit`** (exact-string replacement): `Read(limit:1)` satisfies the check. Use for partial updates against large canvas files.
- **`Write`** (full replacement): full Read still required. Write obliterates the file; you should see what you're about to replace. The shortcut is *not* appropriate here — safety motivation preserved.

**Shipped to**:
- `CLAUDE.md` — canonical rule under "Canvas writes — Read before Write (HARD RULE)"
- All 22 canvas-writing SKILL.md Preflight blocks (byte-identical replacement via script — no per-skill drift risk)

**Estimated savings**: 10–50k tokens per session, ongoing, every Mycelium user. Compounds across the install base.

**Check 31 unchanged**: validator still matches on the `## Preflight: Read target canvas file` heading. The rule body sharpened underneath; structural enforcement layer keeps passing.

**Third entry in the 2026-05-14 framework-health cycle**: pairs with v0.23.16 (framework-on-framework exemption) and v0.23.17 (Hashimoto + Torres external-validation citations).

PATCH — rule clarification + cost optimization; same discipline, documented cheap path.

## v0.23.17 — Citations: Hashimoto (harness engineering), Torres (AI-generated OSTs)

**2026-05-14. Attribution: external-validation-triggered.** Two convergent external signals dated 2026-05-13:

1. **Teresa Torres** ("Behind the Scenes: Building AI-Generated Opportunity Solution Trees", producttalk.org): the canonical OST source now ships AI-generated OSTs via Vistaly, generated *from* customer interview transcripts (3 → 16+). Reinforces `/mycelium:ost-builder`'s "never from brainstorming" rule with canonical-source convergence. Torres's service also surfaces a structural gap Mycelium has not yet implemented: when updating an OST from new evidence, emit a change set (add/delete/reframe/merge/split) alongside the new tree so users can accept/modify/reject each move. Logged as L3 backlog; out of scope for this PATCH.

2. **"Harness engineering" as the fourth paradigm of AI engineering** (TechTimes 2026-05-13, citing Mitchell Hashimoto's Feb 2026 blog post and Ryan Lopopolo's 2026-02-11 OpenAI definition). Hashimoto's principle — *"anytime you find an agent makes a mistake, engineer a solution such that the agent never makes that mistake again"* — names the discipline Mycelium's `corrections.md → cluster → mechanism` graduation loop implements directly. Stanford/Tsinghua research cited in the same piece reports 6x performance gaps from harness design alone with the model held constant.

Two citation edits to shipped framework files:
- `engine/cycle-learning.md` — Hashimoto + Lopopolo citation under the framework-on-framework exemption section (paired with the v0.23.16 mechanism).
- `skills/ost-builder/SKILL.md` — Torres-Vistaly citation under Theory Citations; OST-update-with-change-set gap flagged as L3 backlog.

Canvas evidence entries (landscape.yml component for "harness engineering"; purpose.yml evidence sources) land in the roadmap-repo canvas, not here — per the framework-on-framework exemption shipped at v0.23.16.

README / positioning rewrite ("Mycelium is a **theory-grounded** harness for product development") deferred to a deliberate L5 marketing diamond.

PATCH — citation additions to shipped docs; no schema change, no new validator check, no behavior change for downstream users.

## v0.23.16 — Framework-on-framework exemption for `/framework-health`

**2026-05-14. Attribution: lived-friction-triggered.** `/mycelium:framework-health` was returning early on N=0 cycles when run against this repo, because Mycelium dogfoods itself and framework improvements don't fit the OST→ICE→launch cycle schema. The actual learning signal lives in `corrections.md` graduation (21 corrections → mechanisms; Checks 30–34 are recent examples) and `cluster-instances.md`, not in `cycle-history.yml`.

Step 1 of the skill now detects the framework-self-host case (`plugins/mycelium/.claude-plugin/plugin.json` present AND `CLAUDE.md` starts with `# Mycelium:`) and routes to a corrections-graduation summary, skipping cycle-derived dimensions while still running the non-cycle-gated steps (2b router-discipline re-run, 4b cluster graduation, 4c receipts rotation, 4d docs health).

Exemption documented in `engine/cycle-learning.md#framework-on-framework-exemption` with the reconsider trigger: if Mycelium gains a second product surface (e.g., a hosted service) whose delivery fits the cycle shape, the framework-meta work moves to a parallel `framework-cycle-history.yml`. Until then, corrections graduation is the ledger.

PATCH — skill routing + doc clarification; no schema change to `cycle-history.yml`, no new validator check, no behavior change for non-self-host downstream users.

## v0.23.15 — Check 34: CLAUDE.md ≤ 1 version entry (mechanism graduation)

**2026-05-14. Attribution: lived-friction-triggered.** Graduates the discipline failure surfaced at v0.23.14 (deferred-entries-not-migrated, recurred ×5 in one session) from vigilance to mechanism. New validator check counts `^\*Version [0-9]` lines in CLAUDE.md; fails if more than 1. Latest entry stays; prior entries migrate to this file.

Pairs with Check 30 (plugin.json#version tracks CLAUDE.md) as the doc-discipline-fast-failure family. This commit dogfoods the new check by migrating v0.23.14 out (swap, not append). PATCH — observability-and-mechanism-strengthening; no behavior change for downstream users (`tests/` doesn't ship via the plugin).

## v0.23.14 — Doc-only: regenericize architecture narrative + migrate deferred entries

**2026-05-14. Attribution: lived-friction-triggered.** Two coalesced fixes flowing from the same discipline: keep deferred versions and private-architecture details out of CLAUDE.md.

1. **Forward-only regenericization** of changelog entries that named a private companion repo by path while describing v0.23.13's registry-move fix. Generalizes v0.23.13's lesson one step further: commit messages and changelog text are public-disclosure surfaces even when discussing the architecture that *supports* privacy discipline.
2. **Migrated v0.23.9 through v0.23.13** entries out of CLAUDE.md per the established convention (CLAUDE.md keeps only the current release). Five consecutive bumps this session each violated that discipline; the failure replicated forward without being noticed. Recurring-pattern graduation candidate.

Git history retains original phrasing in `c539f29` and earlier; working-tree view is now generic. PATCH per version-discipline.

## v0.23.13 — Cohort-attribution leak fix + Check 33 architecture correction

**2026-05-14. Attribution: lived-friction-triggered.** Regenericized the last Check-33 leak in `plugins/mycelium/harness/anti-patterns.md` (the date-tagged source citation that named a private-channel observer). Also collapsed an adjacent friction-log attribution to its theoretical-lens framing for consistency. Architecture correction for Check 33 / attribution-registry placement: initial 0.23.12 ship put the registry in this public repo, which was self-defeating (registry contains the very names whose private attribution it tracks). Moved out. Check 33 now resolves the registry via `$MYCELIUM_ATTRIBUTION_REGISTRY` env var; fail-open if unset.

Acknowledged residual: prior public-repo references to the same individual remain in commit history and existing changelog entries. Scrubbing fully would require git history rewrite — higher cost than the marginal incremental exposure. Forward leaks into the plugin tree are now mechanism-prevented; historical references are accepted residual.

PATCH.

## v0.23.12 — Check 33: plugin tree must not contain unconsented personal identifiers

**2026-05-14. Attribution: lived-friction-triggered.** Trigger: in-session user-asked whether a repo-root canvas file could leak into downstream user projects. The literal answer was no (plugin scope is `./plugins/mycelium/`), but the deeper question (whether names embedded in plugin-shipped files leak) surfaced 5 unconsented references in `plugins/mycelium/harness/anti-patterns.md` and `plugins/mycelium/harness/theory-tensions.md`.

**Mechanism shipped:** new validator Check 33 reads an attribution registry (kept outside the public repo) listing each known individual's consent state (`public_ok` | `generic_only` | `unknown`). The check scans `plugins/mycelium/**` for `generic_only` and `unknown` names via word-boundary regex across `.md`, `.yml`, `.yaml`, `.json`, `.py`, `.sh`. Adding a name without a consent value fails registry parsing (forces deliberate consent decisions). WARN-only initially per observability-before-enforcement discipline.

**Deeper lesson:** lived-friction attribution can leak through the graduation chain even when the source is generic-framed at point of capture. Capture-time discipline is necessary but not sufficient — every step from corrections → anti-patterns → engine docs that cites trigger sources is itself an attribution surface. GDPR data-minimization applied to internal framework documentation, not just user data.

Borderline-MINOR (new gate) but PATCH defensible because it lands WARN-only and strengthens existing G-V12 + version-discipline.md anti-leak intent rather than introducing new theory.

## v0.23.11 — Ruff cleanup pass on verify_citations.py

**2026-05-14. Attribution: lived-friction-triggered.** Check 17's 20-error WARN was sitting as de-facto indefinite tech debt with no entry in any `warnings-log.md` and no trigger condition — quiet violation of `feedback_no_tech_debt_deferral.md` ("never indefinite"). Ran validator's own ruff invocation: 4 auto-fixed via `--fix`, 17 manually fixed in `verify_citations.py` (SIM103 ×2, PLW2901, S110+BLE001 narrowed, RET504, PERF401, 9× E501 via implicit string concatenation, EXE001 chmod +x). All 14 unit tests still pass; behavior unchanged. Check 17 returns to 0 errors.

PATCH per version-discipline.md line 11 (explicit "ruff cleanup" listed as PATCH-class).

## v0.23.10 — Migration-skill truth-up + retroactive bump

**2026-05-14. Attribution: lived-friction-triggered.** Two changes coalesced because the second surfaced the first.

1. **`plugins/mycelium/skills/migrate-from-legacy/SKILL.md` Step 7 corrected.** Triggered by per-turn `No such file or directory` hook errors from a stale `"hooks"` block in `.claude/settings.local.json`. SKILL.md previously claimed the legacy migration script warned on both `settings.json` and `settings.local.json`; reality is `settings.json` only. SKILL now owns the dual-file grep itself. Considered-and-reverted: a 130-line `--migrate-to-plugin` flag handler in the plugin's `upgrade.sh` — reverted after archaeology showed the plugin copy is by-design never invoked for migration (legacy users run their local `.claude/scripts/upgrade.sh`).
2. **Retroactive bump for `2f0b003`.** The SIGPIPE fix to Check 10 landed without a version bump; validation appeared to pass because the SIGPIPE bug itself was aborting the script at Check 10 with exit 2 before Check 26 (version-bump-discipline) ran. Fixing the SIGPIPE structurally unmasked the check that would have caught its own missing bump — observer effect.

Lesson candidate for `version-discipline.md`: test-suite fixes that change which downstream checks run are structural changes to the validator's observable behavior, not cosmetic. Worth a sentence next time that doc is edited.

PATCH.

## v0.23.9 — First-run friction batch (9 patches)

**2026-05-13. Attribution: lived-friction-triggered.** Behavior-validated cautious-learner first-run observation surfaced 7 framework opportunities (opp-001 through opp-007); 5 mechanism patches shipped across hooks, skills, and README.

**Specific changes:**
1. `plugins/mycelium/hooks/stop-check.sh` — no longer emits per-turn "Session ended" line when counts are zero (opp-003 closed).
2. `plugins/mycelium/hooks/preflight.sh` + `session-start.sh` — count-display lines disambiguate three states (memory not initialized / empty / N corrections) (opp-001 partial).
3. `plugins/mycelium/skills/setup/SKILL.md` — AGENTS.md prompt rewritten with say-yes-vs-skip framing before the question (opp-002a partial).
4. `README.md` — time-budget routing description aligned with current Universal Brief Flow (opp-002b partial).
5. `plugins/mycelium/skills/interview/SKILL.md` — confidence-0.15 rationale rewritten from "hardcoded floor" framing to canvas-density formula breakdown; DEFERRED block restructured to partial-graduation checkbox status (opp-004 partial).
6. `interview/SKILL.md` brief flow — adds post-write line surfacing auto-tagged `source_class` choice + revise-path; names all five source classes (opp-005 partial).
7. `interview/SKILL.md` + `start/SKILL.md` — NARRATION DISCIPLINE block forbidding phase-number narration to users with ✗/✓ examples (opp-006 partial).
8. `interview/SKILL.md` friction-log prompt — three explicit destinations and consent gates (opp-007 closed).
9. `tests/validate-template.sh` Check 32 wrapper bug fixed (set +e / set -e around rc capture so WARN is actually WARN).

PATCH per version-discipline: all changes are bug fixes, clarification copy, or framing precedent-setting; no new skills, no new gates, no backwards-incompatible behavior.

## v0.23.8 — C1: read-log + verify_citations attack anti-pattern #7 Level 3

**2026-05-11. Attribution: lived-friction-triggered.** Triggered by Supra Insider ep 110 surfacing Apurva Garware describing the exact failure shape ("agent silently used scripts instead of skills + fabricated explanation when probed"); cross-mapped to same-day cluster activity (three fresh framing-shape instances) + deep-dive analysis decomposing the failure into four levels (skipped read / skipped steps / fabricated inputs / fabricated outputs). C1 is the bounded-cost preventive attack on Level 3 (fabricated underlying inputs in citations).

**Two new artifacts:**

1. **`plugins/mycelium/hooks/read-log.sh`** — PostToolUse hook on `Read` tool. Mirrors `change-log.sh` pattern. Appends one JSONL line per Read tool use to `.claude/state/read-log.jsonl` with schema `{ts, tool, file_path, session_id, diamond_id?}`. Fail-open (logging failure never blocks reads). Sister to `change-log.sh` — together they answer "what did the agent claim to read, read, and write during session X?"

2. **`plugins/mycelium/scripts/verify_citations.py`** — standalone Python stdlib script. Extracts `(per: <source>)` citations from agent text, classifies file-shaped vs concept-shaped via path heuristic (slash or known extension), cross-references file-shaped citations against read-log via suffix matching. Reports verified / unverified / unverifiable counts. Explicitly frames "unverified ≠ fabricated" with 4 legitimate-reason scenarios enumerated.

**Test coverage (G-V12):** 14 unit tests in `tests/python/test_verify_citations.py`. All pass. File-shape heuristic, citation extraction with dedup, suffix matching (positive + no-false-positive on `scape.yml` vs `landscape.yml`), all-verified, unverified-caught (load-bearing), concept-routing, session-id filter, missing-read-log fail-open, malformed-JSONL fail-open, end-to-end anti-pattern-7 scenario, human-format, main CLI.

**Sister observability shipped same version**: `plugins/mycelium/engine/consistency-check-spec.md` gains a "Preemptive convention registry" subsection naming the skill-folder-layout convention (one SKILL.md per dir, no helper scripts) as held-by-discipline-not-mechanism. First violation triggers graduation to validator check. Audit confirmed clean across all 49 skill dirs.

**What C1 does NOT catch**: Level-2 framing-shape instances (mechanism-vs-value language, leading-question violations, transactional-vs-relational framing). These don't reference files, so the script is structurally blind. Three such instances surfaced same day; C1 is necessary but not sufficient. **C2 (skill-execution fingerprints) and C3 (external witness)** logged as Tier 2 candidates in private follow-up drafts with concrete graduation triggers.

**Manual invocation only for initial ship.** Automatic Stop-hook integration deferred per Mycelium's observability-before-enforcement discipline.

MINOR per version-discipline (additive observability infrastructure; new PostToolUse matcher on Read; no breaking changes; no behavior change beyond logging + on-demand verification).

## v0.23.7 — Count-drift correction across surface docs

**2026-05-11. Attribution: maintenance-housekeeping.** Count-drift correction surfaced by a peer-agent fact-check during outreach drafting (the agent claimed "the public README confirms 32 anti-patterns" — no such number exists anywhere in the framework; grep-verification caught the fabrication; sister anti-pattern #7 instance #9 to yesterday's BDSK case).

Drift swept across all surface docs:
- **Skill count 45 → 49** (README.md ×2, docs/README.md, docs/skills/by-category.md ×2, .claude-plugin/marketplace.json).
- **Theory-gate count standardized to 13** (was "12" in marketplace.json, "15" in plugin.json — actual count per `engine/theory-gates.md` is 13: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service & Usability Quality, DORA/Delivery Metrics, Corrections, Regulatory, Explainability/XAI).
- Minor redundant phrasing fix in `docs/skills/README.md` ("49 skills (49 skills total)" → "49 skills").

Historical references in `docs/changelog.md` and `docs/receipts/cases/2026-05-08-bentes-install-model.md` deliberately preserved (they cite the count *at that point in history* — correct as historical record).

No anti-pattern count claim in any surface doc — the "32" was fabricated by the peer agent and didn't propagate into Mycelium content. Actual numbered anti-pattern count: 46 across 10 cluster sections.

PATCH per version-discipline (mechanical correctness fix; no new mechanism). Validator: 29 passed, 0 failed, 2 warnings (both pre-existing). Tier 3 candidate for future Validator Check 33 surfaced: skill/gate count consistency between plugin.json description, marketplace.json description, and actual `plugins/mycelium/skills/` + `engine/theory-gates.md` content — would catch this drift class mechanically. Tracked in `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` Tier 2 (count drift is a specialized case of the broader confidence-evidence-coupling validator candidate).

## v0.23.6 — Security strengthening: threat model + memory-poisoning surveillance + OWASP citations

**2026-05-11. Attribution: mixed (research-while-here + lived-friction-triggered).** Triggered by an in-session security deep-study request + a same-day anti-pattern #7 instance #9 (subagent-output-verification sub-class, BDSK-fabrication caught by user prompt). Three coordinated changes:

**(1) New `docs/threat-model.md`** — consolidated entry point for "what attacks does Mycelium worry about, and what does it do about them." Captures 7 Mycelium-specific threats (T-M1 Memory Poisoning, T-M2 Indirect Prompt Injection, T-M3 Secret Leakage, T-M4 Hook Tampering, T-M5 Sub-agent Escalation, T-M6 Audit-Trail Laundering, T-M7 Marketplace-Install Trust) structured against OWASP Top 10 for LLM Applications 2025 + OWASP Agentic AI Threats and Mitigations Feb 2025. Cross-references existing scattered pieces (harness/security-trust.md, docs/ai-system-card.md, anti-patterns.md cognitive cluster, harness/context-management.md sister doc). External-reviewer-shaped — primary audience is auditors who shouldn't have to assemble the answer from five files. Attribution: research-while-here.

**(2) New SessionStart hook Check 7 — memory-poisoning surveillance.** Watches recently-changed (<7 days) `.claude/memory/*.md` and `.claude/harness/decision-log.md` for imperative-shaped bullet content (`Run`, `Execute`, `Delete`, `Send`, `Curl`, `Wget`, `Push`, `Force`, `Disable`, `Bypass`, `Skip`, `Ignore`, `Override`, `Fetch`, `Download`, `Install`, `Eval`, `Exec`) as PR-shipped-instruction signal. **Observability, not enforcement** — surfaces a warning, not a block. Conservative detection (low FP at cost of missed catches). Addresses OWASP Agentic T1 (Memory Poisoning) which was unmitigated at framework layer prior to this ship; the receipts/contributors-as-recognition GTM mechanism (landscape.yml#strategic_frame) deliberately creates an inbound contribution pathway for memory files — the structural defense follows the structural decision. Attribution: lived-friction-triggered (the 2026-05-11 BDSK-fabrication anti-pattern #7 instance + the receipts mechanism design are the load-bearing triggers).

**(3) Citation backfills in `harness/security-trust.md`** Prompt-Injection Defense section — OWASP LLM Top 10 (2025) explicit (LLM01/02/05/06 named as load-bearing four for agentic dev-tool harness) + OWASP Agentic Threats (T1/T2/T15) added + Anthropic prompt-injection-defenses 2026 (substrate-layer RL refusal ~1% attack success on Opus 4.5) + Microsoft Spotlighting paper (arXiv 2403.14720, three techniques: delimiting/datamarking/encoding) as primary source. Tag-wrapping convention explicitly framed as folklore-grade alone, compounds with substrate defense rather than replacing it. Attribution: research-while-here.

PATCH per version-discipline (additive doc + new hook check + citation backfills; no new enforcement mechanism — the memory-poisoning warning is observability). Roadmap-side draft `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` tracks Tier 2 (6 candidates) and Tier 3 (5 deferred items). The 2026-05-11 anti-pattern #7 instance #9 (subagent-output-verification sub-class, BDSK-fabrication caught by user prompt) is logged in `mycelium-roadmap/.claude/memory/corrections.md` and `cluster-instances.md` (instance count 6+ → 7+).

## v0.23.5 — Context-rot defense layer doc + per-graduation attribution discipline

**2026-05-10. Attribution label: `research-while-here`.** Triggered by an in-session research request on context rot for AI agents (specifically Claude). Three coordinated changes: **(1) New harness doc `harness/context-management.md`** codifying Mycelium's structural defense against context rot — six rot mechanisms (lost-in-the-middle, attention dilution, instruction drift, NIAH degradation, compaction loss, prompt-cache bloat) mapped against existing Mycelium defenses (phase-scoped loading, JiT detection, two-memory system, Read-before-Write, canvas as SSOT, externalize-everything). Explicitly names the **blind subagent pattern** as a context-rot defense. Calls out Claude-specific findings: Claude is *especially* sensitive to irrelevant surrounding context per Chroma's 18-model study (largest performance gap between focused vs full-context prompts on LongMemEval), making Mycelium's discipline of phase-scoped loading particularly Claude-suited. Lists known gaps (prompt-cache strategy, conversation-length detection, instruction-budget calculation rules, coherent-haystack risk) without graduating speculative defenses. Primary sources: Liu et al. 2023 (arXiv:2307.03172) — peer-reviewed for U-curve attention; Chroma "Context Rot" 2025 — empirical 18-model study; NVIDIA RULER (NeurIPS 2024); Anthropic Engineering "Effective context engineering for AI agents" + Claude Code postmortem 2026-04-23 (worked failure case where compaction logic fired every turn). **(2) Citation backfills**: Recency Bias in Context (`harness/cognitive-biases.md`) cites Liu 2023 + cross-references Knowledge Reconstruction Tax + the new doc; Cognitive Offloading Loop + Knowledge Reconstruction Tax (`harness/anti-patterns.md`) cite Chroma 2025 + cross-reference each other and the new doc. The symptomatic-bias and structural-anti-pattern now sit beside each other in the agent's mental model. **(3) Per-graduation attribution discipline**: new section in `engine/version-discipline.md` requires every Version line to include a dominant attribution label (`lived-friction-triggered` / `research-while-here` / `maintenance-housekeeping` / `scheduled-discipline`); new Work-Mode Mix section in `engine/feedback-loops.md` defines the four modes + when each is fine vs risky. Surfaced 2026-05-10 in-session as the discipline that closes a meta-instance of anti-pattern #7 at the graduation-velocity layer (one genuine lived-friction trigger from earlier in the day extending into a session-long streak via consistency rather than per-graduation attribution). PATCH per version-discipline. Connection to lived-friction: medium — today's CLAUDE.md restructure (51k → 17.9k) was implicit attention-budget management; today's 4-bump session is the multi-turn agent-loop scenario the research describes; meta-instance of anti-pattern #7 surfaced the graduation-velocity failure surface concretely.

## v0.23.4 — Seven primary-source citations from Laws-of-Software-Engineering gap analysis

**2026-05-10.** Same playbook as v0.23.2 (CBI graduations); 7 Tier-1 candidates from a 56-law catalog (lawsofsoftwareengineering.com, Milan Milanović) graduated as primary-source citations on existing surfaces. **Hyrum's Law** (Wright et al. *Software Engineering at Google* 2020) → `engine/version-discipline.md` Theory grounding, articulating why version-bump discipline is load-bearing in plugin-form install. **Postel's Law / Robustness Principle** (RFC 793, Postel 1981) → `engine/consistency-check-spec.md`, retroactive citation for the 0.16.2 schema fix accepting both `source_class` and `source_classes`. **Leaky Abstractions** (Spolsky 2002) → `engine/version-discipline.md`, citing the bare-path sweeps (v0.20.7 + v0.23.3) as instances. **Tesler's Law of Conservation of Complexity** → `jit-tooling/detector.md`, articulating the JiT philosophy. **Gall's Law** (Gall *Systemantics* 1975) → `engine/framework-reflexion.md`, naming the mechanism-graduation discipline. **Cunningham's Law** → `/devils-advocate` as Technique 6 (publish-rough-then-iterate). **Brooks's Law** (Brooks *Mythical Man-Month* 1975) → `domains/delivery/CLAUDE.md` Theory of Constraints section with AI-assisted variant. Three citations (Hyrum, Postel, Leaky Abstractions) connect directly to lived-friction from the same week. PATCH per version-discipline (citation additions on existing surfaces; no new mechanism). 15 Tier-2 candidates tracked in `mycelium-roadmap/.claude/drafts/lawsose-gap-followups.md` for trigger-driven graduation.

## v0.23.3 — Bare-path discipline sweep (round 2)

**2026-05-10.** Trigger: mycelium-roadmap dogfood ran `/mycelium:metrics-pull` and the skill failed to find adapters because `metrics-pull/SKILL.md` referenced `metrics-adapters/<source>.md` as a bare path that resolves relative to user project root, not the plugin tree. v0.20.7's first-level sweep covered top-level dirs (`engine/`, `harness/`, etc.) but missed sub-directory paths and several cross-plugin-tree refs. Audit fixed two classes: **(1) `metrics-adapters/` references** — 18 sites across `metrics-pull/SKILL.md`, `metrics-detect/SKILL.md`, `interview/SKILL.md`, `jit-tooling/metrics-detector.md`, and the four files inside `jit-tooling/metrics-adapters/` itself (TEMPLATE.md, github.md, GENERATING.md, active-metrics.example.yml). **(2) Cross-plugin-tree refs in framework files** — 12 sites in `harness/anti-patterns.md`, `orchestration/operations.md` + `orchestration/modes.md`, `engine/leaf-lifecycle.md`, `engine/feedback-loops.md`, `engine/xai-canvas-threading.md`, `corrections-audit/SKILL.md`. All routed correctly: framework-resident → `${CLAUDE_PLUGIN_ROOT}/<dir>/`, project-state → `.claude/<dir>/`. Glob patterns in prose, GitHub-rendered markdown links, and `setup/SKILL.md` AGENTS.md template body bullets (under `.claude/` section header) deliberately preserved as bare. Same class as v0.20.7; triggered by real lived-friction (the metrics-pull skill failed visibly during dogfood) — same epistemic structure as the 0.20.11 plugin-form findings: subagent simulations miss what real invocation surfaces. PATCH per version-discipline (mechanical content rewrite, correctness fixes; no new mechanism).

## v0.23.2 — Five bias-mitigation citations from CBI gap analysis

**2026-05-10.** mycelium-roadmap dogfood (gap analysis against cognitivebiasindex.com) surfaced 6 candidate bias additions; pre-ship Read found 1 already present (Dunning-Kruger in L1+L4), 5 graduated as additive citations on existing surfaces. **Illusion of Validity** (Kahneman 2011 ch. 20) added to anti-pattern #7 source line as the established academic name for *Consistency-as-Evidence*. **Curse of Knowledge** (Camerer, Loewenstein & Weber 1989) added as a row to the L2 Opportunity-stage table in `harness/cognitive-biases.md` — founder-vocabulary risk in user interviews. **Hindsight Bias** (Fischhoff 1975) added as a new "Hindsight Bias Check" section in `/retrospective` SKILL.md — counters "we should have seen X coming" rewriting uncertainty as foreknowledge. **Hyperbolic Discounting** (Laibson 1997) added to `/ice-score` Step 5 bias check — near-term Impact overweighting at the expense of longer-horizon outcomes. **Decoy Effect** (Huber, Payne & Puto 1982) added as a Rule in `/ost-builder` — no decoy solutions whose only purpose is to make a preferred option look better. CBI's 14 "tools" all map cleanly to existing Mycelium mechanisms (decision-log, /devils-advocate, /fan-out, /assumption-test, etc.) — no method-level borrowing recommended. User overrode the draft's "wait for real failure" promotion bar; override logged in `mycelium-roadmap/.claude/drafts/cbi-gap-followups.md`. PATCH per version-discipline (additive citations + 1 new table row + 1 new mitigation section in existing skill; no new mechanism, no behavior change beyond the named-and-mitigated biases).

## v0.23.1 — CLAUDE.md restructure

**2026-05-10.** Version history (0.16.0 → 0.23.0) moved from CLAUDE.md into this changelog. CLAUDE.md was 67k chars / 262 lines, with the version preamble alone consuming ~55k. Behavioral content unchanged. Current-version line preserved as Check 26 trigger + agent priming. PATCH per version-discipline (doc-only restructure; no new mechanisms).

## v0.23.0 — Team Topologies multi-agent dogfood findings

**2026-05-09.** Five parallel subagents in isolated git worktrees (3 stream-aligned + 1 platform + 1 stream cross-team) with mechanism-only scoping; social/cognitive findings tagged speculation and discarded at fan-in per anti-pattern #7. Two-agent independent corroboration on F1/F2/F4. **F1 (schema gap, doc-only):** `docs/philosophy.md` adds "What Mycelium does not yet do (single-team scope cut)" naming the deliberate constraint that data + orchestration models assume one author/team/diamond-flow at a time; Team Topologies vocabulary is described content (`/mycelium:team-shape`, L1 strategy table, `team-shape.yml`), not operational discriminator. Four absences named (no `owned_by_team`, no stream→platform request primitive, no interface-contract doc, silent semantic overwrite on multi-author writes). Trigger for revisiting: real adopter brings a two-team setup. **F6 hot-fix (hook deadlock):** `framework-guard.sh` tries `${CLAUDE_PLUGIN_ROOT}/scripts/framework_guard.py` first then falls back to legacy `.claude/scripts/`; legacy path was hardcoded post-0.20.x → bootstrap deadlock. Same hook gains MCP filesystem coverage (`mcp__filesystem__write_file|edit_file|move_file`) — bypass surfaced during dogfood. `framework_guard.py` gains `_handle_mcp_filesystem_path` + `_handle_mcp_filesystem_move` (move handler checks both source + destination). **F8 (Validator Check 32):** `check_four_risks_when_active()` enforces that opportunities referenced by active diamonds have populated `value/usability/feasibility/viability.level` fields. Closes the false-negative gate where `/mycelium:diamond-progress` step 2 vacuously passed when levels were absent. WARN-level initially. **F4 (cluster ledger):** Three new instances of `documented-rule-diverges-from-enforcement` cluster (10/11/12); total 9 → 12; spec-graduation status preserved. MINOR per version-discipline. Theory: Skelton & Pais *Team Topologies*; preferred-blind-subagent-assumption-test pattern; subagent-simulation ≠ lived-friction caveat.

## v0.22.0 — Behavioral enforcement layer for anti-pattern #7

**2026-05-09.** Documentation-only graduation (0.21.0) shipped the named anti-pattern + /devils-advocate Technique 4 + /corrections-audit Step 6d + G-P-pre item 9, but FIVE instances of the same self-application failure occurred in one session post-graduation — TWO within the same hour. Documentation does not produce behavior; structural enforcement does. **F1:** Every canvas-writing SKILL.md (22 skills) gains a `## Preflight: Read target canvas file(s) before any Write/Edit` block naming the failure mode (head/cat/grep via Bash do NOT satisfy the Read-before-Write check), the cost (~14k tokens per failure cycle), and the citation. **F2:** New Validator Check 31 scans Update/Write/Append-mentioning SKILL.md files against `.claude/canvas/*.yml` and verifies the Preflight marker is present (currently passes for all 15 canvas-writing skills; WARN if any future skill ships without it). **F3:** CLAUDE.md "Canvas writes — Read before Write" rule strengthened with explicit HARD RULE label + cost framing; `/mycelium:diamond-assess` Step 3 now carries a Read-before-claim hard rule. MINOR per version-discipline. The anti-pattern's own graduation surfaced exactly the structural enforcement layer Argyris double-loop predicts.

## v0.21.1 — Hygiene patch (plugin.json drift + Check 30)

**2026-05-09 (commit `72bada4`).** 0.21.0 ship missed bumping `plugins/mycelium/.claude-plugin/plugin.json` (still at 0.20.11 while CLAUDE.md was at 0.21.0). Same coupled-field drift class as the 0.20.x dogfood B2 finding but at MINOR-bump scale. plugin.json bumped to 0.21.1 (tracks CLAUDE.md exactly). New Validator Check 30 enforces the invariant going forward (parses leading `*Version` line from CLAUDE.md and `version` from plugin.json, fails on drift). PATCH per version-discipline.

## v0.21.0 — Three anti-pattern graduations

**2026-05-09.** **(#7) Consistency-as-Evidence:** constructing causal chains where ≥1 link rests on observational consistency rather than verified attribution. Three documented instances (2026-04-30 Hoskins over-scoping, 2026-05-03 sharper-framing anchoring, 2026-05-09 cohort-log verbosity-attribution gap). Distinct from confirmation bias (attention-direction failure) — this is attribution failure (misclassifying evidence in hand). Source: Pearl causal inference. **(#8) Stale State Read:** scripts/validators reading state files the same operation is about to replace, producing nominally-correct output against the wrong reference. Four documented instances. Worked example: `parse_manifest.py --manifest=<path>`. **Bias cluster → ambient `/devils-advocate`:** "agent prefers what feels right over what evidence supports" graduated as Techniques 4 (attribution-vs-consistency labeling) and 5 (ambient triggering on assertion-shaped patterns) — converts anti-bias discipline from per-decision ceremony to per-publish self-check. Plus integration: `/corrections-audit` Steps 6d/6e, validator Check 29, CLAUDE.md G-P-pre item 9. MINOR per version-discipline.

## v0.20.15 — Legacy install path deprecated + manifest single-source

**2026-05-09 (commit `1e592f0`).** Three coordinated changes. **(1)** Legacy `npx degit` install path explicitly deprecated; README's "Legacy install" subsection rewritten as deprecation notice (a fresh degit lands an empty `.claude/` with no skills/hooks/engine). Removal scheduled for v0.21.0 / 2026-06-09. **(2)** Stale-upstream detection in `upgrade.sh` legacy refresh mode: when upstream tree has no `.claude/skills/` or `.claude/engine/`, exits with "the canonical Mycelium has moved to plugin form" message recommending `--migrate-to-plugin` or `/mycelium:migrate-from-legacy`. **(3)** `docs/migration.md` gains "Recovering from a broken legacy refresh" section covering four common failure modes. **Manifest dual-source decision:** `plugins/mycelium/manifest.yml` is canonical; `.claude/manifest.yml` is the deprecated legacy copy retained for in-flight migration users (deletion target v0.21.0 / 2026-06-09). New Validator Check 28 enforces byte-equality while both exist. PATCH per version-discipline.

## v0.20.14 — CI restored after legacy `.claude/` cleanup

**2026-05-09 (commit `218477c`).** 0.20.13 migration deleted `.claude/tests/validate-template.sh` + Python tests + auto-dogfood orchestrator, breaking `validate.yml` and orphaning `dogfood.yml`. **(1)** Validator + Python tests rehomed at repo root (`tests/validate-template.sh` + `tests/python/`); REPO_ROOT calc updated; all `.claude/scripts/` references in validator updated to `plugins/mycelium/scripts/`; material_paths in Check 26 stripped of dead `.claude/{skills,engine,harness,hooks,scripts,templates,tests}` entries. **(2)** `plugins/mycelium/manifest.yml` added (copy of `.claude/manifest.yml`) so plugin's `parse_manifest.py` works standalone for `--migrate-to-plugin`. **(3)** `validate.yml` updated to call `bash tests/validate-template.sh`, `python3 plugins/mycelium/scripts/validate_canvas.py`, `pytest tests/python/`; path triggers extended to `plugins/mycelium/**`, `.claude-plugin/**`, `tests/**`, `docs/**`. **(4)** `dogfood.yml` deleted. Validator: 24 passed, 0 failed, 4 warnings. PATCH per version-discipline.

## v0.20.13 — Self-migration dogfood (legacy `.claude/` removed upstream)

**2026-05-09 (commits `7c2a89d` + `e0825be`).** Maintainer ran `--migrate-to-plugin` on upstream and downstream Mycelium repos themselves. **(1)** Legacy `.claude/` framework tree removed from upstream (180 files, 27,464 lines deleted on `chore/legacy-cleanup`); plugin form is now the only Mycelium install path on main. Project state in upstream's `.claude/` (canvas, diamonds, memory, decision-log, evals, drafts, manifest.yml, settings) preserved untouched. **(2)** README.md gains "Heads-up if your install is older than v0.20.10" callout: `--migrate-to-plugin` flag was added in 0.20.10, so older installs misinterpret it as a version arg. Workaround: refresh first, then re-invoke with the flag. PATCH per version-discipline.

## v0.20.12 — Receipts case for plugin-form dogfood

**2026-05-09 (commit `c3cecca`).** New receipts case `docs/receipts/cases/2026-05-09-plugin-form-dogfood.md` capturing: 5 bugs surfaced and closed same-day (B1-B5), the load-bearing L0 adoption assumption ("The harness is light enough that people keep choosing it past the first friction moment"; Cagan four-risks: usability), the operational test design from `/mycelium:assumption-test`, and the framework recusing itself from `/mycelium:bias-check` on its own test design. Lessons: subagent simulation ≠ lived friction; detection-then-route must be a hard gate; variable expansion at Write boundaries is an environment leak; Check 26 must watch manifest files. Receipts indexes updated. PATCH per version-discipline.

## v0.20.11 — Five bug fixes from plugin-form dogfood

**2026-05-09 (commit `5f1b416`).** **B4:** `setup/SKILL.md` warnings-log.md starter content was getting `${CLAUDE_PLUGIN_ROOT}` expanded by the agent during Write, baking the maintainer's absolute path into every user's project. Fixed by switching to prose + explicit "do NOT expand" instruction. **B1:** `start/SKILL.md` Step 2 detection was honored AFTER the agent already ran setup-style `mkdir -p`, causing Read-before-Write tool errors. Fixed by promoting detection to a HARD GATE. **B2:** `plugin.json` version stayed pinned at 0.20.0 while CLAUDE.md moved through 10 patches; ping marker drifted similarly. Fixed: plugin.json bumped to track CLAUDE.md (skill count corrected 45 → 49); ping marker made shape-stable (no version suffix). **B3:** Validator Check 26 watched CLAUDE.md but not `plugin.json` or marketplace.json; `plugins/mycelium/.claude-plugin/plugin.json`, `plugins/mycelium/.claude-plugin/marketplace.json`, `.claude-plugin/marketplace.json` added to material_paths. **B5:** Setup didn't acknowledge `.claude/state/` (Claude Code's runtime state directory). Fixed with one-line note. PATCH per version-discipline. Dogfood also produced the L0 adoption test design at `.claude/evals/assumption-tests/L0-adoption-test.md` (n=5, pre-committed Persevere/Ambiguous/Pivot/Kill thresholds).

## v0.20.10 — Legacy → plugin migration path

**2026-05-08 (commit `34ea768`).** Three coordinated artifacts. **(1)** `.claude/scripts/upgrade.sh` gains `--migrate-to-plugin` flag (deletes legacy framework files, preserves project state — manifest-driven via `parse_manifest.py directories` + `harness_framework`) and `--check-migration` flag (read-only diagnostic). Top-level detection routes plugin-form invocations away from upgrade.sh entirely. **(2)** New skill `/mycelium:migrate-from-legacy` (8 steps: detect form, verify plugin installed, verify clean working tree, render explicit will-DELETE/will-PRESERVE preview à la Liao contrastive XAI, invoke script, verify project state survived, manual settings.json hooks-block cleanup, final commit). Idempotent. **(3)** New `docs/migration.md` with three migration paths (skill, script, manual) + reversibility notes. Skill count 48 → 49. Smoke-tested in `/tmp/migrate-smoketest`: clean delete of 9 framework directories, project state preserved. PATCH per version-discipline.

## v0.20.9 — Validator updated for plugin-form layout

**2026-05-08 (commit `828e6d2`).** Closes "Checks 6/7/9 still expect skills under `.claude/skills/`" pending item from 0.20.5. **(1)** `SKILLS_DIR` detection at top of `validate-template.sh` prefers `plugins/mycelium/skills/`, falls back to `.claude/skills/`, exits 2 if neither exists. **(2)** Every Check (5, 6, 7, 8, 9, 15, 26) threads `$SKILLS_DIR` through; Check 26 watches BOTH plugin and legacy material paths. **(3)** New Check 27 (skills-tree parity): when both trees coexist, compares skill count + name set, WARNs on divergence. New skills `ping`, `setup`, `start` had `description:`-only frontmatter; added `name:` to satisfy Check 8. Skill count 45 → 48. Validator: 24 passed, 0 failed, 5 warnings. PATCH per version-discipline.

## v0.20.8 — Dogfood-mode pattern migrated to plugin tree

**2026-05-08 (commit `96954a2`).** `interview/SKILL.md:285` (and two other surfaces) referenced `.claude/evals/dogfood-reports/README.md` "for the pattern," but plugin-form setup creates only a `.gitkeep` there — dogfood-mode users had no pattern to reference. Framework-reference content moves to plugin (`${CLAUDE_PLUGIN_ROOT}/engine/dogfood-mode.md`); `.claude/evals/dogfood-reports/` in user's project stays empty for their own reports. Updated three references. PATCH per version-discipline.

## v0.20.7 — Bare-path discipline sweep across 45 SKILL.md

**2026-05-08 (commit `70c07fb`).** Smoke-test of 0.20.6 (4 parallel blind subagents) flagged two cross-cutting pre-existing patterns the previous path-rewrite scripts didn't catch: bare project-state paths and bare framework-reference filenames. Both classes brittle once `$CLAUDE_PROJECT_DIR` and `$CLAUDE_PLUGIN_ROOT` split path resolution into two trees. Two-pass sweep: pass 1 prefixes bare project-state with `.claude/` and bare framework filenames (50 unique) with `${CLAUDE_PLUGIN_ROOT}/<dir>/`; pass 2 handles bare `<fw-dir>/X` patterns and routes `harness/decision-log.md` + `harness/warnings-log.md` to `.claude/harness/` (project-state carve-out). 36 files, ~145 path rewrites, 12 decision-log re-routes, 1 typo fix. PATCH per version-discipline.

## v0.20.6 — Onboarding void closer

**2026-05-08 (commit `b5eeb76`).** New `/mycelium:start` combiner skill that runs setup + interview universal-flow in one invocation, with a 30-second welcome (Norman: visible affordances; Krug: don't-make-me-think). `/mycelium:setup` confirmation expanded with one-paragraph welcome + framing of next move. `/mycelium:interview` cherry-picked from `feat/on-ramp` 0.19.1 with universal-flow shape (canvas-state detection + 4-question brief + informed depth menu). README + AGENTS.md: Quick Start now leads with `/mycelium:start`; both surfaces document tab-completion (`/myc<Tab>`) and natural-language invocation. Source: dogfood report 2026-05-09 — "the onboarding has worsened substantially since converting to plugin." PATCH per version-discipline.

## v0.20.5 — Plugin-form path resolution in scripts

**2026-05-07 (commit `0f073b1`).** Subagent re-verification caught that `validate_canvas.py` and `ingest_warnings.py` hardcoded `Path(__file__).parent.parent.parent` as repo root, which resolves correctly only in legacy form (`<repo>/.claude/scripts/X.py`); in plugin form (`<plugin>/scripts/X.py`) it skips a directory level and points at `plugins/`. Both scripts now use `_resolve_paths()` helper honoring `$CLAUDE_PLUGIN_ROOT` (framework-reference content) and `$CLAUDE_PROJECT_DIR` (project state) with auto-detect fallbacks. Tested in three configurations: legacy, plugin form via cwd-detect, plugin form via explicit env vars on a foreign test directory. PATCH per version-discipline.

## v0.20.4 — Plugin-form path + namespace rewrite across 45 SKILL.md

**2026-05-07 (commit `0d17210`).** 35 path rewrites (`.claude/engine/X` → `${CLAUDE_PLUGIN_ROOT}/engine/X`, same for schemas/scripts/domains/orchestration; `.claude/harness/X` excluding decision-log.md/warnings-log.md; `.claude/jit-tooling/X` excluding active-metrics.yml). 155 slash-command rewrites (`/skill-name` → `/mycelium:skill-name` across all 45 known skills). Project-state paths preserved unchanged. Resolves the headline gap from 2026-05-09 subagent re-simulation. PATCH per version-discipline.

## v0.20.3 — Framework reference tree migrated into `plugins/mycelium/`

**2026-05-07 (commit `20850da`).** Closes the architectural gap surfaced by subagent simulation 2026-05-09: `/mycelium:interview` referenced `.claude/engine/canvas-guidance.yml`, `.claude/engine/wayfinding.md`, `.claude/jit-tooling/metrics-detector.md`, `.claude/harness/security-trust.md`, etc. that the plugin did not yet ship. With this migration the plugin self-contains the full framework reference content; only project-state files (canvas/*.yml, diamonds/active.yml, memory/*, harness/decision-log.md, harness/warnings-log.md, evals/, jit-tooling/active-metrics.yml) live in user's project. Plus setup SKILL.md fixes from same simulation: explicit `.gitkeep` stubs for empty dirs, CLAUDE_PROJECT_DIR fallback documented, auto-mode default-yes policy. PATCH per version-discipline.

## v0.20.2 — Plugin-form install instructions

**2026-05-07 (commit `66fe291`).** AGENTS.md + README install instructions updated to document plugin-form install path alongside legacy `npx degit`. AGENTS.md "What's available" table updated with plugin/legacy file-location distinction. README Quick Start gains plugin-install section as recommended path. README Upgrading section gains `/plugin update` instruction. PATCH per version-discipline.

## v0.20.1 — Plugin-form migration progress

**2026-05-07 (commit `61a823b`).** 45 skills migrated to `plugins/mycelium/skills/` (commit `4656910`); 10 hooks migrated with `hooks.json` wiring all event matchers via `${CLAUDE_PLUGIN_ROOT}` paths (commit `69c00c5`); `/mycelium:setup` skill added for idempotent first-run project init (commit `eae91b6`); receipts case `2026-05-08-bentes-install-model.md` documenting Daniel Bentes's install-model finding + CONTRIBUTORS.md v0.20.0 entry crediting his second-cycle architectural review (commit `cc940e3`). Existing `.claude/` framework dir still preserved during migration. PATCH per version-discipline.

## v0.20.0 — Plugin-form bootstrap

**2026-05-06 (commit `a515448`).** Mycelium repackaged as a Claude Code plugin per Anthropic's plugin spec to solve the install-model architectural debt surfaced by Daniel Bentes 2026-05-08 (top-level framework metadata files contaminate user project root). New top-level structure: `.claude-plugin/marketplace.json` (single-plugin marketplace catalog) + `plugins/mycelium/.claude-plugin/plugin.json` (plugin manifest). Initial smoke-test skill `plugins/mycelium/skills/ping/SKILL.md` validates the plugin shape. Architecture cut documented in `plugins/mycelium/README.md`: skills/agents/hooks/harness/engine/schemas/scripts ship in plugin (versioned, replaceable, cached read-only); canvas/diamonds/memory/decision-log/evals/active-metrics live in user project (writable, gitted). Skill names become namespaced (`/interview` → `/mycelium:interview`). MAJOR-shaped change in user-facing install model (new mechanism: `/plugin marketplace add haabe/mycelium`); MINOR per version-discipline because plugin form is additive. Theory: Anthropic plugin convention; AGENTS.md open standard (Linux Foundation); Daniel Bentes BDSK architectural review; Synapti marketplace pattern study.

## v0.18.2 — Phase 3 audit + maintenance wiring

**2026-05-06.** `/corrections-audit` gains step 6c (scans `docs/receipts/cases/` YAML frontmatter for graduation signals — cluster cross-reference, mechanism-or-status pattern detection, contributor distribution audit, candidate-graduation cases, stalled-spec flags). `/canvas-health` gains step 9b (docs validation: audience markers, stub freshness >60d, length-budget hard/soft caps, last-updated >180d freshness, scent-rule scan for "click here" / "see [filename]", marketing-voice scan, receipts case frontmatter required-fields, README highlights >90d rotation candidacy). `/framework-health` gains step 4c (receipts highlights rotation cadence) + step 4d (docs cross-surface check). Internal-audience markers added to `cluster-instances.md` and `decision-log.md`. `docs/receipts/archive.md` placeholder created with archive rules. PATCH per version-discipline. Closes the multi-phase README + docs restructure (Phases 1, 2, 3 of 3 all shipped). Theory grounding: Argyris double-loop closure.

## v0.18.1 — Phase 2 content backfill

**2026-05-06.** 9 forthcoming-stub docs filled (glossary, faq, evaluate, theories, philosophy, usage-modes, jit-tooling, regulatory, changelog, contributing/README) + skills/{README,by-category}.md filled with 45-skill phase-and-category-ordered indexes. evaluate.md is the load-bearing landing for Drew Hoskins's post (~2026-05-25). usage-modes.md ships canvas-sync conflict-resolution rules answering a cohort participant's Q from the 2026-05-07 Juniors.dev presentation. theories.md mechanism-maps every Tier 1 + Tier 2 theory to the Mycelium artifact that implements it. philosophy.md frames opinionated discipline / theory-grounded / in-loop preventive / dogfood-required / build-to-learn-vs-earn / structure-before-content as load-bearing claims. faq.md answers six Juniors.dev questions concretely. PATCH per version-discipline. Validator authority migration from Phase 1 still load-bearing — Checks 6 + 13 now actively validate populated docs/skills/ and docs/theories.md.

## v0.18.0 — README + docs/ restructure (Phase 1 of 3)

**2026-05-08.** README compressed 525 → 152 lines. New `docs/` tree spokes off README hub. Metadocumentation + style guide + 5 receipts case files + indexes ship Phase 1; 10 forthcoming-stub pages fill in Phase 2; audit + maintenance wiring lands in Phase 3. CONTRIBUTORS.md restructured with explicit "How to get listed" recruitment-shaped section. AGENTS.md expanded with portable-vs-Claude-Code-specific surface table + concrete operating models per agent class. Validator updated for new authority locations (Checks 2/3/4 deprecated, 6 reads docs/skills/, 12 reads engine/theory-gates.md, 13 reads docs/theories.md with stub-aware skip). MINOR per version-discipline.

## v0.17.0 — Documented-rule-diverges-from-enforcement cluster spec-graduated

**2026-05-08.** Cluster reached 8 instances; graduated to a spec at `engine/consistency-check-spec.md` rather than to a half-baked detection mechanism. The spec catalogs all 8 instances by subclass, articulates 5 candidate detection rules with per-rule catches/misses/FP-risk, sets the spec→mechanism promotion bar (≥3 rules implemented, <5% FP, 100% TP on cluster fixtures). `cluster-instances.md` becomes canonical instance log. `/corrections-audit` step 6b + `/framework-health` step 4b wire the cluster log into routine audits. JTBD schema gains `validation_status_per_dimension` first-class field for the Christensen tripartite. MINOR per version-discipline. Backward compatible. Closes the recursive bug where the framework's stated graduation criteria could not be mechanically counted.

## v0.16.5

**2026-05-07.** `/diamond-progress` SKILL.md step 4 includes explicit prompt-template naming the re-invocation-as-approval shortcut. Footgun → visible affordance (Norman).

## v0.16.4

**2026-05-07.** `engine/wayfinding.md` tightened with "STRICT — reproduce the template literally" + explicit list of common improvisations to forbid.

## v0.16.3

**2026-05-06.** CLAUDE.md "Canvas writes — Read before Write" paragraph: canvas files ship pre-populated as templates, so Claude Code's `Write` tool always requires a prior `Read`; `cat` via Bash does not count.

## v0.16.2

**2026-05-06.** Provenance schema accepts singular `source_class` (single enum) and `notes` (free-text) alongside plural `source_classes`. Strict mode preserved (typos still caught). Same shape as Check 26's "documented rule diverges from enforcement" cluster, at schema layer.

## v0.16.1

**2026-05-06.** Check 26 refined to WARN on uncommitted post-bump material edits; `.claude/tests/` added to watched material paths; AGENTS.md surfaces upgrade.sh + version-bump caveat.

## v0.16.0 — Self-correcting harness layer

**2026-05-04.** G-V12 (every validator ships coverage proof) + G-P-pre (Mandatory Pre-Ship Protocol with visible gap analysis) graduate two recurring patterns to mechanism. Check 26 enforces version-bump discipline (5th-instance graduation of "documented rule diverges from enforcement"). Explainability: `/xai-check` skill + Gate 13 + `ai-system-card.md` template + Mycelium's own card + context-surface doc. Warnings ingestor turns CI signals into self-learning input alongside `corrections.md`. Detector Step 1c gains `agent_runtime_target` category for harness-shaped products. `parse_manifest` gains `--manifest=<path>` override. `decision-log` gains structured `why_not_alternatives` field (Liao contrastive). +27 unit tests; coverage 52% → 78%; ruff 35 → 0. Theory citations: Doshi-Velez & Kim, Liao et al., Mitchell et al., Lanham et al., Selbst & Barocas, Bansal et al., Lopopolo, EU AI Act Art. 13/50.

See [framework-self-correction case](receipts/cases/2026-05-01-framework-self-correction.md) for the cycle that produced this.

## Earlier

For pre-v0.16.0 history, see CLAUDE.md (the version line summarizes prior bumps) and the git log on `haabe/mycelium`.

## Update discipline

When a version bumps, this page gets a new entry. Manual extraction once on v0.18.0; manual update on each subsequent bump (no automation until pain warrants — per the framework's bias against premature automation).
