# Mycelium Guardrails — Delivery Phase

Loaded when operating within delivery domains (L3-L4 Develop/Deliver phases). Supplements guardrails-core.md.

## Security & Trust

**G-S2: Never skip threat modeling when a solution handles user data or requires system permissions** `REVIEW` `safety`
Before selecting a solution that processes user data OR requires system permissions, run STRIDE threat modeling. Document in `canvas/threat-model.yml`.
*Source: OWASP STRIDE, Microsoft SDL*

**G-S3: Never add a data collection point without Privacy by Design assessment** `REVIEW` `privacy`
Every new piece of data collected must pass: Is it necessary? Is collection minimized? Is consent obtained? Is there a retention policy? Is there a deletion mechanism?
*Source: Cavoukian (Privacy by Design), GDPR Article 25*

**G-S4: Never ship without input validation on all external inputs** `REVIEW` `safety`
All data from external sources must be validated, sanitized, and escaped before use.
*Source: OWASP Top 10, OWASP Secure by Design*

**G-S5: Always apply data minimization** `NUDGE` `privacy`
Collect only data strictly necessary for the current purpose. Default to anonymous/aggregated over individual.
*Source: GDPR Article 5, Cavoukian (Privacy by Design)*

**G-S6: Always design for secure defaults** `NUDGE` `safety`
HTTPS, authentication required, least privilege, sessions expire, CORS restricted, CSP enabled.
*Source: OWASP Secure by Design, Cavoukian (Privacy by Design Principle 2)*

**G-S7: Always disclose AI nature in user-facing systems** `REVIEW` `regulatory` `ethical`
If the product interacts directly with people, it must disclose AI nature. Required by EU AI Act Article 50.
*Source: EU AI Act Article 50, Downe (Good Services Principle 3)*

**G-S8: Always assess EU AI Act risk classification for AI-powered products** `NUDGE` `regulatory`
Before delivering an AI-powered product, assess high-risk category under Annex III. Run `/regulatory-review`.
*Source: EU AI Act (Regulation 2024/1689), Annex III*

## Quality

**G-V1: Never mark delivery complete without running the validation suite** `REVIEW` `quality`
Every deliverable must pass its product-type-appropriate validation before completion.
*Source: Forsgren (Accelerate), n-trax reflexion pattern*

**G-V2: Never ship user-facing work without checking Downe's 15 principles** `REVIEW` `quality`
Evaluate against Good Services principles. Pay special attention to: no dead ends (P10), usable by everyone (P11), explains decisions (P14), easy to get human help (P15).
*Source: Downe (Good Services)*

**G-V3: Never duplicate logic or content** `NUDGE` `quality`
Check for existing implementations before creating new deliverables. Extract shared logic into reusable components.
*Source: DRY (Hunt & Thomas, The Pragmatic Programmer)*

**G-V4: Never add speculative features or abstractions** `NUDGE` `scope`
Build only what is needed now. Three similar lines of code is better than a premature abstraction.
*Source: YAGNI (Extreme Programming), KISS*

**G-V5: Always prefer the simplest working solution** `NUDGE` `quality`
When multiple approaches solve the problem, choose the simplest one. Complexity is a cost.
*Source: KISS, Clean Code (Martin)*

**G-V6: Always maintain clean separation between layers** `NUDGE` `quality`
Business logic, data access, presentation, and infrastructure must be separated. Depend on abstractions, not concretions.
*Source: SoC (Dijkstra), SOLID (Martin), Clean Architecture*

**G-V6b: Document significant architectural tradeoffs** `NUDGE` `quality`
If the solution involves framework selection, infrastructure choices, or integration patterns, document the rationale in `docs/adr/` using Nygard format (Context/Decision/Consequences). `/delivery-bootstrap` scaffolds the format.
*Source: Nygard (Architecture Decision Records), theory-gates.md L3 Evidence Gate*

**G-V7: Always validate alongside implementation** `REVIEW` `quality`
Write tests first (TDD) or alongside code. Never defer validation to "later."
*Source: Forsgren (Accelerate), TDD (Beck)*

**G-V8: Always ensure accessibility for user-facing work** `REVIEW` `quality`
Semantic HTML, ARIA labels, keyboard navigation, color contrast, screen reader compatibility must be built in.
*Source: Downe (Good Services Principle 11), WCAG 2.1 AA*

**G-V9: Always design error states** `REVIEW` `quality`
Every user flow must have designed error, empty, and loading states. Never show raw technical errors to users.
*Source: Downe (Good Services Principles 10, 14)*

**G-V10: Always check usability heuristics for user-facing interfaces** `REVIEW` `quality`
Evaluate against Nielsen's 10 usability heuristics. Run `/usability-check`.
*Source: Nielsen (10 Usability Heuristics, 1994)*

**G-V11: Always declare success criteria before delivery work** `REVIEW` `quality`
Before starting delivery, declare 1-3 measurable success criteria and how each will be verified. Record in decision-log.md. Checked at DoD by `/diamond-progress`. Without upfront criteria, "done" becomes whatever was built — not what was needed.
*Source: Cagan (outcome over output), Patton (build to learn vs build to earn), Paddo (the denominator problem — invisible rework from undefined success)*

**G-V12: Every validator, enforcer, or check ships with a coverage proof** `REVIEW` `quality`
Any new or extended mechanism that nominally checks/enforces a rule (validator scripts, schema rules, hook conditions, skill stages that flag issues) must ship with a test that constructs a known-bad input and asserts the mechanism rejects it. "The validator passed" only proves it ran — not that it caught. No mechanism merges without a coverage proof per rule it claims to enforce.
*Source: Graduated 2026-05-04 from corrections.md "validator passes on incomplete checks" recurring pattern (3 instances: upgrade.sh hardcoded list drift 2026-04-28 + 2026-05-03; validate_canvas.py ID-uniqueness gap 2026-05-04). Lopopolo reframe — fix at the harness layer, not behavior. Cross-references G-P7 (verification protocol) for completion-side discipline.*

**G-V12b: A mechanism documented as automatic owes a WIRING proof, not just a coverage proof** `BLOCK` `quality`
G-V12 proves a mechanism *behaves when called*. It says nothing about whether anything calls it, or whether its output is read by whatever claims to read it. Any mechanism whose docs describe it as automatic — "auto-updated", "auto-populated", "now mechanized", "closes gap X", "Shipped (vN)" — additionally owes: **(1) a caller** on a real execution path (CI step, hook, skill step, validator); **(2) a wiring test** that invokes it the way production does and asserts the output lands where the consumer reads it; **(3) a negative control** — an assertion that it FAILS on deliberately broken input. All three are mechanically gated: `check_wiring.py` Rules A–D, `check_negative_control.py`, and `check_test_authenticity.py`. An allowlist entry may substitute for (1) only with a stated reason; "it has a unit test" is explicitly not a reason, since that is the false green being caught.

**G-V12c — a test that does not run production code is not a test (BLOCK).** The three guards answer three different questions and passing one implies nothing about the others: `check_wiring` asks whether anything *calls* the mechanism; `check_negative_control` asks whether the guard *can fail*; `check_test_authenticity` asks whether **production code runs when the test runs**. A test may import nothing, assert a tautology (`assert True`, `assertEqual(n, n)`, `expect(x).toBe(x)`), or patch away every module it names, and still be green, covered, and counted — coverage records which lines executed, never whether the assertion after them could have failed. Scope is derived from test-naming conventions rather than a maintained list, and a file in an unsupported language is reported UNCHECKED rather than silently passed. Consumer projects run all four from `/mycelium:definition-of-done` before any item is ticked; this repo additionally runs them in CI. **Stated upgrade path:** pattern-matching is an approximation of what **mutation testing** measures directly — mutate the production code, re-run the suite, and a test that still passes did not test what it claimed. It catches what this guard cannot: assertions that are real but too weak to detect a fault, which is precisely the failure found across 22,374 LLM test-generation tasks (models asserting from pre-training knowledge rather than from observed behaviour). Not adopted yet because full-suite-per-mutant is expensive; Meta made it tractable with LLM-assisted mutant selection (FSE 2025, 73% acceptance). **Adoption trigger, not a date:** when either a consumer reports a test that passed `check_test_authenticity` and still missed a regression, or mutation tooling for the stack runs inside the existing suite's wall-clock budget.
*Source: Graduated 2026-07-26 from the silently-inert-mechanism sweep. THREE mechanisms shipped with passing G-V12 coverage proofs and no caller at all.
First, `ingest_warnings.py` — documented as automatic and listed in the receipts index as already shipped, yet invoked by nothing, so the CI-warning learning loop had never run once.
Second, `validate_mermaid.py` — 87% covered, documented as closing the F11 state-id and F13 contrast blind-spots, invoked by no render skill.
Third, the v0.60.1 citation matcher, which required a colon that occurs zero times in real agent output and so matched 0% of live citations for ~2.5 months while reporting "no problems found". From the reader side, `/xai-check` resolved a path nothing ever wrote, so Theory Gate 13 could never fire. Every one of these was pre-announced in prose that nobody had made checkable — hence Rule D. Resolves the hole the 2026-07-25 BVSSH assessment named when it predicted "a second silently-inert check would still be found by hand": it was, twice, the next day. Sibling of G-V12 (there, "the validator passed" only proves it ran) and G-V13 (there, "source-verified" only proves you read it); here, "it has a test" only proves it works if something calls it.*

**G-V13: A solution design is not complete until its integration points are declared (L3)** `REVIEW` `quality`

Before implementation begins, name — as a written artefact, not as intent — every point at which the new thing joins the existing system: who calls it, what reads its output, where its state lives, which existing surface changes. This is Cockburn's **walking skeleton**: "a tiny implementation of the system that performs a small end-to-end function… it should link together the main architectural components," and Hunt & Thomas's tracer bullets are the same idea.

The failure it prevents is structural rather than careless. A model's limited context makes it unable to tell whether the element it just generated is used anywhere else, so plausible-but-unreferenced code is the *expected* output. Measured across 304,362 verified AI-authored commits in 6,275 repositories, "unused variables or parameters" is the **second most frequent issue class**, and "undefined variable or reference" — writer and reader disagreeing — is the **most common runtime bug category**. It accumulates rather than washing out: AI-authored code survives **longer** than human-written code (53.9% vs 69.3% line death rate), so an orphan is *less* likely to be cleaned up than a human's would be.

**Satisfied by** a `.claude/harness/wiring-contract.yml` rule covering the new thing (`/mycelium:wiring-contract` drafts one from the repo's own majority convention; `check_wiring_contract.py` enforces it). **Not satisfied by** a description of what the thing does, however detailed — the obligation is to name the *joins*.

**G-V14: Integrity checks run in the per-change verification command, not only in CI (L4)** `BLOCK` `quality`

`check_wiring.py`, `check_wiring_contract.py`, `check_negative_control.py` and `check_test_authenticity.py` are **architecture fitness functions** in the Ford/Parsons/Kua sense: objective, continuously-executed measures of properties the design must preserve. Their value depends on *when* they run.

Agents respond to automated signals far more reliably than to documentation — an agent that hits a failing command will fix it, while a guardrail paragraph in the context window may simply not be read. So these belong in the command run **after every change**, where the loop closes in seconds, not only in CI where the signal arrives after the work has been declared done and a human has been asked to look.

**Satisfied by** the project's verification command (test script, `make check`, pre-commit) invoking them, with non-zero exit treated as work-not-done. **Not satisfied by** a CI step alone — and not by this paragraph, which is why the four scripts exist.


**G-V13: Always runtime-verify a runnable artifact before claiming it works** `REVIEW` `quality`
A change that adds or modifies a runnable artifact (script, plugin, hook, config, command) AND claims it works / runs / ships is not done until the artifact has been EXECUTED in a representative environment — a runtime existence-proof (`Ran: <cmd> → <result>`) — OR the claim is explicitly downgraded to "source-verified, untested." Source / spec / dev-branch analysis proves the artifact *should* work, not that it *does*; "source-verified" is a non-runtime tag, not a verification synonym. Scoped to fire only when the change *claims* the artifact works (not every trivial config tweak), and "representative environment" can be a light smoke run, not full CI — a NUDGE-weight expectation that converts a weasel word into an honest one, not a new blocking gate on every edit. Sibling of G-V12: there, "the validator passed" only proves it ran; here, "source-verified" only proves you read it.
*Source: Graduated 2026-06-15 from corrections.md — the Mycelium→opencode scaffold authored from dev-branch source analysis, tagged "source-verified", shipped-claim caught only when a user-prompted runtime test found 3 ship-blocking bugs (config wouldn't load, provider unresolved, hook crashed every run). Safety came from a user prompt, not a gate. Generalizes the existence-proof rule (corrections.md `fail-open-scoring-of-absent-work`) from measurements to runnable artifacts; pairs with the verification-surface rule (communication-rules.md) sub-class (i) "source-analysis narrated as runtime-verification" (anti-patterns.md #7). Detection-mechanization deferred — no clean mechanical signal for "did you run it"; prose-discipline + Pre-Ship nudge.*

## Leaf Lifecycle

**G-L1: Every solution leaf must have Four Risks -> ICE -> assumption identification before entering L4** `REVIEW` `quality`
The leaf lifecycle pipeline must be complete before spawning a delivery diamond.
*Source: Torres (CDH), Cagan (Four Risks), Ellis (ICE) / Gilad (Confidence Meter)*

**G-L2: Every GIST entry must trace back to a scored OST leaf** `REVIEW` `quality`
Every idea must have a `source_leaf_id` referencing an OST leaf whose riskiest assumption has a recorded `validated` test verdict (Torres selection, not ICE scoring; corrected 2026-07-01, v0.54.0).
*Source: Gilad (Evidence Guided), Torres (CDH)*

**G-L3: Before archiving a solution, check if it serves an unexamined segment** `NUDGE` `quality`
A solution that scores poorly for one segment might score well for another.
*Source: Torres (CDH)*
