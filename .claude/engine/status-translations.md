# Status Translations: Technical -> Human-Readable

When reporting diamond state to the user, ALWAYS translate technical taxonomy to plain language FIRST, then optionally show technical details.

## Diamond Scale Translations

| Technical | Plain Language |
|-----------|---------------|
| L0: Purpose | "Defining why this product exists" |
| L1: Strategy | "Mapping the strategic landscape" |
| L2: Opportunity | "Discovering what problems to solve" |
| L3: Solution | "Designing how to solve the problem" |
| L4: Delivery | "Building and shipping the solution" |
| L5: Market | "Getting the product to users" |

## Phase Translations

| Technical | Plain Language | What's Happening |
|-----------|---------------|-----------------|
| Discover | "Exploring broadly" | Gathering evidence, challenging assumptions, diverging |
| Define | "Narrowing focus" | Synthesizing discoveries, framing the problem |
| Develop | "Generating solutions" | Ideating, prototyping, comparing options |
| Deliver | "Building and validating" | Implementing, testing, shipping, measuring |

## Combined Status Examples

| Technical State | Plain Language |
|----------------|---------------|
| L0 Purpose - Discover | "Understanding why this product needs to exist. Interviewing stakeholders, exploring the problem space." |
| L0 Purpose - Define | "Crystallizing the product's purpose. Defining mission, vision, values, and ethical boundaries." |
| L2 Opportunity - Discover | "Mapping what users actually need. Conducting interviews, analyzing data, building the opportunity tree." |
| L2 Opportunity - Define | "Prioritizing which problems to solve first. Scoring opportunities by impact, confidence, and strategic fit." |
| L3 Solution - Develop | "Designing solutions for [opportunity name]. Comparing [N] approaches, testing assumptions." |
| L4 Delivery - Deliver | "Building [feature name]. Writing code, tests, and documentation. Validating against acceptance criteria." |
| L5 Market - Discover | "Understanding how to reach users. Analyzing channels, competitors, and positioning options." |

## Confidence Translations

| Score | Gilad Level | Plain Language |
|-------|-------------|---------------|
| 0.1 | Speculation | "Just an idea -- no evidence yet" |
| 0.3 | Anecdotal | "Some signals, but not validated" |
| 0.5 | Data-supported | "Data supports this direction" |
| 0.7 | Test-validated | "Tested and confirmed with real users/data" |
| 0.9 | Launch-validated | "Proven in production" |

Always add context: WHY this level is appropriate and WHAT would increase it.

Example: "Confidence: Moderate (0.6, data-supported). Based on 1 detailed interview covering your full user base. Would increase with external user testing."

## Progress Summary Format

When asked for status or when reporting after a transition, use this format:

```
Current focus: [plain-language description of what we're doing]
  [1-2 sentences of context about what's been accomplished]
  Next step: [what comes next in plain language]
  Confidence: [plain word] ([number], [Gilad level]) -- [why and what would increase it]

Progress: [N] of [M] diamonds complete
  [Diamond name]: [STATUS in caps] -- [one-line plain description]
  [Diamond name]: [STATUS in caps] -- [one-line plain description]
  ...

[If skills are recommended for next step:]
Suggested next actions:
  - /skill-name -- [why this is relevant now]
  - /skill-name -- [why this is relevant now]
```

## Skipped Diamond Explanation

When a diamond is skipped, always explain in plain language:
- WHAT was skipped
- WHY it was skipped (with anti-pattern reference if applicable)
- WHEN it might become relevant

Example: "Strategy mapping skipped -- for a solo hobby project, strategic portfolio management would be gold-plating. Would become relevant if this grows into a product with multiple user segments."
