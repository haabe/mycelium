# Mycelium: Theory-Guided Agentic Product Development

Mycelium is a harnessing system for AI-assisted product development. Like nature's mycelium network, it connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

## How This System Works

Mycelium guides product development through **fractal diamonds** -- recursive Discover/Define/Develop/Deliver cycles that operate at every scale, from defining your organization's purpose down to implementing individual features. Each diamond is theory-guided, evidence-gated, and self-correcting.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Mandatory Pre-Task Protocol

Before ANY implementation task:
1. Read `.claude/memory/corrections.md` for relevant past mistakes
2. Read `.claude/harness/guardrails.md` for hard constraints
3. Identify which diamond you are operating within (check `.claude/diamonds/active.yml`)
4. Load the appropriate domain context (`.claude/domains/{discovery|delivery|quality}/CLAUDE.md`)

## The Diamond Engine

### Diamond Scales (L0-L5)

| Scale | Focus | Primary Theories | Canvas Files |
|-------|-------|-----------------|--------------|
| L0: Purpose | Why we exist | Sinek (Golden Circle), JTBD (Christensen) | `canvas/purpose.yml`, `canvas/jobs-to-be-done.yml` |
| L1: Strategy | Where to play | Wardley Mapping, North Star, Team Topologies (Skelton) | `canvas/landscape.yml`, `canvas/north-star.yml`, `canvas/team-shape.yml` |
| L2: Opportunity | What to solve | Torres (CDH/OST), Allen (User Needs Mapping), Cynefin | `canvas/opportunities.yml`, `canvas/user-needs.yml` |
| L3: Solution | How to solve it | Gilad (GIST/ICE), Cagan (Inspired), Downe (Good Services) | `canvas/gist.yml`, `canvas/services.yml` |
| L4: Delivery | Build and ship | Forsgren (DORA), OWASP, DRY/KISS/YAGNI/SOLID/SoC | `canvas/dora-metrics.yml`, `canvas/threat-model.yml` |
| L5: Market | Reach users | Lauchengco (Loved), Shotton (behavioral science) | `canvas/go-to-market.yml`, `canvas/trust-signals.yml` |

### Diamond Phases (within each scale)

Each diamond has four phases. The transition between phases is **gated by theory checks**, not just confidence scores.

1. **Discover** (diverge) -- Explore broadly. Gather evidence. Challenge assumptions.
2. **Define** (converge) -- Synthesize discoveries. Narrow focus. Frame the problem/opportunity.
3. **Develop** (diverge) -- Generate multiple solutions. Ideate. Prototype.
4. **Deliver** (converge) -- Validate, build, ship, measure.

See `.claude/engine/diamond-rules.md` for full transition rules.

### Fractal Property

Diamonds spawn child diamonds when complexity requires it:
- L0 spawns L1 when purpose is defined
- L1 spawns L2 when strategic landscape is mapped
- L2 spawns L3 when opportunities have sufficient evidence
- L3 spawns L4 when solutions pass confidence threshold
- L4 can spawn sub-L4 diamonds for complex features
- L5 spawns L2 when market feedback reveals new opportunities

**Smooth flow**: Parent diamonds don't stop when children spawn. L2 can continue discovering while L3 works on a previously-identified opportunity.

### Diamond Regression

If delivery reveals a bad assumption, the diamond **regresses** back to its discovery phase with new evidence. This is not failure -- it's the system working correctly.

## Theory Gates (Decision Checkpoints)

Every diamond transition must pass ALL applicable gates. See `.claude/engine/theory-gates.md` for complete rules.

**You cannot progress a diamond by saying "I'm confident enough." You must demonstrate evidence that satisfies each gate.**

### Gate Categories

| Gate | What It Checks | Source Theory |
|------|---------------|---------------|
| Evidence | Is there research-backed evidence? Multiple sources? | Torres (CDH), Gilad (Evidence Guided) |
| Four Risks | Have value, usability, feasibility, viability been assessed? | Cagan (Inspired) |
| JTBD | Have emotional and social dimensions been mapped, not just functional? | Christensen |
| Cynefin | Is the domain classified? Is the method appropriate? | Snowden |
| Bias Check | Was research designed to mitigate cognitive biases? | Shotton, Kahneman |
| Security | Has threat modeling been done? Privacy assessed? | OWASP (STRIDE), GDPR (PbD) |
| BVSSH | Does this align with Better, Value, Sooner, Safer, Happier? | Smart |
| Service Quality | Do Downe's 15 principles pass? | Downe (Good Services) |
| DORA | Are delivery metrics healthy? | Forsgren (Accelerate) |
| Corrections | Have past mistakes been reviewed? | Mycelium self-learning |

## The Canvas (Source of Truth)

All product knowledge lives in `.claude/canvas/*.yml`. These files are:
- The **single source of truth** for the product's state
- Committed to git (they are documentation-as-code)
- Updated through evidence, not assumption
- Readable by any team member starting a new session

**Never make a significant decision without first checking and updating the relevant canvas file.**

## Harnessing System

### Guardrails (`.claude/harness/guardrails.md`)
Hard constraints that the agent MUST NEVER violate. These override confidence scores, user requests, and agent judgment. Read them before every task.

### Anti-Patterns (`.claude/harness/anti-patterns.md`)
Known failure modes with detection rules. If you catch yourself falling into one, stop and self-correct.

### Cognitive Biases (`.claude/harness/cognitive-biases.md`)
Per-stage bias checklist. Review before conducting research, making decisions, or designing solutions.

### Security & Trust (`.claude/harness/security-trust.md`)
Per-stage security requirements. Security is designed in, not bolted on.

### Engineering Principles (`.claude/harness/engineering-principles.md`)
DRY, KISS, YAGNI, SoC, SOLID, LoD -- explicit rules for all delivery work.

## Self-Learning System

### Corrections Memory (`.claude/memory/corrections.md`)
Accumulated learning from mistakes. **Read before every implementation task.** Apply prevention rules proactively.

### Pattern Library (`.claude/memory/patterns.md`)
Successful patterns to reuse. Captured from delivery and discovery successes.

### Decision Log (`.claude/harness/decision-log.md`)
Every significant decision with: context, alternatives considered, theory that guided it, evidence, confidence level.

### Reflexion Loop
When implementing (delivery phase):
1. Implement the solution
2. Run validation suite
3. If fails: structured self-critique (what failed, why, root cause, fix)
4. Apply fix, retry (max 3 iterations)
5. On success: capture patterns/corrections if learned something new
6. On failure after 3: report to user with full analysis

See `.claude/skills/reflexion/SKILL.md` for complete workflow.

### Eval Benchmarks (`.claude/evals/`)
Periodic self-assessment against scenarios. Measures pass rate, iterations needed, time.

### Prompt Optimization (`.claude/optimization/`)
A/B testing of Mycelium instruction changes against eval baselines.

## Domain Contexts

Load the appropriate context based on current diamond phase:

- **Discovery**: `.claude/domains/discovery/CLAUDE.md` -- Torres-style interviewing, OST construction, bias-aware research
- **Delivery**: `.claude/domains/delivery/CLAUDE.md` -- Agile/DevOps practices, clean code, security, accessibility, DORA metrics
- **Quality**: `.claude/domains/quality/CLAUDE.md` -- Always-active overlay: validation, accessibility, security, service principles

## JiT Tooling

Mycelium is **language-agnostic**. When a delivery diamond begins:
1. Auto-detect the tech stack from project files
2. Generate stack-appropriate validation commands, linters, test runners
3. Configure security scanning for the detected stack
4. The agent asks the user to confirm/adjust before proceeding

See `.claude/jit-tooling/detector.md` for detection rules.

## Usage Modes

### Solo Developer
- You interact directly with the agent
- Canvas is your shared memory with the agent
- Decision log is your cross-session continuity

### Team
- Canvas files are committed to git -- they ARE the team's product documentation
- Any team member's agent session reads the same canvas
- Canvas updates are PR-reviewed like code
- Use Agent Teams or worktrees for parallel delivery work

See `.claude/orchestration/modes.md` for complete patterns.

## Agent Orchestration

For parallel OST exploration (multiple solutions tested simultaneously):
- Lead agent manages diamond state and canvas
- Worker agents (subagents/Agent Teams) each explore one solution branch
- Workers get worktree isolation (their own branch)
- Workers read canvas (read-only) for alignment
- Lead agent collects results, updates ICE scores, picks winners

See `.claude/orchestration/agent-teams.md` for patterns.

## Skills Reference

Invoke skills with `/skill-name`. Key skills:

| Skill | When to Use |
|-------|------------|
| `/interview` | Onboarding: establish purpose, vision, North Star |
| `/diamond-assess` | Check current state, get recommended next action |
| `/diamond-progress` | Move a diamond forward (runs all theory gates) |
| `/cynefin-classify` | Classify a problem's domain (Clear/Complicated/Complex/Chaotic) |
| `/ost-builder` | Build or update Opportunity Solution Tree |
| `/ice-score` | Score and prioritize ideas with confidence meter |
| `/bias-check` | Review cognitive biases before research/decisions |
| `/threat-model` | STRIDE threat modeling for a component/solution |
| `/reflexion` | Self-correcting implementation loop |
| `/preflight` | Pre-code validation checklist |
| `/bvssh-check` | Holistic health evaluation (Better, Value, Sooner, Safer, Happier) |
| `/service-check` | Evaluate against Downe's 15 principles |
| `/dora-check` | Delivery performance metrics assessment |
| `/delivery-bootstrap` | Auto-detect tech stack and set up delivery tooling |
| `/definition-of-done` | Verify increment satisfies all DoD criteria |
| `/a11y-check` | Accessibility audit |
| `/devils-advocate` | Systematically challenge current assumptions |
| `/retrospective` | Post-delivery learning capture |

## Getting Started

If the canvas is empty (new project), start with:
```
/interview
```

If the canvas is populated (continuing work), start with:
```
/diamond-assess
```

The system will guide you from there.
