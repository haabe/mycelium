# Mycelium: Theory-Guided Agentic Product Development

*Version 0.15.1 -- Instruction budget management: phase-scoped guardrails (core/discovery/delivery/market), instruction_budget frontmatter on all 44 skills, lazy-reference guardrail index. Interviewing: Brown's three mindsets (curiosity/skepticism/humility), stakeholder vs user distinction, internal_stakeholder source class, validated flag, constraints category, closing question. 7 external evidence articles logged. Sources: Horthy (instruction budget), Haagsman (40-instruction budget), Brown (stakeholder interviewing).*

Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger.

**You are an agent operating within Mycelium. Every action you take must be guided by the frameworks below, harnessed by the guardrails, and logged in the decision system.**

## Communication Rules

**Always communicate in plain language first, technical details second.** Use `.claude/engine/status-translations.md` to translate diamond states.

- Say "Discovering what problems to solve" not "L2 Opportunity Discover phase"
- Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5"
- When reporting confidence, always include: the level, the evidence type, WHY it's appropriate, and what would increase it

**Always suggest relevant skills at transitions.** When checking theory gates, surface the skill that satisfies each gate: "Before delivering, consider running `/security-review` (security gate) and `/a11y-check` (accessibility)."

**Always offer to capture learnings after each diamond phase.** After completing a phase, prompt: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."

## Mandatory Pre-Task Protocol

Before ANY implementation task, load context in this order (task-specific first, background last — models attend best to early and late context):
1. Identify which diamond you are operating within (check `.claude/diamonds/active.yml`)
2. Load the appropriate domain context (`.claude/domains/{discovery|delivery|quality}/CLAUDE.md`) — **skip if canvas is empty** (new project with no diamond yet; `/interview` creates the first diamond)
3. Read `.claude/memory/corrections.md` for relevant past mistakes — **skip on first `/interview` round** (no corrections exist yet)
4. Load phase-scoped guardrails: always load `guardrails-core.md`; add `guardrails-discovery.md` (L0-L2), `guardrails-delivery.md` (L3-L4), or `guardrails-market.md` (L5) per current phase. See `.claude/harness/guardrails.md` for full reference.

## Mandatory Post-Task Protocol (G-P7)

After completing ANY batch of changes, before reporting done:
1. **Verify**: If changes span repos, diff changed files for consistency. Check reference integrity (counts, cross-links, no orphans).
2. **Corrections**: Did any mistakes happen during this task? Log to `corrections.md`, update TL;DR.
3. **Patterns**: Did anything reusable emerge? Log to `patterns.md`.
4. **Sync**: Ensure both repos match on all changed files.

If the user has to ask whether this happened, the protocol already failed.

## The Diamond Engine

### Diamond Scales (L0-L5)

| Scale | Focus | Primary Theories | Canvas Files |
|-------|-------|-----------------|--------------|
| L0: Purpose | Why we exist | Sinek (Golden Circle), JTBD (Christensen) | `canvas/purpose.yml`, `canvas/jobs-to-be-done.yml` |
| L1: Strategy | Where to play | Wardley Mapping, North Star, Team Topologies (Skelton) | `canvas/landscape.yml`, `canvas/north-star.yml`, `canvas/team-shape.yml` |
| L2: Opportunity | What to solve | Torres (CDH/OST), Allen (User Needs Mapping), Hoskins (Scenarios), Cynefin | `canvas/opportunities.yml`, `canvas/user-needs.yml`, `canvas/scenarios.yml` |
| L3: Solution | How to solve it | Gilad (GIST), Ellis (ICE, adopted by Gilad within GIST), Cagan (Inspired), Downe (Good Services) | `canvas/gist.yml`, `canvas/services.yml` |
| L4: Delivery | Build and ship | Forsgren (DORA), OWASP, Goldratt (ToC), DRY/KISS/YAGNI/SOLID/SoC | `canvas/dora-metrics.yml`, `canvas/threat-model.yml`, `canvas/value-stream.yml` |
| L5: Market | Reach users | Lauchengco (Loved), Shotton (behavioral science) | `canvas/go-to-market.yml`, `canvas/trust-signals.yml` |

L0-L3 are product-agnostic. L4-L5 adapt to `product_type` (software, content_course, content_publication, content_media, ai_tool, service_offering). See `canvas-guidance.yml#product_types`.

### Diamond Phases

Each diamond has four phases, gated by theory checks:
1. **Discover** (diverge) -- Explore broadly. Gather evidence. Challenge assumptions.
2. **Define** (converge) -- Synthesize discoveries. Narrow focus. Frame the problem/opportunity.
3. **Develop** (diverge) -- Generate multiple solutions. Ideate. Prototype.
4. **Deliver** (converge) -- Validate, build, ship, measure.

Diamonds spawn child diamonds when complexity requires it (L0->L1->L2->L3->L4, L5->L2 on market feedback). Parents continue while children execute. If delivery reveals a bad assumption, the diamond **regresses** back with new evidence -- this is the system working correctly.

See `.claude/engine/diamond-rules.md` for full transition rules, WIP limits, and lifecycle management.

### OST Leaf Lifecycle

Every OST solution leaf follows a 10-phase pipeline from creation to market feedback. Each phase has explicit input artifacts, gates, output artifacts, and discard criteria. The pipeline is:

**OST Leaf → Four Risks → ICE Score → Assumption Test → GIST Entry → Bounded Context → Threat Model → Preflight → Delivery Diamond → Launch + Feedback**

See `.claude/engine/leaf-lifecycle.md` for complete phase definitions, discard rules, and cross-reference map. Archived leaves go to `canvas/archived-solutions.yml`.

### Perspective Resolution

When product, design, and engineering perspectives conflict, use the structured resolution framework. See `.claude/engine/perspective-resolution.md`.

### Leaf Bakeoff (Parallel A/B Testing)

When multiple leaves compete for the same opportunity, use the bakeoff protocol for structured comparison. See `.claude/orchestration/leaf-bakeoff.md`.

## Theory Gates (Decision Checkpoints)

Every diamond transition must pass applicable gates from: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory. See `.claude/engine/theory-gates.md` for complete definitions, pass/fail criteria, and suggested skills.

**You cannot progress a diamond by saying "I'm confident enough." You must demonstrate evidence that satisfies each gate.**

## The Canvas (Source of Truth)

All product knowledge lives in `.claude/canvas/*.yml`. These files are:
- The **single source of truth** for the product's state
- Committed to git (they are documentation-as-code)
- Updated through evidence, not assumption
- Readable by any team member starting a new session

**Never make a significant decision without first checking and updating the relevant canvas file.**

Canvas files should include `_meta` blocks for versioning and staleness detection (see `canvas-guidance.yml`). Run `/canvas-health` periodically to lint for missing fields, stale confidence, inconsistent evidence types, and orphaned references.

## Harnessing System

- **Guardrails** (`.claude/harness/guardrails.md`): Three-tier enforcement -- BLOCK (mechanically prevented), REVIEW (gates progression), NUDGE (advised, not blocking).
- **Anti-Patterns** (`.claude/harness/anti-patterns.md`): Known failure modes with detection rules. Stop and self-correct if you catch yourself in one.
- **Cognitive Biases** (`.claude/harness/cognitive-biases.md`): Per-stage bias checklist.
- **Security & Trust** (`.claude/harness/security-trust.md`): Per-stage security requirements.
- **Engineering Principles** (`.claude/harness/engineering-principles.md`): DRY, KISS, YAGNI, SoC, SOLID, LoD.

## Self-Learning System

### Two Memory Systems -- Important Distinction

| System | Location | Scope | Committed to git? |
|---|---|---|---|
| **Project memory** | `.claude/memory/` (in the project repo) | Team-level learnings about *this product* | Yes |
| **Auto-memory** | `~/.claude/projects/<id>/memory/` (in user home) | Per-session continuity between you and the agent | No (user-local) |

**Routing rule**: Project-team learnings -> project memory. Agent-user learnings -> auto-memory. Hardware/environment failures -> neither.

The reflexion hook (PostToolUseFailure) is scoped to **project-relevant failures only** -- do not log entries to project memory for agent self-inflicted tool errors or environment issues outside the project directory.

### Key Artifacts
- **Corrections** (`.claude/memory/corrections.md`): Accumulated learning from mistakes. **Read before every task.**
- **Patterns** (`.claude/memory/patterns.md`): Successful patterns to reuse.
- **Decision Log** (`.claude/harness/decision-log.md`): Every significant decision with context, alternatives, theory, evidence, confidence.
- **Feedback Loops** (`.claude/engine/feedback-loops.md`): Four-speed system (immediate/incremental/strategic/transformative). Run `/feedback-review` to check health.
- **Reflexion Loop**: Implement -> validate -> self-critique -> retry (max 3). See `.claude/skills/reflexion/SKILL.md`.
- **Eval Benchmarks** (`.claude/evals/`): Periodic self-assessment against scenarios.
- **Cycle History** (`.claude/canvas/cycle-history.yml`): Completed leaf lifecycle outcomes for calibration. See `.claude/engine/cycle-learning.md`.
- **Adaptive Thresholds** (`.claude/canvas/thresholds.yml`): Calibrated thresholds that improve from data. See `.claude/engine/adaptive-thresholds.md`.

### Learning Metabolism (Self-Improving System)

Mycelium gets smarter over time through five learning mechanisms:

1. **Cycle Learning** (`.claude/engine/cycle-learning.md`): Every completed or discarded leaf generates calibration data — predicted vs actual ICE, effort accuracy, risk dimension accuracy.
2. **Pattern Emergence** (`.claude/engine/pattern-detector.md`): Statistical patterns across cycle history surface as correlation rules, anti-pattern signals, and success patterns. Woven into `/retrospective` and `/diamond-assess`.
3. **Adaptive Thresholds** (`.claude/engine/adaptive-thresholds.md`): ICE advance threshold, confidence calibration, and evidence staleness thresholds adjust from historical data. Defaults until N=10 cycles.
4. **Framework Reflexion** (`.claude/engine/framework-reflexion.md`): Quarterly self-assessment — cycle velocity, discard trends, confidence calibration, gate effectiveness, regression rate. Run `/framework-health`.
5. **Evidence Decay** (`.claude/engine/evidence-decay.md`): Evidence ages. Confidence degrades over time unless refreshed. `/canvas-health` flags stale evidence.

## Domain Contexts

Load the appropriate context based on current diamond phase:

- **Discovery**: `.claude/domains/discovery/CLAUDE.md` -- Torres-style interviewing, OST construction, bias-aware research
- **Delivery**: `.claude/domains/delivery/CLAUDE.md` -- Agile/DevOps practices, clean code, security, accessibility, DORA metrics
- **Quality**: `.claude/domains/quality/CLAUDE.md` -- Always-active overlay: validation, accessibility, security, service principles

## JiT Tooling

Mycelium is **language-agnostic** and **product-type-agnostic**. When a delivery diamond begins, auto-detect the tech stack (or product type), generate appropriate validation, and confirm with the user. See `.claude/jit-tooling/detector.md`.

## Usage & Orchestration

Solo developers use canvas as shared memory with the agent. Teams commit canvas to git as shared product documentation. For parallel exploration, use `/fan-out` with worktree-isolated worker agents.

See `.claude/orchestration/modes.md` for usage patterns and `.claude/orchestration/agent-teams.md` for parallel orchestration.

## Operations & Maintenance

- **Day-to-day**: `.claude/orchestration/operations.md` -- Session resumption, canvas maintenance, diamond lifecycle, memory pruning
- **Escape hatch**: `.claude/orchestration/escape-hatch.md` -- Legitimate process bypass for emergencies. Must be documented and paid back.

## Skills

All 44 skills are auto-discovered from `.claude/skills/*/SKILL.md`. Suggested skills are surfaced at diamond transitions by `/diamond-progress` and `/diamond-assess`, and contextually by hooks. Type `/` to see the current list.

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
