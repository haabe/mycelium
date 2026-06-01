---
id: 2026-06-01-architecture-discovery-narrowed
date: 2026-06-01
contributor: Håvard Bartnes (founder self-dogfood)
contributor_link: CONTRIBUTORS.md
project: mycelium-roadmap (private — generic-framed receipt; raw artifacts and the practitioner identity stay private until consent)
mechanism_or_status: investigated — hypothesized gap captured as a failing-first scenario, then dogfooded; the gap is narrower than its first framing. A light-touch solution candidate is sketched in the private OST. NOTHING shipped to the framework. A leaf still requires a second independent external ask.
commits: []
subclass: self-dogfood
---

# architecture-discovery-narrowed — dogfooding a hypothesized gap

**Audience**: contributors and evaluators interested in how Mycelium handles a *hypothesized* gap before it earns a build — and what changes when you run the gap against the framework instead of writing about it.
**Time to read**: 5 min.
**Last updated**: 2026-06-01.

## The trigger

An external practitioner — a backend engineer working on .NET / ML production systems — commented on a public post from the founder. The comment validated the existing thesis ("forcing agents to do discovery before building is the right problem to solve") and asked a real question: could Mycelium's evidence-gate be extended from *product* discovery to *technical* discovery — architecture, API contracts, data models — where the practitioner had observed agents "confidently guessing and getting it wrong"?

Identity, employer, and named clients live in the private roadmap canvas. Per the framework's attribution discipline (Lars Jenssen pattern), nothing in this case names the practitioner, their company, or any client; the receipt is about what we *did* with the signal, not who sent it.

N=1, soft trial intent only ("next time we do product work"). A positioning + demand signal — not behavior validation.

## The temptation, and why we did not yield

The obvious move on receiving a thoughtful adjacency request is to **build for it**. A "technical-discovery scale" — L0' / L1' for architecture — would be a perfectly seductive design exercise. Two things held the line:

1. **N=1, no tool-run**. The opportunity (`opp-007` in the private roadmap) was logged with confidence 0.25 and an explicit graduation rule: a second independent external ask must arrive before any leaf earns a build. Dogfood is internal evidence; it does not satisfy that rule. The graduation gate stays closed.
2. **Lane risk**. Extending the evidence-gate into technical decisions could pull Mycelium out of the upstream-discovery lane the strategic frame defends. Whether the gate-mechanism *transfers* to technical decisions without distorting the lane was genuinely unknown.

So instead of designing the leaf, we built the **test** that would tell us whether the gap is what it looks like.

## The instrument — a failing-first scenario

Mycelium's auto-dogfood harness supports a `_failing_first/` directory: scenarios that are *expected to fail* against the current framework, tagged with the opportunity they prove. The scenario for this gap (`sw-tech-discovery-architecture-guess.yml`) plants a specific failure: a confident solo backend engineer building a reconciliation service against an unread third-party API and an unvalidated 1:1 data-model assumption. Persona, pre-scripted answers, journey of skills, and seven success criteria — five product-discovery sanity-floor checks (should pass today), two technical-discovery enforcement checks (expected to fail, *proving* the gap).

The scenario *is* the design memo. Its `expected_to_fail: true` records the hypothesis; its `success_criteria` records what would falsify or confirm it. The cost is one YAML file. The value is that the gap becomes mechanically inspectable.

(Hoskins: predict the failure before you read the disk. The pre-commitment is what makes the result honest.)

## The dogfood

The scenario had never been run. The orchestrator's default model overrides expect Claude credits the founder does not currently have, and the free-model harness (opencode + OpenRouter) is still being measured for whether it executes tool calls in scenarios or narrates them. So we ran it directly via a Claude Code subagent: a fresh workdir, the plugin installed, the persona's pitch + answers given to the subagent verbatim, and an instruction to execute the journey skills and let the framework do its work.

The subagent ran for ~22 turns through `/mycelium:interview` × 2, `/mycelium:diamond-assess`, `/mycelium:diamond-progress`, and a closing `/mycelium:diamond-assess`. The author then read the workdir disk state directly — `canvas/*.yml`, `diamonds/active.yml`, `harness/decision-log.md` — and grepped for the literal terms the success criteria named. *Disk-verified*, not subagent-reported.

## What surfaced — 5/7 pass, 2/7 partial

**The blocking behavior is correct.** `/mycelium:diamond-progress` refused to advance the L0 diamond. Confidence 0.35 vs effective threshold 0.72. Failing gates: Evidence (zero external_human signals) and Bias (availability heuristic on a two-year-old API memory; confirmation bias on a 1:1 mapping assumption that directly contradicts the stated drift problem). Anti-pattern #7 (Consistency-as-Evidence) cited explicitly on "it was like that two years ago." The unverified API contract and the unvalidated 1:1 mapping were tagged in canvas constraints with `validated: false`. The persona's "yes, let's move, I want to start building" was logged as a confirmation-bias signal, not as override.

This was a real surprise. The first framing of the gap had assumed *no gate fires*. In fact the existing gates do the work.

**The three things that are still missing** — narrower than the original framing, but real:

1. **Vocabulary**. The literal phrase "technical discovery" appeared 0× in the decision-log output across four entries. The framework has the right blocking behavior but no name for the kind of evidence it just rejected. A reader sees an Evidence-gap, not a technical-shape gap.
2. **Routing**. The recommended next move included `/mycelium:user-interview` — half-wrong here. You do not interview a finance-ops person to learn a third-party API contract. The right surface is "read the docs / pull a real payload," and the framework does not currently offer it.
3. **State drift**. `theory_gates_status` in `active.yml` stayed `pending` while the decision-log records FAIL for two gates. The log is the truth; the gate-status field is stale. New instance of the `documented-rule-diverges-from-enforcement` cluster — not the topic of this receipt, but logged so the next sweep catches it.

The leaf shape that follows from this is not "a dedicated technical-discovery scale." It is a vocabulary + routing nudge on the gates that already fire. A *much* smaller commitment.

## What this case taught the framework

The receipt is less about the architecture-discovery question and more about the **discipline that protected the framework from over-building a hypothesized adjacency**. Two moves did the work:

1. **Logging the opportunity with a graduation rule it could not satisfy yet.** Confidence 0.25, "second independent external ask required for any leaf." The dogfood result did not — and still does not — graduate this. Internal evidence stayed labeled as such.
2. **Capturing the hypothesis as a failing-first scenario before reaching for a fix.** The scenario is mechanically inspectable; the disk-verified result is interpretable; the leaf shape is now grounded in observed behavior rather than imagined behavior.

The combination shrank the candidate solution from "a new diamond scale" to "a vocabulary + routing branch on existing gates." If the second external ask arrives, the cost of acting will be small. If it does not, nothing was built.

Attribution honesty: every causal claim above ("the gap is narrower than feared", "the leaf shape collapses to a nudge") is grounded in disk-verified behavior from a single subagent run. N=1, no external behavior. The narrowed leaf-shape candidate (`sol-007a` in the private OST) is itself a bet — its discard criterion is that *re-running the failing-first scenario after the nudge ships still routes the user toward `/mycelium:user-interview` for an API-contract gap*. If that happens, the nudge is insufficient and the leaf was wrong.

## Mechanism + status

**Status**: investigated. Nothing shipped to the framework. The private roadmap carries the dogfood result on `opp-007` (held at confidence 0.25), a sketched candidate solution `sol-007a` (vocabulary + routing nudge), and a decision-log entry recording the alternatives considered. Any actual leaf is gated on the documented external-second-ask criterion. The state-drift surface finding (active.yml vs decision-log) is parked for the next `documented-rule-diverges-from-enforcement` cluster instance sweep.

## Attribution note

External practitioner: identity, employer, and named clients live in the private roadmap (`opp-007` and the 2026-06-01 decision-log entry). Per the Lars Jenssen pattern, public framework surfaces stay generic until explicit consent. This receipts case is the generic surface. Nothing here identifies the inbound contact.
