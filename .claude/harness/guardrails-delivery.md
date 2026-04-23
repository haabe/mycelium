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

## Leaf Lifecycle

**G-L1: Every solution leaf must have Four Risks -> ICE -> assumption identification before entering L4** `REVIEW` `quality`
The leaf lifecycle pipeline must be complete before spawning a delivery diamond.
*Source: Torres (CDH), Cagan (Four Risks), Ellis (ICE) / Gilad (Confidence Meter)*

**G-L2: Every GIST entry must trace back to a scored OST leaf** `REVIEW` `quality`
Every idea must have a `source_leaf_id` referencing an OST leaf that has passed ICE threshold.
*Source: Gilad (Evidence Guided), Torres (CDH)*

**G-L3: Before archiving a solution, check if it serves an unexamined segment** `NUDGE` `quality`
A solution that scores poorly for one segment might score well for another.
*Source: Torres (CDH)*
