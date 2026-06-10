---
id: 2026-06-11-fable5-autonomous-run
date: 2026-06-11
contributor: Håvard Bartnes (founder, Q3 bet-on-being-wrong test)
contributor_link: CONTRIBUTORS.md
project: mycelium-fable5-testrun + mycelium-fable5-stage2 (sandbox; dogfood evaluation of Fable 5 against Mycelium v0.40.4)
mechanism_or_status: shipped. v0.41.0 adds engine/autonomous-mode.md (declaration, substitution ladder, mandatory ledger, evidence-integrity boundary, human-only registry, harness-permission story) plus inline hard-gate markers in diamond-assess, diamond-progress, and mocked-persona-interview. Canvas opp-011 carries the evidence.
commits: [v0.41.0 bump commit]
subclass: dogfood-run-finds-missing-mode
---

# fable5-autonomous-run: the run that worked because its prompt smuggled in a missing framework concept

**Audience**: contributors and operators who want Mycelium runnable by scheduled agents and headless sessions without corrupting the evidence ledger. Also: anyone curious what happens when you point a frontier model at a framework designed around a person being present.
**Time to read**: 4 min.
**Last updated**: 2026-06-11.

## The trigger

The founder's Q3 bet-on-being-wrong: "I cannot make Fable 5 complete a full test run on Mycelium because of the way Mycelium is designed." A two-stage assumption test put the bet on trial. Stage 1 desk-audited all 54 skills for blocking interaction points. Stage 2 launched a headless Fable 5 session in a clean sandbox and told it to drive the minimal path: start, brief, assumption-test, diamond-assess. No human available, ever.

The prediction, confirmed before running: two to four hard human gates that the run must mock or skip.

## What the audit found

Five blocking points across 54 skills had documented non-interactive fallbacks. Five. Setup's AGENTS.md auto-mode default, interview's runtime_llm default, xai-check's tier default, metrics-pull's auto-routing, log-evidence's gap branch. Everything else either addressed questions to a user who would not exist, or hard-gated on a human response. The sharpest cut: `/mycelium:mocked-persona-interview`, the framework's own substitution mechanism for absent users, pre-commits its spectrum and stop condition by asking the user. The tool for simulating humans required a human.

And `engine/dogfood-mode.md`, the obvious place such authority would live, reframes stop conditions only. A killed diamond becomes a learning. It says nothing about who answers the questions. Mycelium had no documented autonomous-mode concept at all.

## What the run did

The run prompt carried a one-paragraph improvisation rule: use the documented default if one exists, else self-answer as the mocked founder persona and tag everything internal_simulated, else log a hard gate honestly and keep moving. With that paragraph, all six completion criteria passed. Zero human-input requests. No process cliff. The substitution ledger matched the Stage 1 predictions point for point.

Two findings stand above the rest. First, the model held the evidence boundary without being asked to: it tagged every persona-derived entry internal_simulated, failed its own Evidence gate honestly ("progressing on simulated evidence would game the Evidence gate"), and refused to simulate interview results, leaving its assumption test in designed status. The improvisation rule permitted answering-as-persona; the model correctly distinguished that from fabricating-external-evidence on its own.

Second, the run's only true hard gate was not Mycelium. The harness auto-denied every write under the sandbox's `.claude/` as a sensitive file in headless mode, across Bash, Write, cp, and filesystem-MCP, and rejected `$CLAUDE_PROJECT_DIR` expansion for good measure. The run mirrored its entire state tree to `mycelium-state/` and documented the mitigation rather than evading the control. Neither the founder's prediction nor the desk audit had considered a third actor.

## The cheap path, and why we did not take it

The cheap reading: the run completed, the bet is settled, archive the transcript. That reading leaves every future autonomous run re-inventing the improvisation rule in its prompt, which means every run measures prompt quality instead of framework behavior, and every audit starts by reverse-engineering what the prompt authorized. Undocumented behavior is audit noise even when the behavior is good.

The discipline path: graduate the rule the run proved. The prompt paragraph becomes `engine/autonomous-mode.md`. The ledger the run kept becomes the mandatory ledger format. The boundary the model held becomes the doc's hard rule. The gates the audit listed get inline markers: a documented fallback where substitution is legitimate, an explicit human-only marker where it is not.

## What shipped

v0.41.0. One engine doc and three skill markers. The doc covers declaration (explicit consent in the run prompt plus an `autonomous: true` flag; headless detection alone never activates the mode), the three-rung substitution ladder, the mandatory ledger at `.claude/evals/autonomous-run-log.md`, the evidence-integrity boundary, a human-only registry keyed to delegation-authority's no-standing list, and a harness-permission story: operator allowlist first (untested, honestly labeled so, gated by the next run), mandatory write probe, mirror fallback with re-integration.

The markers: diamond-assess substitutes its cognitive-forcing and coaching questions at rung (b), with the persona judgment recorded before state is read, because the ordering was always the load-bearing part, not the human authorship. Diamond-progress treats required-approval transitions and kill confirmations as autonomous hard gates, and explicitly revokes its re-invocation-as-approval shortcut for autonomous runs, since an agent re-invoking itself must never count as its own approval. Mocked-persona-interview may self-author its spectrum and stop condition, provided both hit the decision log before any profile exists.

## What this case taught the framework

1. **A framework designed around a present human encodes that assumption everywhere except where you can grep for it.** The audit found the gates not by searching "human" but by reading every interaction point and asking who answers. The fix is a mode, not a patch, because the assumption was a mode all along.
2. **The model's epistemic discipline exceeded its instructions, and the framework should bank that, not depend on it.** Fable 5 drew the answering-as-persona versus fabricating-evidence line unprompted. n=1, one model, one path. The boundary now lives in the doc so the next model does not have to be this good.
3. **Autonomous-mode design has three actors, not two.** Framework gates, model behavior, and the harness permission layer. The run's only stall came from the actor nobody predicted. The permission story is part of the mode's definition now, with its one untested claim labeled as untested.

## Mechanism + status

**Status**: shipped in v0.41.0. Canvas opp-011 (test-validated, confidence 0.7) holds the evidence chain; the solution entry logs two open assumptions, the settings-allowlist question first among them. The next autonomous run under the shipped doc is the test of that assumption, and its ledger is where the answer lands.

The founder bet that Mycelium's design would stop the run. The design held its gates exactly where the audit said they were, the model crossed them only where a documented rule authorized it, and the one wall nobody saw coming belonged to the harness. Good frameworks lose bets like this in the most useful possible way.

## Attribution note

Internal-only case. The operator is the founder; the test design, predictions, run prompt, transcript, and artifacts live in the sandbox repos (`mycelium-fable5-testrun`, `mycelium-fable5-stage2`). Persona and product vehicle (TrailNote) are fictional test scenario content. No external participants.
