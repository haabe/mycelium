---
id: 2026-06-07-framework-health-temporal-independence
date: 2026-06-07
contributor: Håvard Bartnes (founder, dogfood-session catch)
contributor_link: CONTRIBUTORS.md
project: mycelium-roadmap (private; the dogfood project. The skill that found the gap is the skill the gap was in)
mechanism_or_status: shipped. v0.39.22 tightens `skills/framework-health/SKILL.md` Step 4e with an explicit temporal-independence rule applying symmetrically to 4b and 4d. One commit, four files, validator green at HEAD.
commits: [a5d2584, d24e9bf]
subclass: skill-finds-rule-gap-in-itself
---

# framework-health-temporal-independence: the audit caught the rule it was running by

**Audience**: contributors and operators who care about how the framework's self-assessment skills surface their own latent failure modes. Also: anyone who has ever run the same audit twice in a row and wondered why nothing new came out.
**Time to read**: 4 min.
**Last updated**: 2026-06-07.

## The trigger

A second `/mycelium:framework-health` run, same day as the morning one. The morning pass had already executed its five recommendations and shipped them. The PM re-run started not because anything had changed in the cycle data. It started because a downstream session was using the skill as a sanity check before a different kind of work.

The PM dashboard rolled through the cycle-derived dimensions, all unchanged. It rolled through cluster graduation-readiness, also unchanged. Then it hit Step 4e, the chat-UX axiom audit. The morning run had flagged six skills for Hick's Law or Von Restorff violations: canvas-update, ost-builder, ice-score, canvas-health, bvssh-check, dora-check. The 4e graduation rule reads "if the same skill is flagged across two assessments, promote to a mechanical `tests/bash` check."

The PM run re-flagged the same six skills, because nothing in those skills had changed. The mechanical reading of 4e said: graduate them. All six. Right now. Through `tests/bash`, into Check 37 enforcement, in a single same-day re-run with no intervening edit.

## Why this is not a one-off bug

The graduation rule was written with quarterly cadence in mind. The skill's own header says quarterly review or after twenty completed leaf cycles. The "two assessments" wording carried an implicit assumption: the two are separated by real observation time, real cycle motion, or at minimum a deliberate skill-template change between the runs. The on-demand re-run case was never explicit.

Same gap shape in 4b (cluster graduation-readiness, "criterion has been met for >30 days without graduation action") and 4d (docs health, "any forthcoming-doc Last updated >60 days"). The 4b version reads less brittle because it has a duration term. The 4d version is similar. But neither says explicitly: same-session re-flag does not count as independent confirmation. A skill that runs itself twice in a row would not violate the letter of those rules either. It just would not be doing what the rules were written for.

The recursion is the load-bearing part. The skill that named "graduation requires two assessments" was the skill being run twice in a row. The mechanical reading of its own rule would have produced six false-positive graduations on a single PM pass. Caught at narration time, not at write time. The dashboard prose was articulating *why 4e should not graduate today* and surfaced the missing rule in the same sentence.

## The cheap path, and why we did not take it

The cheap reading is: this is a known special case, the operator will not actually run framework-health twice in a row in production, move on. That reading has two problems. First, the operator *just did*. Second, framework-health is the skill the agent reaches for when something feels off about the framework's own behavior. The on-demand re-run is exactly the use case the skill ships for.

The slightly more expensive cheap path is: add a behavioral note to the skill docstring and call it done. Documentation-only graduation. The exact pattern this project's anti-pattern #7 graduation cycle named as insufficient (cycle-002, 2026-05-09, five same-day instances of the rule violation in the session the rule shipped). The fix has to be in the rule text the agent reads at Step 4e execution time, not in a side note.

The discipline path is: amend Step 4e itself, name 4b and 4d as siblings of the same gap, ship as a patch with the version-bump rules the framework already enforces. That is what v0.39.22 does.

## What shipped

One paragraph appended to Step 4e:

> **Temporal independence required.** "Flagged across two assessments" means two assessments separated by independent observation windows — a quarterly run, a cycle-count-trigger run, or an explicit re-audit after deliberate skill-template edits. Same-day re-runs with no intervening skill edit are mechanically the same flag, not two observations; record the prior run's flag-set as the baseline and check the next independent run against it. Without this rule, any agent running `/mycelium:framework-health` twice in a row would graduate the entire flagged set on the second run. The rule applies symmetrically to 4b (cluster graduation-readiness) and 4d (docs health) — re-flagging in the same session does not count as independent confirmation.

The version-bump discipline did its job. Check 30 caught `plugin.json` left behind on the first commit; the follow-up commit `d24e9bf` folded the bump plus `sync_derived` outputs. The token-replacer in `sync_derived` rewrote a literal "6 skills" in the CLAUDE.md version line to "50 skills", because the regex matches `<digit> skills` without context. That second catch lands as wording discipline in the follow-up commit message; if it recurs once more, the sync_derived guard moves from prose to mechanism.

## What this case taught the framework

Three lessons, each grounded in the artifact rather than the intent:

1. **Graduation rules need a temporal axis when they describe "two observations" or "across two assessments."** The 4e wording was written for quarterly cadence and read as mechanical for any cadence. The fix is to name the axis in the rule, not to assume the operator will infer it. Sister surfaces in the same skill (4b, 4d) got the same clarification at the same time, because the gap shape transfers cleanly across sub-steps that share the "across assessments" phrasing.
2. **Audit-time narration catches what audit-time mechanism does not.** The Step 4e graduation would have fired on the mechanical reading. The dashboard prose, written to explain the assessment to a human reader, articulated *why the graduation should not fire* and surfaced the missing rule in the same breath. The lesson the framework keeps re-learning: the human-facing narrative pass is itself an audit layer, not decoration around the mechanical layer.
3. **A skill finding a rule-gap in itself is a positive signal, not a failure.** The discomfort of "we just shipped this skill and it has a gap" is the discomfort of working in a discipline that surfaces its own friction. The alternative is a skill that does not catch its own gap, ships a six-skill false-positive graduation, and gets reverted in a panic two days later. The session that produced this case also produced the morning run that shipped five working recommendations. Same skill, same day, both outputs counted honestly.

## Mechanism + status

**Status**: shipped. v0.39.22 carries the temporal-independence rule across 4e/4b/4d. v0.39.23 adds this receipts case and rotates nothing on the README per the morning audit's "zero rotation pressure" finding. Cases stay in `docs/receipts/cases/` whether or not they are surfaced on the README; the rotation is the next maintainer decision, not this commit's.

The skill that found the rule it was running by is the skill the rule was in. The audit that named the gap was the audit it was already running. The catch lands as a paragraph the next operator reads at Step 4e execution time, and the next time someone runs `/mycelium:framework-health` twice in a row, that paragraph is the one that fires.

## Attribution note

Internal-only case. Sources are the live session that produced the catch and the upstream skill file. The session log lives in the operator's transcript; the resulting commits (`a5d2584`, `d24e9bf`, and the v0.39.23 commit that ships this case) carry the audit trail.
