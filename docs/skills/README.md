# Skills index

**Audience**: practitioners looking up a skill, evaluators surveying capability surface.
**Time to read**: 5 min for the table; depth lives in each `SKILL.md`.
**Last updated**: 2026-06-08.

This index lists all 54 skills. Each skill's full behaviour lives in its `SKILL.md` — `plugins/mycelium/skills/<name>/SKILL.md` in plugin form (recommended), or `.claude/skills/<name>/SKILL.md` in legacy form (supported during transition). Loaded JIT by Claude Code. This page is an orientation map by phase; [by-category.md](by-category.md) is the alternate index by category of work.

## Onboarding & navigation

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/interview` | New project: purpose, vision, North Star, project classification | Evidence (L0) |
| `/diamond-assess` | Resume a session: where am I and what next | — |
| `/diamond-progress` | Move a diamond forward through gate checks | All applicable to the transition |

## Discovery (L0–L2)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/user-interview` | Story-based interviews with bias mitigation (Torres) | Evidence, JTBD |
| `/mocked-persona-interview` | Disciplined mocked personas when real users unavailable | Evidence (with speculation tag) |
| `/user-needs-map` | Map needs independently of solutions (Allen) | Evidence |
| `/jtbd-map` | Jobs to be Done mapping (Christensen tripartite) | JTBD |
| `/cynefin-classify` | Classify problem domain (Snowden) | Domain Fit |
| `/wardley-map` | Strategic landscape mapping (L1) | Evidence (L1) |
| `/ost-builder` | Build Opportunity Solution Tree from research (L2) | Evidence, Four Risks (per leaf) |
| `/assumption-test` | Design smallest viable test for an assumption (Torres + Gilad AFTER) | Four Risks |
| `/ice-score` | Impact × Confidence × Ease prioritization (Ellis) | — |
| `/handoff` | Structured handoff for offline human tasks (interviews, observations, outreach) | — |
| `/log-evidence` | Record findings from completed offline conversations back into canvas | Evidence |

## Solution & planning (L3)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/gist-plan` | GIST planning: goals, ideas, steps, tasks (Gilad) | — |
| `/preflight` | Pre-implementation validation checklist | Learning |

## Build & delivery (L4)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/delivery-bootstrap` | Auto-detect tech stack, generate validation tooling, scaffold ADRs | — |
| `/reflexion` | Self-correcting loop: implement → validate → self-critique → retry (max 3) | — |
| `/definition-of-done` | Executable checklist: tests, types, lint, secrets, BVSSH, accessibility, decision log | Outcomes (BVSSH), Service Quality |
| `/dora-check` | DORA metrics (deployment freq, lead time, CFR, FDRT, reliability) | Delivery Health |
| `/retrospective` | Post-delivery: what worked, what did not, pattern + correction extraction | Learning |

## Audit & governance (any scale)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/bias-check` | Review cognitive biases before research/decisions | Bias |
| `/devils-advocate` | Challenge assumptions before major decisions (counter-argument) | Bias |
| `/bvssh-check` | Holistic BVSSH outcome evaluation | Outcomes (BVSSH) |
| `/service-check` | Downe's 15 service principles | Service Quality |
| `/threat-model` | STRIDE threat modeling | Security |
| `/privacy-check` | Privacy by Design / GDPR (Cavoukian) | Privacy |
| `/security-review` | OWASP Top 10:2025 secure-design review | Security |
| `/usability-check` | Nielsen's 10 usability heuristics | Service Quality |
| `/a11y-check` | Accessibility audit (WCAG 2.1 AA) | Service Quality |
| `/regulatory-review` | EU AI Act risk classification (Annex III, Art 13/50) | Regulatory |
| `/xai-check` | Explainability audit for AI-containing products (5-stage tier-scaled) | Explainability |

## Evidence & metrics

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/metrics-detect` | Detect external metric sources (GitHub, analytics, payments, app stores) | — |
| `/metrics-pull` | Snapshot all configured sources, compute deltas, draft canvas evidence | Evidence |

## Market & organization (L5 / L1)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/launch-tier` | Classify releases, plan go-to-market (Lauchengco) | — |
| `/team-shape` | Team Topologies assessment (Skelton) | — |

## Canvas & orchestration

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/canvas-update` | Update canvas with new evidence | Evidence |
| `/canvas-health` | Lint canvas for staleness, missing fields, orphaned references | — |
| `/canvas-sync` | Synchronize canvas across team via git (cross-session sync helper) | — |
| `/fan-out` | Parallel agent orchestration with worktree isolation | — |

## Render & output (v0.40.0+)

Read-only visualization of canvas + state surfaces. All four skills share `engine/render-conventions.md` (consent + privacy HARD RULE, supported formats, WCAG AA theme convention, frontmatter Mermaid syntax). Validator Check 43 enforces `identifier_exposure: YES|NONE|MIXED` declaration on every render-fleet skill.

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/diamond-render` | Emit `diamonds/active.yml` as Mermaid stateDiagram-v2 / ascii / json (current phase, gates, confidence). Recommend at end of `/diamond-assess`. | — |
| `/ost-render` | Emit `opportunities.yml` as Mermaid mindmap / ascii / markdown-list / json. Consent-gate via attribution registry. | — |
| `/cycle-render` | Emit `cycle-history.yml` as Mermaid gantt + pie / ascii / json. Honest small-N + class-distribution disclosure. | — |
| `/render` | Dispatcher: routes intent to a specialist (recommends, never auto-invokes); lists what's renderable. Cross-cutting `--view traceability` research-gated to Phase 4a–4d. | — |

## Self-improvement (framework-level)

| Skill | When to use | Gates it satisfies |
|---|---|---|
| `/feedback-review` | Aggregate feedback signals across active loops, check health | — |
| `/eval-runner` | Run benchmark scenarios to measure framework effectiveness | — |
| `/corrections-audit` | Analyze correction trends, surface recurring patterns, flag graduation candidates | — |
| `/prompt-optimizer` | A/B test instruction changes against eval benchmarks | — |
| `/framework-health` | Quarterly self-assessment: cycle velocity, discard trends, calibration, regression rate | — |

## How to use this index

If you are mid-diamond and want a skill: look at the phase section that matches your scale. If you are auditing: look at audit & governance. If you are doing framework-level work: look at self-improvement.

Skills are auto-discovered from `.claude/skills/*/SKILL.md` frontmatter — Claude Code reads them at session start. Adding a skill is creating a new directory + SKILL.md; this index then needs updating per the [version-discipline](../../.claude/engine/version-discipline.md) rule on material framework changes.

## See also

- [by-category.md](by-category.md) — alternate index ordered by type of work
- [glossary.md](../glossary.md) — vocabulary used in skill descriptions
- `.claude/engine/theory-gates.md` — canonical gate definitions
