# Contributors

Mycelium is shaped by the product development community. The people listed here surfaced friction that shaped the framework — the per-cycle detail of *what* shaped what lives in [docs/receipts/](docs/receipts/README.md).

This is the **PEOPLE view**. The receipts directory is the **WORK view** of the same facts.

## How to get listed

Surface friction the framework doesn't yet handle. Document it. If it shapes the framework — meaning it lands as a mechanism, an anti-pattern, a guardrail, a corrections.md entry, or a receipts case — you get a named entry on this page. Your contribution becomes a row in [docs/receipts/](docs/receipts/README.md).

The friction-to-mechanism trace is portable proof: point at it on a CV, on a portfolio, in a conversation. The framework's bias is to credit the named person who shaped a mechanism, not the maintainer who merged it.

The asymmetric deal is deliberate: low cost to find friction (surface it in an issue, a DM, a 30-min call), uncapped credit if it shapes the framework. See [docs/contributing/](docs/contributing/README.md) for process.

## v0.9.0 — Computational Enforcement Layer

**Simon Rohrer** — Identified Mycelium's core weakness: that inferential GATED controls are treated as advisory by the model. Introduced Birgitta Böckeler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html) vocabulary to the framework. Prompted the eval depth audit, the framework tensions documentation, and the honest gate renaming.

→ Receipts: tracked in framework history; case file forthcoming if the v0.9.0 cycle gets a dedicated write-up.

**Daniel Bentes** — Provided the architectural comparison between Mycelium and [BDSK (synaptiai/bdsk)](https://github.com/synaptiai/bdsk), clarifying the division of labor: Mycelium ensures you think about the right things before deciding; BDSK ensures the code respects what was decided. Directly shaped the v0.9.0 computational enforcement layer — scope hooks, state files, trace edges, schema validation.

→ Receipts: tracked in framework history; case file forthcoming.

## v0.11.0 — Product-Type-Agnostic Delivery

**Linda Maria Sneve** — Asked the question no one inside the project had considered: "How can I use Mycelium for non-software products — courses, ebooks, videos, AI tools?" This prompted the entire product_type dimension: 6 product types, 3 new delivery metrics canvases, conditional theory gates, product-type Definition of Done variants, non-software delivery guidance, and product-type-specific launch channels. Made Mycelium's largest structural expansion since v0.9.0.

→ Receipts: tracked in framework history; case file forthcoming.

## v0.15.0 — Scenarios as First-Class Primitive

**Drew Hoskins** — Staff PM at Temporal, author of *The Product-Minded Engineer*. Over two rounds of LinkedIn feedback (2026-04-14, 2026-04-17), Hoskins sharpened two key critiques: (1) L0-L2 scales make sense, but L3-L5 "starts to look like another way to think of the product lifecycle" — the upstream is differentiated, the downstream needs more. (2) Scenarios should be a first-class primitive, not an implicit byproduct of JTBD mapping. His SAP talk slides ("Attention to Users Is All You Need", April 2026) provided the specific structure: Persona + Means + Motive + Simulation. This directly led to `canvas/scenarios.yml` as a new canvas artifact, scenario wiring through the leaf lifecycle (phases 1, 5, 8, 10), and scenario extraction in `/user-interview`. Hoskins' "User Knowledge Repository" concept also validated Mycelium's canvas evidence system as architecturally aligned.

A second round on 2026-04-30, against an 8-hour take-home interview clock, surfaced seven more framework changes (Phase 0 path selector, constraint-first preflight, two anti-patterns, lightweight continuation mode).

→ Receipts: [drew-hoskins-takehome](docs/receipts/cases/2026-04-30-drew-hoskins-takehome.md).

## v0.20.0 — Plugin-Form Install Model

**Daniel Bentes** (second-cycle credit; see v0.9.0 above for first-cycle credit) — On 2026-05-08, on first install of Mycelium against a real project, Daniel surfaced the install-model architectural debt: the framework's top-level files (CLAUDE.md, README, CONTRIBUTORS, LICENSE) describe Mycelium-the-framework as if Mycelium IS the project, contaminating user project root and (worse) overwriting user files in brownfield installs. His finding directly drove the v0.20.0 architectural pivot: Mycelium repackaged as a Claude Code plugin (per Anthropic plugin spec), with all framework files living in plugin cache and the user's project root staying user-owned. Skill names became namespaced (`/mycelium:<name>`); a `/mycelium:setup` skill creates project-state directories on first run; AGENTS.md became the canonical cross-agent instructions surface. Same architectural-reviewer rigor that shaped v0.9.0's computational enforcement layer.

→ Receipts: [bentes-install-model](docs/receipts/cases/2026-05-08-bentes-install-model.md).

---

## v0.23.9 — First-run friction batch (cautious-learner observer)

**Frida** — On 2026-05-10, Frida ran Mycelium end-to-end on a real project of her own — a public-sector mobile app for next-of-kin in home care (GDPR, healthcare, AI-naive end users) — and returned the most thorough first-run observation the framework had received: she prepared before starting, read every prompt before approving, and wrote a structured recap the next day. Her log produced ten friction points; seven became opportunity-tree entries (opp-001–007) and four–five shipped in the v0.23.9 batch. Among them: a real bug she caught — the "Session ended. 0 corrections, 0 decisions logged" hook output leaking between every interview question, which she read (correctly) as an error; the request that the agent preserve originals as `revision_note` / `confidence_note` when updating a brief; the README time-budget fix; the L0-confidence formula display (showing the math, not just "we know it's wrong"); and the "Phase 6" internal-vocabulary leak. Two weeks later, as cohort-tester-1, her friction log named the framework's deepest unsolved surface verbatim — *"the terminology feels like it's written for people who already know the frameworks"* — and flagged that `/diamond-assess` reads as "evaluation" rather than "where were we" on re-entry. That naming is now driving the L0–L2 discoverability hardening.

→ Receipts: [frida-first-run](docs/receipts/cases/2026-05-10-frida-first-run.md).

---

## v0.23.28 — First non-developer user signal (book project)

**Edith-Mari Pedersen Bartnes** — On 2026-05-20, Edith-Mari became the first non-developer user to test Mycelium end-to-end. She ran `/mycelium:start` on her book project (content_publication product-type) and reached the assumption-test stage in ~10–15 minutes. The brief Mycelium produced from her input nearly brought her to tears — "captured and presented well, even though it was her own words." The assumption test left her feeling that the framework "really saw" her and what she was trying to achieve with her book. Five friction items surfaced in the same session; one ("You are here" wayfinding gap at the assumption-test → deep-dive-interview transition) graduated into a corrections.md entry extending the orientation mechanism to fire at every phase transition.

This is the first concrete validation that Mycelium's brief-synthesis-as-identity-mirror and assumption-test mechanisms work at the affective layer for non-developer users on non-software product types. Sample size 1; specific relationship (founder's wife); real signal but not statistical.

→ Receipts: [edith-mari-book-project](docs/receipts/cases/2026-05-20-edith-mari-book-project.md).

---

## v0.31.x — Cohort first-run friction (output density + post-build silence)

**Alex** (Juniors.dev cohort tester) — In May 2026, Alex ran Mycelium on his own project in what became the deepest single first-run session the framework had seen: `/start` → interview → feature selection → research prompts → diamond progression → a proof-of-concept build. His friction log drove three changes. (1) **Post-build silence**: after the POC built, the agent "just kind of stopped" without prompting next steps — he had to dig through the README to find `/diamond-assess` → shipped as the v0.31.1 post-build-silence nudge. (2) **"Brain fried from the gigantic walls of text"**: framework-wide output density → shipped as the v0.31.2 BLUF + Footnote convention. (3) **"Kept getting a little lost in the vocabulary"**: skill names assume product-thinking fluency → queued as L0–L2 discoverability hardening. He also flagged that the POC shipped "riddled with bugs" with no gate catching it — a candidate L4 code-quality scenario. His "is it just me, or would someone fluent find it easier?" framing was itself the signal: the framework wasn't teaching its own vocabulary in-flow.

Sessions 2–3 (late May 2026) surfaced the mid-build half of the story — friction that only appears once you're carrying a real project. The loudest: he stopped waiting for a visual canvas surface (a request from his first run) and **built his own** — a live-reloading dashboard for diamond state, opportunities, solutions, decision log, and a tooltip glossary, packaged as a drop-in skill. Alongside it: in-flight feature ideas get "absorbed in the chat" with no home (he asked for a backlog/exploration log); the feature-first drift guardrail fired only *after* he pushed back rather than proactively; challenged suggestions resolve to an invisible state (build now? defer?); the L0-vs-L2 scope line is unclear mid-build; and AI-generated canvas YAML broke with a duplicate key and content swapped between `opportunities.yml`/`solutions.yml`, caught only when his dashboard failed to parse it. All triaged as candidate bets, nothing shipped yet — the build decisions are deliberately left open.

→ Receipts: [alex-cohort-first-run](docs/receipts/cases/2026-05-26-alex-cohort-first-run.md), [alex-cohort-sessions-2-3](docs/receipts/cases/2026-05-30-alex-cohort-sessions-2-3.md).

---

## How Mycelium uses feedback

Mycelium follows its own feedback loop discipline:

- **Immediate** (seconds): reflexion + corrections on tool failures
- **Incremental** (hours/days): phase learnings, DORA
- **Strategic** (weeks/months): BVSSH, Wardley refresh
- **Transformative** (quarterly): external feedback integration — this file

Feedback is credited to the people who genuinely reshaped the framework's direction.

---

## Theory authors

The 30+ frameworks Mycelium integrates are credited in [docs/theories.md](docs/theories.md).

---

## Outreach archive

### synaptiai (BDSK)

**Status**: Sent 2026-04-09. Issue: [synaptiai/bdsk#6](https://github.com/synaptiai/bdsk/issues/6)

**Context**: BDSK is architecturally complementary to Mycelium. Daniel Bentes's comparison (see above) showed that Mycelium ensures upstream thinking discipline while BDSK ensures downstream execution enforcement. v0.9.0 adopted several BDSK-inspired patterns (scope enforcement hook, state files, trace edges, change log). The outreach was a thank-you + a proposal to explore cross-pollination.

**What was proposed**:
1. Cross-reference in Mycelium's README pointing at BDSK as a complementary project
2. Shared document articulating the upstream-thinking / downstream-enforcement division of labor
3. Compare notes on Böckeler's computational vs inferential distinction

**Response**: No response as of 2026-04-17. Daniel's v0.4.0 commit (`a2f1592`, 2026-04-09) appears in the issue timeline but this is a false positive — the commit message references internal improvement proposal "#6" (validator dependency bundling), and GitHub auto-linked it to the GitHub issue #6. The 14 proposals are internal BDSK quality issues unrelated to the outreach.

**How to handle a response**:
- If synaptiai accepts (1): add a cross-reference in README.md under a "Related projects" section (create if needed) pointing at https://github.com/synaptiai/bdsk with a one-line summary of the complementarity
- If synaptiai is open to (2): the division-of-labor document is a good candidate for a shared GitHub repo or a post on martinfowler.com's harness engineering thread; log any follow-up discussion here
- If synaptiai declines or doesn't respond: no action needed. Mycelium's credit in CONTRIBUTORS.md and release notes stands regardless.

**Full sent text**: archived in the issue body at the link above.
