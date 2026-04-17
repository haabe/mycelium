# OST Leaf Lifecycle

The complete pipeline from opportunity discovery to market feedback. Every OST solution leaf follows this lifecycle. Each transition has an explicit input artifact, gate, output artifact, and discard/archive criteria.

## Overview

```
OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry
→ Bounded Context → Threat Model → Preflight → Delivery Diamond
→ Launch → Market Feedback → Loop to L2
```

## The 10 Phases

### Phase 1: OST Leaf Creation (L2 Discover/Define)

**Input**: Research evidence (interviews, behavioral data, analytics)
**Gate**: Opportunity must cite ≥2 evidence sources (Torres CDH rule)
**Output**: Solution leaf in `canvas/opportunities.yml` under its parent opportunity
**Scenario link**: Each opportunity should have at least one scenario in `canvas/scenarios.yml` that illustrates the need. Scenarios are born from interview stories (`/user-interview`) — extract the persona, means, motive, and simulation from real user narratives. If no scenario exists for this opportunity, create one before generating solutions.
**Skill**: `/ost-builder`, `/user-interview`

The leaf is a hypothesis: "This solution might address this opportunity." It is NOT validated yet.

### Phase 2: Four Risks Assessment (L2 Define / L3 Discover)

**Input**: OST solution leaf
**Gate**: All four risk dimensions assessed from trio perspectives (see theory-gates.md §2)
**Output**: `four_risks` block on the solution leaf in `canvas/opportunities.yml`

Each risk dimension must have:
- A distinct assessment from its primary perspective (product/design/engineering/cross-cutting)
- Separate evidence (not a combined statement)
- A risk level (low/medium/high)

**Skill**: `/ost-builder` (step 6), `/usability-check`, `/devils-advocate`

### Phase 3: ICE Scoring (L2 Define / L3 Discover)

**Input**: Four Risks assessment
**Gate**: Four Risks must exist before scoring (ICE without risks is ungrounded)
**Output**: `ice_score` block on the solution leaf in `canvas/opportunities.yml`

ICE is derived FROM the Four Risks, not scored independently:
- **Impact** ← value + usability + viability risk assessments
- **Confidence** ← evidence quality across all risk dimensions (Gilad's meter)
- **Ease** ← feasibility risk assessment

**Skill**: `/ice-score`

### Phase 4: Assumption Testing (L3 Discover/Define)

**Input**: Riskiest assumptions identified from Four Risks + ICE (step 4 of `/ice-score`)
**Gate**: At least the #1 riskiest assumption must be tested before advancing
**Output**: Assumption test results in `assumptions[]` on the solution leaf; confidence updated

Test the assumption with the cheapest viable method:
- Value risk → fake door test, survey, concierge
- Usability risk → prototype test, wizard of oz
- Feasibility risk → technical spike, proof of concept
- Viability risk → stakeholder review, legal check

**Discard criteria**: If the riskiest assumption fails AND no pivot path exists → archive the leaf.

**Skill**: `/assumption-test`

### Phase 5: GIST Entry (L3 Define)

**Input**: ICE-scored leaf with assumption test results
**Gate**: ICE ≥ configurable threshold (default: 100) AND riskiest assumption tested
**Output**: Idea entry in `canvas/gist.yml` with `source_leaf_id` backreference
**Scenario link**: The GIST idea must reference which scenarios it addresses. Update `canvas/scenarios.yml` — add the solution to `lifecycle.designed_against[]` for each relevant scenario. If the solution only partially fits a scenario, document the gaps. A solution that doesn't address any scenario is a solution without a user — challenge it.

The leaf graduates from the OST (opportunity space) into GIST (solution space). The GIST idea inherits the leaf's ICE score and confidence level.

**Discard criteria**: ICE < threshold → archive with reason `low-ice-score`.
**Segment check**: Before discarding, verify the leaf doesn't serve a different user segment where it might score higher. If it does, re-score for that segment.

**Skill**: `/gist-plan`

### Phase 6: Bounded Context / Service Design (L3 Develop)

**Input**: GIST idea entry
**Gate**: If feasibility risk was medium or high, spike results must be documented. Cynefin domain classified.
**Output**: Service entry in `canvas/services.yml` with `gist_id` reference. If software: bounded context defined. If content: content architecture defined.

Cynefin routing applies here:
- **Clear/Complicated**: Standard design and architecture patterns
- **Complex**: Probe-sense-respond — design an experiment, not a full solution
- **Chaotic**: Stabilize first, then move to Complex

**Skill**: `/service-check`, `/cynefin-classify`

### Phase 7: Threat Model + Architecture Review (L3 Develop / L4 Discover)

**Input**: Bounded context / service design
**Gate**: If solution handles user data or requires permissions → STRIDE threat model required (G-S2). Architecture principles checked.
**Output**: Threat entry in `canvas/threat-model.yml` with `solution_id` cross-reference. Security requirements documented.

**Skill**: `/threat-model`, `/security-review`

### Phase 8: Preflight Check (L4 Define)

**Input**: All artifacts from phases 1-7
**Gate**: Corrections.md reviewed (G-P5). Definition of Done drafted. Acceptance criteria defined.
**Output**: Delivery diamond spawned (L3 spawns L4). Preflight stamp in decision log.
**Scenario link**: Acceptance criteria should be derived from scenario simulations. For each scenario in `canvas/scenarios.yml` linked to this solution, the success_state becomes an acceptance criterion and the failure_state becomes a negative test case.

The preflight verifies:
- Four Risks assessed ✓
- ICE scored ✓
- Riskiest assumption tested ✓
- GIST entry created ✓
- Service/bounded context designed ✓
- Threat model complete (if applicable) ✓
- Corrections reviewed ✓
- Scenarios linked and acceptance criteria derived ✓

**Skill**: `/preflight`, `/delivery-bootstrap`

### Phase 9: Delivery Diamond (L4 Develop/Deliver)

**Input**: L4 diamond with all upstream artifacts
**Gate**: Standard L4 theory gates (see theory-gates.md L4 matrix)
**Output**: Shipped deliverable. DORA metrics recorded. Retrospective completed.

This is the standard L4 diamond lifecycle — Discover, Define, Develop, Deliver — with all applicable gates. The upstream leaf artifacts provide context, not shortcuts — L4 still runs its own gates.

**Skill**: `/definition-of-done`, `/dora-check`, `/retrospective`

### Phase 10: Launch + Market Feedback (L5 / Loop)

**Input**: Shipped deliverable + launch plan
**Gate**: Success criteria defined pre-launch. Telemetry in place.
**Output**: Market feedback entry in `canvas/go-to-market.yml` with `source_leaf_id` backreference.
**Scenario link**: Validate scenarios against reality. Update `canvas/scenarios.yml` — set `lifecycle.validated_in_market` for each scenario: did the persona's story actually play out? Confirmed scenarios strengthen confidence. Invalidated scenarios are the most valuable learning — they reveal where our model of the user was wrong.

Post-launch:
- **Metrics confirm value**: Update confidence on original OST leaf. Mark as `launch-validated`. Update linked scenarios to `status: validated`.
- **Metrics contradict**: Spawn new L2 diamond with market evidence. Update linked scenarios to `status: invalidated` with evidence. The original leaf's provenance updates to reflect the contradiction.
- **Mixed signals**: Run `/retrospective`, then decide: iterate (stay in L5) or regress (back to L3/L2). Update scenario status to reflect which parts confirmed and which didn't.

**Skill**: `/launch-tier`, `/retrospective`

---

## Discard and Archive Protocol

When a leaf is killed at any phase, it is archived — never deleted.

### Archive Location

`canvas/archived-solutions.yml` — structured log of discarded leaves.

### Archive Entry Format

```yaml
- leaf_id: opp-001-sol-A
  opportunity_id: opp-001
  archived_at: "2026-04-12T10:00:00Z"
  archived_at_phase: 5  # Which lifecycle phase
  reason: low-ice-score | failed-assumption | feasibility-block | viability-block | superseded | market-rejection
  ice_score_at_archive: {i: 3, c: 4, e: 2, total: 24}
  four_risks_snapshot:
    value: {level: medium, summary: "..."}
    usability: {level: high, summary: "..."}
    feasibility: {level: high, summary: "..."}
    viability: {level: low, summary: "..."}
  evidence_snapshot: "Key evidence at time of archival"
  segments_checked: [general]  # Which segments were evaluated
  revival_conditions: "Could revive if feasibility improves (new tech available)"
```

### Discard Decision Rules

| Phase | Discard Trigger | Required Before Discard |
|-------|----------------|------------------------|
| 3 (ICE) | ICE < threshold (default 100) | Check other segments. Log in decision-log.md. |
| 4 (Assumption) | Riskiest assumption fails | Verify no pivot path. Log evidence. |
| 6 (Bounded Context) | Feasibility spike fails | Document what was learned. Feed back to L2. |
| 7 (Threat Model) | Unacceptable security/privacy risk | Document the risk. Consider if scope reduction resolves it. |
| 9 (Delivery) | Implementation reveals bad assumption | Regress to appropriate phase with evidence. |
| 10 (Launch) | Market rejects | Spawn new L2 diamond with rejection evidence. |

**Anti-pattern: Score-Only Discard** — Never discard a leaf on ICE score alone without checking if a different user segment would benefit. A solution that scores poorly for power users might score well for new users.

---

## Cycle Recording at Terminal States

Every leaf that reaches a terminal state (shipped, discarded, or market-rejected) MUST create or update a record in `canvas/cycle-history.yml`. This is the data input for the learning metabolism.

### When to Record

| Terminal State | Trigger | Skill Responsible |
|---------------|---------|-------------------|
| Shipped (Phase 9 complete) | Delivery diamond completes | `/retrospective` |
| Launched (Phase 10 feedback captured) | Market feedback collected | `/launch-tier` |
| Discarded (any phase) | Leaf archived | The skill performing the archive (manual or `/diamond-progress kill`) |

### What to Record

- **Predicted**: ICE score, feasibility risk level, estimated effort (captured at Phase 3/5)
- **Actual**: Outcome, actual effort, DORA metrics, user metrics (captured at Phase 9/10)
- **Calibration**: Delta between predicted and actual for each dimension

### Why This Matters

Without cycle records, the following systems have no data:
- **Adaptive thresholds** (`engine/adaptive-thresholds.md`) — cannot calibrate ICE threshold
- **Pattern detector** (`engine/pattern-detector.md`) — cannot identify correlations
- **Framework reflexion** (`engine/framework-reflexion.md`) — cannot measure cycle velocity or confidence calibration
- **Evidence decay** (`engine/evidence-decay.md`) — cannot calibrate staleness thresholds

---

## WIP and Flow

Leaf WIP follows diamond WIP limits from `diamond-rules.md`:
- L3 working WIP: 2 solutions (compare at most 2 concurrently)
- L3 hard ceiling: 5 solutions
- When 2 leaves are in active evaluation, others queue

For parallel leaf evaluation (bakeoff), see `orchestration/leaf-bakeoff.md`.

---

## Cross-Reference Map

Every artifact created during the lifecycle must be traceable:

```
canvas/opportunities.yml  (leaf_id, four_risks, ice_score, assumptions)
  ↓ source_leaf_id
canvas/gist.yml  (idea with source_leaf_id backreference)
  ↓ gist_id
canvas/services.yml  (service/bounded context with gist_id reference)
  ↓ solution_id
canvas/threat-model.yml  (threat entry with solution_id reference)
  ↓ (delivery diamond inherits all references)
canvas/go-to-market.yml  (launch with source_leaf_id backreference)
  ↓ (market feedback loops back)
canvas/opportunities.yml  (original leaf updated with launch evidence)
```

If any link in this chain is missing, `/canvas-health` should flag it as an orphaned reference.

---

## Theory Citations

- Torres: Continuous Discovery Habits (OST, assumption testing, trio perspectives)
- Cagan: Inspired (Four Risks framework)
- Ellis: ICE scoring (Impact × Confidence × Ease). Gilad: Evidence-Guided (Confidence Meter — evidence-grading layer on Ellis's ICE)
- Gothelf: Lean UX (hypothesis-driven solution framing)
- Snowden: Cynefin (domain-appropriate methods at Phase 6)
- Downe: Good Services (service design at Phase 6)
- Forsgren: Accelerate (DORA metrics at Phase 9)
- Lauchengco: Loved (market feedback at Phase 10)
