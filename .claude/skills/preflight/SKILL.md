---
name: preflight
description: "Use before writing any code. Pre-implementation validation checklist to ensure readiness."
---

# Preflight Skill

Pre-code validation checklist. Run before every implementation task.

## Checklist

### Context
- [ ] corrections.md reviewed for relevant past mistakes
- [ ] patterns.md reviewed for applicable patterns
- [ ] Current diamond phase is Develop or Deliver
- [ ] Acceptance criteria are clear and measurable

### Scope
- [ ] This is the smallest vertical slice that delivers value
- [ ] Scope is explicitly bounded (what is NOT included)
- [ ] No speculative features (YAGNI check)
- [ ] Dependencies identified and available

### Technical Readiness
- [ ] Tech stack detected and understood
- [ ] Build/test/lint commands confirmed working
- [ ] Development environment functional
- [ ] Existing code patterns reviewed

### Security
- [ ] Data classification understood for this feature
- [ ] Security requirements identified (auth, input validation, etc.)
- [ ] No secrets will be hardcoded
- [ ] Dependencies checked for known vulnerabilities

### Accessibility
- [ ] Accessibility requirements identified
- [ ] Semantic HTML approach planned
- [ ] Keyboard interaction model defined
- [ ] Color contrast requirements noted

### Testing Strategy
- [ ] Test approach defined (unit, integration, e2e)
- [ ] Edge cases identified
- [ ] Error scenarios identified
- [ ] Test data/fixtures available or planned

### Definition of Done
- [ ] DoD criteria reviewed and understood
- [ ] All criteria are achievable within this task

## If Any Item Fails

Do not proceed to implementation. Instead:
1. Document what is missing.
2. Determine the fastest path to readiness.
3. Address the gap before writing code.

## Theory Citations
- Smart: BVSSH (Sooner -- avoid rework by preparing)
- Forsgren: Accelerate (reduce lead time by removing blockers early)
