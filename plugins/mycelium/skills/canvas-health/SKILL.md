---
name: canvas-health
description: "Lint canvas files for staleness, missing fields, inconsistent evidence types, and orphaned references. Run periodically or before major transitions."
metadata:
  instruction_budget: "87"
  framework_dependency: "mycelium"
  framework_dependency_note: "This skill is designed to run within the Mycelium framework (https://github.com/haabe/mycelium). Standalone use will skip the canvas state, theory gates, and harness behavior the skill assumes. Install: /plugin install mycelium@haabe-mycelium."
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
   - Flag `last_validated` past **the horizon for that file's category**, per the
     "Which threshold applies to which canvas file" table in
     `${CLAUDE_PLUGIN_ROOT}/engine/evidence-decay.md` (strategic 180d, technical
     feasibility 120d, user-needs/competitive/market 90d, delivery metrics 30d,
     regulatory 365d; unlisted files fall back to 90d).
   - **SKIP any file whose `_meta.applicability` marks it inapplicable** (a value
     starting `n/a`, or naming a product type this project is not, or saying "NOT
     actively used"). Added v0.90.0. Two dogfood canvases held ZERO evidence — every
     metric field null, the only non-null leaves `False` schema defaults — and already
     said so in their own `_meta`. They decayed on a 30-day horizon anyway, and the only
     way to silence that warning would have been to date a validation of a file nobody
     uses: the manufactured-validation move v0.89.0 removed `last_updated` to prevent.
     Precedents for the marker: `dora-metrics.yml#sre` (`n/a-until-production`) and
     `dependency-pins.yml` (`scope: local`).
     **This replaced a flat 30-day rule in v0.89.0.** That rule was the only
     staleness number in this skill grounded in nothing — step 7 below has always
     used the decay table — and on the dogfood repo it flagged 20 of 25 canvases,
     including a strategic file validated 46 days earlier against a 180-day
     horizon. A check that fires on 80% of a corpus trains its reader to skip it.
   - Flag `version` field missing or at 0

4. **Check confidence consistency**:
   - Gather all `confidence:` values across canvas files
   - Flag confidence > 0.5 with `evidence_type: speculation` or `evidence_type: assumption`
   - Flag confidence > 0.7 with fewer than 2 evidence sources
   - Flag confidence values that haven't changed across git history (anchored confidence anti-pattern)
   - Cross-check against `.claude/diamonds/active.yml` confidence
   - **Cross-check the confidence RATIONALE prose too, not only the `confidence:` field.** Projects record *why* a value moved in narrative fields (`confidence_effect`, `confidence_effect_v2`, or any prose block that names a number). Nothing reads those, so a canvas can be numerically consistent everywhere while the sentence explaining the number contradicts it. Flag when a rationale block names a confidence value that no longer matches `.claude/diamonds/active.yml`. **Prose that encodes state is state, and it is otherwise unvalidated.** (Roadmap dogfood 2026-08-02: the field said 0.10, the narrative beside it still said 0.25, and the numeric check passed.)

5. **Check evidence type consistency**:
   - Every canvas file with `evidence_type:` should have it set to one of the shipped schema enum values (`schemas/canvas/_common.schema.json#$defs/evidence_type` — Gilad's evidence ladder): `speculation`, `anecdotal`, `data-supported`, `test-validated`, `launch-validated`
   - Flag unknown evidence types (note: `_meta` blocks in the field carry structural markers like `schema` / `assessment` / `not-yet-populated` — flag these only when they appear OUTSIDE `_meta`; inside `_meta` they describe the file, not an evidence claim)
   - Flag evidence graded `anecdotal` or better whose only sources are mocked personas / `internal_simulated` (honesty check — simulated evidence sits at `speculation` on the ladder regardless of how vivid it reads)
   - Every `source_class:` value must be one of the values in the SHIPPED SCHEMA
     enum — read `${CLAUDE_PLUGIN_ROOT}/schemas/canvas/_common.schema.json#$defs/source_class`
     and compare against that, exactly as the `evidence_type` rule above already does.
     **Do NOT hardcode the list here.** Until v0.90.0 this step named five values while
     the schema had six; `pointer` is valid, `check_source_independence.py` handles it
     correctly, and a dogfood canvas used it 61 times. Following the prose produced 61
     phantom violations — the documented-rule-diverges-from-enforcement class, in a step
     whose own sibling rule says to read the schema.
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

7c. **Run the do-not-cite register scan** — do NOT re-derive this from prose:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_citations.py" --project-dir .
```

   Reports any canvas line repeating a claim the project has already ruled against, printing the
   register entry VERBATIM. It reads `.claude/harness/do-not-cite.yml`; with no register it says
   NOTHING WAS CHECKED rather than passing.

   **Why it is a script and not a rule in this file.** A do-not-cite register existed in one
   project's agent memory and failed twice in a single day (2026-09-01): once by not being read
   before a citation was written into two canvas files, and once by having a narrow entry
   PARAPHRASED into a broad one that was then acted on, rewriting four surfaces that were already
   correct. The rule was right both times and was not consulted at the moment of use.

   **It is not a lexical guard.** It matches a curated list a human wrote, so it cannot fire on a
   claim nobody has ruled on. That distinction matters here: the sibling `absence-claim-guard` hook
   matches a prose signature and was consumer-measured at 29 lifetime fires, 16 in one day, and
   zero of that day's four confirmed errors caught. On first run against a real 25-file canvas this
   check found 3 true positives — including two in a file that an earlier manual correction pass on
   the same claims had missed entirely.

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
   - **Ignore a match that sits inside a NEGATION** (`not`, `NOT`, `never`, `rather than`,
     `instead of` within ~40 characters before it). Added v0.90.0: this fired on two dogfood
     diamonds whose outcomes read "**NOT** shipped-a-product-through-it" and ("Bet validated",
     **not** "shipped"). Both explicitly disclaim being earn-bars, and saying so is what tripped
     the check built to catch earn-bars. Left unfixed it fires on every well-written
     build-to-learn DoD, because disclaiming the earn-bar is the natural way to write one.
   - On a match → **WARN** (do not auto-fail — this is a keyword tripwire, not the semantic adjudication): *"Possible build-to-earn goal on a build-to-learn (L0–L3) diamond. Confirm this is a ship-to-LEARN outcome (disposable / opt-in, the learning is the done-bar) and not a premature earn-bar. If it's an earn-bar, re-run `/define-done` — production rollout is the L4 outcome."*
   - This converts the birth-only, agent-adjudicated gate into a check that fires regardless of whether the run engaged the gate prose. It routes the semantic call back to a human/agent; it never adjudicates "earn-shaped" itself (that stays with `/define-done`).

8c. **Human-task reconciliation** (added v0.31.3, closes the evidence/status/consent decoupling drift — corrections.md 2026-05-28):

The failure this catches: a fact about a human-task lives in 2+ places (the task `status`, the evidence file it produced, the contributor's consent registry) and only the salient one gets updated, so the canvas silently drifts from reality. Three sub-checks over `.claude/canvas/human-tasks.yml#pending_tasks`:

   - **(a) Status-vs-activity staleness**: **SKIP `status: watching` ENTIRELY** (v0.132.0) — a watch owes nothing, so "untouched 90d" is its CORRECT state and flagging it is a false positive that teaches the reader to ignore this check. Before the value existed, projects hand-exempted their watches from staleness rules in prose, which is the evidence the state is real. For each remaining task whose `status` is non-terminal (NOT `completed`/`abandoned`/`stalled`), compute the latest activity date across `updated_at`, `reopened_at`, `touch_log[].date`, and `partial_findings[].date`. (`reopened_at` MUST count as activity — a task deliberately reopened today is fresh, not stale, even when its other dates are months old; the reopen convention writes `reopened_at`, so omitting it here mis-flags every reopened task. Dogfood 2026-07-05: ht-003, reopened that day, read as 70d stale because this list omitted `reopened_at`.) If the latest is >21 days ago (or no activity date at all), flag: "ht-XXX untouched [N]d while still `[status]` — decide: mark `stalled`, mark `abandoned`, or nudge the contact. Abandonment is a non-event; nothing else will surface this." (The session-start hook flags this at 14d for awareness; canvas-health is the deeper 21d decision prompt.)
   - **(b) Evidence-exists-but-task-open**: **FIRST, IF `status` IS `waiting` OR `watching`, THAT IS THE RECORDED REASON THE TASK STAYS OPEN — do not flag** (v0.132.0). This sub-check used to infer "legitimately waiting" from a future `horizon` date, which is a proxy for a state the author can now simply declare; an explicit status beats a date a reader has to interpret. The horizon fallback below still applies to `pending`/`in_progress` tasks. Then, for each non-terminal task, check whether it has already produced evidence — i.e. it has a populated `partial_findings` block, OR its `canvas_refs` resolve to real evidence entries in purpose.yml/user-needs.yml dated at/after the task's activity. **FIRST, CHECK `horizon` / `scoring_horizon`. If it is in the FUTURE, do not flag** —
     a dated horizon IS the recorded reason the task stays open, which is precisely what this
     sub-check asks the author to supply. Added v0.90.0: the 2026-08-05 dogfood run flagged
     seven tasks and five had future horizons, so the check demanded a reason that was already
     written in the field beside it. Only the two horizonless tasks were real findings, and the
     right remedy for those is a horizon (see the ht-027 precedent), not closure.
     If evidence exists, the task is still open, AND no future horizon is set, flag: "ht-XXX has captured evidence (partial_findings / linked purpose.yml entry) but status is `[status]` — close it (`completed`) or record why it stays open. Logging evidence and closing the source task are separate steps; this catches the gap." Recommend `/mycelium:log-evidence` should be closing the task going forward.
   - **(c) Consent-registry sync** (best-effort; cross-source): if an attribution registry is available (`$MYCELIUM_ATTRIBUTION_REGISTRY` or a private companion repo's `.claude/memory/attribution-registry.yml`), compare each contributor's `consent` value there against any consent state recorded in the agent's auto-memory (`~/.claude/projects/<id>/memory/`). Flag mismatches: "Consent for [name] is `[X]` in the registry but `[Y]` in auto-memory — the registry is canonical (Check 33 reads it); sync them." If neither source is accessible in the current context, skip this sub-check and note it was skipped. Do NOT print the literal value of any `generic_only`/project-name carve-out term into the report.

   - **(d) Untracked-channel evidence** (added v0.39.10, symmetric inverse of `(b)` — closes the drift where outreach produces evidence with no source-task at all): scan recent evidence entries across `.claude/canvas/*.yml` (windowed to entries dated within the last 30 days) for items with `source_class: external_human` whose `provenance.relationship` OR `provenance.evidence_sources[]` names an external contributor by name or handle. For each, check whether ANY `human-tasks.yml` entry (pending OR completed) lists that name in `target_persona`, `touch_log`, or a `backfill_note`. If no match, flag: "purpose.yml#L[NN] (or other canvas) records external_human evidence from [name] dated [date], but `human-tasks.yml` has no task covering this contributor. Backfill an `ht-XXX` with a `backfill_note` so the channel is addressable for follow-ups, learning-target coupling, and consent tracking. `/mycelium:log-evidence` v0.39.10+ catches this at log-time; older entries may need retroactive backfill." Skip names already flagged as registry-private (`generic_only`). NUDGE-tier, not gating.


   - **(e) Reply owed** — **DO NOT re-derive this from prose. Run the script:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_reply_owed.py" --project-dir .
```

     This step used to describe the algorithm here, in parallel with an
     implementation inside `hooks/session-start.sh`. **One rule, two implementations,
     and only one of them could be executed.** The same-day tie-break was diagnosed
     2026-08-05, written into THIS PROSE at v0.90.0, and left live in the hook — which
     flagged the same two tasks (ht-060, ht-003) again on 2026-08-07, two days later.
     A rule repaired in the copy that cannot run is not repaired.

     So the logic now lives in `scripts/check_reply_owed.py` and both surfaces call it.
     What it does, for reading rather than for reimplementing: it walks `touch_log[]`,
     considers only CONTACT directions (`internal` notes are not contact and must not
     mask an inbound), takes the newest by date with **ties broken by log position**
     — dates are day-granular and carry no ordering within a day — and flags a task
     whose newest contact is `inbound` and ≥3 days old. An explicit `reply_owed:`
     field forces the flag. The tiebreak is position rather than direction because
     preferring outbound on a tie would silence the honest case where they wrote BACK
     the same day.

     **Why this is not covered by `(a)`.** `(a)` treats any `touch_log` entry as
     activity, so an inbound REFRESHES the staleness clock — a task where the contact
     is waiting on you scores as HEALTHIER than one where you sent something and heard
     nothing. Opposite states, indistinguishable. Dogfood 2026-08-01: three unanswered
     inbounds aged 4–7 days sat invisible behind a green staleness pass.

     **Migration nudge**: entries lacking `direction` are invisible to this check and
     to `session-start`. Pre-v0.68.0 logs predate the contract, so suggest backfilling
     and never fail on it. NUDGE-tier.

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
- **Only count a date the gate WAITS FOR, not the date it was AUTHORED ON.** Added v0.90.0.
  Require the date to sit in a waiting construction — `pending <date>`, `by <date>`,
  `until <date>`, `after <date>`, `expires <date>` — within the ON HOLD clause. A bare date
  anywhere in the surrounding prose is usually provenance (when the hold was written, re-gated,
  or last re-checked), not a deadline. On the 2026-08-05 dogfood run this produced 0 genuine
  findings from 4 flags: every hold was CONDITION-gated (waiting on a signal, e.g. "≥1
  theory-fluent tester signal"), and the dates matched were the dates the gates were re-gated.
  One of them even carried its own maintenance record — "GATE RE-CHECKED 2026-07-03 ... Hold
  unchanged" — i.e. a gate being tended, reported as rotting.
- **A condition-gated hold with no awaited date is not overdue and must not be flagged by this
  check.** Its staleness question is "has the signal arrived?", which no regex can answer.
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

## Canvas-recorded framework version vs installed (added v0.90.0)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_canvas_version_drift.py" --root . --framework-root "${CLAUDE_PLUGIN_ROOT}"
```

A dogfood canvas was found asserting `ai-tool-metrics.yml :: model_metrics.version:
"Mycelium 0.16.1"` while the running plugin was **0.89.0 — 73 releases behind**. It sat
wrong for three months because nothing compared a version a canvas CLAIMS against the one
actually loaded: `_meta.version` is an integer schema revision, and `sync_derived.py` syncs
docs rather than canvases.

It reads only values under keys literally named `version` that also name the framework —
never free prose, because canvases legitimately cite historical versions ("shipped in
v0.70.0") and flagging those would make it noise on day one. UNKNOWN (exit 2) when no
plugin.json is readable, never a clean pass it did not earn.

## Decision-log reconcile — a dated event whose canvas row was never written

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_log_reconcile.py" --root .
```

Registered classes of dated decision-log event are reconciled against the canvas history that
should have gained a row. **Log-without-canvas is the ORPHAN and fails; canvas-without-log is the
harmless direction and is INFO** — the canvas is the source of truth, and failing that direction
trains people to stop writing it.

**It guards two recorded failures**: a BVSSH assessment orphaned to the log, and DORA 2026-08-09
where the measurement was taken, the history row was never written, and one file ended up carrying
three different dates for one measurement.

**IT SHIPS GREEN AND SAYS SO EVERY RUN.** It found nothing on the corpus that motivated it. It is a
regression guard, not a discovery tool, and if it stays green over a long window it should be
narrowed or retired rather than left running — the near-zero-action-rate rule applies to it too.

## Upstream candidate registry — is surfaced friction already fixed?

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_upstream_candidates.py"
```

For projects that surface framework friction back upstream. Re-runs every `verify` probe in
`.claude/harness/upstream-candidates.yml` against the live framework tree and reports the two
disagreements that matter: **LANDED** (marked open, but the change is in the tree — close it) and
**REGRESSED** (marked shipped, but the probe can no longer find it).

**The value is knowing what is already built, not remembering what to build.** A dogfood pass on
2026-08-17 found six of ten surfaced items already shipped; the log is append-only, so shipped work
reads as open forever unless something walks back and checks.

## Findings that name people, and no task that reaches them

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_named_people_unactioned.py" --root .
```

Every other check here audits **artefacts** — staleness, orphaned references, pre-registration,
unread surfaces. **None of them asks whether a finding names somebody who could simply be asked.**

The case it exists for: a dogfood hand-verification named six public repos under *"REAL EXTERNAL
CONTACT EVIDENCED"* and sat **eleven days** with zero mentions in `human-tasks.yml`, green in every
gate the whole time. "Ask them" never emerged as a path, because nothing was looking for that shape.

**Report-only, and not as a placeholder for a gate.** The extractor also matches namespaced paths
that look like `owner/repo` (`search/code` was the live false positive), so failing on it would be
worse than the disease. **The file-level ratio is the signal — read the file before acting.** It is
also NOT a claim that every named identifier deserves a task: the same source file named 28
hand-classified contaminants alongside the six genuine cases.

## Contacts recorded as prose, never as a touch

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contact_recorded_as_prose.py" --root .
```

The check below verifies that the entries which EXIST are ordered. **This one asks whether the log
is COMPLETE**, which is a different question and was not being asked by anything.

A dogfood task carried the line *"lost nine touches to prose-only logging"* and then lost a tenth
the same way — **inside the entry that documents the rule.** An inbound was written up as a field
named `eighth_inbound_2026_08_26_...` and never entered `touch_log`. `check_reply_owed` then read
the last inbound as five days old when it was one, because it reads the log and the log did not know.

**A field NAME carrying both a date and a contact word is a claim that a contact happened on that
date.** If no touch shares the date, the claim lives in prose only — invisible to reply-owed, to
the attribution registry, and to the exclusion duty later sweeps owe an already-touched population.

**REPORT-ONLY, and do not clear a finding by inventing a date.** Some contacts genuinely have no
known event date; an entry dated by when it was REPORTED asserts an event date nobody has. Either
log the touch with its real date, or state in the task that the date is unknown.

## touch_log order — is the last entry actually the most recent?

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_touch_log_order.py" --root .
```

Every reader of a `touch_log` — human, script or agent — treats `touch_log[-1]` as "what happened
last". An out-of-order log looks wrong to nobody and parses cleanly; it just silently returns the
wrong answer to the question the file exists to answer: **what happened last, and does anyone owe
anyone a reply?** Surfaced 2026-08-18 in dogfood, where it reported two already-sent replies as
unsent.

**A scan that finds zero files exits 1, not 0.** An empty scan is UNKNOWN, and UNKNOWN is never a
pass — added after a CI run reported "ascending across 0 file(s)" and went green because the scan
root had not resolved.

## Instrument contract — frozen predictions with no home, no expiry, or silent edits

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_instrument_contract.py" --root .
```

`/mycelium:assumption-test` Step 5b writes a four-field contract header onto every instrument in
`.claude/evals/assumption-tests/`. This reports the five ways that goes wrong: **uncontracted** (a
file that reads like an instrument and carries no header), **no expiry** (a prediction that can
never be overdue, so it can never be scored), **due/overdue**, **not in git** (nothing timestamps
it), and **drifted** — the prediction block changed after the commit that introduced it with no
`amended:` note.

**Drift is the one it exists for.** Registries do not fail by fabrication, they fail by nobody
diffing the registration against the report.

It prints its own limits every run, and that is deliberate: it verifies four mechanical facts about
files and cannot tell you a prediction was good or a test was severe. **Every green here is a green
about paperwork.**

## Climatic predictions due for scoring (added v0.95.0)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_climatic_predictions.py" --root .
```

`/mycelium:wardley-map`'s Climate step emits dated predictions into
`landscape.yml#climatic_predictions`. Predictions are the only part of a Wardley map that can
be WRONG — positions cannot be — so they are the part worth protecting, and they fail in one
specific way: **nobody scores them.**

Not through dishonesty. Scoring is boring and mapping is interesting, so the unscored pile
grows until the record means nothing and the project keeps meeting predictable things as news.
The Climate step tells the agent to score due predictions first, which covers the case where
someone runs a mapping pass. **This check covers the case where nobody does** — canvas-health
is periodic and does not wait for anyone to feel like mapping.

Exit 1 lists what is due, overdue, or **undated** (a prediction with no `due` can never be
overdue, so it can never be scored, so it is free to be right forever). Exit 2 is UNKNOWN and is
never a pass. Two advisory notes ride along and neither is an error: which of the five climatic
patterns has never produced a prediction, and — the one worth reading — whether a corpus with
scored predictions contains **zero** refuted or unscoreable ones. A forecasting record that has
never been wrong was not at risk.

## Evidence breadth (G-D2 / G-D4)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_source_independence.py" --root .
```

**Added v0.80.0.** This skill has cited "Torres: Evidence triangulation" since it
was written, and nothing computed it. G-D2 (2+ independent evidence *types*) and
G-D4 (2+ sources per opportunity) both carried a declared `NUDGE` level and
existed only as prose in three markdown files.

Two things the output means, and one it does not:

- A **G-D2 finding on one source** means a single source is carrying a claim
  above `anecdotal`/0.3. Either add a second source or lower the claim. One
  source *labelled* anecdotal is compliant, not a violation.
- A **G-D2 finding on many sources** means they all share one `source_class`.
  The count says N; the coverage says one. Two interviews are two sources and one
  method.
- The **unclassified count is not a violation.** It is why the triangulation
  denominator is small. Add `source_classes` to provenance to make those
  judgeable; until then the check says so rather than passing over them.

Report the denominator whenever quoting the result. A verdict over 4 of 47
provenance objects is not a statement about the canvas.

## Theory Citations
- Karpathy: Knowledge base health checks and auto-maintained indexes
- aiops3000: Anti-drift through externalized knowledge, versioned reference artifacts
- Raschka: "Context quality = model quality" -- canvas quality determines agent output quality
- Gilad: Confidence must be evidence-backed (confidence consistency checks)
- Torres: Evidence triangulation (evidence type consistency)

## Postflight: Verify-After-Write (claim matches state)

**Hard rule** (per CLAUDE.md Communication Rules, anti-pattern #7 *write-narration-verification* — mechanism Check 42, graduated v0.39.18; enforced surface expanded to this skill v0.44.0). This skill mandates multi-field canvas updates. Before narrating "updated / wrote / refreshed [canvas]" in any user-facing summary, RE-READ the value fields this skill's MANDATORY says to update and confirm they actually changed — not just `_meta.last_validated` or a freshness stamp. Each field you claim to have updated must reflect its new value. The symmetric half of the Read-before-Write Preflight: that one protects what gets read before a write; this one protects that the write matches the claim. Worked failures: 2026-06-05 #18 (`/dora-check` narrated "updated" with value fields unchanged) + #19 (`/retrospective` left a cycle-history aggregate un-propagated).

## Content in key position (added 2026-08-31, founder ruling)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_key_shape.py" --canvas-dir .claude/canvas
```

A canvas key carrying a date or an entity id in its NAME — `scope_correction_2026_08_27`,
`ht_010_status` — is content sitting in key position: a sentence wearing a field's clothes. It is
invisible to every field-level mechanism, no schema can declare it, and **a date in a key can only be
grepped, which is why `horizon_set_2026_08_28` never goes overdue while `horizon: 2026-08-28` can.**

Measured on the dogfood canvas at the ruling: **523 such keys**, 226 in `human-tasks.yml` alone.

The remedy is to move the content into values:

```yaml
# instead of
scope_correction_2026_08_27: "the sweep restates the thesis"
# write
notes:
  - date: 2026-08-27
    kind: scope_correction
    note: "the sweep restates the thesis"
```

**REPORT-ONLY unless `--strict`, and that is proportionality rather than timidity** — a rule written
today cannot make 523 pre-existing keys a build failure (see the founder's own note on gate-remedy
proportionality). Seed once with `--write-baseline`; from then on `--strict` fails only on NEW keys, so
the cost falls on new writing.

## Fields the canvas writes that no schema declares (added 2026-08-31)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_field_wiring.py" --live --canvas-dir .claude/canvas
```

**WHY A SECOND MODE EXISTS.** The default scan reads SCHEMAS, so it only sees fields somebody
declared. Every canvas schema sets `additionalProperties: true`, so a field can be written into the
canvas and never declared anywhere: measured on the dogfood canvas, **2210 of 2494 live keys (88%) are
declared by no schema.** `unlocked_at` was caught within three hours only because it happened to go
through a schema. `kill_criterion.date` did not, and sat unread for months.

**ONE-OFF KEYS ARE EXCLUDED AS PROSE.** Of 84 undeclared promise-shaped keys, **65 were used exactly
once** and were narrative annotations (`horizon_set_2026_08_28`); 19 recurred and were real fields.
Recurrence is what separates them, and without that filter this check would demand a consumer for 65
sentences and be muted within a day.

Seed the per-project baseline once with `--write-baseline`; from then on `--strict` fails only on a
NEW undeclared, unconsumed field — so the cost falls on new writing. The baseline lives in the
consumer's own repo (`.claude/harness/canvas-field-consumers.yml`), not in the framework, because
canvas content is project-specific.

**Each finding gets the four-step new-field rule** from `engine/agent-operating-contract.md`: is it
necessary, does a similar field already exist (`--similar <name>`), declare it in the schema, and wire
it or record it as human-only.
