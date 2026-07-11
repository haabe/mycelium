# Skills by category

**Audience**: practitioners scanning skills by type of work.
**Time to read**: 3 min.
**Last updated**: 2026-06-08.

Alternate index to the phase-first [skills/README.md](README.md). Same 58 skills, different ordering.

## Research & discovery

User research, interviews, evidence-gathering, classification. Use when you do not yet know what you are deciding.

- `/user-interview` — story-based interviewing (Torres)
- `/mocked-persona-interview` — disciplined mocked personas when real users unavailable
- `/user-needs-map` — needs independent of solutions (Allen)
- `/jtbd-map` — Jobs to be Done (Christensen)
- `/cynefin-classify` — domain classification (Snowden)
- `/wardley-map` — strategic landscape (Wardley)
- `/handoff` — structured offline conversation prep
- `/log-evidence` — record findings back into canvas

## Synthesis & planning

Turn research into decisions. Use when discovery has produced enough signal to converge.

- `/ost-builder` — Opportunity Solution Tree (Torres)
- `/ice-score` — Impact × Confidence × Ease (Ellis)
- `/gist-plan` — GIST planning (Gilad)
- `/assumption-test` — smallest viable test (Torres + Gilad AFTER)
- `/diamond-progress` — move a diamond through gate checks
- `/diamond-assess` — current state + recommended next action
- `/define-done` — pin a diamond's outcome Definition of Done (Seiden/Cagan/Adzic)

## Build & delivery

Implementation, validation, completion. Use when scope is committed and you are building.

- `/delivery-bootstrap` — auto-detect tech stack + generate validation
- `/preflight` — pre-implementation checklist
- `/reflexion` — implement → validate → self-critique → retry
- `/definition-of-done` — executable completion gates
- `/dora-check` — DORA metrics (Forsgren)
- `/retrospective` — post-delivery learning extraction

## Audit & governance

Quality, security, privacy, accessibility, regulatory, explainability. Use as gates fire — not as theatre.

- `/bias-check` — cognitive bias review
- `/devils-advocate` — counter-argument check
- `/bvssh-check` — holistic outcome evaluation (Smart)
- `/service-check` — 15 service principles (Downe)
- `/threat-model` — STRIDE
- `/privacy-check` — Privacy by Design (Cavoukian)
- `/security-review` — OWASP Top 10:2025
- `/harms-check` — dark/deceptive patterns + foreseeable misuse (safety-by-design; NUDGE)
- `/usability-check` — Nielsen's 10 heuristics
- `/a11y-check` — WCAG 2.1 AA
- `/regulatory-review` — EU AI Act
- `/xai-check` — explainability audit (5-stage)

## Evidence & metrics

Quantitative grounding. Use when canvas needs measurable evidence beyond user research.

- `/metrics-detect` — find applicable metric sources
- `/metrics-pull` — snapshot + compute deltas + draft evidence

## Orchestration

Multi-agent + canvas-coordination patterns. Use when work fans out.

- `/fan-out` — parallel agent orchestration
- `/canvas-update` — write evidence to canvas
- `/canvas-health` — lint canvas
- `/canvas-sync` — cross-session canvas sync helper

## Render & output

Read-only rendering of canvas + state surfaces. All five skills share `engine/render-conventions.md` (consent + privacy HARD RULE, WCAG AA theme, frontmatter Mermaid syntax). Use when sharing state with operators or external readers.

- `/diamond-render` — emit `diamonds/active.yml` as stateDiagram-v2 / ascii / json
- `/ost-render` — emit `opportunities.yml` as Mermaid mindmap / ascii / markdown-list / json
- `/cycle-render` — emit `cycle-history.yml` as gantt + pie / ascii / json
- `/render` — dispatcher: routes intent to a specialist (recommends, never auto-invokes)
- `/receipt-render` — turn a completed diamond into a shareable, factual one-page work receipt with a volitional onward-handoff data flow (standalone; not a `/render` target)

## Setup & lifecycle

Project bootstrap, plugin install hygiene, install-form transitions. Run at onboarding or when changing install form.

- `/start` — one command from plugin-installed to running brief on your idea (combines `/setup` + `/interview`)
- `/setup` — first-run project-state initialization (`.claude/canvas`, `.claude/diamonds`, `.claude/memory`, `.claude/harness`)
- `/migrate-from-legacy` — migrate from legacy (`npx degit`) install to plugin install
- `/ping` — smoke-test that the Mycelium plugin loaded correctly

## Market & organization

Reaching users, team shape. Use at L5 / L1.

- `/launch-tier` — go-to-market classification (Lauchengco)
- `/team-shape` — Team Topologies (Skelton)

## Framework self-improvement

Mycelium itself. Use when dogfooding the framework or as part of `/framework-health` cycles.

- `/feedback-review` — aggregate active feedback loops
- `/eval-runner` — benchmark scenarios
- `/corrections-audit` — trend analysis on corrections
- `/prompt-optimizer` — A/B test instruction changes
- `/framework-health` — quarterly self-assessment
- `/theory-fidelity` — audit whether claimed theories are faithfully operationalized (source-grounds the load-bearing ones)
- `/scaffold-cost-check` — measure Mycelium's own scaffold token cost (CLAUDE.md + engine + harness + canvas + memory)
- `/interview` — onboarding flow (lives here because it is the entry point to the rest)

## See also

- [README.md](README.md) — phase-first index of the same 58 skills
- [glossary.md](../glossary.md) — vocabulary
