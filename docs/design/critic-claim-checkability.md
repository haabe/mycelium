# Design: make a plan's factual claims checkable, not retrievable

**Status:** PROPOSED — not built. No skill, hook, or check implements this yet.
**Last updated:** 2026-08-07.
**Origin:** roadmap dogfood — an external practitioner reported that shared-context
critics rationalise instead of critiquing; a five-run tier-stratified test was built to
borrow his fix, failed to reproduce his failure at the top tier, reproduced it decisively
at the tiers that matter, and landed on a different mechanism than the one it set out to copy.

> Authoring home: upstream (this repo). Evidence trail lives in the roadmap repo:
> `.claude/evals/assumption-tests/2026-08-07-same-context-critic-advocacy.md` (five frozen
> predictions, all results below them, none revised after the fact),
> `landscape.yml#comp-081`, `human-tasks.yml#ht-065`, `ht-067`.

---

## 1. The problem, as it was first framed — and why that framing was wrong

Brooks Talley (`brookstalley/prawduct`, the closest structural analog to Mycelium found to
date) reported, unprompted, in email 2026-08-06:

> *"Early versions that had access to the builder's reasoning, or even the build plan,
> tended to create justifications for design mistakes. Or the build plan would have bad
> reasoning like 'the library we use doesn't support PNG' and the same-context critic would
> accept that at face value."*

His fix is a Critic skill running with `context: fork` plus `allowed-tools` restrictions that
structurally prevent it from running tests or builds — it sees code and specs but never the
builder's reasoning — plus a session hook that blocks completion if code changed with no
independent review.

Mycelium's exposure was real. Verified 2026-08-07 by recursive grep over
`plugins/mycelium/skills/` and `plugins/mycelium/engine/` for `context: fork`, `context:fork`,
`blind subagent`, `blind_subagent`: **zero hits**. `/reflexion` Step 3 is titled "Self-Critique"
and runs in the builder's own context; `/devils-advocate` also runs in-context. The only
subagent usage in that scope is `framework-health`, `theory-fidelity` and `fan-out`, none
inside the build loop.

**The borrow was the obvious move. It does not survive the evidence.**

## 2. What the dogfood evidence settles

Five runs, 33 agents, three model tiers, two critic configurations. Full method and the five
frozen predictions in the roadmap eval doc.

### 2.1 The headline: claim TYPE predicts auditing — not context, not authorship

A build plan carried a **false but checkable** factual premise ("PyYAML has no common base
exception class across versions", when `yaml.YAMLError` is the documented base) alongside a
genuine defect it was used to justify.

| Claim type | What auditing it requires | opus-5 | sonnet | haiku |
|---|---|---|---|---|
| **External factual** — *does `yaml.YAMLError` exist?* | retrieval from world knowledge | **3/3 audited** | **0/3** | **0/3** |
| **Artifact-verifiable** — *is the "unreachable" fallback actually reachable?* | reasoning over material in hand | 3/3 | **3/3** | partial |
| **Own prior claim** — *is my own "Never raises" docstring true?* | reasoning over material in hand | 3/3 | **2/3** | not run |

**Six consecutive sonnet and haiku runs accepted the false external fact** while competently
attacking the same code on other grounds. The same models audited artifact-verifiable claims
well at every tier, including claims they had written themselves minutes earlier.

**Detection never dropped.** The defect the false premise defended was flagged 3/3 at *every*
tier. A found/not-found metric scores all three tiers identically and sees none of this. What
degrades is whether the critic checks the *reason*.

### 2.2 A second effect, at haiku only: severity discounting

A hardcoded credential was rated **HIGH by 3/3 blind reviewers** and **MEDIUM by 2/3 informed
reviewers**, each quoting the plan's reassurance while downgrading — *"even if marked as
'unreachable in production'"*. The defect was never missed; its severity was discounted by the
presence of a justification. Invisible to any count-based metric.

### 2.3 The rationale is genuinely useful input — non-monotonically

Findings that appeared **only** when the critic could see the plan: the cross-decision
interaction (swallowing parse errors makes the "unreachable" fallback reachable), the
load-bearing claim named and refuted, justification-to-artifact mismatch (plan cites tests that
do not exist), and design-intent-dependent defects. The cross-decision finding came from **3/3
sonnet** informed runs but only **1/3 opus**. The plan helps and misleads at the same tier, on
different axes.

### 2.4 `/reflexion` Step 3 is not broken, but it is not sufficient

At sonnet, self-critique found the top defect **2/3** where blind reviewers of the identical
artifact found it **3/3**. One self-review endorsed its own tradeoff — *"that's the right
degrade behavior"* — where the blind arm pushed harder.

## 3. What is REJECTED, and why

**Forking the critic's context — REJECTED.** No run supports it. The blind arms did not catch
the false premise either; they simply never saw it, so "premise refuted" is undefined for them
rather than zero. Forking would discard the §2.3 findings that only exist when the plan is
visible. **Scope of this rejection:** the test varies plan-presence together with
premise-exposure, so **no arm isolates the effect of hiding the plan**. This rejects forking as
*unsupported by our evidence*, not as *proven harmful*.

**Simply feeding rationale to the critic — REJECTED.** This was the conclusion when the test
had only been run at opus, and it fails at sonnet and haiku, where more rationale means more
unchallenged assertions.

**Brooks's tool restriction — NOT REJECTED, NOT TESTED.** A critic barred from running tests
must reason from the artifact, which is exactly the claim type that survives down-tier. This
investigation makes it *more* plausible, not less. It remains a live borrow candidate.

## 4. The proposed mechanism

**Convert external-factual claims into artifact-verifiable ones.** The failing claim type is
the one requiring retrieval. The succeeding type is the one checkable from material in hand. So
do not ask the critic to retrieve — oblige the plan to carry what makes checking possible.

**Shape (design only, not a spec):**

1. **A load-bearing factual assertion in a plan carries a citation or a verification step.**
   "PyYAML has no common base class" is load-bearing when a decision rests on it. It ships with
   a source, a command that demonstrates it, or an explicit `UNVERIFIED` tag.
2. **The critic checks the citation rather than the fact.** Checking that a cited source says
   what the plan claims is artifact-verifiable — the claim type that held 3/3 at sonnet.
3. **`UNVERIFIED` is legal and visible.** The goal is not to ban unverified claims; it is to
   stop them passing as established. An untagged bare factual assertion supporting a decision
   is the defect.
4. **Tier-appropriate by construction.** This works *because* it needs no retrieval, so it
   should degrade gracefully to haiku. That must be tested, not assumed.

**Why this and not a nudge:** per the roadmap's `make-claims-real-not-nudge` discipline, a
theory-fidelity gap gets a mechanism with teeth. An advisory "consider verifying claims" is
prose, and prose is what the six failing runs were already ignoring.

## 5. What must be true before this is built

- [ ] **Re-run at haiku for round 2** (self-critique). Not run.
- [ ] **A third arm**: plan present, false premises removed. Without it, forking is rejected on
      absence of support rather than on evidence of harm.
- [ ] **A false premise about a proprietary/internal system**, unverifiable from training data.
      The tested premise was checkable from world knowledge, which is the *easy* case for the
      tier that passed.
- [ ] **Test the mechanism itself at sonnet and haiku before shipping**, not at opus.

## 6. The meta-lesson, which outlives this design

**Validate at sonnet and haiku, never at opus alone.** This repo's dogfood convention already
said so — `.claude/auto-dogfood/schema.md` pins `mycelium_agent: sonnet`, `user_simulator: haiku`,
and a prior correction records that *"auto-dogfood validity is model-stratified"* and that
*"sonnet vs opus diverge meaningfully on canvas-discipline-internalization."*

The investigation that produced this design **broke that convention silently** by passing no
model parameter and inheriting opus, then wrote a limitations section arguing the uncertainty
was harmless. It was not: the run measured the one tier where the failure has been outgrown, and
reached the opposite conclusion. It was caught by the founder, not by any check.

**Three pre-registered predictions failed, all in the same direction.** Each assumed the failure
would be motivational — ego, advocacy, defending one's own reasoning. The real failure is
epistemic and tier-dependent: models do not check facts they would have to retrieve.
