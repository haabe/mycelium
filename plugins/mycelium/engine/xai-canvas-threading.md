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
| Per-decision rationale, alternatives, confidence | `.claude/harness/decision-log.md` |
| Calibration of past confidence vs reality | `.claude/canvas/cycle-history.yml`, `.claude/canvas/thresholds.yml` |
| Mistake learning | `memory/corrections.md` |
| Successful patterns | `memory/patterns.md` |

Eval coverage: `evals/assumption-tests/2026-05-04-xai-inline-attribution.md`.

**Path 2 — XAI of the product the user is building.** Whether the *product the founder ships* explains its AI behavior to *its users* appropriately. This is the gap-heavy path.

## Path 2 threading scheme

| XAI property | Canvas file | Field / location |
|---|---|---|
| AI components present and what kind | `.claude/jit-tooling/active-stack.yml` | `ai_components` block (Step 1c output of detector) |
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

## Special case: `agent_runtime_target` products (added 2026-05-04)

When the detector emits `agent_runtime_target` (Mycelium itself, agent-engineered products, harness frameworks operated by Claude Code / Codex / Cursor / etc.), the XAI surface is unusual: the AI is the runtime that consumes the project, not a dependency the project embeds. The framework's logic shapes how the runtime behaves.

For products in this category, the threading still applies but with these substitutions:

- **System card** describes the framework's *recommendation logic and known limitations*, not the underlying LLM (whose system card is the runtime vendor's responsibility — Anthropic for Claude Code, etc.). Mycelium's own system card would describe what the framework guides the agent to do, not what Claude does.
- **Recourse path** for users contesting framework recommendations is the existing `corrections.md` mechanism — file an entry, /corrections-audit picks up patterns, recurring entries graduate to mechanism. This satisfies Selbst & Barocas substance check.
- **Fidelity audit** maps to the inline-attribution rule (CLAUDE.md Communication Rule, eval `2026-05-04-xai-inline-attribution`) — does the agent's stated rationale faithfully reflect the framework state that drove it? Same Lanham faithfulness check, applied to framework-shaped products.
- **Disclosure** is partly the runtime's responsibility (Claude Code discloses it's AI) and partly the framework's docs (the README/CLAUDE.md should mention the framework guides AI behavior).

`/xai-check` works for `agent_runtime_target` products without modification — Stages 1-5 all map. The user_facing_decisions confirmation can default to yes for this category (the runtime IS the user surface).

## Out of scope for canvas threading

- **Per-decision provenance for the user's product** (i.e., logs of every AI decision made by the user's product, in production). That's product runtime data, not Mycelium state. Mycelium recommends product teams keep such logs but does not store them.

- **A standalone `xai.yml` canvas file.** Considered and rejected: the per-service shape under `services.yml` is more accurate (XAI is a quality dimension of a service, not a separate concept). A standalone file would drift from the rest of the canvas and duplicate service references.

## Schema impact

Asymmetric — only some target canvases have schemas today. Phase 2 status:

- `services.yml` — **schema shipped 2026-05-04** at `.claude/schemas/canvas/services.schema.json` with optional `xai` block per service, all sub-fields validated by enum (tier, verdict). Phase 2.1 ✓.
- `threat-model.yml` — schema exists. Phase 2.3 must update it to accept the `explanation_attacks` category, or `/threat-model` writes will get rejected post-extension.
- `go-to-market.yml` — schema exists. Phase 2 launch-tier extension must update it for per-channel `ai_disclosure`.

## Phase 2 prerequisites (status)

- **Phase 2.0 (audit prerequisites) — DONE 2026-05-04:**
  - ✓ `validate_canvas.py` ID-uniqueness check (graduated 3-instance "validator passes on incomplete checks" pattern; G-V12 coverage proof shipped)
  - ✓ `guardrails-delivery.md` G-V12 (every validator/enforcer ships with a coverage proof)
  - ✓ `CLAUDE.md` Mandatory Pre-Ship Protocol G-P-pre (graduated user feedback on missing pre-ship gap analysis)
  - ✓ `manifest.yml` `.claude/templates/` entry

- **Phase 2.1 (`/xai-check`) — DONE 2026-05-04:**
  - ✓ `services.schema.json` (permissive, with xai block) + 6 schema tests
  - ✓ `theory-gates.md` Gate 13 (Explainability — operational gate composing with G-S7/S8)
  - ✓ `templates/ai-system-card.md` (Mitchell et al. 2019 format)
  - ✓ `skills/xai-check/SKILL.md` (5-stage tier-scaled)
  - ✓ 6 eval scenarios (xai-tier-classification, xai-fidelity-detects-unfaithful, xai-recourse-detected, xai-cap-enforced, xai-matrix-detects-missing-recourse-surface, xai-system-card-detects-missing-sections)

- **Phase 2.2 (AI-aware Definition of Done) — pending:**
  - `/definition-of-done` consults Gate 13 verdicts when `ai_components.detected: true`
  - `/preflight` Constraints adds AI confirmation
  - `/diamond-progress`, `/diamond-assess` integration
  - `${CLAUDE_PLUGIN_ROOT}/domains/delivery/CLAUDE.md` and `${CLAUDE_PLUGIN_ROOT}/domains/quality/CLAUDE.md` XAI sections
  - `${CLAUDE_PLUGIN_ROOT}/engine/status-translations.md` Gate 13 entry

- **Phase 2.3 (`/threat-model` XAI extension) — pending:**
  - `threat-model.schema.json` adds `explanation_attacks` category
  - `/threat-model` skill writes the new category when AI present
  - `/security-review` integrates explanation-attack threats
  - `go-to-market.schema.json` adds per-channel `ai_disclosure`
  - `/launch-tier` extension

## References

- Doshi-Velez & Kim (2017) — evaluation tier honesty
- Liao, Gruen, Miller (2020) — question-matrix structure
- Mitchell et al. (2019) — system card format
- Lanham et al. (2023) — fidelity audit method
- Selbst & Barocas (2018) — recourse-as-substance
- Bansal et al. (2021) — adaptive-explanation framing
- EU AI Act Art. 13 + 50 + Annex III — risk tiering
- NIST AI RMF — explainability vs interpretability split
