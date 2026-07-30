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

## Authored Artifacts (fires on ANY prose edit, any product type — v0.66)

**Trigger: the work created or edited any prose artifact.** Not "touched a human-facing class." A draft of this section gated on the latter, which disarmed the agent-contract protection below in precisely the case it exists for — work that edits only `CLAUDE.md` and `SKILL.md` files would never have armed the section whose first checkbox protects them. Out-of-scope files (code, CI, test fixtures, third-party evidence) do not arm it; see `detector.md` Step 1d Step 0.

Classification rules and per-class treatment: `../engine/audience-register.md`. Note that `artifact_audiences` in `active-stack.yml` is a project-level inventory and cannot tell you which class a specific edit touched — derive that per-file from Step 1d.

- [ ] Audience class of each edited file identified by **path**, not by tone
- [ ] **`agent_contract` files were not trimmed, tightened, or given narrative structure.** Compression removes rules that hookless runtimes depend on. Includes READMEs inside agent trees, and `CLAUDE.md`/`AGENTS.md` at any depth — not just root
- [ ] If a size ceiling forced a reduction (Check 36, style budgets): the rule was **split out and linked**, not compressed — and a one-line statement of the obligation was left at the original site, so a runtime that does not follow links still learns the rule exists
- [ ] `human_reference` files carry no narrative machinery. Long is not a defect here unless the length is duplication or self-superseded content
- [ ] **Templates: scaffolding untouched, emitted prose written for its destination.** Placeholders, guidance comments and any token a downstream check matches on (section headings, `**Required**` markings read by `/xai-check`) are `agent_contract` and were not tidied. The prose that ships verbatim follows the destination's class
- [ ] **Structured config: human-display strings checked as copy.** `description`, `tagline`, `summary` and `title` values in JSON/YAML take the register check; keys, comments and structure in agent-tree config were not pruned as redundant
- [ ] **`human_persuasive`: register matched to the reader's awareness stage.** Checkable from the text — a mechanism claim aimed at someone who has not agreed they have the problem is the default failure
- [ ] **`human_persuasive`: falsifier stated, where a falsifiable claim exists.** Exempt for announcements and headlines that make no argument. Citation volume is not a substitute — narrowing a reader's view works as well inside a flood of true facts as without one

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
- [ ] DORA metrics not degraded (deployment frequency, lead time, failure rate, FDRT, reliability)
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
- [ ] **Efficacy criterion named and wired (v0.66)** — state what change in the receiver this content exists to produce, and which `content-metrics.yml` field will show whether it happened (`engagement.completion_rate`, drop-off point, `time_to_first_value`). Bloom alignment states the target; this states how you will know it landed.
- [ ] **Completion test run** — someone who did not write it finished the task using only this content, or the gap is named

**Why these two are not more hygiene.** Every other item above verifies the artifact is *well-formed* — reviewed, accurate, attributed, consistent, accessible. A course can satisfy all of them and be inert, because nothing asks whether it does its job. For a course or a publication, the receiver changing is not a quality attribute, it is the product promise. This is the built-not-wired failure class applied to content: the measurement already exists in `content-metrics.yml` and was simply never required by the gate. Naming an efficacy criterion you cannot yet measure is acceptable and honest; leaving the field null with no criterion named is the thing this item blocks.

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
