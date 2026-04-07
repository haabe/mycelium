# Mycelium: Theory-Guided Agentic Product Development

*Version 0.4.0 -- Canvas-guided, theory-gated, self-learning, feedback-driven.*

Mycelium is a harnessing system for AI-assisted product development. Like nature's mycelium network, it connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

## How This System Works

Mycelium guides product development through **fractal diamonds** -- recursive Discover/Define/Develop/Deliver cycles that operate at every scale, from defining your organization's purpose down to implementing individual features. Each diamond is theory-guided, evidence-gated, and self-correcting.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Communication Rules

**Always communicate in plain language first, technical details second.** Use `.claude/engine/status-translations.md` to translate diamond states.

- Say "Discovering what problems to solve" not "L2 Opportunity Discover phase"
- Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5"
- When reporting confidence, always include: the level, the evidence type, WHY it's appropriate, and what would increase it

**Always suggest relevant skills at transitions.** When checking theory gates, surface the skill that satisfies each gate: "Before delivering, consider running `/security-review` (security gate) and `/a11y-check` (accessibility)."

**Always offer to capture learnings after each diamond phase.** After completing a phase, prompt: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."

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
| Security | Has threat modeling been done? | OWASP (STRIDE) |
| Privacy | Has privacy been assessed? Data minimized? | Cavoukian (PbD), GDPR |
| BVSSH | Does this align with Better, Value, Sooner, Safer, Happier? | Smart |
| Service Quality | Do Downe's 15 principles pass? | Downe (Good Services) |
| DORA | Are delivery metrics healthy? | Forsgren (Accelerate) |
| Corrections | Have past mistakes been reviewed? | Mycelium self-learning |
| Regulatory | Has EU AI Act risk classification been assessed? | EU AI Act (2024/1689) |

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

### Feedback Loops (`.claude/engine/feedback-loops.md`)
Four-speed feedback system based on Gene Kim's Three Ways, Argyris's double-loop learning, and Meadows's leverage points:
- **Loop 1 (Immediate)**: Reflexion, secret detection, corrections matching -- seconds
- **Loop 2 (Incremental)**: Phase learnings, DORA metrics, retrospectives -- hours/days
- **Loop 3 (Strategic)**: BVSSH health, North Star trajectory, Wardley refresh -- weekly/monthly
- **Loop 4 (Transformative)**: Eval benchmarks, prompt optimization, system improvement -- quarterly

Run `/feedback-review` to check health across all loops. SessionStart and Stop hooks monitor for overdue strategic checks.

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

## Operations & Maintenance

- **Day-to-day**: `.claude/orchestration/operations.md` -- Session resumption, canvas maintenance, diamond lifecycle, memory pruning, weekly/monthly/quarterly routines
- **Escape hatch**: `.claude/orchestration/escape-hatch.md` -- When and how to legitimately bypass the full process (production incidents, hotfixes, trivial changes). Must be documented and paid back.

## Agent Orchestration

For parallel OST exploration (multiple solutions tested simultaneously):
- Lead agent manages diamond state and canvas
- Worker agents (subagents/Agent Teams) each explore one solution branch
- Workers get worktree isolation (their own branch)
- Workers read canvas (read-only) for alignment
- Lead agent collects results, updates ICE scores, picks winners

See `.claude/orchestration/agent-teams.md` for patterns.

## Skills Reference

Invoke skills with `/skill-name`. All 32 skills:

### Onboarding & Assessment
| Skill | When to Use |
|-------|------------|
| `/interview` | Onboarding: establish purpose, vision, North Star, project type |
| `/diamond-assess` | Check current state, get recommended next action (plain language) |
| `/diamond-progress` | Move a diamond forward (runs all theory gates, suggests skills) |

### Discovery Skills
| Skill | When to Use |
|-------|------------|
| `/user-interview` | Torres-style story-based interviews with bias mitigation |
| `/ost-builder` | Build or update Opportunity Solution Tree from research |
| `/jtbd-map` | Map Jobs to be Done (functional, emotional, social) |
| `/assumption-test` | Design smallest viable test to validate an assumption |
| `/cynefin-classify` | Classify problem domain (Clear/Complicated/Complex/Chaotic) |
| `/wardley-map` | Create or update Wardley Map of value chain |
| `/ice-score` | Score and prioritize ideas with confidence meter |
| `/gist-plan` | GIST planning: goals, ideas, steps, tasks |

### Quality & Governance Skills
| Skill | When to Use |
|-------|------------|
| `/bias-check` | Review cognitive biases before research/decisions |
| `/devils-advocate` | Systematically challenge assumptions before major decisions |
| `/bvssh-check` | Holistic health evaluation (Better, Value, Sooner, Safer, Happier) |
| `/service-check` | Evaluate against Downe's 15 Good Services principles |
| `/threat-model` | STRIDE threat modeling for a component/solution |
| `/privacy-check` | Privacy by Design / GDPR assessment |
| `/security-review` | OWASP secure design review for code and architecture |
| `/a11y-check` | Accessibility audit (WCAG 2.1 AA) |

### Delivery Skills
| Skill | When to Use |
|-------|------------|
| `/delivery-bootstrap` | Auto-detect tech stack and set up delivery tooling |
| `/preflight` | Pre-code validation checklist |
| `/reflexion` | Self-correcting implementation loop (implement/validate/critique/retry) |
| `/definition-of-done` | Verify increment satisfies all DoD criteria |
| `/dora-check` | Delivery performance metrics assessment |
| `/retrospective` | Post-delivery learning capture |

### Market & Go-to-Market Skills
| Skill | When to Use |
|-------|------------|
| `/launch-tier` | Classify releases into tiers and plan go-to-market |
| `/team-shape` | Team Topologies assessment (cognitive load, interaction modes) |

### Canvas & Orchestration Skills
| Skill | When to Use |
|-------|------------|
| `/canvas-update` | Update canvas sections with new evidence |
| `/canvas-sync` | Synchronize canvas state across team sessions via git |
| `/fan-out` | Parallel agent orchestration for OST exploration |

### Self-Improvement Skills
| Skill | When to Use |
|-------|------------|
| `/feedback-review` | Aggregate all feedback loop signals, check health, flag regressions |
| `/eval-runner` | Run benchmark scenarios to measure agent effectiveness |
| `/prompt-optimizer` | A/B test instruction changes against eval baselines |

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
