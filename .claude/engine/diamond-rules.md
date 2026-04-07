# Diamond Rules

Diamonds are the core workflow unit in Mycelium. Each diamond represents a cycle of divergent and convergent thinking applied to a problem at a specific scale.

## The Four Phases

Every diamond passes through four phases (Double Diamond):

```
    DISCOVER          DEFINE           DEVELOP          DELIVER
   /        \        /      \         /       \        /       \
  /  Diverge  \    / Converge \     / Diverge  \    / Converge  \
 /   explore   \  /  synthesize\   /   ideate   \  /  implement  \
/    research   \/   prioritize \/ prototype    \/   validate    \
```

1. **Discover** (Divergent): Explore the problem space. Research, interview, observe. Expand understanding. No solutions yet.
2. **Define** (Convergent): Synthesize findings. Frame the problem. Identify opportunities. Select focus.
3. **Develop** (Divergent): Generate solutions for the defined problem. Prototype. Experiment. Multiple options.
4. **Deliver** (Convergent): Build, test, ship. Validate with real users. Measure outcomes.

## The Six Scales (L0-L5)

Diamonds operate at different scales of abstraction:

| Scale | Name | Scope | Duration | Example |
|-------|------|-------|----------|---------|
| **L0** | Purpose | Why the organization exists | Months-years | "We help teams ship better products" |
| **L1** | Strategy | Strategic direction and bets | Weeks-months | "Focus on AI-assisted product development" |
| **L2** | Opportunity | Problem/opportunity spaces | Days-weeks | "Teams struggle with discovery-delivery handoff" |
| **L3** | Solution | Specific solution approaches | Days-weeks | "An AI agent that enforces theory gates" |
| **L4** | Feature | Individual features/stories | Hours-days | "Implement bias-check skill" |
| **L5** | Task | Atomic implementation tasks | Minutes-hours | "Write unit tests for confidence scoring" |

## Spawning Rules

Diamonds can spawn child diamonds at the next scale down:

- An L1 diamond in Define phase can spawn L2 diamonds for each identified opportunity.
- An L2 diamond in Develop phase can spawn L3 diamonds for each solution approach.
- An L3 diamond in Deliver phase can spawn L4 diamonds for each feature.
- An L4 diamond in Deliver phase can spawn L5 diamonds for each task.

**Constraints:**
- Never skip more than one scale level when spawning.
- Parent diamond remains active while children execute.
- Child diamond outcomes feed back into parent diamond evidence.
- Maximum active diamonds per scale: L0=1, L1=3, L2=5, L3=5, L4=10, L5=20.

## Regression Rules

When evidence invalidates a higher-level assumption, regress:

- If L4 delivery reveals the L3 solution is wrong, regress to L3 Develop.
- If L3 prototyping reveals the L2 opportunity is misframed, regress to L2 Define.
- If L2 research reveals the L1 strategy is flawed, regress to L1 Define.

**Regression protocol:**
1. Document what was learned (update product-journal.md).
2. Archive, do not delete, the invalidated diamond's artifacts.
3. Re-enter the parent diamond at the appropriate phase.
4. Update confidence scores to reflect new evidence.
5. Never treat regression as failure -- it is learning.

## Smooth Flow

Optimize for flow across diamonds:

- **WIP limits**: Maximum 1 diamond in active focus per scale level at a time.
- **Pull, don't push**: Start new diamonds only when capacity allows.
- **Small batches**: Prefer many small diamonds over few large ones.
- **Unblock first**: If a diamond is blocked, resolve the blocker before starting new work.
- **Minimize handoffs**: Same agent/team should own a diamond from Discover through Deliver when possible.

## Phase Transitions Require Theory Gates

Moving from one phase to the next is not automatic. Each transition must pass the relevant theory gates:

| Transition | Key Gates |
|------------|-----------|
| Discover -> Define | Evidence sufficiency, bias check, triangulation |
| Define -> Develop | Problem framing validated, JTBD mapped, Cynefin classified |
| Develop -> Deliver | Solution validated, four risks assessed, security reviewed |
| Deliver -> Complete | DoD met, BVSSH check, DORA metrics, retrospective |

See `theory-gates.md` for detailed gate criteria per scale.

## Diamond State Tracking

Every diamond maintains:

```yaml
id: [unique identifier]
scale: [L0-L5]
phase: [discover | define | develop | deliver | complete]
confidence: [0.0 - 1.0]
parent: [parent diamond ID or null]
children: [list of child diamond IDs]
created: [timestamp]
last_updated: [timestamp]
evidence: [list of evidence references]
blockers: [list of current blockers]
theory_gates:
  discover_to_define: [pass | fail | pending]
  define_to_develop: [pass | fail | pending]
  develop_to_deliver: [pass | fail | pending]
  deliver_to_complete: [pass | fail | pending]
```

Update state on every significant action. State is the source of truth for what the agent should do next.
