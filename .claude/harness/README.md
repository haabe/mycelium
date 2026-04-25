# Harness — Guardrails, Constraints, and Decision Quality

The harness is what keeps the agent honest. While the [engine](../engine/) defines the workflow and the [canvas](../canvas/) holds the state, the harness enforces constraints that prevent shortcuts, catch bias, and maintain quality.

The term "harness" comes from [Birgitta Böckeler's harness engineering concept](https://martinfowler.com/articles/harness-engineering.html): scaffolding that constrains an AI agent's behavior through a mix of computational enforcement (hooks, scripts) and inferential guidance (instructions, checklists).

## What's Here

### Guardrails (Phase-Scoped)
- **[guardrails.md](guardrails.md)** — Full reference of all 36 guardrails across three enforcement tiers. Read this for the complete picture.
- **[guardrails-core.md](guardrails-core.md)** — Always loaded. Secret detection (BLOCK), corrections preflight (BLOCK), canvas updates, decision logging.
- **[guardrails-discovery.md](guardrails-discovery.md)** — Loaded during L0-L2. Evidence quality, no skipping discovery for complex domains, bias checks.
- **[guardrails-delivery.md](guardrails-delivery.md)** — Loaded during L3-L4. Testing, security, accessibility, input validation, error states.
- **[guardrails-market.md](guardrails-market.md)** — Loaded during L5. AI disclosure, launch readiness, trust signals.
- **[guardrails-index.md](guardrails-index.md)** — Quick lookup index for all guardrails by ID.

### Three Enforcement Tiers

| Tier | Count | Effect | Example |
|------|-------|--------|---------|
| **BLOCK** | 2 | Mechanically prevented by hooks | No plaintext secrets in code (G-S1) |
| **REVIEW** | 17 | Gates diamond progression | Tests must exist before delivery complete (G-V7) |
| **NUDGE** | 17 | Advised but not blocking | Evidence quality checks, BVSSH reminders |

### Decision Quality
- **[anti-patterns.md](anti-patterns.md)** — Known failure modes with detection rules. "Confidence theater," "discovery skip," "scope creep through accretion." If the agent catches itself in one, it stops and self-corrects.
- **[cognitive-biases.md](cognitive-biases.md)** — Per-stage bias checklist. Confirmation bias in research, sunk cost in delivery, optimism in market planning. Paired with the `/bias-check` skill.
- **[theory-tensions.md](theory-tensions.md)** — What happens when theories contradict each other? Wardley says "evolve" but YAGNI says "don't build it yet." This file maps known tensions and resolution strategies.

### Engineering Quality
- **[engineering-principles.md](engineering-principles.md)** — DRY, KISS, YAGNI, SoC, SOLID, Law of Demeter. Applied as NUDGE-tier guardrails during delivery. Not dogma — each principle includes when to bend or break it.
- **[security-trust.md](security-trust.md)** — Per-stage security requirements. OWASP at L4, trust signals at L5, threat modeling for anything handling user data.

### Decision History
- **[decision-log.md](decision-log.md)** — Every significant decision with context, alternatives considered, theory justification, evidence, and confidence level. The audit trail for "why did we do it this way?"

## How It Fits Together

```
Agent attempts an action
  → Hooks (computational enforcement) check BLOCK-tier guardrails
  → If allowed, action proceeds
  → Post-action hooks inject NUDGE-tier reminders
  → At phase transitions, REVIEW-tier guardrails gate progression
  → Anti-pattern detector watches for failure modes
  → Bias checklist runs before research and decisions
  → Everything is logged in decision-log.md
```

The harness works with the [hooks](../hooks/) system for computational enforcement and the [engine](../engine/) for inferential checks during phase transitions.
