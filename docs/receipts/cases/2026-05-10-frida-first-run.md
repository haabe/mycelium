---
id: 2026-05-10-frida-first-run
date: 2026-05-10
contributor: Frida
contributor_link: CONTRIBUTORS.md#v0239--first-run-friction-batch-cautious-learner-observer
project: frida-first-run
mechanism_or_status: shipped-v0.23.9
commits: ["fe5f282", "9c021b6", "d05968a"]
subclass: first-run-friction
---

# frida-first-run — the most thorough first-run observation the framework had

**Audience**: contributors and evaluators interested in how a single careful first-run log drove a whole patch batch, and how Mycelium handles cautious-learner onboarding friction.
**Time to read**: 4 min.
**Last updated**: 2026-05-28.

## The friction

On 2026-05-10, Frida ran Mycelium end-to-end on a real project of her own — a public-sector mobile app for next-of-kin in home care (GDPR, healthcare, AI-naive end users). She prepared before starting, read every prompt before approving, and wrote a structured recap the next day. It is the most thorough first-run observation the framework has received.

Her log produced ten friction points. Two landed especially hard:

- **A real bug**: "Session ended. 0 corrections, 0 decisions logged" appeared between *every* interview question — hook output leaking into the interview. She read it as an error message. It was one.
- **A discipline the framework should have enforced itself**: when the agent moved to update her brief, she asked that the originals be preserved as `revision_note` / `confidence_note`. That is exactly the evidence-preservation discipline Mycelium claims — surfaced by the user, not the framework.

## What changed

Seven of the ten points became opportunity-tree entries (opp-001–007); four–five shipped in the v0.23.9 batch:

- the "0 corrections / 0 decisions" hook leak removed; "0 skills" / "0 corrections" now distinguish *not-initialized* from *empty* from *N*
- the AGENTS.md prompt got say-yes-or-skip framing before the question
- README updated (the old time-budget question described a flow `/interview` no longer runs — what she went looking for)
- L0 confidence 0.15 now shows the formula behind the value, not just "we know it's wrong"
- "Phase 6" and other internal vocabulary no longer leak to the user (explicit skill prohibition, with her examples as ✗-patterns)

## The deeper finding (cohort-tester-1)

Two weeks later, as cohort-tester-1, Frida named the framework's deepest unsolved surface verbatim: *"the terminology feels like it's written for people who already know the frameworks."* She also flagged that `/diamond-assess` reads as "evaluation," not "where were we," on re-entry. She nearly held the note back, attributing it to her own tiredness — but the friction is structural, not state-dependent, and her "is it just me?" framing was itself the signal. This is now driving the L0–L2 discoverability hardening.

## Mechanism + status

**Status**: shipped-v0.23.9 (`fe5f282` batch 1 opp-001/002/003/004; `9c021b6` batch 2 opp-005/006/007; `d05968a` release). The vocabulary / re-entry findings are queued as L0–L2 discoverability hardening.

## Attribution note

Frida consented to be named on 2026-05-26 (prior references were generic per a two-surface consent model). Her project is named only by the generic descriptor above, at her request — the project name is withheld in all artifacts.
