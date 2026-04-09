# Contributors

Mycelium is shaped by the product development community. The following people contributed feedback, critique, and insight that directly influenced the framework.

## v0.9.0 — Computational Enforcement Layer (in planning)

**Simon Rohrer** — Identified Mycelium's core weakness: that inferential GATED controls are treated as advisory by the model. Introduced Birgitta Böckeler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html) vocabulary to the framework. Prompted the eval depth audit, the framework tensions documentation, and the honest gate renaming.

**Daniel Bentes** — Provided the architectural comparison between Mycelium and [BDSK (synaptiai/bdsk)](https://github.com/synaptiai/bdsk), clarifying the division of labor: Mycelium ensures you think about the right things before deciding; BDSK ensures the code respects what was decided. Directly shaped the v0.9.0 computational enforcement layer — scope hooks, state files, trace edges, schema validation.

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

## Planned Outreach

### synaptiai (BDSK)

**Status**: Draft ready. Not yet sent.

**Context**: BDSK is architecturally complementary to Mycelium. Daniel Bentes's comparison (see above) showed that Mycelium ensures upstream thinking discipline while BDSK ensures downstream execution enforcement. v0.9.0 adopted several BDSK-inspired patterns (scope enforcement hook, state files, trace edges, change log). It would be valuable to reach out for cross-pollination.

**Draft message** (GitHub issue on synaptiai/bdsk, or email if a contact is available):

> Subject: BDSK + Mycelium: complementary harness engineering approaches
>
> Hi,
>
> I'm the author of [Mycelium](https://github.com/haabe/mycelium), a theory-guided product development harness for Claude Code. A contributor (Daniel Bentes) recently pointed me at BDSK in the context of comparing harness engineering approaches, and I spent several hours reading your architecture in depth.
>
> The framing that emerged from the comparison: **Mycelium ensures you think about the right things before deciding; BDSK ensures the code respects what was decided.** Mycelium is strong upstream (40+ product development theories, evidence-gated discovery, bias checks, corrections memory, dogfood reports) and was weak downstream (mostly inferential enforcement). BDSK is the opposite — strong computational enforcement via scope hooks, trace edges, and the 8-phase validator, but fewer upstream thinking tools.
>
> Mycelium v0.9.0 adopted several BDSK-inspired patterns explicitly:
> - PreToolUse scope enforcement hook (modeled on `check-scope.sh`)
> - `.claude/state/` runtime state directory with JSON files
> - JSONL change log audit trail
> - JSON schemas for canvas files with DAG cycle detection via Kahn's algorithm
> - Trace edges (`upstream`/`downstream`) with 10 canonical edge types on high-stakes canvas entries
> - Fail-closed hook policy
>
> We credited BDSK and your project in our CONTRIBUTORS.md and v0.9.0 release notes.
>
> Daniel also suggested five things BDSK could adopt from Mycelium — an anti-pattern catalog as `codegen_policy`, evidence-based gating with `evidence_refs`, bias checks as a pre-approval step, self-learning `corrections/` memory, and multi-speed feedback loops. I'm not suggesting you should adopt any of them — just surfacing them in case they're useful.
>
> If you're open to it, I'd love to:
> 1. Add a cross-reference in Mycelium's README pointing at BDSK as a complementary project
> 2. Discuss whether there's value in a shared document articulating the upstream/downstream division of labor
> 3. Compare notes on the Böckeler "computational vs inferential" distinction, which seems to be the common theoretical ground
>
> Either way, thank you for the architecture — it solved a problem I'd been wrestling with, and the comparison prompted v0.9.0's entire direction.
>
> Best,
> [Your name]

**How to send**: Open an issue at https://github.com/synaptiai/bdsk/issues, copy the draft above, and personalize the signature. Don't delete this draft from CONTRIBUTORS.md after sending — mark the status as "sent" with the date and link to the issue, so future versions of Mycelium can see the outreach history.

**When to send**: After v0.10.0 is tagged and pushed. The outreach has more weight when backed by a released version that actually implements BDSK-inspired patterns.
