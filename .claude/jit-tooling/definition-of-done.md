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

## Product Type Variants (v0.11.0)

The checklist above is written for software products. For non-software product types, use the appropriate variant below. Items from the universal checklist (Delivery Health, Documentation) still apply.

### Content Products (content_course, content_publication, content_media)

Replace Code Quality and Testing with:
- [ ] Content reviewed by subject matter expert (or self-review with checklist)
- [ ] No factual errors or unsupported claims
- [ ] Sources attributed where applicable
- [ ] Consistent formatting, style, and terminology throughout
- [ ] Learning objectives met (courses: aligned to Bloom's taxonomy level)

Replace Accessibility with:
- [ ] Captions/subtitles for video content
- [ ] Transcripts for audio content
- [ ] Alt text for all images and diagrams
- [ ] Readable typography (sufficient size, contrast, line spacing)
- [ ] Structured headings for navigation

Replace Security with:
- [ ] If behind paywall/LMS: access control tested
- [ ] No personal data collected without consent
- [ ] No secrets in published content (API keys in tutorials, etc.)

Replace Delivery Health with:
- [ ] Publication cadence not degraded
- [ ] Content metrics updated in content-metrics.yml
- [ ] Corrections.md updated if content errors were found

### AI Tools (ai_tool)

Replace Testing with:
- [ ] Prompt/model evaluated against test cases (accuracy, consistency)
- [ ] Red-team testing completed (adversarial inputs, jailbreak attempts, harmful output)
- [ ] Bias assessment completed (demographic, cultural, domain-specific)
- [ ] Output variance within acceptable bounds
- [ ] Edge cases tested (empty input, very long input, multilingual, ambiguous)

Add:
- [ ] EU AI Act risk classification assessed (Annex III categories)
- [ ] If user-facing AI: transparency disclosure present (Article 50)
- [ ] Model/prompt version tracked and rollback possible
- [ ] Training data provenance documented (if fine-tuned)

### Service Offerings (service_offering)

Replace Code Quality and Testing with:
- [ ] Service blueprint reviewed (end-to-end client journey mapped)
- [ ] Client onboarding flow tested (at least one real or simulated run-through)
- [ ] Pricing validated against market (competitive analysis or client feedback)
- [ ] Delivery workflow documented and repeatable
- [ ] Handoff points clearly defined (where client action is needed)

Replace Delivery Health with:
- [ ] Service metrics updated in service-metrics.yml
- [ ] Client satisfaction measured (even informal feedback counts)
- [ ] Corrections.md updated if delivery issues found
