# Contributors

Mycelium is shaped by the product development community. The following people contributed feedback, critique, and insight that directly influenced the framework.

## v0.9.0 — Computational Enforcement Layer (in planning)

**Simon Rohrer** — Identified Mycelium's core weakness: that inferential GATED controls are treated as advisory by the model. Introduced Birgitta Böckeler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html) vocabulary to the framework. Prompted the eval depth audit, the framework tensions documentation, and the honest gate renaming.

**Daniel Bentes** — Provided the architectural comparison between Mycelium and [BDSK (synaptiai/bdsk)](https://github.com/synaptiai/bdsk), clarifying the division of labor: Mycelium ensures you think about the right things before deciding; BDSK ensures the code respects what was decided. Directly shaped the v0.9.0 computational enforcement layer — scope hooks, state files, trace edges, schema validation.

## v0.11.0 — Product-Type-Agnostic Delivery

**Linda Maria Sneve** — Asked the question no one inside the project had considered: "How can I use Mycelium for non-software products — courses, ebooks, videos, AI tools?" This prompted the entire product_type dimension: 6 product types, 3 new delivery metrics canvases, conditional theory gates, product-type Definition of Done variants, non-software delivery guidance, and product-type-specific launch channels. Made Mycelium's largest structural expansion since v0.9.0.

## v0.15.0 — Scenarios as First-Class Primitive

**Drew Hoskins** — Staff PM at Temporal, author of *The Product-Minded Engineer*. Over two rounds of LinkedIn feedback (2026-04-14, 2026-04-17), Hoskins sharpened two key critiques: (1) L0-L2 scales make sense, but L3-L5 "starts to look like another way to think of the product lifecycle" — the upstream is differentiated, the downstream needs more. (2) Scenarios should be a first-class primitive, not an implicit byproduct of JTBD mapping. His SAP talk slides ("Attention to Users Is All You Need", April 2026) provided the specific structure: Persona + Means + Motive + Simulation. This directly led to `canvas/scenarios.yml` as a new canvas artifact, scenario wiring through the leaf lifecycle (phases 1, 5, 8, 10), and scenario extraction in `/user-interview`. Hoskins' "User Knowledge Repository" concept also validated Mycelium's canvas evidence system as architecturally aligned.

---

## How Mycelium Uses Feedback

Mycelium follows its own feedback loop discipline:

- **Immediate** (seconds): reflexion + corrections on tool failures
- **Incremental** (hours/days): phase learnings, DORA
- **Strategic** (weeks/months): BVSSH, Wardley refresh
- **Transformative** (quarterly): external feedback integration — this file

Feedback is credited here not to the framework author but to the people who genuinely reshaped the framework's direction.

---

## Theory Authors

The 40+ frameworks Mycelium integrates are credited in the *Theories & Frameworks Integrated* table in [README.md](README.md).

---

## Outreach History

### synaptiai (BDSK)

**Status**: Sent 2026-04-09. Issue: [synaptiai/bdsk#6](https://github.com/synaptiai/bdsk/issues/6)

**Context**: BDSK is architecturally complementary to Mycelium. Daniel Bentes's comparison (see above) showed that Mycelium ensures upstream thinking discipline while BDSK ensures downstream execution enforcement. v0.9.0 adopted several BDSK-inspired patterns (scope enforcement hook, state files, trace edges, change log). The outreach was a thank-you + a proposal to explore cross-pollination.

**What was proposed**:
1. Cross-reference in Mycelium's README pointing at BDSK as a complementary project
2. Shared document articulating the upstream-thinking / downstream-enforcement division of labor
3. Compare notes on Böckeler's computational vs inferential distinction

**Response**: No response as of 2026-04-17. Daniel's v0.4.0 commit (`a2f1592`, 2026-04-09) appears in the issue timeline but this is a false positive — the commit message references internal improvement proposal "#6" (validator dependency bundling), and GitHub auto-linked it to the GitHub issue #6. The 14 proposals are internal BDSK quality issues unrelated to the outreach.

**How to handle a response**:
- If synaptiai accepts (1): add a cross-reference in README.md under the "Related projects" section (create if needed) pointing at https://github.com/synaptiai/bdsk with a one-line summary of the complementarity
- If synaptiai is open to (2): the division-of-labor document is a good candidate for a shared GitHub repo or a post on martinfowler.com's harness engineering thread; log any follow-up discussion here
- If synaptiai declines or doesn't respond: no action needed. Mycelium's credit in CONTRIBUTORS.md and release notes stands regardless.

**Full sent text**: archived in the issue body at the link above. The draft that preceded it is preserved in git history of this file (pre-commit `[next hash]`).
