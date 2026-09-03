---
id: 2026-08-16-l1-population-read
date: 2026-08
contributor: internal-dogfood
contributor_link: null
project: mycelium-roadmap
mechanism_or_status: research-hand-read-population-sweep
commits: []
subclass: market-research
---

# 46 posts, shipped and nobody came: what people actually did next

**Audience**: evaluators and anyone deciding whether "talk to users first" is real advice or a slogan.
**Time to read**: 4 min.
**Last updated**: 2026-08-16.

## The question

Every subreddit for people building software carries the same confession on a loop: shipped it, nobody came. The advice under those posts is almost always "you should have talked to users first." Nobody had checked whether the people posting had actually done that, or what happens after they didn't.

## The method

46 posts, hand-read one at a time, across r/microsaas, r/SideProject and r/vibecoding, each one a confirmed "I shipped and got no traction" moment, not a general complaint thread. Each post classified on one question only: does the author say, anywhere in their own words, that they talked to a person who has the problem, before or after shipping?

Full method, the pre-registered classification rules, and the post-by-post breakdown live in the roadmap repo's own evals: `.claude/evals/results/l1-sweeps/2026-08-16-self-reported-user-contact.md`.

## The result

| what they said | count | share of 46 |
|---|---|---|
| Never mentioned talking to anyone with the problem | 37 | 80% |
| Talked to people who had the problem, not yet users | 6 | 13% |
| Heard from people already using what they built | 3 | 6.5% |

Of the six who did reach problem-holders, most didn't describe it as a discrete step. It arrived fused into something else already underway: a sales call, a Facebook favor, an inbound question they had to answer. One sent thirteen cold emails and got nothing back from any of them. One did roughly fifty live demos and learned more from the forty-eight that didn't convert than from the two that did.

## What this is not

**Not a rate.** A builder who talked to users and never mentioned it stays invisible in a text-only read; the true share can only be higher than what's counted here. **The timing question stays open too.** The sweep coded *whether* contact happened, never *when* relative to build, so no post in this set demonstrates the clean "ask, then build" sequence. That sequence is not something this reading found anyone doing. It's the gap the numbers describe rather than close.

## Why it stays on the receipts list

It's the difference between an opinion about discovery and a count of it. The advice under every one of these posts already says "talk to users." What was missing was whether the population being told that had done it. For 37 of 46, the honest answer is that nobody said they had.
