---
id: 2026-06-07-faros-whiplash-integration
date: 2026-06-07
contributor: Håvard Bartnes (founder self-dogfood + external report integration)
contributor_link: CONTRIBUTORS.md
project: mycelium-roadmap (private; generic-framed receipt. Raw assessment artifacts live in the private dogfood draft)
mechanism_or_status: shipped. Three framework changes landed in one cycle (v0.39.19) plus a discipline note for the symmetric premise-check honesty pattern. The counter-metric for the new APEX fields ships with them, per the self-applied scaffold-without-instrumentation rule.
commits: [73fb436, 7454894, 50fe441, 1dcc39b]
subclass: external-report-integration
---

# faros-whiplash-integration: when the report you cite is the one that fact-checks you

**Audience**: contributors and evaluators interested in how Mycelium integrates an external research artifact without letting the report's vocabulary become the framework's vocabulary by import.
**Time to read**: 6 min.
**Last updated**: 2026-06-07.

## The trigger

Two external reports arrived as prompts in the same week. Faros AI's *Acceleration Whiplash* (2026-04-12, telemetry from 22,000 devs and 4,000 teams) plus its companion *Harness Engineering* note (2026-05-22) name a five-layer model for AI coding agents: orchestration, verification, context and memory, guardrails, observability. The headline finding is colder than the layer model. Strong DORA foundations did *not* protect mature teams. Rework climbed. Churn climbed. PRs merged with no review climbed. Datadog's *State of AI Engineering* (2026, production telemetry from 1,000+ customers) arrived a few days later as a same-session amendment from independent runtime data: system prompts averaging ~69% of input tokens; only ~28% of cache-capable calls hitting cache; capacity and rate-limit dominating runtime failure.

The ask was to score Mycelium honestly against the five-layer model, map each finding to a Mycelium response, design the single highest-value improvement, and propose an ICE-scored backlog. Two passes were requested: the first ran on the Faros pair; the same session a second prompt added Datadog and a new dimension (AI products built *with* Mycelium, not just Mycelium itself).

## The temptation, and why we did not yield

The amendment prompt described the first pass as having **no source provenance** and missing the Datadog source. Reading the on-disk artifact, the first defect was not present. The draft, the decision-log entry, and the corrections entry all carried [S1]–[S4] tags inline on every claim, with URLs and dates. The second defect, missing Datadog, was real.

The cheap path on receiving a wrong factual premise is silent agreement. Regenerate the prior pass as if it had no provenance; the founder cited the gap; the gap is closed; everyone moves on. Silent agreement reads as helpful. It costs the agent nothing in the moment.

The path the framework asks for is the symmetric move to a pattern already documented (`corrections.md` 2026-05-25, *"agent uses founder's own framings as legitimation for the cheap default"*). That cluster's shape was: agent reaches for the nearest founder-cited *principle* to justify a default that happens to be cheap. The new shape is: agent reaches for silent agreement with a founder-cited *factual claim* about a prior artifact's state when the cheap default is to regenerate from scratch. Same System-1 root. Different surface.

So the amendment surfaced the discrepancy in the draft, in the decision-log, and in a new corrections entry, then executed the substantive new asks ([S5] integration, the new Level B dimension, a reconciled tagged backlog). Three valid reads of why the founder framed it that way (intentional discipline test, honest misremember, working from stale state) all served the same response: honest readback, not silent agreement.

## What surfaced in the scoring

Five layers, honest scores: tool orchestration 3/5, verification loops 4/5, context and memory 4/5, guardrails 3/5, **observability 3/5: strong scaffolding, weak instrumentation**. The L5 finding refined the founder's pre-existing hypothesis ("L5 is the weakest") rather than confirming it as stated. L5 is not bare. It has the most ambitious schema and the thinnest enforcement. The APEX block in `dora-metrics.yml` declares fields named `ai_rework_rate`, `ai_acceptance_rate`, scope-expansion. The `change-log.jsonl` event stream captures every Edit/Write with session_id and diamond_id. The `corrections.md` entries are origin-tagged. The infrastructure exists. The *computation*, the hook or skill that reads raw artifacts on a cadence and surfaces a number, does not. The 2026-06-02 audit's finding "~90% ai-generated, ~63% caught by user, 0% caught by hook/evaluator" lives in `corrections.md` prose because a human noticed during a manual audit. Scaffold-mistaken-for-instrumentation: the appearance of observability without the measurement.

The Whiplash report's "+861% code churn" and "31.3% PRs merged with no review" findings have a Mycelium-specific shape. Solo + agent means "agent-authored" is 100% by construction, so the incident-disambiguation question does not apply. But the rework-rate canary tells the same story by a different route. Mycelium's loose CFR climbed from ~21% (2026-05-04 snapshot) to ~38% (2026-06-05). That climb is the same shape the Whiplash telemetry names as the load-bearing signal. Five elite DORA metrics did not protect against it. The dispute with DORA's 2025 "strong foundations protect you" conclusion lands directly on the framework's own self-assessment.

## What shipped, and how the level split works

The founder selected three changes from a seven-option decision point, all Level A (the framework itself):

1. **A new skill `/mycelium:scaffold-cost-check`** that sums bytes across `CLAUDE.md + engine + harness + AGENTS.md + canvas + memory`, divides by 4 (±15% heuristic), and prints a structured table. Print-only default; `--write` opt-in persists to `dora-metrics.yml#apex.scaffold_token_estimate`. First dogfood run produced the first number we have ever had for this surface: ~115K tokens framework load, ~331K tokens project state, **~449K tokens total eligible scaffold**.
2. **An extended `/mycelium:dora-check` MANDATORY** that requires three APEX fields (`ai_rework_rate`, `ai_acceptance_rate`, `hook_detection_rate`) to be **computed from raw artifacts** (git log plus `corrections.md` detection_origin tags) rather than filled with narrative. The `hook_detection_rate` field promotes the 2026-06-02 narrative finding to a tracked metric. First compute-from-raw run: roadmap 30d rework 5.3%; upstream 30d 16.1%; today 0% (sample-of-1, does not collapse the 2026-06-05 burst canary); hook_detection_rate 8.3% over tagged-sample, ~0% on the deep classes where the corrections cluster mostly fires.
3. **A new orthogonal canvas-guidance axis `runtime_llm: true|false`** plus an `/mycelium:interview` Phase 6 question. Decoupled from `product_type` because a `content_publication` with an LLM-backed reader-Q&A is `runtime_llm: true`. Precondition for a planned Runtime-LLM Harness Gate at L3 (v0.40.x), modeled on the existing Regulatory Gate template.

The fourth item, the Level B gate itself, was explicitly *not* shipped. A gate that requires AI products to instrument before Mycelium itself does is the rule-we-don't-follow-ourselves pattern the framework already names. Sequenced behind Level A telemetry stabilizing.

The first dogfood run also produced one positioning finding. Project canvas plus memory (~331K tokens) is 2.9× the framework load surface (~115K). The claim "Mycelium has small framework overhead" is defensible. The claim "the discipline imposes a small *total* load" is not, because the canvas and memory the framework asks you to write is where the mass lives. A counter-discipline was added to the scaffold-mistaken-for-instrumentation correction: scaffold-cost framing must cover canvas and memory, not just framework files, when used in external-facing copy.

## What this case taught the framework

Three lessons, each grounded in the artifact rather than the intent:

1. **Provenance stays inline on substantive claims.** Even when the prompt frames the prior work as missing it, even when silent agreement is cheaper, the audit trail is the artifact. Not the framing around it. The premise-check is itself the discipline: read the prior artifact before amending it. Same Read-before-Recommend shape; new surface (factual premise about prior state, not gate-narration).
2. **Scaffold-mistaken-for-instrumentation is the L5 trap that templates encourage.** Schema fields anchor expectations the moment they're named. The fix is not better narrative in canvas; it is shipping the computation alongside the schema, at the same maturity, with its Goodhart counter. The compute-from-raw discipline lands as a `MANDATORY` block in `/mycelium:dora-check`, not as a recommendation. The framework's own discipline now refuses to ratify the narrative-only path.
3. **External vocabulary lands as a layer, not a replacement.** The five-layer model from Faros, the production telemetry shape from Datadog, the Level A versus Level B split: these became a refinement on the framework's existing decomposition (engine, harness, hooks, skills, canvas), not a parallel system. The Regulatory Gate template was the load-bearing reuse. A conditional-fire gate on a canvas classification flag was already proven once; the `runtime_llm` gate is the second instance, not a new mechanism.

The counter-metric for `ai_rework_rate` and `hook_detection_rate` (first-pass-success rate computed from `evals/pass-history.json`) ships in the same cycle, per the scaffold-mistaken-for-instrumentation discipline now self-applied. Currently the pass-history shows 0 runs across all evals; the COMPUTE is real, the underlying data isn't, and the output honestly says so until eval-runner is in regular use. That honest gap is itself the staged-measurement-plan move: read existing raw data first, even when the data shows the gap.

The report that prompted the assessment is the one that fact-checked it. A receipts case can confirm that on the way out the door, or it can pretend it didn't. We chose the first one.

## Mechanism + status

**Status**: shipped. v0.39.19 carries B14 (scaffold-cost-check), B2 (dora-check Part 2b compute-from-raw), B13 (runtime_llm orthogonal axis + interview extension). v0.39.20 adds the counter computation (`apex.first_pass_success_rate`) to the same Part 2b block so the new metrics ship with their pair. The roadmap-side draft (`.claude/drafts/faros-whiplash-assessment-2026-06-07.md`) carries the full five-source-tagged assessment, the level split, the seven-option decision point, the founder selection, and the upstream-author brief. Decision-log entries on the roadmap side record [S1]–[S5] provenance and the symmetric premise-check honesty pattern.

Deferred to v0.40.x: the Level B Runtime-LLM Harness Gate itself, the SessionStart cache-prefix audit, and the AI-product loop-budget + cache-strategy declaration requirements. Sequenced behind the 2026-06-05 rework canary stabilizing in the now-numeric APEX read.

## Attribution note

External reports cited with URLs and dates:

- [S1] Faros AI, *Ten takeaways from the AI Engineering Report 2026: The Acceleration Whiplash* (2026-04-12). https://www.faros.ai/blog/ai-acceleration-whiplash-takeaways
- [S2] Faros AI, *Harness Engineering: What makes AI coding agents work in 2026* (2026-05-22). https://www.faros.ai/blog/harness-engineering
- [S3] Anthropic, *Harness design for long-running agents*. https://www.anthropic.com/engineering/harness-design-long-running-apps
- [S4] DORA, *2025 State of AI-Assisted Software Development report*. https://dora.dev/research/2025/dora-report/
- [S5] Datadog, *State of AI Engineering* (2026). https://www.datadoghq.com/state-of-ai-engineering/

[S1] and [S5] reach the observability-essential conclusion from independent data (build-time vs runtime telemetry). [S1] explicitly disputes [S4]'s "strong foundations protect you" conclusion using telemetry rather than survey. The dispute is informative, not invalidating; the framework records it as a paired-conclusion finding.
