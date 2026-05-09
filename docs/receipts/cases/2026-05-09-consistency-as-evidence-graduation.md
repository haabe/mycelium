---
id: 2026-05-09-consistency-as-evidence-graduation
date: 2026-05-09
contributor: Håvard Bartnes (founder dogfood)
contributor_link: CONTRIBUTORS.md
project: mycelium-self-discipline
mechanism_or_status: graduated
commits: ["TBD"]
subclass: anti-pattern-graduation
---

# consistency-as-evidence-graduation — three instances become a named failure mode

**Audience**: contributors curious about how Mycelium graduates recurring agent failures into named anti-patterns; evaluators wanting to see the receipts pipeline working.
**Time to read**: 4 min.
**Last updated**: 2026-05-09.

## The recurring failure

Three times in five weeks, the agent constructed a structural conclusion (a plan, a framing reconciliation, a causal chain) by treating *consistency-with-hypothesis* as *evidence-for-hypothesis*, without isolating attribution. Each time, the user caught it post-publication.

| Date | Surface | What happened |
|---|---|---|
| 2026-04-30 | Hoskins takehome session | Agent built 20h delivery plan from partial discovery without checking the 8h budget. Discovery completion was *consistent with* "ready to plan delivery" but didn't *evidence* it. |
| 2026-05-03 | Q4 baseline framing audit | Agent anchored on `landscape.yml#gameplay`'s "users burned by building the wrong thing" framing and proposed sharpening README to match. Internal-doc consistency was treated as evidence the framing was correct, without testing against the full evidence base (Juniors.dev cohort, Cutler 2026-05-03 identity-trap). Sharpening would have shrunk the segment. |
| 2026-05-09 | Verbosity-adaptation memo | Agent built "verbose discipline → session-token burn → Pro-tier rate-limit → adoption ceiling" chain anchored on Hoskins (Mycelium-attributable) and extended to Frida (consistency-only — her rate-limit reports may not be Mycelium-driven). Treated cohort-level consistency as evidence for a structural exclusion claim. |

## Why three instances forced graduation

Mycelium's recurring-pattern rule (per `corrections.md` line 11, citing the upgrade.sh hardcoded-list precedent: *"Don't wait for incident #3"*) was already met at instance 3. The 2026-05-09 user intervention made the meta-pattern explicit: *"You need to log the conclusion jumping to the self learning. This is not the first time!"* The framework's existing graduation pipeline (G-V12, Check 16, consistency-check-spec.md) has graduated similar recurring failures before — the threshold and the mechanism shape were both established.

Notable: the agent often *knew the rule* at each instance — the framework's discovery and confidence anti-patterns explicitly warn against extrapolation, single-source validation, and anchored confidence. The failure was in *self-application*: the agent applied the rule to user behavior but didn't run it on its own analysis pre-publish. That's the meta-pattern the graduation closes.

## What graduated

**Anti-pattern #7 in `harness/anti-patterns.md`** — *Consistency-as-Evidence*. Distinct from confirmation bias (attention-direction failure: seeking evidence that confirms); this is attribution failure (misclassifying evidence already in hand). Detection rule: structural-significance claim resting on multiple data points where ≥1 is consistency-only, or generalization from N=1.

**`/devils-advocate` Technique 4** — Attribution-vs-Consistency Check. For each piece of evidence supporting a claim, label *cleanly-attributed* (cause demonstrably driving effect), *consistency-only* (data compatible with multiple explanations), or *unrelated*. Mark chains provisional if any link is consistency-only.

**`/devils-advocate` Technique 5** — Ambient triggering on assertion-shaped patterns. Self-check on output containing structural-claim shapes ("X causes Y," "this means Z," "the framework needs..."). Converts anti-bias discipline from per-decision ceremony to per-publish self-check. (Closes the bias-cluster open candidate from the same TL;DR — a sibling graduation in the same release.)

**`/corrections-audit` Step 6d** — ongoing detection. Scan corrections.md for the consistency-as-evidence signature; surface as graduation-confirmed at 3+ instances per 90 days.

**`CLAUDE.md` G-P-pre item 9** — pre-publish protocol step. Attribution check on causal claims is now part of the Mandatory Pre-Ship Protocol, so the framework's anti-bias discipline self-applies to the agent's own analysis.

## Theory grounding

- **Pearl** (causal inference): observational evidence vs interventional evidence. Consistency-with-hypothesis is observational; attribution requires intervention or controlled isolation. The anti-pattern names the conflation.
- **Argyris** (single-loop vs double-loop learning): single-loop fixes the symptom (correct each instance after the user catches it); double-loop fixes the pattern (graduate the rule into the framework so future instances are caught structurally). This graduation is the double-loop close.
- **Mycelium's own G-V12** (every check ships coverage proof): the receipts cases serve as the coverage proof for the new anti-pattern — three documented instances become the test fixtures.

## Mechanism + status

**Status**: graduated (2026-05-09). All five integration points landed in v0.21.0:
- Anti-pattern #7 in `harness/anti-patterns.md`
- `/devils-advocate` Techniques 4 and 5
- `/corrections-audit` Step 6d
- `CLAUDE.md` G-P-pre item 9
- This receipts case as the coverage-proof artifact

**Watch-list**: future instances of the pattern should be caught by Technique 5 ambient triggering OR by `/corrections-audit` Step 6d. If a 4th instance reaches publication despite the prevention layer, that's a signal the framework needs harder enforcement (e.g., a hook that fires on assertion-shape detection rather than relying on the agent to self-invoke `/devils-advocate`).

## Cross-references

- Sibling graduation: [stale-state-read-graduation](2026-05-09-stale-state-read-graduation.md) — anti-pattern #8 in the same release
- Sibling graduation: [bias-cluster-graduation](2026-05-09-bias-cluster-graduation.md) — `/devils-advocate` Techniques 4 and 5
- Source corrections: `corrections.md` 2026-04-30 (Agent over-scoped), 2026-05-03 (Sharper framing isn't always more correct), 2026-05-09 (RECURRING: Causal chain from observational consistency)
- Auto-memory pointer (founder-side): `feedback_self_apply_framework_discipline.md` (the meta-pattern: agent knows the rule, doesn't self-apply)
