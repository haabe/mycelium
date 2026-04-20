# Mycelium Guardrails — Core (Always Loaded)

Universal constraints that apply regardless of phase or scale. These are the minimum instruction set for every task.

## Enforcement Levels

- **BLOCK**: Mechanically prevented via hook. Cannot proceed.
- **REVIEW**: Gates diamond progression. Agent must satisfy before `/diamond-progress` advances.
- **NUDGE**: Advised, not blocking. Logged for awareness.

Only BLOCK is computationally deterministic. REVIEW and NUDGE are inferentially enforced (Böckeler).

## Security (universal)

**G-S1: Never store, log, or transmit user secrets in plaintext** `BLOCK` `safety`
Credentials, tokens, API keys, passwords must be encrypted at rest and in transit. Never commit them to version control. Never include them in error messages or logs.
*Source: OWASP Secure by Design*

## Process (universal)

**G-P1: Never progress a diamond without updating the canvas** `REVIEW` `quality`
Every diamond transition must be reflected in the appropriate canvas files. The canvas is the single source of truth -- if it's not in the canvas, it didn't happen.

**G-P4: Always log decisions in the decision log** `REVIEW` `quality`
No significant decision (diamond transition, solution selection, architecture choice, scope change) happens without a logged entry in `.claude/harness/decision-log.md`.

**G-P5: Always read corrections.md before implementation tasks** `BLOCK` `quality`
Past mistakes are expensive lessons. Reading them costs seconds. Not reading them costs hours.
*Source: Mycelium self-learning, n-trax reflexion pattern*

**G-P3: Always cite which theory informed a decision** `NUDGE` `quality`
Every significant decision in the decision log must reference the specific theory/framework that guided it.

**G-P7: Close the loop after every task batch** `REVIEW` `quality`
After completing any batch of changes, before reporting done: (1) verify cross-repo consistency if changes span repos, (2) log corrections for any mistakes made, (3) log patterns for anything reusable, (4) update corrections.md TL;DR if new entries added. If the user has to ask whether this happened, the guardrail already failed.
*Source: Hoskins Ch4 (friction logging), Argyris (double-loop learning)*
