# JIT Tooling Adoption Strategy: 4-Layer Composition

**Audience**: agents working inside Mycelium; framework contributors.
**Status**: Active as of v0.31.0 (2026-05-26).

## The Principle

The framework does **not** know the user's language, purpose, dev-loop preferences, machine constraints, or pre-existing toolchain opinions. Therefore the framework **never auto-installs tools, never selects rulesets on the user's behalf, never prescribes a stack-default**. All adoption is per-tool, per-consent. See founder rationale in auto-memory `feedback-jit-nudge-not-push` (2026-05-26).

The framework's job is to make the right tool visible at the right moment, then ask.

## Why Not a Simpler Approach

A deep study (2026-05-26) compared 10 approaches against industry evidence and Mycelium's constraints. Key rejections:

- **PAVED-ROAD / STARTER-PACK / CONVENTION-OVER-CONFIG**: founder-veto — Mycelium isn't a platform owner; can't authoritatively pick toolchains.
- **PEER-LEARNING / social proof**: no telemetry — any "78% of similar projects use X" numbers would be fabricated (violates anti-pattern #7).
- **OFFER-MENU alone**: 1-shot decision = likely "no thanks / later" = permanent zero-state. Same outcome as today's gap.
- **NUDGE-AT-FAILURE alone**: circular — needs the bug to surface via some other mechanism first.
- **WIZARD as primary**: documented abandonment risk; agent-UI conversation already approximates a wizard without the framing.

The composition is needed because each single approach has a failure mode the others patch.

## The 4 Layers

### Layer 1 — OFFER-MENU at bootstrap (with PROGRESSIVE ordering)

**Where**: `delivery-bootstrap` SKILL.md Step 3a.
**Trigger**: project bootstrap; stack detected.
**Action**: present the stack-matched menu from `security-scanning.md`, ordered smallest-friction first (secrets → linter → SAST → dep audit → container scan). Ask once, per tool.
**Record**: declined offers logged to `active-stack.yml#tooling_offers_declined` so Layer 2 can re-surface.

### Layer 2 — RISK-TRIGGERED re-offer

**Where**: `delivery-bootstrap` SKILL.md Step 3b; also fires whenever a risk shape is later detected.
**Trigger**: code matches a risk shape (AUTH, AI, PII/data, public endpoint) AND the relevant tool was declined or never offered.
**Action**: re-surface the relevant subset with the risk as citation. *"AUTH shape detected at app.py:42 → SAST recommended."*
**Evidence**: contextual nudges at decision moments produce ~8× higher detection vs no-nudge baseline (Less is More, arxiv 2202.04586 — *consistency_only*, single experimental study).

### Layer 3 — NUDGE-AT-FAILURE

**Where**: `security-review`, `reflexion`, `threat-model` SKILL.md.
**Trigger**: a finding/failure surfaces that a standard tool would have caught automatically.
**Action**: append single-line nudge *"This class of bug is what `{tool}` catches automatically — want help wiring it up now?"*. Converts a demonstrated-value moment into low-friction install consent.

### Layer 4 — PR-TIME gap flag

**Where**: `definition-of-done` SKILL.md Security checklist.
**Trigger**: diamond closes; validation suite lacks SAST equivalent for the detected stack.
**Action**: surface as a visible (non-blocking) finding. *"Closing this diamond without SAST coverage. Best-practice menu was offered at bootstrap; gap is on the record."*
**Not blocking**: respects founder-principle that the user owns the choice. Visibility ≠ enforcement.

## Risk-Shape Detection (Layer 2 supporting data)

| Shape | Patterns to match | Re-offer subset | SAST coverage |
|---|---|---|---|
| AUTH | `/login`, `/auth`, `/register`, `password`, `session`, `token`, `jwt`, `oauth`, trust-bearing headers (`x-user-id`) | SAST + `/mycelium:threat-model` + `/mycelium:security-review` | **Blind spot** — identity-trust design isn't SAST-catchable; route to security-review |
| AI | imports from `ai_components` categories (detector.md Step 1c) | `/mycelium:xai-check` | n/a (XAI-specific) |
| PII / data | `email`, `ssn`, `phone`, `address`, `payment`, `card`, fields matching PII | secrets scanner + `/mycelium:privacy-check` | Partial — secrets scanners catch literals; field-level PII handling isn't tool-catchable |
| Public endpoint | routes without auth middleware | SAST + DAST | **Blind spot** — "no authz check" is intent-level, not tool-catchable |
| File upload | `upload`, `multipart`, `FormFile`, `ServeFile`, `ServeContent`, `Content-Disposition`, FS write from request | SAST + DAST + `/mycelium:threat-model` (MIME-allowlist, filename sanitization, size cap, overwrite policy) | Partial — gosec/semgrep catch path-traversal patterns; MIME-confusion, stored-XSS, public-list disclosure aren't tool-catchable |

Patterns are starting points, not exhaustive. Junior-friendly: pattern-grep is good enough at the bootstrap surface; deeper detection lives in `/mycelium:threat-model`.

## SAST Coverage Honesty

When a risk shape fires, Layer 2 re-offers SAST tooling — but the agent must label which bug classes the recommended SAST **cannot catch**. Identity-trust design, authorization-presence checks, MIME confusion, business-logic flaws, and ownership checks are design-level concerns invisible to pattern-matching SAST. For these, the framework routes to `/mycelium:security-review` regardless of whether SAST consent was given. Failing to surface this distinction risks the user thinking "I ran SAST, I'm covered" — a false-comfort outcome worse than knowing the gap exists.

This was added 2026-05-26 after cycle 2 testing surfaced 0/5 bugs caught by eslint-plugin-security on a Node project where every bug was design-level.

## What This Does NOT Do

- Does not run `pip install` / `npm install` / `cargo install` on behalf of the user.
- Does not select rulesets (`--select S` for ruff, etc.) — explicit user choice.
- Does not ship a `.semgrep.yml` users didn't ask for.
- Does not block diamond progression on absence of tools the user declined.
- Does not invent peer-usage statistics ("X% of similar projects use Y").

## Honesty Caveats

- The 8× detection finding is from a single experimental study (small N, lab conditions). *consistency_only* per anti-pattern #7 — strong signal, not settled.
- The 4-layer composition has not been validated in production with real users — the design is theory-backed (deep study 2026-05-26) but the *adoption rate* claim is *unverified*.
- The "PROGRESSIVE smallest-first ordering" claim leans on pre-commit-adoption practitioner literature (multiple consistent blog reports, no controlled studies surfaced). *consistency_only*.

## Related Files

- `plugins/mycelium/jit-tooling/detector.md` — stack detection (input to Layer 1)
- `plugins/mycelium/jit-tooling/security-scanning.md` — tool menu per stack (Layer 1 + Layer 3 data)
- `plugins/mycelium/skills/delivery-bootstrap/SKILL.md` — Layer 1 + Layer 2 entry point
- `plugins/mycelium/skills/security-review/SKILL.md` — Layer 3
- `plugins/mycelium/skills/reflexion/SKILL.md` — Layer 3
- `plugins/mycelium/skills/definition-of-done/SKILL.md` — Layer 4
