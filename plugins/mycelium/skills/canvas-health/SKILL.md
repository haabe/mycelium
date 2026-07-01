---
name: canvas-health
description: "Lint canvas files for staleness, missing fields, inconsistent evidence types, and orphaned references. Run periodically or before major transitions."
metadata:
  instruction_budget: "87"
  framework_dependency: "mycelium"
  framework_dependency_note: "This skill is designed to run within the Mycelium framework (https://github.com/haabe/mycelium). Standalone use will skip the canvas state, theory gates, and harness behavior the skill assumes. Install: /plugin install mycelium@haabe/mycelium."
---

# Canvas Health Check

Audit the canvas knowledge base for quality, consistency, and completeness. The canvas is Mycelium's source of truth -- its quality directly determines agent output quality (Raschka: "context quality = model quality").

## When to Use

- Before any diamond phase transition (called automatically by `/mycelium:diamond-assess`)
- After a period of inactivity (>7 days since last canvas update)
- When agent output quality seems to degrade
- After onboarding a new team member (ensures canvas is self-explanatory)
- Proactively: run periodically to catch silent drift

## Workflow

1. **Load project configuration**:
   - Read `.claude/diamonds/active.yml` for `product_type` and `project_type`
   - Read `${CLAUDE_PLUGIN_ROOT}/engine/canvas-guidance.yml` for required/recommended/optional files per project type

2. **Check file presence**:
   - For each **required** canvas file: does it exist? Is it non-empty (>50 bytes)?
   - For each **recommended** canvas file: does it exist? Flag as gap if missing.
   - Report: `N/M required files present, K recommended files missing`

3. **Check `_meta` blocks**:
   - For each existing canvas file, check for `_meta:` block
   - Flag missing `_meta` blocks
   - Flag `last_validated` older than 30 days (staleness warning)
   - Flag `version` field missing or at 0

4. **Check confidence consistency**:
   - Gather all `confidence:` values across canvas files
   - Flag confidence > 0.5 with `evidence_type: speculation` or `evidence_type: assumption`
   - Flag confidence > 0.7 with fewer than 2 evidence sources
   - Flag confidence values that haven't changed across git history (anchored confidence anti-pattern)
   - Cross-check against `.claude/diamonds/active.yml` confidence

5. **Check evidence type consistency**:
   - Every canvas file with `evidence_type:` should have it set to one of: `interview`, `survey`, `analytics`, `experiment`, `speculation`, `assumption`, `mocked_persona`
   - Flag unknown evidence types
   - Flag `evidence_type: interview` when only mocked personas were used (honesty check)
   - Every `source_class:` value should be one of: `external_human`, `external_data`, `internal_stakeholder`, `internal_desk`, `internal_simulated` — flag unknown values
   - Flag `internal_stakeholder` evidence with confidence > 0.5 that has `validated: false` or no `validated` field — stakeholder beliefs should not carry high confidence without external validation (Brown: organizational mythology)
   - Flag L2 opportunity canvas entries where ALL evidence is `internal_stakeholder` or `internal_desk` — no external human voice heard (Spool: secondhand research insufficient)

6. **Check for orphaned references**:
   - Canvas files that reference other canvas files (e.g., jobs-to-be-done.yml referencing opportunities.yml) -- verify the referenced file exists
   - Diamond references to canvas files -- verify they exist

7. **Check evidence freshness** (evidence decay):
   - Scan all `provenance` blocks across canvas files for `validated_at` or `captured_at` timestamps
   - Compare against staleness thresholds from `${CLAUDE_PLUGIN_ROOT}/engine/evidence-decay.md`:
     - User needs/interviews: 90 days
     - Competitive intelligence: 90 days
     - Strategic assumptions: 180 days
     - Technical feasibility: 120 days
     - DORA/delivery metrics: 30 days
   - Flag evidence past threshold as warning; past 3x threshold as critical
   - Suggest refresh actions: "Evidence in [file] is [N] days old. Run `/mycelium:user-interview` or `/mycelium:log-evidence` to refresh."
   - Note: corrections and patterns do NOT decay — process learnings are timeless

7b. **Check metric snapshot freshness** (v0.14):
   - If `.claude/jit-tooling/active-metrics.yml` exists, for each `status: active` source:
     - Find the newest snapshot in `.claude/evals/metrics/<source>/`.
     - If >7 days old: warning ("[source] snapshot is [N] days old — run `/mycelium:metrics-pull` to refresh").
     - If >30 days old: critical (evidence this stale is worse than no metric reference — anchors old state).
     - If missing entirely: info-level ("No snapshots yet for [source]. Run `/mycelium:metrics-pull`.").
   - Also check per-adapter freshness: for each adapter file in `${CLAUDE_PLUGIN_ROOT}/jit-tooling/metrics-adapters/`, if `last_known_working` is >180 days old, flag as warning suggesting regeneration via `metrics-adapters/GENERATING.md`.
   - Source: v0.14 metrics harvesting. Metric evidence has a faster staleness curve than interview evidence because the underlying data changes continuously.

8. **Check cross-reference integrity** (leaf lifecycle):
   - Every GIST idea with `source_leaf_id` → verify (a) the leaf exists in `opportunities.yml` and is not in `archived-solutions.yml` without the GIST being shelved, AND (b) the leaf's #1 riskiest assumption carries a recorded test **verdict of `validated`** (v0.54.0 — Torres selection: a GIST idea may only trace to a leaf that PASSED its assumption test, not one that merely exists or scored high on ICE). Flag a GIST idea whose source leaf has an untested / `partial` / `invalidated` riskiest assumption as a broken graduation (G-L2 REVIEW blocks it).
   - Every service entry with `gist_id` → verify that GIST idea exists
   - Every threat model entry with `solution_id` → verify that solution exists
   - Every go-to-market `feedback_loop` entry with `source_leaf_id` → verify leaf exists
   - Flag broken references as warnings ("Zombie Solution" anti-pattern)

8b. **Check scenario health** (Hoskins):
   - If `.claude/canvas/scenarios.yml` exists:
     - Every scenario must have all three Hoskins elements populated (motivation, persona, simulation) — flag incomplete scenarios (corrected 2026-07-01: the model has THREE elements; the prior "persona/means/motive/simulation" was a distortion — "Means" is not a Hoskins element)
     - Every scenario must have `lifecycle.born_at` set — flag if missing (orphan scenario with no origin)
     - Every scenario with `confidence > 0.5` must have evidence sources — flag unsupported confidence
     - Every scenario referenced in `lifecycle.designed_against[]` → verify the solution exists in `opportunities.yml` or `gist.yml`
     - Every scenario referenced in `lifecycle.tested_against[]` → verify test date is not in the future
     - Flag scenarios with `status: draft` older than 30 days (stale draft — either promote or discard)
     - **Falsifiable-success check:** every scenario with `status` other than `draft` must have `simulation.success_criteria` with at least one entry carrying `observable` + `threshold` — flag a non-draft scenario whose success is only the qualitative `simulation.success_state` (an un-falsifiable scenario is a user story, not a Hoskins scenario; it cannot be run against the eval-runner)
     - **Grounding check:** a scenario listed in any `lifecycle.designed_against[]`, OR carrying `confidence > 0.3`, must have `provenance.source_class` of `external_human` or `external_data` — flag any `internal_simulated` / `evidence_type: speculation` scenario that is driving design or confidence (envision-only scenarios stay `status: draft` until a real source grounds them; a fabricated scenario feels like research because it is a story)
   - If `.claude/canvas/scenarios.yml` does NOT exist but project_type requires it (per ${CLAUDE_PLUGIN_ROOT}/engine/canvas-guidance.yml): flag as warning

8c. **Check build-mode** (Patton/Cagan — the `/define-done` build-mode gate's unconditional backstop):
   - For each diamond in `active.yml` at scale **L0–L3** (build-to-learn), lint its `definition_of_done.outcome` against an earn-verb lexicon (`deploy`, `ship`, `releas`, `production`, `go live`, `roll out`, `launch`, `all users`).
   - On a match → **WARN** (do not auto-fail — this is a keyword tripwire, not the semantic adjudication): *"Possible build-to-earn goal on a build-to-learn (L0–L3) diamond. Confirm this is a ship-to-LEARN outcome (disposable / opt-in, the learning is the done-bar) and not a premature earn-bar. If it's an earn-bar, re-run `/define-done` — production rollout is the L4 outcome."*
   - This converts the birth-only, agent-adjudicated gate into a check that fires regardless of whether the run engaged the gate prose. It routes the semantic call back to a human/agent; it never adjudicates "earn-shaped" itself (that stays with `/define-done`).

8c. **Human-task reconciliation** (added v0.31.3, closes the evidence/status/consent decoupling drift — corrections.md 2026-05-28):

The failure this catches: a fact about a human-task lives in 2+ places (the task `status`, the evidence file it produced, the contributor's consent registry) and only the salient one gets updated, so the canvas silently drifts from reality. Three sub-checks over `.claude/canvas/human-tasks.yml#pending_tasks`:

   - **(a) Status-vs-activity staleness**: for each task whose `status` is non-terminal (NOT `completed`/`abandoned`/`stalled`), compute the latest activity date across `updated_at`, `touch_log[].date`, and `partial_findings[].date`. If the latest is >21 days ago (or no activity date at all), flag: "ht-XXX untouched [N]d while still `[status]` — decide: mark `stalled`, mark `abandoned`, or nudge the contact. Abandonment is a non-event; nothing else will surface this." (The session-start hook flags this at 14d for awareness; canvas-health is the deeper 21d decision prompt.)
   - **(b) Evidence-exists-but-task-open**: for each non-terminal task, check whether it has already produced evidence — i.e. it has a populated `partial_findings` block, OR its `canvas_refs` resolve to real evidence entries in purpose.yml/user-needs.yml dated at/after the task's activity. If evidence exists but the task is still open, flag: "ht-XXX has captured evidence (partial_findings / linked purpose.yml entry) but status is `[status]` — close it (`completed`) or record why it stays open. Logging evidence and closing the source task are separate steps; this catches the gap." Recommend `/mycelium:log-evidence` should be closing the task going forward.
   - **(c) Consent-registry sync** (best-effort; cross-source): if an attribution registry is available (`$MYCELIUM_ATTRIBUTION_REGISTRY` or a private companion repo's `.claude/memory/attribution-registry.yml`), compare each contributor's `consent` value there against any consent state recorded in the agent's auto-memory (`~/.claude/projects/<id>/memory/`). Flag mismatches: "Consent for [name] is `[X]` in the registry but `[Y]` in auto-memory — the registry is canonical (Check 33 reads it); sync them." If neither source is accessible in the current context, skip this sub-check and note it was skipped. Do NOT print the literal value of any `generic_only`/project-name carve-out term into the report.

   - **(d) Untracked-channel evidence** (added v0.39.10, symmetric inverse of `(b)` — closes the drift where outreach produces evidence with no source-task at all): scan recent evidence entries across `.claude/canvas/*.yml` (windowed to entries dated within the last 30 days) for items with `source_class: external_human` whose `provenance.relationship` OR `provenance.evidence_sources[]` names an external contributor by name or handle. For each, check whether ANY `human-tasks.yml` entry (pending OR completed) lists that name in `target_persona`, `touch_log`, or a `backfill_note`. If no match, flag: "purpose.yml#L[NN] (or other canvas) records external_human evidence from [name] dated [date], but `human-tasks.yml` has no task covering this contributor. Backfill an `ht-XXX` with a `backfill_note` so the channel is addressable for follow-ups, learning-target coupling, and consent tracking. `/mycelium:log-evidence` v0.39.10+ catches this at log-time; older entries may need retroactive backfill." Skip names already flagged as registry-private (`generic_only`). NUDGE-tier, not gating.

   Output all (a)–(d) as warnings (not critical) — they are drift, not breakage. Each names the specific ht-ID (or missing-ht contributor) and the specific action.

8d. **Learning-target coupling on feedback tasks** (added v0.31.6, closes the "we asked for feedback but didn't ask what we needed to learn" gap — see `engine/canvas-guidance.yml#learning_target_coupling`):

The failure this catches: the canvas carries open learning needs (ON HOLD / RE-GATED action flags, in-progress human-tasks naming a MISSING SIGNAL, low-confidence entries with an un-validated assumption), AND a feedback-gathering task is open, but the task's questions target none of those gaps — so the feedback returns whatever the respondent volunteers rather than the answers the canvas is waiting on. Feedback capacity is scarce and non-repeating; an un-targeted session spends it without retiring any gap.

   - First, build the open-gap set: scan all canvas `.yml` files for (i) `ON HOLD` / `RE-GATED` markers, (ii) `human-tasks.yml` tasks with `status: in_progress` whose `success_criteria` name a MISSING SIGNAL or un-met track, (iii) entries with `confidence < 0.5` carrying a named un-validated assumption. If the open-gap set is empty, skip this check (nothing to couple to).
   - Then, for each feedback-gathering task that is open (`human-tasks.yml` tasks with a `key_questions` block, status non-terminal): check whether any question carries a `[<gap-handle> → <file>#<anchor>]` tag (the coupling tag) OR plainly references one of the open gaps by name. **Tag format**: the `<gap-handle>` is a short descriptive name for the open gap (e.g., `[L0 adoption / cautious-learner → purpose.yml L797 + ht-002 track(c)]`, `[anti-state #1 vocabulary wall → purpose.yml#anti_states lost-in-vocabulary]`); the literal placeholder `target` is also accepted (`[target → <file>#<anchor>]`) but the descriptive form is the validated-in-use convention and is more informative at read-time. Both forms match the same `\[[^\]]+→[^\]]+\]` regex shape. If NONE do, flag (NUDGE): "ht-XXX gathers feedback but none of its key_questions target an open canvas gap ([list 2-3 open gaps]). Seed ≥1 learning-target question per `learning_target_coupling`, or record why this is pure discovery."
   - Also flag any `[<gap-handle> → ref]` tag whose `<file>#<anchor>` does not resolve to a real canvas entry (broken coupling — the gap it claimed to feed was renamed or closed): "ht-XXX question tags [ref] but that entry no longer exists — re-point or drop the tag."
   - **Scope-narrow** (added 2026-06-05): 8d applies to feedback-EXTRACTION tasks (interview, deep-session, observation). It does NOT apply to: warm-referral asks (the question is a relationship move, not feedback-extraction), single-question broadcast recruits (the questions are the post text, not extraction prompts), or close-the-loop receipt asks where the "question" is acknowledgment, not learning. The check should skip these task shapes when their `objective:` field clearly signals non-extraction intent; if in doubt, flag with the carve-out language ("ht-XXX appears to be a [shape] task rather than feedback-extraction — apply 8d only if extraction was the intent").
   - NUDGE-tier, not a gate. Zero-target feedback sessions are legitimate (pure discovery); the check makes the omission a visible choice rather than an oversight. Each flag names the specific ht-ID and the specific open gaps it could target.

8e. **Diamond Definition-of-Done presence** (added with `/mycelium:define-done` — retrofit detector):

The failure this catches: a diamond reaches Deliver (or sits in any phase) with no explicit outcome bar, so "done" defaults implicitly to the harshest, least-controllable outcome — wrong for validating purpose and a demotivation engine (see `docs/design/definition-of-done.md`).

   - Read `.claude/diamonds/active.yml`. For each diamond in `active_diamonds` whose state is not terminal (NOT `archived`/`killed`), check for a `definition_of_done` block with non-empty `outcome` and `signal`.
   - If missing or stub-empty: flag (NUDGE) — "Diamond [id] ([scale], [phase]) has no outcome Definition of Done. Run `/mycelium:define-done` to pin what behaviour-change marks it done. The Deliver→Complete gate will block without it." Do NOT auto-fill — the question is what produces a real bar, not the field.
   - For child diamonds (non-null `parent`) that DO have a DoD: flag if `rolls_up_to` is absent — "Diamond [id] is a child but its DoD names no parent outcome it rolls up to (contribution-not-summation)."
   - NUDGE-tier; names the specific diamond id and the specific action.

9. **Check for boilerplate content**:
   - Flag canvas files where >50% of content matches the template defaults from ${CLAUDE_PLUGIN_ROOT}/engine/canvas-guidance.yml
   - Flag files with placeholder text ("TBD", "TODO", "fill in later", "placeholder")

9b. **Check `docs/` health** (added 2026-05-08 with the docs restructure):
   - **Audience markers**: every public doc under `docs/` (excluding `docs/receipts/cases/` which carry frontmatter) must have **Audience**, **Time to read**, and **Last updated** lines in the first 5 lines. Flag missing markers.
   - **Stub freshness**: docs containing `is forthcoming` are Phase 2 stubs. Flag any stub with `Last updated` older than 60 days — Phase 2 may have stalled.
   - **Length budget compliance**: per `docs/README.md` and `docs/contributing/style.md`:
     - README ≤ 250 lines (hard cap; soft cap 200)
     - `docs/<page>.md` ≤ 400 lines (hard cap; soft cap 250)
     - `docs/receipts/cases/<case>.md` ≤ 250 lines (hard cap; soft cap 150)
     - Flag any file over hard cap (FAIL); warn over soft cap (NUDGE).
     - **Exempt by convention** (added v0.39.16, per /mycelium:framework-health 2026-06-05 finding 4d): append-only log files where the line count IS the value. `docs/changelog.md` (the full version history is the artifact's purpose; pages-as-shape is a category error) and any file whose first 5 lines declare itself a log surface (e.g., `**Format**: append-only log`, or a similar self-declaration). The exemption is intentional and bounded — narrative docs that drift into log-shape are still flagged.
   - **Last updated freshness**: any `docs/` file with `Last updated` older than 180 days gets flagged for refresh.
   - **Stable-cohort signal** (added v0.39.16, per /mycelium:framework-health 2026-06-05 finding 4d): when ≥3 docs share the same `Last updated` date AND that date is approaching the 180d threshold (within 30 days of expiry, i.e., older than 150 days), surface as a *cohort-validation event overdue* rather than flagging each file individually. The pattern (multiple docs frozen at the same date) signals "one batch validated at that time, no individual re-touches since" — the right remediation is a single batch re-validation pass that touches each, not 13 separate touch-passes. Cohort signal is INFORMATIONAL (not FAIL/WARN); intent is to make the batch nature visible so the response matches the cause.
   - **Information scent on links**: scan for "click here", "see [filename](path)" patterns — these violate the scent rule. Flag for review.
   - **Marketing-voice scan**: scan for "powerful", "comprehensive", "robust", "seamless", "best-in-class". Flag occurrences for voice review per `docs/contributing/style.md`.
   - **Receipts case frontmatter**: every file under `docs/receipts/cases/` must have YAML frontmatter with the required fields (id, date, contributor, contributor_link, project, mechanism_or_status, commits, subclass). Flag missing fields.
   - **Highlights rotation cadence**: if README's "How Mycelium got smarter" section has not changed in >90 days (check git log for last commit touching that section), flag as a rotation candidate per `docs/contributing/style.md#highlights-rotation`. The flag is informational; rotation is a `/mycelium:framework-health` decision, not an automatic move.
   - **System-card content freshness vs services.yml** (added v0.39.14 — closes the substantive content gap that Check 40's mechanical-token sync doesn't cover): for any project whose `.claude/canvas/services.yml` has a service with an `xai:` block (i.e., AI-component product per `/mycelium:xai-check`), compare key fields in `docs/ai-system-card.md` (or equivalent system card path) against the canvas. Fields to compare: §9 "Last full audit" date vs `xai.last_assessed_at`; §5/§9 eval status references vs `xai.fidelity` block (especially when an eval has closed — `samples_audited` and verdict change but card prose lingers); §1 AI Act risk tier text vs `xai.tier` + `xai.tier_provisional`. NUDGE-tier flag (informational, not failing) on any mismatch >7 days old, with canvas treated as canonical and remediation pointing to a system-card edit OR an extension to `sync_derived.py` if the field is mechanically derivable. Worked failure 2026-06-05: `docs/ai-system-card.md` §5/§9 still cited `2026-05-04-xai-inline-attribution (1/10 sessions)` 24 days after the eval closed 2026-05-12 at session 11 INSTRUMENT FAILED; the 2026-06-04 canvas-health spot-check missed it because no rule existed to compare card content to services.yml. This sub-check closes the gap.

9c. **Check action-flag timeout handling** (added 2026-05-23 v0.23.43, closes a documented-rule-diverges-from-enforcement instance):

Per `${CLAUDE_PLUGIN_ROOT}/engine/canvas-guidance.yml#action_flags.transitions.timeout_handling`: "ON HOLD entries with calendar conditions (e.g., 'pending May 7 evidence') that pass their named date should be flagged, not silently expired. Surface as a stale flagged item via /canvas-health (existing staleness machinery applies). Do NOT auto-transition to OPEN — the absence of the awaited evidence is itself a finding worth surfacing to the user. After 30 days past a named date with no resolution, suggest re-evaluating whether the condition is still relevant."

The convention says canvas-health surfaces this. Until v0.23.43 it didn't — the convention was written 2026-05-03 but no canvas-health check was added. This check closes that gap (cluster instance #11 of documented-rule-diverges-from-enforcement, 2026-05-23).

Concretely:
- Scan all canvas `.yml` files for ON HOLD markers via the keyword pattern: `(ON HOLD|on hold)` with a parenthetical containing a calendar date in any of: `YYYY-MM-DD`, `Month DD`, `MM/DD/YYYY`, or month-name forms (e.g., "May 7", "May 2026").
- For each match, parse the date. Resolve relative months to the most plausible recent occurrence (e.g., "May 7" → most recent 2026-05-07).
- Compare to today's date:
  - Future date → no flag (item correctly waiting).
  - Past date, <30 days → **warning**: surface the item as a flagged-pending-with-passed-date, recommend the user check whether the awaited evidence has arrived (and if so, transition per `transitions.on_hold_condition_met` audit rules). Format: "Canvas [file]: item flagged ON HOLD pending [name] [date]; date passed [N] days ago. Evidence: check if [name] arrived; if yes, transition ON HOLD → OPEN per canvas-guidance#transitions; if no, leave."
  - Past date, ≥30 days → **escalation**: same format plus "≥30 days past named date — re-evaluate whether the condition is still relevant or whether the underlying assumption has changed (per canvas-guidance#transitions.timeout_handling.escalation)."
- Do NOT auto-transition any marker. The check surfaces; the maintainer decides.
- The check is INCOMPLETE without inspection of awaited-evidence sources. Treat the output as a prompt for human judgment, not a verdict.

10. **Log findings to .claude/harness/decision-log.md** (MANDATORY):
   - APPEND a `### Canvas Health Report` entry to `.claude/harness/decision-log.md`
   - Include: overall status (HEALTHY/WARNINGS/CRITICAL), stale evidence found, refresh recommendations
   - Use these words explicitly when applicable: "stale", "evidence", "refresh", "interview", "validate"
   - Example: "Evidence in opportunities.yml is stale (183 days old, threshold 90). Refresh needed: run fresh interviews to validate opportunity assumptions."
   - This log entry is essential for auditability and for downstream skills (e.g., `/mycelium:diamond-progress`) to detect health issues

11. **Generate health report**:
   - Summarize findings by severity: critical (required file missing), warning (stale, inconsistent), info (recommended file missing, meta block absent)

## Output Format

```
## Canvas Health Report

> **Status: [HEALTHY | WARNINGS | CRITICAL]** — [one-line verdict, e.g., "0 critical, 3 warnings, 1 info — system-card content stale vs services.yml; chat-UX axiom flags first-fire"]

Files checked: N canvas files, M diamonds files

### Critical Issues
- [required file missing or empty]

### Warnings
- [stale confidence, inconsistent evidence, anchored values]

### Suggestions
- [missing recommended files, absent _meta blocks]

### Coverage Summary
| Category | Required | Present | Gap |
|----------|----------|---------|-----|
| Discovery (L0-L2) | N | M | ... |
| Solution (L3) | N | M | ... |
| Delivery (L4) | N | M | ... |
| Market (L5) | N | M | ... |

Recommended actions:
  - /mycelium:canvas-update [file] -- [reason]
  - /mycelium:interview -- [if evidence gaps found]
  - /mycelium:log-evidence -- [if confidence unsupported]
```

## Theory Citations
- Karpathy: Knowledge base health checks and auto-maintained indexes
- aiops3000: Anti-drift through externalized knowledge, versioned reference artifacts
- Raschka: "Context quality = model quality" -- canvas quality determines agent output quality
- Gilad: Confidence must be evidence-backed (confidence consistency checks)
- Torres: Evidence triangulation (evidence type consistency)

## Postflight: Verify-After-Write (claim matches state)

**Hard rule** (per CLAUDE.md Communication Rules, anti-pattern #7 *write-narration-verification* — mechanism Check 42, graduated v0.39.18; enforced surface expanded to this skill v0.44.0). This skill mandates multi-field canvas updates. Before narrating "updated / wrote / refreshed [canvas]" in any user-facing summary, RE-READ the value fields this skill's MANDATORY says to update and confirm they actually changed — not just `_meta.last_validated` or a freshness stamp. Each field you claim to have updated must reflect its new value. The symmetric half of the Read-before-Write Preflight: that one protects what gets read before a write; this one protects that the write matches the claim. Worked failures: 2026-06-05 #18 (`/dora-check` narrated "updated" with value fields unchanged) + #19 (`/retrospective` left a cycle-history aggregate un-propagated).
