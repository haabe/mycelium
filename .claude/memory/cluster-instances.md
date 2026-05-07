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
