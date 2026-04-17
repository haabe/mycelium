# Theory Gates

Decision gates that must pass before a diamond transitions between phases. Gates vary by scale level. Each gate has specific pass/fail criteria.

## Gate Structure

```
Gate Name
  Source: [theory/author]
  Applies to: [which transitions and scales]
  Pass criteria: [specific, measurable]
  Fail criteria: [what constitutes failure]
  Evidence required: [what artifacts demonstrate pass]
  Suggested skill: [skill to run to satisfy this gate]
```

**IMPORTANT**: When checking gates during `/diamond-progress`, always surface the suggested skill for each gate. Say: "This transition requires a security check. Run `/security-review` to satisfy the Security Gate."

---

## Trio Perspective Requirement (Torres Product Trio)

Every gate check should consider three perspectives: **Product** (PM), **Design** (UX), and **Engineering** (Dev). Not every perspective applies at every gate — but omission must be explicit ("N/A: [reason]"), not silent.

The trio coverage varies by diamond scale. Where a perspective is currently weak or missing, specific guidance is provided below.

### Trio Coverage by Scale

| Scale | Product | Design | Engineering | Notes |
|-------|---------|--------|-------------|-------|
| L0 Purpose | Strong | **Add**: Experience vision, emotional job framing | **Add**: Technical capability requirements, constraint mapping | Design asks "How will users experience this purpose?" Engineering asks "What does this purpose require technically?" |
| L1 Strategy | Strong | Weak (implicit in interviews) | **Add**: Technology landscape, Wardley evolution stages | Engineering should assess what tech enables/constrains the strategy |
| L2 Opportunity | Strong | **Add**: Design research (observation, contextual inquiry) | **Add**: Technical discovery (what's possible, what's expensive) | Both perspectives should inform opportunity framing, not just product |
| L3 Solution | Strong | Strong | Weak (spikes are post-hoc) | Engineering spikes should happen DURING ideation, not after. Feasibility informs solution design. |
| L4 Delivery | Strong | Strong | Strong | Most complete coverage across all three perspectives |
| L5 Market | Strong | **Add**: Brand/positioning validation, visual identity review | Moderate | Design should validate user-facing messaging and visual coherence |

### How to Apply

When checking gates during `/diamond-progress`, for each applicable gate:
1. State the **product perspective** assessment (or N/A with reason)
2. State the **design perspective** assessment (or N/A with reason)
3. State the **engineering perspective** assessment (or N/A with reason)

For solo developers: apply perspectives sequentially as distinct evaluation passes, not collapsed into one. See `.claude/engine/perspective-resolution.md` for when perspectives conflict.

---

## Gate Definitions

### 1. Evidence Gate

**Source**: Torres (Continuous Discovery Habits), Gilad (Evidence-Guided)

**Applies to**: All transitions, all scales

| Scale | Pass Criteria | Fail Criteria |
|-------|--------------|---------------|
| L0 | Market research, competitive analysis, stakeholder interviews documented | Assumptions stated without supporting data |
| L1 | Strategic evidence from multiple sources; quantified opportunity size | Strategy based on opinion or single data point |
| L2 | 5+ user interviews with triangulated findings; behavioral data | Fewer than 3 evidence sources; no triangulation |
| L3 | Prototype tested with users; measurable feedback collected. Design hypotheses validated using Lean UX format (Gothelf). If multi-domain: bounded contexts identified (DDD/Evans). | Solution chosen without user validation |
| L4 | Acceptance criteria defined with measurable outcomes | Vague or missing acceptance criteria |
| L5 (software) | Test cases written before or alongside implementation | No tests; untested code |
| L5 (content) | Content reviewed against objectives; accessibility verified | Unreviewed content; missing captions/alt text |
| L5 (ai_tool) | Eval cases passing; safety checks clean | No evaluation; untested prompts/models |
| L5 (service) | Delivery step documented and repeatable | Undocumented delivery process |

**Evidence required**: Interview transcripts, analytics screenshots, research synthesis documents, test results.

**External metric snapshots count as `external_data`** (v0.14): snapshots produced by `/metrics-pull` (`.claude/evals/metrics/<source>/*.json`) satisfy the `external_data` source_class at L0/L1/L2/L5. They do NOT substitute for `external_human` conversations where the L2 source-ratio gate requires them, but they satisfy the Evidence gate's "behavioral data" criterion and freshen traction evidence at L0/L5. Adapter `provenance.snapshot` path must be included in the canvas evidence entry.

**Suggested skill**: `/user-interview` (for gathering evidence), `/assumption-test` (for validating evidence), `/canvas-health` (for verifying evidence quality and staleness in canvas files), `/metrics-pull` (for L0/L1/L2/L5 external traction / product / market metrics)

#### Source Ratio Sub-Check (v0.11.0)

Evidence sources in canvas provenance objects carry an optional `source_classes` field (see `_common.schema.json`). This sub-check prevents the Goodhart trap where confidence climbs on desk research alone while zero external human voices are heard.

**Classification**: `external_human` (real user interview, stakeholder conversation, survey response, usability test), `external_data` (third-party analytics, behavioral data, market data), `internal_desk` (desk research, competitive analysis, brainstorming), `internal_simulated` (mocked persona interview, thought experiment). Unclassified sources default to `internal_desk`.

**Enforcement levels**:

| Transition | Scales | Level | Behavior |
|-----------|--------|-------|----------|
| Discover->Define | L0-L2 | -- | No check (discovery is exploratory) |
| Define->Develop | L0-L2 | NUDGE | If zero `external_human` or `external_data` sources across all canvas provenance for this diamond: warn. "All evidence is desk-derived. Consider `/handoff` to plan an external conversation or `/user-interview` to conduct one." |
| Develop->Deliver | L0, L2 | REVIEW | Blocks progression. Purpose (L0) is foundational -- shipping it without any external voice means the entire product is built on unvalidated assumptions. Opportunity (L2) without external validation is the core Goodhart trap. |
| Develop->Deliver | L1 | NUDGE | Warn but don't block. Strategy can sometimes proceed on desk research (competitive analysis, Wardley mapping) if the project type warrants it. |
| All other transitions | L3-L5 | -- | No source ratio check (delivery-level evidence is validation results, not user research) |

**Dogfood modifier**: When `dogfood: true` in `diamonds/active.yml`, the L0/L2 REVIEW gate accepts `internal_simulated` (mocked persona) as ONE of the required external sources -- but still requires at least one source classified as `external_human` or `external_data` before clearing the REVIEW. This means dogfood projects can use mocked personas to supplement real evidence, but cannot replace it entirely. The dogfood report's #1 finding was that the system under-pushes for external evidence; weakening this gate would make that problem worse.

**Anti-gaming rule**: `internal_simulated` (mocked persona interviews) does NOT count as external evidence, even though it simulates external perspectives. The system pushes toward real human contact.

**Suggested skill**: `/handoff` (to plan an external evidence-gathering task), `/log-evidence` (to record findings from completed conversations)

### 2. Four Risks Gate

**Source**: Cagan (Inspired, Empowered), Torres (Product Trio perspective requirement)

**Applies to**: Define->Develop and Develop->Deliver transitions, L1-L4

All four risks must be assessed, and the assessment must demonstrate that **three distinct perspectives** were applied (Torres's Product Trio). Each risk maps to a primary perspective — a single-lens assessment does not pass.

| Risk | Perspective | Pass Criteria | Fail Criteria |
|------|------------|--------------|---------------|
| **Value** (Cagan: "Desirability") | Product (PM) | Evidence that users want/need this (not just stakeholder opinion). Grounded in user research, JTBD, or opportunity scoring. | No user validation; only internal demand; assessed purely from technical feasibility |
| **Usability** | Design (UX) | Users can figure out how to use it (tested, not assumed). Assessed through user flows, prototypes, or heuristic evaluation. | No usability testing; assumed "intuitive"; assessed only as "we'll make it simple" |
| **Feasibility** | Engineering (Dev) | Engineering confirms buildable within constraints. Specific technical risks identified, dependencies mapped, spike results documented. | No technical assessment; unknown dependencies; hand-waved as "straightforward" |
| **Business Viability** | Cross-cutting | Aligns with business model, legal, ethical constraints | Conflicts with business constraints; legal risk unassessed |

**Perspective rule**: Each of the three perspectives (product, design, engineering) must produce at least one distinct piece of evidence or assessment. A single combined statement like "this is valuable, usable, and feasible" fails — it indicates one perspective was applied and the others were assumed. For solo developers, the three perspectives must still be applied sequentially as distinct evaluation passes, not collapsed into one.

**Evidence source**: The primary evidence for this gate comes from **OST solution leaves** in `canvas/opportunities.yml`. Each solution leaf should have a `four_risks` block with separate assessments per dimension. The `/ice-score` skill derives ICE scores from these risk assessments — ICE without Four Risks is ungrounded estimation.

**Evidence required**: User research findings (product lens), usability test results or heuristic evaluation (design lens), technical spike outcomes or dependency analysis (engineering lens), business model canvas or viability assessment (cross-cutting).

**Suggested skill**: `/ost-builder` (produces Four Risks per leaf), `/ice-score` (derives scores from risks), `/assumption-test` (tests riskiest unknowns), `/usability-check` (design lens), `/devils-advocate` (challenge single-lens thinking)

### 3. JTBD Gate

**Source**: Christensen (Competing Against Luck)

**Applies to**: Discover->Define and Define->Develop, L1-L3

| Scale | Pass Criteria | Fail Criteria |
|-------|--------------|---------------|
| L1 | Strategic jobs identified with all 3 dimensions | Jobs described only functionally |
| L2 | Opportunity-level jobs mapped from research data | Jobs assumed without research |
| L3 | Solution explicitly addresses functional, emotional, and social dimensions | Solution addresses only functional job |

**Evidence required**: JTBD statements with all three dimensions (functional, emotional, social), linked to interview data.

**Suggested skill**: `/jtbd-map`

### 4. Cynefin Gate

**Source**: Snowden (Cynefin framework)

**Applies to**: Define->Develop, all scales

| Pass Criteria | Fail Criteria |
|--------------|---------------|
| Problem classified into a Cynefin domain | No classification attempted |
| Method chosen matches the domain (see cynefin-routing.md) | Complex problem treated as Clear (best practice applied to emergent situation) |
| If Complex, experiments designed with clear learning goals | Attempting to plan/predict outcomes in complex domain |

**Evidence required**: Cynefin classification document with rationale, method selection justification.

**Suggested skill**: `/cynefin-classify`

### 5. Bias Gate

**Source**: Shotton (The Choice Factory), Kahneman (Thinking, Fast and Slow)

**Applies to**: All transitions, all scales

| Pass Criteria | Fail Criteria |
|--------------|---------------|
| cognitive-biases.md checklist reviewed for current stage | No bias review conducted |
| Potential biases identified and mitigation documented | Known biases present but unacknowledged |
| Disconfirming evidence actively sought | Only confirming evidence collected |
| Agent's own biases examined (see cognitive-biases.md agent section) | Agent assumes objectivity |

**Evidence required**: Completed bias checklist, documented mitigation actions.

**Suggested skill**: `/bias-check`

### 6. Security Gate

**Source**: OWASP Top 10:2025, STRIDE (Shostack)

**Applies to**: Develop->Deliver and Deliver->Complete, L3-L5

**Product type conditioning** (v0.11.0):
- **software, ai_tool**: Full OWASP + STRIDE as below
- **content_course, content_publication, content_media**: Security applies only to the distribution platform (LMS, paywall, hosting), not the content itself. If content is self-hosted or behind access control, STRIDE applies to the access control mechanism.
- **service_offering**: STRIDE applies to any digital infrastructure used to deliver the service (client portal, scheduling system, data storage). If purely offline service, this gate is N/A.

| Scale | Pass Criteria | Fail Criteria |
|-------|--------------|---------------|
| L3 | STRIDE threat model completed; security architecture reviewed | No threat analysis |
| L4 | OWASP Top 10:2025 addressed; input validation; auth/authz verified | Known vulnerability unaddressed |
| L5 | Code-level security checks passing; no hardcoded secrets; dependencies scanned | Security scan findings ignored |

**Evidence required**: STRIDE analysis, security review checklist, dependency scan results, SAST/DAST results.

**Suggested skill**: `/threat-model` (for STRIDE analysis), `/security-review` (for code-level review)

### 7. Privacy Gate

**Source**: GDPR, Privacy by Design (Cavoukian)

**Applies to**: Define->Develop and Develop->Deliver, L2-L4

| Scale | Pass Criteria | Fail Criteria |
|-------|--------------|---------------|
| L2 | Data subjects identified; purpose limitation defined | Collecting data without defined purpose |
| L3 | DPIA completed for high-risk processing; data minimization applied | Processing PII without impact assessment |
| L4 | Consent mechanisms implemented; data retention defined; right to deletion supported | No consent flow; unlimited retention |

**Evidence required**: Data flow diagram, DPIA document, consent mechanism design, retention policy.

**Suggested skill**: `/privacy-check`

### 8. BVSSH Gate

**Source**: Smart (Sooner Safer Happier)

**Applies to**: Deliver->Complete, all scales. **REVIEW** -- diamond-progress requires a BVSSH quick-check (even brief) before allowing delivery completion. This ensures holistic health is assessed for every delivery, not just on a monthly cadence.

All five dimensions must be assessed (even a one-sentence answer per dimension is sufficient for a quick-check):

| Dimension | Pass Criteria | Fail Criteria |
|-----------|--------------|---------------|
| **Better** | Quality metrics stable or improved | Quality degraded; tech debt increased without plan |
| **Value** | Measurable user/business value delivered or validated | No measurable outcome; vanity metrics only |
| **Sooner** | Lead time maintained or reduced; no unnecessary delays | Lead time increased; batch size too large |
| **Safer** | Risk reduced; compliance maintained; no new vulnerabilities | New risks introduced without mitigation |
| **Happier** | Four stakeholders assessed — customers, colleagues, citizens, climate (Smart). Sustainable pace; no burnout; compute usage proportionate to value; no negative societal impact | Unsustainable pace; team morale concerns; wasteful compute (brute-force retries); negative community impact |

**Evidence required**: Metrics dashboard, team health check, DORA metrics comparison.

**Suggested skill**: `/bvssh-check`

### 9. Service & Usability Quality Gate

**Source**: Downe (Good Services), Nielsen (10 Usability Heuristics)

**Applies to**: Develop->Deliver and Deliver->Complete, L2-L4

**Product type note** (v0.11.0): Downe's 15 principles apply to ALL product types, not just software. For content products, "service" means the learning/reading/viewing experience. For service offerings, it means the client delivery experience. Nielsen's heuristics apply only to digital interfaces.

**Core Model nudge** (v0.11.1): For `content_course`, `content_publication`, `content_media`, and `service_offering` product types, this gate includes a NUDGE at the **Develop->Deliver** transition: "Content-heavy product detected. Consider mapping core pages (inward paths, core content, forward paths) in `services.yml#core_pages` per Halland's Core Model. This helps ensure no dead ends (Downe P10) and that users find what they need through natural pathways." This is advisory, not blocking — skip it if the product has no web presence or page-based content architecture.

Two quality layers for user-facing work:

**Service Quality (Downe -- end-to-end service design)**:

| Pass Criteria | Fail Criteria |
|--------------|---------------|
| Service evaluated against all 15 Downe principles | No service design review |
| No dead ends in user journeys | Users can get stuck with no next action |
| Accessible to all users equally | Accessibility not tested |
| Minimum possible steps to complete the outcome | Unnecessary steps in the flow |

**Interface Usability (Nielsen -- screen-level interaction design)**:

| Pass Criteria | Fail Criteria |
|--------------|---------------|
| Interface evaluated against Nielsen's 10 heuristics | No usability review for user-facing work |
| System status visible to users | Users don't know what's happening |
| Error messages constructive and plain-language | Raw error codes shown to users |
| Consistency maintained (internal + platform conventions) | Inconsistent patterns across screens |

**Evidence required**: Completed service-check output, usability-check output, user journey map, accessibility audit.

**Suggested skill**: `/service-check` (Downe's 15 principles), `/usability-check` (Nielsen's 10 heuristics), `/a11y-check` (WCAG 2.1 AA accessibility)

### 10. DORA / Delivery Metrics Gate

**Source**: Forsgren (Accelerate)

**Applies to**: Deliver->Complete, L3-L5

**Product type routing** (v0.11.0): This gate measures delivery health using the metrics canvas appropriate for the product type. The principle is the same (are you delivering at a sustainable cadence with acceptable quality?) but the specific metrics differ.

| Product Type | Metrics Canvas | Key Metrics |
|-------------|---------------|-------------|
| software | dora-metrics.yml | Deployment frequency, lead time, change failure rate, failed deployment recovery time (FDRT, formerly MTTR), reliability |
| content_* | content-metrics.yml | Publication cadence, production lead time, revision rate, completion rate |
| ai_tool | ai-tool-metrics.yml | Eval frequency, prompt version cadence, safety score, bias assessment |
| service_offering | service-metrics.yml | Client throughput, delivery lead time, client satisfaction, repeatability |

**Pass criteria** (universal across product types):
- Delivery cadence maintained or improved
- Lead time within target
- Quality/failure rate within target
- Recovery/revision capability demonstrated

**Fail criteria**: Cadence declining, lead time increasing, quality degrading without a plan.

**Evidence required**: Product-type-appropriate metrics canvas populated with current measurements.

**Suggested skill**: `/dora-check` (auto-routes to product-type-appropriate assessment)

### 11. Corrections Gate

**Source**: Mycelium (internal learning loop)

**Applies to**: All transitions, all scales

| Pass Criteria | Fail Criteria |
|--------------|---------------|
| corrections.md reviewed before work began | Corrections not consulted |
| No previously-documented mistakes repeated | Known mistake pattern detected |
| Any new mistakes documented with prevention strategy | Mistakes occurred but not logged |
| Corrections filtered for relevance to current diamond scale and opportunity area | Generic "I read corrections.md" without identifying relevant entries |

**Relevance filtering**: When reviewing corrections.md, filter for entries relevant to:
1. The current **diamond scale** (L0-L5) — an L4 delivery correction is less relevant during L2 discovery
2. The current **opportunity area** — corrections about API design are less relevant when working on user research
3. The current **solution domain** — corrections about feasibility estimation are highly relevant during ICE scoring

The goal is not to read every correction every time, but to surface the corrections most likely to prevent repeating a mistake in the current context.

**Evidence required**: Timestamp of corrections.md review, specific entries identified as relevant, new entries if applicable.

**Suggested skill**: `/preflight` (includes corrections review), `/reflexion` (includes corrections-driven implementation), `/corrections-audit` (for trend analysis and guardrail graduation)

### 12. Regulatory Gate

**Source**: EU AI Act (Regulation 2024/1689), other applicable AI regulation

**Applies to**: Define->Develop and Develop->Deliver, L3-L5

This gate checks whether the product being built falls under AI regulation. Mycelium itself is not regulated (it's configuration files, not an AI system), but products built WITH Mycelium may be.

| Scale | Pass Criteria | Fail Criteria |
|-------|--------------|---------------|
| L3 | EU AI Act risk classification assessed: is this product in a high-risk category (Annex III)? If yes, conformity assessment requirements identified. | No regulatory assessment done for a product that may interact with users or make automated decisions |
| L4 | If high-risk: technical documentation requirements planned. If user-facing AI: Article 50 transparency disclosure designed (users must know they're interacting with AI). | High-risk system entering delivery without regulatory awareness |
| L5 | If user-facing: AI disclosure present. If high-risk: conformity assessment path identified. | Product launched without required transparency or compliance planning |

**Key Annex III high-risk categories** (if your product falls into any of these, full compliance is required):
- Biometric identification/categorization
- Critical infrastructure management
- Education and vocational training (access, assessment)
- Employment (recruitment, screening, evaluation)
- Essential services (credit scoring, insurance, social benefits)
- Law enforcement
- Migration and border control
- Justice and democratic processes

**Article 50 transparency** (applies from 2 August 2026):
- AI systems that interact directly with people must disclose they are AI
- Systems generating synthetic content must machine-mark outputs
- Deployers of deepfakes must disclose artificial generation

**What this gate does NOT require**: Mycelium is not a legal compliance tool. This gate raises awareness and prompts the user to assess regulatory applicability. It does not certify compliance. For actual compliance decisions, consult qualified EU AI law counsel.

**Evidence required**: Regulatory classification assessment document, or explicit statement that the product is minimal-risk / not in scope.

**Suggested skill**: `/regulatory-review` (for structured EU AI Act assessment), plus review `canvas/threat-model.yml` for data handling scope and `canvas/privacy-assessment.yml` for data protection.

---

## Transition Matrix

Summary of which gates apply to which transitions:

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | Required | Required | Required | Required |
| Four Risks | -- | Required (L1-4) | Required (L1-4) | -- |
| JTBD | Required (L1-3) | Required (L1-3) | -- | -- |
| Cynefin | -- | Required | -- | -- |
| Bias | Required | Required | Required | Required |
| Security | -- | -- | Required (L3-5) | Required (L3-5) |
| Privacy | -- | Required (L2-4) | Required (L2-4) | -- |
| BVSSH | -- | -- | -- | Required |
| Service Quality | -- | -- | Required (L2-4) | Required (L2-4) |
| Delivery Metrics | -- | -- | -- | Required (L3-5) |
| Corrections | Required | Required | Required | Required |
| Regulatory | -- | Required (L3-5) | Required (L3-5) | -- |

**Product type conditioning** (v0.11.0): Gates marked with product_type conditions (Security, DORA/Delivery Metrics, Service Quality) use the delivery profile from `canvas-guidance.yml#product_types`. The `product_type` is set during `/interview` Phase 6 and stored in `diamonds/active.yml`. When checking these gates, always verify which product_type applies before evaluating pass criteria.

**Fallback when product_type is not set**: If `product_type` is null or missing in `diamonds/active.yml`, treat product-type-conditioned gates as if the product is `software` (the strictest default). Log a NUDGE: "Product type not set — defaulting to software. Run `/interview` Phase 6 to set the correct product type."

---

## Scale × Transition Applicability Matrix (v0.11.1)

Use this matrix to determine exactly which gates to evaluate for a given scale and transition. "R" = Required, "--" = Not applicable. When initializing `theory_gates_status` in `active.yml`, include all gates marked "R" for the diamond's scale at any transition.

### L0 Purpose

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | -- | -- | -- |
| JTBD | -- | -- | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | -- | -- |
| Privacy | -- | -- | -- | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | -- | -- |
| Delivery Metrics | -- | -- | -- | -- |
| Corrections | R | R | R | R |
| Regulatory | -- | -- | -- | -- |

**Applicable gates**: Evidence, Cynefin, Bias, BVSSH, Corrections (5 gates)

**Trio guidance for L0**:
- **Product**: Why does this purpose matter to users? What jobs does it serve? (Strong — already core to L0)
- **Design**: How will users experience this purpose? What emotional and social dimensions does the purpose address? Frame the purpose as a user experience vision, not just a business statement.
- **Engineering**: What technical capabilities does this purpose require? What constraints does it impose on future architecture? Early technical framing prevents L3/L4 surprises.

### L1 Strategy

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | R | R | -- |
| JTBD | R | R | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | -- | -- |
| Privacy | -- | -- | -- | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | -- | -- |
| Delivery Metrics | -- | -- | -- | -- |
| Corrections | R | R | R | R |
| Regulatory | -- | -- | -- | -- |

**Applicable gates**: Evidence, Four Risks, JTBD, Cynefin, Bias, BVSSH, Corrections (7 gates)

**Trio guidance for L1**:
- **Product**: Where should we play? What's the strategic opportunity? (Strong — already core to L1)
- **Design**: What does the user research reveal about unmet experience gaps? Are interview insights being examined for design implications, not just product implications?
- **Engineering**: What does the technology landscape enable or constrain? Wardley evolution stages of key components. Technical feasibility should inform strategic bets, not just follow them. Add to `/wardley-map` skill.

### L2 Opportunity

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | R | R | -- |
| JTBD | R | R | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | -- | -- |
| Privacy | -- | R | R | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | R | R |
| Delivery Metrics | -- | -- | -- | -- |
| Corrections | R | R | R | R |
| Regulatory | -- | -- | -- | -- |

**Applicable gates**: Evidence, Four Risks, JTBD, Cynefin, Bias, Privacy, BVSSH, Service Quality, Corrections (9 gates)

**Trio guidance for L2**:
- **Product**: What problems are worth solving? What does the research say about user needs? (Strong — already core to L2)
- **Design**: Dedicated design research — not just interview analysis but observation, contextual inquiry, journey mapping. Design perspective surfaces usability and emotional dimensions that product-only analysis misses. Add to `/ost-builder` workflow.
- **Engineering**: Technical discovery — what's technically possible, what's expensive, what emerging capabilities change the opportunity space? Engineering perspective prevents framing opportunities that are technically infeasible.

### L3 Solution

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | R | R | -- |
| JTBD | R | R | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | R | R |
| Privacy | -- | R | R | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | R | R |
| Delivery Metrics | -- | -- | -- | R |
| Corrections | R | R | R | R |
| Regulatory | -- | R | R | -- |

**Applicable gates**: All 12 gates

**Trio guidance for L3**:
- **Product**: Does the solution address the validated opportunity? Is there evidence users want this? (Strong)
- **Design**: Is the solution usable? Has it been evaluated with prototypes or heuristic review? (Strong)
- **Engineering**: Engineering spikes should happen DURING ideation, not after. If feasibility risk is medium or high, spike results must exist before ICE scoring. Feasibility informs solution design — it's not a post-hoc constraint. Add to `/ice-score`: feasibility assessment must include spike results if feasibility risk > medium.

### L4 Delivery

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | R | R | -- |
| JTBD | -- | -- | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | R | R |
| Privacy | -- | R | R | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | R | R |
| Delivery Metrics | -- | -- | -- | R |
| Corrections | R | R | R | R |
| Regulatory | -- | R | R | -- |

**Applicable gates**: Evidence, Four Risks, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory (11 gates — all except JTBD)

**Trio guidance for L4**:
- **Product**: Are acceptance criteria aligned with user value? Does the deliverable match what was validated in L3? (Strong)
- **Design**: Is the implementation meeting usability standards? Are error states, loading states, and edge cases designed? Run `/usability-check` and `/a11y-check`. (Strong)
- **Engineering**: Is the code clean, tested, secure, and performant? DORA metrics healthy? Dependencies scanned? (Strong — this is engineering's home scale)

### L5 Market

| Gate | Disc->Def | Def->Dev | Dev->Del | Del->Comp |
|------|-----------|----------|----------|-----------|
| Evidence | R | R | R | R |
| Four Risks | -- | -- | -- | -- |
| JTBD | -- | -- | -- | -- |
| Cynefin | -- | R | -- | -- |
| Bias | R | R | R | R |
| Security | -- | -- | R | R |
| Privacy | -- | -- | -- | -- |
| BVSSH | -- | -- | -- | R |
| Service Quality | -- | -- | -- | -- |
| Delivery Metrics | -- | -- | -- | R |
| Corrections | R | R | R | R |
| Regulatory | -- | R | R | -- |

**Applicable gates**: Evidence, Cynefin, Bias, Security, BVSSH, Delivery Metrics, Corrections, Regulatory (8 gates)

**Trio guidance for L5**:
- **Product**: Is the positioning aligned with validated user needs? Does the GTM motion match the buyer journey? (Strong)
- **Design**: Brand and positioning validation — does the visual identity, messaging, and user-facing presentation cohere? Is the landing/onboarding experience designed, not just written? Design should validate that the market-facing artifacts meet the same quality bar as the product itself.
- **Engineering**: Is telemetry in place to measure launch success? Are infrastructure and scalability considerations addressed for the expected launch load? (Moderate — usually covered)

### Quick Reference: Gates per Scale (for `theory_gates_status` initialization)

| Scale | Total Gates | Gate Names |
|-------|-----------|------------|
| L0 | 5 | Evidence, Cynefin, Bias, BVSSH, Corrections |
| L1 | 7 | Evidence, Four Risks, JTBD, Cynefin, Bias, BVSSH, Corrections |
| L2 | 9 | Evidence, Four Risks, JTBD, Cynefin, Bias, Privacy, BVSSH, Service Quality, Corrections |
| L3 | 12 | All gates |
| L4 | 11 | All except JTBD |
| L5 | 8 | Evidence, Cynefin, Bias, Security, BVSSH, Delivery Metrics, Corrections, Regulatory |
