---
id: 2026-05-16-opencode-phase1-runtime
date: 2026-05-16
contributor: Håvard Bartnes (founder)
contributor_link: CONTRIBUTORS.md
project: mycelium
mechanism_or_status: runtime-verification-overturned-prior-claims
commits: []
subclass: port-feasibility
related: [2026-05-16-opencode-port-feasibility]
---

# opencode-phase1-runtime — three runtime tests overturn the port-feasibility headline

**Audience**: evaluators following the opencode port arc; contributors weighing whether the "1–3 day adapter" estimate from the feasibility case still holds.
**Time to read**: 3 min.
**Last updated**: 2026-05-16.

## What was tested

Earlier the same day, a feasibility case ([2026-05-16-opencode-port-feasibility](2026-05-16-opencode-port-feasibility.md)) used desk research plus static + binary inspection of the installed opencode binary to estimate the adapter port at ~1–3 days. Three runtime unknowns were flagged as gated on a working API session: `tui.prompt.append` mutation reach, `tool.execute.after` failure signal, and edit-without-read enforcement.

A worktree-isolated subagent then ran the three tests headlessly against **opencode 1.15.1** with **local Ollama** as the provider (`llama3.1:8b` with a 32k-context Modelfile variant — the model substitution is irrelevant to the load-bearing signal in all three tests, which is whether the plugin's own log file records hook firings).

## What the runtime tests found

**Three of three runtime unknowns surfaced concrete gaps versus the desk + static estimate.**

1. **`tui.prompt.append` is silently inert in `opencode run`.** The hook never fires in headless mode; the `tui.*` namespace is TUI-scoped. The plugin loaded (`plugin.init` line written), but four invocations across two models produced zero `tui.prompt.append` log entries. Mycelium's Pre-Task Protocol (`G-P-pre`) cannot be hook-enforced in headless opencode runs. Workaround paths exist (system-prompt config block, parent-process prompt wrapping, `AGENTS.md` prose) but none of them is "opencode already does this."

2. **`tool.execute.after` is success-only.** A failed `read` on a nonexistent file fires `tool.execute.before` but never the `after` event. The error reaches the message stream and the model summarises it, but the hook stream sees only successes. Symmetric naming (`before` / `after`) did not imply symmetric coverage. Mycelium's reflexion port cannot piggyback on `tool.execute.after` for failure detection; it would need to reconcile orphaned `before` callIDs against `message.*` events, or parse message-part error fields. Sidecar mechanism, not drop-in.

3. **Read-before-Edit precondition is NOT runtime-enforced — only described to the model.** Edit applied cleanly in a fresh session with no prior read; `Version: 0.23.23 → 0.23.24` succeeded without warning. The binary-inspection finding from the feasibility case ("the precondition is enforced") was **wrong** — the string `"You must use your Read tool at least once in the conversation before editing"` is in the LLM-facing tool description, not the runtime code path. A model that ignores the instruction (4B/8B local models will, frequently) edits happily. This is a real parity gap versus Claude Code.

## Two consequential corrections

The case is logged as a receipt because Mycelium's verification discipline applies to *Mycelium's own conclusions*, not just to user-content claims. Two corrections to log:

- **Prior claim "binary inspection confirms Read-before-Edit enforcement" was wrong.** Binary strings are evidence about *what the agent is told*, not *what the runtime enforces*. The two layers diverge, and only the runtime layer matters for the framework's anti-pattern #8 protections. Pattern: don't infer enforcement from schema/description strings. Worth a `patterns.md` entry on its own.
- **Symmetric API names don't imply symmetric semantics.** `tool.execute.before` and `tool.execute.after` fire on completely different populations of tool calls (before: all calls; after: only successful ones). Read the docs *and* run the test; don't infer one from the name of the other.

## Effort revision

Feasibility case estimate: **~1–3 days** (thin adapter, opencode already does most of what we need).

Phase 1 evidence revises to: **~1–2 weeks**. Every workaround is custom Mycelium plugin code re-implementing a Claude Code primitive (prompt-injection emulator, tool-wrapper for failure signalling, Read-before-Edit guard plugin). The adapter is no longer "thin" — it's a fork-scale surface that reproduces three runtime behaviours the desk research assumed opencode provided natively.

## Confidence

`.claude/harness/decision-log.md` entry "Adopt two-lane harness path" was logged at confidence 0.55. Phase 1 evidence drops it to **0.32**. The decision is immutable per decision-log format; a new entry "Re-scope opencode adapter post-Phase-1" captures the recalibration.

## What this case does NOT prove

- That opencode is unsuitable as a Mycelium runtime — it's still feasible, just costlier.
- That the TUI mode would behave the same way — `tui.prompt.append` may well mutate the outbound prompt in interactive TUI sessions. Not tested in Phase 1 because Mycelium's adapter target is headless / orchestratable, not interactive.
- That an alternative event would work better — `session.created`, `agent.*`, and `message.*` events are documented but not exercised; one of them might provide the missing hooks.

## Snapshot

- opencode version: 1.15.1
- Provider: Ollama local, `llama3.1:8b` (32k-ctx Modelfile variant)
- Plugin hooks tested: `plugin.init` (works), `tui.prompt.append` (silent in headless), `tool.execute.before` (works), `tool.execute.after` (success-only)
- Test artefacts in subagent worktree at `.claude/worktrees/agent-af66540bb18a65261/test-sandbox/`; removed after this receipt was written.

Sources: subagent test report `test-sandbox/PHASE-1-RESULTS.md` (worktree, since cleaned); opencode docs at opencode.ai/docs/plugins.
