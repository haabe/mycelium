---
name: dora-check
description: "Assess delivery health metrics. For software: DORA + APEX. For content/AI/service products: product-type-appropriate metrics."
metadata:
  instruction_budget: "126"
  framework_dependency: "mycelium"
  framework_dependency_note: "This skill is designed to run within the Mycelium framework (https://github.com/haabe/mycelium). Standalone use will skip the canvas state, theory gates, and harness behavior the skill assumes. Install: /plugin install mycelium@haabe/mycelium."
---

# Delivery Metrics Check

Assess delivery health using product-type-appropriate metrics. Check `product_type` from `.claude/diamonds/active.yml` to determine which assessment to run.

**Product type routing** (v0.11.0):
- **software**: Full DORA + APEX assessment (Parts 1-3 below)
- **content_course, content_publication, content_media**: Content Delivery Assessment (Part 4 below)
- **ai_tool**: AI Tool Assessment (Part 5 below) + DORA/APEX if code components exist
- **service_offering**: Service Delivery Assessment (Part 6 below)

---

## Preflight: Read target canvas file(s) before any Write/Edit

**Hard rule.** Before issuing `Write` or `Edit` against any `.claude/canvas/*.yml`, use the **Read tool** on that file in this session. Claude Code's Read-before-Write check requires the `Read` tool specifically — `cat`/`head`/`grep` via Bash do NOT satisfy it.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`** (exact-string replacement): `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`** (full replacement): do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

**ID-bearing entries — scan the ID space before assigning** (added 2026-05-15, v0.23.19): When adding a new component, opportunity, solution, or any other ID-bearing entry to a canvas file, run a Bash grep first to confirm the next ID in your prefix sequence is actually free:

```
grep "^  - id: <prefix>-" .claude/canvas/<file>.yml | sort -u
```

Replace `<prefix>` with the canvas's ID prefix (`comp` for landscape, `opp` for opportunities, `sol` for solutions, `ht` for human-tasks, etc.). Then pick the next free integer. `validate_canvas.py` has a duplicate-ID check (lines 230-239) that catches the failure on CI, but a duplicate can persist in the working tree for days if CI isn't run between edit and discovery — see roadmap-repo `corrections.md` 2026-05-15 "Duplicate canvas ID created in landscape.yml" for the worked example.

Original failure mode: anti-pattern #7 instance #5, 2026-05-09 — agent conflated Bash `head` with the Read tool, lost ~14k tokens to a Write-fail → remedial-full-Read → re-Write loop. The `limit:1` discipline (graduated 2026-05-14, v0.23.18) prevents the second-order cost where the agent *correctly* follows the rule but full-Reads every time. The ID-scan discipline (graduated 2026-05-15, v0.23.19) prevents the related class where the agent reads enough of the file to satisfy the Edit check but not enough to see existing ID assignments — kin to anti-pattern #8 (Stale State Read).

If this skill writes to multiple canvas files, register each one first (limit:1 for Edit-only paths; full Read for Write paths) AND ID-scan any prefix you intend to assign.

See `CLAUDE.md` *Canvas writes — Read before Write* for the canonical rule.

## Software Products

Assess delivery health using Forsgren's five DORA metrics AND LinearB's APEX AI-era metrics.

## Part 1: DORA Metrics (Forsgren)

Gather current metrics from CI/CD, deployment logs, incident records.

*Note: DORA expanded from 4 to 5 metrics. "MTTR" was renamed to "Failed Deployment Recovery Time" (FDRT) for precision — the original name was ambiguous with other mean-time-to-X metrics. "Reliability" was added as the 5th metric in the 2024 State of DevOps report.*

**Deployment Frequency**: How often does code reach production?
- Elite: On-demand (multiple deploys/day)
- High: Between once/day and once/week
- Medium: Between once/week and once/month
- Low: Less than once/month

**Lead Time for Changes**: Commit to production time?
- Elite: Less than one hour
- High: Between one day and one week
- Medium: Between one week and one month
- Low: More than one month

**Change Failure Rate**: % of deployments causing failure?
- Elite: 0-15%
- High: 16-30%
- Medium: 31-45%
- Low: 46-100%

**Failed Deployment Recovery Time (FDRT)**: Time to restore service after a failed deployment?
- Elite: Less than one hour
- High: Less than one day
- Medium: Between one day and one week
- Low: More than one week

*Formerly "Mean Time to Recovery (MTTR)." Renamed for precision — FDRT measures recovery from failed deployments specifically, not all incidents.*

**Reliability**: Does the software meet or exceed its reliability targets?
- Elite: Meets or exceeds targets
- High: Slightly below targets
- Medium: Moderately below targets
- Low: Significantly below targets

*Added in DORA 2024. Measures operational reliability via SLOs/SLIs. Connects to SRE metrics in Part 3.*

## Part 2: APEX Metrics (LinearB)

**"Faster coding doesn't mean faster delivery."**

Assess the four APEX pillars to detect AI-era delivery problems:

### A — AI Leverage
- What % of PRs/code changes are AI-generated or AI-assisted?
- What is the AI suggestion acceptance rate? (Benchmark: 32.7% for AI vs 84.4% for human — LinearB 2026)
- What is the AI rework rate? (% of AI code rewritten within 21 days)
- Is AI code quality comparable to human code? (Check corrections.md origin field)

### P — Predictability
- Planning accuracy: % of planned work completed per cycle?
- Rework rate: % of ALL code rewritten within 21 days?
- Are delivery estimates getting more or less reliable with AI?

### E — Flow Efficiency (The Shifting Bottleneck)
- End-to-end cycle time: is it actually decreasing?
- Review wait time: are PRs waiting longer before first review?
- AI review wait ratio: do AI PRs wait longer than human PRs? (Benchmark: 4.6x — LinearB 2026)
- **KEY CHECK**: Is coding faster but review/testing/deployment slower? If yes, the bottleneck has shifted. AI is generating code the pipeline can't absorb.

### X — Developer Experience
- Developer satisfaction with AI tools (survey or conversation)
- Cognitive load: is AI helping or adding complexity?
- Burnout signals: unsustainable pace? Context-switching? Alert fatigue?
- Maps to BVSSH "Happier" dimension

## Part 2b: Compute APEX from raw artifacts (v0.39.19, MANDATORY for software / ai_tool)

**Why this is mandatory** ([S1] Faros *Acceleration Whiplash* 2026, [S2] Faros *Harness Engineering* 2026, [S5] Datadog *State of AI Engineering* 2026): the APEX section was prone to being filled with narrative `notes:` and `status:` colors while the underlying numbers stayed unmeasured — scaffold-without-instrumentation (corrections.md 2026-06-07 in the roadmap repo). The fix is to compute the load-bearing APEX fields from raw artifacts the project already produces, rather than treating the canvas surface as the measurement.

For each field below, **compute the number first** from the raw artifact, **then** write `value:` to canvas; preserve the prior narrative as `notes:` (do not destroy it).

**`apex.ai_rework_rate`** — fix-forward commits as a % of total commits in window.
- Raw artifact: `git log --since="<window>" --pretty='%H %s'` on the repo's primary branches.
- Computation: a commit counts as "fix-forward" if its subject matches the project's fix-pattern (default: `^(fix|amend|patch|hotfix|chore: re-validate|chore: fix)` or modifies files touched by the immediately prior commit on the same path within N hours). Document the chosen pattern + window in `apex.ai_rework_rate.method`.
- Output: `{ value: <pct>, window: "<24h|7d|30d>", method: "<pattern>", notes: "<prior narrative>" }`.
- Trend: maintain a small numeric series in `measurement_history` alongside the existing `change_failure_rate` strings.
- Honest framing: when the project is 100% AI (solo + agent), `ai_rework_rate` ≈ project rework_rate; name this in `notes:`.

**`apex.ai_acceptance_rate`** — proportion of agent-proposed actions the user accepts without redirection.
- Raw artifact (proxy, honest about being a proxy): count of `corrections.md` entries with `detection_origin: user` in the same window ÷ count of total agent actions narrated in the session log if available; otherwise narrative estimate carried forward with `method: "narrative; instrumentation pending"`.
- Output: `{ value: <pct>, method: "<exact|proxy|narrative>", notes: "<prior narrative>" }`.

**`apex.hook_detection_rate`** — proportion of corrections that were caught by a hook or validator vs by the user.
- Raw artifact: `corrections.md` entries' `detection_origin:` field (`user` / `hook` / `evaluator` / `agent`). Count by category in window.
- Output: `{ value: <pct>, denom: <total>, user: <n>, hook: <n>, evaluator: <n>, agent: <n>, window: "<7d|30d>", notes: "load-bearing — if hook+evaluator ≈ 0%, the harness-detection-gap signal applies (corrections.md 2026-06-02 audit)" }`.
- This field is the [S1] + [S5] canary: a harness with rising rework and ~0% hook-detection is the failure mode both reports diagnose.

**Goodhart pair** (already named in `dora-metrics.yml#goodhart_check`): `ai_rework_rate` MUST be paired with `ai_acceptance_rate`. Rework-rate rising while acceptance-rate ALSO rising = healthy (validators catching real issues, user still accepting agent direction). Rework-rate rising while acceptance-rate falling = unhealthy (agent output quality dropping). Never report one without the other.

**`apex.first_pass_success_rate`** (v0.39.20, the Goodhart counter for `ai_rework_rate` + `hook_detection_rate`) — proportion of eval scenarios that pass on first attempt across the active corpus.
- Raw artifact: `.claude/evals/pass-history.json`. Each eval entry carries `{runs, passes, last_5, last_run, status}`.
- Computation: sum `passes` ÷ sum `runs` across all evals where `status: active`. If `last_5` is populated, also report the trailing-5 pass rate as a sharper recent signal.
- Output: `{ value: <pct>, denom: <runs>, numerator: <passes>, trailing_5_pct: <pct or null>, active_evals: <count>, method: "sum-passes/sum-runs over status:active evals from pass-history.json", notes: "<honest framing>" }`.
- **Honest framing on the data-gap**: if total runs is 0 (eval-runner not invoked recently), report `value: null, method: "N/A — 0 runs across N active evals; counter exists, underlying data does not until eval-runner is in regular use", note: "this honest read is itself the staged-measurement-plan move [S2] — read existing raw data first even when data shows the gap"`. Do NOT default to a fake number.
- **Goodhart pair anchor**: this field is the explicit counter for `ai_rework_rate` and `hook_detection_rate`. Rework falling AND first-pass-success rising = healthy. Rework falling AND first-pass-success ALSO falling = unhealthy (you've optimized rework by NOT shipping, or by gaming the rework pattern). Never read rework alone.
- **Discipline source**: per the scaffold-mistaken-for-instrumentation correction (roadmap `corrections.md` 2026-06-07): every new metric field ships with its counter at the same maturity. This field exists because the three preceding APEX numerics shipped in v0.39.19; the counter ships in v0.39.20 in the same Part 2b block to honor that discipline.

**Cadence**: compute on every `/mycelium:dora-check` run; do not narrate "refreshed APEX" unless these four numeric fields actually moved (Postflight discipline below).

**Sources**:
- [S1] Faros AI, *Ten takeaways from the AI Engineering Report 2026: The Acceleration Whiplash*, 2026-04-12. https://www.faros.ai/blog/ai-acceleration-whiplash-takeaways
- [S2] Faros AI, *Harness engineering: What makes AI coding agents work in 2026*, 2026-05-22. https://www.faros.ai/blog/harness-engineering
- [S5] Datadog, *State of AI Engineering* (production LLM telemetry, 1,000+ customers), 2026. https://www.datadoghq.com/state-of-ai-engineering/

## Postflight: Verify-After-Write (write-narration-verification discipline)

**Hard rule** (per CLAUDE.md Communication Rules, anti-pattern #7 Stage 2 graduation — v0.39.18). Before the user-facing summary claims "✅ updated `dora-metrics.yml`" / "✅ refreshed APEX" / similar, verify the write actually changed the value fields named in `## Canvas Output` below — not just `_meta.last_validated`. Use the **Read tool** on `dora-metrics.yml` after the edits to confirm `deployment_frequency.current`, `change_failure_rate.current`, `time_to_restore.current`, `apex.*`, `measurement_history`, etc. hold the new measurements. If only `_meta` changed and value fields stayed stale, the narration is a state-claim on a state the skill did not achieve (AP#7 instance #18 was the worked failure, 2026-06-05 — operator surfaced it with the Torres-shape question *"Did you run the dora check?"*). Symmetric to the Preflight above: Preflight protects what gets WRITTEN; Postflight protects what gets CLAIMED about what was written. Validator Check 42 enforces preamble presence.

## Output

**Lead with the verdict; isolate the bottleneck** (Von Restorff, per `harness/design-principles.md` — the constraining metric is the one finding the reader must not scroll past; graduated from two consecutive `/framework-health` 4e flags, 2026-06-05 + 2026-06-12):

```
## DORA + APEX Assessment

> **Verdict: [HEALTHY | BOTTLENECK: <metric> — <one line on where the constraint lives and the first focusing step>]**

### DORA Metrics
| Metric | Current | Level | Target | Gap |
|--------|---------|-------|--------|-----|
| Deploy freq | ... | ... | ... | ... |
| Lead time | ... | ... | ... | ... |
| Change fail rate | ... | ... | ... | ... |
| FDRT | ... | ... | ... | ... |
| Reliability | ... | ... | ... | ... |

### APEX Metrics (AI-Era)
| Pillar | Status | Key Signal |
|--------|--------|-----------|
| AI Leverage | ... | AI acceptance rate: ...% |
| Predictability | ... | Planning accuracy: ...%, Rework rate: ...% |
| Flow Efficiency | ... | Cycle time: ..., Review wait: ... |
| Developer Experience | ... | Satisfaction: ..., Burnout: ... |

### Shifting Bottleneck Check
[Is coding faster but review/deployment slower? Yes/No]
[If yes: where is the new bottleneck?]

### DORA Bottleneck
[The metric most constraining overall performance]

### Value Stream Diagnosis (if bottleneck detected)
If DORA shows a bottleneck, map the value stream to identify WHERE in the flow the constraint lives:
- Run `/mycelium:canvas-update` to update `.claude/canvas/value-stream.yml` with current stage timings
- Apply Theory of Constraints Five Focusing Steps (Goldratt): Identify -> Exploit -> Subordinate -> Elevate -> Repeat
- Look for wait times >> process times (a sign of queuing, not capacity, problems)
- Look for high handoff counts (each handoff adds delay and information loss)
- Calculate flow efficiency: process_time / lead_time -- target >25%

### Top 3 Improvements
1. [specific action]
2. [specific action]
3. [specific action]
```

## Part 3: SRE Metrics (Error Budgets)

If SLIs/SLOs defined in `.claude/canvas/dora-metrics.yml` sre section:
- Review each service's SLI values against SLO targets
- Calculate error budget remaining: (SLO - actual) / (1 - SLO) * 100%
- **Healthy** (>50%): Ship features. Budget available.
- **Warning** (<25%): Slow down. Increase testing.
- **Depleted** (0%): Feature freeze. Reliability takes priority.

Error budgets are the social contract: reliability earns the right to ship faster. Connects to BVSSH Safer.

If NOT defined: "Consider defining SLIs/SLOs to balance velocity with reliability."

## Decision Log (MANDATORY)
**Always APPEND** a `### DORA Assessment` or `### Delivery Metrics Assessment` entry to `.claude/harness/decision-log.md` with:
- Each metric assessed, current baseline, target, and classification level
- The identified bottleneck and recommended improvements
- Any shifting bottleneck signals (AI-era: coding faster but review slower)
This ensures the delivery metrics gate has auditable evidence.

## Canvas Output
**Always update** `.claude/canvas/dora-metrics.yml` with:
- DORA metrics, classifications, and capability scores
- APEX section: ai_leverage, predictability, efficiency, developer_experience
- SRE section: SLI/SLO status, error budget remaining
- Measurement history for trend tracking

---

## Part 4: Content Delivery Assessment (v0.11.0)

For content_course, content_publication, content_media products. Read `.claude/canvas/content-metrics.yml`.

### Producer-Side (how well we make it)

**Publication Cadence**: How often does content reach the audience?
- Consistent: meeting target cadence
- Improving: cadence accelerating
- Declining: cadence slowing -- investigate bottleneck

**Production Lead Time**: Idea to published -- how long?
- Identify the bottleneck: writing, editing, recording, review, publishing?

**Revision Rate**: % of published content requiring significant revision?
- Low (<10%): healthy quality process
- Medium (10-25%): review process may need strengthening
- High (>25%): quality issues -- root cause analysis needed

**Completion Rate**: % of planned content actually completed on schedule?

### Customer-Side (how well it sells and retains)

**Time to First Value (TTFV)**: How quickly does a buyer access and get value after purchase?
- Instant download/access: excellent
- Hours (email delivery, account setup): acceptable
- Days (manual enrollment, approval): investigate bottleneck
- Lower TTFV = lower refund risk.

**Engagement & Drop-off**: Course completion rate, satisfaction, return rate?
- Where do users abandon? (drop_off_points) If >30% drop at the same point, the content has a structural problem there.

**Acquisition**: Conversion rate, cost per acquisition, cart abandonment?
- Healthy CVR varies by channel (organic: 2-5%, paid: 1-3%, email: 5-15%)

**Revenue Health**: Refund rate, CLV, churn (subscriptions), NRR?
- Refund rate is the most honest quality signal. Target: < 5%.
- Refund rate > 10% = product-market fit problem, not just delivery quality.

### Canvas Output
Update `.claude/canvas/content-metrics.yml` with current measurements and `last_measured` timestamp.

---

## Part 5: AI Tool Assessment (v0.11.0)

For ai_tool products. Read `.claude/canvas/ai-tool-metrics.yml`.

### Producer-Side (quality & safety)

**Eval Frequency**: How often are prompts/models evaluated?
- Regular evaluation prevents quality drift

**Accuracy & Consistency**: Are eval scores stable or improving?

**Safety Score**: Red-team results -- are adversarial inputs handled?

**Bias Assessment**: Last assessed when? Any demographic gaps found?

**Version Cadence**: How often are prompt/model versions shipped?

**Regulatory Status**: EU AI Act risk classification current?

### Customer-Side (usage & retention)

**Time to First Value (TTFV)**: How quickly does a user get useful output after first access?
- Seconds (paste prompt, get result): excellent
- Minutes (configure API key, learn UI): acceptable
- Hours (training required): investigate onboarding friction

**Usage & Retention**: DAU, task success rate, retention (7-day, 30-day)?
- Task success rate < 70% = prompt/model quality issue
- Drop-off points: where do users abandon? (onboarding, first complex task, pricing wall)

**Revenue Health**: Refund rate, CLV, churn, NRR?
- Same benchmarks as content: refund rate target < 5%

### Canvas Output
Update `.claude/canvas/ai-tool-metrics.yml` with current measurements and `last_measured` timestamp.

---

## Part 6: Service Delivery Assessment (v0.11.0)

For service_offering products. Read `.claude/canvas/service-metrics.yml`.

### Producer-Side (delivery capacity & quality)

**Client Throughput**: How many clients/engagements per period?

**Delivery Lead Time**: Engagement start to delivery -- how long?
- Identify bottleneck: client feedback, research, production?

**Client Satisfaction**: NPS, CSAT, retention rate, referral rate?

**Repeatability**: Is the delivery workflow documented and templated? Score 1-5.

### Customer-Side (acquisition & revenue)

**Time to First Value (TTFV)**: How quickly does a client receive meaningful value after engaging?
- First deliverable or quick win within days: excellent
- Weeks before any tangible output: investigate onboarding process

**Acquisition**: Conversion rate, cost per acquisition, proposal win rate?

**Revenue Health**: Refund/dispute rate, CLV, churn (retainers), NRR?

### Canvas Output
Update `.claude/canvas/service-metrics.yml` with current measurements and `last_measured` timestamp.

---

## Theory Citations
- Forsgren, Humble, Kim: Accelerate (DORA metrics -- 5 metrics including Reliability and FDRT naming from 2024 report)
- LinearB: APEX Framework (AI-era delivery measurement)
- Beyer, Jones, Petoff, Murphy: Site Reliability Engineering (error budgets, SLIs/SLOs)
- Smart: BVSSH (holistic flow optimization — APEX X maps to Happier)
- Kim: Three Ways (Second Way — amplify feedback loops, detect shifting bottlenecks)
