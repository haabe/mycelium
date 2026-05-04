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

Asymmetric — only some target canvases have schemas today. Phase 2 must address each path explicitly:

- `services.yml` — **no schema exists.** Phase 2.1 must build `services.schema.json` *before* `/xai-check` writes the `xai` block, otherwise the new fields land structurally ungated. (Building the schema is the right move — relying on the absence of schema enforcement extends an existing inconsistency rather than fixing it.)
- `threat-model.yml` — schema exists. Phase 2.3 must update it to accept the `explanation_attacks` category, or `/threat-model` writes will get rejected post-extension.
- `go-to-market.yml` — schema exists. Phase 2 launch-tier extension must update it for per-channel `ai_disclosure`.

## Phase 2 prerequisites (don't ship paper rules)

Each Phase 2 item depends on a non-XAI prerequisite. Listed here so they don't get dropped at planning-to-build time:

- **Phase 2.1 (`/xai-check`)** requires `services.schema.json` to exist. See "Schema impact" above. The XAI plan's claim of "schema updates ship with /xai-check" is honest only if Phase 2.1 builds the `services.yml` schema, not just adds fields to a non-existent one.

- **Phase 2.2 (AI-aware Definition of Done)** requires an XAI gate in `engine/theory-gates.md` that consults `ai_components.detected` and routes to `/xai-check`. Without that gate, AI-aware DoD is a paper rule — `/definition-of-done` is gate-driven, and gates are the enforcement surface. The conditional-overlay list in `jit-tooling/detector.md` is documentation, not enforcement.

- **Phase 2.3 (`/threat-model` XAI extension)** requires the `threat-model.schema.json` update noted under "Schema impact" — same shape as 2.1 but applied to an existing schema rather than a new one.

- **Phase 2.4 (AI System Card template)** requires a manifest entry for `.claude/templates/`. The directory does not exist today; without manifest coverage, future templates won't sync downstream on `upgrade.sh`. Add to `manifest.yml :: directories` (replace wholesale) when 2.4 lands.

- **Validator capability gap (cross-cutting):** `validate_canvas.py` currently does not enforce ID uniqueness within a single canvas file (caught when adding `comp-009` to `landscape.yml` 2026-05-04 — an earlier accidental `comp-007` collision passed validation). This is independent of XAI but should be closed before Phase 2.1, because adding fielded structure (xai blocks per service) increases the surface where ID collisions matter. See corrections.md.

## References

- Doshi-Velez & Kim (2017) — evaluation tier honesty
- Liao, Gruen, Miller (2020) — question-matrix structure
- Mitchell et al. (2019) — system card format
- Lanham et al. (2023) — fidelity audit method
- Selbst & Barocas (2018) — recourse-as-substance
- Bansal et al. (2021) — adaptive-explanation framing
- EU AI Act Art. 13 + 50 + Annex III — risk tiering
- NIST AI RMF — explainability vs interpretability split
