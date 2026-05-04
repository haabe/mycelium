# Decision Log

Record of significant decisions made during product development. Decisions are immutable once logged -- if a decision is reversed, log a new entry that references the original.

## Format

```
### [DATE] - [SHORT TITLE]
- **Diamond**: [ID, scale, phase]
- **Decision**: What was decided.
- **Why_not_alternatives** (structured, per-alternative): list every option considered and a one-line rejection rationale per option. Contrastive explanations ("why X rather than Y") land harder than purely positive ones (Liao et al. 2020); this field must be populated for any decision with ≥1 real alternative. Format:
    - `Option A: <one-line rejection rationale>`
    - `Option B: <one-line rejection rationale>`
- **Theory**: Which framework/theory informed this decision (e.g., "Cynefin - Complex domain", "Cagan - Four Risks").
- **Evidence**: What data or research supports this decision.
- **Confidence**: [0.0-1.0] How confident are we, and what would change this.
- **Scenario ref**: [optional — which scenario from scenarios.yml does this decision serve? Keeps architecture decisions connected to user context. Hoskins: "Draw a line between the problem and the why."]
- **Reversibility**: [easily reversible | costly to reverse | irreversible]
```

## Decisions

