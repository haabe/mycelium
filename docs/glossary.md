# Glossary

**Audience**: anyone — designers, PMs, junior devs, evaluators — who hits a Mycelium-specific term and wants the 2-sentence answer.
**Time to read**: 5 min.
**Last updated**: 2026-10-01.

Two-to-four sentences per entry. No theory teaching here — entries link out to canonical sources for depth ([theories.md](theories.md), original authors).

## Mycelium concepts

**Anti-pattern** — A known failure mode the framework has seen and documents in `../plugins/mycelium/harness/anti-patterns.md`. Detection rules let the agent flag the shape early. See `../plugins/mycelium/harness/anti-patterns.md` for the catalog.

**Build to learn vs build to earn** — Patton/Cagan distinction. Discovery work is built to learn (the artifact may be discarded once the learning lands); delivery work is built to earn (it has to ship and run). In Mycelium these are the two modes, read off a diamond's decisions: discovery until it records `commit_to_build`, delivery after (see **Mode**). See [theories.md#build-to-learn-vs-earn](theories.md).

**Canvas** — The collection of YAML files in `.claude/canvas/` that hold all product knowledge. The canvas IS the spec — the prototype-IS-the-spec discipline (Cagan) applied to product knowledge, not just code. Each canvas file is committed to git as documentation-as-code.

**Cognitive forcing** — Buçinca, Malaya, Gajos. A design technique that makes the human judge first, then shows the AI's answer — reduces automation bias. Mycelium applies it before a decision is recorded (the user gives their own judgement before seeing the gate verdict).

**Correction** — A learning entry written to `.claude/memory/corrections.md` after the agent makes a mistake. Corrections inform the next session's pre-task protocol. Recurring corrections (≥3 instances of the same root cause) graduate to a guardrail or anti-pattern.

**Cluster** — A group of corrections that share a root-cause shape. Tracked in `.claude/memory/cluster-instances.md`. When a cluster crosses a graduation criterion (typically ≥6 instances or specific spec evidence), it gets promoted to a mechanism (guardrail, anti-pattern, validator check, or a spec for a future check).

**Counter-argument check** — A bias-mitigation step the agent runs before strong claims. Forces it to articulate the strongest case against its own current position. Implemented in `/devils-advocate`.

**Decision** — What a diamond records to move: `set_target`, `start_experiment`, `commit_to_build` (recorded with `start_experiment` the first time), `release`, `close`; an L0 records `state_purpose` and later `review`. Each entry carries its date, the gates it passed and the ruling. Decisions are only ever added: a loop iterates by appending (another `start_experiment` for a new test), and since v0.309.1 a write that removes or rewrites a recorded decision is refused.

**Diamond** — One learning loop at one scale. Every scale below purpose (L1–L5) runs the same loop of five **decisions**, each of which must pass its theory gates; L0 Purpose is not a loop (it states its purpose and reviews it). Defined in `plugins/mycelium/engine/diamond-rules.md`.

**Dogfood** — Using a tool on its own development. Mycelium's framework is dogfooded on Mycelium itself — the friction the founder hits while building Mycelium becomes corrections that shape Mycelium. The `meta_dogfood` project type formalizes this. See [philosophy.md](philosophy.md) for why it's required.

**Exposure record** — An entry in a diamond's `exposures`: who a delivery reaches (audience, channel, data class, until when, how consent was given) and the gates passed for them. Nothing built may meet real people without one covering it; the release gate checks it.

**Escape hatch** — A sanctioned bypass for emergencies. Documented in `plugins/mycelium/orchestration/escape-hatch.md`. The bypass must be paired with a debt entry — every escape hatch use gets paid back.

**Gate / theory gate** — An evidence check that must pass before a diamond records a decision. Each gate is grounded in a specific framework (Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, Outcomes/BVSSH, Service Quality, Delivery Health, Learning, Regulatory, Explainability). Defined in `plugins/mycelium/engine/theory-gates.md`.

**GIST** — Goals, Ideas, Steps, Tasks (Gilad). The prioritization model used at L3 Solution scale. Steps are the testable unit; tasks are the executable unit. See [theories.md#gist](theories.md).

**Guardrail** — A constraint enforced at one of three tiers: BLOCK (mechanically prevented), REVIEW (gates progression at a checkpoint), or NUDGE (surfaced but not blocking). Defined in `../plugins/mycelium/harness/guardrails.md`. Three-tier vocabulary follows Birgitta Böckeler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html).

**Harness** — The set of mechanisms that constrain agent behavior: hooks, guardrails, gates, validators, pre/post-task protocols. The harness is what makes the framework's claims load-bearing rather than aspirational.

**ICE score** — the average of Impact, Confidence and Ease (Ellis, adopted by Gilad within GIST). Ellis averages the three ratings; Mycelium multiplied them until v0.229.0 (`errata.md` §A). Used to prioritize ideas at L3. Confidence must be evidence-backed. See [theories.md#ice](theories.md).

**In-loop preventive** — Mycelium's strategic positioning: gates fire DURING the agent's loop to block progression on insufficient evidence; they do not score outputs after the fact. Distinct from post-run evaluative tools (like Anthropic Outcomes).

**JIT tooling** — Just-in-time tooling. Mycelium does not pre-ship a per-language or per-product-type catalog of validation; it detects what's there and generates adapters. See [jit-tooling.md](jit-tooling.md).

**Leaf (OST leaf)** — A single solution node in the Opportunity Solution Tree. Every leaf moves through a 10-step lifecycle (creation → four risks → ICE → assumption test → GIST → bounded context → threat model → preflight → delivery diamond → launch + feedback). See `plugins/mycelium/engine/leaf-lifecycle.md`.

**Leaf bakeoff** — A protocol for parallel A/B testing of competing leaves. When multiple leaves compete for the same opportunity, the bakeoff structure compares them. See `plugins/mycelium/orchestration/leaf-bakeoff.md`.

**Mode** — Discovery or delivery, read off a diamond's decisions: discovery until it records `commit_to_build`, delivery after. The two run in parallel across a project (one diamond can be in discovery while another delivers). The mode is never declared, only read.

**Opportunity Solution Tree (OST)** — Torres's discovery framework. Multiple opportunities are found, multiple solutions are generated for each, solutions compete, the winner spawns an L3 Solution diamond. Loser leaves are archived with evidence, not deleted. See [theories.md#ost](theories.md).

**Phase** — Until v0.306.0, one of Discover / Define / Develop / Deliver within a diamond. Retired: where a diamond is, is now read from its decisions (see **Position** and **Mode**). Some internal names keep the old word.

**Position** — Where a diamond is, said by what it has decided: no decision yet, target set, committed to build, released, closed. An L0 has stated its purpose or not yet.

**Pre-task protocol** — The mandatory context-loading sequence the agent must perform before any implementation task. Defined in CLAUDE.md.

**Pre-ship protocol (G-P-pre)** — The mandatory pre-commit gap analysis the agent must surface visibly before substantive work ships. Defined in CLAUDE.md.

**Process cliff** — The point in a session where Mycelium's structure starts feeling heavier than the value it adds. The Hoskins take-home surfaced this at the 75% mark. Lightweight discovery-to-delivery continuation mode is the ongoing fix.

**Purpose stance** — A short verdict on whether a solution contradicts your own why, how or what, checked against the binding properties derived from them. If your *what* is "anonymous users post short strings of emoji", a solution that requires login contradicts it. See [purpose stance](purpose-stance.md).

**Reflexion** — A self-correcting loop: implement → validate → self-critique → retry (max 3 iterations). Reflexion pattern: Shinn et al. (2023). Implemented as `/reflexion` and as a PostToolUseFailure hook.

**Scale** — One of L0 Purpose / L1 Strategy / L2 Opportunity / L3 Solution / L4 Delivery / L5 Market. Scales answer "what am I deciding?". Each scale opens under the one above it (since v0.247.0), so none is skipped; on a small project the upper ones can be a few lines.

**Scenario** — A user-context primitive (Motivation + Persona + Simulation, Hoskins, *The Product-Minded Engineer* ch. 1). Born at L2, designed against at L3, tested at L4, validated at L5. Lives in `canvas/scenarios.yml`. See [theories.md#scenarios](theories.md).

## Theory framework names

**APEX** — Agent Productivity Engineering Experience. Used alongside DORA for agent-runtime-target products. Tracked in `canvas/ai-tool-metrics.yml`.

**BVSSH** — Better Value Sooner Safer Happier (Smart). Holistic outcome check when a diamond records `close`, at every scale. See [theories.md#bvssh](theories.md).

**Cagan four risks** — Value, Usability, Feasibility, Viability. Required before `commit_to_build` and `release`, at L1–L4. See [theories.md#cagan](theories.md).

**Cynefin** — Snowden's domain classification (Clear, Complicated, Complex, Chaotic, Confused). Determines which methods apply. See [theories.md#cynefin](theories.md).

**DORA** — Forsgren/Humble/Kim. Four core delivery metrics (deployment frequency, lead time, change failure rate, FDRT — formerly MTTR). **Reliability** is a 2021 *operational-performance* dimension, not a fifth delivery metric. Checked at `close`, L3–L4. See [theories.md#dora](theories.md).

**JTBD** — Jobs to be Done (Christensen, Ulwick). Functional, emotional, social dimensions. Checked at `set_target` and `commit_to_build`, L1–L3. See [theories.md#jtbd](theories.md).

**OWASP / STRIDE** — Security frameworks. STRIDE for threat modeling; OWASP Top 10:2025 for the secure-design checklist. Required before `release` and at `close`, L3–L5. See [theories.md#owasp](theories.md).

**Wardley** — Strategic landscape mapping with evolution stages. L1. See [theories.md#wardley](theories.md).

## See also

- [theories.md](theories.md) — full mechanism-mapped theory list
- [philosophy.md](philosophy.md) — why these concepts are load-bearing rather than decorative
