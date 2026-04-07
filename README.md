# Mycelium

**Theory-guided agentic product development for Claude Code.**

Like nature's mycelium network -- the invisible intelligence that connects trees, shares nutrients, adapts to conditions, and makes the whole forest ecosystem stronger -- Mycelium connects product development theories, shares learning across sessions, adapts to any tech stack, and makes your product development practice stronger.

Mycelium is an open-source harnessing system that guides AI agents through proper incremental product development using best practices from 17+ established frameworks and books. It prevents the agent from going haywire by enforcing theory-guided decision gates, reflexion loops, cognitive bias checks, and quality guardrails at every stage.

## The Problem

AI coding agents are powerful but unguided. They'll jump from an idea to code without discovery, skip security considerations, ignore accessibility, repeat past mistakes, and inflate their own confidence. Mycelium solves this by encoding decades of product development wisdom into a structured agent harness.

## Quick Start

### New Project

Click **"Use this template"** on GitHub to create a new repo with Mycelium pre-installed, or:

```bash
npx degit haabe/mycelium my-project
cd my-project
```

Then start Claude Code and run:
```
/interview
```

### Existing Project

Copy Mycelium into your project:

```bash
# From your project root:
npx degit haabe/mycelium/CLAUDE.md ./CLAUDE.md
npx degit haabe/mycelium/.claude ./.claude
```

Then start Claude Code and run:
```
/interview
```

The interview skill will guide you through establishing your product's purpose, vision, North Star metric, and strategic landscape.

## How It Works

### Fractal Diamonds

Mycelium guides development through **fractal diamonds** -- recursive Discover/Define/Develop/Deliver cycles that operate at every scale:

```
L0: Purpose     "Why do we exist?"           (Sinek, Christensen)
L1: Strategy    "Where do we play?"          (Wardley, North Star, Skelton)
L2: Opportunity "What problem to solve?"     (Torres, Allen, Cynefin)
L3: Solution    "How to solve it?"           (Gilad, Cagan, Downe)
L4: Delivery    "Build and ship"             (Forsgren, OWASP, SOLID)
L5: Market      "Reach users"               (Lauchengco, Shotton)
```

Each diamond has four phases: **Discover** (diverge) -> **Define** (converge) -> **Develop** (diverge) -> **Deliver** (converge).

Diamonds spawn child diamonds when complexity requires it. Parent diamonds continue while children execute. If delivery reveals a bad assumption, the diamond **regresses** back with new evidence. This creates smooth flow from idea to delivery without artificial phase breaks.

### Theory Gates

Every diamond transition must pass **theory gates** -- not just a confidence score, but evidence checks grounded in specific frameworks:

| Gate | What It Checks | Source |
|------|---------------|--------|
| Evidence | Research-backed? Multiple sources? | Torres, Gilad |
| Four Risks | Value, usability, feasibility, viability assessed? | Cagan |
| JTBD | Emotional and social dimensions mapped? | Christensen |
| Cynefin | Domain classified? Method appropriate? | Snowden |
| Bias Check | Research designed to mitigate cognitive biases? | Shotton, Kahneman |
| Security | Threat model updated? Privacy assessed? | OWASP, GDPR |
| BVSSH | Aligned with Better, Value, Sooner, Safer, Happier? | Smart |
| Service Quality | Downe's 15 principles checked? | Downe |
| DORA | Delivery metrics healthy? | Forsgren |
| Corrections | Past mistakes reviewed? | Mycelium self-learning |

If ANY gate fails, the agent reports which gates failed, cites the theory, and recommends the smallest action to satisfy each -- but does NOT proceed.

### The Canvas (Source of Truth)

All product knowledge lives in `.claude/canvas/*.yml` -- 15 structured YAML files that serve as the single source of truth:

| Canvas File | What It Captures | Source Theory |
|-------------|-----------------|---------------|
| `purpose.yml` | Why/How/What, ethical boundaries | Sinek |
| `north-star.yml` | North Star metric + input metrics | North Star Framework |
| `bvssh-health.yml` | Better/Value/Sooner/Safer/Happier | Smart |
| `landscape.yml` | Wardley Map components + evolution | Wardley |
| `team-shape.yml` | Team types, cognitive load, interactions | Skelton |
| `opportunities.yml` | Opportunity Solution Tree | Torres |
| `user-needs.yml` | User needs map (functional/emotional/social) | Allen |
| `gist.yml` | Goals, Ideas, Steps, Tasks | Gilad |
| `services.yml` | 15 Good Services principles assessment | Downe |
| `go-to-market.yml` | Positioning, launch tiers, GTM motion | Lauchengco |
| `dora-metrics.yml` | Four key delivery metrics | Forsgren |
| `threat-model.yml` | STRIDE threat model per component | OWASP |
| `privacy-assessment.yml` | Privacy by Design / GDPR assessment | Cavoukian |
| `trust-signals.yml` | Trust architecture, transparency | Digital Trust |
| `jobs-to-be-done.yml` | JTBD map (functional/emotional/social) | Christensen |

Canvas files are committed to git. They ARE your product documentation. In team settings, canvas updates are PR-reviewed like code changes.

### Harnessing System (What Prevents the Agent from Going Haywire)

**Guardrails** (`.claude/harness/guardrails.md`) -- Hard constraints that override confidence scores. Examples:
- Never skip discovery for Complex-domain problems
- Never commit code without running validation
- Never ship without checking accessibility (WCAG 2.1 AA)
- Never add data collection without Privacy by Design assessment
- Always run bias checklist before conducting research

**Anti-Patterns** (`.claude/harness/anti-patterns.md`) -- Known failure modes with detection rules:
- "Solution-first thinking" -- proposing solutions before mapping opportunities
- "Confidence inflation" -- self-assigning high confidence without evidence
- "Security-later" -- deferring security to after delivery
- "Dark pattern design" -- using behavioral science to manipulate users

**Cognitive Biases** (`.claude/harness/cognitive-biases.md`) -- Per-stage bias checklist based on Shotton and Kahneman. The agent reviews relevant biases before research, interviews, decisions, and design.

**Security & Trust** (`.claude/harness/security-trust.md`) -- Per-stage security requirements from OWASP, STRIDE, and Privacy by Design.

**Engineering Principles** (`.claude/harness/engineering-principles.md`) -- Explicit rules for DRY, KISS, YAGNI, SoC, SOLID, and Law of Demeter.

### Self-Learning

Borrowed from production-tested patterns:

- **Corrections Memory** -- Accumulated learning from mistakes. Read before every task.
- **Pattern Library** -- Successful patterns to reuse.
- **Reflexion Loop** -- Implement, validate, self-critique, retry (max 3 iterations).
- **Eval Benchmarks** -- Periodic self-assessment against scenarios.
- **Prompt Optimization** -- A/B testing of instruction changes against baselines.

## Skills Reference

| Skill | When to Use |
|-------|------------|
| `/interview` | Onboarding: establish purpose, vision, North Star |
| `/diamond-assess` | Check current state, get recommended next action |
| `/diamond-progress` | Move a diamond forward (runs all theory gates) |
| `/cynefin-classify` | Classify a problem's domain |
| `/ost-builder` | Build or update Opportunity Solution Tree |
| `/ice-score` | Score and prioritize ideas with confidence meter |
| `/bias-check` | Review cognitive biases before research/decisions |
| `/threat-model` | STRIDE threat modeling |
| `/privacy-check` | Privacy by Design / GDPR assessment |
| `/reflexion` | Self-correcting implementation loop |
| `/preflight` | Pre-code validation checklist |
| `/delivery-bootstrap` | Auto-detect tech stack and set up tooling |
| `/definition-of-done` | Verify increment satisfies all DoD criteria |
| `/bvssh-check` | Holistic health evaluation |
| `/service-check` | Evaluate against Downe's 15 principles |
| `/dora-check` | Delivery performance metrics |
| `/a11y-check` | Accessibility audit (WCAG 2.1 AA) |
| `/security-review` | OWASP secure design review |
| `/devils-advocate` | Systematically challenge assumptions |
| `/retrospective` | Post-delivery learning capture |
| `/wardley-map` | Strategic landscape mapping |
| `/jtbd-map` | Jobs to be Done mapping |
| `/assumption-test` | Design smallest viable assumption test |
| `/user-interview` | Torres-style story-based interview guide |
| `/gist-plan` | GIST planning workflow |
| `/launch-tier` | Classify releases + plan go-to-market |
| `/team-shape` | Team Topologies assessment |
| `/fan-out` | Parallel agent orchestration for OST exploration |
| `/eval-runner` | Run benchmark scenarios |
| `/prompt-optimizer` | A/B test instruction changes |

## Theories & Frameworks Integrated

| Theory/Framework | Author(s) | Applied To |
|-----------------|-----------|------------|
| Golden Circle (Start with Why) | Sinek | L0: Purpose, mission, values |
| Jobs to be Done | Christensen, Ulwick | L0-L2: Functional/emotional/social needs |
| Wardley Mapping | Wardley | L1: Strategic landscape, evolution |
| North Star Framework | Ellis, Amplitude | L1: Key metric + input metrics |
| Team Topologies | Skelton, Pais | L1: Team structure, cognitive load |
| Continuous Discovery Habits / OST | Torres | L2: Opportunity discovery, assumption testing |
| User Needs Mapping | Allen | L2: User needs independent of solutions |
| Cynefin Framework | Snowden | L2-L4: Domain classification, method selection |
| GIST Planning / ICE Scoring | Gilad | L3: Evidence-guided prioritization |
| Inspired / Empowered | Cagan | L3: Four risks, empowered teams |
| Good Services (15 Principles) | Downe | L3-L4: Service design quality |
| Accelerate / DORA Metrics | Forsgren, Humble, Kim | L4: Delivery performance measurement |
| OWASP Secure by Design / STRIDE | OWASP, Microsoft | L4: Security throughout lifecycle |
| Privacy by Design | Cavoukian, GDPR | L3-L4: Privacy as default |
| DRY, KISS, YAGNI, SOLID, SoC | Various | L4: Engineering principles |
| Loved (Product Marketing) | Lauchengco | L5: Positioning, go-to-market |
| Behavioral Science / Cognitive Biases | Shotton, Kahneman | All stages: Bias mitigation, ethical design |
| Double Diamond | Design Council | Core: Diverge/converge pattern at every scale |
| BVSSH | Smart | Cross-cutting: Holistic outcome measurement |

## Usage Modes

### Solo Developer
- Canvas is your shared memory with the agent
- Decision log provides cross-session continuity
- The agent is your product thinking partner
- Run `/diamond-assess` to continue where you left off

### Team
- Canvas files committed to git = shared product documentation
- Any team member's agent reads the same canvas state
- Canvas updates are PR-reviewed like code changes
- Different team members can work on different diamonds simultaneously
- Use Agent Teams or worktrees for parallel delivery

### Agent Orchestration

When the OST has multiple solutions to explore in parallel:

```
Lead Agent (main session)
  |-- Worker 1 (worktree: feature/ai-search)   -- explores Solution A
  |-- Worker 2 (worktree: feature/filters)      -- explores Solution B
  |-- Worker 3 (worktree: feature/feed-algo)    -- explores Solution C
  |
  Fan-in: Compare results, update ICE scores, select winner
```

Workers get read-only canvas access and worktree isolation. Only the lead agent updates canvas and progresses diamonds.

## JiT Tooling (Language-Agnostic)

Mycelium works with **any** tech stack. When delivery begins:

1. Auto-detects language, framework, project shape, existing tooling
2. Generates stack-appropriate validation commands
3. Configures security scanning for the detected stack
4. Agent asks user to confirm before proceeding

Universal principles (DRY, KISS, testing pyramid, OWASP) apply to all stacks. Specific tooling (test runners, linters, formatters) is discovered per project.

## Directory Structure

```
your-project/
  CLAUDE.md                    # Root Mycelium agent instructions
  .claude/
    engine/                    # Diamond engine rules + theory gates
    canvas/                    # 15 YAML source-of-truth files
    diamonds/                  # Active diamond state tracking
    harness/                   # Guardrails, anti-patterns, biases, security, principles
    memory/                    # Corrections, patterns, journals
    domains/                   # Phase-specific agent behavior (discovery/delivery/quality)
    skills/                    # 32 invocable skills
    hooks/                     # PreToolUse gate, PostToolUseFailure reflexion
    orchestration/             # Solo/team modes, agent teams, fan-out
    jit-tooling/               # Language-agnostic delivery tooling
    evals/                     # Benchmark scenarios + results
    optimization/              # Prompt A/B testing
    settings.local.json        # Claude Code permissions + hooks
```

## Contributing

Contributions are welcome. Mycelium is built on open product development theory -- if you see a gap in the frameworks, a missing bias, an incomplete guardrail, or a better way to harness agent behavior, please open an issue or PR.

### Areas for Contribution
- New skills for frameworks not yet integrated
- JiT tooling improvements for specific tech stacks
- Eval scenarios that test agent harnessing quality
- Translations of canvas templates
- Integration patterns with other AI coding tools

## License

MIT License. See [LICENSE](LICENSE).

---

*Mycelium is not affiliated with any of the authors or publishers of the books and frameworks referenced. All theory citations are for educational purposes and to properly credit the intellectual foundations this system builds upon.*
