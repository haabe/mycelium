# Cynefin Routing

How to classify problems into Cynefin domains and choose appropriate methods (Snowden).

## The Five Domains

### 1. Clear (formerly Simple/Obvious)

**Characteristics:**
- Cause and effect are obvious to everyone.
- Best practices exist and are well-documented.
- The relationship between cause and effect is linear and repeatable.
- Constraints are rigid and well-understood.

**Approach:** Sense - Categorize - Respond

**Appropriate methods:**
- Apply established best practices.
- Use checklists and standard operating procedures.
- Delegate to automation where possible.
- Focus on efficiency and consistency.

**Examples:**
- Implementing a standard login form with established patterns.
- Setting up CI/CD with well-known tooling.
- Applying OWASP security checklist to a standard web app.
- Creating CRUD endpoints for a simple data model.

**Mycelium techniques:**
- Use engineering-principles.md directly.
- Apply Definition of Done checklist.
- Reference patterns.md for known solutions.
- L5 diamonds operate mostly here.

### 2. Complicated

**Characteristics:**
- Cause and effect discoverable but require expertise.
- Multiple right answers exist.
- Analysis can predict outcomes, but requires skill.
- Constraints are governing but allow some flexibility.

**Approach:** Sense - Analyze - Respond

**Appropriate methods:**
- Expert analysis and consultation.
- Architectural review and technical spikes.
- Multiple solution evaluation with trade-off analysis.
- Wardley mapping for strategic positioning.

**Examples:**
- Choosing between database architectures for a new service.
- Designing an API that needs to serve multiple client types.
- Optimizing performance of a complex query.
- Planning a migration between technology stacks.

**Mycelium techniques:**
- Run technical spikes in L4 diamonds.
- Use ICE scoring for solution comparison.
- Apply STRIDE threat modeling.
- L3-L4 diamonds often operate here.

### 3. Complex

**Characteristics:**
- Cause and effect only discoverable in retrospect.
- Emergent patterns -- outcomes are unpredictable.
- The system changes as you interact with it.
- No right answer -- only better or worse probes.

**Approach:** Probe - Sense - Respond

**Appropriate methods:**
- Safe-to-fail experiments.
- Hypothesis-driven development.
- A/B testing and progressive rollout.
- Continuous discovery with rapid feedback loops.
- Assumption testing (smallest viable test).

**Examples:**
- Understanding why users abandon a signup flow.
- Finding product-market fit for a new concept.
- Changing team behavior or organizational culture.
- Entering a new market segment.

**Mycelium techniques:**
- Torres-style continuous discovery.
- OST construction from research.
- Assumption testing skill.
- L1-L2 diamonds often operate here.
- Multiple small experiments over single big bets.

### 4. Chaotic

**Characteristics:**
- No perceivable cause and effect.
- Crisis situation requiring immediate action.
- No time for analysis or experiments.
- Turbulence -- the situation is unstable.

**Approach:** Act - Sense - Respond

**Appropriate methods:**
- Stabilize first, then analyze.
- Establish order with decisive action.
- Command and control temporarily appropriate.
- Post-crisis retrospective to learn.

**Examples:**
- Production system down with unknown cause.
- Security breach in progress.
- Critical dependency suddenly deprecated.
- Major regulatory change with immediate deadline.

**Mycelium techniques:**
- Automated rollback (DORA).
- Incident response procedures.
- Retrospective skill after stabilization.
- Move to Complex or Complicated once stabilized.

### 5. Disorder

**Characteristics:**
- Don't know which domain applies.
- Multiple perspectives disagree on the nature of the problem.
- The situation is unclear or ambiguous.

**Approach:** Gather information to classify into another domain.

**Appropriate methods:**
- Break the problem into smaller parts.
- Classify each part independently.
- Consult multiple perspectives.
- Start with discovery to reduce ambiguity.

**Examples:**
- New project with unclear requirements and unknown technology.
- Conflicting stakeholder visions with no data.
- Inherited codebase with no documentation.

**Mycelium techniques:**
- Start with L0/L1 discovery diamond.
- Interview skill for stakeholder alignment.
- Cynefin-classify skill to decompose.
- bias-check before classification.

## Wardley Evolution to Cynefin Mapping

Wardley map evolution stages roughly correlate:

| Wardley Stage | Typical Cynefin Domain | Reasoning |
|---------------|----------------------|-----------|
| **Genesis** | Complex / Chaotic | Novel, uncertain, experimental. Probe and learn. |
| **Custom** | Complex / Complicated | Emerging understanding. Some patterns visible. Expert analysis valuable. |
| **Product** | Complicated | Known approaches exist. Multiple valid architectures. Expertise needed. |
| **Commodity** | Clear | Well-understood. Best practices established. Standardize and automate. |

**Important:** This mapping is a heuristic, not a rule. A genesis-stage component might have Clear sub-problems (e.g., its deployment pipeline), and a commodity component might face Complex challenges (e.g., migrating between commodity providers).

## Decision Flow

```
Is the problem well-understood with known best practices?
  YES -> Clear: Apply best practice.
  NO  -> Can experts analyze and predict outcomes?
    YES -> Complicated: Get expert analysis, evaluate options.
    NO  -> Is the situation stable enough for experiments?
      YES -> Complex: Design safe-to-fail probes.
      NO  -> Is there immediate crisis?
        YES -> Chaotic: Act to stabilize, then reassess.
        NO  -> Disorder: Decompose and reclassify parts.
```
