# Theories integrated

**Audience**: practitioner peers (PMs, senior engineers, designers, researchers) who want to know which frameworks Mycelium uses and how each one is wired in.
**Time to read**: 15 min for full read; 2 min if you only want the table.
**Last updated**: 2026-06-18.

The differentiator vs other framework lists: every theory is **mechanism-mapped** — the column "Implemented as" answers "which Mycelium artifact actually applies this?" Citations without mechanism-mapping are theatre.

## Tier 1 — Load-bearing theories

These shape Mycelium's structure. Removing one collapses a load-bearing wall.

### Sinek — Golden Circle (Why / How / What)

The L0 Purpose canvas (`canvas/purpose.yml`) follows the Why → How → What ordering Sinek argues for, and `/interview` elicits purpose first. Honest scope: the L0→L1 transition is governed by the generic **Evidence gate**, not a `why`-specific population-and-evidence check, and the schema treats `why` as optional — so "start with Why" is modeled in canvas structure and interview ordering, not hard-gated. Implemented as: `canvas/purpose.yml`, `/interview` first phase, gate 1 (Evidence) at L0→L1.

### Christensen — Jobs to be Done

JTBD with the Christensen tripartite (functional, emotional, social). Each canvas entry can carry per-dimension evidence after the v0.17.0 schema fix (`validation_status_per_dimension`). Implemented as: `canvas/jobs-to-be-done.yml`, `/jtbd-map` skill, gate 3 (JTBD) at L2→L3.

### Torres — Continuous Discovery / Opportunity Solution Tree

The OST is the bridge from L2 Opportunity to L3 Solution: opportunities are decomposed into solutions, solutions are compared via **assumption tests** (Torres's method — she explicitly cautions *against* scoring frameworks like ICE for solution selection), the winner spawns L3, loser leaves are archived with evidence. ICE [Ellis] is a secondary prioritization aid derived from the Four Risks, not the Torres selection mechanism. Torres's interviewing structure also informs `/user-interview`. Implemented as: `canvas/opportunities.yml`, `/ost-builder`, `/user-interview`, leaf-lifecycle.md.

### Cagan — Inspired / Empowered (four risks)

Value, Usability, Feasibility, Viability. Every leaf must show evidence on each before advancing out of L3. Mycelium's "canvas IS the spec" is an *analogical extension* of Cagan's "prototype IS the spec" (his claim is about high-fidelity discovery prototypes, not a YAML canvas — plausible, but Mycelium's framing, not a verbatim Cagan mechanism). Implemented as: gate 2 (Four Risks), `/assumption-test`, leaf-lifecycle.md phase 2.

### Wardley — Mapping

Strategic landscape with evolution stages (Genesis → Custom → Product → Commodity). Mycelium's L1 strategic_frame articulates "where Mycelium plays" using Wardley's vocabulary. Implemented as: `canvas/landscape.yml`, `/wardley-map`, and a **NUDGE at Develop→Deliver + a suggested L1 Engineering-trio skill** (there is no hard Wardley gate at L1→L2 — the skill and canvas carry the discipline).

### Cynefin (Snowden) — Domain classification

Clear / Complicated / Complex / Chaotic / Confused. Determines which methods apply (best-practice vs good-practice vs probe-sense-respond). Mycelium uses Cynefin to scale the discovery rigor: complex domains get more diamond depth, clear domains skip scales. Implemented as: `/cynefin-classify`, gate 4 (Domain Fit) at L2 transitions.

### Forsgren / Humble / Kim — DORA

Four core delivery metrics (deployment frequency, lead time, change failure rate, FDRT — formerly MTTR). **Reliability** is a *2021* operational-performance dimension (dora.dev classifies it as operational, not software-delivery), assessed via SRE/SLOs in `/dora-check` Part 3 — not a fifth delivery metric. (The 2024 report's additional delivery metric was *deployment rework rate*, which Mycelium does not separately track.) L4 only. Adapted for non-software product types (content, AI tool, service) into APEX-shaped variants — **rationale**: DORA's deployment-centric metrics don't map onto content/AI/service delivery, so product-type-appropriate cadence/quality/recovery proxies stand in. Implemented as: `canvas/dora-metrics.yml` (the 4 core), `/dora-check`, gate 10 (Delivery Health) at L4→complete.

### Hoskins — Scenarios as connective tissue

**Motivation + Persona + Simulation** (Hoskins's three elements). Born at L2 from interview stories, designed against at L3, tested at L4, validated at L5. Primary source: Hoskins, *The Product-Minded Engineer* (O'Reilly), ch. 1 — the scenario as the core primitive of product thinking. (**Corrected 2026-07-01:** an earlier in-repo model claimed FOUR elements — Persona/Means/Motive/Simulation — but **"Means" is not a Hoskins element** (a distortion); and the cited "SAP talk 'Attention to Users Is All You Need'" was **fabricated**. Both removed; "how they interact with tools" lives inside the Simulation.) Implemented as: `canvas/scenarios.yml`, scenario extraction in `/user-interview`, scenario wiring through leaf-lifecycle phases 1, 5, 8, 10.

## Tier 2 — Integrated theories

Each one shapes a specific surface; removable in isolation, but the surface goes with it.

| Theory | Author(s) | Implemented as |
|---|---|---|
| User Needs Mapping | Allen | `canvas/user-needs.yml`, `/user-needs-map` (needs independent of solutions, feeds OST) |
| GIST Planning | Gilad | `canvas/gist.yml`, `/gist-plan` (L3 prioritization) |
| ICE Scoring | Ellis (adopted by Gilad) | `/ice-score` (evidence-backed confidence; calibration via `cycle-history.yml`) |
| North Star Framework | Ellis | `canvas/north-star.yml` (key metric + input metrics) |
| Team Topologies | Skelton, Pais | `/team-shape` skill (cognitive load, interaction modes) — **advisory-only until multi-team adoption**: `canvas/team-shape.yml` has no schema and nothing else in the system consumes it yet (see philosophy.md "What Mycelium does not yet do") |
| Good Services | Downe | `canvas/services.yml`, `/service-check` (15 service principles) |
| OWASP Top 10:2025 / STRIDE | OWASP, Shostack | `canvas/threat-model.yml`, `/threat-model`, `/security-review` (gate 6) |
| Privacy by Design | Cavoukian | `canvas/privacy-assessment.yml`, `/privacy-check` (gate 7) |
| Loved | Lauchengco | `canvas/go-to-market.yml`, `/launch-tier` (L5) |
| BVSSH | Smart | `canvas/bvssh-health.yml`, `/bvssh-check` (gate 8 Outcomes) |
| Build to Learn vs Build to Earn | Patton, Cagan | Discovery diamonds = build-to-learn; delivery diamonds = build-to-earn. Rationale in `philosophy.md`; enforced via G-M2 + define-done/DoD guardrails |
| Cognitive Forcing Functions | Buçinca, Malaya, Gajos | `/diamond-assess` step 0 + `/diamond-progress` — human articulates unprimed judgment before the agent shows gate verdicts |
| Theory of Constraints | Goldratt | `value-stream.yml`, bottleneck identification at L4 |
| Three Ways / Five Ideals | Kim | Three Ways map the four feedback-loop speeds (`engine/feedback-loops.md`); Five Ideals = L4 prose checklist in `domains/delivery/CLAUDE.md` (principle-text, not a gate) |
| The Fifth Discipline | Senge | System archetypes (Fixes That Fail / Shifting the Burden / Limits to Growth / Eroding Goals) in `harness/anti-patterns.md` (#12–15), checked at L1/L2 in `/diamond-assess` step 5; `cluster-instances.md` is the recurrence-to-structure ledger |
| Double-loop learning | Argyris | The named ground for the fractal double-loop architecture (philosophy.md) and the corrections→cluster→mechanism graduation cycle; sourced in guardrail G-P7 (`guardrails-core.md`) |
| Domain-Driven Design | Evans | `canvas/bounded-contexts.yml` (L3→L4 boundary) |
| Lean UX | Gothelf, Seiden | Hypothesis-driven design feeds `/assumption-test` |
| Toyota Kata | Rother | Coaching-question shape in `/diamond-assess` |
| Architecture Decision Records | Nygard | `decision-log.md` shape (with contrastive `why_not_alternatives`, Liao et al. extension) |

## Tier 3 — Background theories (citation-only)

These show up as citations and inform the framework's ethics or peripheral mechanisms; they do not shape primary structure. Listed as `... and more` below — the table format is reserved for tier 1 + tier 2 (the load-bearing surface).

- **Behavioral Science** (Shotton, Kahneman) — bias mitigation in `/bias-check`, ethical design constraints
- **Amabile** (creativity research) — *Brilliant but Cruel* (1983) grounds the Negativity-as-Competence bias item in `/bias-check` (harsh critique reads as competence, so adversarial-review findings get weighed on cited evidence, not severity); componential theory backs the separable-process bet named in [philosophy.md](philosophy.md)
- **CALMS** (Willis, Humble) — DevOps culture vocabulary in `/bvssh-check` + `domains/delivery/CLAUDE.md` (corrected 2026-07-01: previously said "retrospectives", where it does not appear)
- **Hooked / Indistractable** (Eyal) — ethical engagement design (anti-dark-pattern check)
- **Clean Architecture / SOLID** (Martin) — engineering-principles.md NUDGE tier
- **SRE** (Beyer, Jones, Petoff, Murphy) — error budgets, toil, SLIs/SLOs vocabulary
- **TPS / Lean** (Ohno, Toyoda) — 7 Wastes (TIMWOOD) checklist in `domains/delivery/CLAUDE.md` + `/retrospective` (corrected 2026-07-01: previously said `value-stream.yml`, which carries Goldratt's Theory of Constraints)
- **Norman** (visible affordances) — UX surface for footgun-to-affordance graduations (`diamond-progress` prompt template; corrected 2026-07-01: the "wayfinding strict marker" example carried no Norman attribution in-repo and was removed)
- **Liao et al. (2020)** — contrastive explanations land harder than purely positive ones; informs `decision-log.md` `why_not_alternatives` field
- **Lanham et al. (2023)** — citations must be faithful, not after-the-fact rationalization; informs the `(per: <source>)` discipline
- **Mitchell et al. (2019)** — Model Cards format adapted to AI System Card (`docs/ai-system-card.md`)
- **Doshi-Velez & Kim (2017)** — explainability tier classification informs `/xai-check`
- **Selbst & Barocas (2018)** — recourse-as-substance (an explanation must enable the user to *act*) in `/xai-check` Stage 5 (corrected 2026-07-01: previously cited as "disparate impact / fairness in /regulatory-review", conflating the 2016 "Big Data's Disparate Impact" paper with the 2018 recourse paper the mechanism actually implements — the engine cite at `theory-gates.md` was already correct)
- **Bansal et al.** — human-AI complementarity informs adaptive-vs-always-on explanation in `/xai-check` Stage 2 (corrected 2026-07-01: previously credited to cognitive forcing, which is Buçinca/Malaya/Gajos)
- **Reflexion (Shinn et al., 2023)** — self-correcting loop reference for `/reflexion` (the framework's `reflexion/SKILL.md` already cites Shinn; Ryan Lopopolo is separately and correctly cited elsewhere for the *harness-context reframe*, not for Reflexion)
- **EU AI Act Art. 13 / 50** — transparency + disclosure requirements; tested by `/regulatory-review` and `/xai-check`

*(Removed 2026-07-01: "Halland CORE — informs the docs structure" — a decorative citation appearing nowhere but its own line; nothing in `docs/` operationalized it. If CORE is wanted as a real docs-structure convention, that is a separate build, not a citation.)*

## See also

- [philosophy.md](philosophy.md) — the why-opinionated rationale that picks these specific theories
- [glossary.md](glossary.md) — short definitions for theory vocabulary
- `plugins/mycelium/engine/theory-gates.md` — canonical theory gate definitions per scale
