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
- **Happier**: Are users happier? Is the team happier? Is this sustainable?

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
