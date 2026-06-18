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

## Cluster catalog (13 known instances)

Sourced from `memory/cluster-instances.md#documented-rule-diverges-from-enforcement`. Subclasses help the detection-rule design — different shapes need different rules.

| # | Subclass | Shape attribute | Detection-rule candidate |
|---|---|---|---|
| 1-4 | mixed (pre-Check 26) | various | various per-instance |
| 5 | validator-vs-doc | "doc says validator enforces X; validator did not" | Cross-reference validator script against doc claims |
| 6 | schema-vs-discipline (vocabulary) | "doc teaches singular `source_class`; schema only accepts plural `source_classes`" | Term-coverage check across discipline-doc and schema |
| 7 | doc-vs-rendering | "doc shows template; renderer produces different output" | STRICT-marker presence on rendering-spec docs |
| 8 | schema-vs-discipline (missing field) | "doc teaches per-dimension backing; schema has only aggregate" | Discipline-vocabulary inventory matched to schema field inventory |
| 9 | validator-vs-doc (mid-ship) | `validate-template.sh` Checks 2/3/4/6/12/13 coupled to README structure that the docs split replaced; failed mid-Phase-1 ship 2026-05-08 | Continuous coupling-graph check between validator scripts and the doc surfaces they consume |
| 10 | test-driver-vs-source-of-truth | 2026-05-23: auto-dogfood orchestrator's hardcoded `_<skill>_task()` prompts bypass framework SKILL.md; three framework SKILL.md edits (v0.23.39/40/41) had zero auto-dogfood effect | Drift-check between framework SKILL.md write-paths and roadmap orchestrator task templates (Rule 6 below). Implementation already exists at `mycelium-roadmap/.claude/auto-dogfood/scripts/check_skill_prompt_drift.py` |
| 11 | validator-vs-doc | 2026-05-23: `canvas-guidance.yml#action_flags.transitions.timeout_handling` (2026-05-03) said "Surface as a stale flagged item via /canvas-health" but `canvas-health` SKILL.md had no scanner for ON HOLD calendar timeouts; gap surfaced by the `agents-md-router-discipline` regression scenario re-run 2026-05-23. Fixed same-session by adding Step 9c to `canvas-health/SKILL.md` (v0.23.43). | Hook-claim cross-reference (Rule 5) generalized to "every doc that names a downstream surface ("/skill does X") must trace to that surface's actual implementation" |
| 12 | hook-vs-documented-behavior (cross-surface) | 2026-06-12: `autonomous-evidence-guard.sh` shipped v0.42.0 registered in `hooks.json` only — `hooks.codex.json` + `hooks.cursor.json` never gained the registration, leaving Codex/Cursor surfaces with ZERO autonomous evidence-integrity enforcement for the exact fabrication class the guard blocks (and the framework docs describing the guard made no surface distinction). Found by the 2026-06-12 five-dimension gap analysis; fixed same-session (v0.44.1) + mechanized as Check 44. | Rule 5 narrowed to its mechanizable core: registered-script existence + cross-surface registration parity with a documented-divergence allowlist (Check 44) |

Pattern observations:
- Instances 1-5 fixed mechanism-side (validator changes, doc-following hook).
- Instances 6-8 fixed schema-or-doc side (schema accepts more shapes, doc tightens with STRICT marker).
- The asymmetry is meaningful: closer to schema/doc layer, the fix is closer to "make the artifact match the discipline." Closer to validator/hook layer, the fix is closer to "make the mechanism do what the doc says."

## Detection-rule candidates

Six concrete candidates. The promotion bar requires ≥3 to be validated against the cluster's instance corpus with <5% false-positive rate. Rule 6 added 2026-05-23 alongside instance 10 (test-driver-vs-source-of-truth subclass); an implementation of Rule 6 already exists in the roadmap repo as `check_skill_prompt_drift.py`.

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

### Rule 4: STRICT-marker presence on rendering specs — PROMOTED (Check 39, 2026-06-02)

Any `engine/*.md` containing "Template" + "Render" sections must contain either a "STRICT — reproduce literally" marker OR a documented "this template is illustrative" disclaimer. Default-strict prevents improvisation.

**Catches:** instance 7 (wayfinding before 0.16.4 fix).
**Misses:** instances 5, 6, 8.
**False-positive risk:** low — narrow scope. Measured FP rate on the upstream engine/ corpus 2026-06-02: 0/20 docs (2 in scope, both compliant).
**Maintenance burden:** low.

**Promotion provenance:** /mycelium:framework-health on the dogfood repo 2026-06-02 surfaced the cluster's 25-day spec-status duration. Analysis determined the original "≥3 rules" criterion was not met and was not nearly-met (only Rule 6 has an implementation; Rule 6's FP measurement is pending). Rather than downgrade the criterion OR ship the broader mechanism unprepared, Rule 4 was promoted independently because it is (a) narrow, (b) mechanizable today, (c) directly addresses one known historical instance, (d) prevents the same shape in any new rendering-spec doc. The broader cluster remains at `spec` status; this is **per-rule promotion**, not cluster graduation. See Promotion bar §"Per-rule promotion" below.

### Rule 5: Hook-claim cross-reference

For each documented hook behavior (in CLAUDE.md, `harness/guardrails-*.md`, or skill PreToolUse claims), verify the corresponding hook file in `.claude/hooks/` or `.claude/scripts/` actually implements the behavior. Use grep + AST inspection if needed.

**Catches:** future hook-vs-rule instances (no historical instance documented yet, but the cluster shape is real per pattern observations).
**Misses:** non-hook instances.
**False-positive risk:** medium — hooks often have escape paths the doc doesn't fully describe.

### Rule 6: Test-driver vs source-of-truth drift (added 2026-05-23)

For each test driver that has hardcoded expectations about framework artifacts (the auto-dogfood orchestrator's `_<skill>_task()` prompt templates being the canonical case), compare the test driver's expectations against the corresponding framework SKILL.md's documented write-paths / behavior. Warn when the framework documents a write-path the test driver doesn't enforce, or vice versa.

**Catches:** instance 10 (auto-dogfood orchestrator's `_interview_task()` bypassing `/interview` SKILL.md). Same shape applies to any future test driver / fixture / scenario that's decoupled from its canonical source.
**Misses:** divergences in non-write-path behavior (e.g., conditional logic, dynamic content rendering). The current implementation is heuristic on write-paths only.
**False-positive risk:** medium-to-high — the heuristic over-collects when SKILL.md mentions paths in meta-references or conditional contexts (see `mycelium-roadmap/.claude/auto-dogfood/scripts/README.md` for the known caveat list).

**Implementation status:** EXISTS at `mycelium-roadmap/.claude/auto-dogfood/scripts/check_skill_prompt_drift.py` (~200 LOC, pure stdlib). Roadmap-private because the auto-dogfood orchestrator is roadmap-private per the 2026-05-22 architectural decision. Counts toward the promotion-bar's "validated against the cluster's instance corpus" requirement for instance 10 (the specific instance this rule catches). FP rate measurement against the broader instance corpus pending.

**Maintenance burden:** low. Heuristic regex + write-context window; no external dependencies.

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
| Framework-wide procedural writes (added 2026-06-02) | Writes mandated by framework-wide rules, not skill-specific decisions: `harness/decision-log.md` (G-P4 — every decision-bearing skill logs to it) and `diamonds/active.yml` (theory-gates / diamond-progress — every gate-bearing skill updates it). Repeating these in every SKILL.md would be noise. | The flagged write path is one of `harness/decision-log.md`, `diamonds/active.yml`. The orchestrator (or other downstream test driver) writes it; SKILL.md doesn't repeat it because the rule lives at framework scope. Applies to Rule 6 (test-driver drift) specifically; documented mid-Rule-6-FP-measurement 2026-06-02 (see `.claude/auto-dogfood/rule-6-fp-measurement-2026-06-02.md` in dogfood repo). |

Annotations are intentional friction: writers must explicitly mark divergences as legitimate. The mechanism's default is "flag every divergence."

## Promotion bar (spec → mechanism)

### Per-rule promotion (added 2026-06-02)

A single detection rule may graduate independently of the rest of the cluster when **all four** of the following hold for that rule:

1. **Implementation exists** as a concrete check (in `tests/validate-template.sh`, `.claude/scripts/`, or `plugins/mycelium/scripts/`).
2. **<5% false-positive rate** measured on the upstream corpus (engine/, skills/, harness/ as relevant to the rule's scope).
3. **Covers ≥1 known historical instance** from the cluster catalog.
4. **Hook integration** in place (pre-commit, CI, or session hook).

Per-rule promotion ships as a single Check (e.g., Check 39 for Rule 4) and a decision-log entry stating the rule, the FP rate measured, and the integration point. The cluster's overall status remains `spec` until the cluster-level bar (below) is met. This path exists because the cluster is heterogeneous — forcing all rules to ship together would gate easy mechanizable subclasses on hard research-shaped ones.

### Cluster-level promotion

The cluster graduates from `spec` to `guardrail` (REVIEW tier) when **all four** conditions are met:

1. **≥3 detection rules** from the candidate list above are implemented (per-rule promotion counts toward this).
2. **<5% false-positive rate** for each implemented rule, measured on the false-positive corpus.
3. **100% true-positive rate** across the cluster's known-instance fixtures (every historical instance is detected by at least one rule).
4. **Hook integration:** the checks are wired into either pre-commit (`validate-template.sh`), `/corrections-audit`, or a new dedicated hook. Detection without integration doesn't count.

Cluster-level promotion requires an explicit decision-log entry stating the rules implemented, the FP rate measured per rule, and the aggregate TP coverage across the historical instances.

### Current promotion state (as of 2026-06-02)

| Rule | Status | Implementation | FP rate | Hook integration |
|---|---|---|---|---|
| Rule 1 (Term-coverage) | spec | none | — | — |
| Rule 2 (Schema-discipline map) | spec | none | — | — |
| Rule 3 (Validator-claim cross-ref) | spec | none | — | — |
| Rule 4 (STRICT-marker presence) | **mechanism** | Check 39 in `tests/validate-template.sh` | 0/20 on upstream engine/ | run-all in `validate-template.sh` (pre-commit + CI) |
| Rule 5 (Hook-claim cross-ref) | **mechanism (narrowed core)** | Check 44 in `tests/validate-template.sh` (registered-script existence + cross-surface registration parity, divergence allowlist) | 0 FP on the 3-surface upstream corpus post-fix; TP proven on the pre-fix 2026-06-12 state (instance 12 fixture `tests/bash/fixtures/check_44/codex_drift`) | run-all in `validate-template.sh` (pre-commit + CI); G-V12 test `tests/bash/test_check_44.sh` |
| Rule 6 (Test-driver drift) | **promotion-bar-shape-mismatch** | `mycelium-roadmap/.claude/auto-dogfood/scripts/check_skill_prompt_drift.py` (260 LOC, framework-wide-procedural-writes escape valve honored 2026-06-02) | measured 2026-06-02: 21/28 task fns flagged after escape valve (75% raw); residual flags are dominantly conditional/scenario-dependent writes (test-scaffold simplification) by Phase-5 Option-C design — not drift | not integrated |

Cluster bar at 2/3 implemented rules (Rule 4 Check 39, 2026-06-02; Rule 5 narrowed-core Check 44, 2026-06-12). Honest scope note on Rule 5: Check 44 mechanizes the *registration* half (script existence + cross-surface parity); the fuzzy half (natural-language "hook X does Y" claims in docs traced to implementations) remains spec — promoting the narrowed core does not retire that residue. **Rule 6 promotion blocked on shape mismatch, not implementation.** FP measurement 2026-06-02 (see `mycelium-roadmap/.claude/auto-dogfood/rule-6-fp-measurement-2026-06-02.md`) surfaced that the cluster's `<5% FP rate` criterion was specified for validator-shaped rules (flag-and-fix). Rule 6 is a maintainer-review-surfacer (flag-and-decide) — its success criterion is "every flag has a maintainer decision logged" not "≤5% of corpus flagged." Two unblocking paths: (A) revise Rule 6's promotion bar to per-flag-decision-log shape; (B) graduate Rule 3 or Rule 5 first (more validator-shaped). Either advances cluster bar to 2/3; neither in scope for the session that surfaced this finding.

## What this spec does NOT do

- **Does not ship a check.** This is articulation; mechanism is deferred.
- **Does not require all five candidate rules.** Three is sufficient if they cover the cluster well; rules can be added post-promotion.
- **Does not auto-update.** Updates to this spec require explicit revision; that's the point — the framework's discipline about its own consistency-checking should be deliberate.

## Preemptive convention registry

Conventions that **currently hold by discipline alone** — not enforced by any mechanism. Named here so they have a discoverable identity before the first violation. Each entry sets the graduation trigger: the moment the convention diverges, it becomes a cluster instance and ships a check.

The registry's purpose is to close the silent-erosion path: an unnamed convention that holds is indistinguishable from no convention at all; when it eventually breaks, the failure looks like a new pattern rather than a known one. Naming it makes the eventual failure detectable as a recurrence, not a novelty.

| Convention | Currently true because | Graduation trigger | Candidate detection |
|---|---|---|---|
| **Skill-folder layout: one `SKILL.md` per directory, no helper scripts** | All 49 plugin-form skill dirs contain only `SKILL.md`; scripts live in sibling `plugins/mycelium/scripts/`. Audit confirmed clean 2026-05-11 (Supra Insider ep 110 Apurva-anecdote dogfood). | First skill dir gains a non-`SKILL.md` file. Either: skill legitimately ships assets (then frontmatter must declare them) OR convention violated (then ship the check). | Lint in `validate-template.sh`: `find plugins/mycelium/skills -type f ! -name SKILL.md ! -name README.md` → if non-empty, every result must appear in its parent skill's frontmatter under a declared `assets:` list. |
| **Capability promises ship with their mechanism or a `Gated by:` marker** (added 2026-06-12) | Going-forward convention from the 2026-06-12 gap analysis: every "skill X surfaces/does Y" sentence added to a SKILL.md or engine doc either cites the implementing step OR carries an explicit `Gated by:`/deferred marker. Pre-existing un-implemented promises are catalogued in the Promise registry below, not silently grandfathered. | A NEW capability claim lands without implementing artifact or gate marker (found by `/framework-health` 4f promise-registry sweep). | Fuzzy half of Rule 5 / Rule 3 — claim-extraction over "surfaces/reads/checks/enforces" verbs cross-referenced to skill steps; FP risk is why this is registry-tracked rather than check-shipped. |
| **New canvas files ship with a schema (or an explicit waiver)** (added 2026-06-12) | Going-forward convention: any canvas file newly taught in `canvas-guidance.yml` gets a `schemas/canvas/<stem>.schema.json` (permissive, house-style) in the same change. The pre-existing 11 schema-less files are a visible WARN backlog (`validate_canvas.py` names them every run), worked down opportunistically — tier-1 (purpose, north-star, gist, diamonds/active) closed v0.45.0. | The schema-less WARN count INCREASES between two `/framework-health` runs (4f schema-coverage trend) — a new file was taught without schema or waiver. | Mechanical: diff `canvas-guidance.yml` taught-file list against `schemas/canvas/*.schema.json` stems; candidate Check once the backlog reaches 0 (flag any taught file without schema). |
| **Every theory a skill/gate cites is mechanism-mapped in `theories.md`** (added 2026-06-18) | Going-forward convention from the theory-fidelity audit: a skill `## Theory Citations` / `Source:` author or a `theory-gates.md` gate `**Source**:` either appears as a row in `docs/theories.md` (Tier 1/2 mechanism-mapped, or Tier 3 citation-only by intent) or is a tracked Promise-registry row. The structural half (refs resolve, gates grounded, no name-only theory) is enforced now by `check_theory_fidelity.py`; the semantic half (faithful vs distorted) is the `/theory-fidelity` skill on cadence. | A new `Source:`/citation author lands with no `theories.md` mapping — found by `/framework-health` 4g (theory surface changed → run `/theory-fidelity`) or 4f promise-registry sweep. Becomes a Promise-registry row until mapped. | Structural subset shipped (`check_theory_fidelity.py`, validate.yml + pre-push). Semantic subset is irreducibly LLM + source-grounding — registry-tracked, not check-shipped. |

Add a row when: (a) a convention is named in conversation or in a memory entry but lacks a mechanism, (b) the convention is currently holding without violation, (c) the cost of writing the check is higher than the cost of the current violation rate (zero).

**Promotion path for a preemptive-registry entry**: when the graduation trigger fires, the entry moves into the main Cluster catalog above (becomes instance N) and a detection rule is added to the candidate list. The check ships per the Promotion bar.

## Promise registry (capability claims awaiting mechanism)

Known places where framework prose claims a surface does something that nothing implements yet. The preemptive convention registry covers conventions that *currently hold*; this registry covers claims that currently *don't* — each is either implemented (row closes, citing the version), explicitly re-marked as `Gated by:` in its source doc, or removed from the doc. Swept by `/framework-health` 4f each run. Source: 2026-06-12 gap analysis (4 instances found; 1 implemented same-session).

| # | Claim | Where documented | Status | Close condition |
|---|---|---|---|---|
| P1 | `/feedback-review` + `/diamond-assess` surface parked diamonds with resume conditions | `diamond-progress/SKILL.md` § Park | **CLOSED v0.45.0** — implemented as diamond-assess 2b + feedback-review 2b | — |
| P2 | WIP limits are enforced (hard ceiling per scale) | `engine/diamond-rules.md` § WIP Limits | **CLOSED v0.47.0** — re-worded to advisory; `Gated by:` a spawn-time count-and-block gate, marked not-yet-built | — |
| P3 | `/ice-score` checks corrections.md for DORA calibration data before scoring ease | `engine/feedback-loops.md` § DORA → Feasibility | **CLOSED v0.47.0** — re-worded: reverse loop marked aspirational + manual; `Gated by:` an ice-score grep step, not-yet-built | — |
| P4 | Canvas-sync conflict resolution: "the person with more evidence wins" | `canvas-sync/SKILL.md` § Conflict Resolution | **CLOSED v0.47.0** — re-worded as a manual-resolution heuristic; `Gated by:` a `/canvas-merge` procedure, not-yet-built | — |

Adding a row requires only: the claim, its source location, and a concrete close condition with both an implement-path and an honest re-word-path (a promise can legitimately close by the doc stopping to promise). A row OPEN across 3 consecutive `/framework-health` runs escalates to the cluster catalog as a documented-rule-diverges-from-enforcement instance.

## Audit and maintenance

- **`/corrections-audit`** reads this file (post-promotion to spec-graduated, 2026-05-08). When the audit detects a candidate cluster instance, it cross-references this spec's catalog AND the preemptive convention registry; an instance matching a registered convention promotes that registry row rather than creating a novel cluster entry.
- **`/framework-health`** checks the promotion bar quarterly. When ≥3 candidate rules have been drafted, framework-health surfaces graduation as a candidate next-step. Also: surfaces any preemptive-registry conventions whose graduation triggers have fired since last audit.
- **Direct edits to this file** require a corrections.md entry and a decision-log entry — the spec is a load-bearing artifact, not a scratchpad. Preemptive-registry rows are an exception: adding a row that names a currently-true convention is single-line bookkeeping and does not require corrections.md.

## Theory grounding

- **Senge** (Fifth Discipline): structural thinking — when patterns recur, the lever is structural, not behavioral. This spec is the structural articulation.
- **Argyris** (double-loop learning): single-loop = fix the instance; double-loop = fix the rule that allowed the instance. Triple-loop = fix the rule that prevented seeing the rule. The cluster log is double-loop; this spec is triple-loop (we're now reasoning about what kind of rule we'd need).
- **Lopopolo** ("every interaction is a failure of the harness to provide enough context"): un-detected divergences are accumulated harness-context-debt. This spec scopes the debt.
- **Mycelium's own discipline:** L1 → L2 → L3 → L4. The mechanism (L4) without an L3 (this spec) is exactly the process cliff the framework warns against. Building the mechanism without the spec would be skipping scales.
- **Postel's Law / Robustness Principle** ("be conservative in what you do, be liberal in what you accept from others" — RFC 793, Postel 1981). When a schema teaches `additionalProperties: false` strictness AND the rest of the framework conventions point at a field name the strict schema rejects, the schema is being more conservative in what it accepts than the framework is in what it teaches. The 0.16.2 fix accepting both `source_class` (singular) and `source_classes` (plural) inside provenance was Postel's Law applied: the strict mode preserves typo-detection (conservative on what it ships out — error messages) while accepting both natural-feeling forms (liberal on what it accepts in). Future `additionalProperties: false` decisions should pre-check whether the rejected field is a typo OR a natural extension of framework convention; if the latter, accept it. This is the schema-vs-discipline-vocabulary subclass's structural cure.
