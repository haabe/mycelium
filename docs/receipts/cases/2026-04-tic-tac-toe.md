---
id: 2026-04-tic-tac-toe
date: 2026-04
contributor: internal-dogfood
contributor_link: null
project: tic-tac-toe
mechanism_or_status: one-off
commits: []
subclass: null
---

# tic-tac-toe — what Mycelium learned

**Audience**: practitioners curious about what early Mycelium dogfood looked like on a real shipped project.
**Time to read**: 3 min.
**Last updated**: 2026-05-08.

## The project

[huggingface.co/spaces/haabe/tic-tac-toe](https://huggingface.co/spaces/haabe/tic-tac-toe). React + TypeScript + Node.js WebSocket on Hugging Face Spaces. 40 Vitest tests. WCAG 2.1 AA accessible. Zero human-written lines of code. The agent plus early Mycelium carried it end-to-end.

## What it taught the framework

One durable engineering pattern came out: **optimistic UI in client-server real-time apps**. The agent shipped a desync bug between the client's optimistic move-render and the server's authoritative reconciliation. Mycelium's reflexion loop caught the desync on the next play-test and the fix landed in that project's `.claude/memory/corrections.md` so the agent will not ship the same bug shape on the next real-time UI project.

This case is "one-off": no cluster, no graduated mechanism, just a project-local correction. It is here on the receipts list because the discipline of logging it — even when it didn't escalate — is the mechanism that makes everything else work.

## Why it stays on the receipts list

It's the cleanest small example of the loop: a real bug, a recorded correction, a future project guarded by it. The framework-self-correction case (May 2026) shows the same loop at scale; this one shows it at minimum viable scale.
