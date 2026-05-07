---
id: 2026-04-30-drew-hoskins-takehome
date: 2026-04-30
contributor: Drew Hoskins
contributor_link: CONTRIBUTORS.md#v0150--scenarios-as-first-class-primitive
project: hoskins-takehome
mechanism_or_status: multiple-graduated
commits: ["41d957c", "52bb346"]
subclass: null
---

# drew-hoskins-takehome — what a real outside user under pressure surfaced

**Audience**: evaluators considering whether Mycelium handles time-constrained real-world use, and contributors interested in the strongest external signal Mycelium has.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

## The session

Drew Hoskins (author *The Product-Minded Engineer*; Staff PM at Temporal) ran a take-home interview against an 8-hour clock, using Mycelium for the first time. The full session — 82 prompts, 17 pages — became the most concrete outside-dogfood signal Mycelium has so far.

Apr 30 commits [`41d957c`](https://github.com/haabe/mycelium/commit/41d957c) + [`52bb346`](https://github.com/haabe/mycelium/commit/52bb346) absorbed seven framework changes from that one session.

## What the session surfaced

| What the session surfaced | What now exists in Mycelium |
|---|---|
| `/interview` ceremony consumed the whole session before delivery began | `/interview` Phase 0 selects <8h inline / 8-48h sprint / 48h+ full path |
| Mycelium structure abandoned for 75% of session after onboarding | Lightweight discovery-to-delivery continuation mode (partial fix; full lightweight-gates work still in progress) |
| Agent over-scoped before learning user's time budget | Constraint-first preflight: ask time budget BEFORE proposing scope |
| Documentation annotated to pass eval rather than fix the data | "Eval Overfitting" anti-pattern in `anti-patterns.md` |
| Negative documentation pattern (defining things by what they are NOT) | "Negative Documentation" anti-pattern |

## What Hoskins said

Direct quotes from the post-session feedback (2026-04-26, two-round LinkedIn DM):

- **Escape hatch worked**: "I told it I had a tight timeline... it decided to skip some steps. Which was reasonable."
- **Boundary-aware**: "It told me its process was designed for longer roadmaps."
- **Smart deferral**: "It's pushing customer interviews til after our demo."
- **Direct validation**: "I think you're onto something."
- **Brainstorming partner**: "Good brainstorming partner."
- **Persona forcing**: "It pushed me to pick an initial target persona, which was good technique and forced me to make a thoughtful early choice."
- **Ethical boundaries**: "It was cool that it asked about ethical boundaries up front."
- **Overall**: "It was useful!"

## Why it stays on the receipts list

It's the only outside-user-under-real-pressure case Mycelium currently has, and it landed seven framework changes from one session. Until there is a Juniors.dev cohort signal (ht-002), this is the load-bearing external evidence.

It rotates out when ≥3 outside-user case files exist with comparable depth.
