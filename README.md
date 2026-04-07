# Mycelium

**Theory-guided agentic product development for Claude Code.** *v0.4.0*

Like nature's mycelium network -- the invisible intelligence that connects trees, shares nutrients, adapts to conditions, and makes the whole forest ecosystem stronger -- Mycelium connects product development theories, shares learning across sessions, adapts to any tech stack, and makes your product development practice stronger.

Mycelium is an open-source harnessing system that guides AI agents through proper incremental product development using best practices from 20+ established frameworks and books. It prevents the agent from going haywire by enforcing theory-guided decision gates, feedback loops at four speeds, reflexion loops, cognitive bias checks, and quality guardrails at every stage.

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

The interview skill guides you through establishing your product's purpose, vision, North Star metric, strategic landscape, and classifies your project type to determine which canvas files matter.

## How It Works

### Fractal Diamonds

Mycelium guides development through **fractal diamonds** -- recursive Discover/Define/Develop/Deliver cycles (based on the Double Diamond by the Design Council) that operate at every scale:

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

Diamond lifecycle: diamonds can be **active**, **blocked**, **archived**, or **killed**. Stale diamonds (30+ days without progress) are flagged for review.

### Theory Gates (11 gates)

Every diamond transition must pass **theory gates** -- not just a confidence score, but evidence checks grounded in specific frameworks:

| Gate | What It Checks | Source | Suggested Skill |
|------|---------------|--------|----------------|
| Evidence | Research-backed? Multiple sources? | Torres, Gilad | `/user-interview`, `/assumption-test` |
| Four Risks | Value, usability, feasibility, viability assessed? | Cagan | `/assumption-test` |
| JTBD | Emotional and social dimensions mapped? | Christensen | `/jtbd-map` |
| Cynefin | Domain classified? Method appropriate? | Snowden | `/cynefin-classify` |
| Bias Check | Research designed to mitigate cognitive biases? | Shotton, Kahneman | `/bias-check` |
| Security | Threat model updated? | OWASP (STRIDE) | `/threat-model`, `/security-review` |
| Privacy | Privacy assessed? Data minimized? | Cavoukian (PbD), GDPR | `/privacy-check` |
| BVSSH | Aligned with Better, Value, Sooner, Safer, Happier? | Smart | `/bvssh-check` |
| Service Quality | Downe's 15 principles checked? | Downe | `/service-check`, `/a11y-check` |
| DORA | Delivery metrics healthy? | Forsgren | `/dora-check` |
| Corrections | Past mistakes reviewed? | Mycelium self-learning | `/preflight`, `/reflexion` |

If ANY gate fails, the agent reports which gates failed, cites the theory, **suggests the skill to run**, and recommends the smallest action to satisfy each -- but does NOT proceed.

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

Canvas files are committed to git. They ARE your product documentation. Not all canvas files are required for every project -- the `/interview` skill classifies your project type (solo hobby, solo product, team startup, team enterprise) and tells you which canvas files to focus on.

### Harnessing System (What Prevents the Agent from Going Haywire)

**Guardrails** (`.claude/harness/guardrails.md`) -- 22 hard constraints, each marked as **ENFORCED** (mechanically blocked) or **ADVISORY** (agent discipline):
- 12 ENFORCED: security, validation, accessibility, corrections review, canvas updates, decision logging
- 10 ADVISORY: engineering principles (DRY, KISS), bias checks, BVSSH, devil's advocate

**Anti-Patterns** (`.claude/harness/anti-patterns.md`) -- 11 known failure modes across discovery, confidence, security, delivery, and market/GTM:
- "Solution-first thinking", "Confidence inflation", "Security-later", "Dark pattern marketing", "Regression avoidance", and more

**Cognitive Biases** (`.claude/harness/cognitive-biases.md`) -- Per-stage bias checklist based on Shotton and Kahneman. 20+ biases mapped across L0-L5 including agent's own biases.

**Security & Trust** (`.claude/harness/security-trust.md`) -- Per-stage security requirements from OWASP, STRIDE, and Privacy by Design.

**Engineering Principles** (`.claude/harness/engineering-principles.md`) -- Explicit rules for DRY, KISS, YAGNI, SoC, SOLID, Law of Demeter, Clean Code.

### 5-Layer Hook Enforcement

Mycelium enforces guardrails through hooks that fire automatically at different points:

| Layer | Event | What It Does | Cost |
|-------|-------|-------------|------|
| 1. PreToolUse gate | Before code edits | Preflight check + secret detection (blocks hardcoded API keys, tokens) | ~30 tokens |
| 2. PostToolUse nudge | After code edits | Context-aware reminders (a11y for UI files, OWASP for API files) | ~50 tokens |
| 3. PostToolUseFailure | After failures | Reflexion analysis: diagnose root cause before retrying | ~200 tokens |
| 4. Stop check | Session end | Canvas gap detection, overdue feedback loop warnings | ~50 tokens |
| 5. SessionStart check | Session start/resume | Reminds about overdue strategic reviews (BVSSH, DORA) | ~50 tokens |
| 6. Skill-level gates | On demand | Full 11-gate theory evaluation via `/diamond-progress` | varies |

Total overhead: ~6,000 tokens/session (negligible vs typical 50K-200K sessions).

### Four-Speed Feedback Loop System

Based on Gene Kim's Three Ways, Argyris's double-loop learning, and Meadows's leverage points:

| Loop | Speed | Purpose | Key Mechanisms |
|------|-------|---------|---------------|
| **1. Immediate** | Seconds | Fix the error (single-loop) | Reflexion, secret detection, corrections matching |
| **2. Incremental** | Hours/days | Improve the process (single-loop + memory) | Phase learnings, DORA metrics, retrospectives |
| **3. Strategic** | Weekly/monthly | Question the assumptions (double-loop) | BVSSH health, North Star trajectory, Wardley refresh |
| **4. Transformative** | Quarterly | Improve the system itself (triple-loop) | Eval benchmarks, prompt optimization |

Run `/feedback-review` to check health across all loops. Includes regression warning triggers (e.g., "DORA declined twice in a row") and Goodhart's Law protection (counter-metrics for every tracked metric).

**The L5 -> L2 feedback loop**: After launch, market signals feed back into new L2 Opportunity diamonds, closing the full cycle: Purpose -> Strategy -> Discovery -> Solution -> Delivery -> Market -> Discovery.

### Self-Learning

- **Corrections Memory** -- Accumulated learning from mistakes. Read before every task. Pruned when > 30 entries.
- **Pattern Library** -- Successful patterns to reuse across diamonds.
- **Reflexion Loop** -- Implement, validate, self-critique, retry (max 3 iterations).
- **Eval Benchmarks** -- 6 scenarios across discovery, delivery, and integration categories.
- **Prompt Optimization** -- A/B testing of instruction changes against eval baselines.

### Plain-Language Communication

Mycelium communicates in human language, not framework jargon:
- "Discovering what problems to solve" not "L2 Opportunity Discover phase"
- "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5"
- After each phase, the agent offers to capture learnings

### Operations & Maintenance

- **Day-to-day**: Session resumption via `/diamond-assess`, corrections review via hooks
- **Weekly**: Diamond state review, canvas updates
- **Monthly**: BVSSH health check, Wardley map review, stale diamond cleanup
- **Quarterly**: North Star review, strategic landscape refresh, eval benchmarks
- **Escape hatch**: Documented bypass process for emergencies (production incidents, hotfixes) with mandatory payback

## Skills Reference (34 skills)

### Onboarding & Assessment
| Skill | When to Use |
|-------|------------|
| `/interview` | Onboarding: purpose, vision, North Star, project classification |
| `/diamond-assess` | Current state in plain language, recommended next action |
| `/diamond-progress` | Move diamond forward with theory gates + skill suggestions |

### Discovery
| Skill | When to Use |
|-------|------------|
| `/user-interview` | Torres-style story-based interviews with bias mitigation |
| `/user-needs-map` | Allen's methodology: map needs independently of solutions |
| `/ost-builder` | Build/update Opportunity Solution Tree from research |
| `/jtbd-map` | Jobs to be Done (functional, emotional, social) |
| `/assumption-test` | Design smallest viable test for an assumption |
| `/cynefin-classify` | Classify problem domain |
| `/wardley-map` | Create/update Wardley Map of value chain |
| `/ice-score` | Prioritize with ICE scoring + confidence meter |
| `/gist-plan` | GIST planning: goals, ideas, steps, tasks |

### Quality & Governance
| Skill | When to Use |
|-------|------------|
| `/bias-check` | Review cognitive biases before research/decisions |
| `/devils-advocate` | Challenge assumptions before major decisions |
| `/bvssh-check` | Holistic BVSSH health evaluation |
| `/service-check` | Downe's 15 Good Services principles |
| `/threat-model` | STRIDE threat modeling |
| `/privacy-check` | Privacy by Design / GDPR assessment |
| `/security-review` | OWASP secure design review |
| `/a11y-check` | Accessibility audit (WCAG 2.1 AA) |

### Delivery
| Skill | When to Use |
|-------|------------|
| `/delivery-bootstrap` | Auto-detect tech stack, set up tooling |
| `/preflight` | Pre-code validation checklist |
| `/reflexion` | Self-correcting implementation loop |
| `/definition-of-done` | Verify all DoD criteria |
| `/dora-check` | DORA delivery performance metrics |
| `/retrospective` | Post-delivery learning capture |

### Market & Organization
| Skill | When to Use |
|-------|------------|
| `/launch-tier` | Classify releases, plan go-to-market |
| `/team-shape` | Team Topologies assessment |

### Canvas & Orchestration
| Skill | When to Use |
|-------|------------|
| `/canvas-update` | Update canvas with new evidence |
| `/canvas-sync` | Synchronize canvas across team via git |
| `/fan-out` | Parallel agent orchestration for OST exploration |

### Self-Improvement
| Skill | When to Use |
|-------|------------|
| `/feedback-review` | Aggregate all feedback signals, check health across 4 loops |
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
| Three Ways of DevOps | Kim | Feedback loops: flow, amplify feedback, continuous learning |
| Double/Triple-Loop Learning | Argyris | Self-learning: single-loop (fix), double-loop (question), triple-loop (transform) |
| Leverage Points | Meadows | Systems thinking: where to intervene for maximum effect |
| Goodhart's Law | Goodhart | Measurement discipline: counter-metrics prevent gaming |

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

Mycelium works with **any** tech stack, including polyglot/multi-language projects. When delivery begins:

1. Auto-detects languages, frameworks, project shape (single app, monorepo, multi-service), existing tooling
2. Generates stack-appropriate validation commands, linting, testing
3. Configures security scanning for detected stack(s)
4. Agent asks user to confirm before proceeding

Universal principles (DRY, KISS, testing pyramid, OWASP) apply to all stacks. Specific tooling (test runners, linters, formatters) is discovered per project.

## Directory Structure

```
your-project/
  CLAUDE.md                    # Root Mycelium agent instructions (v0.4.0)
  .claude/
    settings.json              # Shared hook config + permissions (committed)
    engine/                    # Diamond rules, theory gates, confidence thresholds, Cynefin routing
    canvas/                    # 15 YAML source-of-truth files
    diamonds/                  # Active diamond state tracking
    harness/                   # Guardrails, anti-patterns, biases, security, engineering principles
    memory/                    # Corrections, patterns, product journal, delivery journal
    domains/                   # Phase-specific agent behavior (discovery/delivery/quality)
    skills/                    # 34 invocable skills
    hooks/                     # 6-layer enforcement (gate, nudge, reflexion, stop-check, session-start, skill-gates)
    orchestration/             # Solo/team modes, agent teams, fan-out, operations, escape hatch
    jit-tooling/               # Language-agnostic delivery tooling + polyglot detection
    evals/                     # 6 benchmark scenarios + results
    optimization/              # Prompt A/B testing baselines + variants
```

## Regulatory Awareness: EU AI Act

**Mycelium itself is not regulated** by the EU AI Act (Regulation 2024/1689). It is configuration files, not an AI system under Article 3(1). It is protected as an open-source component under Article 25(4) and Recital 102.

**However, products built WITH Mycelium may be regulated.** If you're building an AI-powered product that makes decisions about people, interacts with users, or operates in the EU market, you should assess your obligations:

- **High-risk systems** (employment, credit scoring, healthcare, education, law enforcement) require conformity assessments, documentation, and human oversight
- **User-facing AI** must disclose its AI nature (Article 50, effective August 2026)
- **Generative AI** must mark synthetic content as AI-generated

Mycelium includes a **Regulatory Gate** in its theory gates that prompts you to assess risk classification at the L3 Solution stage. See `.claude/harness/security-trust.md` for the full regulatory awareness guide.

**Mycelium does not certify EU AI Act compliance. For compliance decisions, consult qualified EU AI law counsel.**

## Contributing

Contributions are welcome. Mycelium is built on open product development theory -- if you see a gap in the frameworks, a missing bias, an incomplete guardrail, or a better way to harness agent behavior, please open an issue or PR.

### Areas for Contribution
- New skills for frameworks not yet integrated
- JiT tooling improvements for specific tech stacks
- Eval scenarios that test agent harnessing quality
- Hook enforcement patterns for new Claude Code events
- Integration patterns with other AI coding tools

## License

MIT License. See [LICENSE](LICENSE).

---

*Mycelium is not affiliated with any of the authors or publishers of the books and frameworks referenced. All theory citations are for educational purposes and to properly credit the intellectual foundations this system builds upon.*
