# Theories integrated

**Audience**: practitioner peers (PMs, senior engineers, designers, researchers) who want to know which frameworks Mycelium uses and how each one is wired in.
**Time to read**: 15 min for full read; 2 min if you only want the table.
**Last updated**: 2026-06-14.

The differentiator vs other framework lists: every theory is **mechanism-mapped** — the column "Implemented as" answers "which Mycelium artifact actually applies this?" Citations without mechanism-mapping are theatre.

## Tier 1 — Load-bearing theories

These shape Mycelium's structure. Removing one collapses a load-bearing wall.

### Sinek — Golden Circle (Why / How / What)

The L0 Purpose canvas (`canvas/purpose.yml`) follows the Why → How → What ordering Sinek argues for. The agent refuses to spawn an L1 Strategy diamond before L0 has at least the `why` field populated with evidence. Implemented as: `canvas/purpose.yml`, `/interview` first phase, gate 1 (Evidence) at L0→L1.

### Christensen — Jobs to be Done

JTBD with the Christensen tripartite (functional, emotional, social). Each canvas entry can carry per-dimension evidence after the v0.17.0 schema fix (`validation_status_per_dimension`). Implemented as: `canvas/jobs-to-be-done.yml`, `/jtbd-map` skill, gate 3 (JTBD) at L2→L3.

### Torres — Continuous Discovery / Opportunity Solution Tree

The OST is the bridge from L2 Opportunity to L3 Solution: opportunities are decomposed into solutions, solutions compete on ICE, the winner spawns L3. Loser leaves are archived with evidence. Torres's interviewing structure also informs `/user-interview`. Implemented as: `canvas/opportunities.yml`, `/ost-builder`, `/user-interview`, leaf-lifecycle.md.

### Cagan — Inspired / Empowered (four risks)

Value, Usability, Feasibility, Viability. Every leaf must show evidence on each before advancing out of L3. Cagan's "prototype IS the spec" discipline is also the load-bearing claim behind Mycelium's "canvas IS the spec". Implemented as: gate 2 (Four Risks), `/assumption-test`, leaf-lifecycle.md phase 2.

### Wardley — Mapping

Strategic landscape with evolution stages (Genesis → Custom → Product → Commodity). Mycelium's L1 strategic_frame articulates "where Mycelium plays" using Wardley's vocabulary. Implemented as: `canvas/landscape.yml`, `/wardley-map`, gate at L1→L2.

### Cynefin (Snowden) — Domain classification

Clear / Complicated / Complex / Chaotic / Confused. Determines which methods apply (best-practice vs good-practice vs probe-sense-respond). Mycelium uses Cynefin to scale the discovery rigor: complex domains get more diamond depth, clear domains skip scales. Implemented as: `/cynefin-classify`, gate 4 (Domain Fit) at L2 transitions.

### Forsgren / Humble / Kim — DORA

Five delivery metrics (deployment frequency, lead time, change failure rate, FDRT, reliability). L4 only. Adapted for non-software product types (content, AI tool, service) into APEX-shaped variants. Implemented as: `canvas/dora-metrics.yml`, `/dora-check`, gate 10 (Delivery Health) at L4→complete.

### Hoskins — Scenarios as connective tissue

Persona + Means + Motive + Simulation. Born at L2 from interview stories, designed against at L3, tested at L4, validated at L5. Hoskins's "User Knowledge Repository" concept validated Mycelium's canvas approach as architecturally aligned. Implemented as: `canvas/scenarios.yml`, scenario extraction in `/user-interview`, scenario wiring through leaf-lifecycle phases 1, 5, 8, 10.

## Tier 2 — Integrated theories

Each one shapes a specific surface; removable in isolation, but the surface goes with it.

| Theory | Author(s) | Implemented as |
|---|---|---|
| User Needs Mapping | Allen | `canvas/user-needs.yml`, `/user-needs-map` (needs independent of solutions, feeds OST) |
| GIST Planning | Gilad | `canvas/gist.yml`, `/gist-plan` (L3 prioritization) |
| ICE Scoring | Ellis (adopted by Gilad) | `/ice-score` (evidence-backed confidence; calibration via `cycle-history.yml`) |
| North Star Framework | Ellis | `canvas/north-star.yml` (key metric + input metrics) |
| Team Topologies | Skelton, Pais | `canvas/team-shape.yml`, `/team-shape` (cognitive load, interaction modes) |
| Good Services | Downe | `canvas/services.yml`, `/service-check` (15 service principles) |
| OWASP Top 10:2025 / STRIDE | OWASP, Shostack | `canvas/threat-model.yml`, `/threat-model`, `/security-review` (gate 6) |
| Privacy by Design | Cavoukian | `canvas/privacy-assessment.yml`, `/privacy-check` (gate 7) |
| Loved | Lauchengco | `canvas/go-to-market.yml`, `/launch-tier` (L5) |
| BVSSH | Smart | `canvas/bvssh-health.yml`, `/bvssh-check` (gate 8 Outcomes) |
| Build to Learn vs Build to Earn | Patton, Cagan | Discovery diamonds = build-to-learn; delivery diamonds = build-to-earn (load-bearing distinction in CLAUDE.md) |
| Cognitive Forcing Functions | Buçinca, Malaya, Gajos | Diamond transition gates: human articulates evidence before agent shows verdict |
| Theory of Constraints | Goldratt | `value-stream.yml`, bottleneck identification at L4 |
| Three Ways / Five Ideals | Kim | DevOps flow / feedback / continual learning shaping L4 practices |
| The Fifth Discipline | Senge | `cluster-instances.md` is the recurring-pattern ledger; cluster log is the structural-issue surface |
| Domain-Driven Design | Evans | `canvas/bounded-contexts.yml` (L3→L4 boundary) |
| Lean UX | Gothelf, Seiden | Hypothesis-driven design feeds `/assumption-test` |
| Toyota Kata | Rother | Coaching-question shape in `/diamond-assess` |
| Architecture Decision Records | Nygard | `decision-log.md` shape (with contrastive `why_not_alternatives`, Liao et al. extension) |

## Tier 3 — Background theories (citation-only)

These show up as citations and inform the framework's ethics or peripheral mechanisms; they do not shape primary structure. Listed as `... and more` below — the table format is reserved for tier 1 + tier 2 (the load-bearing surface).

- **Behavioral Science** (Shotton, Kahneman) — bias mitigation in `/bias-check`, ethical design constraints
- **Amabile** (creativity research) — *Brilliant but Cruel* (1983) grounds the Negativity-as-Competence bias item in `/bias-check` (harsh critique reads as competence, so adversarial-review findings get weighed on cited evidence, not severity); componential theory backs the separable-process bet named in [philosophy.md](philosophy.md)
- **CALMS** (Willis, Humble) — DevOps culture vocabulary in retrospectives
- **Hooked / Indistractable** (Eyal) — ethical engagement design (anti-dark-pattern check)
- **Clean Architecture / SOLID** (Martin) — engineering-principles.md NUDGE tier
- **SRE** (Beyer, Jones, Petoff, Murphy) — error budgets, toil, SLIs/SLOs vocabulary
- **TPS / Lean** (Ohno, Toyoda) — 7 Wastes inform value-stream.yml
- **Argyris** — double-loop learning informs the corrections-graduates-to-mechanism cycle
- **Norman** (visible affordances) — UX surface for footgun-to-affordance graduations (e.g., wayfinding strict marker, diamond-progress prompt template)
- **Liao et al. (2020)** — contrastive explanations land harder than purely positive ones; informs `decision-log.md` `why_not_alternatives` field
- **Lanham et al. (2023)** — citations must be faithful, not after-the-fact rationalization; informs the `(per: <source>)` discipline
- **Mitchell et al. (2019)** — Model Cards format adapted to AI System Card (`docs/ai-system-card.md`)
- **Doshi-Velez & Kim (2017)** — explainability tier classification informs `/xai-check`
- **Selbst & Barocas** — disparate impact / fairness considerations in `/regulatory-review`
- **Bansal et al.** — human-AI complementarity informs cognitive forcing applications
- **Lopopolo (Reflexion)** — self-correcting loop reference for `/reflexion`
- **EU AI Act Art. 13 / 50** — transparency + disclosure requirements; tested by `/regulatory-review` and `/xai-check`
- **Halland CORE** — Central content / Outward paths / Related links / Entry points; informs the docs structure

## See also

- [philosophy.md](philosophy.md) — the why-opinionated rationale that picks these specific theories
- [glossary.md](glossary.md) — short definitions for theory vocabulary
- `.claude/engine/theory-gates.md` — canonical theory gate definitions per scale
