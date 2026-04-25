# Domains — Phase-Specific Agent Instructions

Domains are instruction sets that configure the agent's behavior for specific phases of work. Instead of loading every instruction at once (which degrades model performance past ~150 instructions), Mycelium loads only the domain relevant to the current phase.

## Structure

```
domains/
  discovery/CLAUDE.md   — Loaded during L0-L2 (Purpose, Strategy, Opportunity)
  delivery/CLAUDE.md    — Loaded during L3-L4 (Solution, Delivery)
  quality/CLAUDE.md     — Always-active overlay
```

### Discovery Domain
Active during L0-L2 phases. Covers:
- Torres-style interviewing and Opportunity Solution Trees
- Bias-aware research design
- Evidence quality requirements
- JTBD mapping and user needs analysis

### Delivery Domain
Active during L3-L4 phases. Covers:
- Agile/DevOps practices
- Clean code principles and engineering standards
- Security requirements (OWASP, STRIDE)
- Accessibility standards
- DORA metric measurement
- Testing strategy

### Quality Domain
Always active as an overlay. Covers:
- Validation and verification patterns
- Accessibility baseline
- Security baseline
- Service design principles (Downe)

## Why Domains Exist

AI models lose consistency when given too many instructions simultaneously. Research (Horthy, Haagsman) shows that models work best with ~40 focused instructions per phase rather than 200+ loaded at once.

Domains implement this by scoping instructions to the current phase. The agent loads `quality/CLAUDE.md` always, plus whichever domain matches the active diamond's scale.

See the [CLAUDE.md](../../CLAUDE.md) "Mandatory Pre-Task Protocol" section for the loading sequence.
