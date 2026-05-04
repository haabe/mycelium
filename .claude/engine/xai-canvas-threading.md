# XAI Canvas Threading

Where Explainable-AI (XAI) signals live in the canvas. Decided 2026-05-04 during XAI Phase 0 planning.

## Principle: vocabulary ≠ gap

Mycelium's existing mechanisms already cover most XAI properties under different names: decision logs cover traceability, theory gates cover justifiability, the confidence-with-evidence rule covers calibration transparency, plain-language-first covers stakeholder accessibility. **Don't import XAI vocabulary onto existing mechanisms** — the substance is there. New canvas fields and a new skill (`/xai-check`) close the **specific** gaps that aren't already covered: end-user-facing explanation surface, fidelity audit, recourse mechanism, system card.

No new canvas file. XAI signals thread through existing files where they semantically belong. This keeps the canvas count flat and avoids a separate XAI silo that drifts from the rest of the canvas state.

## Two paths, two homes

**Path 1 — XAI of the agent itself (Mycelium user path).** How transparently the agent explains its own work to the human using Mycelium. Already largely covered:

| XAI property | Lives in |
|---|---|
| Inline reasoning attribution | CLAUDE.md Communication Rule (`(per: <source>)`) |
| Per-decision rationale, alternatives, confidence | `harness/decision-log.md` |
| Calibration of past confidence vs reality | `canvas/cycle-history.yml`, `canvas/thresholds.yml` |
| Mistake learning | `memory/corrections.md` |
| Successful patterns | `memory/patterns.md` |

Eval coverage: `evals/assumption-tests/2026-05-04-xai-inline-attribution.md`.

**Path 2 — XAI of the product the user is building.** Whether the *product the founder ships* explains its AI behavior to *its users* appropriately. This is the gap-heavy path.

## Path 2 threading scheme

| XAI property | Canvas file | Field / location |
|---|---|---|
| AI components present and what kind | `jit-tooling/active-stack.yml` | `ai_components` block (Step 1c output of detector) |
| Risk-tier classification | `services.yml` | per-service `xai.tier: minimal\|limited\|high` |
| Per-stakeholder explanation surfaces (Liao question matrix) | `services.yml` | per-service `xai.surfaces:` keyed by stakeholder |
| Recourse path | `services.yml` | per-service `xai.recourse:` (path, SLA, logging) |
| Fidelity audit results | `services.yml` | per-service `xai.fidelity:` (samples, blind-prediction accuracy, last_audited_at) |
| System card existence and sections | `services.yml` | per-service `xai.system_card:` (path, sections_present) |
| Explanation-layer threats | `threat-model.yml` | new threat category `explanation_attacks` (misleading explanation, prompt-injection rationale, explanation side-channel, explanation fatigue) |
| AI disclosure copy and labeling | `go-to-market.yml` | per-channel `ai_disclosure:` (Art. 50 compliance, AI-generated content labels) |
| Regulatory classification (AI Act tier, GDPR Art. 22 applicability) | `privacy-assessment.yml` (already exists) and `services.yml` (xai.tier hint) | Existing `/regulatory-review` outputs feed `xai.tier`; threading is one-way. |

## Skill responsibilities

| Skill | Reads | Writes |
|---|---|---|
| `delivery-bootstrap` (detector Step 1c) | filesystem | `active-stack.yml :: ai_components` |
| `/xai-check` | `active-stack.yml`, `services.yml`, `privacy-assessment.yml` | `services.yml :: <service>.xai.*` |
| `/threat-model` (XAI extension when AI detected) | `active-stack.yml :: ai_components` | `threat-model.yml :: explanation_attacks` |
| `/launch-tier` / `/regulatory-review` | `active-stack.yml :: ai_components` | `go-to-market.yml :: <channel>.ai_disclosure` |
| `/definition-of-done` (AI-aware extension) | `active-stack.yml :: ai_components`, `services.yml :: xai` | DoD checklist (no canvas write) |

## What lives outside canvas

- **AI System Card** for the product itself: published as `docs/ai-system-card.md` (or product-team equivalent), template at `.claude/templates/ai-system-card.md` (Phase 2.4). Mitchell et al. (2019) format. Referenced from `services.yml :: xai.system_card.path`. Not a canvas file because it's a public-facing artifact, not internal product state.

- **Per-output fidelity samples**: stored under `evals/xai-fidelity/<service>/YYYY-MM-DD.json`, mirroring the metrics-pull pattern. Each sample is the input + output + agent's stated rationale + blind-reviewer prediction + verdict. Aggregate stats land in `services.yml :: xai.fidelity`.

## Out of scope for canvas threading

- **Per-decision provenance for the user's product** (i.e., logs of every AI decision made by the user's product, in production). That's product runtime data, not Mycelium state. Mycelium recommends product teams keep such logs but does not store them.

- **A standalone `xai.yml` canvas file.** Considered and rejected: the per-service shape under `services.yml` is more accurate (XAI is a quality dimension of a service, not a separate concept). A standalone file would drift from the rest of the canvas and duplicate service references.

## Schema impact

`services.yml` schema gains an optional `xai` block per service. `threat-model.yml` schema gains an optional `explanation_attacks` category. Neither is required when `ai_components.detected: false`. Schema updates ship with `/xai-check` (Phase 2.1), not with this threading note.

## References

- Doshi-Velez & Kim (2017) — evaluation tier honesty
- Liao, Gruen, Miller (2020) — question-matrix structure
- Mitchell et al. (2019) — system card format
- Lanham et al. (2023) — fidelity audit method
- Selbst & Barocas (2018) — recourse-as-substance
- Bansal et al. (2021) — adaptive-explanation framing
- EU AI Act Art. 13 + 50 + Annex III — risk tiering
- NIST AI RMF — explainability vs interpretability split
