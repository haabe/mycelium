# Engine — Core Decision Logic

The engine is the brain of Mycelium. It defines how diamonds work, what gates must pass before progression, how confidence is scored, and how the system routes decisions based on complexity.

## What's Here

### Diamond Lifecycle
- **[diamond-rules.md](diamond-rules.md)** — The core workflow: six scales (L0-L5), four phases per diamond, transition rules, WIP limits, parent-child spawning, regression paths. **Start here.**
- **[leaf-lifecycle.md](leaf-lifecycle.md)** — The 10-phase pipeline every solution leaf follows, from creation through delivery to market feedback. Includes discard criteria.

### Decision Gates
- **[theory-gates.md](theory-gates.md)** — The 12 gates that must pass before a diamond transitions: Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory. Each gate has pass/fail criteria and a suggested skill.
- **[confidence-thresholds.yml](confidence-thresholds.yml)** — How much evidence is enough? Thresholds per scale, adapted by project type and dogfood mode.
- **[adaptive-thresholds.md](adaptive-thresholds.md)** — Thresholds that improve from historical data. ICE advance threshold, confidence calibration, evidence staleness — all adjust as cycle history accumulates.

### Routing and Classification
- **[cynefin-routing.md](cynefin-routing.md)** — Snowden's Cynefin framework applied: how to classify problems as Clear, Complicated, Complex, or Chaotic, and what that means for which approach to use.
- **[perspective-resolution.md](perspective-resolution.md)** — When product, design, and engineering perspectives conflict, this framework resolves them without suppressing any voice.
- **[canvas-guidance.yml](canvas-guidance.yml)** — Which canvas files are relevant at which scale, for which product type (software, content, AI tool, service).

### Self-Improvement
- **[feedback-loops.md](feedback-loops.md)** — Four-speed learning system: immediate (reflexion), incremental (diamond phases), strategic (BVSSH/DORA/Wardley), transformative (eval benchmarks).
- **[framework-reflexion.md](framework-reflexion.md)** — Quarterly self-assessment: cycle velocity, discard trends, confidence calibration, gate effectiveness.
- **[cycle-learning.md](cycle-learning.md)** — Every completed or discarded leaf generates calibration data. Predicted vs actual ICE, effort accuracy, risk dimension accuracy.
- **[pattern-detector.md](pattern-detector.md)** — Statistical patterns across cycle history surface as correlation rules and anti-pattern signals.
- **[evidence-decay.md](evidence-decay.md)** — Evidence ages. Confidence degrades over time unless refreshed.

### Communication
- **[status-translations.md](status-translations.md)** — Plain-language translations for every diamond state. "L2 Opportunity Discover" becomes "Discovering what problems to solve."
- **[wayfinding.md](wayfinding.md)** — Navigation aids for orienting within the framework.
- **[surfaces.yml](surfaces.yml)** — Surface definitions for framework presentation.

### Change Tracking
- **[mutation-log.md](mutation-log.md)** — Record of structural changes to the engine itself.

## How It Fits Together

```
User starts work
  → Engine identifies current diamond (diamonds/active.yml)
  → Cynefin classifies the problem domain
  → Diamond rules determine current phase
  → Theory gates check if phase transition is allowed
  → Confidence thresholds set the evidence bar
  → Feedback loops capture learning
  → Cycle learning calibrates future thresholds
```

The engine never acts alone — it works with the [harness](../harness/) (constraints), [canvas](../canvas/) (state), and [skills](../skills/) (operations).
