# Cluster Instances

**Audience**: internal — published as audit trail, not as public reading.

Tracks instances of recurring correction patterns ("clusters") and their graduation status. Without this file, "the cluster has graduated 5 times" has no auditable backing — and the framework's own stated graduation criteria (e.g., Check 26's "graduate at instance 6") become unenforceable promises rather than mechanical triggers.

## How clusters work

Mycelium accumulates corrections in `corrections.md`. When multiple corrections share a root cause shape, they form a **cluster**. Per the framework's pattern-emergence rule (CLAUDE.md, leaf-lifecycle.md, framework-reflexion.md):

- ≥3 instances of the same root-cause shape = **first graduation candidate** (typically pattern entry, anti-pattern entry, or guardrail proposal).
- Subsequent instances trigger escalation per the cluster's stated graduation criterion.
- A cluster's graduation criterion is set when the pattern is recognized and SHOULD be re-evaluated as instances accumulate.

## How to use this file

- **When a new correction is logged in `corrections.md`**: check whether it fits an existing cluster. If yes, increment the cluster's instance count and add a row to its instance log. If no, create a new cluster section if the shape recurs (≥2 candidates).
- **When `/corrections-audit` runs**: it reads this file and reports cluster status (counts, graduation state, recent instances) alongside its frequency analysis.
- **When `/framework-health` runs**: it checks whether any cluster has crossed its graduation criterion without being graduated. Surfaces as a graduation-readiness signal.
- **Graduation status values**:
  - `pending` — below initial graduation candidate threshold
  - `pattern` — graduated to a `patterns.md` entry
  - `anti-pattern` — graduated to an `anti-patterns.md` entry
  - `guardrail` — graduated to a guardrail in `harness/guardrails-*.md` (typically REVIEW or BLOCK tier)
  - `spec` — specified in an engine doc but mechanism not yet shipped (deliberate scope choice)
  - `deprecated` — cluster no longer relevant (e.g., schema changed and the divergence shape can no longer occur)

## Active Clusters

### documented-rule-diverges-from-enforcement

A rule the framework teaches diverges from how the framework enforces it. Subclasses: schema-vs-discipline (vocabulary), validator-vs-doc (rule), hook-vs-rule (behavior), doc-vs-rendering (template strictness), schema-vs-skill (field shape).

**Graduation status:** `spec` (graduated to `engine/consistency-check-spec.md` 2026-05-08, version 0.17.0)

**Mechanism graduation bar:** ≥3 detection rules from the spec validated against the cluster's instance corpus with <5% false-positive rate. See `engine/consistency-check-spec.md#promotion-bar`.

**Total instances:** 14 (as of 2026-05-23 — instance 14 added late-session during validate_canvas.py refactor investigation; new sub-shape `validator-tolerance-vs-parser-strictness` graduated to mechanism same session via fail-loud refactor + positional argv fix + G-V12 fixture test)

**First instance:** pre-2026-04-28 (referenced in the Check 26 graduation commit `d6c4e9d`)

**Most recent:** 2026-05-23 late (instance 13 — ht-014/015 status field said `pending` while Discord activity since 2026-05-14 had moved testers to receive-mode; canvas-state did not flow back from external channel)

**Instance log:**

| # | Date | Title | Subclass | Outcome |
|---|---|---|---|---|
| 1-4 | various pre-2026-04-28 | Pre-Check 26 instances (referenced in Check 26 graduation commit `d6c4e9d`) | mixed | Each fixed individually |
| 5 | 2026-05-04 | Documented version-bump rule diverged from enforcement (downstream project saw "0.15.1 → 0.15.1, 42 files refreshed") | validator-vs-doc | Graduated → Check 26 (commit `d6c4e9d`, version 0.16.0) |
| 6 | 2026-05-06 | Singular `source_class` canonical at top-level, rejected inside provenance | schema-vs-discipline | Schema fix accepting both forms (commit `75a27cc`, version 0.16.2) |
| 7 | 2026-05-06 | Wayfinding doc was descriptive, not prescriptive; agent improvised template | doc-vs-rendering | Doc tightened with STRICT marker + forbidden deviations (commit `4259121`, version 0.16.4) |
| 8 | 2026-05-07 | JTBD schema can't natively express Christensen tripartite (per-dimension backing) | schema-vs-discipline | Schema fix + spec graduation (this commit, version 0.17.0) |
| 9 | 2026-05-08 | `validate-template.sh` checks 2/3/4/6/12/13 coupled to old README structure that the docs split replaced; failed mid-Phase-1 ship | validator-vs-doc | Fixed inline during Phase 1 ship (commit `114d841`, version 0.18.0): Checks 2/3/4 deprecated (Check 5 covers via canvas-update SKILL.md); Check 6 reads `docs/skills/README.md` with stub-aware skip; Check 12 reads `engine/theory-gates.md` (canonical gate source); Check 13 reads `docs/theories.md` with stub-aware skip |
| 10 | 2026-05-23 | Auto-dogfood orchestrator's hardcoded `_<skill>_task()` prompt templates bypass framework SKILL.md; three framework SKILL.md edits (v0.23.39/40/41) had zero auto-dogfood effect on `/interview` cold-start scenario | test-driver-vs-source-of-truth (new subclass) | Diagnosed via deep-dive 2026-05-23. Fixed in roadmap by adding decision-log directive to `_interview_task()` template (commit `6bb47f2`). Subclass added to `engine/consistency-check-spec.md` 2026-05-23 as Rule 6 with the roadmap `check_skill_prompt_drift.py` as the candidate detection rule's existing implementation. Framework `corrections.md` 2026-05-23 entry + `patterns.md` "Isolated capability test before instruction iteration" landed in parallel. |
| 11 | 2026-05-23 | `canvas-guidance.yml#action_flags.transitions.timeout_handling` (added 2026-05-03) said "Surface as a stale flagged item via /canvas-health" but `canvas-health` SKILL.md had no scanner for ON HOLD calendar timeouts; gap surfaced by the same-session `agents-md-router-discipline` regression scenario re-run that exposed instance 10 — the subagent observed that an ON HOLD item's May 7 date had silently passed 16 days ago with no canvas-health surfacing. **Recursive aspect**: this very session graduated instance 10 (test-driver bypassing SKILL.md) and almost immediately discovered instance 11 (canvas-health doesn't implement what its convention says). Two same-cluster instances in one session is itself a pattern worth noting — the cluster's substrate (every place where doc-says-X but mechanism-doesn't-do-X) has more surface area than the spec's 5-rule taxonomy currently catches. | validator-vs-doc (closest existing subclass; could justify a sibling subclass `convention-promise-vs-skill-implementation`) | Fixed same-session by adding Step 9c to `canvas-health/SKILL.md` (v0.23.43). The new step is a checked-but-not-mechanically-validated implementation; a Rule 7 candidate (generalized "convention promise → downstream-skill implementation" cross-reference) could be drafted in the next consistency-check-spec.md update if a 12th instance surfaces. |
| 12 | 2026-05-23 late | Session-start hook claimed "BVSSH health has never been assessed" while `mycelium-roadmap/.claude/canvas/bvssh-health.yml` showed 5 prior assessments (last 2026-05-04). Hook scans framework-local canvas only; blind to roadmap-side state. Doc-says-X (BVSSH never assessed); mechanism-doesn't-see-Y (roadmap canvas). Discovered during user prompt "run bvssh on l0" — l0-purpose lives in roadmap. | hook-vs-state (new sub-shape: instrument scope mismatch) | Not fixed in-session. L4-backlogged: broaden BVSSH session-start hook to scan roadmap canvas. Per CLAUDE.md v0.23.43 changelog forecast ("12th instance suggests sibling subclass `convention-promise-vs-skill-implementation`"), this instance arguably belongs to a third sibling: `hook-scope-vs-canvas-distribution`. Pre-graduation; needs ≥2 more instances of this sub-shape. |
| 13 | 2026-05-23 late | `human-tasks.yml` showed `status: pending` for ht-014 and ht-015 while an external communication channel had recorded outbound brief 2026-05-14, infrastructure provisioning 2026-05-19, and capacity-window heads-up 2026-05-20. 9-day canvas drift. Explore agent reported "pending start"; downstream assessment built a recommendation on the stale state. **New sub-shape**: `canvas-state-vs-reality-drift` — divergence direction is inverted from instances 1-11 (state-of-reality-is-X-canvas-says-Y, not doc-says-X-mechanism-doesn't-do-X). No back-flow mechanism from external activity channels into canvas. | canvas-state-vs-reality (new sub-shape candidate) | Fixed in-session: ht-014/015 status pending→in_progress; touch_log entries appended. No mechanism added — single instance of this sub-shape. Carry-forward candidates if recurrence: (a) `/canvas-health` warning when `human-tasks.yml` entries have `status:pending` with `created_at` >14 days ago; (b) session-start prompt to confirm in-flight ht-* status. |
| 14 | 2026-05-23 late | `validate_canvas.py` reported "Canvas validation: PASS" on roadmap canvas despite YAML parse error in `north-star.yml` (introduced same session by /metrics-pull #35 commit f06634d, broken until next-session triage). Root cause: schema-validation layer silently returned `[]` for files without schemas (line 135-137); trace walk warned-then-continued (line 212-218). Combined effect on schemaless files with parse errors: silent PASS. Also surfaced: validator silently defaulted to cwd canvas when positional argv was ignored — session-long "PASS" reports were against framework canvas while user thought they were against roadmap. | validator-tolerance-vs-parser-strictness (new sub-shape) | **GRADUATED TO MECHANISM same session**. Added `validate_all_yaml_parses()` to validate_canvas.py main() — fail-loud parse check runs BEFORE schema validation + trace walk; surfaces ALL parse errors regardless of schema presence. Also added positional argv handling (`python3 validate_canvas.py [canvas_dir]`) to fix the cwd-confusion surface. G-V12 fixture test at `tests/bash/test_validate_canvas_fail_loud.sh` (broken_yaml + clean fixtures; 6 assertions; first-try pass). Inventory pass against both repos pre-flip confirmed 0 pre-existing breaks (50 files scanned). Bash-check-without-fixture-test convention used as test home — same shape as v0.23.43's bash fixture-test infrastructure. |

**Spec-graduation rationale (2026-05-08):** Cluster reached the Check 26 stated graduation criterion ("graduate at instance 6") several days before today's audit; instances 6 and 7 were fixed individually without being counted. Today's instance 8 forced an honest recount and a decision: graduate fully now (full mechanism) vs spec-only (framework-discipline-driven choice). Chose spec because the cluster's instances are heterogeneous and a single detection rule covering all subclasses is research-shaped; spec articulates what consistency-checking means + sets a mechanical promotion bar without shipping a half-baked check. See `engine/consistency-check-spec.md` for full rationale.

### consistency-as-evidence

Agent constructs a causal chain or behavior-claim where ≥1 link rests on consistency-only evidence (data point is consistent with the hypothesis but does not test it) and treats the chain as load-bearing. Sub-classes catalogued so far: (a) **canvas-write** — agent writes a claim into a canvas file conflating consistency with attribution; (b) **conversational** — agent confirms a behavior claim asserted in dialog without challenging the evidence source; (c) **self-application** — agent constructs the chain in its OWN analysis even after warning against the same failure mode for users in the same response; (d) **graduation-velocity** — multiple framework graduations in one session where the genuine lived-friction trigger extends into adjacent graduations via consistency-with-the-running-playbook rather than per-graduation attribution; (e) **subagent-output-verification** — agent accepts a subagent's specific claim about Mycelium files/fields and propagates it in synthesis without grep/Read verification; (f) **window-framing-inconsistency** — agent applies different time windows to different metrics within a single synthesis, picking framings that produce the cleaner narrative; (g) **capacity-vs-evidence-gating** — agent labels evidence-gated items as capacity-deferred (implicit causal link between a date and an unblock event where the date is observationally consistent but not interventionally causal).

**Graduation status:** `anti-pattern` (graduated 2026-05-09 to `harness/anti-patterns.md` as #7) + `behavioral-enforcement-canvas-writes` (v0.22.0 shipped Read-before-Write, Validator Check 31, /diamond-assess Step 3 Read-before-claim hard rule).

**Pending sub-graduations:**
- **Conversational sub-class**: NOT covered by the canvas-write enforcement layer. Next graduation candidate: structural enforcement requiring agent to name + cite + (where applicable) read the evidence source before confirming a behavior claim. Threshold criterion already met.
- **Implicit-causal-link sub-class** (sub-class g, surfaced 2026-05-23): NOT covered by Pre-Ship #9 (attribution-labelling pass operates on explicit causal chains, not implicit date/threshold causality). Candidate mechanism: output convention requiring `Gated by: [event]` clause on every deferral, threshold, or date-based recommendation — making the implicit causal link inspectable in user-facing output. See CLAUDE.md Communication Rules.

**Graduation philosophy (load-bearing, established 2026-05-09):** This class is **almost impossible to fully avoid** — humans don't write or tell absolutely everything (Grice's maxim of quantity; Sperber & Wilson relevance theory). Speakers compress; listeners interpolate; the interpolation IS the failure surface. The mechanism cannot be "stop interpolating" (cognitively impossible at scale). The mechanism must be **make the interpolation visible so it can be checked** — surface the inferred bridge as a flag for the human, not as a claim the agent acts on. Different mechanism class than anti-patterns where the answer is "stop doing X." This philosophy distinguishes AP#7-shaped graduations from the rest of the cluster catalog.

**Total instances:** 12+ catalogued across both repos (framework public corrections.md + roadmap private corrections.md). 4 new instances added 2026-05-23 session: sub-class g implicit-causal-link (BVSSH-deferral conflation) + sub-class g variant temporal-binarization (same-turn recurrence) + sub-class e new surface validator-output-verification (EXE001 "pre-existing" claim) + sub-class c self-application (P6 Edith-Mari evidence dismissed within service-check). Sub-class distribution skews to conversational + self-application + trust-without-verification; canvas-write enforcement layer (v0.22.0) reduced canvas-write recurrence but did not eliminate adjacent surfaces. Sub-class e broadened from subagent-output-verification → trust-without-verification 2026-05-23 to cover any tool/wrapper/dialog claim the agent didn't independently verify. `Verify-before-propagate:` convention shipped 2026-05-23 to CLAUDE.md Communication Rules as next mechanism layer for sub-classes b + e.

**First instance:** 2026-04-30 (agent over-scoped before learning constraints; constructed plan from partial information without checking budget)

**Most recent (framework-visible):** 2026-05-23 (capacity-vs-evidence-gating conflation in BVSSH-on-l0-purpose recommendation; Pre-Ship #9 ran and did not catch the implicit causal link between deferral date and unblock event)

**Instance summary (generic-framed; per-instance detail in roadmap-private cluster-instances.md):**

| Date range | Sub-class | Count | Notable |
|---|---|---|---|
| 2026-04-30 → 2026-05-03 | self-application | 2 | Pre-graduation; established cluster shape |
| 2026-05-09 | canvas-write + conversational + self-application | 5 | Same-day graduation + 3 same-day instances of self-failure; documentation alone proved insufficient |
| 2026-05-10 → 2026-05-11 | graduation-velocity, subagent-output-verification, window-framing-inconsistency | 3 | Three new sub-classes within 2 days; surface proliferation rate signal |
| 2026-05-23 | capacity-vs-evidence-gating + temporal-binarization | 2 | Pre-Ship #9 ran without catching; implicit-causal-link sub-shape (NEW: g). 2nd instance same-turn as convention's ship (analogue of 2026-05-09 same-day-as-graduation recurrence pattern) — convention's effectiveness requires applying it to agent's own scope-pushback statements, not just user-facing recommendations |
| 2026-05-23 (post-ship) | validator-output-verification (new surface for sub-class e) | 1 | After v0.24.0 ship, agent reported 3 validator WARNs as "all pre-existing tech debt" by reading the validator's wrapper text instead of running ruff to inspect findings. Drill-down revealed ruff EXE001 was on `check_gated_by.py` (shipped same commit, ~1 hour earlier). Self-introduced regression propagated as pre-existing because trust-without-verification. Fix: chmod +x; v0.24.1 PATCH. Same shape as sub-class (e) instance #9 (2026-05-11) but applied to validator output instead of subagent output — sub-class needs re-definition to cover "any tool output containing a wrapper claim the agent didn't independently verify." |

**Why this cluster has its own structural entry:** The 5+ instances within one working day post-graduation (2 within a single 6-hour window in 2026-05-09) made graduation accounting load-bearing rather than oral history. Lived in `corrections.md` only until structurally promoted. Theory grounding (Grice, Sperber-Wilson) is the framework-public insight that distinguishes this cluster's mechanism class from "stop doing X" anti-patterns.

**Theory grounding for this cluster:** Pearl (causal inference — observational vs interventional evidence); Kahneman *Thinking Fast and Slow* ch. 20 (*Illusion of Validity* — over-confidence in judgments from internally-consistent but causally-unverified evidence); Grice (maxim of quantity — speakers compress, listeners interpolate); Sperber & Wilson (relevance theory — the listener's interpolation is the failure surface, not the failure cause); Lopopolo ("every interaction is a failure of the harness to provide enough context" — un-graduated AP#7 sub-classes are accumulated harness-context-debt).

### bash-check-without-fixture-test

A Bash check graduated to `tests/validate-template.sh` ships without a fixture test demonstrating it flags its target failure mode. G-V12 from `engine/consistency-check-spec.md` (graduated 2026-05-04) requires "every check that flags a problem ships with a test demonstrating it does." Bash checks have shipped without this discipline because (a) Python testing infrastructure was mature (pytest, conftest.py, test_*.py convention) and Bash testing had no convention, (b) bash check functions in the validator weren't sourcing-friendly (running them in isolation required refactor), (c) coverage proof was implicitly assumed from "the check fired during the historical instance that triggered graduation" — consistency-only evidence, exactly the AP#7 sub-class (e) shape (subagent-output-verification analogue: trusting the historical fire instance as coverage without an interventional fixture proof).

**Graduation status:** `pattern` (graduated 2026-05-23 to test convention in `tests/bash/`; Phase 1 — all 7 post-G-V12 checks — completed same day. Phases 2-5 retroactive sweep of pre-G-V12 checks remains as lower-priority backlog.)

**Mechanism shipped 2026-05-23:**
- Sourcing guard in `tests/validate-template.sh` so check_* functions can be invoked individually
- `tests/bash/` convention: `_assert.sh` + `run.sh` + `test_check_<N>.sh` + `fixtures/check_<N>/<scenario>/`
- Worked examples: Check 30 (plugin.json version sync), Check 34 (CLAUDE.md single version), Check 28 (manifest byte-match)
- Wired into Check 17 alongside pytest — bash check tests now run as part of `tests/validate-template.sh`

**Total instances:** 7 catalogued (Checks 26, 28, 29, 31, 32, 33, 34 — all graduated post-2026-05-04 without fixtures) + ~22 pre-G-V12-era Bash checks (Checks 1-25, lacking fixtures but predating the discipline)

**First instance:** 2026-05-04 (Check 26 version-bump discipline shipped without fixture — same commit that graduated G-V12 spec)

**Most recent:** 2026-05-23 (Check 30 plugin.json sync shipped same morning without fixture; same-day audit surfaced the cluster)

**Instance log (post-G-V12 graduations):**

| # | Date | Check | Fixture-test status |
|---|---|---|---|
| 1 | 2026-05-04 | Check 26 (version-bump discipline) | ✅ Fixture test shipped 2026-05-23 (runtime git-repo construction in tempdir) |
| 2 | 2026-05-? | Check 28 (manifest byte-match) | ✅ Fixture test shipped 2026-05-23 |
| 3 | 2026-05-? | Check 29 (stale-state-read pattern scan) | ✅ Fixture test shipped 2026-05-23 |
| 4 | 2026-05-09 | Check 31 (canvas-write Preflight) | ✅ Fixture test shipped 2026-05-23 |
| 5 | 2026-05-09 | Check 32 (Four-Risks levels) | ✅ Fixture test shipped 2026-05-23 |
| 6 | 2026-05-14 | Check 33 (named-attribution leak) | ✅ Fixture test shipped 2026-05-23 (env-var-pointed fixture registry) |
| 7 | 2026-05-23 | Check 34 (CLAUDE.md single version) | ✅ Fixture test shipped 2026-05-23 |
| (+0) | 2026-05-23 | Check 30 (plugin.json version sync) | ✅ Worked example shipping the convention |

**Phase 1 complete (2026-05-23):** All 7 post-G-V12 Bash checks now have fixture tests, plus the worked example (Check 30). 8 total test files. Original estimate 4.5-6.5h; actual time ~1.5h thanks to convention reuse — each subsequent fixture took 15-25 min once the pattern was established (sourcing guard + capture()/run_test()/report() helpers). Cluster's primary graduation pressure now closed: every check graduated under G-V12 has an interventional coverage proof.

**Phases 2-5 (retroactive coverage of pre-G-V12 Bash checks):** ~22 additional checks (1-25 excluding 17, 26, 27, which are either complex/external or covered). 12-17 hours estimated. Lower priority — these pre-date G-V12 and have implicit production stress-test history. Defer until next post-surgery work window.

**Phases 2-5 (retroactive coverage of pre-G-V12 Bash checks):** ~22 additional checks, 12-17 hours estimated total. Lower priority — these checks pre-date the G-V12 discipline and have implicit production stress-test history. Defer until Phase 1 lands, then evaluate against then-current capacity and competing priorities.

**Theory grounding for this cluster:** Pearl (interventional vs observational evidence — "the check fired historically" is observational; an intentionally-broken fixture flag is interventional). Ohno (jidoka — build the test that catches the failure; don't rely on memory of when the failure last surfaced). Bridge to anti-pattern #7 sub-class (e) subagent-output-verification: same trust-without-verification shape applied to a different surface (trust-without-fixture-proof instead of trust-without-grep-verification).

### subagent-simulation-misses-lived-friction

Pre-ship validation done via parallel blind subagent simulations passes — but the same code path fails when invoked for real by a user. The subagent's simulated invocation doesn't reproduce all the runtime conditions of a real session (path resolution context, prior conversation state, tool-surface idiosyncrasies). The simulations confirm what they're scoped to confirm; they don't catch what they're not scoped to look at. **Distinct from confirmation bias**: the simulations are honestly testing what they were designed to test; the failure is scope-of-test, not interpretation-of-result.

**Graduation status:** `pending` (2 instances, structural pattern named but no mechanism graduated yet)

**Graduation criterion:** Either (a) 3rd instance with the same shape (subagent simulation passes, real invocation fails), OR (b) a designed countermeasure that proves itself. Candidate countermeasures:
1. **Real-invocation smoke layer**: after every framework change shipped behind subagent simulation, the maintainer must invoke the affected entrypoint in a real session before declaring "done." Not just `bash tests/validate-template.sh` — actually invoking the user-facing skill.
2. **Subagent test-design audit**: for each subagent simulation, name explicitly what conditions are NOT being reproduced (path context, conversation state, tool-surface specifics) — published in the test design, not implicit.

**Total instances:** 2 (as of 2026-05-10)

**First instance:** 2026-05-09 (plugin-form dogfood B1-B5)

**Most recent:** 2026-05-10 (bare-path round-2 gap surfaced by `/metrics-pull`)

**Instance log:**

| # | Date | Title | What the simulation missed | Outcome |
|---|---|---|---|---|
| 1 | 2026-05-09 | Plugin-form dogfood found 5 bugs (B1-B5) that 4 prior parallel blind-subagent simulations of v0.20.6 had not caught (warnings-log starter content getting `${CLAUDE_PLUGIN_ROOT}` expanded during Write, start/SKILL.md mkdir-before-detection ordering, plugin.json drift, Check 26 watch-list gap, `.claude/state/` not acknowledged) | Subagents simulated workflow steps but didn't simulate (a) literal `${CLAUDE_PLUGIN_ROOT}` text being expanded in a Write target body, (b) how Read-before-Write interacts with hard-gate ordering, (c) what an actual user's `.claude/state/` directory looks like | All 5 bugs fixed in v0.20.11; "subagent simulation ≠ lived friction" graduated as a lesson in receipts case `2026-05-09-plugin-form-dogfood.md`; lesson cited in v0.23.0 dogfood report |
| 2 | 2026-05-10 | `/mycelium:metrics-pull` failed in plugin form because `metrics-pull/SKILL.md` referenced bare `metrics-adapters/<source>.md`. 4 parallel blind-subagent simulations of v0.20.6 (which preceded the v0.20.7 sweep) didn't catch this because they tested workflow correctness, not path-resolution-in-plugin-form for sub-directory paths | Subagents tested skill workflow shape (do the steps run? do they produce output?), not "does the path resolve correctly when the agent's CWD is the user's project and the plugin tree is elsewhere?" The simulation passed because the simulated-skill happened to have access to framework files via its own context, masking the missing-path-prefix bug | All 30 sites fixed in v0.23.3; cluster section created in roadmap; ported to framework 2026-05-23 |

**Why this cluster has a structural entry at only 2 instances:** Surfaced at 2 rather than waiting for ≥3 because (a) failure shape is unusually clean — both instances are "subagent simulation passed → real invocation failed" with no other variable; (b) second instance occurred same day as the first cluster member's graduation lesson was logged (compressed time signal — the lesson exists, the structural fix doesn't); (c) the project actively prefers blind-subagent simulations as the assumption-test method (auto-memory feedback note) so the failure mode is structurally aligned with how this team works rather than accidental. Graduation criterion is set explicitly to give the next instance a target rather than letting it accumulate further.

**Theory grounding for this cluster:** Argyris (single-loop vs double-loop learning — simulation passing was single-loop "did the steps execute"; lived-friction failure is the double-loop "are the right things being tested"). Hoskins (scenario-driven validation — synthetic scenarios cover the scenarios the test author imagined; lived scenarios cover what users actually do). Bridge to anti-pattern #7: trusting simulation results without testing them against real invocation is Level 2 (executed step, missing attribution) of the consistency-as-evidence anti-pattern's failure-level decomposition.

### agent-as-instrument-on-shadow-logs

A test/check requires the agent to self-record behavioral data (per-session rows, citation counts, faithfulness audits) without a mechanical capture mechanism, and the recording is unreliable. Anti-pattern #7 Level 1 (skipped step) applied to test instruments specifically. Subclasses: shadow-log table (per-session rows empty), counter-misclassification (non-shadow-log file swept into session-counter nagging).

**Graduation status:** `pending` (at first graduation candidate threshold: 2 instances; one more recurrence triggers graduation)

**Graduation criterion (if pending):** ≥3 instances OR ≥1 instance where the missing data led to a wrong framework decision (e.g., a rule kept that should have been killed, or vice versa). When met, graduate to mechanism: a recording hook companion to v0.23.8's C1 (`read-log.sh` + `verify_citations.py`) — same capture-then-audit shape, different captured behavior. C1 is the worked example for what the relay-check / shadow-log-record hook should look like.

**Total instances:** 2 (as of 2026-05-12)

**First instance:** 2026-05-02 (`relay-norms` shadow log opened)

**Most recent:** 2026-05-12 (closure session that surfaced the cluster)

**Instance log:**

| # | Date | Title | Subclass | Outcome |
|---|---|---|---|---|
| 1 | 2026-05-02 → 2026-05-12 | `relay-norms` assumption-test ran 15/10 sessions with empty per-session log table; agent didn't fill in rows | shadow-log-table | Closed INCONCLUSIVE 2026-05-12. Norm 1 (SessionStart relay) flagged for harness graduation; Norms 2-3 kept in CLAUDE.md as low-trust. |
| 2 | 2026-05-04 → 2026-05-12 | `xai-inline-attribution` assumption-test ran 11/10 sessions with only session 1 recorded (partial); sessions 2-11 absent | shadow-log-table | Closed INSTRUMENT-FAILED 2026-05-12. Rule remains in CLAUDE.md; v0.23.8's C1 (`verify_citations.py`) supersedes the shadow-log instrument. Juniors.dev named as next evaluation surface. |

**Near-miss (not counted; different root cause):**

`xai-check-evals` (2026-05-04 → 2026-05-12) — static coverage-fixture set incorrectly counter-nagged at sessions=10. NOT the same shape as instances 1-2 (the agent didn't fail to record; the counter mechanism failed to discriminate non-shadow-log files). Logged separately as harness-followup candidate: counter-mechanism should require `kind: shadow_log` field before nagging.

**Theory grounding for this cluster:** Lopopolo ("every interaction with the agent is a failure of the harness to provide enough context") — the shadow-log pattern asks the agent to be the harness for itself. The relay-norms doc explicitly named this risk in its own Codification-venue section 2026-05-02 ("if a norm has a clean mechanical trigger, prefer harness encoding — it survives agent-norm drift"); the cluster's two instances are evidence that the warning was correct. Bridge to anti-pattern #7: skipping the recording step is Level 1 (skipped step) of the consistency-as-evidence anti-pattern's failure-level decomposition (v0.23.8 deep dive).

## Format for new clusters

```markdown
### <cluster-slug>

<one-paragraph description of the cluster's root-cause shape>

**Graduation status:** <pending | pattern | anti-pattern | guardrail | spec | deprecated>

**Graduation criterion (if pending):** <what triggers graduation; e.g., ≥3 instances, ≥3 detection rules validated, etc.>

**Total instances:** <N>

**First instance:** <date>

**Most recent:** <date> (<one-line title>)

**Instance log:**

| # | Date | Title | Subclass | Outcome |
|---|---|---|---|---|
| 1 | <date> | <title> | <subclass if useful> | <fix or graduation outcome> |
```

## Theory grounding

- **Senge** (Fifth Discipline): recurring patterns signal structural issues. The cluster log is the structural-issue ledger.
- **Toyoda/Ohno** (5 Whys): when 3+ instances share a root cause, the root has structural locus. Graduation moves it from per-instance handling to mechanism.
- **Argyris** (double-loop learning): single-loop = fix the instance; double-loop = fix the rule that lets the instance happen. Graduation IS the double-loop step.
- **Lopopolo** ("every interaction is a failure of the harness to provide enough context"): un-graduated clusters are accumulated harness-context-debt.
