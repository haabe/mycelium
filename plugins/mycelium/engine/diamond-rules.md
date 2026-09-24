# Diamond Rules

Diamonds are the core workflow unit in Mycelium. Each diamond represents a cycle of divergent and convergent thinking applied to a problem at a specific scale.

## The Four Phases

Every diamond passes through four phases, based on the **Double Diamond** model (Design Council, 2004). The Design Council evolved this into a broader "Framework for Innovation" (2019) adding Design Principles, Methods Bank, and Culture layers. For Complex-domain problems (Cynefin), consider the Design Council's Systemic Design Framework:

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
| **L3** | Solution | How to solve it | Gilad (GIST) / Ellis (ICE), Cagan (Inspired), Downe (Good Services) | Days-weeks | "An AI agent that enforces theory gates" |
| **L4** | Delivery | Build and ship | Forsgren (DORA), OWASP, DRY/KISS/YAGNI/SOLID/SoC | Hours-days | "Implement bias-check skill with tests" |
| **L5** | Market | Reach users | Lauchengco (Loved), Shotton (behavioral science) | Days-weeks | "Position and launch the product" |

**Note on L4 sub-diamonds**: Complex features within L4 can spawn their own sub-L4 diamonds (e.g., a large feature broken into independently deliverable slices). These are still L4 scale but nested. Atomic tasks within delivery do NOT need their own diamond -- they are simply tasks within the L4 Deliver phase.

## What each level RECURS ON — and why only two scales have a catalogue door

**Read this before proposing a catalogue door for L0, L1, L4 or L5.** Added v0.242.3 after an agent
enumerated the doors, found two, and filed the asymmetry as a probable defect — twice, in one
session, the second time after a blind reviewer had already corrected the first attempt. The
reasoning existed; it was not on this page.

A level's unit is one diverge→converge cycle that **emits** something and **recurs** on something.
The shape is uniform; the trigger is not, and the trigger is what decides whether a door is possible.

| scale | the inquiry emits | recurs on | entered by |
|---|---|---|---|
| L0 | a WHY (once), and Just Causes (plural) | drift | founding; there is one purpose |
| L1 | triggers | **a decision** | an event offer when a strategic decision arises: `/wardley-map` after gameplay, or `/diamond-progress` when an L0 enters define (v0.243.0) |
| L2 | a validated or killed opportunity | **continuously** | parent spawn **or the catalogue** |
| L3 | a build-or-kill verdict | **per candidate** | parent spawn **or the catalogue** |
| L4 | an increment; a closed session | **per increment** | an event offer when an increment is ready to build: `/preflight` passing on a solution (v0.243.0) |
| L5 | a launch | **a release categorised as a major launch** | the L4→L5 spawn (v0.232.0) |

**THE RULE THAT FALLS OUT OF IT: a catalogue door is possible only where a level recurs on a PILE.**
L2 recurs continuously and L3 per candidate — both are drawn from an enumerable set of project
records, so `/ost-builder` and `/ice-score` can offer the door. L1, L4 and L5 recur on **events** —
a decision, an increment, a categorisation. An event has no queue to select from, so there is
nothing for a door to open ON, and building one would mean inventing a record type the level does
not produce.

**BUT EVERY SCALE MUST BE ENTERABLE, AND THAT IS THE HIGHER RULE (v0.243.0).** The founder's
principle, stated when this page was found to leave L1 and L4 unreachable: *"If there's no way to
progress into and out of all or any of the diamonds, the model is wrong."* No pile means no
catalogue door; it does not mean no entrance. **A scale that recurs on an event is entered by an
EVENT OFFER**: the skill that is running when the event happens offers to open the cycle, names
what the cycle is on, and records one line if it is declined. L1's event is a strategic decision
(`/wardley-map`, and `/diamond-progress` when an L0 enters define); L4's is an increment ready to
build (`/preflight`); L5's is a release categorised as a major launch (`/launch-tier`). Until
v0.243.0 L1 and L4 had only a sentence saying they would be spawned, and no skill that did it:
in dogfood full-ladder runs 6 to 20 neither was ever created, including three runs in which L0
reached define. **A route that is documented and never fires is no route.**

**Every entrance in the table passes through its scale's entry lock** (Spawning Rules, Entry locks,
v0.245.0): a door or event offer is made only once the parent has established what the child builds
on. Being enterable and being locked are both required; v0.243.0 got the first and dropped the second.

**Every product has some kind of delivery**, so L4 is never optional. Its form follows the product
type, as the Evidence gate's L4 rows already say: tested code for software, reviewed and accessible
content, passing evals for an AI tool, a documented and repeatable step for a service.

**L1 SPECIFICALLY, because its files DO carry id-bearing records and that is the trap.**
`landscape.yml#components[]`, `landscape.yml#climatic_predictions[]` and `doctrine.yml#doctrine[]`
all have ids, and none of them is a proposal awaiting a decision to work on it. Wardley separates
them himself: doctrine is *"universally applicable... Don't pick and choose, apply them all"* —
a class you apply in full, not a menu; climate *"will apply to you regardless of your choice"*, so
it has no producer and **must not be given a diamond**, which would invent a maker for something the
world makes. Gameplay is the one Wardley output that IS a proposal — and he states the gameplay and
doctrine sets are **open**, so it is a library you choose FROM, not a project backlog you draw DOWN.

**L4 SPECIFICALLY.** No canvas schema carries an id-bearing record for a delivery increment:
`gist.yml#steps[]` and `#current_tasks[]` have no `id`, and GIST belongs to L3 in any case. L4's own
theories supply no catalogue — DORA measures a continuous stream, OWASP supplies checks, SOLID
supplies design rules. An increment is decomposed from the solution above it, not selected from a
pile. **What L4 was missing was a promotion trigger, not a door**: the `four_risks` gate fired and
nothing consumed its result to open the L4. Closed in v0.243.0 by the event offer in `/preflight`,
which is where `leaf-lifecycle.md` Phase 8 had always said the delivery diamond is spawned.

*Sources: Wardley (doctrine/climate/gameplay as quoted); Cagan (four risks as the discovery exit);
Lauchengco (release categorisation); Forsgren (DORA as stream measurement); Rother (target before
work). The per-level table is the consolidated reading recorded by a consumer project after reading
the books, three adversarial rounds and founder correction.*

## Spawning Rules

**A record and a cycle are different objects (v0.217.0).** An opportunity in `opportunities.yml` is a record; an L2 diamond is a cycle of work on it. Scoring, evidence and a resolving `rolls_up_to` make a good record and open nothing. A cycle is opened by a spawn from the parent (below) OR from the catalogue: `/ost-builder` offers an L2 on a scored, evidence-backed opportunity and `/ice-score` offers an L3 on the highest-ranked scored leaf. Both doors open only when the scale's entry lock holds.

### Entry locks: each scale opens on what its parent has established (v0.245.0)

**Two questions, never answered with each other.** ENTRY: what must exist above a child before it opens. SPEED: once open, how fast it moves. The founder's model is a dependency tree — *"It might be unwise to build a strategy unless you have a purpose. It would be unwise to start looking into opportunities without knowing who to reach doing what (L0+L1). And so on."* — and the speed ruling of v0.243.0 (*"a child of the same L can progress faster than the parent"*) is about SPEED only. Between v0.217.0 and v0.243.0 every door offered its cycle regardless of the parent, which answered ENTRY with the speed ruling: every scale could open at once, and nothing stopped a user building the wrong thing straight away. An end-to-end dogfood run shipped a release over 31 commits under an L0 in discover.

| Child opens | when the parent has established | Read from | Source |
|---|---|---|---|
| **L1** Strategy | a stated purpose: who it is for and why (provisional; L1 may revise it) | `purpose.yml` `why` (3+ words) and `who` (or `target_users`) | Wardley p12; Cagan, *Empowered* p113-118 |
| **L2** Opportunity | the L1 lock, plus a desired outcome: who to reach, doing what. A learning goal is enough to start | `opportunities.yml` `desired_outcome.metric` (or a `desired_outcomes[].metric`) | Torres, *CDH* p27, p44-47 |
| **L3** Solution | the L2 lock, plus a chosen target opportunity with evidence behind it (anecdotal or better, with the source it came from). The choice is reversible | the diamond's `object_ref` (or its L2 parent's) resolves to an opportunity with `provenance.evidence_type` and `evidence_sources`; at entry it must be open and, with several roots, name one in `rolls_up_to` | Torres p101-107; Gilad, *Testing Product Ideas* p9 |
| **L4** Delivery | the L3 lock on the L3 it delivers, plus that L3's evidence at **medium confidence or higher**: `data-supported`, `test-validated` or `launch-validated`. The bar rises with cost and risk | the L4's `parent` (or the L3 with the same `object_ref`) and its `evidence_type` | Gilad, *Evidence-Guided* p158-159; *ICE Done Right* p14 |
| **L5** Market | the L4 lock on its parent L4, that L4 shipped, and launch data: usage, feedback or movement in the target metric | the L5's `parent`, and `launch_data` on that L4 or the L5 | Gilad, *Evidence-Guided* p123 |

**Code sits inside the chain.** New source files are written under an open L3 (build to learn), L4 or L5 whose lock holds — the discovery gate's second stage reads it. An L3 opened straight after `/mycelium:start` does not qualify: the interview leaves a purpose and nothing else.

**Artefacts at L1-L3, a confidence band only at L4 and L5, and why.** Every source read orders the levels top-down (Wardley p12, Cagan p113-118, Torres p27, Gilad *Evidence-Guided* p43), and none locks the upper levels on a score: Torres works the tree "bottom-up … evolving the entire tree at once" (p35) and has strategy emerge from discovery decisions (p101); Wardley's purpose changes as you act (p32). Gilad's numbers are for ideas only, and he calls the ICE scores themselves "meaningless — they're just a way to compare ideas" (*ICE Done Right* p4). So the lock at L1-L3 is that the parent's artefact EXISTS, and the only numeric lock is the Confidence band where Gilad puts it, before delivery and launch. ICE ranks; it never unlocks.

**The locks are mechanical.** `scripts/scale_locks.py` is the one place they are defined. `hooks/scale-lock-gate.sh` refuses a write to `diamonds/active.yml` that OPENS a diamond (a new id, a rescaled one, or one moved back into the active list) whose lock does not hold, naming what is missing; the discovery gate refuses new source files outside a held chain; `scale_locks.py --check` reports every open diamond (canvas-health reads it); `--can-open <scale>` answers the doors. **Override:** only the user can open a diamond past its lock, with one line per diamond in `.claude/state/scale-lock-ack`: `<id> <scale> <YYYY-MM-DD> <their own words>`, valid for that id at that scale only (guarded state: the agent writing it gets an ASK).

**Once open, a diamond moves at its own speed.** A child moves through its own transitions on its own gates and may be ahead of its parent; the parent stays active while children execute. **Findings flow upward**: a child may revise its parent (Torres p35, Wardley p32), and a parent revised under an open child marks the child for a re-check at its next `/diamond-assess`, it does not close it. **What entry means once a diamond is open:** the open-opportunity check applies at entry only, so an opportunity marked `addressed` after shipping re-locks nothing. What an open delivery cycle must still have to carry NEW source files is its chain: a purpose, an outcome, a target with evidence. **Diamonds opened before v0.245.0** are never blocked on edit, and `--check` lists any whose chain does not hold; such a diamond cannot carry new source files until the missing artefact exists or the user acks it.

**`solo_hobby` skips the L1 diamond, not the L1 lock.** With no L1 cycle, the L2 lock still needs the purpose and the desired outcome; the artefact, not the diamond, is what it reads.

**What the locks cannot do.** They check that the parent's artefact EXISTS, not that it is true: an evidence type and a source are fields an agent can write. The L3 lock therefore asks for a named source as well as a type, which makes an invented one visible in review; the truth of evidence stays with the evidence gates and the human.

Diamonds spawn child diamonds, each through its lock above:

- L0 spawns L1 when purpose is stated and a strategic question arises (the event offer: `/wardley-map`, `/diamond-progress`)
- L1 spawns L2 when the desired outcome is set and opportunities need exploration (`/ost-builder`)
- L2 spawns L3 when a target opportunity has evidence for solution design (`/ice-score`)
- L3 spawns L4 when an increment is ready to build and the L3 is at medium confidence (the event offer: `/preflight`)
- L4 can spawn sub-L4 diamonds for complex features requiring their own discovery
- **L4 spawns L5 when a release is categorised as a MAJOR LAUNCH on the project's own release scale** and launch data exists (v0.232.0, written by `/launch-tier`)
- L5 spawns L2 when market feedback reveals new opportunities (feedback loop)

**The L4→L5 edge was missing until v0.232.0, and its absence is why L5 never opened by itself.** Every
other rung had a spawn; the top one had only an exit (L5→L2) and no entry, so an L5 could be created
only by hand. The trigger is Lauchengco's, and it is mechanical rather than temporal — *"The
distinctions between a minor release and a major launch are really important... what does or doesn't
get done flows from how releases are categorized"* — so the categorisation `/launch-tier` already
makes IS the trigger. It was being made and nothing acted on it.

**Entry lock: launch data from the shipped L4** (Entry locks table above). Until v0.245.0 the L5 could
open with its entry condition "explicitly unmet", which made it the one scale whose lock was optional.
**Product/market fit is what the L5 works toward and measures** (Cagan), with Ellis's Must-Have Survey
typed on the diamond as `pmf`. **`band: not-yet-measurable` stays a first-class answer about PMF** —
below a real sample a percentage is not a percentage, and a manufactured 40% is theatre — but it is no
longer a way in: the launch data (usage, feedback, metric movement) must exist at any n. **Major launch
means the top band of YOUR scale**; a project with no release history has no scale, so it cannot
categorise and this cannot fire.

**One open L5 at a time.** L5 recurs on the market, not on the release: a second L5 for a later launch
splits one market question across two records. Add the release to the open one.

**Constraints:**
- Parent diamond remains active while children execute (smooth flow)
- Child diamond outcomes feed back into parent diamond evidence
- L5 Market feedback can trigger new L2 Opportunity diamonds (the learning loop)

## WIP Limits (single source of truth)

Two limits apply: a hard ceiling per scale and a working WIP limit per scale.

**Hard ceiling per scale** (architectural maximum — advisory, not gate-enforced):

> **Enforcement is advisory.** `/diamond-progress` surfaces these ceilings but does not currently block an over-ceiling spawn. `Gated by:` a spawn-time count-and-block gate in `/diamond-progress` (count active diamonds per scale vs ceiling, block + suggest park candidates) — not yet built. Until then the ceiling is a convention the agent and team hold, not a hard stop.

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

**Anti-pattern: Regression Avoidance** -- Refusing to regress because of sunk cost. If evidence says the assumption is wrong, the evidence wins. See `../harness/anti-patterns.md`.

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
definition_of_done: [outcome-based done-criterion, set at birth — see below]
theory_gates:
  discover_to_define: [pass | fail | pending]
  define_to_develop: [pass | fail | pending]
  develop_to_deliver: [pass | fail | pending]
  deliver_to_complete: [pass | fail | pending]
```

Update state on every significant action. State is the source of truth for what the agent should do next.

### Definition of Done (outcome bar, per diamond)

Every diamond carries an explicit, **outcome-based** `definition_of_done`, pinned at birth — *a change in human behaviour that creates value* (Seiden), not "the feature shipped." Without it the bar defaults implicitly to the harshest, least-controllable outcome, which is both wrong for validating purpose and a demotivation engine. Set it with `/mycelium:define-done` (problem-first Socratic sequence); retrofit when missing. Distinct from the per-feature agile quality checklist run by `/mycelium:definition-of-done` at Deliver→Complete.

```yaml
definition_of_done:
  outcome:   "<what changes, for WHOM — a behaviour, not a feature>"   # required; problem-first
  signal:    "<the ONE observable thing you'd see them DO>"            # required; OMTM
  kind:      leading | lagging                                        # defaulted by scale (lead-low / lag-high)
  threshold: "<a target IF one genuinely fits>"                       # OPTIONAL — numbers not mandatory
  rolls_up_to: "<parent diamond id + parent outcome>"                 # child diamonds; contribution-not-summation
  kill_criterion: { state: "...", date: "YYYY-MM-DD", premortem: "..." }   # state+date, pre-committed via pre-mortem
  provenance: { source_class, validated, captured_at }
```

The **Deliver→Complete** gate passes only when the diamond's DoD `signal` is met **OR** its `kill_criterion` (the *invalidation criterion*: state+date; the key is named for its worst reading, and each kill on the dogfood canvas states what to RETHINK, not what to abandon) fired with evidence (done-by-invalidation, routed through `dogfood-mode` + decision-log). A child is done only when its outcome **rolls up** to move the parent — contribution, not summation. Full design + evidence grades: `docs/design/definition-of-done.md`; per-scale defaults + the question sequence: `${CLAUDE_PLUGIN_ROOT}/skills/define-done/SKILL.md`.

## Diamond Lifecycle Management

### Diamond States
- **active**: Currently being worked on or recently progressed
- **blocked**: Waiting on dependency, evidence, or decision (document the blocker)
- **completed**: The Definition of Done was **met, with evidence** (`completed_at` + `dod_verdict`, written by `/diamond-progress` Step 9b into `completed_diamonds`). Canvas data preserved.
- **archived**: Work that **STOPPED without meeting its bar** — deliberately paused, superseded, or no longer tracked. Canvas data preserved. Removed from active tracking.

  *Until v0.230.0 this single state read "Completed or deliberately paused", putting two opposite outcomes in one bucket. With them merged, nothing downstream could tell work that MET its bar from work that merely stopped, so compliance with completion was unverifiable by construction — the count of finished cycles and the count of abandoned ones were the same number. `check_scale_occupancy.py` had been reading a `completed_diamonds` key that no schema defined and no skill wrote, so it counted zero completions at every scale no matter what shipped.*
- **killed**: Abandoned with documented reason. Canvas data preserved with "killed" marker.

### Stale Diamond Detection
A diamond is stale when:
- No progress for 30+ days without a documented blocker
- Phase hasn't changed in 2+ weeks without documented reason
- Its children are all complete but the parent hasn't progressed

### Cleanup Process
1. Run `/diamond-assess` to identify stale diamonds
2. For each stale diamond: decide to continue, complete, archive, or kill
3. **Complete**: DoD met — move to `completed_diamonds` with `completed_at` and a `dod_verdict` carrying `signal_observed` and `verified_by`. The schema rejects a completion without them, so this cannot be asserted in passing.
4. **Archive**: Stopped WITHOUT meeting the DoD — move to `archived_diamonds` in active.yml. Canvas data stays. Choosing archive over complete is a real answer; reaching for it because the verdict is awkward to write is the thing the split exists to expose.
5. **Kill**: Remove from active.yml. Log reason in decision-log.md. Canvas data stays with "killed" note.
6. **Never delete canvas artifacts** -- they're learning, even from killed work

See `../orchestration/operations.md` for full maintenance schedules.

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

**What is delegable at Develop → Deliver** (the **Delegate**/**Review** seam above): not "hand off everything." Implementation decisions are delegated to the agent *up to the consequence line* — reversible, contained work is the agent's; the deploy decision, destructive/shared-state ops, and any no-standing tradeoff stay the human's. The authority map and the consequence rule (effective-reversibility × aggregate-blast-radius) live in `${CLAUDE_PLUGIN_ROOT}/harness/delegation-authority.md`. A human who delegates *past* that line is in the Cognitive Offloading Loop; an agent that acts *past* it violates behavioral-contract N9/N10.

*Source: AI Interaction Atlas (23 human actions), adapted for Mycelium's diamond model*

## Relationship to Other Methodologies

- **Disciplined Agile (DA)**: Mycelium's Cynefin-based domain routing + canvas-guidance project type classification IS DA's "Choose Your WoW" implemented for agentic development. The diamond engine adapts method to context, which is the core DA principle.
- **Feature-Driven Development (FDD)**: FDD's five processes (develop model, build feature list, plan by feature, design by feature, build by feature) map directly to diamond phases. Already covered by the diamond engine.
- **Kanban WIP Limits**: See the WIP Limits section above for the canonical table. The L4 working limit (2) is the most-cited example because L4 delivery work has the highest context-switching cost.
