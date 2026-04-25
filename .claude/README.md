# .claude/ — Mycelium Framework Root

This directory contains the complete Mycelium framework: a theory-guided harness for AI-assisted product development. Everything an AI agent needs to go from "why does this product exist?" to "ship it and measure" lives here.

## How It Works

Mycelium doesn't let an AI agent jump straight to code. It forces a structured journey through product discovery, strategy, opportunity analysis, solution design, delivery, and market feedback — each stage gated by established product and engineering frameworks.

```
Purpose (L0) → Strategy (L1) → Opportunity (L2) → Solution (L3) → Delivery (L4) → Market (L5)
```

Each stage uses a **diamond** (diverge → converge → diverge → converge), and the agent can't progress until evidence satisfies **theory gates** drawn from 30+ frameworks.

## Directory Map

| Directory | What It Does | Start Here |
|-----------|-------------|------------|
| [`engine/`](engine/) | Core decision logic — diamond lifecycle, theory gates, confidence scoring, routing | [diamond-rules.md](engine/diamond-rules.md) |
| [`harness/`](harness/) | Guardrails, anti-patterns, cognitive biases, engineering principles | [guardrails.md](harness/guardrails.md) |
| [`canvas/`](canvas/) | Product canvas — the single source of truth for all product knowledge | [purpose.yml](canvas/purpose.yml) |
| [`skills/`](skills/) | 44 reusable skills (interview, assumption-test, threat-model, etc.) | Any `SKILL.md` |
| [`hooks/`](hooks/) | Automated enforcement — secret detection, scope gating, reflexion | [README.md](hooks/README.md) |
| [`domains/`](domains/) | Phase-specific agent instructions (discovery, delivery, quality) | The CLAUDE.md in each |
| [`orchestration/`](orchestration/) | Multi-agent coordination, parallel exploration, operational patterns | [modes.md](orchestration/modes.md) |
| [`diamonds/`](diamonds/) | Active diamond state — what the agent is working on right now | [active.yml](diamonds/active.yml) |
| [`memory/`](memory/) | Self-learning system — corrections, patterns, journals | [corrections.md](memory/corrections.md) |
| [`jit-tooling/`](jit-tooling/) | Just-in-time tech stack detection and validation generation | [detector.md](jit-tooling/detector.md) |
| [`evals/`](evals/) | Framework self-evaluation — scenarios, benchmarks, dogfood reports | [schema.md](evals/schema.md) |
| [`schemas/`](schemas/) | Canvas file schemas for validation | |
| [`state/`](state/) | Runtime audit logs (change-log, diamond-state-audit) | [README.md](state/README.md) |
| [`optimization/`](optimization/) | A/B testing for framework variants | [README.md](optimization/README.md) |
| [`auto-dogfood/`](auto-dogfood/) | Automated framework validation runner | [README.md](auto-dogfood/README.md) |
| [`scripts/`](scripts/) | Utility scripts (scope check, canvas validation, upgrades) | |

## Key Concepts

**Diamonds** are work units. Each has four phases (Discover/Define/Develop/Deliver) and operates at one of six scales (L0 Purpose through L5 Market). See [`engine/diamond-rules.md`](engine/diamond-rules.md).

**Theory gates** are checkpoints between diamond phases. The agent must demonstrate evidence — not just claim confidence — before progressing. See [`engine/theory-gates.md`](engine/theory-gates.md).

**Canvas files** are the product's source of truth. Strategy, opportunities, threat models, metrics — all stored as YAML, committed to git, readable by humans and agents. See [`canvas/`](canvas/).

**Guardrails** enforce constraints at three tiers: BLOCK (mechanically prevented), REVIEW (gates progression), NUDGE (advised). See [`harness/guardrails.md`](harness/guardrails.md).

**Skills** are composable operations the agent can perform — from user interviews to security reviews to DORA metric checks. See [`skills/`](skills/).

## Getting Started

If you're exploring Mycelium for the first time:

1. Read the [top-level README](../README.md) for the thesis
2. Look at [`engine/diamond-rules.md`](engine/diamond-rules.md) to understand the workflow
3. Browse [`canvas/`](canvas/) to see what product knowledge looks like as structured data
4. Check [`skills/`](skills/) for the full list of agent capabilities
5. Read [`hooks/README.md`](hooks/README.md) to see how enforcement works in practice

## Framework Theories

Mycelium integrates 30+ established frameworks. The major ones:

- **Sinek** (Start with Why) — Purpose definition at L0
- **Wardley** (Wardley Mapping) — Strategic landscape at L1
- **Torres** (Continuous Discovery Habits) — Opportunity discovery at L2
- **Cagan** (Inspired/Empowered) — Four risks assessment at L3
- **Forsgren** (Accelerate/DORA) — Delivery metrics at L4
- **Christensen** (Jobs to Be Done) — User motivation throughout
- **Snowden** (Cynefin) — Complexity classification for routing decisions
- **Smart** (Better Value Sooner Safer Happier) — Holistic health checks
- **Downe** (Good Services) — Service quality principles

See [`engine/theory-gates.md`](engine/theory-gates.md) for how each theory becomes an actionable gate.
