# Mycelium Guardrails

Hard constraints that override confidence scores, user requests, and agent judgment. These are non-negotiable.

## Enforcement Levels

Each guardrail is marked as:
- **ENFORCED**: Checked by hooks/gate.sh or diamond-progress. Blocks progression if violated.
- **ADVISORY**: Agent should follow, but violation doesn't block. Logged as a warning.

The distinction matters: enforced guardrails prevent mistakes mechanically. Advisory guardrails rely on agent discipline and user awareness.

## Discovery Guardrails

**G-D1: Never skip discovery for Complex-domain problems** `ENFORCED`
Complex problems (Cynefin) require probe-sense-respond. Applying best practices or expert analysis to Complex problems will produce wrong answers with false confidence.
*Source: Snowden (Cynefin), Smart (BVSSH)*

**G-D2: Never treat a single interview as sufficient evidence** `ADVISORY`
Require triangulation: at least 2 independent evidence types (e.g., interviews + behavioral data, or interviews + surveys). Single-source evidence is anecdotal (0.3 on Gilad's confidence meter), regardless of how compelling it feels.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D3: Never ask hypothetical or leading questions in research** `ADVISORY`
Use story-based interviewing: ask about specific past behavior ("Tell me about the last time you..."), never hypothetical preferences ("Would you use X?"). Hypotheticals trigger System 2 rationalization, not System 1 truth.
*Source: Torres (CDH), Kahneman (Thinking Fast and Slow)*

**G-D4: Never validate opportunities using only one evidence type** `ADVISORY`
Each opportunity in the OST must have evidence from at least 2 sources. Frequency data alone is insufficient -- impact and strategic alignment must also be assessed.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D5: Always run bias checklist before conducting research** `ADVISORY`
Review `.claude/harness/cognitive-biases.md` before designing interviews, surveys, or experiments. Design research that mitigates confirmation bias, anchoring, social desirability, and availability heuristic at minimum.
*Source: Shotton (Choice Factory), Kahneman (Thinking Fast and Slow)*

**G-D6: Always map emotional and social dimensions, not just functional** `ADVISORY`
User needs have three dimensions: functional (what they need to do), emotional (how they need to feel), and social (how it affects their relationships/status). Mapping only functional needs misses the actual hiring criteria.
*Source: Christensen (Jobs to be Done)*

## Security & Trust Guardrails

**G-S1: Never store, log, or transmit user secrets in plaintext** `ENFORCED`
Credentials, tokens, API keys, passwords must be encrypted at rest and in transit. Never commit them to version control. Never include them in error messages or logs.
*Source: OWASP Secure by Design*

**G-S2: Never skip threat modeling when a solution handles user data** `ENFORCED`
Before selecting a solution that processes, stores, or transmits user data, run STRIDE threat modeling. Document threats and mitigations in `canvas/threat-model.yml`.
*Source: OWASP STRIDE, Microsoft SDL*

**G-S3: Never add a data collection point without Privacy by Design assessment** `ENFORCED`
Every new piece of data collected must pass: Is it necessary? Is collection minimized? Is consent obtained? Is there a retention policy? Is there a deletion mechanism?
*Source: Cavoukian (Privacy by Design), GDPR Article 25*

**G-S4: Never ship without input validation on all external inputs** `ENFORCED`
All data from external sources (user input, APIs, file uploads, URL parameters, headers, cookies) must be validated, sanitized, and escaped before use.
*Source: OWASP Top 10, OWASP Secure by Design*

**G-S5: Always apply data minimization** `ADVISORY`
Collect only the data that is strictly necessary for the current purpose. If you can achieve the goal with less data, use less data. Default to anonymous/aggregated over individual.
*Source: GDPR Article 5, Cavoukian (Privacy by Design)*

**G-S6: Always design for secure defaults** `ADVISORY`
HTTPS, authentication required, least privilege, sessions expire, CORS restricted, CSP enabled. Users must opt INTO less security, never opt OUT of it.
*Source: OWASP Secure by Design, Cavoukian (Privacy by Design Principle 2)*

**G-S7: Always disclose AI nature in user-facing systems** `ENFORCED`
If the product being built will interact directly with people, it must clearly disclose that users are interacting with an AI system. This is required by EU AI Act Article 50 (effective 2 August 2026) and is good practice regardless of jurisdiction. Do not disguise AI as human.
*Source: EU AI Act Article 50, Downe (Good Services Principle 3: Set expectations)*

**G-S8: Always assess EU AI Act risk classification for AI-powered products** `ADVISORY`
Before delivering an AI-powered product, assess whether it falls into a high-risk category under Annex III (biometrics, critical infrastructure, employment, credit scoring, law enforcement, etc.). If it does, conformity assessment and extensive documentation requirements apply. This is a regulatory awareness check, not legal certification.
*Source: EU AI Act (Regulation 2024/1689), Annex III*

## Delivery Guardrails

**G-V1: Never commit delivery code without running the validation suite** `ENFORCED`
Every code change must pass: tests, type checking, linting, dead code detection, and security scanning before being considered complete.
*Source: Forsgren (Accelerate), n-trax reflexion pattern*

**G-V2: Never ship without checking Downe's 15 principles** `ENFORCED`
For any user-facing work, evaluate against the relevant Good Services principles. Pay special attention to: no dead ends (P10), usable by everyone (P11), explains decisions (P14), easy to get human help (P15).
*Source: Downe (Good Services)*

**G-V3: Never duplicate logic** `ADVISORY`
Before writing new code, check for existing implementations. Extract shared logic into well-named, single-responsibility functions. Every piece of knowledge must have a single, unambiguous representation.
*Source: DRY (Hunt & Thomas, The Pragmatic Programmer)*

**G-V4: Never add speculative features or abstractions** `ADVISORY`
Build only what is needed now. Do not create abstractions, configuration options, or extensibility points for hypothetical future requirements. Three similar lines of code is better than a premature abstraction.
*Source: YAGNI (Extreme Programming), KISS*

**G-V5: Always prefer the simplest working solution** `ADVISORY`
When multiple approaches solve the problem, choose the simplest one. Complexity is a cost, not a feature. If a junior developer couldn't understand it in 5 minutes, it's probably too complex.
*Source: KISS, Clean Code (Martin)*

**G-V6: Always maintain clean separation between layers** `ADVISORY`
Business logic, data access, presentation, and infrastructure must be separated. No layer should have knowledge of another layer's implementation details. Depend on abstractions, not concretions.
*Source: SoC (Dijkstra), SOLID (Martin), Clean Architecture*

**G-V7: Always write tests alongside implementation** `ENFORCED`
Tests are not an afterthought. Write them first (TDD) or alongside the implementation. Never defer testing to "later." Tests document behavior and prevent regression.
*Source: Forsgren (Accelerate), TDD (Beck)*

**G-V8: Always ensure accessibility from the start** `ENFORCED`
Accessibility is a design constraint, not a polish step. Semantic HTML, ARIA labels, keyboard navigation, color contrast, screen reader compatibility must be built in, not retrofitted.
*Source: Downe (Good Services Principle 11), WCAG 2.1 AA*

**G-V9: Always design error states** `ENFORCED`
Every user flow must have designed error, empty, and loading states. Error messages must be helpful (what happened, what the user can do). Never show raw technical errors to users.
*Source: Downe (Good Services Principles 10, 14)*

## Process Guardrails

**G-P1: Never progress a diamond without updating the canvas** `ENFORCED`
Every diamond transition must be reflected in the appropriate canvas files. The canvas is the single source of truth -- if it's not in the canvas, it didn't happen.

**G-P2: Never ignore BVSSH dimensions** `ADVISORY`
When evaluating progress, check ALL five dimensions. Do not sacrifice Safer or Happier for Sooner. Quality (Better) is not traded for speed.
*Source: Smart (BVSSH)*

**G-P3: Always cite which theory informed a decision** `ADVISORY`
Every significant decision in the decision log must reference the specific theory/framework that guided it. This creates accountability and enables review.

**G-P4: Always log decisions in the decision log** `ENFORCED`
No significant decision (diamond transition, solution selection, architecture choice, scope change) happens without a logged entry in `.claude/harness/decision-log.md`.

**G-P5: Always read corrections.md before implementation tasks** `ENFORCED`
Past mistakes are expensive lessons. Reading them costs seconds. Not reading them costs hours.
*Source: Mycelium self-learning, n-trax reflexion pattern*

**G-P6: Always play devil's advocate before major transitions** `ADVISORY`
Before progressing a diamond to a new scale (L2->L3, L3->L4), systematically challenge the current assumptions. What if we're wrong? What evidence contradicts our position?
*Source: Kahneman (Thinking Fast and Slow), Shotton (Choice Factory)*
