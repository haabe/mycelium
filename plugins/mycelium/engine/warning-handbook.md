# Warning Handbook

Best-practice fix per CI warning class. Consumed by `.claude/scripts/ingest_warnings.py` (which logs occurrences to `.claude/memory/warnings-log.md`) and surfaced by `/corrections-audit` when a class crosses the recurring-≥3 graduation threshold.

This file is **the system's documented memory of how to fix each warning class.** The ingestor classifies CI output against the signatures listed here; the agent (or user) consults this handbook when a fresh warning lands, rather than re-deriving the fix each time. New warning classes get added as `KNOWN_SIGNATURES` in `ingest_warnings.py` and as a section here in the same change.

## How to use

1. CI runs (validate-template.sh, upgrade.sh) emit `WARN:` / `FAIL:` lines.
2. `ingest_warnings.py` reads stdout, classifies each line against `KNOWN_SIGNATURES`, updates `warnings-log.md`.
3. When a known class crosses recurrence-≥3 across runs, `/corrections-audit` flags it as a graduation candidate.
4. Fix per the **Best practice** below; mark `Status: closed` in `warnings-log.md` when the fix lands.
5. If fix is structurally infeasible right now, mark `Status: accepted-as-baseline` with a date or trigger condition (per `feedback_no_tech_debt_deferral.md` — never indefinite).

When CI emits a line the ingestor classifies as `unclassified`, that is the signal to **add a new section here** + a new entry to `KNOWN_SIGNATURES`. Don't let unclassified accumulate — it's the equivalent of unread alerts.

## Warning classes

### hardcoded-top-level-literal

**Signature**: `upgrade.sh contains \d+ hardcoded top-level filename literal`
**Detection**: `validate-template.sh` Check 16 — drift detector for upgrade.sh
**Best practice**: Refactor to read via `parse_manifest.py`. Add a manifest field (e.g., `framework.version_source`) and consume it: `VAR=$(python3 .claude/scripts/parse_manifest.py <key>); use "$VAR"`. Pattern set 2026-05-04 with `version_source` field. The drift detector tiers: 0 = pass, 1-2 = WARN, 3+ = FAIL — so a single load-bearing literal is *tolerated* if it can't be manifest-driven, but the goal is 0.
**Graduation**: Already graduated to G-V12 + manifest-driven pattern. Recurrence after this point indicates a regression — investigate the script edit that re-introduced the literal.

### hardcoded-directory-literal

**Signature**: `upgrade.sh contains \d+ hardcoded framework-directory literal`
**Detection**: `validate-template.sh` Check 16
**Best practice**: Same as `hardcoded-top-level-literal` — read directories via `parse_manifest.py directories` and loop. The first incident (2026-04-28) introduced the manifest-driven loop pattern; this signature catches regressions only.
**Graduation**: G-V12 covers regression detection.

### user-content-skill-unclassified

**Signature**: `new skill\(s\) show strong user-content-handling signal`
**Detection**: `validate-template.sh` Check 15 Part B
**Best practice**: For each surfaced skill, decide:
1. Does the skill *interpolate user content into model prompts* — directly OR indirectly via persisting to canvas/state files that future agent context will read? If yes → add to `at_risk_skills` array in `validate-template.sh` AND ensure SKILL.md mentions the wrapping convention (`security-trust.md#prompt-injection-defense`).
2. If no (e.g., skill mentions "ask user" but doesn't persist user content): document the rationale inline as a comment near the skill's mention, and accept the heuristic false positive for now (the curated list is honest about what's actually at risk).
**Graduation**: not a graduation candidate — heuristic + curated list is the right shape (confirmed by the original 21-false-positives audit).

### wrapping-convention-missing

**Signature**: `Curated at-risk skill missing|does not acknowledge the wrapping convention`
**Detection**: `validate-template.sh` Check 15 Part A
**Best practice**: Add a one-line reference to `security-trust.md#prompt-injection-defense` in the skill's user-content-handling section. The skill must demonstrate it knows the content is untrusted, not just handle it implicitly.
**Graduation**: not yet — first incidents in 2026-05-04. Watch for recurrence on newly-added at-risk skills.

### canvas-in-update-mapping-missing

**Signature**: `Canvas file \S+ not in canvas-update mapping`
**Detection**: `validate-template.sh` Check 5
**Best practice**: Add a one-line entry to `../skills/canvas-update/SKILL.md`'s mapping table. Format: `| <description> | <filename>.yml | <theory source> |`. Without the mapping, the agent doesn't know which canvas file holds which kind of state, so updates to that canvas may be skipped or misrouted.
**Graduation**: low priority — fires only when a new canvas type ships without the mapping update. Consider folding into the canvas-template addition workflow if it recurs.

### ruff-total-above-baseline

**Signature**: `ruff: \d+ total errors across all`
**Detection**: `validate-template.sh` Check 17
**Best practice**: Per `feedback_no_tech_debt_deferral.md` — **fix in-session if mechanically tractable.** Run `ruff check --fix` then handle the remainder. The cleanup-cycle pattern is for *batched* cleanup, not indefinite deferral. If genuinely deferring (e.g., would block higher-priority delivery): mark in `warnings-log.md` with `Status: accepted-as-baseline` AND a date or trigger condition. Never mark as `accepted` without a follow-up plan.
**Graduation**: G-V12 partially covers (new validators ship coverage proofs, which usually means clean code). Full graduation to FAIL-tier is too aggressive — the cleanup-cycle pattern needs to remain a viable steady-state for legacy code.

### validation-failed

**Signature**: `VALIDATION FAILED`
**Detection**: `validate-template.sh` final summary
**Best practice**: This is a hard FAIL — the most recent specific check failure earlier in the output is the cause. Read the previous `FAIL:` line, fix that, re-run. Common causes: skill count mismatch (README/CLAUDE.md vs disk), canvas validation errors, schema regressions.
**Graduation**: already a hard FAIL — no further graduation needed.

### dirty-state-pre-upgrade

**Signature**: `Uncommitted changes detected\. Commit or stash first`
**Detection**: `upgrade.sh` startup check
**Best practice**: Commit or stash before running `upgrade.sh`. If the dirty state is intentional roadmap session work, commit it as part of the recoverability protocol (per CLAUDE.md instructions on roadmap commits).
**Graduation**: not a graduation candidate — this is a defensive pre-condition, not a quality signal.

### framework-dev-without-l4-dod

**Signature**: `framework changes shipped without L4 delivery discipline`
**Detection**: future hook (corrections.md 2026-05-03)
**Best practice**: Spawn an L4 delivery diamond when shipping ≥3 framework files. Run `/preflight` → implement → `/definition-of-done` → `/retrospective`. Convention layer is in CLAUDE.md; mechanical layer (PostToolUse hook) is the graduation candidate if the convention recurs as skipped.
**Graduation**: convention is current state. Watch for recurrence in cycle-history; graduate to mechanism on incident #2.

## When to add a new section

If `ingest_warnings.py` reports unclassified WARN/FAIL lines, that's the trigger to add a new section here. Process:

1. Read the unclassified lines from `warnings-log.md` (they accumulate under the `unclassified` class).
2. Identify the underlying validator/script producing them.
3. Add a stable `(class_name, signature_regex)` tuple to `KNOWN_SIGNATURES` in `ingest_warnings.py`.
4. Add a section here with: signature, detection, best practice, graduation note.
5. Re-run the ingestor; the previously-unclassified lines should re-classify under the new name.

This file grows as the framework's vocabulary of failure modes grows. It does not get consolidated by `/corrections-audit` — that skill operates on `corrections.md` and `warnings-log.md`, not on the handbook.
