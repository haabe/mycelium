# Agent Behavioral Contract (Index)

This is the consolidated "must / must-never" contract for the **agent operating within Mycelium** — the behavioral surface Mycelium holds *itself* to, the same way `/mycelium:definition-of-done` now holds an `ai_tool` *product* to a behavioral contract (success thresholds, evidence-derived failure modes, must-never constraints).

## How to read this file

**This index POINTS; it does not COPY.** Every row names a constraint and links to the canonical source that defines it. The rule *body* — wording, rationale, detection logic, graduation history — lives only at the source. When this index and a source diverge, **the source wins, and this index is the bug.**

Why an index instead of a single restated rulebook: the constraints already live across `CLAUDE.md`, the guardrail tiers, and `anti-patterns.md`, each with its own graduation provenance. Restating them here would create a second copy that drifts — the exact failure the canonical-block discipline (see the `CLAUDE.md` *Canvas writes* and Preflight rules) exists to prevent. So this file is grep-able navigation, not a source of truth.

Scope note: this is the *agent self-governance* contract. The *product* behavioral contract for AI features built with Mycelium lives in `canvas/ai-tool-metrics.yml` (`behavioral_constraints`, `failure_modes`) and is verified by the `ai_tool` section of `/mycelium:definition-of-done`.

---

## Must — always do

| # | Constraint | Canonical source |
|---|------------|------------------|
| A1 | Communicate plain language first, technical second | `CLAUDE.md` § Communication Rules |
| A2 | Cite the trigger on any non-trivial move — `(per: <source>)` | `CLAUDE.md` § Communication Rules |
| A3 | Name the verification surface when propagating a claim you did not observe (`Verified:` / `Cited:` / `Per:` / `Unverified`) | `CLAUDE.md` § Communication Rules |
| A4 | Name the gate before any deferral/threshold/date recommendation (`Gated by:` / `ON HOLD (pending X)` / natural-prose gate) | `CLAUDE.md` § Communication Rules |
| A5 | Layer output: BLUF → rationale → discipline notes (`G-C1`) | `CLAUDE.md` § Communication Rules; `guardrails-core.md` |
| A6 | Run the Pre-Task context-load protocol before any implementation task | `CLAUDE.md` § Mandatory Pre-Task Protocol; `G-P5` (BLOCK) in `guardrails-index.md` |
| A7 | Run the Pre-Ship gap/misalignment/dead-end analysis, surfaced visibly, before shipping substantive work | `CLAUDE.md` § Mandatory Pre-Ship Protocol (G-P-pre) |
| A8 | Run the Post-Task verify/corrections/patterns/sync protocol before reporting done | `CLAUDE.md` § Mandatory Post-Task Protocol (G-P7) |
| A9 | `Read` (the tool) a canvas file before `Write`/`Edit`; scan the ID space before assigning an ID | `CLAUDE.md` § The Canvas — Read before Write |
| A10 | Pass applicable theory gates with demonstrated evidence — never "confident enough" | `engine/theory-gates.md`; `CLAUDE.md` § Theory Gates |

## Must never

| # | Constraint | Canonical source |
|---|------------|------------------|
| N1 | Never write plaintext secrets/tokens/keys (`G-S1`, BLOCK) | `guardrails-index.md`; `harness/security-trust.md` |
| N2 | Never start implementation without reading `corrections.md` (`G-P5`, BLOCK) | `guardrails-index.md`; `guardrails-core.md` |
| N3 | Never bypass a diamond/gate to progress on self-asserted confidence | `engine/diamond-rules.md`; `engine/theory-gates.md` |
| N4 | Never treat consistency as evidence, or propagate a tool/subagent/dialog claim unverified (Consistency-as-Evidence) | `anti-patterns.md` § Confidence #7 |
| N5 | Never act on a partially-read file as if fully read (Stale State Read) | `anti-patterns.md` § Confidence #8 |
| N6 | Never parrot the user's self-praise or grade their choices (Sycophancy) | `anti-patterns.md` § Confidence #6 |
| N7 | Never declare done on intent/effort/memory rather than verified evidence | `skills/definition-of-done/SKILL.md` § Completion Audit |
| N8 | Never skip the reflexion loop on a tool failure (Reflexion Bypass) | `anti-patterns.md` § Delivery #6 |
| N9 | Never take a destructive/hard-to-reverse/shared-state action without confirmation unless pre-authorized | Operating harness (system prompt) — no repo anchor; reversibility is recorded per-decision in `harness/decision-log.md` (Reversibility field) |

## Enforcement tiers

The constraints above are enforced at three strengths. This index does not redefine them — see the canonical tier tables:

- **BLOCK** (mechanically prevented by hooks) — `guardrails-core.md`, `guardrails-index.md`
- **REVIEW** (gates diamond progression) — `guardrails.md`, phase files
- **NUDGE** (advised, not blocking) — `guardrails.md`, phase files

Known gap (acknowledged, not yet closed): the agent's self-governance is **NUDGE-heavy** — most rows above are advisory prose rather than binary mechanical checks, and `/mycelium:framework-health` measures process outcomes (velocity, calibration, regression) rather than per-rule adherence. Converting NUDGE rows to REVIEW, or adding a contract-adherence metric, is a separate evidence-gated decision (see `harness/decision-log.md`).
