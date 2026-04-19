# Guardrails Quick Index

Compact reference for lazy loading. Load full rule from `guardrails.md` only when a trigger matches.

| ID | Level | Trigger condition | One-line rule |
|---|---|---|---|
| G-S1 | BLOCK | Writing/logging credentials, tokens, keys | No plaintext secrets ever |
| G-S2 | REVIEW | Solution handles user data or needs system permissions | Run STRIDE threat model first |
| G-S3 | REVIEW | Adding any new data collection point | Privacy by Design assessment required |
| G-S4 | REVIEW | Processing external input (user, API, file, URL) | Validate, sanitize, escape all inputs |
| G-S5 | NUDGE | Collecting any user data | Minimize data; prefer anonymous/aggregated |
| G-S6 | NUDGE | Setting up auth, CORS, sessions, permissions | Secure defaults: opt INTO less security |
| G-S7 | REVIEW | Building user-facing AI interaction | Disclose AI nature (EU AI Act Art 50) |
| G-S8 | NUDGE | Building AI-powered product | Assess EU AI Act risk classification |
| G-D1 | REVIEW | Starting work on a Complex-domain problem | Don't skip discovery; probe-sense-respond |
| G-D2 | NUDGE | Interpreting research findings | Triangulate: 2+ independent evidence types |
| G-D3 | NUDGE | Designing interview/survey questions | Story-based only; no hypotheticals |
| G-D4 | NUDGE | Validating opportunities in OST | 2+ evidence sources per opportunity |
| G-D5 | NUDGE | Before conducting any research | Run bias checklist first |
| G-D6 | NUDGE | Mapping user needs | Include emotional + social, not just functional |
| G-V1 | REVIEW | Marking any delivery complete | Run validation suite for product type |
| G-V2 | REVIEW | Shipping user-facing work | Check Downe's 15 service principles |
| G-V3 | NUDGE | Creating new code/content | Check for existing implementations first (DRY) |
| G-V4 | NUDGE | Adding features or abstractions | Build only what's needed now (YAGNI) |
| G-V5 | NUDGE | Choosing between approaches | Pick the simplest working solution (KISS) |
| G-V6 | NUDGE | Structuring code architecture | Separate layers; depend on abstractions (SoC) |
| G-V7 | REVIEW | Writing implementation code | Tests alongside, not after |
| G-V8 | REVIEW | Building user-facing interfaces | Accessibility built in: semantic HTML, ARIA, keyboard, contrast |
| G-V9 | REVIEW | Designing user flows | Error, empty, and loading states designed |
| G-V10 | REVIEW | Completing user-facing interface | Nielsen's 10 heuristics checked |
| G-L1 | REVIEW | Moving leaf to L4 delivery | Four Risks + ICE + assumptions must be done |
| G-L2 | REVIEW | Creating GIST entry | Must trace to scored OST leaf |
| G-L3 | NUDGE | Archiving a solution | Check if it serves an unexamined segment |
| G-P1 | REVIEW | Any diamond phase transition | Update canvas files |
| G-P2 | NUDGE | Evaluating progress | Check all 5 BVSSH dimensions |
| G-P3 | NUDGE | Logging a decision | Cite the theory that informed it |
| G-P4 | REVIEW | Any significant decision | Log in decision-log.md |
| G-P5 | BLOCK | Starting any implementation task | Read corrections.md first |
| G-P6 | NUDGE | Major transition (L2->L3, L3->L4) | Play devil's advocate first |
