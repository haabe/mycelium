# Regulatory awareness

**Audience**: evaluators in regulated jurisdictions (EU primarily) checking whether Mycelium-built products fall under AI regulation.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

> **Mycelium does not certify compliance. For compliance decisions, consult qualified EU AI law counsel.** This page is a navigational aid, not legal advice.

## Mycelium itself is not a regulated AI system

Mycelium is configuration files plus orchestrated prompts. It does not classify, score, or generate decisions about people. It does not fall under the EU AI Act's definition of an AI system in its own right.

Products built with Mycelium **may** be regulated, depending on what they do. The framework's job is to surface the regulatory question early — at L3 Solution scale via the Regulatory gate (gate 12) and at L4 via `/xai-check` if the product contains AI components.

## EU AI Act mapping table

The Act has multiple Articles relevant to AI products. Mycelium's mechanisms partially align — the table below is a starting point, not an exhaustive compliance checklist.

| EU AI Act provision | What it requires | Mycelium mechanism |
|---|---|---|
| Article 13 (Transparency for high-risk systems) | Users must be able to interpret system output and use it appropriately | `/xai-check` Stage 4 (system card), `docs/ai-system-card.md` template, decision-log contrastive `why_not_alternatives` |
| Article 50 (Disclosure for AI interaction) | Users must know they are interacting with an AI; AI-generated content must be marked | `/regulatory-review` flags Article 50 exposure; project's go-to-market.yml may need disclosure plan |
| Annex III (High-risk classifications) | Specific use cases (employment, credit, education, justice, etc.) trigger high-risk requirements | `/regulatory-review` Stage 1 classifies risk tier |
| Article 9 (Risk management) | High-risk systems need documented risk management | `canvas/threat-model.yml` + `canvas/privacy-assessment.yml` are starting points; not a formal RMS |
| Article 10 (Data governance) | Training data quality + bias considerations | Out of scope for Mycelium (the framework does not train models); applies to the product being built |
| Article 14 (Human oversight) | High-risk systems need meaningful human oversight | The framework's in-loop preventive layer is itself a human-oversight pattern; the product being built may need its own |

## What `/regulatory-review` checks

Five-stage classification:

1. **Risk tier** — Annex III check; classify as prohibited / high-risk / limited-risk / minimal-risk
2. **Stakeholder × question matrix** — who needs to understand what about the system
3. **Pre-existing alignment** — what mechanisms already cover the requirements
4. **Gap analysis** — what is missing for the product's risk tier
5. **Recourse path** — how affected users can challenge or contest outputs

Output goes into `canvas/threat-model.yml` (regulatory subsection) + `decision-log.md` for the regulatory exposure decision.

## What `/xai-check` adds

For products containing AI components (the agent_runtime_target product type), `/xai-check` is a five-stage tier-scaled explainability audit:

1. Risk classification (per Doshi-Velez & Kim)
2. Stakeholder × question matrix (per Liao et al. 2020 contrastive surface check)
3. Fidelity audit (does the explanation match the model behavior, per Lanham et al. 2023)
4. AI System Card generation (Mitchell et al. 2019 format adapted)
5. Recourse path (Selbst & Barocas)

Mycelium itself was xai-checked in v0.16.0. Its system card is at [docs/ai-system-card.md](ai-system-card.md). Honest disclosure: parts of the card are functionally validated, parts need user testing — the card is explicit about which.

## What is out of scope for this page

- **Specific compliance decisions** — see qualified counsel
- **Other jurisdictions' AI law** (US sectoral, UK, Canada, China, etc.) — the framework is EU-Act-shaped today; other jurisdictions get scoped onto the gate as the Act-comparable obligations land
- **Pre-Act guidance** (NIST AI RMF, ISO 42001, EU AI Pact voluntary commitments) — useful but not load-bearing here

## See also

- [docs/ai-system-card.md](ai-system-card.md) — Mycelium's own system card (Mitchell et al. 2019 format)
- [docs/context-surface.md](context-surface.md) — what data the agent reads under Mycelium
- `.claude/harness/security-trust.md` — security and trust per stage
- `plugins/mycelium/skills/regulatory-review/SKILL.md` — full regulatory review skill
- `plugins/mycelium/skills/xai-check/SKILL.md` — explainability audit
