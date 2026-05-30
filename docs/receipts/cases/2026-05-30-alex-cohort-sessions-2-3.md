---
id: 2026-05-30-alex-cohort-sessions-2-3
date: 2026-05-30
contributor: Alex
contributor_link: CONTRIBUTORS.md#v031x--cohort-first-run-friction-output-density--post-build-silence
project: alex-cohort-first-run
mechanism_or_status: partially-shipped — signals 3/4/5/6 shipped as the OST-routing ritual (guardrail G-D7 + discovery-domain intake subsection); 1/2/2b/7/8 still open (dispositions below)
commits: []
subclass: mid-build-friction
---

# alex-cohort-sessions-2-3 — what surfaces once the build is real and ideas start arriving

**Audience**: contributors and evaluators interested in mid-build friction — the gap between "first run" novelty and the day-to-day of carrying a real project through the framework.
**Time to read**: 5 min.
**Last updated**: 2026-05-30.

This case follows [alex-cohort-first-run](2026-05-26-alex-cohort-first-run.md). The first-run case captured the `/start` → build arc. This one captures Alex's Captains-Log for **Session 2 (2026-05-25, bug-fixing)** and **Session 3 (2026-05-29, feature expansion)**, plus a **canvas dashboard he built himself**, plus a cost/scaling note from his Discord message (2026-05-29). Raw artifacts live in the roadmap repo at `alex-feedback/` (`Captains-Log.md`, `mycelium-dashboard.JPG`).

Session 2 was mostly Alex fixing his own app's bugs and "learning to embrace agentic AI rather than my usual pair-programming style" — low framework signal by his own account. The weight is in Session 3 and the dashboard.

## The friction (triaged signals)

Eight distinct framework signals. Two are **recurrences** from the first-run case (they get heavier, not just longer); six are new at N=1. Honest attribution per signal below — most are single-tester, and the *fix* for each is a bet, not a settled conclusion.

1. **Canvas needs a visual surface — he built one** *(recurrence, N=2; strongest signal in this batch)*. First-run he asked "can we make an interface for the canvas to show progress in a more visual way?" Session 3 he stopped waiting and built it: a local live-reloading server showing diamond state, opportunities, solutions, decision log, and a searchable glossary with tooltips "so I'm not constantly flicking through docs to figure out what things mean." He packaged it **as a skill so anyone could drop it into a Mycelium project.** Drivers he names: the wall-of-text overwhelm, wanting "all my info in one place," and a checklist/overview instinct ("ADHD brain"). We have the screenshot, not the code yet.

2. **Walls of text recur — but we don't know his version** *(recurrence, N=2; confounded)*. First-run drove the v0.31.2 BLUF + Footnote convention. Session 3, `diamond-assess` still produced "a giant wall of text… a bit overwhelming." The tempting inference — "BLUF didn't land in the assessment skills" — is **unsafe**: v0.31.2 shipped 2026-05-26, Alex installed the plugin on 2026-05-15, and there is **no evidence he upgraded** before Session 3 (2026-05-29). The most parsimonious explanation is that he simply didn't have the fix. What the recurrence *does* confirm is that the friction is real and persistent for him; what it cannot tell us is whether v0.31.2 addresses it, because we never observed v0.31.2 running on his machine. This surfaces a **second-order signal**: cohort testers run whatever version they installed and rarely re-pull, so shipped fixes don't reach the people whose friction motivated them. Version-on-machine is an unmeasured variable in every cohort report — we should capture it.

3. **In-flight ideas have no home** *(new, N=1, specific)*. He rattled off features (preferred stores, split-store shopping, barcode scanner, substitutions, Kassal scraping). "It keeps absorbing new ideas in the chat but hasn't added them specifically anywhere yet… won't some of this get lost in the noise if I run multiple sessions?" He found ideas eventually land in the decision log but reads that as decisions-made, not ideas-under-consideration, and asks for "a backlog or exploration log for ideas outside the current scope."

4. **The drift guardrail fires reactively, not proactively** *(new, N=1)*. "It only flagged that I was drifting into feature-first territory when I started pushing back, so I had to go looking for the reality check rather than the framework giving me one." The feature-first NUDGE arrived after he self-corrected — backwards.

5. **Challenged-suggestion state is invisible** *(new, N=1)*. When the framework challenged a feature he proposed, he couldn't tell the outcome: "does this mean they are added to the current build or something to add later? Doesn't seem to have added them to any of the canvas files." A challenge resolves to *some* disposition (build now / defer / discard) and the user can't see which.

6. **L0-vs-L2 boundary is unclear mid-build** *(new, N=1)*. "Hard to tell what actually belongs in the current diamond vs what should be its own thing further down the scale. The L0 vs L2 split makes sense on paper but mid-build it's not obvious when you're crossing that line."

7. **YAML generation breaks the canvas, caught only by hand** *(new, N=1, concrete failure)*. The AI-generated canvas had a duplicate key (parse failure) and **content swapped between files** — solutions sitting in `opportunities.yml`, opportunities in `solutions.yml`. He fixed it manually. `validate_canvas.py` has a duplicate-ID check, but it runs on CI, not inline at generation time, and a swapped-content / duplicate-*key* failure can sit in the working tree until something tries to read it — which for Alex was his own dashboard. "Especially if I want a live dashboard that relies on this data being correct."

8. **Context/plan cost will scale with the codebase** *(new, N=1, Discord)*. On the Claude Pro plan; hasn't hit caps "but I assume it will become a problem as more code gets added and it does an assessment of the current project state." A real ceiling for cohort testers on lower tiers as project-state assessments grow.

Two further items in the log — list comparison when a store doesn't stock a product, and discontinued products in search results — are **his app's** problems, not framework signals. Logged here only to mark them as correctly *not* metabolized.

## Disposition (nothing shipped — these are bets for the maintainer)

| # | Signal | Candidate disposition | Confidence in the fix |
|---|---|---|---|
| 1 | Canvas visual surface | Elevate the *need*, not his artifact. A first-party canvas-viz answer must be **harness-agnostic** — read the portable `canvas/*.yml` substrate, render across Claude Code TUI, Claude Code desktop/web UI, opencode, and OpenAI/Codex-style surfaces alike. His dashboard is Claude-Code-specific; don't adopt or ask for the code, design for the multi-surface case. | Friction cleanly-attributed (N=2 + built it). Fix shape open and explicitly cross-harness. |
| 2 | Walls of text (version-confounded) | First, capture cohort version-on-machine so this is measurable. Only then judge whether v0.31.2 BLUF reaches assess/progress output — don't audit against a fix he may never have run. | Friction real; the *cause* is unmeasured (version unknown). |
| 2b | Stale cohort versions | Add a lightweight "what version are you on?" prompt to feedback intake; consider an upgrade nudge / version surfacing so testers know they're behind. | New second-order signal from #2; N=1 but structural. |
| 3 | No home for in-flight ideas | **Don't build a new store** (see Existing-systems check below). Route ideas into the existing OST (`opportunities.yml` / `gist.yml`), pruning via archive-with-reason. The gap is the routing *ritual* not firing mid-build, not a missing file. | N=1; reframed from "new store" to "use existing OST" after investigation. |
| 4 | Reactive drift guardrail | Feature-first NUDGE should fire on idea accumulation, not on pushback. "Park" must resolve to a scoped child opportunity or archive-with-reason — never an unbounded list. | N=1; consistency-only on mechanism. |
| 5 | Challenged-item state invisible | When the agent challenges a suggestion, state the disposition (routed-to-opp / gist-leaf / archived-with-reason) + where it landed. | N=1; pairs with #3. |
| 6 | L0-vs-L2 boundary | Surface scale at intake using the existing `scale`+`parent` fields on `opportunities.yml`. | N=1; the structure already supports it. |
| 7 | Inline canvas validation | Run `validate_canvas.py` (or a subset) right after AI canvas writes; extend it to catch swapped-content + duplicate non-ID keys. | Concrete failure; clear value. |
| 8 | Context-cost scaling | Track against `docs/context-surface.md`; scope project-state assessment for lower-tier plans. | N=1; watch for cohort recurrence. |

Signals 3, 5, and 6 cluster: they're all "where does this idea/decision *go*, and can I see it?"

**Existing-systems check (run 2026-05-30 before proposing anything new).** The homes already exist and are actively used: `canvas/opportunities.yml` (OST opportunities, with `scale` + `parent` fields — exactly the L0-vs-L2 axis of #6), `canvas/gist.yml` (GIST solution leaves), `canvas/archived-solutions.yml` (discarded leaves logged **with a reason**), plus `scenarios.yml`/`user-needs.yml`. The maintainer's own recollection — an early dogfood session where he "dumped a lot of material" and the agent stored it correctly — is the discovery intake routing into exactly these files; it still works (opportunities.yml populated through 2026-05-24). Crucially, `engine/leaf-lifecycle.md` makes the OST **deliberately anti-backlog**: a named *Score-Only Discard* anti-pattern, an explicit Discard/Archive protocol, ideas pruned-with-reason rather than accumulated.

So the cluster is **not a missing-storage problem** — a new `exploration-log.yml` parking lot would (a) compete with the OST and (b) reintroduce the backlog anti-pattern the Thoughtworks SDD podcast warns against (*"a spec should never end up in a backlog"* — accumulation decoupled from the active loop = waterfall regression), which is the exact "lost in the noise" failure Alex himself feared. It's a missing-**routing-ritual** problem: mid-build, the agent stopped routing ideas into the existing OST and absorbed them into chat instead. Fix is behavioral, not structural — route each idea into the OST immediately (new opportunity / gist leaf / scoped child opportunity via existing `scale`+`parent`), state disposition + scale back visibly, prune via archive-with-reason. No new file.

(Note: opp-009 "UI modality coverage gap" is *adjacent* to signal #1 but distinct — it's about quality-eval skills clustering on web/GUI for the user's product, not the framework's own output surface. Don't conflate them.)

## What this case taught the framework

The first-run case was about *getting through* the arc. This one is about *carrying a real project* — and the friction moved accordingly: from "what do I do next" to "where did my idea go" and "can I trust the data." The single loudest fact is **signal #1**: a tester hit enough terminal-output pain that he built his own visual layer rather than wait. That's the second independent request for a canvas UI and the first time someone shipped one. It says the wall-of-text problem isn't only a density problem the BLUF convention can fully solve — for some users it's a *modality* problem (terminal vs. visual overview), which is a strategic question, not a copy-editing one.

Attribution honesty: seven of eight signals are N=1 from one cohort tester. None of the *fixes* are validated. What's cleanly-attributed is that the friction is **real and lived** (a working dashboard is hard to argue with); what's a bet is every proposed remedy. Per anti-pattern #7, no structural conclusion gets drawn from N=1 here — the dispositions are candidates for the maintainer to weigh, not a roadmap.

## Mechanism + status

**Status**: partially-shipped. Signals **3/4/5/6** shipped 2026-05-30 as the OST-routing ritual — guardrail **G-D7** (`harness/guardrails-discovery.md`, `NUDGE` `scope`) plus a concrete "In-flight idea intake (mid-build)" subsection in `domains/discovery/CLAUDE.md`: route each idea into the existing OST in the same turn, state where it landed + disposition + scale, resolve challenges to a named disposition, fire the drift nudge proactively on idea-accumulation. No new store (the `exploration-log.yml` parking-lot was examined and rejected on Thoughtworks anti-backlog grounds). Decision trail: `.claude/harness/decision-log.md` 2026-05-30 — the original PROPOSAL plus the implementation entry "Implement the OST-routing ritual (G-D7)". The fix's efficacy is untested (N=1); confidence 0.55. Signals **1, 2/2b, 7, 8** remain open — build decisions (which to act on, how) are the maintainer's, deliberately not pre-decided here; signal 2 stays gated on Alex's plugin-version reply.

## Attribution note

Alex consented to be named on 2026-05-26 (reconfirmed 2026-05-28); public/nameable in framework-facing docs. Raw artifacts stay in the roadmap repo's `alex-feedback/`, matching the `hoskins-feedback/` precedent.
