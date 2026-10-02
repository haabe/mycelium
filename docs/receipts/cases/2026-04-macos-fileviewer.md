---
id: 2026-04-macos-fileviewer
date: 2026-04
contributor: internal-dogfood
contributor_link: null
project: macos-fileviewer
mechanism_or_status: multiple-graduated
commits: []
subclass: null
---

# macos-fileviewer — what Mycelium stopped, and what that gave it

**Audience**: evaluators and contributors. The cleanest demonstration of "killing a project early is the framework working."
**Time to read**: 5 min.
**Last updated**: 2026-10-02 (corrected: the stop rested on simulated personas, and no real person was asked).

## The project that didn't ship

A planned macOS file viewer that **never wrote a line of code**. Stopped in L0 Discovery after a mocked-persona exercise, run instead of real interviews: 4 of 6 personas would not switch in its scoped form, including the modal user. The project's own decision log (2026-04-09) graded that as speculation, lowered confidence from 0.4 to 0.35, called it "stop and reconsider" rather than abandonment, and listed real user interviews among the next moves. They were never run; the founder took the simulated no as enough.

Mycelium forced the stop and labelled it honestly, as speculation. The value here is not in shipping, and it is not evidence that the idea was wrong: it is the 12-finding dogfood report the framework then turned into mechanism.

## What the kill produced

| What the kill found | What now exists in Mycelium |
|---|---|
| No discipline for mocked personas | `/mocked-persona-interview` skill |
| No "I'm dogfooding the framework" project mode | `meta_dogfood` project type, `dogfood: true` canvas flag |
| Two memory systems undocumented and overlapping | Memory boundary section in `CLAUDE.md` |
| Reflexion hook fired on agent-internal failures | Hook scoped to project-relevant failures only |
| No sanctioned exit from a stuck diamond | `/diamond-progress pivot/park/kill` subcommands |
| Strategic loop checks easy to ignore | `/feedback-review` skill |
| No quarterly framework self-assessment | `/framework-health` skill |
| Canvas drifts toward confident-sounding speculation | `/canvas-health` lints provenance and staleness |
| No mechanism for the framework to learn from its cycles | `cycle-history.yml` + adaptive thresholds + framework-reflexion |
| No accumulator for dogfood findings | `.claude/evals/dogfood-reports/` directory |

## Why it stays on the receipts list

It's the strongest counter-example to "AI agents always build". The framework's mocked-persona discipline stopped the founder before any code, on speculation it named as speculation, and the stop produced more durable framework value than either of the projects that did ship. Whether the product was unwanted is not known: no real person was asked.

This is the receipt the receipts argument rests on. It does not rotate.
