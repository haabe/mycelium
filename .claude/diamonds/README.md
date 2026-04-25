# Diamonds — Active Work State

This directory tracks active diamonds — the work units currently in progress. Think of it as the "what are we working on right now?" file.

## What's Here

- **[active.yml](active.yml)** — The current diamond state: which diamond is active, what scale (L0-L5), what phase (Discover/Define/Develop/Deliver), confidence level, and gate status.

## What's a Diamond?

A diamond is a cycle of divergent and convergent thinking applied to a problem at a specific scale:

```
  Discover (diverge) → Define (converge) → Develop (diverge) → Deliver (converge)
```

Diamonds operate at six scales:
- **L0**: Purpose — why we exist
- **L1**: Strategy — where to play
- **L2**: Opportunity — what to solve
- **L3**: Solution — how to solve it
- **L4**: Delivery — build and ship
- **L5**: Market — reach users

Parent diamonds spawn child diamonds when complexity requires it. If delivery reveals a bad assumption, the diamond regresses back with new evidence.

## How State Changes

Diamond state is managed through the `/diamond-progress` skill, not by direct editing. The skill validates all theory gates, checks confidence thresholds, and logs the transition in the decision log before updating this file.

Direct edits to `active.yml` are tracked by the `diamond-state-audit.sh` hook for observability.

See [`../engine/diamond-rules.md`](../engine/diamond-rules.md) for the complete lifecycle rules.
