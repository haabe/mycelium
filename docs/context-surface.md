# Context Surface — what the agent reads when running Mycelium

This document answers a question the audit (`/xai-check` on `svc-mycelium`, 2026-05-04) flagged as a Stage 2 partial: **"What data does the agent see when it makes a recommendation under Mycelium?"** Today the answer is distributed across many files. This is the consolidated map.

---

## Per-task read order

When the agent starts any non-trivial task, it loads context in this order (per `CLAUDE.md :: Mandatory Pre-Task Protocol`):

1. **`.claude/diamonds/active.yml`** — which diamond is active. Determines scale (L0/L1/L2/L3/L4/L5) and phase (Discover/Define/Develop/Deliver).
2. **`.claude/domains/{discovery|delivery|quality}/CLAUDE.md`** — the appropriate domain context for the active scale.
3. **`.claude/memory/corrections.md`** — past mistakes. Read in full. Recurring patterns inform present behavior.
4. **`.claude/harness/guardrails-core.md`** — always loaded — plus phase-scoped: `guardrails-discovery.md` (L0-L2), `guardrails-delivery.md` (L3-L4), `guardrails-market.md` (L5).

After loading: the agent reads any task-specific files the user references, then invokes the relevant skill (which may itself read further canvas state).

## Persistent state the agent has access to

### Canvas (`.claude/canvas/*.yml`)

The product's source of truth. Each file is committed to git; any session can read prior session state.

| File | Holds |
|---|---|
| `purpose.yml` | L0 Purpose — Sinek's Why, mission, market signals |
| `landscape.yml` | L1 Strategy — Wardley map, components, evolution stages |
| `north-star.yml` | L1 Strategy — North Star metric and inputs |
| `team-shape.yml` | L1 Strategy — Skelton team topologies |
| `bvssh-health.yml` | L1 Strategy — Better Value Sooner Safer Happier scores |
| `opportunities.yml` | L2 Opportunity — OST, problem framings |
| `user-needs.yml` | L2 Opportunity — Allen user needs map |
| `jobs-to-be-done.yml` | L2 Opportunity — Christensen JTBD |
| `scenarios.yml` | L2 Opportunity — Hoskins user scenarios |
| `gist.yml` | L3 Solution — Gilad GIST (goals, ideas, steps, tasks) |
| `services.yml` | L3 Solution — Downe service quality + per-service `xai` block |
| `bounded-contexts.yml` | L3 Solution — DDD bounded contexts |
| `archived-solutions.yml` | L3 Solution — discarded leaves |
| `threat-model.yml` | L4 Delivery — STRIDE threats |
| `privacy-assessment.yml` | L4 Delivery — Privacy by Design + GDPR scope |
| `dora-metrics.yml` | L4 Delivery — DORA-shaped metrics for software products |
| `ai-tool-metrics.yml` | L4 Delivery — eval/safety metrics for AI products |
| `content-metrics.yml` | L4 Delivery — content delivery metrics |
| `service-metrics.yml` | L4 Delivery — service-offering metrics |
| `value-stream.yml` | L4 Delivery — Rother & Shook VSM |
| `go-to-market.yml` | L5 Market — Lauchengco Loved framework |
| `trust-signals.yml` | L5 Market — digital trust architecture |
| `human-tasks.yml` | All scales — pending offline human tasks |
| `cycle-history.yml` | All scales — completed leaf lifecycles for calibration |
| `thresholds.yml` | All scales — adaptive thresholds (ICE, confidence, evidence-decay) |

### Memory (`.claude/memory/`)

| File | Holds |
|---|---|
| `corrections.md` | Friction log (Hoskins Ch. 4) — agent-introduced failures with prevention rules |
| `patterns.md` | Successful patterns to reuse |
| `warnings-log.md` | CI signals (validator + upgrade WARN/FAIL) — auto-updated by `ingest_warnings.py` |

### Decision log (`.claude/harness/decision-log.md`)

Every significant decision: context, alternatives, theory, evidence, confidence. The structured `why_not_alternatives` field (added 2026-05-04) requires per-alternative rejection rationale — contrastive explanations per Liao et al. (2020).

### State (`.claude/state/`)

| File | Holds |
|---|---|
| `upstream.json` | Dogfood instances: pointer to upstream framework repo (activates framework-guard) |
| `active-execution.json` | L4 delivery: in-scope and out-of-scope path lists (consumed by `scope-gate.sh`) |

### JiT detection (`.claude/jit-tooling/`)

| File | Holds |
|---|---|
| `active-stack.yml` | Detected language stack + AI components (Step 1c output of `delivery-bootstrap`). Gitignored. |
| `active-metrics.yml` | Detected metric sources for `/metrics-pull` |

## Skills the agent can invoke

45+ skills auto-discovered from `.claude/skills/*/SKILL.md`. The agent reads the skill's SKILL.md when it invokes the skill — not all 45 at once. Type `/` to see the current list, or read `surfaces.yml` for the index.

## Hooks that constrain the agent

These run automatically and can block the agent's actions:

| Hook | Triggers on | Effect |
|---|---|---|
| `framework-guard.sh` | Edit/Write/Bash on framework files in dogfood instances | Blocks; redirects to upstream-then-sync flow |
| `scope-gate.sh` | Edit/Write outside in_scope_paths during L4 | Blocks; allows .claude/** unconditionally |
| `prompt-injection-defense.sh` | Skill outputs handling user-supplied content | Wraps untrusted content per security-trust.md |
| Reflexion (PostToolUseFailure) | Bash/tool failures | Prompts the agent to diagnose + log |

## What the agent does NOT have access to

To set expectations honestly:

- **No browser, no internet.** The agent can `WebFetch` if a URL is given but cannot freely browse.
- **No persistent state outside the repo.** Each session starts fresh; everything carried forward lives in canvas + memory + decision-log.
- **No user data outside `.claude/`** unless the user explicitly references files.
- **No automated communication with external services.** `/metrics-pull` calls APIs (GitHub, etc.) only when the user runs it; results are saved as snapshots.
- **No model internals.** Mycelium reads what the runtime vendor's API exposes — the framework cannot inspect Claude's reasoning beyond the chain-of-thought it surfaces (which has its own faithfulness caveats — see system card §5).

## Verification

To audit what the agent saw on a given task: read the corresponding entries in `decision-log.md` (the agent records the canvas/memory references that drove each significant move) and the commit history of the canvas files.

---

*This doc closes the Stage 2 `input` partial finding from the 2026-05-04 `/xai-check` audit (`services.yml :: svc-mycelium.xai.surfaces.{end_user,deployer_developer}.input`). It's deliberately a single page — the underlying files are the source of truth; this map exists so a new developer doesn't have to read all of CLAUDE.md to know what shapes the agent's reasoning.*
