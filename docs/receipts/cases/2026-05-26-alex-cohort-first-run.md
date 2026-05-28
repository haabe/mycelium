---
id: 2026-05-26-alex-cohort-first-run
date: 2026-05-26
contributor: Alex
contributor_link: CONTRIBUTORS.md#v031x--cohort-first-run-friction-output-density--post-build-silence
project: alex-cohort-first-run
mechanism_or_status: shipped-v0.31.0-v0.31.2
commits: ["8acbed8", "51e73d0", "43e002e"]
subclass: first-run-friction
---

# alex-cohort-first-run — the deepest single session, and what it cost the reader

**Audience**: contributors and evaluators interested in how a deep first-run exposed output-density and post-build-silence gaps, driving the v0.31.x batch.
**Time to read**: 4 min.
**Last updated**: 2026-05-28.

## The friction

In May 2026, Alex (Juniors.dev cohort tester, cohort-tester-2) ran Mycelium on his own project in what became the deepest single first-run session the framework had seen: `/start` → interview → feature selection → research prompts → diamond progression → a proof-of-concept build. Further than the framework had been driven before.

Three things broke at depth:

1. **Post-build silence.** After the POC built, the agent "just kind of stopped and didn't prompt me for more info or advise what to do next." He had to dig through the README to find `/diamond-assess` to get back on course.
2. **"Brain fried from the gigantic walls of text."** Output density forced a session break — framework-wide, not skill-specific.
3. **"Kept getting a little lost in the vocabulary."** Skill names assume product-thinking fluency. His own framing — "I assume someone familiar with the vocabulary would find it less straining" — was itself the signal: a tester shouldn't have to wonder "is it just me?"

He also flagged that the POC shipped "riddled with bugs" with no gate catching it — *"the framework should have caught that before declaring complete,"* not a write-better-tests problem.

## What changed

- **Post-build silence** → v0.31.1 post-build-silence nudge (`51e73d0`).
- **Walls of text** → v0.31.2 BLUF + Footnote output convention (`43e002e`): every emission layers BLUF → rationale → discipline-notes-below-the-fold. Research-grounded (Sweller CLT, Cowan ~4 chunks, Nielsen F-pattern, W3C COGA).
- **Vocabulary** → queued as L0–L2 discoverability hardening.
- **Buggy POC** → candidate L4 code-quality scenario (PHASE-5-HARDENING).

(v0.31.0, `8acbed8`, set up the 4-layer adoption composition this batch built on.)

## What this case taught the framework

The walls-of-text fix is the honest-caveat case: the chain "output density → comprehension failure → cohort attrition" is `consistency_only` at N=1. The convention is research-informed, not research-validated for this surface — a `/prompt-optimizer` A/B is the right next step. The fix shipped anyway because the friction was real and the layering costs nothing when there's little to say.

## Mechanism + status

**Status**: shipped-v0.31.0–v0.31.2. Vocabulary + L4 code-quality items queued post-recovery.

## Attribution note

Alex consented to be named on 2026-05-26. Already-shipped commits (`51e73d0`, `43e002e`) use "cohort-tester-2"; this case adds the named attribution going forward without rewriting history.
