---
id: 2026-05-28-canvas-drift-reconciliation
date: 2026-05-28
contributor: Mycelium (dogfood self-correction)
contributor_link: CONTRIBUTORS.md#how-mycelium-uses-feedback
project: canvas-drift-reconciliation
mechanism_or_status: shipped-v0.31.3-detection-layer
commits: ["74084fa"]
subclass: canvas-state-vs-reality-drift
---

# canvas-drift-reconciliation — when the framework's own bookkeeping drifted from reality

**Audience**: contributors and evaluators interested in how Mycelium caught and mechanized a recurring "canvas drifts from reality" failure in its own dogfood.
**Time to read**: 3 min.
**Last updated**: 2026-05-28.

## The friction

During a backlog-triage session, the maintainer asked a plain question the framework couldn't answer well: *"why weren't these updated when the agent got the data?"*

The answer was a multi-home-drift pattern. A fact about a human-task lives in two-or-more places — the task `status`, the evidence file it produces, and the contributor's consent registry — and only the home salient to the current task gets updated. The others drift silently:

- tasks left `in_progress` after their evidence was already logged;
- a contributor's consent reaching auto-memory but never the canonical attribution registry (stale two days);
- cold outreach left open because **abandonment is a non-event** — nothing triggers a status change when nothing happens.

The session-start hook that should have surfaced this counted raw `len(pending_tasks)` regardless of status, so it reported "16 pending" when only 4 were genuinely open. Noise, not signal.

## What changed (v0.31.3, detection layer)

- **session-start hook `CHECK 5`** now counts OPEN tasks by status (excludes `completed`/`abandoned`/`stalled`) and flags items with no activity in 14+ days. Dogfood: 16 entries → 4 open, all stale.
- **`/canvas-health` sub-check 8c** reconciles three divergences: status-vs-activity staleness (21d), evidence-exists-but-task-open, and consent-registry-vs-auto-memory mismatch.

This graduated instance 15 of the `documented-rule-diverges-from-enforcement` cluster — the recurrence of a sub-shape (`canvas-state-vs-reality-drift`) first flagged as a one-off on 2026-05-23.

## Deferred (honest)

The generating-side fix — `/log-evidence` auto-closing the source task and syncing the registry at evidence-write — is **not** in this release. This ships *detection*, not *auto-close*. Tracked in corrections.md 2026-05-28.

## The recursive part

`/framework-health` then found the same pattern in the framework's *own* cluster log: it had lagged the dogfood log by four days and didn't record this very graduation. The fact-home that exists to prevent drift had drifted. Reconciled in the same pass.

## Mechanism + status

**Status**: shipped-v0.31.3 detection layer (`74084fa`); validator passed 34/0/1. Close-the-loop deferred.
