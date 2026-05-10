# Consistency-Check Specification

Specification for a future REVIEW-tier guardrail that detects when **what the framework teaches diverges from what the framework enforces**. Graduates the "documented-rule-diverges-from-enforcement" cluster (see `memory/cluster-instances.md`) to spec status without yet shipping the mechanism. Promotion bar defined below.

This document is the artifact required by Check 26's stated graduation criterion: *"If a 6th instance of any subclass surfaces, the next graduation step is a unified 'framework changes ship with their own consistency checks' guardrail at REVIEW tier"* (commit `d6c4e9d`, 2026-05-04). The cluster reached that threshold and now sits at instance 8.

## Purpose

The framework documents disciplines (skills, theory gates, harness rules) and enforces them via mechanisms (schemas, validators, hooks, lints). When the documentation says one thing and the mechanism does something incompatible, writers — humans or agents — hit avoidable friction. Eight known instances spanning schema-vs-discipline, validator-vs-doc, hook-vs-rule, and doc-vs-rendering shapes (see cluster log).

This spec defines what consistency-checking would mean operationally, articulates detection-rule candidates per subclass, sets coverage-proof requirements, and specifies the bar for promoting from spec to a shipped mechanism.

## Definition

A **consistency check** verifies that one of the following pairs agree:

| Pair | What "agree" means |
|---|---|
| Schema vs discipline-vocabulary | Every term the discipline-doc teaches as canonical appears as a known field/value in the relevant schema |
| Validator vs documented rule | Every rule the doc claims is enforced is actually checked by the validator |
| Hook vs documented behavior | Every behavior CLAUDE.md or a guardrail claims fires, fires |
| Doc vs rendering | Every template the doc shows as canonical is reproduced by the renderer (no improvisation) |
| Skill vs schema | Fields a skill is taught to write are accepted by the schema (not rejected by additionalProperties strictness) |

A consistency violation is detected when the pair disagree AND the disagreement is unintentional (legitimate divergences are documented; see "Escape valves" below).

## Cluster catalog (8 known instances)

Sourced from `memory/cluster-instances.md#documented-rule-diverges-from-enforcement`. Subclasses help the detection-rule design — different shapes need different rules.

| # | Subclass | Shape attribute | Detection-rule candidate |
|---|---|---|---|
| 1-4 | mixed (pre-Check 26) | various | various per-instance |
| 5 | validator-vs-doc | "doc says validator enforces X; validator did not" | Cross-reference validator script against doc claims |
| 6 | schema-vs-discipline (vocabulary) | "doc teaches singular `source_class`; schema only accepts plural `source_classes`" | Term-coverage check across discipline-doc and schema |
| 7 | doc-vs-rendering | "doc shows template; renderer produces different output" | STRICT-marker presence on rendering-spec docs |
| 8 | schema-vs-discipline (missing field) | "doc teaches per-dimension backing; schema has only aggregate" | Discipline-vocabulary inventory matched to schema field inventory |

Pattern observations:
- Instances 1-5 fixed mechanism-side (validator changes, doc-following hook).
- Instances 6-8 fixed schema-or-doc side (schema accepts more shapes, doc tightens with STRICT marker).
- The asymmetry is meaningful: closer to schema/doc layer, the fix is closer to "make the artifact match the discipline." Closer to validator/hook layer, the fix is closer to "make the mechanism do what the doc says."

## Detection-rule candidates

Five concrete candidates. The promotion bar requires ≥3 to be validated against the cluster's instance corpus with <5% false-positive rate.

### Rule 1: Term-coverage check

For each `engine/*.md`, `skills/*/SKILL.md`, and `harness/*.md`, extract canonical-vocabulary terms (typically lowercase identifiers used as field names or enum values). For each canonical term, verify it appears in the relevant `schemas/canvas/*.schema.json` as either a property name, an enum value, or a $def name.

**Catches:** instance 6 (singular `source_class`), instance 8 (per-dimension naming).
**Misses:** instance 5 (validator-vs-doc), instance 7 (doc-vs-rendering).
**False-positive risk:** medium — vocabulary terms like "evidence" or "confidence" appear in many docs but only in some schemas. Need a corpus-curated allowlist of terms-to-skip.

### Rule 2: Schema-discipline mapping table

Maintain `engine/schema-discipline-map.yml` listing each discipline-vocabulary item, the schema where it lives, and any deliberate-divergence escape-valve markers. CI verifies the map is current: every `additionalProperties: false` schema must have all its "expected" fields enumerated in the map; any vocabulary term in the discipline doc must reference its schema location in the map.

**Catches:** instances 6, 8 directly. Forces documentation of new vocabulary at the moment it's added.
**Misses:** instances 5, 7.
**False-positive risk:** low — explicit map.
**Maintenance burden:** non-trivial (every schema/discipline change touches the map).

### Rule 3: Validator-claim cross-reference

For each `harness/*.md` or `engine/*.md` that contains "validates", "checks", "enforces" (or similar), extract the claim and verify a corresponding line exists in `.claude/scripts/` or `.claude/tests/`.

**Catches:** instance 5 (version-bump claim was in doc, validator didn't enforce).
**Misses:** instances 6, 7, 8.
**False-positive risk:** high — natural-language claim extraction is fuzzy.

### Rule 4: STRICT-marker presence on rendering specs

Any `engine/*.md` containing "Template" + "Render" sections must contain either a "STRICT — reproduce literally" marker OR a documented "this template is illustrative" disclaimer. Default-strict prevents improvisation.

**Catches:** instance 7 (wayfinding before 0.16.4 fix).
**Misses:** instances 5, 6, 8.
**False-positive risk:** low — narrow scope.
**Maintenance burden:** low.

### Rule 5: Hook-claim cross-reference

For each documented hook behavior (in CLAUDE.md, `harness/guardrails-*.md`, or skill PreToolUse claims), verify the corresponding hook file in `.claude/hooks/` or `.claude/scripts/` actually implements the behavior. Use grep + AST inspection if needed.

**Catches:** future hook-vs-rule instances (no historical instance documented yet, but the cluster shape is real per pattern observations).
**Misses:** non-hook instances.
**False-positive risk:** medium — hooks often have escape paths the doc doesn't fully describe.

## Coverage proof requirements (G-V12)

Per G-V12, any check that ships must demonstrate it catches at least one known-bad case. For this cluster the bar is sharper because the cluster's heterogeneity is the entire reason we're spec-only. The mechanism's coverage proof must include:

1. **Per-instance fixture set:** every cluster instance from `cluster-instances.md` becomes a test fixture (the artifacts at the time of the instance, before the fix).
2. **Per-rule expected-detect mapping:** which rules are expected to detect which fixtures (per the "Catches" lines above).
3. **False-positive corpus:** a set of artifacts that look-similar-but-aren't (e.g., legitimate divergences from "Escape valves" below). Each rule must NOT flag any FP-corpus member.
4. **Aggregate FP rate calculation:** rules that exceed 5% FP rate on the corpus do not count toward the promotion bar.

## Escape valves (legitimate divergence)

Not all documented-rule-divergences-from-enforcement are bugs. The mechanism must skip:

| Escape valve | Why legitimate | Detection signal |
|---|---|---|
| `out_of_scope` blocks (canvas/landscape.yml, decision-log entries) | Deliberate boundary; the framework explicitly does NOT enforce this | Look for `out_of_scope_summary`, `out of scope`, decision-log entry titled "scoping" |
| Emerging-research areas | Discipline genuinely too fast-moving to schematize yet | Doc carries `_research_emerging: true` annotation |
| Language-specific schema constraints | E.g., JSON Schema can't express some discipline shapes natively | Schema carries `_constraint_inherited: <language>` annotation |
| Workaround-pending-graduation | Known divergence, scheduled for fix | Doc references `cluster-instances.md` and the cluster's graduation status is `pending` |

Annotations are intentional friction: writers must explicitly mark divergences as legitimate. The mechanism's default is "flag every divergence."

## Promotion bar (spec → mechanism)

The cluster graduates from `spec` to `guardrail` (REVIEW tier) when **all four** conditions are met:

1. **≥3 detection rules** from the candidate list above are implemented as concrete checks (in `.claude/scripts/` or `.claude/tests/`).
2. **<5% false-positive rate** for each implemented rule, measured on the false-positive corpus.
3. **100% true-positive rate** across the cluster's known-instance fixtures (every historical instance is detected by at least one rule).
4. **Hook integration:** the checks are wired into either pre-commit (`validate-template.sh`), `/corrections-audit`, or a new dedicated hook. Detection without integration doesn't count.

Promotion requires an explicit decision-log entry stating the rules implemented, the FP rate measured, and the integration point chosen. The mechanism then ships with a Check number (e.g., Check 27) and a CLAUDE.md version bump (MINOR per version-discipline.md).

## What this spec does NOT do

- **Does not ship a check.** This is articulation; mechanism is deferred.
- **Does not require all five candidate rules.** Three is sufficient if they cover the cluster well; rules can be added post-promotion.
- **Does not auto-update.** Updates to this spec require explicit revision; that's the point — the framework's discipline about its own consistency-checking should be deliberate.

## Audit and maintenance

- **`/corrections-audit`** reads this file (post-promotion to spec-graduated, 2026-05-08). When the audit detects a candidate cluster instance, it cross-references this spec's catalog and reports whether the instance is novel or a recurrence.
- **`/framework-health`** checks the promotion bar quarterly. When ≥3 candidate rules have been drafted, framework-health surfaces graduation as a candidate next-step.
- **Direct edits to this file** require a corrections.md entry and a decision-log entry — the spec is a load-bearing artifact, not a scratchpad.

## Theory grounding

- **Senge** (Fifth Discipline): structural thinking — when patterns recur, the lever is structural, not behavioral. This spec is the structural articulation.
- **Argyris** (double-loop learning): single-loop = fix the instance; double-loop = fix the rule that allowed the instance. Triple-loop = fix the rule that prevented seeing the rule. The cluster log is double-loop; this spec is triple-loop (we're now reasoning about what kind of rule we'd need).
- **Lopopolo** ("every interaction is a failure of the harness to provide enough context"): un-detected divergences are accumulated harness-context-debt. This spec scopes the debt.
- **Mycelium's own discipline:** L1 → L2 → L3 → L4. The mechanism (L4) without an L3 (this spec) is exactly the process cliff the framework warns against. Building the mechanism without the spec would be skipping scales.
- **Postel's Law / Robustness Principle** ("be conservative in what you do, be liberal in what you accept from others" — RFC 793, Postel 1981). When a schema teaches `additionalProperties: false` strictness AND the rest of the framework conventions point at a field name the strict schema rejects, the schema is being more conservative in what it accepts than the framework is in what it teaches. The 0.16.2 fix accepting both `source_class` (singular) and `source_classes` (plural) inside provenance was Postel's Law applied: the strict mode preserves typo-detection (conservative on what it ships out — error messages) while accepting both natural-feeling forms (liberal on what it accepts in). Future `additionalProperties: false` decisions should pre-check whether the rejected field is a typo OR a natural extension of framework convention; if the latter, accept it. This is the schema-vs-discipline-vocabulary subclass's structural cure.
