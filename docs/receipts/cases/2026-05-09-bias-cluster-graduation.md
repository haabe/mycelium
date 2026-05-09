---
id: 2026-05-09-bias-cluster-graduation
date: 2026-05-09
contributor: Håvard Bartnes (founder dogfood)
contributor_link: CONTRIBUTORS.md
project: mycelium-self-discipline
mechanism_or_status: graduated
commits: ["TBD"]
subclass: skill-extension
---

# bias-cluster-graduation — three failure modes get an ambient self-check

**Audience**: contributors curious about how Mycelium converts named bias categories into per-publish self-checks rather than per-decision ceremony.
**Time to read**: 3 min.
**Last updated**: 2026-05-09.

## The cluster

`corrections.md` TL;DR (line 15) has been carrying a three-mode bias cluster as an open graduation candidate:

> *"Bias cluster (×3 distinct modes, common root): L5 sycophancy (G-M1), eval overfitting (anti-pattern), sharper framing isn't always more correct (anchoring without testing exclusion). Common shape: agent prefers what feels right over what evidence supports, especially under competing pressure. Open candidate: ambient `/devils-advocate` triggering on assertion-shaped patterns."*

Three distinct surfaces, one root cause. Each had been individually addressed (G-M1 for sycophancy, an anti-pattern for eval overfitting, a one-off correction for sharper-framing). None had a unified prevention mechanism. The graduation closes that gap.

## What graduated

Two new techniques in `plugins/mycelium/skills/devils-advocate/SKILL.md`:

**Technique 4 — Attribution-vs-Consistency Check.** Per anti-pattern #7 (*Consistency-as-Evidence*, sibling graduation in v0.21.0). For each piece of evidence supporting a claim, label it cleanly-attributed / consistency-only / unrelated. Mark chains provisional if any link is consistency-only. N=1 means no structural conclusion.

**Technique 5 — Ambient triggering on assertion-shaped patterns.** Beyond formal diamond-transition use, run a fast self-check whenever the agent writes text containing structural-claim shapes:
- "X causes Y"
- "this means Z"
- "the framework needs..."
- "the right answer is..."
- "this generalizes to..."

For each, ask: *what specific evidence supports this claim, and does any of it merely support it by consistency rather than attribution?* If you can't name cleanly-attributed evidence, downgrade the claim from assertion to hypothesis.

The "When to Use" section gains an "Ambient" entry — the techniques fire on every publish containing assertion-shaped claims, not only on formal decision points.

## Why this shape

The bias-cluster failure mode has historically been caught by the user, not the framework. L5 sycophancy was named when the user noticed promotional language in decision logs. Eval overfitting was named when Drew Hoskins flagged the "NOT" annotations. Sharper-framing was caught when the user pushed back on landscape.yml anchoring. Each correction shipped a localized prevention; none made the underlying bias *self-detectable* by the agent at output time.

Technique 5 changes the surface: by tying the check to assertion-shaped patterns in agent output, the prevention fires per-publish rather than per-decision. That's the promotion from "user catches the agent" to "agent catches itself before publishing."

## Theory grounding

- **Argyris** (double-loop): three localized single-loop fixes (G-M1, anti-pattern entry, one-off correction) didn't prevent the next instance because they were surface-specific. Double-loop graduation moves the rule to a self-check at output time, so the *class* of failure is caught regardless of which surface it manifests on.
- **Buçinca, Malaya & Gajos** (Cognitive Forcing Functions, Harvard CHI/CSCW 2021): forcing the agent's initial judgment into an explicit attribution-vs-consistency labeling step is exactly the cognitive forcing function shape — interrupts the System-1 substitution where consistency feels like evidence.
- **Mycelium's own discipline applied to itself**: the framework already uses this anti-bias shape on user behavior (devil's-advocate before major decisions); Technique 5 turns it inward.

## Mechanism + status

**Status**: graduated (2026-05-09). Two integration points:
- `/devils-advocate` Techniques 4 and 5 in the skill SKILL.md
- "When to Use" section extended with ambient triggering

**Coverage proof** (per G-V12): the three corrections.md instances cited in the cluster (L5 sycophancy 2026-04-20, eval overfitting 2026-04-30, sharper framing 2026-05-03) serve as the test fixtures. Each is a concrete worked example of the kind of assertion-shape claim Technique 5 would have caught.

**Watch-list**: if a 4th instance of the cluster pattern reaches publication despite the prevention, that's a signal Technique 5 needs to move from skill-time check to ambient hook (e.g., a Stop-event hook that scans agent output for assertion shapes and fires `/devils-advocate` automatically).

## Cross-references

- Sibling graduation: [consistency-as-evidence-graduation](2026-05-09-consistency-as-evidence-graduation.md) — anti-pattern #7, the specific attribution-failure subtype of the broader bias cluster
- Sibling graduation: [stale-state-read-graduation](2026-05-09-stale-state-read-graduation.md) — anti-pattern #8 in the same release
- Source corrections: `corrections.md` 2026-04-20 (L5 sycophancy → G-M1), 2026-04-30 (eval overfitting → anti-pattern entry), 2026-05-03 (sharper framing isn't always more correct)
- Existing related anti-patterns: #3 Confirmation Research, #6 Sycophancy
