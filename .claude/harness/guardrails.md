# Mycelium Guardrails

Hard constraints that override confidence scores, user requests, and agent judgment. These are non-negotiable.

## TL;DR

**BLOCK** (mechanical): G-S1 (no plaintext secrets), G-P5 (read corrections.md before implementation).
**REVIEW** (gates progression): G-D1 (no skipping discovery for complex domains), G-S2 (threat model for user data/permissions), G-S3 (privacy assessment for data collection), G-S4 (input validation), G-S7 (AI disclosure), G-V1 (validation suite), G-V2 (Downe's 15), G-V7 (tests alongside code), G-V8 (a11y), G-V9 (error states), G-V10 (usability heuristics), G-P1 (canvas updated at transitions), G-P4 (decision log).
**NUDGE** (advised): Everything else — evidence quality, bias checks, engineering principles, BVSSH.

**Constraint types**: Each guardrail is tagged by what it protects — `safety`, `quality`, `scope`, `privacy`, `regulatory`, `ethical`. Inspired by AI Interaction Atlas's 37-constraint taxonomy.

## Three-Tier Enforcement

Each guardrail has one of three enforcement levels:

### `BLOCK` — Mechanically prevented
The action cannot happen. gate.sh returns exit 2 (deny). The agent cannot proceed regardless of intent.
*Used for: security violations that must never reach disk (secrets, credentials).*

### `REVIEW` — Diamond progression blocked
The agent can write code, but `/diamond-progress` will refuse to advance Deliver->Complete if this guardrail is unsatisfied. The stop-check hook also escalates these as warnings.
*Used for: quality requirements that must be met before shipping (tests, a11y, services, threat modeling for applicable work).*

### `NUDGE` — Nudged, not blocked
The agent should follow this, and post-write-nudge reminds about it, but violation doesn't prevent progression. Logged for awareness.
*Used for: engineering best practices, bias awareness, stylistic preferences.*

The distinction matters: BLOCK prevents the action via mechanical hook. REVIEW depends on agent judgment during phase transitions (it is not mechanically enforced). NUDGE guides but doesn't prevent.

**Honesty about enforcement** (per [Birgitta Böckeler's harness engineering article](https://martinfowler.com/articles/harness-engineering.html)): only BLOCK is computationally deterministic. REVIEW and NUDGE are *inferentially enforced* — they depend on the agent running the appropriate skill or responding to the nudge. If the agent bypasses a REVIEW check (e.g., by hand-editing diamond state instead of using `/diamond-progress`), the audit hooks (PostToolUse on diamond state) create traceability via `.claude/state/diamond-state-audit.jsonl`. The `stop-check.sh` hook surfaces direct edit counts at session end. This is observability, not enforcement.

**Why this honesty matters**: Mycelium's previous nomenclature (BLOCKED/GATED/ADVISORY) implied that GATED items had mechanical teeth. They don't. The rename to BLOCK/REVIEW/NUDGE reflects the actual computational capability honestly. If you want stronger enforcement on a REVIEW item, the path is to write a new BLOCK guardrail backed by a hook — not to add another REVIEW.

## Discovery Guardrails

**G-D1: Never skip discovery for Complex-domain problems** `REVIEW` `scope`
Complex problems (Cynefin) require probe-sense-respond. Applying best practices or expert analysis to Complex problems will produce wrong answers with false confidence.
*Source: Snowden (Cynefin), Smart (BVSSH)*

**G-D2: Never treat a single interview as sufficient evidence** `NUDGE` `quality`
Require triangulation: at least 2 independent evidence types (e.g., interviews + behavioral data, or interviews + surveys). Single-source evidence is anecdotal (0.3 on Gilad's confidence meter), regardless of how compelling it feels.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D3: Never ask hypothetical or leading questions in research** `NUDGE` `quality`
Use story-based interviewing: ask about specific past behavior ("Tell me about the last time you..."), never hypothetical preferences ("Would you use X?"). Hypotheticals trigger System 2 rationalization, not System 1 truth.
*Source: Torres (CDH), Kahneman (Thinking Fast and Slow)*

**G-D4: Never validate opportunities using only one evidence type** `NUDGE` `quality`
Each opportunity in the OST must have evidence from at least 2 sources. Frequency data alone is insufficient -- impact and strategic alignment must also be assessed.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D5: Always run bias checklist before conducting research** `NUDGE` `quality`
Review `.claude/harness/cognitive-biases.md` before designing interviews, surveys, or experiments. Design research that mitigates confirmation bias, anchoring, social desirability, and availability heuristic at minimum.
*Source: Shotton (Choice Factory), Kahneman (Thinking Fast and Slow)*

**G-D6: Always map emotional and social dimensions, not just functional** `NUDGE` `quality`
User needs have three dimensions: functional (what they need to do), emotional (how they need to feel), and social (how it affects their relationships/status). Mapping only functional needs misses the actual hiring criteria.
*Source: Christensen (Jobs to be Done)*

## Security & Trust Guardrails

**G-S1: Never store, log, or transmit user secrets in plaintext** `BLOCK` `safety`
Credentials, tokens, API keys, passwords must be encrypted at rest and in transit. Never commit them to version control. Never include them in error messages or logs.
*Source: OWASP Secure by Design*

**G-S2: Never skip threat modeling when a solution handles user data or requires system permissions** `REVIEW` `safety`
Before selecting a solution that processes, stores, or transmits user data, OR that requires system permissions (Accessibility, Camera, Contacts, Location, Files, Network, Bluetooth), run STRIDE threat modeling. Permission-requiring APIs are security surfaces even when no user data is involved. Document threats and mitigations in `canvas/threat-model.yml`.
*Source: OWASP STRIDE, Microsoft SDL*

**G-S3: Never add a data collection point without Privacy by Design assessment** `REVIEW` `privacy`
Every new piece of data collected must pass: Is it necessary? Is collection minimized? Is consent obtained? Is there a retention policy? Is there a deletion mechanism?
*Source: Cavoukian (Privacy by Design), GDPR Article 25*

**G-S4: Never ship without input validation on all external inputs** `REVIEW` `safety`
All data from external sources (user input, APIs, file uploads, URL parameters, headers, cookies) must be validated, sanitized, and escaped before use.
*Source: OWASP Top 10, OWASP Secure by Design*

**G-S5: Always apply data minimization** `NUDGE` `privacy`
Collect only the data that is strictly necessary for the current purpose. If you can achieve the goal with less data, use less data. Default to anonymous/aggregated over individual.
*Source: GDPR Article 5, Cavoukian (Privacy by Design)*

**G-S6: Always design for secure defaults** `NUDGE` `safety`
HTTPS, authentication required, least privilege, sessions expire, CORS restricted, CSP enabled. Users must opt INTO less security, never opt OUT of it.
*Source: OWASP Secure by Design, Cavoukian (Privacy by Design Principle 2)*

**G-S7: Always disclose AI nature in user-facing systems** `REVIEW` `regulatory` `ethical`
If the product being built will interact directly with people, it must clearly disclose that users are interacting with an AI system. This is required by EU AI Act Article 50 (effective 2 August 2026) and is good practice regardless of jurisdiction. Do not disguise AI as human. Run `/regulatory-review` to assess transparency requirements.
*Source: EU AI Act Article 50, Downe (Good Services Principle 3: Set expectations)*

**G-S8: Always assess EU AI Act risk classification for AI-powered products** `NUDGE` `regulatory`
Before delivering an AI-powered product, assess whether it falls into a high-risk category under Annex III (biometrics, critical infrastructure, employment, credit scoring, law enforcement, etc.). If it does, conformity assessment and extensive documentation requirements apply. This is a regulatory awareness check, not legal certification. Run `/regulatory-review` for structured assessment.
*Source: EU AI Act (Regulation 2024/1689), Annex III*

## Delivery Guardrails

**G-V1: Never mark delivery complete without running the validation suite** `REVIEW` `quality`
Every deliverable must pass its product-type-appropriate validation before being considered complete. Software: tests, type checking, linting, security scanning. Content: quality review, fact-check, accessibility (captions/alt text). AI tool: eval test cases, safety checks, bias assessment. Service: service blueprint walkthrough, documentation review.
*Source: Forsgren (Accelerate), n-trax reflexion pattern*

**G-V2: Never ship user-facing work without checking Downe's 15 principles** `REVIEW` `quality`
For any user-facing work, evaluate against the relevant Good Services principles. Pay special attention to: no dead ends (P10), usable by everyone (P11), explains decisions (P14), easy to get human help (P15).
*Source: Downe (Good Services)*

**G-V3: Never duplicate logic or content** `NUDGE` `quality`
Before creating new deliverables, check for existing implementations or content. Extract shared logic into reusable components (code: functions/modules; content: templates/modules; services: documented workflows). Every piece of knowledge must have a single, unambiguous representation.
*Source: DRY (Hunt & Thomas, The Pragmatic Programmer)*

**G-V4: Never add speculative features or abstractions** `NUDGE` `scope`
Build only what is needed now. Do not create abstractions, configuration options, or extensibility points for hypothetical future requirements. Three similar lines of code is better than a premature abstraction.
*Source: YAGNI (Extreme Programming), KISS*

**G-V5: Always prefer the simplest working solution** `NUDGE` `quality`
When multiple approaches solve the problem, choose the simplest one. Complexity is a cost, not a feature. If a junior developer couldn't understand it in 5 minutes, it's probably too complex.
*Source: KISS, Clean Code (Martin)*

**G-V6: Always maintain clean separation between layers** `NUDGE` `quality`
Business logic, data access, presentation, and infrastructure must be separated. No layer should have knowledge of another layer's implementation details. Depend on abstractions, not concretions.
*Source: SoC (Dijkstra), SOLID (Martin), Clean Architecture*

**G-V7: Always validate alongside implementation** `REVIEW` `quality`
Validation is not an afterthought. Software: write tests first (TDD) or alongside code. Content: review against objectives during production, not after. AI tools: define eval cases before writing prompts. Never defer validation to "later." Validation documents expected behavior and prevents regression.
*Source: Forsgren (Accelerate), TDD (Beck)*

**G-V8: Always ensure accessibility for user-facing work** `REVIEW` `quality`
Accessibility is a design constraint, not a polish step. Semantic HTML, ARIA labels, keyboard navigation, color contrast, screen reader compatibility must be built in, not retrofitted.
*Source: Downe (Good Services Principle 11), WCAG 2.1 AA*

**G-V9: Always design error states** `REVIEW` `quality`
Every user flow must have designed error, empty, and loading states. Error messages must be helpful (what happened, what the user can do). Never show raw technical errors to users.
*Source: Downe (Good Services Principles 10, 14)*

**G-V10: Always check usability heuristics for user-facing interfaces** `REVIEW` `quality`
Before marking user-facing delivery complete, evaluate against Nielsen's 10 usability heuristics. Interface-level quality (Nielsen) complements service-level quality (Downe G-V2). Run `/usability-check`.
*Source: Nielsen (10 Usability Heuristics, 1994)*

## Process Guardrails

**G-P1: Never progress a diamond without updating the canvas** `REVIEW` `quality`
Every diamond transition must be reflected in the appropriate canvas files. The canvas is the single source of truth -- if it's not in the canvas, it didn't happen.

**G-P2: Never ignore BVSSH dimensions** `NUDGE` `quality`
When evaluating progress, check ALL five dimensions. Do not sacrifice Safer or Happier for Sooner. Quality (Better) is not traded for speed.
*Source: Smart (BVSSH)*

**G-P3: Always cite which theory informed a decision** `NUDGE` `quality`
Every significant decision in the decision log must reference the specific theory/framework that guided it. This creates accountability and enables review.

**G-P4: Always log decisions in the decision log** `REVIEW` `quality`
No significant decision (diamond transition, solution selection, architecture choice, scope change) happens without a logged entry in `.claude/harness/decision-log.md`.

**G-P5: Always read corrections.md before implementation tasks** `BLOCK` `quality`
Past mistakes are expensive lessons. Reading them costs seconds. Not reading them costs hours.
*Source: Mycelium self-learning, n-trax reflexion pattern*

**G-P6: Always play devil's advocate before major transitions** `NUDGE` `quality`
Before progressing a diamond to a new scale (L2->L3, L3->L4), systematically challenge the current assumptions. What if we're wrong? What evidence contradicts our position?
*Source: Kahneman (Thinking Fast and Slow), Shotton (Choice Factory)*
