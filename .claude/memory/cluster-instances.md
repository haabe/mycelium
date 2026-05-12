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

**Total instances:** 9 (as of 2026-05-08)

**First instance:** pre-2026-04-28 (referenced in the Check 26 graduation commit `d6c4e9d`)

**Most recent:** 2026-05-08 (validator-template.sh checks coupled to old README structure)

**Instance log:**

| # | Date | Title | Subclass | Outcome |
|---|---|---|---|---|
| 1-4 | various pre-2026-04-28 | Pre-Check 26 instances (referenced in Check 26 graduation commit `d6c4e9d`) | mixed | Each fixed individually |
| 5 | 2026-05-04 | Documented version-bump rule diverged from enforcement (downstream project saw "0.15.1 → 0.15.1, 42 files refreshed") | validator-vs-doc | Graduated → Check 26 (commit `d6c4e9d`, version 0.16.0) |
| 6 | 2026-05-06 | Singular `source_class` canonical at top-level, rejected inside provenance | schema-vs-discipline | Schema fix accepting both forms (commit `75a27cc`, version 0.16.2) |
| 7 | 2026-05-06 | Wayfinding doc was descriptive, not prescriptive; agent improvised template | doc-vs-rendering | Doc tightened with STRICT marker + forbidden deviations (commit `4259121`, version 0.16.4) |
| 8 | 2026-05-07 | JTBD schema can't natively express Christensen tripartite (per-dimension backing) | schema-vs-discipline | Schema fix + spec graduation (this commit, version 0.17.0) |
| 9 | 2026-05-08 | `validate-template.sh` checks 2/3/4/6/12/13 coupled to old README structure that the docs split replaced; failed mid-Phase-1 ship | validator-vs-doc | Fixed inline during Phase 1 ship (commit `114d841`, version 0.18.0): Checks 2/3/4 deprecated (Check 5 covers via canvas-update SKILL.md); Check 6 reads `docs/skills/README.md` with stub-aware skip; Check 12 reads `engine/theory-gates.md` (canonical gate source); Check 13 reads `docs/theories.md` with stub-aware skip |

**Spec-graduation rationale (2026-05-08):** Cluster reached the Check 26 stated graduation criterion ("graduate at instance 6") several days before today's audit; instances 6 and 7 were fixed individually without being counted. Today's instance 8 forced an honest recount and a decision: graduate fully now (full mechanism) vs spec-only (framework-discipline-driven choice). Chose spec because the cluster's instances are heterogeneous and a single detection rule covering all subclasses is research-shaped; spec articulates what consistency-checking means + sets a mechanical promotion bar without shipping a half-baked check. See `engine/consistency-check-spec.md` for full rationale.

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
