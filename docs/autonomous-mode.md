# Autonomous mode

**Audience**: operators running Mycelium headless or agent-to-agent; practitioners evaluating what the framework does without a human present.
**Time to read**: 5 min.
**Last updated**: 2026-06-12

Mycelium normally assumes a human is in the loop: skills ask questions, gates wait for approval, kills require confirmation. **Autonomous mode** is the declared exception — a headless or agent-to-agent run where the agent answers the framework's prompts itself, under a documented substitution discipline and a mechanical evidence guard.

This page is the operator's view. The full mechanism (substitution ladder, ledger format, per-skill behavior table) lives in the engine doc: `plugins/mycelium/engine/autonomous-mode.md`.

## The one rule that frames everything

**Autonomous mode is consent, not detection.** Running headless does NOT activate it. A headless session without a declaration stalls honestly at blocking points instead of improvising. And the reverse: a present human always outranks the flag — in an interactive session the agent asks you, even if the flag is set.

## How to declare it (three surfaces)

1. **Run prompt** (canonical for headless runs): the launching prompt states that autonomous mode is active, the persona to answer as (if any), the intended scope, and the ledger path. The prompt is the consent artifact.
2. **Environment variable**: `MYCELIUM_AUTONOMOUS_RUN=1` — the only surface a hook can read before the first state write.
3. **Project state**: `autonomous: true` in `.claude/diamonds/active.yml`.

## What it guarantees (and what it can't)

- **Substitution ledger** — every self-answered prompt is logged with its rung (documented default / persona substitution / honest hard-gate), tagged `source_class: internal_simulated`, and self-audited at end of run.
- **Human-only registry** — some decisions are never substitutable: confirming a diamond kill, approving where human approval is *required*, security/privacy/ethics tradeoffs. The run blocks honestly and leaves them for the next human session.
- **Evidence guard (mechanical)** — the `autonomous-evidence-guard` hook hard-blocks any write that introduces `source_class: external_human|external_data`, `validated: true`, or an `evidence_type` above `speculation` into canvas/diamond state during a declared run. An autonomous run cannot legitimately produce any of these — no human or world answered. The hook is a strict no-op in interactive sessions. As of v0.44.1 it is registered on all three runtime surfaces (Claude Code, Codex, Cursor).
- **Honestly bounded**: the guard covers the canonical write path. Bash-heredoc writes, in-conversation prose fabrication, and non-canonical paths are NOT mechanically blocked — the model-tier restriction below covers those.

## Model-tier restriction (hard)

The prose evidence-integrity boundary is **model-dependent**: held by Fable-5-tier models in testing (n=2), violated by Haiku 4.5 (n=1 — it fabricated interview results and did not know it had). **Do not run autonomous mode on a sub-Fable-5-tier model without a present human.** Sonnet-tier is unmeasured; treat it as unsupported until the scheduled test settles. Details: engine doc § known limitation + `docs/receipts/cases/2026-06-11-fable5-autonomous-run.md`.

## How a run ends

The end-of-run self-audit is part of the run: the ledger gets a summary (substitutions by rung, hard gates hit), and anything rung-(c)-blocked is surfaced for the next human session to decide. Reviewing the ledger is the human's first move after any autonomous run.

## See also

- `plugins/mycelium/engine/autonomous-mode.md` — full mechanism (the source of truth)
- [environment.md](environment.md) — all `MYCELIUM_*` variables in one place
- [ai-system-card.md](ai-system-card.md) §2/§4/§5 — the disclosure-level description
