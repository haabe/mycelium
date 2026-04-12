# Perspective Resolution Framework

When product, design, and engineering perspectives conflict on a solution, this framework provides structured resolution. Conflicts are healthy — they mean all three perspectives are being applied. Suppressing a perspective is the anti-pattern.

## When This Applies

Any time the three trio perspectives (Torres) produce conflicting assessments during:
- Four Risks evaluation (value vs usability vs feasibility)
- ICE scoring disagreements
- Solution design trade-offs
- Architecture vs UX decisions
- Scope negotiations

## Step 1: Surface the Tension

Log the conflict explicitly in `.claude/harness/decision-log.md`:

```yaml
decision: "Perspective conflict on [solution name]"
context: "During [phase] of [diamond id]"
perspectives:
  product: "Position and evidence"
  design: "Position and evidence"
  engineering: "Position and evidence"
conflict_type: value-vs-feasibility | usability-vs-feasibility | value-vs-viability | usability-vs-viability | three-way
```

Never resolve implicitly. If a perspective was overridden, the record must show it and why.

## Step 2: Classify the Conflict

### Value vs Feasibility
Users want it, but engineering says it's hard/risky.

**Resolution path**: Can the solution be simplified to reduce feasibility risk while preserving core value? Look for the minimum viable version that still addresses the user need. If no simplification works, the feasibility risk becomes the riskiest assumption — test it with a spike.

### Usability vs Feasibility
Design wants a better experience, but engineering says it's expensive.

**Resolution path**: Can the UX be phased? MVP experience first (functional but not ideal), polish in a subsequent iteration. The key question: is the MVP experience good enough that users will succeed (Downe P4: Enable completion), even if it's not delightful?

### Value vs Viability
Users want it, but business/legal/ethical constraints say no.

**Resolution path**: Business constraints generally win unless user evidence is overwhelming (≥3 independent sources showing strong need). If constraints win, document clearly — the user need doesn't disappear, it waits for constraints to change. If user evidence is overwhelming, escalate: the business constraint itself may need re-evaluation.

### Usability vs Viability
Design wants a better experience, but business/legal/ethical constraints prevent it.

**Resolution path**: Can the experience be redesigned within the constraints? Often the constraint itself suggests a design direction (e.g., GDPR consent flows can be designed well, not just bolted on). If constraints are hard legal requirements, design works within them. If constraints are business policy, and usability evidence is strong (≥2 user tests showing failure), escalate: the policy may need re-evaluation.

### Three-Way Disagreement
All three perspectives see different problems with the solution.

**Resolution path**: This usually means the solution is trying to do too much. Decompose it into smaller pieces. If decomposition doesn't help, escalate to assumption testing — test the riskiest dimension first, let data resolve the disagreement.

## Step 3: Apply Resolution Method

In order of preference:

### 1. Constraint-Based Resolution
Find a solution variant that satisfies all three perspectives within acceptable thresholds. This is the ideal outcome — no perspective is overridden.

**How**: Map each perspective's minimum acceptable threshold. Find the overlap. If overlap exists, that's the solution space.

### 2. Phased Resolution
Deliver in stages, addressing each perspective's concerns sequentially.

**How**: Phase 1 addresses the highest-risk perspective. Phase 2 addresses the next. Each phase is a deliverable increment. Use MoSCoW (DSDM) to tag phases: Must (Phase 1), Should (Phase 2), Could (Phase 3).

### 3. Evidence-Based Resolution
Run an assumption test targeting the disputed dimension. Let data decide.

**How**: Design the cheapest test that would resolve the disagreement. The perspective with the least evidence goes first. If the test validates one perspective over others, the data wins.

### 4. Scope Reduction
Reduce scope until all three perspectives align.

**How**: Systematically remove features/capabilities until the remaining scope is acceptable to all three perspectives. What's removed goes to a "future consideration" backlog, not forgotten.

## Anti-Pattern: Perspective Suppression

**Never resolve a conflict by ignoring a perspective.** Common forms:
- "Engineering will figure it out" (suppresses feasibility)
- "Users will learn" (suppresses usability)
- "We'll find the users later" (suppresses value)
- "Legal won't notice" (suppresses viability)

If a perspective is overridden, it must be:
1. Explicitly documented in the decision log
2. Justified with evidence (not convenience)
3. Tagged as a risk to monitor post-launch

## For Solo Developers

Solo developers embody all three perspectives sequentially. The risk is collapsing perspectives — engineering convenience wins because that's the developer's primary lens.

**Protocol for solo work**:
1. Evaluate as Product first: "Would I pay for this? Would users switch from their current solution?"
2. Evaluate as Design second: "Can someone who isn't me figure this out in under 30 seconds?"
3. Evaluate as Engineering last: "Can I build this within my constraints?"
4. If Engineering overrules Product or Design, document WHY in the decision log with specific constraints.

## Theory Citations

- Torres: Product Trio (three perspectives requirement)
- Cagan: Inspired/Empowered (Four Risks as structured evaluation)
- DSDM: MoSCoW (scope flexing for phased resolution)
- Senge: The Fifth Discipline (systems thinking for understanding trade-offs)
