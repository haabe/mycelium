# Receipts

**Audience**: evaluators, contributors, practitioners curious about what "Mycelium gets smarter with each project cycle" actually means in artifacts.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

This directory is the WORK view of how the framework has evolved: per project, per cycle, per friction-to-mechanism trace. The PEOPLE view (per contributor) lives in [CONTRIBUTORS.md](../../CONTRIBUTORS.md). Same facts, two indexes — frontmatter cross-links them.

## Patterns view

Below: active patterns (multiple cases, may graduate), graduated mechanisms (case → harness), and one-off learnings (case → project memory only). All link to the case file where the pattern surfaced.

### Graduated mechanisms

| Mechanism | Origin case | Status |
|---|---|---|
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
| `/interview` Phase 0 path selector (<8h / 8-48h / 48h+) | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| Lightweight discovery-to-delivery continuation mode | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Partial |
| Constraint-first preflight (ask time budget before scope) | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| "Eval Overfitting" anti-pattern | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| "Negative Documentation" anti-pattern | [hoskins-takehome](cases/2026-04-30-drew-hoskins-takehome.md) | Shipped |
| Guardrail **G-V12** (every check ships coverage-proof test) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| Guardrail **G-P-pre** (Mandatory Pre-Ship Protocol) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| `/xai-check` skill + theory Gate 13 + AI System Card | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |
| Check 26 (version-bump enforcement) | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0/0.16.1) |
| `ingest_warnings.py` + `warning-handbook.md` + `warnings-log.md` | [framework-self-correction](cases/2026-05-01-framework-self-correction.md) | Shipped (v0.16.0) |

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

## Other indexes

- [By date](by-date.md) — chronological
- [By contributor](by-contributor.md) — per-person (links into CONTRIBUTORS.md)
- [By mechanism](by-mechanism.md) — per-graduated-thing

## How to add a case

When a project, session, or framework cycle produces friction that shapes the framework, add a file under `cases/` with frontmatter per [docs/contributing/style.md](../contributing/style.md#receipts-case-file-frontmatter). Update the tables above. Cross-link the contributor entry in [CONTRIBUTORS.md](../../CONTRIBUTORS.md).
