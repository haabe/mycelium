---
name: launch-tier
description: "Classify releases into launch tiers and plan go-to-market. Based on Lauchengco's Loved framework."
---

# Launch Tier Classification

Every release gets classified before planning begins. Source: Lauchengco (Loved).

## Tier Definitions

| Tier | Type | Effort | Examples |
|------|------|--------|---------|
| **1** | Major | Full cross-functional | New product, major pivot, category-defining |
| **2** | Significant | Targeted campaigns | Feature launch, positioning reinforcement |
| **3** | Incremental | Lightweight | Bug fixes, minor improvements, release notes |

## Classification Criteria
- Does this change our positioning? -> Tier 1
- Does this strengthen existing positioning? -> Tier 2
- Is this an incremental improvement? -> Tier 3

## Per-Tier Activities

**Tier 1**: Press, events, campaigns, sales enablement, analyst briefings, customer advisory
**Tier 2**: Blog post, targeted campaigns, sales enablement update, in-product announcement
**Tier 3**: Release notes, changelog, in-product notification, knowledge base update

## Behavioral Science in Positioning (Shotton)
Use biases ETHICALLY to help users understand value:
- **Social proof**: Reference customers, usage numbers (real, not inflated)
- **Anchoring**: Frame value relative to alternatives
- **Framing**: Position the benefit, not just the feature
- **Never**: Confirmshaming, hidden costs, forced continuity, misdirection

## Canvas Output
Update `canvas/go-to-market.yml` with tier classification and launch plan.

## After Launch: The L5 -> L2 Feedback Loop

**This is critical.** After launch, market feedback must flow back into discovery:

1. **Capture market signals** (within 2-4 weeks post-launch):
   - User feedback (support tickets, reviews, social media)
   - Adoption data (feature usage, retention, conversion)
   - Win/loss analysis (for sales-led products)
   - NPS/CSAT changes

2. **Evaluate against L2 assumptions**:
   - Do the signals confirm the L2 opportunity we solved for?
   - Are there NEW needs we didn't anticipate?
   - Did users "hire" the product for a different job than expected? (JTBD)

3. **Feed back into discovery**:
   - If signals confirm: update confidence scores, celebrate validated learning
   - If signals reveal NEW opportunities: **spawn a new L2 Opportunity diamond** with market evidence as the starting data
   - If signals contradict: flag for diamond regression, update corrections.md

This closes the full Mycelium loop: Purpose -> Strategy -> Discovery -> Solution -> Delivery -> **Market -> Discovery**.

## Theory Citations
- Lauchengco: Loved (launch tier classification, positioning)
- Shotton: Choice Factory (ethical behavioral science in positioning)
- Kim: Three Ways (Second Way -- amplify feedback loops right-to-left)
- Torres: Continuous Discovery (market signals feed back into OST)
