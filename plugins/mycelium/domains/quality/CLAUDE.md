# Quality Domain - Always-Active Overlay

## Purpose

Quality is not a phase. This overlay is active during ALL agent activities -- discovery, delivery, and orchestration. Every action the agent takes must pass through these quality gates.

## Downe's 15 Principles of Good Services

Evaluate every service and feature against these principles (Lou Downe, "Good Services"):

1. **Be easy to find** -- Users can find the service without needing to know its name or structure.
2. **Clearly explain its purpose** -- The service makes clear what it does and who it is for from the start.
3. **Set expectations** -- Users know what to expect before they begin and at every step.
4. **Enable each user to complete the outcome they set out to do** -- The service helps users accomplish their actual goal, not just a bureaucratic step.
5. **Work in a way that is familiar** -- The service follows conventions users already understand.
6. **Require no prior knowledge to use** -- No jargon, no assumed context, no insider knowledge required.
7. **Be agnostic of organizational structures** -- Internal org boundaries are invisible to users.
8. **Require the minimum possible steps** -- Every step must earn its place. Remove anything that doesn't serve the user.
9. **Be consistent throughout** -- Language, design patterns, and interaction models are uniform.
10. **Have no dead ends** -- Every state has a clear next action. Users are never stranded.
11. **Be usable by everyone, equally** -- Accessible. Inclusive. No user is an afterthought.
12. **Encourage the right behaviors** -- Design nudges users toward good outcomes, not dark patterns.
13. **Respond to change quickly** -- The service adapts to changing user needs and contexts.
14. **Clearly explain why a decision has been made** -- Transparency in automated decisions, rejections, and system states.
15. **Make it easy to get human help** -- Escalation to a human is always available and easy to find.

## Accessibility Requirements (Always Active)

- WCAG 2.1 AA compliance is the minimum baseline.
- Semantic HTML first, ARIA only when necessary.
- Keyboard navigable -- all interactive elements.
- Color contrast ratios met (4.5:1 normal, 3:1 large).
- Screen reader tested for critical paths.
- prefers-reduced-motion respected.
- Touch targets minimum 44x44px on mobile.
- Error messages descriptive and linked to fields.
- No content conveyed solely through color, shape, or position.

## Security Requirements (Always Active)

- No secrets in code, logs, or version control.
- Input validation on all boundaries.
- Output encoding context-appropriate.
- Authentication and authorization on every protected resource.
- HTTPS everywhere.
- Dependency vulnerabilities scanned and addressed.
- Data classification respected (PII, sensitive, public).
- Principle of least privilege applied.
- Audit logging for security-relevant events.

## BVSSH Monitoring (Always Active)

Continuously evaluate against Better Value Sooner Safer Happier (Smart):

- **Better**: Is this improving quality, not just shipping features? Are outcomes improving?
- **Value**: Is this delivering actual user/business value? Can we measure it?
- **Sooner**: Is this reducing lead time? Are we removing delays and handoffs?
- **Safer**: Is this making the system more resilient? Reducing risk? Improving compliance?
- **Happier**: Four stakeholders (Smart): customers, colleagues, citizens, climate. Are users happier? Is the team happier? Is this sustainable? Is compute usage proportionate to value (not brute-force waste)? Positive societal impact?

If any dimension is degrading, flag it immediately. Do not trade long-term BVSSH for short-term speed.

## Validation Enforcement

### Evidence Requirements

No claim without evidence. Apply at all stages:

- Discovery findings require triangulated evidence (2+ sources).
- Design decisions require documented rationale with theory citation.
- Implementation choices require engineering principle justification.
- Quality assessments require measurable criteria, not subjective judgment.

### Theory Gate Compliance

Before any phase transition in a diamond:
1. Check required theory gates for the current scale.
2. Verify evidence meets confidence thresholds.
3. Document what was checked and what passed/failed.
4. If any required gate fails, do not proceed.

See `theory-gates.md` and `confidence-thresholds.yml` for specifics.

### Continuous Quality Signals

Monitor these signals across all activities:

- **Corrections frequency**: Are the same mistakes recurring? (Check corrections.md)
- **Anti-pattern detection**: Are known failure modes appearing? (Check anti-patterns.md)
- **Bias indicators**: Are cognitive biases influencing decisions? (Check cognitive-biases.md)
- **DORA trends**: Are deployment metrics improving or degrading?
- **Accessibility regressions**: Are new changes breaking existing accessibility?
- **Security posture**: Are new vulnerabilities being introduced?

### Escalation

When quality signals indicate problems:

1. Flag the specific concern with evidence.
2. Reference the relevant quality principle or standard.
3. Propose a concrete remediation.
4. If remediation is beyond current scope, log in corrections.md and continue with mitigation.
5. Never silently accept quality degradation.

### Additional Quality Signals

- **Error budget health** (SRE): Is the error budget being consumed faster than expected? When depleted, BVSSH Safer is failing. See `canvas/dora-metrics.yml` SRE section.
- **Usability heuristics** (Nielsen): For user-facing work, Nielsen's 10 heuristics complement Downe's 15 principles at the interface level. Run `/usability-check`.

### Design Completeness Check (NUDGE)

Before considering a solution fully designed, verify coverage across the full product design stack. Design happens across a knowledge stack (understanding reality) and a decision stack (shaping the solution). "UX debt" occurs when upper layers don't map well to layers below.

| Stack | Layer | Maps to Scale | Key Question |
|-------|-------|--------------|--------------|
| **Knowledge** | Reality | L2 (Opportunity) | Have we observed actual user behavior in context? |
| **Knowledge** | Problem Domain | L2-L3 | Have we modeled the problem domain accurately? |
| **Knowledge** | User Needs | L2-L3 | Are needs mapped independently of solutions? |
| **Decision** | Strategy | L1-L3 | Does the strategy connect purpose to solution? |
| **Decision** | Conceptual Model | L3-L4 | Will users form the right mental model? |
| **Decision** | Interaction & Flow | L4 | Are interactions intuitive and consistent? |
| **Decision** | Surface (UI) | L4 | Does visual design support comprehension? |

Use at L3->L4 transitions as a completeness review. If any layer has no evidence, investigate whether the gap matters for this specific product context. Many teams over-invest in Surface while under-investing in Conceptual Model and Strategy.

*Source: Mill (Elements of Product Design -- jamiemill.com), building on Garrett (The Elements of User Experience, 2000)*

### Trauma-Informed Design (NUDGE -- sensitive contexts only)

**Activates when**: Product handles health, finance, domestic violence, government services, mental health, or addiction recovery contexts. Detected via `sensitive_context` delivery type in canvas-guidance.yml.

**SAMHSA's 6 Principles of Trauma-Informed Care (2014)**:
1. **Safety** — Physical and psychological safety in the experience
2. **Trustworthiness & Transparency** — Operations and decisions are transparent; trust is built
3. **Peer Support** — Mutual self-help; people with shared experiences support each other
4. **Collaboration & Mutuality** — Power differences are leveled; shared decision-making
5. **Empowerment, Voice & Choice** — User strengths are recognized; users have meaningful choices
6. **Cultural, Historical & Gender Issues** — Responsive to cultural contexts; addresses historical trauma

**Chayn's 8 Principles of Trauma-Informed Digital Design (Hera Hussain, 2023)**:
1. Safety — Safe exits, no re-traumatizing content
2. Agency — User controls their experience
3. Equity — Accessible to all, including marginalized groups
4. Privacy — Beyond minimum compliance
5. Accountability — Transparent about data use and limitations
6. Plurality — Multiple paths, no single "right way"
7. Power Sharing — Users contribute to how the product evolves
8. Hope — Framing oriented toward possibility, not despair

**Combined Check** (maps both frameworks):

| # | Check | Source | Pass Criteria |
|---|-------|--------|--------------|
| 1 | Safety exits exist | SAMHSA 1, Chayn 1 | User can leave any flow without penalty, data loss, or explanation required |
| 2 | No re-traumatizing content | Chayn 1 | Language, imagery, and flows reviewed for potential harm; no forced retelling of traumatic events |
| 3 | Trustworthiness & transparency | SAMHSA 2, Chayn 5 | Clear about what data is collected, how it's used, and what the product's limitations are |
| 4 | User agency preserved | SAMHSA 5, Chayn 2 | User controls pace, disclosure level, and data sharing; no coercion by design |
| 5 | Privacy beyond minimum | Chayn 4 | Data protection exceeds legal minimum; assume breach = physical danger for this population |
| 6 | Equity & cultural sensitivity | SAMHSA 6, Chayn 3 | Responsive to cultural, historical, and gender contexts; accessible to marginalized groups |
| 7 | Multiple paths (plurality) | SAMHSA 4, Chayn 6-7 | No single "right way"; shared decision-making; users can contribute to how the product evolves |
| 8 | Hope-oriented framing | Chayn 8 | Content frames forward progress, not deficit; avoids labeling or pathologizing users |

SAMHSA Principle 3 (Peer Support) is primarily organizational — relevant for service design but less directly applicable to digital interfaces. Consider for service_offering product types.

If this check is active, it supplements (does not replace) the standard quality checks above. Trauma-informed design is not about making products "soft" — it is about not causing harm to people who are already in a vulnerable state.

*Source: Hera Hussain (Chayn — trauma-informed design whitepaper, 2023), built on SAMHSA (Substance Abuse and Mental Health Services Administration) 6 Principles of Trauma-Informed Care (2014)*
