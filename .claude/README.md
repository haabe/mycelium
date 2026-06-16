# .claude/ — Mycelium's dogfood instance

This directory is **not** the framework. Since the plugin migration, the Mycelium
framework lives in [`plugins/mycelium/`](../plugins/mycelium/) (shipped via the
`@haabe-mycelium` plugin). What lives here is the framework **eating its own
cooking**: the canvas, diamonds, memory, and evidence that accumulate while
Mycelium is used to develop Mycelium.

In other words, `.claude/` here is exactly what a `.claude/` looks like in any
project that installs the plugin — except the project under development is
Mycelium itself. It is project-owned state, not framework source.

## What's here

| Directory | What it holds |
|-----------|---------------|
| [`canvas/`](canvas/) | Product canvas — purpose, opportunities, landscape, threat model, metrics (the source of truth for this project's knowledge) |
| [`diamonds/`](diamonds/) | Active diamond state — what's being worked on right now ([active.yml](diamonds/active.yml)) |
| [`memory/`](memory/) | Self-learning record — corrections, patterns, cluster-instances, journals ([corrections.md](memory/corrections.md)) |
| [`harness/`](harness/) | Decision provenance + CI signal capture for this project — decision-log.md, warnings-log.md |
| [`evals/`](evals/) | This project's self-evaluation — scenarios, assumption-tests, dogfood reports ([schema.md](evals/schema.md)) |
| [`state/`](state/) | Runtime audit logs (read-log, change-log, plugin state) ([README.md](state/README.md)) |
| [`drafts/`](drafts/) | Work-in-progress notes and operational follow-ups |
| [`worktrees/`](worktrees/) | Scratch git worktrees for isolated agent work |

## Where the framework actually lives

The engine, skills, hooks, guardrails, schemas, and theory gates are **not** in
this directory — they ship in the plugin:

| Framework concept | Canonical location |
|---|---|
| Diamond lifecycle, routing, confidence | [`plugins/mycelium/engine/diamond-rules.md`](../plugins/mycelium/engine/diamond-rules.md) |
| Theory gates (30+ frameworks → actionable checkpoints) | [`plugins/mycelium/engine/theory-gates.md`](../plugins/mycelium/engine/theory-gates.md) |
| Guardrails, anti-patterns, cognitive biases | [`plugins/mycelium/harness/`](../plugins/mycelium/harness/) |
| Skills (interview, assumption-test, threat-model, …) | [`plugins/mycelium/skills/`](../plugins/mycelium/skills/) |
| Hooks (secret detection, scope gating, reflexion) | [`plugins/mycelium/hooks/`](../plugins/mycelium/hooks/) |
| Canvas schemas + validators | [`plugins/mycelium/schemas/canvas/`](../plugins/mycelium/schemas/canvas/), [`plugins/mycelium/scripts/validate_canvas.py`](../plugins/mycelium/scripts/validate_canvas.py) |

## How it works (the short version)

Mycelium doesn't let an AI agent jump straight to code. It forces a structured
journey — Purpose (L0) → Strategy (L1) → Opportunity (L2) → Solution (L3) →
Delivery (L4) → Market (L5) — where each stage is a **diamond** (diverge →
converge → diverge → converge) that can't progress until evidence satisfies
**theory gates**. The mechanics live in the plugin; the lived results of running
them on this project live here.

## Getting oriented

1. Read the [top-level README](../README.md) for the thesis.
2. See the framework mechanics in [`plugins/mycelium/`](../plugins/mycelium/) — start with [diamond-rules.md](../plugins/mycelium/engine/diamond-rules.md).
3. Browse [`canvas/`](canvas/) to see what this project's knowledge looks like as structured data.
4. Read [`memory/corrections.md`](memory/corrections.md) — the friction log is where the dogfooding pays off.
