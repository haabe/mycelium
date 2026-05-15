# Patterns Library

Reusable patterns discovered through practice. Reference before starting new work.

## Discovery Patterns

_Patterns for research, interviewing, synthesis, and opportunity identification._

### Verify every claim in external-agent landscape analyses before canvas-flow

LLM-generated competitive-landscape analyses reach for plausible specifics (named products, beta status, distribution model, star counts, founding dates) that fit the narrative shape **even when those specifics aren't anchored to verifiable sources**. Treating any of it as `data-supported` evidence without per-claim verification turns the canvas into a confidence-laundering machine — anti-pattern #7 (Consistency-as-Evidence) at scale.

**Detection rule for "this is a guess, not knowledge"** — hedge language in the source analysis:
- *"possibly called X or Y"*
- *"often via a SaaS like X"*
- *"likely a"*, *"is testing"*, *"has been developing"*
- specific dates without per-claim citations
- product names without URLs

Each hedge is the LLM's own signal that it's reaching. Treat as **zero evidence**, not weak evidence.

**Verification protocol that worked across three rounds 2026-05-15/16**:
1. **Repo / URL HEAD checks** for any named product — does it actually exist at the claimed location?
2. **Canonical-source own-voice fetch** for any "what is person X doing" claim — pull their actual public writing (Medium, blog, LinkedIn), not the LLM's summary of it.
3. **Feature-page fetch** for any "Product X does Y" claim — verify Y is a named, vendor-claimed feature, not LLM-extrapolated capability.
4. **Category-error check** — theories the framework *implements* (Cagan, GIST, JTBD) are not products users substitute for. Distinguish "framework grounding" from "competitive product." LLM analyses routinely conflate the two.
5. **Public-figure attribution check** — Wardley speaking on his own Medium is `public_ok`; cohort-participant friction logs are `generic_only` until consent. Different attribution classes, same verification discipline.

**Three external-agent rounds verified 2026-05-15/16**:
- Round 1 (BMAD analysis): claimed BMAD-METHOD was "18+ months old" — actual age 13 months. Off by ~5 months. Other facts verified; analysis logged as comp-014 with correction.
- Round 2 (broad landscape): claimed Cagan/GIST as "intellectual competitors" — they're theories the framework implements; rejected. Claimed Paddo as "direct competitor" — he's a teacher-practitioner; reclassified to convergent-thesis ally as comp-022. Eight new comp entries added (comp-015..022) after verification.
- Round 3 (Torres + Wardley deep-dive): claimed "Product Talk AI" — fabricated name, real product is Vistaly; corrected to comp-023. Claimed "Wardley AI / MapSim" private beta — no Wardley-authored product exists; founder provided Wardley's actual LinkedIn post confirming personal-exploration tooling only; logged as comp-024. Inflated Productboard AI features; under-reported Linear's substrate-level agent platform features. Both corrected via vendor-page verification.

**What the discipline enables**: external-agent analyses become *raw landscape research input* rather than landscape-canvas content. The agent's role shifts from "trust and transcribe" to "extract claim-list, verify per-claim, write only the verified residue." Time cost is real (each round consumed significant token budget on verification) but the cost-of-trust on canvas writes is what makes the canvas usable as evidence later.

**What it prevents**: the canvas filling with fabrications that read as data-supported, then propagating into positioning, strategy, and resource allocation decisions downstream. Anti-pattern #7 at the landscape layer.

**Counter-pattern**: a single LLM round of verification ("ask another LLM if this claim is correct") is NOT verification. It's another instance of the same epistemic class. Verification means hitting the actual source: vendor URL, repo metadata, the named person's own voice in their own publishing surface.

*Source: Three external-agent landscape analyses 2026-05-15 → 2026-05-16, each with fabrications, all caught at verification time. The pattern is structurally similar to corrections.md 2026-05-09 "consistency-as-evidence" anti-pattern (#7) graduated discipline — but applied at the canvas-write boundary rather than at the conversational-claim boundary.*

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

