# Patterns Library

Reusable patterns discovered through practice. Reference before starting new work.

## Discovery Patterns

_Patterns for research, interviewing, synthesis, and opportunity identification._


## Delivery Patterns

_Patterns for implementation, testing, deployment, and monitoring._


## Orchestration Patterns

_Patterns for diamond management, theory gate navigation, and workflow coordination._

### Spawn child diamonds at strategic-events density, not parent confidence completion

When a parent diamond's confidence reaches its **effective threshold** (after `project_type` and `dogfood` adaptations) AND multiple strategic events arrive that require child-scale framing, spawn the child immediately rather than waiting for parent → Complete. Don't conflate "L0 at threshold" with "L0 done"; they're different conditions, and the child diamond exists precisely to handle work the parent's scale can't hold.

The trigger is **events density**, not confidence saturation. Concrete indicators:
- The parent's canvas (e.g., landscape.yml at L1, opportunities.yml at L2) has accumulated enough material that a coherent child-frame statement is feasible — work would be aggregation, not generation.
- ≥2 strategic events in the next 30 days require child-scale work (e.g., a public post, a launch, a partnership conversation, a planned test program). Doing those without a child-diamond frame risks the *process cliff* anti-pattern (corrections.md 2026-04-30) — L3-level work being designed under an L2 that doesn't exist.
- The cognitive-forcing pre-question yields a prediction like *"this'll mostly be putting existing pieces into a new structure"* — that IS the signal that the child is overdue, not premature.

What this prevents: child diamonds spawned too late carry the cost of having driven solution-design (L3) under a parent (L0/L1) that couldn't formally hold strategy/opportunity. What this enables: parent stays in Develop while child does Discover work; parent re-baselines on child findings; the engine matches CLAUDE.md "parents continue while children execute" cleanly.

What this prevents on the OTHER end: children spawned too early (parent confidence well below effective threshold AND no strategic events in window) end up doing speculative work with too little parental footing. The dual condition (threshold AND events) is what makes the spawn timely.

*Source: Mycelium dogfooded its own L1 spawn 2026-05-07 — L0 confidence sat at 0.61 vs effective threshold 0.612 (functionally at-threshold, not far above) WHILE strategic events (Hoskins post window, Juniors.dev presentation just delivered, audience-attendee fork from a cohort participant, four-track convergence) made L1 framing necessary. Spawning at exactly that intersection produced an L1 diamond with low initial confidence (0.20) but coherent strategic input, avoiding the process cliff that would have come from doing receipts-architecture L2/L3 work without an L1 frame. CLAUDE.md "Diamond Engine" — parents continue while children execute. Counter-pattern: waiting for parent → Complete delayed L1 past strategic-event windows.*

