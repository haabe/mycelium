# Glossary

**Audience**: anyone — designers, PMs, junior devs, evaluators — who hits a Mycelium-specific term and wants the 2-sentence answer.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

Two-to-four sentences per entry. No theory teaching here — entries link out to canonical sources for depth ([theories.md](theories.md), original authors).

## Mycelium concepts

**Anti-pattern** — A known failure mode the framework has seen and documents in `.claude/harness/anti-patterns.md`. Detection rules let the agent flag the shape early. See `.claude/harness/anti-patterns.md` for the catalog.

**Build to learn vs build to earn** — Patton/Cagan distinction. Discovery work is built to learn (the artifact may be discarded once the learning lands); delivery work is built to earn (it has to ship and run). Mycelium gates which mode applies before the agent commits scope. See [theories.md#build-to-learn-vs-earn](theories.md).

**Canvas** — The collection of YAML files in `.claude/canvas/` that hold all product knowledge. The canvas IS the spec — the prototype-IS-the-spec discipline (Cagan) applied to product knowledge, not just code. Each canvas file is committed to git as documentation-as-code.

**Cognitive forcing** — Buçinca, Malaya, Gajos. A design technique that makes the human judge first, then shows the AI's answer — reduces automation bias. Mycelium applies it at diamond transitions (the user must articulate evidence before seeing the gate verdict).

**Correction** — A learning entry written to `.claude/memory/corrections.md` after the agent makes a mistake. Corrections inform the next session's pre-task protocol. Recurring corrections (≥3 instances of the same root cause) graduate to a guardrail or anti-pattern.

**Cluster** — A group of corrections that share a root-cause shape. Tracked in `.claude/memory/cluster-instances.md`. When a cluster crosses a graduation criterion (typically ≥6 instances or specific spec evidence), it gets promoted to a mechanism (guardrail, anti-pattern, validator check, or a spec for a future check).

**Counter-argument check** — A bias-mitigation step the agent runs before strong claims. Forces it to articulate the strongest case against its own current position. Implemented in `/devils-advocate`.

**Diamond** — A four-phase Discover → Define → Develop → Deliver cycle. Every scale (L0–L5) runs the same diamond. Transitions between phases must pass theory gates. Defined in `.claude/engine/diamond-rules.md`.

**Dogfood** — Using a tool on its own development. Mycelium's framework is dogfooded on Mycelium itself — the friction the founder hits while building Mycelium becomes corrections that shape Mycelium. The `meta_dogfood` project type formalizes this. See [philosophy.md](philosophy.md) for why it's required.

**Escape hatch** — A sanctioned bypass for emergencies. Documented in `.claude/orchestration/escape-hatch.md`. The bypass must be paired with a debt entry — every escape hatch use gets paid back.

**Gate / theory gate** — An evidence check that must pass before a diamond transitions phase. Each gate is grounded in a specific framework (Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, Outcomes/BVSSH, Service Quality, Delivery Health, Learning, Regulatory, Explainability). Defined in `.claude/engine/theory-gates.md`.

**GIST** — Goals, Ideas, Steps, Tasks (Gilad). The prioritization model used at L3 Solution scale. Steps are the testable unit; tasks are the executable unit. See [theories.md#gist](theories.md).

**Guardrail** — A constraint enforced at one of three tiers: BLOCK (mechanically prevented), REVIEW (gates progression at a checkpoint), or NUDGE (surfaced but not blocking). Defined in `.claude/harness/guardrails.md`. Three-tier vocabulary follows Birgitta Böckeler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html).

**Harness** — The set of mechanisms that constrain agent behavior: hooks, guardrails, gates, validators, pre/post-task protocols. The harness is what makes the framework's claims load-bearing rather than aspirational.

**ICE score** — Impact × Confidence × Ease (Ellis, adopted by Gilad within GIST). Used to prioritize ideas at L3. Confidence must be evidence-backed. See [theories.md#ice](theories.md).

**In-loop preventive** — Mycelium's strategic positioning: gates fire DURING the agent's loop to block progression on insufficient evidence; they do not score outputs after the fact. Distinct from post-run evaluative tools (like Anthropic Outcomes).

**JIT tooling** — Just-in-time tooling. Mycelium does not pre-ship a per-language or per-product-type catalog of validation; it detects what's there and generates adapters. See [jit-tooling.md](jit-tooling.md).

**Leaf (OST leaf)** — A single solution node in the Opportunity Solution Tree. Every leaf moves through a 10-phase lifecycle (creation → four risks → ICE → assumption test → GIST → bounded context → threat model → preflight → delivery diamond → launch + feedback). See `.claude/engine/leaf-lifecycle.md`.

**Leaf bakeoff** — A protocol for parallel A/B testing of competing leaves. When multiple leaves compete for the same opportunity, the bakeoff structure compares them. See `.claude/orchestration/leaf-bakeoff.md`.

**Opportunity Solution Tree (OST)** — Torres's discovery framework. Multiple opportunities are found, multiple solutions are generated for each, solutions compete, the winner spawns an L3 Solution diamond. Loser leaves are archived with evidence, not deleted. See [theories.md#ost](theories.md).

**Phase** — One of Discover / Define / Develop / Deliver within a diamond. Each phase has a divergent or convergent character; transitions require gates.

**Pre-task protocol** — The mandatory context-loading sequence the agent must perform before any implementation task. Defined in CLAUDE.md.

**Pre-ship protocol (G-P-pre)** — The mandatory pre-commit gap analysis the agent must surface visibly before substantive work ships. Defined in CLAUDE.md.

**Process cliff** — The point in a session where Mycelium's structure starts feeling heavier than the value it adds. The Hoskins take-home surfaced this at the 75% mark. Lightweight discovery-to-delivery continuation mode is the ongoing fix.

**Reflexion** — A self-correcting loop: implement → validate → self-critique → retry (max 3 iterations). Lopopolo / academic origin. Implemented as `/reflexion` and as a PostToolUseFailure hook.

**Scale** — One of L0 Purpose / L1 Strategy / L2 Opportunity / L3 Solution / L4 Delivery / L5 Market. Scales answer "what am I deciding?". Not all scales are required for every project.

**Scenario** — A user-context primitive (Persona + Means + Motive + Simulation, Hoskins). Born at L2, designed against at L3, tested at L4, validated at L5. Lives in `canvas/scenarios.yml`. See [theories.md#scenarios](theories.md).

## Theory framework names

**APEX** — Agent Productivity Engineering Experience. Used alongside DORA for agent-runtime-target products. Tracked in `canvas/ai-tool-metrics.yml`.

**BVSSH** — Better Value Sooner Safer Happier (Smart). Holistic outcome measurement at L4. See [theories.md#bvssh](theories.md).

**Cagan four risks** — Value, Usability, Feasibility, Viability. Required check before a leaf advances out of L3. See [theories.md#cagan](theories.md).

**Cynefin** — Snowden's domain classification (Clear, Complicated, Complex, Chaotic, Confused). Determines which methods apply. See [theories.md#cynefin](theories.md).

**DORA** — Forsgren/Humble/Kim. Five delivery metrics (deployment frequency, lead time, change failure rate, FDRT, reliability). L4 only. See [theories.md#dora](theories.md).

**JTBD** — Jobs to be Done (Christensen, Ulwick). Functional, emotional, social dimensions. L0/L2. See [theories.md#jtbd](theories.md).

**OWASP / STRIDE** — Security frameworks. STRIDE for threat modeling; OWASP Top 10:2025 for the secure-design checklist. L4 only. See [theories.md#owasp](theories.md).

**Wardley** — Strategic landscape mapping with evolution stages. L1. See [theories.md#wardley](theories.md).

## See also

- [theories.md](theories.md) — full mechanism-mapped theory list
- [philosophy.md](philosophy.md) — why these concepts are load-bearing rather than decorative
