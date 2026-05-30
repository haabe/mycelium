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

### PreToolUse hooks fail OPEN — a raised exception or non-zero exit does NOT block

A Claude Code `PreToolUse` hook that hits an unhandled exception, or exits non-zero *without* emitting a decision payload, **fails open**: the tool call proceeds. The only way to *block* (fail closed) is to emit `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", ...}}` on stdout and `exit 0`. So a guard that does `raise ValueError(...)` / `sys.exit(1)` on its own internal failure is silently permissive at exactly the moment its invariant broke — the worst time to wave the edit through.

**Detection rule**: for every guard hook, ask "what happens when the guard *itself* errors?" Trace the error path, not just the happy path. If the error path is a bare exception or `exit 1`, the guard fails open. A guard whose *purpose* is containment (scope-gate, manifest-integrity, secret-detection) must catch its own internal errors and convert them to a `deny` decision + `exit 0`, so a broken guard denies rather than admits.

**Counter-pattern**: testing only that the guard blocks the *bad input* it was written to catch, while never testing what it does when its *own* parsing/lookup fails. The fail-open path is invisible until the parser drifts — and then the guard is wide open precisely when structure has changed underneath it.

*Source: v0.31.10 Critical audit group (`framework_guard.py`). `_manifest_lib.parse_manifest` was hardened to raise `ValueError` on structural drift (non-empty manifest → zero parsed buckets). The first cut let that exception propagate — which in a PreToolUse hook means exit non-zero, which means the edit proceeds: a manifest-integrity guard that fails open exactly when the manifest structure drifted. Fixed by catching the `ValueError` and emitting a `deny` JSON + `exit 0`. Same epistemic class as the two patterns above — verify the behavior at the layer you depend on (the runtime's block semantics), not the layer that describes it (the function "raises an error, so surely it's blocked").*


## Orchestration Patterns

_Patterns for diamond management, theory gate navigation, and workflow coordination._

### Memory-application discipline gap — having an auto-memory loaded ≠ applying it at the inference moment

When the agent has a relevant auto-memory or prior-conversation context loaded in the session, **having it loaded is not the same as applying it at the right moment.** The agent must explicitly check whether relevant context applies BEFORE making an inference, not just at the load moment.

**Why it matters**: an auto-memory captures a discipline that was costly to learn. If the agent loads it but doesn't reach for it when it would change the inference, the memory is decorative — it documents what the agent "knows" without changing what the agent does. The cost was paid; the benefit doesn't materialize.

**Detection rule**: when an inference is being made from an artifact (a title, a name, a brief tool output, a wrapper-text summary, a self-described category), check: is there an auto-memory or prior-conversation context that would change this inference? If yes, surface the check explicitly. If you can't be bothered to check, your inference is at AP#7 sub-(e) trust-without-verification risk.

**Worked failures (2026-05-26 session)**:

1. **Auto-dogfood dir not grepped before sketching architecture**: agent designed a parallel `mycelium-roadmap/.claude/auto-dogfood/playground-runs/` architecture proposal without first running `ls .claude/auto-dogfood/`. Existing mature 50k-LOC orchestrator + 23 scenarios + active 19/19 PASS baseline already lived there. Founder pushback: "Did you look inside .claude/auto-dogfood for what already exists?" Acknowledged as AP#7 sub-(e); architecture proposal was 95% reinvention.

2. **Cohort-member role-title treated as expertise-class evidence without applying loaded juniors-context discipline**: agent had a juniors-context auto-memory loaded (rule: "role titles in junior-cohort contexts signal grow-into-this, not 10+y expertise; treat as junior unless evidence says otherwise"). When a cohort tester was described with a senior-shaped role title (CTO-class), agent inferred "if a senior-title-holder is hitting the vocabulary wall, the issue is structural regardless of theory-fluency" — without applying the juniors-context discipline that was already in memory. Founder pushback recalled the discipline; recalibrated read placed the tester in the junior-class evidence column (where the existing N=1 cohort-junior signal already sat), removing the spurious "theory-fluency" inference. Acknowledged as AP#7 sub-(e); inference rebuilt with corrected framing.

**Counter-discipline**: before any inference that depends on interpretation of a brief artifact (title, summary, wrapper-text, name, self-described category), the agent runs a one-line self-check: "What auto-memory or prior context would change this inference if applied?" If the check surfaces anything relevant, apply it explicitly with a `Per auto-memory [name]:` citation form (parallel to the Verify-before-propagate convention). If nothing, proceed with explicit `No relevant memory found` note.

**Graduation status**: 2 instances same day, same root cause (loaded-but-not-applied), different surfaces (directory existence vs. interpretive context). Pattern is well-defined; counter-discipline is mechanizable as a self-check. Candidate for framework-level Communication Rule in CLAUDE.md ("Before any inference that depends on interpretation of a brief artifact, run a one-line check for relevant auto-memory or prior context.") — decision deferred to post-recovery.

*Source: 2026-05-26 in-session founder pushbacks on two distinct AP#7-shape instances. Both involved agent failing to apply available context at the inference moment despite the context being technically loaded. Cousins: anti-pattern #7 sub-(e) trust-without-verification (this is the cousin "trust-without-checking-loaded-context" sub-shape).*


### Framework hosts primitives, roadmap composes them — the universal-product-model test as the gate

When designing a new mechanism (skill, hook, scheduled task, validator check), the architectural placement question is:

> **Does this mechanism serve any Mycelium adopter's product-delivery workflow, regardless of what product they're building, without requiring a "dogfood-mode" toggle?**

If **yes** → framework-side. Ship in `plugins/mycelium/` and it travels to every adopter via `/plugin install`. This is the **universal-product-model test**.

If **no** (only useful for the Mycelium team operating on Mycelium-the-product, OR only useful in specific dogfood contexts) → **roadmap-side** (or the adopter's analogous ops dir). Live in `mycelium-roadmap/.claude/auto-dogfood/` or equivalent. Compose framework skills via `claude -p` non-bare from a wrapper script; schedule via launchd/cron/Actions.

**Why this matters**: the framework distribution is inherited by every adopter at install time. Mycelium-team operational concerns embedded in the framework (scheduled scrape-watches targeting `haabe/mycelium`, retrospective skills tuned to OUR commit cadence, trio-coverage hooks specifically auditing OUR framework MINOR bumps) become invisible context-mismatches for downstream users — kin to the same epistemic risk we shipped `framework_dependency` frontmatter (v0.28.0) to address in the opposite direction. The architectural separation also protects the open-source-learning-project trajectory: embedded scheduled-headless-cron infrastructure pushes the framework toward a service-shape that the trajectory commitment explicitly rejects.

**Concrete test results from the design session 2026-05-25** (six compound-dogfood candidates surfaced from "how do we improve auto-dogfooding"):

| Compound | Test result | Placement |
|---|---|---|
| #4 anomaly → devils-advocate auto-chain | ✅ Passes — AP#7 sub-(g) risk applies to any adopter writing canvas evidence from metrics, regardless of product type | Framework-side (shipped v0.29.0 as `/metrics-pull` Step 10) |
| #2 compound retrospective | ❌ Fails — composes framework skills on Mycelium-team cadence against Mycelium-team commit history | Roadmap-side |
| #3 scrape watch | ❌ Fails — target (`haabe/mycelium`) is Mycelium-team-specific | Roadmap-side |
| #5 cohort-of-one friction walk | ❌ Fails — Mycelium-team measurement | Roadmap-side |
| #6 trio-coverage on commits | ❌ Fails — auditing framework-modification commits is team-specific; generalized trio-coverage already exists as a theory gate at diamond transitions | Roadmap-side |

**Hooks DO live inside the framework** (PostToolUse, SessionStart, etc.) and are absolutely automation — so "automation lives inside" is partially true. The distinction is: framework-internal automation is **event-driven on user action and universally relevant**; roadmap-side automation is **scheduled, autonomous, and Mycelium-team-specific**.

**Anti-pattern**: shipping mechanisms behind a `dogfood_mode: true` toggle is a smell. If a toggle is needed to justify framework-side residence, the mechanism's universal value couldn't be justified — which means it belongs roadmap-side, no toggle.

**Generalizable for any adopter**: this isn't a Mycelium-team-only architectural rule. Every adopter has (or should have) an ops/roadmap analogue — a place where their own dogfood loops and scheduled compositions live, separate from the framework primitives. The framework/roadmap split is itself a Mycelium architectural pattern.

*Source: Architectural sharpening session 2026-05-25 in conversation context, prompted by founder's "I am scared of introducing autodogfooding into Mycelium. I think it should live outside." Initial proposal had 4 of 6 compounds framework-side; user pushback sharpened the test; final classification put only 1 framework-side. v0.29.0 shipped the lone framework-side compound (`/metrics-pull` Step 10 anomaly chain) as the worked example. Cousins: anti-pattern #7 sub-class (e) trust-without-verification (architectural-trust shape) + `framework_dependency` frontmatter v0.28.0 (the inverse epistemic boundary — skills protected from running outside framework context; framework protected from carrying team-specific automation inside).*


### Spawn child diamonds at strategic-events density, not parent confidence completion

When a parent diamond's confidence reaches its **effective threshold** (after `project_type` and `dogfood` adaptations) AND multiple strategic events arrive that require child-scale framing, spawn the child immediately rather than waiting for parent → Complete. Don't conflate "L0 at threshold" with "L0 done"; they're different conditions, and the child diamond exists precisely to handle work the parent's scale can't hold.

The trigger is **events density**, not confidence saturation. Concrete indicators:
- The parent's canvas (e.g., landscape.yml at L1, opportunities.yml at L2) has accumulated enough material that a coherent child-frame statement is feasible — work would be aggregation, not generation.
- ≥2 strategic events in the next 30 days require child-scale work (e.g., a public post, a launch, a partnership conversation, a planned test program). Doing those without a child-diamond frame risks the *process cliff* anti-pattern (corrections.md 2026-04-30) — L3-level work being designed under an L2 that doesn't exist.
- The cognitive-forcing pre-question yields a prediction like *"this'll mostly be putting existing pieces into a new structure"* — that IS the signal that the child is overdue, not premature.

What this prevents: child diamonds spawned too late carry the cost of having driven solution-design (L3) under a parent (L0/L1) that couldn't formally hold strategy/opportunity. What this enables: parent stays in Develop while child does Discover work; parent re-baselines on child findings; the engine matches CLAUDE.md "parents continue while children execute" cleanly.

What this prevents on the OTHER end: children spawned too early (parent confidence well below effective threshold AND no strategic events in window) end up doing speculative work with too little parental footing. The dual condition (threshold AND events) is what makes the spawn timely.

*Source: Mycelium dogfooded its own L1 spawn 2026-05-07 — L0 confidence sat at 0.61 vs effective threshold 0.612 (functionally at-threshold, not far above) WHILE strategic events (Hoskins post window, Juniors.dev presentation just delivered, audience-attendee fork from a cohort participant, four-track convergence) made L1 framing necessary. Spawning at exactly that intersection produced an L1 diamond with low initial confidence (0.20) but coherent strategic input, avoiding the process cliff that would have come from doing receipts-architecture L2/L3 work without an L1 frame. CLAUDE.md "Diamond Engine" — parents continue while children execute. Counter-pattern: waiting for parent → Complete delayed L1 past strategic-event windows.*


## Verification Patterns

### Isolated capability test before instruction iteration

**Pattern**: When an agent isn't producing artifact X during a test, verify in isolation that the agent CAN produce X before iterating on instruction wording.

**Mechanism**: Construct a minimal `claude -p` invocation that asks the agent to produce X directly, in a manually-mimicked workdir matching the test environment's structure. If the agent succeeds, capability is proven — the issue is somewhere between the test driver and the agent (prompt-template content, missing context, conflicting instructions, scenario configuration). If it fails, capability is the gap — instruction wording / SKILL.md / framework state is the right place to iterate.

**What this prevents**: iterating on the wrong surface. Today's example (2026-05-22→23): three framework SKILL.md patches (v0.23.39/40/41) tried to make the agent write a decision-log entry during `/interview`. None worked. A 30-second isolated test (`claude -p "Write to .claude/harness/decision-log.md..."`) succeeded immediately. That single test would have ended the SKILL.md iteration arc 6 hours earlier and pointed to the actual gap: the orchestrator's hardcoded prompt template.

**When to apply**:
- ANY time an instruction-following failure looks systematic across multiple runs (>2/3 fail rate with the same failure mode).
- BEFORE the second framework patch in a "fix the test" loop. If iteration #1 didn't move the verdict, do the isolated capability test before iteration #2.
- When the failure mode is "agent didn't do X" (vs "agent did X wrong" — the latter usually IS an instruction-wording issue).

**Diagnostic shape**: isolated test → result interpretation:
- Agent succeeds in isolation → instruction-following IS possible; trace upstream from "where does the agent get its instructions for this test?" through the test driver / scenario config / prompt template / framework loading until you find the layer that's missing the directive.
- Agent fails in isolation → capability gap; investigate at the framework / model / tool-availability level. Instruction wording is downstream of capability and won't fix it.

**Sister mechanism**: `mycelium-roadmap/.claude/auto-dogfood/scripts/check_skill_prompt_drift.py` mechanically surfaces drift between framework SKILL.md write-paths and orchestrator task templates — closes the specific failure mode of "framework edits don't reach the test" for the orchestrator class. The pattern above is the general discipline; the script is one mechanism that implements it for one cross-surface invariant.

*Source: 2026-05-22→23 auto-dogfood Phase 5 cycle. After three framework SKILL.md iterations failed to move the test verdict, an isolated direct-claude-p test took 30 seconds to prove capability and point at the real root cause (orchestrator's hardcoded prompt). Logged 2026-05-23. Theory: Gilad (evidence-guided — three failed iterations IS evidence the wrong layer was being edited); Hashimoto (engineer out recurrence — make the diagnostic shape a reflex, not a thing-to-remember).*
