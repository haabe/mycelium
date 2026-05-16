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

### Don't infer runtime enforcement from schema/description strings

Binary inspection of an installed tool can find strings like *"This tool will error if you attempt an edit without reading the file"* or *"You must X before Y."* That evidence proves only **what the agent is told**, not **what the runtime enforces**. The two layers diverge routinely: tool authors often put preconditions in the LLM-facing schema text as a behavioural nudge while leaving the executable code path permissive. A model that ignores the instruction will succeed; a guard that depends on the precondition being enforced will silently no-op.

**Detection rule**: any claim of the form "the runtime enforces X" backed only by strings in a binary, schema, or docs is **prompt-level evidence**, not enforcement evidence. To reach enforcement evidence you must:
1. Construct the exact condition the schema warns against.
2. Run it against the real runtime.
3. Observe whether the runtime refuses, errors, or proceeds.

If the runtime proceeds, the precondition is **agent-discipline, not framework-discipline** — and a less-disciplined agent (smaller model, different harness, or the same model on a long-context distraction) will violate it without consequence. Frameworks that depend on the precondition for safety properties must ship their own guard rather than relying on the host runtime.

**Counter-pattern**: a single round of "the binary says X, therefore the runtime enforces X" is the structural twin of the consistency-as-evidence anti-pattern (#7). The binary string is *compatible with* runtime enforcement, but also compatible with prompt-level-only enforcement. Distinguishing the two requires a runtime test, not more reading.

*Source: opencode adapter Phase 1 runtime test 2026-05-16 (`docs/receipts/cases/2026-05-16-opencode-phase1-runtime.md`). The Phase 0 desk + binary inspection concluded "Read-before-Edit is enforced — the binary contains the precondition string." Phase 1 runtime test: clean edit succeeded on a fresh session with no prior read. The precondition string was in the LLM-facing tool description, not the code path. Confidence in the entire adapter feasibility estimate dropped 0.55 → 0.32 on that single correction, plus two adjacent ones. The pattern is the same shape as Wardley/Vistaly fabrication verification (2026-05-15/16) — different surface, same epistemic class.*

### Symmetric API names don't imply symmetric semantics

When an event surface ships paired names like `before` / `after`, `on_start` / `on_end`, `pre_*` / `post_*`, the names suggest the two hooks fire on the same population of events with mirror-image timing. Treating that as a contract is a guess, not a fact. Hook taxonomies routinely diverge on populations:

- `tool.execute.before` fires for **all** tool calls; `tool.execute.after` fires only for **successful** ones.
- `session.start` may fire once per connection; `session.end` may not fire at all on abnormal disconnect.
- `request.received` may include preflight CORS; `request.completed` may not.

The naming convention promises **temporal ordering** (after fires later than before, when both fire), not **population symmetry** (after fires for the same calls before fired for). Any reflexion / retry / cleanup logic that depends on "for every X.before I get X.after" must be **verified at runtime**, not inferred from the name pair.

**Detection rule**: in any plugin/hook adapter design, list which event pairs the design relies on for population symmetry. For each pair, run an explicit test for the failure / abnormal-termination case to verify the second event fires. If it doesn't, design a sidecar mechanism: tag events with callIDs at `.before`, reconcile orphans against the message/result stream, treat absence-of-`.after` as the failure signal.

*Source: opencode Phase 1 runtime test 2026-05-16. Mycelium's reflexion port from Claude Code's `PostToolUseFailure` to opencode's `tool.execute.after` was designed on the assumption that the latter fires for failures. Headless test with a forced read failure: `tool.execute.before` fired, `tool.execute.after` never did. The naming convention strongly suggests otherwise; the runtime is authoritative. Same class as the prior pattern — both are "verify at the layer you're depending on, not the layer that describes it."*


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

