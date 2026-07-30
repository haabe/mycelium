# Receipts

**Audience**: evaluators, contributors, practitioners curious about what "Mycelium gets smarter with each project cycle" actually means in artifacts.
**Time to read**: 5 min.
**Last updated**: 2026-07-30.

This directory is the WORK view of how the framework has evolved: per project, per cycle, per friction-to-mechanism trace. The PEOPLE view (per contributor) lives in [CONTRIBUTORS.md](../../CONTRIBUTORS.md). Same facts, two indexes — frontmatter cross-links them.

## Patterns view

Below: active patterns (multiple cases, may graduate), graduated mechanisms (case → harness), and one-off learnings (case → project memory only). All link to the case file where the pattern surfaced.

### Graduated mechanisms

| Mechanism | Origin case | Status |
|---|---|---|
| Hook-leak fix (`0 corrections`/`0 skills` now distinguish not-initialized from empty) + AGENTS.md say-yes-or-skip framing | [frida-first-run](cases/2026-05-10-frida-first-run.md) | Shipped (v0.23.9) |
| Post-build-silence nudge + BLUF/Footnote output convention (`G-C1`) | [alex-cohort-first-run](cases/2026-05-26-alex-cohort-first-run.md) | Shipped (v0.31.0) |
| Guardrail **G-D7** (OST-routing ritual, `harness/guardrails-discovery.md`, NUDGE tier) | [alex-cohort-sessions-2-3](cases/2026-05-30-alex-cohort-sessions-2-3.md) | partially-shipped — signals 3/4/5/6 shipped as the OST-routi |
| `/mycelium:scaffold-cost-check` + APEX-extended `/dora-check` (3 mandatory AI fields) + Check 43 | [faros-whiplash-integration](cases/2026-06-07-faros-whiplash-integration.md) | Shipped (v0.39.19) |
| `/mycelium:framework-health` temporal-independence rule (4e/4b/4d) | [framework-health-temporal-independence](cases/2026-06-07-framework-health-temporal-independence.md) | Shipped (v0.39.22) |
| Render fleet: `/mycelium:{diamond,ost,cycle}-render` + `/mycelium:render` dispatcher + Check 43 | [render-fleet-foundation](cases/2026-06-07-render-fleet-foundation.md) | Shipped (v0.40.0) |
| `engine/autonomous-mode.md` (autonomous-mode declaration + substitution ladder) | [fable5-autonomous-run](cases/2026-06-11-fable5-autonomous-run.md) | Shipped (v0.41.0) |
| Pre-push delivery gate (Layer 3) + `check_coverage_floor.py` + `check_legacy_paths.py` (test-on-add / rot guards) | [legacy-path-rot-guard](cases/2026-06-18-legacy-path-rot-guard.md) | Shipped (v0.49.6–v0.49.8) |
| Preflight project-dir robustness + count-bug fix (Cowork cross-runtime dogfood) | [cowork-runtime-gap](cases/2026-06-19-cowork-runtime-gap.md) | Shipped (v0.49.21); Cowork F1/F3 platform-gap documented |
| Canvas-vs-reality drift detection (human-task reconciliation) | [canvas-drift-reconciliation](cases/2026-05-28-canvas-drift-reconciliation.md) | Shipped (v0.31.3) |
| `/mocked-persona-interview` skill | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `meta_dogfood` project type + `dogfood: true` flag | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| Memory boundary (project memory vs auto-memory) | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Documented in CLAUDE.md |
| Reflexion hook scoped to project-relevant failures | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `/diamond-progress` pivot/park/kill subcommands | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `/feedback-review` skill | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `/framework-health` skill | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `/canvas-health` provenance + staleness lints | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `cycle-history.yml` + adaptive thresholds + framework-reflexion | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `.claude/evals/dogfood-reports/` directory | [macos-fileviewer kill](cases/2026-04-macos-fileviewer.md) | Shipped |
| `/interview` Phase 0 path selector (<8h / 8-48h / 48h+) | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped, **since removed** — replaced by canvas-state detection; the time-budget question asked the user to predict the future before any value was delivered |
| Lightweight discovery-to-delivery continuation mode | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Partial |
| Constraint-first preflight (ask time budget before scope) | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped, **since superseded** — same removal as the Phase 0 selector above |
| "Eval Overfitting" anti-pattern | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| "Negative Documentation" anti-pattern | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| Guardrail **G-V12** (every check ships coverage-proof test) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| Guardrail **G-P-pre** (Mandatory Pre-Ship Protocol) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| `/xai-check` skill + theory Gate 13 + AI System Card | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| Check 26 (version-bump enforcement) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0/0.16.1) |
| `ingest_warnings.py` + `warning-handbook.md` + `warnings-log.md` | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| Plugin-form install (marketplace + plugin manifest) | [bentes-install-model](cases/2026-05-08-bentes-install-model.md) | Shipped (v0.20.x canonical 2026-05-09) |
| `/mycelium:start` welcome + universal-flow brief | [plugin-form-dogfood](cases/2026-05-09-plugin-form-dogfood.md) | Shipped (v0.20.6) |
| `/mycelium:migrate-from-legacy` + `--migrate-to-plugin` flag | [plugin-form-dogfood](cases/2026-05-09-plugin-form-dogfood.md) | Shipped (v0.20.10) |
| Validator Check 27 (skills-tree parity) + manifest-file watching | [plugin-form-dogfood](cases/2026-05-09-plugin-form-dogfood.md) | Shipped (v0.20.9 / v0.20.11) |
| Hard-gate ordering pattern (detection-then-route) in skill SKILL.md | [plugin-form-dogfood](cases/2026-05-09-plugin-form-dogfood.md) | Shipped (v0.20.11) |
| Anti-pattern #7 *Consistency-as-Evidence* + `/devils-advocate` Technique 4 + G-P-pre item 9 | [consistency-as-evidence-graduation](cases/2026-05-09-consistency-as-evidence-graduation.md) | Shipped (v0.21.0) |
| Anti-pattern #8 *Stale State Read* + `/corrections-audit` Step 6e + Validator Check 29 | [stale-state-read-graduation](cases/2026-05-09-stale-state-read-graduation.md) | Shipped (v0.21.0) |
| `/devils-advocate` Technique 5 (ambient assertion-shape triggering) + `/corrections-audit` Step 6d | [bias-cluster-graduation](cases/2026-05-09-bias-cluster-graduation.md) | Shipped (v0.21.0) |

### Active clusters (spec, not yet mechanism)

| Cluster | Origin case | Status |
|---|---|---|
| `documented-rule-diverges-from-enforcement` (8 instances) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) + several pre-Check-26 instances | Spec at `engine/consistency-check-spec.md` (v0.17.0); promotion bar mechanical |

Canonical cluster log: [`.claude/memory/cluster-instances.md`](../../.claude/memory/cluster-instances.md).

### One-off learnings

| Learning | Origin case | Where it lives |
|---|---|---|
| Optimistic UI desync in client-server real-time apps | [tic-tac-toe](cases/2026-04-tic-tac-toe.md) | Project-local `corrections.md` |
| `@EnvironmentObject` lost on SwiftUI Table cell scroll | [macos-can-i-open](cases/2026-04-macos-can-i-open.md) | Project-local `corrections.md` |
| `AXIsProcessTrusted()` lies for ad-hoc-signed apps | [macos-can-i-open](cases/2026-04-macos-can-i-open.md) | Project-local `corrections.md` |


### Evidence & investigation (no mechanism shipped)

Cases that produced evidence, overturned a prior claim, or closed an investigation without shipping a framework change. They belong in the receipts because a documented null or a narrowed hypothesis is a result; they are not mechanisms and are not project-local learnings.

| Case | What it produced |
|---|---|
| [opencode-phase1-runtime](cases/2026-05-16-opencode-phase1-runtime.md) | runtime-verification-overturned-prior-claims |
| [opencode-port-feasibility](cases/2026-05-16-opencode-port-feasibility.md) | research-with-hands-on-verification |
| [phase0-substrate-audit](cases/2026-05-16-phase0-substrate-audit.md) | audit-with-queued-rewrites |
| [edith-mari-book-project](cases/2026-05-20-edith-mari-book-project.md) | brief-synthesis-as-identity-mirror-validated |
| [architecture-discovery-narrowed](cases/2026-06-01-architecture-discovery-narrowed.md) | investigated — hypothesized gap captured as a failing-first scenario, then dogfooded; the gap is narrower than its first framing. A light-touch soluti |
| [dagfinn-minilisp-vibe-mistral](cases/2026-06-23-dagfinn-minilisp-vibe-mistral.md) | first-arms-length-full-run / no-Claude-in-the-loop / context-budget friction documented |

## Other indexes

- [By date](by-date.md) — chronological
- [By contributor](by-contributor.md) — per-person (links into CONTRIBUTORS.md)
- [By mechanism](by-mechanism.md) — per-graduated-thing

## How to add a case

When a project, session, or framework cycle produces friction that shapes the framework, add a file under `cases/` with frontmatter per [docs/contributing/style.md](../contributing/style.md#receipts-case-file-frontmatter). Update the tables above. Cross-link the contributor entry in [CONTRIBUTORS.md](../../CONTRIBUTORS.md).
