# Diamond Rules

Diamonds are the core workflow unit in Mycelium. Each diamond represents a cycle of divergent and convergent thinking applied to a problem at a specific scale.

## The Four Phases

Every diamond passes through four phases, based on the **Double Diamond** model (Design Council, 2005):

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

| Scale | Name | Focus | Primary Theories | Duration | Example |
|-------|------|-------|-----------------|----------|---------|
| **L0** | Purpose | Why we exist | Sinek (Golden Circle), JTBD (Christensen) | Months-years | "We help teams ship better products" |
| **L1** | Strategy | Where to play | Wardley Mapping, North Star, Team Topologies (Skelton) | Weeks-months | "Focus on AI-assisted product development" |
| **L2** | Opportunity | What to solve | Torres (CDH/OST), Allen (User Needs), Cynefin (Snowden) | Days-weeks | "Teams struggle with discovery-delivery handoff" |
| **L3** | Solution | How to solve it | Gilad (GIST/ICE), Cagan (Inspired), Downe (Good Services) | Days-weeks | "An AI agent that enforces theory gates" |
| **L4** | Delivery | Build and ship | Forsgren (DORA), OWASP, DRY/KISS/YAGNI/SOLID/SoC | Hours-days | "Implement bias-check skill with tests" |
| **L5** | Market | Reach users | Lauchengco (Loved), Shotton (behavioral science) | Days-weeks | "Position and launch the product" |

**Note on L4 sub-diamonds**: Complex features within L4 can spawn their own sub-L4 diamonds (e.g., a large feature broken into independently deliverable slices). These are still L4 scale but nested. Atomic tasks within delivery do NOT need their own diamond -- they are simply tasks within the L4 Deliver phase.

## Spawning Rules

Diamonds spawn child diamonds when complexity or scope requires it:

- L0 spawns L1 when purpose is defined and strategic questions arise
- L1 spawns L2 when landscape is mapped and opportunities need exploration
- L2 spawns L3 when opportunities have sufficient evidence for solution design
- L3 spawns L4 when solutions pass confidence threshold and need building
- L4 can spawn sub-L4 diamonds for complex features requiring their own discovery
- L5 spawns L2 when market feedback reveals new opportunities (feedback loop)

**Constraints:**
- Parent diamond remains active while children execute (smooth flow)
- Child diamond outcomes feed back into parent diamond evidence
- L5 Market feedback can trigger new L2 Opportunity diamonds (the learning loop)

## WIP Limits (single source of truth)

Two limits apply: a hard ceiling per scale and a working WIP limit per scale.

**Hard ceiling per scale** (architectural maximum — cannot exceed):

| Scale | Max active | Rationale |
|---|---|---|
| L0 Purpose | 1 | A product has one purpose |
| L1 Strategy | 3 | Multiple strategic experiments are valid (e.g., Wardley + Team Topologies + Market) |
| L2 Opportunity | 5 | OST exploration benefits from breadth |
| L3 Solution | 5 | Multiple solution candidates per opportunity is valid |
| L4 Delivery | 10 | Hard ceiling — never exceed even briefly |
| L5 Market | 3 | Multiple launch tiers can run in parallel |

**Working WIP limit per scale** (recommended for healthy flow — exceed only with explicit rationale):

| Scale | Working WIP | Rationale |
|---|---|---|
| L0 Purpose | 1 | Always 1 |
| L1 Strategy | 1 | Focus one strategic bet at a time |
| L2 Opportunity | 2 | Explore at most 2 opportunities concurrently |
| L3 Solution | 2 | Compare at most 2 solution candidates concurrently |
| L4 Delivery | 2 | Maximum 2 active L4 delivery diamonds. If both are blocked, resolve blockers before starting a third. Prevents context-switching overhead. |
| L5 Market | 1 | One launch at a time |

**Why two limits**: the hard ceiling prevents architectural collapse; the working WIP enforces healthy flow. Working WIP can be temporarily exceeded under documented exceptions (e.g., a hotfix L4 alongside an in-progress feature L4), but the hard ceiling never moves.

## Regression Rules

When evidence invalidates a higher-level assumption, regress:

- If L4 Delivery reveals the L3 Solution is wrong -> regress to L3 Develop
- If L3 prototyping reveals the L2 Opportunity is misframed -> regress to L2 Define
- If L2 research reveals the L1 Strategy is flawed -> regress to L1 Define
- If L5 Market feedback reveals the L2 Opportunity was wrong -> spawn new L2 diamond with market evidence

**Regression triggers** (what signals the need to go back):
- User testing contradicts value assumption (Cagan four risks)
- Metrics don't move after delivery (North Star input metrics flat)
- Market feedback contradicts positioning (Lauchengco win/loss)
- Security incident reveals design flaw (OWASP)
- Assumption test fails after delivery (Torres)

**Regression protocol:**
1. Document what was learned in `.claude/memory/product-journal.md`
2. Archive, do not delete, the invalidated diamond's artifacts in canvas
3. Mark the diamond's confidence as decreased with evidence citation
4. Re-enter the parent diamond at the appropriate phase (usually Define or Develop)
5. Update all affected canvas files with the new evidence
6. Log the regression decision in `.claude/harness/decision-log.md`
7. Never treat regression as failure -- it is the system working correctly

**Anti-pattern: Regression Avoidance** -- Refusing to regress because of sunk cost. If evidence says the assumption is wrong, the evidence wins. See `.claude/harness/anti-patterns.md`.

## Smooth Flow

Optimize for flow across diamonds:

- **WIP limits**: Per the WIP table above. Working WIP is 1-2 per scale; hard ceiling is higher (see WIP Limits section). When in doubt, focus.
- **Pull, don't push**: Start new diamonds only when capacity allows.
- **Small batches**: Prefer many small diamonds over few large ones.
- **Unblock first**: If a diamond is blocked, resolve the blocker before starting new work.
- **Minimize handoffs**: Same agent/team should own a diamond from Discover through Deliver when possible.
- **Scope flexing with MoSCoW (DSDM)**: When a delivery timebox is exceeded, flex scope — cut Could/Won't items before compromising Must/Should. Never cut quality to meet a deadline; cut scope instead. See `/gist-plan` for MoSCoW tagging of steps.

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

## Diamond Lifecycle Management

### Diamond States
- **active**: Currently being worked on or recently progressed
- **blocked**: Waiting on dependency, evidence, or decision (document the blocker)
- **archived**: Completed or deliberately paused. Canvas data preserved. Removed from active tracking.
- **killed**: Abandoned with documented reason. Canvas data preserved with "killed" marker.

### Stale Diamond Detection
A diamond is stale when:
- No progress for 30+ days without a documented blocker
- Phase hasn't changed in 2+ weeks without documented reason
- Its children are all complete but the parent hasn't progressed

### Cleanup Process
1. Run `/diamond-assess` to identify stale diamonds
2. For each stale diamond: decide to continue, archive, or kill
3. **Archive**: Move to `archived_diamonds` section in active.yml. Canvas data stays.
4. **Kill**: Remove from active.yml. Log reason in decision-log.md. Canvas data stays with "killed" note.
5. **Never delete canvas artifacts** -- they're learning, even from killed work

See `.claude/orchestration/operations.md` for full maintenance schedules.

## Human Actions at Phase Transitions

Each diamond transition involves both agent and human actions. The agent executes skills and checks gates. The human participates through these actions (from AI Interaction Atlas's 23 human action primitives):

| Transition | Human Actions | Agent Actions |
|------------|--------------|---------------|
| → Discover | **Provide-evidence**: share context, domain knowledge, existing research | Run /interview, /user-interview, /bias-check |
| Discover → Define | **Validate**: confirm findings match reality. **Correct**: fix misinterpretations | Run /diamond-progress, /ost-builder |
| Define → Develop | **Approve**: accept problem framing. **Prioritize**: select which opportunities to pursue | Run /ice-score, /gist-plan |
| Develop → Deliver | **Delegate**: hand off implementation decisions. **Review**: check solution design | Run /preflight, /delivery-bootstrap |
| Deliver → Complete | **Accept**: confirm deliverable meets standards. **Escalate**: flag issues for re-work | Run /diamond-progress, /definition-of-done |
| Regression (any) | **Override**: force regression with evidence. **Provide-evidence**: explain what changed | Run /diamond-progress (backward) |

**Key principle**: The human actions column defines what the framework EXPECTS from the human at each point. If the human is not performing these actions, the Cognitive Offloading Loop anti-pattern may be emerging.

*Source: AI Interaction Atlas (23 human actions), adapted for Mycelium's diamond model*

## Relationship to Other Methodologies

- **Disciplined Agile (DA)**: Mycelium's Cynefin-based domain routing + canvas-guidance project type classification IS DA's "Choose Your WoW" implemented for agentic development. The diamond engine adapts method to context, which is the core DA principle.
- **Feature-Driven Development (FDD)**: FDD's five processes (develop model, build feature list, plan by feature, design by feature, build by feature) map directly to diamond phases. Already covered by the diamond engine.
- **Kanban WIP Limits**: See the WIP Limits section above for the canonical table. The L4 working limit (2) is the most-cited example because L4 delivery work has the highest context-switching cost.
