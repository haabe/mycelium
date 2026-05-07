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
**Last updated**: 2026-05-08.

## The project that didn't ship

A planned macOS file viewer that **never wrote a line of code**. Killed in L0 Discovery after a mocked-persona exercise: 4 of 6 personas would not switch defaults, including the modal user.

Mycelium correctly forced the stop. The framework's value here is not in shipping; it's in not-shipping with evidence — a 12-finding dogfood report that the framework then turned into mechanism.

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

It's the strongest counter-example to "AI agents always build". The framework's mocked-persona discipline saved the founder from building an unwanted product, and the kill produced more durable framework value than either of the projects that did ship.

This is the receipt the receipts argument rests on. It does not rotate.
