# Universal Definition of Done

Every delivery increment must satisfy ALL applicable items before being considered complete.

## Code Quality (ALL stacks)
- [ ] Code reviewed (or pair/mob programmed)
- [ ] No duplicated logic (DRY) -- checked existing implementations first
- [ ] Simplest working solution chosen (KISS)
- [ ] No speculative features added (YAGNI)
- [ ] Clean separation between layers/modules (SoC)
- [ ] SOLID principles followed
- [ ] Meaningful names, small functions, clear intent

## Testing (ALL stacks)
- [ ] All automated tests pass (unit, integration, e2e as applicable)
- [ ] New code has tests (written alongside, not after)
- [ ] Edge cases and error paths tested
- [ ] No test exclusions to make validation pass

## Type Safety (typed languages)
- [ ] Type checking passes with zero errors
- [ ] No `any` escape hatches (TS) or equivalent type-system bypasses
- [ ] API contracts typed at boundaries

## Linting & Formatting (ALL stacks)
- [ ] Linting passes with zero errors
- [ ] Formatting is consistent (automated formatter applied)
- [ ] Dead code removed

## Security (ALL stacks)
- [ ] Input validation on all external inputs
- [ ] No new security vulnerabilities introduced (dependency audit)
- [ ] No secrets in code, logs, or config
- [ ] Error messages don't leak internal details
- [ ] If user data involved: threat model updated, privacy check done

## Accessibility (user-facing work)
- [ ] WCAG 2.1 AA requirements met
- [ ] Semantic HTML / appropriate ARIA
- [ ] Keyboard navigation works
- [ ] Color contrast sufficient
- [ ] Screen reader tested (or automated a11y scan clean)

## Service Quality (user-facing work)
- [ ] Error states designed -- not just happy path (Downe P10)
- [ ] No dead ends in user flows (Downe P10)
- [ ] Decisions explained to users where applicable (Downe P14)
- [ ] Human help accessible where applicable (Downe P15)
- [ ] Consistent with existing patterns (Downe P9)

## Documentation
- [ ] Public API documentation updated if changed
- [ ] Breaking changes documented

## Delivery Health
- [ ] DORA metrics not degraded (deployment frequency, lead time, failure rate, MTTR)
- [ ] Corrections.md updated if new patterns discovered
- [ ] Delivery journal updated with outcome

## Applicability

Not every item applies to every increment. Use judgment:
- Backend API with no UI: skip accessibility items
- Internal tool: lighter service quality standards
- Security-critical feature: heavier security review
- Prototype/experiment: lighter overall (but NEVER skip security)
