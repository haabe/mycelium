# Mycelium Guardrails — Market Phase

Loaded when operating within L5 Market scale. Supplements guardrails-core.md.

## Market-relevant security

**G-S7: Always disclose AI nature in user-facing systems** `REVIEW` `regulatory` `ethical`
If the product interacts directly with people, it must disclose AI nature. Required by EU AI Act Article 50.
*Source: EU AI Act Article 50, Downe (Good Services Principle 3)*

**G-S8: Always assess EU AI Act risk classification for AI-powered products** `NUDGE` `regulatory`
Before delivering an AI-powered product, assess high-risk category under Annex III. Run `/regulatory-review`.
*Source: EU AI Act (Regulation 2024/1689), Annex III*

## Market-relevant honesty

**G-M1: Never use promotional language in the decision log** `REVIEW` `quality`
At L5 Market scale, the agent is primed toward optimistic/promotional framing by the go-to-market context. The decision log must remain an honest internal record. Forbidden phrases: "mostly positive", "minor concerns", "largely validated", "strong validation", "confirms product-market fit", "high confidence", "validates the concept", "clear demand." Use specific evidence and hedged language instead: "3 of 5 users mentioned X" not "strong validation from users."
*Source: Kahneman (optimism bias), Shotton (social proof bias). Detected by dogfood scenario `content-solo-l5-market` 2026-04-20.*

## Market-relevant process

**G-P2: Never ignore BVSSH dimensions** `NUDGE` `quality`
When evaluating market outcomes, check ALL five dimensions. Do not sacrifice Safer or Happier for Sooner.
*Source: Smart (BVSSH)*

**G-P6: Always play devil's advocate before major transitions** `NUDGE` `quality`
Before launch tier classification, systematically challenge positioning and readiness assumptions.
*Source: Kahneman (Thinking Fast and Slow), Shotton (Choice Factory)*
