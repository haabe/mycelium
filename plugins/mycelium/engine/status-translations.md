# Status Translations: Technical -> Human-Readable

When reporting diamond state to the user, ALWAYS translate technical taxonomy to plain language FIRST, then optionally show technical details.

## Cut interface-load, keep problem-load

Plain language is necessary but not sufficient. Also cut words that make the user think about *Mycelium* instead of *their product*. Three moves, judged per sentence:

- **Cut** — pure framework-facing words with no other function: taxonomy ("harness", "discovery-and-discipline"), mechanism jargon ("evidence gates", "theory gates", "canvas state"), reassurance answering a question the user hasn't asked yet.
- **Keep** — problem-facing substance: what the user gets, the actual discovery questions, what's done vs still owed, why a confidence level is what it is. Never cut this.
- **Rewrite / relocate** — a sentence whose *form* is framework-facing but which carries a latent function the user needs (credibility, brownfield-safety reassurance). Preserve the function in fewer words; surface specifics where they become relevant. Example: don't enumerate framework names at a welcome ("JTBD, OST, Wardley, Cagan, Cynefin, BVSSH…") — the enumeration signals "built on established knowledge, not invented over a weekend", so keep the credibility ("grounded in 30+ established frameworks") and let each name appear when its skill actually runs, where it's problem-load, not interface-load.

Per-sentence test: "Does this make the user think about THEIR product, or about MYCELIUM?" Their product → keep. Mycelium → does the sentence carry a latent function the user needs? No → cut. Yes → rewrite, don't delete. This **optimizes; it does not gut** — never cut substance or a credibility/safety signal, only the words not doing work. (Krug, *Don't Make Me Think*, third law: "get rid of half the words, then get rid of half of what's left.")

**Differentiator carve-out (the rule's most important guardrail).** Mycelium IS a mechanism-differentiated product — its value is that the agent *can't skip the hard thinking* (steps must clear evidence checks). So "cut mechanism jargon" and "never cut a credibility signal" collide whenever the credibility IS the mechanism. The cut-bias must lose that collision: **the sentence that states why Mycelium is different from a plain AI assistant is always KEEP or REWRITE, never CUT — even though it is mechanism-facing.** Rewrite the term, keep the function: "evidence gates, so steps can't be skipped" → "each step has to clear an evidence check first." A blunt mechanism-cutting pass applied across many outputs will sand off exactly this distinctiveness; this carve-out is the stop. (Caught 2026-06-28 by a blind adversarial review of the `/start` welcome rewrite, which had deleted the enforcement clause as "jargon" — the differentiator — leaving an unsupported "makes the agent think" claim indistinguishable from any vibe-y tagline.)

Verbosity is a presentation knob, never a discipline knob: strictness and gate enforcement do not change. The framework still requires the same evidence; it just stops re-explaining itself to a user who is trying to think about their idea.

## Diamond Scale Translations

| Technical | Plain Language |
|-----------|---------------|
| L0: Purpose | "Defining why this product exists" |
| L1: Strategy | "Mapping the strategic landscape" |
| L2: Opportunity | "Discovering what problems to solve" |
| L3: Solution | "Designing how to solve the problem" |
| L4: Delivery | "Building and shipping the solution" |
| L5: Market | "Getting the product to users" |

## Phase Translations

| Technical | Plain Language | What's Happening |
|-----------|---------------|-----------------|
| Discover | "Exploring broadly" | Gathering evidence, challenging assumptions, diverging |
| Define | "Narrowing focus" | Synthesizing discoveries, framing the problem |
| Develop | "Generating solutions" | Ideating, prototyping, comparing options |
| Deliver | "Building and validating" | Implementing, testing, shipping, measuring |

## Combined Status Examples

| Technical State | Plain Language |
|----------------|---------------|
| L0 Purpose - Discover | "Understanding why this product needs to exist. Interviewing stakeholders, exploring the problem space." |
| L0 Purpose - Define | "Crystallizing the product's purpose. Defining mission, vision, values, and ethical boundaries." |
| L2 Opportunity - Discover | "Mapping what users actually need. Conducting interviews, analyzing data, building the opportunity tree." |
| L2 Opportunity - Define | "Prioritizing which problems to solve first. Scoring opportunities by impact, confidence, and strategic fit." |
| L3 Solution - Develop | "Designing solutions for [opportunity name]. Comparing [N] approaches, testing assumptions." |
| L4 Delivery - Deliver (software) | "Building [feature name]. Writing code, tests, and documentation. Validating against acceptance criteria." |
| L4 Delivery - Deliver (content) | "Producing [content name]. Writing, reviewing, and publishing. Validating against learning objectives or editorial standards." |
| L4 Delivery - Deliver (ai_tool) | "Building [tool name]. Writing prompts, running evaluations, and testing safety. Validating against quality criteria." |
| L4 Delivery - Deliver (service) | "Delivering [service name]. Executing the service blueprint, documenting the workflow, and gathering client feedback." |
| L5 Market - Discover | "Understanding how to reach users. Analyzing channels, competitors, and positioning options." |

## Confidence Translations

| Score | Gilad Level | Plain Language |
|-------|-------------|---------------|
| 0.1 | Speculation | "Just an idea -- no evidence yet" |
| 0.3 | Anecdotal | "Some signals, but not validated" |
| 0.5 | Data-supported | "Data supports this direction" |
| 0.7 | Test-validated | "Tested and confirmed with real users/data" |
| 0.9 | Launch-validated | "Proven in production" |

Always add context: WHY this level is appropriate and WHAT would increase it.

Example: "Confidence: Moderate (0.6, data-supported). Based on 1 detailed interview covering your full user base. Would increase with external user testing."

## Progress Summary Format

When asked for status or when reporting after a transition, use this format:

```
Current focus: [plain-language description of what we're doing]
  [1-2 sentences of context about what's been accomplished]
  Next step: [what comes next in plain language]
  Confidence: [plain word] ([number], [Gilad level]) -- [why and what would increase it]

Progress: [N] of [M] diamonds complete
  [Diamond name]: [STATUS in caps] -- [one-line plain description]
  [Diamond name]: [STATUS in caps] -- [one-line plain description]
  ...

[If skills are recommended for next step:]
Suggested next actions:
  - /skill-name -- [why this is relevant now]
  - /skill-name -- [why this is relevant now]
```

## Skipped Diamond Explanation

When a diamond is skipped, always explain in plain language:
- WHAT was skipped
- WHY it was skipped (with anti-pattern reference if applicable)
- WHEN it might become relevant

Example: "Strategy mapping skipped -- for a solo hobby project, strategic portfolio management would be gold-plating. Would become relevant if this grows into a product with multiple user segments."

## Delivery-Phase Quality Expectations

When reporting status during delivery phases, include what quality checks apply RIGHT NOW based on what the developer is working on:

| Working On | What's Expected |
|-----------|----------------|
| Writing UI code | "Tests alongside. Accessibility built in. Error states designed. Semantic markup." |
| Writing API/backend code | "Input validation on all endpoints. Auth checks. No secrets. Tests alongside." |
| Writing tests | "Good. Cover happy path, edge cases, and error paths." |
| Preparing to complete delivery | "Run /diamond-progress for the executable DoD checklist. Tests must pass. Services checked if user-facing. BVSSH quick-check required." |
| Fixing a bug | "Use /reflexion. Diagnose root cause first. Log correction after fix." |

This makes current expectations visible without the developer needing to remember all guardrails.

## Completion Readiness Summary

When a developer asks "am I done?" or when approaching Deliver->Complete:

```
Ready to mark this delivery complete?

REVIEW (must pass to complete):
  □ Tests exist and pass
  □ Type checking clean (if applicable)
  □ No secrets in code
  □ [If user-facing]: Services checked + a11y assessed
  □ [If data/permissions]: Threat model done
  □ Decision logged
  □ BVSSH quick-check answered

PROMPTED (should do, won't block):
  □ Delivery journal updated
  □ Patterns captured
  □ Retrospective done
```
