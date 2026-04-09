# Theory Tensions

Mycelium integrates 40+ frameworks. Some of them disagree. This file names the known tensions and provides navigation guidance for choosing between competing approaches.

**Why this file exists**: Simon Rohrer's LinkedIn feedback (v0.8.x) called out that "there's a lot in there that doesn't necessarily align 100%." Until v0.9.0, Mycelium hid these tensions and trusted the agent to reconcile them silently. That's the inferential-enforcement trap. This file makes the tensions explicit so the agent can name the choice and log the rationale in `decision-log.md`.

**How to read this file**: Each tension is named, classified by nature (using Springer's taxonomy: interference / inconsistency / conflict), described in plain terms, and given multi-dimensional context criteria for choosing between the frameworks. The criteria are not a decision tree — they are signals the agent should weigh. When you make a choice, log it in the decision log with the specific signals that drove it.

## Taxonomy (Springer, *Reconciling Requirements*)

- **Interference** — Both frameworks are valid; they compete for the same resource (time, attention, scope). Choosing one means deprioritizing the other temporarily. *Example: Continuous discovery vs quarterly GIST goals — both are right; cadence determines which wins this week.*
- **Inconsistency** — The frameworks make contradictory claims about the same situation. One is more right than the other in this context. *Example: XP pair programming vs Team Topologies X-as-a-Service — they prescribe opposite collaboration defaults.*
- **Conflict** — The frameworks are mutually exclusive. Adopting one structurally precludes the other. *Example: MoSCoW time-box-first vs Shape Up appetite-first — these are different scope-flexing models that cannot coexist on the same delivery cycle.*

---

## Tension 1: Continuous Discovery vs Quarterly GIST Goals

**Frameworks**: Torres (Continuous Discovery Habits — weekly user research) vs Gilad (GIST — quarterly goals with idea bank)

**Nature**: Interference (both valid, different cadences competing for the same research bandwidth)

**The disagreement**:
- Torres: research happens every week, regardless of planning cycle. The OST is updated continuously.
- Gilad: goals are set quarterly. Ideas are scored and promoted on the same cadence. Mid-quarter, the focus is execution.

**Context criteria for choosing**:

| Signal | Lean toward Torres | Lean toward Gilad |
|---|---|---|
| **Cynefin domain** | Complex (need probe-sense-respond) | Complicated (expert analysis is reliable) |
| **Product maturity** | Greenfield, pre-product-market-fit | Established, predictable user base |
| **Team size** | Solo or small team (discovery + delivery overlap) | Larger team (specialization is realistic) |
| **Delivery cadence** | Continuous deployment | Quarterly release cycles |
| **User feedback latency** | Hours-days | Weeks-months |

**Decision log prompt**: When choosing one over the other, state which signals dominated. Example: *"Chose Torres weekly research because we're pre-PMF (greenfield) in a Complex domain with daily user contact. Gilad-style quarterly batching would slow learning."*

---

## Tension 2: MoSCoW Time-Box-First vs Shape Up Appetite-First

**Frameworks**: DSDM MoSCoW (fix the time, flex the scope) vs Basecamp Shape Up (fix the appetite, shape scope around it)

**Nature**: Conflict (mutually exclusive scope-flexing models within the same delivery cycle)

**The disagreement**:
- MoSCoW: lock the deadline. Categorize work as Must / Should / Could / Won't. When the time runs out, ship Must-haves and re-plan the rest.
- Shape Up: define an "appetite" (how much time the work is worth) BEFORE shaping. The team designs a solution that fits within the appetite. No fixed must-haves.

**Context criteria for choosing**:

| Signal | Lean toward MoSCoW | Lean toward Shape Up |
|---|---|---|
| **Team experience with the problem** | Familiar (can categorize accurately) | Unfamiliar (categorization would be guessing) |
| **Stakeholder relationship** | Hard deadline driven by external commitment | Internal product decisions |
| **Appetite definition** | Cannot define "what's it worth" upfront | Can answer "how much is this worth" before scoping |
| **Solution space** | Well-understood, multiple known options | Wide-open, design space matters |
| **Risk tolerance for cutting features** | Acceptable (Should/Could items) | Acceptable (whole bet might pivot) |

**Decision log prompt**: *"Chose Shape Up because we don't yet know what 'must-have' looks like for this feature — the appetite (6 weeks) is the constraint, and the team will shape the solution to fit."*

---

## Tension 3: XP Pair Programming vs Team Topologies X-as-a-Service

**Frameworks**: Beck (Extreme Programming, pair programming as default) vs Skelton/Pais (Team Topologies, X-as-a-Service as default for cross-team work)

**Nature**: Inconsistency (they prescribe opposite defaults for the same situation)

**The disagreement**:
- XP: collaboration is the default. Pair programming for hard work, mob programming for harder work. Tight feedback, shared knowledge, fewer handoffs.
- Team Topologies: collaboration is expensive — limit it to time-boxed periods. Most teams should consume each other's outputs via clean APIs (X-as-a-Service), not collaborate continuously.

**Context criteria for choosing**:

| Signal | Lean toward XP collaboration | Lean toward Team Topologies X-as-a-Service |
|---|---|---|
| **Same team or different teams** | Same team (collaboration is internal) | Different teams (collaboration crosses boundaries) |
| **Cognitive load** | Manageable (can hold both contexts) | Already overloaded (need to reduce, not add) |
| **Knowledge transfer needed** | Yes — onboarding, novel problem, skill sharing | No — interface is well-defined, knowledge is captured in docs |
| **Delivery interdependence** | Tight (output of A is input of B same-day) | Loose (B consumes A's stable API) |
| **Frequency of handoffs** | Continuous | Episodic |

**Decision log prompt**: *"Within the team, pairing on the new auth module (XP). Across teams, the platform team's auth API is consumed via X-as-a-Service — we don't pair with them, we consume their docs."*

---

## Tension 4: Cagan Empowered Teams vs Team Topologies Cognitive Load Reduction

**Frameworks**: Cagan (Inspired/Empowered — give teams autonomy and outcome ownership) vs Skelton/Pais (Team Topologies — bound team scope by cognitive load capacity)

**Nature**: Interference (both valid, compete for the same dimension: how much should a team own?)

**The disagreement**:
- Cagan: empowered teams own outcomes end-to-end. Constraining their scope to what's "easy" limits impact.
- Team Topologies: cognitive load is a hard constraint. Stream-aligned teams should own a coherent bounded context, not "everything that affects the user."

**Context criteria for choosing**:

| Signal | Lean toward Cagan autonomy | Lean toward Team Topologies bounding |
|---|---|---|
| **Team size** | Small enough for full ownership (5-9) | Larger or growing (need bounded scope) |
| **Domain complexity** | Cohesive domain (one mental model) | Multi-domain (split by bounded context) |
| **Cognitive load signal** | Team thriving | Team showing burnout / context-switching |
| **Outcome measurement** | Team can be held accountable to metrics they control | Team's outcomes depend on systems they can't change |

**Decision log prompt**: *"Empowered the team end-to-end on checkout, but split discovery for billing (different domain) into a separate stream-aligned team. Cognitive load was getting unsustainable."*

---

## Tension 5: Lean UX Hypotheses vs JTBD Statements vs BDD Scenarios

**Frameworks**: Gothelf (Lean UX outcome hypotheses) vs Christensen (JTBD job statements) vs North (BDD Given/When/Then scenarios)

**Nature**: Interference (different abstraction levels for the same underlying need)

**The disagreement**: All three are ways to express "what we believe a user needs," but they operate at different levels:
- **Lean UX**: outcome-level. *"We believe Outcome X for User Y if Change Z."*
- **JTBD**: motivation-level. *"When [situation], I want to [motivation], so I can [outcome]."*
- **BDD**: behavior-level. *"Given [precondition], When [action], Then [observable result]."*

**Context criteria for choosing**:

| Signal | Lean toward Lean UX | Lean toward JTBD | Lean toward BDD |
|---|---|---|---|
| **Phase** | L2 Opportunity discovery | L2-L3 framing | L3-L4 specification |
| **Audience** | Product + research | Product + design | Engineering + QA |
| **Granularity** | Outcome | Job | Test case |
| **Falsifiability** | Hypothesis testable in days | Job stable for months | Test runs in seconds |

**Decision log prompt**: They're not always in conflict — they layer. JTBD frames the why, Lean UX frames the testable bet, BDD frames the deliverable behavior. Conflict only arises when the team picks ONE and tries to use it for everything, which forces ill-fitting framings.

---

## Tension 6: Kanban WIP Limits vs GIST Idea Bank

**Frameworks**: Kanban (limit work in progress to maximize flow) vs Gilad GIST (maintain a large idea bank, hold many ideas loosely)

**Nature**: Interference (different scopes — generation vs execution)

**The disagreement**:
- Kanban: limit WIP. Finish before starting. Reduce context-switching cost.
- GIST: generate many ideas. Most will fail (>80%). Hold them loosely until evidence promotes one.

**Context criteria for choosing**:

| Signal | Apply Kanban WIP | Apply GIST idea bank |
|---|---|---|
| **Stage** | Execution / delivery | Discovery / opportunity exploration |
| **Resource being constrained** | Engineering capacity | Cognitive shelf for "what could we try" |
| **Failure cost** | High (in-flight work has carrying cost) | Low (ideas in the bank are cheap) |

**Decision log prompt**: GIST's idea bank isn't WIP — it's not "in progress." WIP limits apply to **steps** (the experiments testing ideas), not to the bank itself. Resolved by scope: GIST handles ideas, Kanban handles steps + tasks.

---

## Adding New Tensions

When you encounter a new tension between frameworks Mycelium integrates, add it here using this template:

```markdown
## Tension N: [Framework A] vs [Framework B]

**Frameworks**: [author A] vs [author B]
**Nature**: interference | inconsistency | conflict
**The disagreement**: [one paragraph]
**Context criteria for choosing**:
| Signal | Lean toward A | Lean toward B |
|---|---|---|
| ... | ... | ... |
**Decision log prompt**: [an example sentence the agent could use when logging the choice]
```

The goal is not to "resolve" the tension — most cannot be resolved in the abstract. The goal is to make the choice **visible and traceable** so the agent doesn't silently pick one framework and pretend the other doesn't exist.

---

*Sources*:
- Simon Rohrer (LinkedIn feedback, v0.8.x)
- Springer: *Reconciling Requirements* taxonomy (interference / inconsistency / conflict)
- PMI: *Reconciling Differences* (agile vs traditional PM)
- SEBoK: Decision Management — context-driven trade studies over decision trees
- All framework citations are in [README.md](../../README.md) Theories table
