# Mycelium Feedback Loop System

Feedback loops are how Mycelium learns, corrects, and improves. They operate at four speeds, mapped to Argyris's learning levels and Meadows's leverage points.

## Kim's Three Ways of DevOps (The DevOps Handbook, 2016; Wiring the Winning Organisation, 2023)

The four loop speeds implement Kim's Three Ways:

- **First Way — Flow** (left-to-right): Optimize the flow of work from development to operations to the customer. Small batches, WIP limits, reduce handoffs. Loops 1-2 support flow by catching errors early and keeping increments small.
- **Second Way — Feedback** (right-to-left): Amplify feedback loops so problems are detected and corrected quickly. The product-outcome→discovery edge is wired through the DoD `measure` block (`/define-done`): `/metrics-pull` checks target-vs-actual after ship and routes the result back to the opportunity (met → confidence up; missed → reopen discovery), with a `session-start` nudge when a shipped diamond's outcome-check is overdue. **Honest scope:** for outcomes with an automated metric source this is a real closed loop; for manual/interview-based outcomes — many early product outcomes, and any that depend on real users experiencing the thing — the loop is *prompted, not automated*: the harness surfaces the overdue check, the human supplies the lived outcome. DORA/delivery metrics flow back into feasibility estimates. Loops 2-3 are the primary feedback amplifiers.
- **Third Way — Continual Learning and Experimentation**: Create a culture of experimentation, learning from failure (blameless post-mortems), and practice (repetition). Loop 4 is where the system questions and transforms itself.

*In "Wiring the Winning Organisation" (2023), Kim & Spear reframe the Three Ways as three mechanisms: **Slowification** (move problem-solving from execution to planning), **Simplification** (reduce complexity in processes), and **Amplification** (make problems visible fast). These are complementary lenses on the same principles.*

## The Four Loop Speeds

### Loop 1: Immediate (Single-Loop -- "Fix the Error")
**Speed**: Seconds to minutes. Fires on every action.
**Learning type**: Single-loop (Argyris) -- correct the deviation without questioning assumptions.
**Meadows leverage**: Level 12-10 (parameters, buffers).

| Signal | Source | Action | Mechanism |
|--------|--------|--------|-----------|
| Validation failure | Test/lint/typecheck | Diagnose root cause, fix, retry | Reflexion loop + PostToolUseFailure hook |
| Secret detected in code | PreToolUse content scan | Block write, use env vars | gate.sh secret detection |
| Past mistake pattern match | corrections.md | Apply prevention rule proactively | Preflight stamp + corrections.md |
| Accessibility violation | Automated a11y scan | Fix before proceeding | /a11y-check + PostToolUse nudge |

**Health signal**: If the same immediate correction fires repeatedly, escalate to Loop 2 (it's a pattern, not a one-off).

### Loop 2: Incremental (Single-Loop -- "Improve the Process")
**Speed**: Hours to days. Fires per diamond phase or delivery increment.
**Learning type**: Single-loop with memory -- fix and remember.
**Meadows leverage**: Level 9-8 (delays, balancing feedback).

| Signal | Source | Action | Mechanism |
|--------|--------|--------|-----------|
| Diamond phase complete | Phase transition | Capture learnings, update patterns | diamond-progress learning capture |
| Delivery increment done | DoD satisfied | DORA metrics, delivery journal, retrospective | /retrospective skill |
| Assumption test result | Experiment outcome | Update ICE scores, confidence levels | /ice-score, /canvas-update |
| User interview complete | Research session | Update OST, user needs, JTBD | Interview snapshot -> canvas |
| Code review findings | Peer review | Update patterns or corrections | Manual -> corrections.md |
| Corrections accumulating | 3+ corrections logged | Trend analysis, graduation candidates | /corrections-audit |

**Health signal**: If confidence isn't increasing after 3+ incremental loops on the same diamond, escalate to Loop 3 (the assumptions may be wrong). If the same correction category appears 3+ times, run `/corrections-audit` to check for guardrail graduation.

**Cadence**: After every diamond phase transition and every delivery increment.

### Loop 3: Strategic (Double-Loop -- "Question the Assumptions")
**Speed**: Weekly to monthly. Fires on schedule.
**Learning type**: Double-loop (Argyris) -- question the governing variables, not just the outputs.
**Meadows leverage**: Level 7-5 (feedback loop gain, information flows, rules).

| Signal | Source | Action | Mechanism |
|--------|--------|--------|-----------|
| BVSSH dimension declining | /bvssh-check | Investigate root cause, adjust strategy | Monthly BVSSH review |
| North Star metric flat | /metrics-pull snapshot trend | Re-evaluate opportunities, consider pivot | Weekly /metrics-pull + monthly North Star review |
| External traction stalling (L0/L1/L2/L5) | /metrics-pull snapshot deltas (stars, views, conversion, review velocity) | Investigate: new channels, messaging, or reposition | Weekly /metrics-pull, compare against prior snapshot |
| Unexplained referrer / market signal | /metrics-pull "unexplained signals" flag | Investigate source (HN, press, viral) before acting on it | Per /metrics-pull run |
| DORA metrics degrading | /dora-check | Investigate delivery bottlenecks | Per-delivery-cycle DORA check |
| Confidence stagnant | OST stagnation | Re-evaluate opportunity, consider regression | Diamond stale detection |
| Competitive landscape shift | Market intelligence | Update Wardley map, reassess positioning | Monthly /wardley-map review |
| Win/loss pattern emerging | GTM feedback | Adjust positioning or product direction | /launch-tier -> L2 feedback |
| Corrections patterns repeating | corrections.md themes | Graduate to guardrails or anti-patterns | Corrections pruning |

**Health signal**: If strategic corrections don't improve the trajectory after 2+ cycles, escalate to Loop 4 (the framework itself may need adjustment).

**Cadence**:
- Weekly: /diamond-assess + corrections review + /metrics-pull (L0/L1/L2/L5 diamonds)
- Monthly: /bvssh-check + /wardley-map + stale diamond cleanup
- Per-delivery: /dora-check + /retrospective
- On launch: /metrics-pull 24-48h after launch to capture the bump, then weekly for the first month

### Loop 4: Transformative (Triple-Loop -- "Transform the System")
**Speed**: Quarterly. Fires on evaluation cycles.
**Learning type**: Triple-loop (Argyris) -- question the learning system itself.
**Meadows leverage**: Level 4-2 (self-organization, goals, paradigms).

| Signal | Source | Action | Mechanism |
|--------|--------|--------|-----------|
| Eval pass rate trending down | /eval-runner history | Optimize instructions, adjust thresholds | /prompt-optimizer |
| Skills consistently underutilized | Session patterns | Improve skill surfacing, adjust gate suggestions | Theory gate skill suggestions |
| Guardrails being bypassed | Escape hatch log analysis | Adjust process weight for project type | Canvas guidance recalibration |
| Purpose evolved | Organizational change | Re-interview, refresh L0 diamond | /interview re-run |
| Framework friction | User feedback | Adjust Mycelium itself | CLAUDE.md / skill modifications |

**Cadence**: Quarterly North Star review + eval benchmark + strategic landscape refresh.

## Regression Warning Triggers

When feedback signals indicate the current direction is wrong, the system should warn (not auto-regress):

| Signal Pattern | Warning | Suggested Action |
|---------------|---------|-----------------|
| DORA metrics declined 2+ consecutive checks | "Delivery health declining. Consider whether the L3 solution design needs revisiting." | Run /diamond-assess, consider L4->L3 regression |
| Confidence hasn't increased in 3+ GIST steps | "Evidence isn't building. The opportunity framing may be wrong." | Run /devils-advocate, consider L3->L2 regression |
| NPS/CSAT dropping post-launch | "Users aren't happy with what was delivered." | Capture feedback, spawn new L2 opportunity diamond |
| Same correction logged 3+ times | "This keeps happening. The prevention rule isn't working." | Graduate correction to guardrail or anti-pattern |
| AI rework rate > 30% | "AI-generated code is being rewritten too frequently." | Review AI prompt quality, consider more specific instructions |
| Review wait time increasing while coding speed increases | "THE SHIFTING BOTTLENECK (APEX): AI is generating code faster but the review pipeline can't keep up." | Add reviewers, automate review gates, reduce PR size |
| AI PR acceptance rate declining | "AI suggestions are becoming less useful. Context may be stale." | Refresh corrections.md, update canvas context, re-run /delivery-bootstrap |
| BVSSH Safer declining while Sooner improving | "Trading safety for speed. This is the BVSSH anti-pattern Smart warns about." | Run /bvssh-check, pause delivery to address safety |
| SRE error budget depleted | "Reliability budget consumed. Feature work should pause until budget recovers." | Run /dora-check SRE section, enforce error budget policy, focus on stability |
| Same bottleneck persists after 2+ improvement attempts | "FIX THAT FAILED (Senge): The fix addressed symptoms, not root cause. The bottleneck returns." | Apply ToC Five Focusing Steps (Goldratt): Identify -> Exploit -> Subordinate -> Elevate -> Repeat. Map the value stream to find the real constraint. |

## DORA → Feasibility Feedback Loop

DORA metrics from completed deliveries should feed back into feasibility risk assessments for future solutions. This closes the loop between "how hard we thought it would be" and "how hard it actually was."

| DORA Signal | Feedback Into | Action |
|-------------|---------------|--------|
| Deploy frequency dropped after shipping solution X | Feasibility risk assessment for similar solutions | Increase default feasibility risk for solutions in the same domain/pattern |
| Lead time increased for solution type Y | ICE ease scoring | Reduce ease scores for similar solution types |
| Change failure rate high for pattern Z | Four Risks feasibility dimension | Flag pattern Z as high feasibility risk in future assessments |
| FDRT acceptable for solution W | Feasibility risk positive signal | Note that this solution type is operationally manageable |

**Mechanism**: After each `/dora-check`, compare actual delivery metrics with the original ICE ease score and feasibility risk assessment. Log significant deviations (>2 points on ICE ease scale) in `corrections.md` as calibration data.

**Skill integration**: `/dora-check` surfaces this comparison. The reverse direction is *aspirational* — `/ice-score` does not yet read DORA calibration data before scoring ease. `Gated by:` an ice-score step that greps corrections.md for "DORA calibration:" entries matching the solution shape — not yet built. Until then this loop runs manually: a human carries the calibration signal from `/dora-check` output into the next `/ice-score`.

## The L5 -> L2 Feedback Loop

When market/launch feedback reveals new user needs or invalidates assumptions:

```
L5 Market (launch complete)
  |
  |-- Capture market signals (user feedback, adoption data, win/loss)
  |-- Evaluate: Do signals confirm or contradict L2 opportunity assumptions?
  |
  |-- If confirms: Continue. Update confidence scores.
  |-- If contradicts: Spawn new L2 Opportunity diamond with market evidence.
  |     The new L2 diamond starts with market data as evidence (not from scratch).
  |
  This closes the loop: Market -> Discovery -> Solution -> Delivery -> Market
```

This is triggered by `/launch-tier` completion and `/retrospective` after market diamonds.

## Goodhart's Law Protection

**"When a measure becomes a target, it ceases to be a good measure."** (Strathern's 1997 generalization, commonly attributed to Goodhart. Goodhart's 1975 original: "Any observed statistical regularity will tend to collapse once pressure is placed upon it for control purposes.")

Every metric in Mycelium must have a **counter-metric** to prevent gaming:

| Metric | Risk if Gamed | Counter-Metric |
|--------|--------------|---------------|
| Deployment frequency | Deploy empty changes | Change failure rate + actual value delivered |
| Lead time | Skip reviews/testing | Change failure rate + defect density |
| Confidence score | Self-inflate without evidence | Evidence TYPE must match level (adapted from Gilad's Confidence Meter) |
| Test coverage | Write meaningless tests | Mutation testing score or defect leakage |
| Diamond velocity | Rush through gates | Regression rate (how often do diamonds regress?) |
| Correction count | Log trivial corrections | Correction IMPACT (did prevention rules prevent recurrence?) |
| AI coding speed | Generate code without review capacity | Review wait time + AI rework rate (APEX shifting bottleneck) |
| AI PR volume | Flood the review pipeline | AI PR acceptance rate + merge time vs human (APEX) |
| Evidence source count | Self-inflate with desk research only | External evidence ratio (external_human + external_data vs total sources) |
| Conversion rate | Optimize landing page at expense of product quality | Refund rate + completion rate (are converters actually satisfied?) |
| Refund rate (target low) | Restrict refund policy instead of improving quality | NPS + repeat purchase rate (are customers genuinely happy or just trapped?) |
| TTFV (target low) | Strip onboarding to raw access without guidance | Task success rate + completion rate (fast access but confused users?) |

**Rule**: Never optimize a single metric in isolation. Always check its counter-metric. If both move in the right direction, the improvement is real.

## Connecting to Existing Mycelium Mechanisms

| Mycelium Mechanism | Loop Speed | Enhancement Needed |
|---|---|---|
| corrections.md | Loop 1-2 | Add `trend` tracking (recurring patterns) |
| patterns.md | Loop 2 | No change needed |
| Reflexion loop | Loop 1 | No change needed |
| PostToolUseFailure hook | Loop 1 | No change needed |
| PostToolUse nudge | Loop 1 | No change needed |
| Stop check | Loop 2-3 | **Enhanced**: check for overdue strategic loops |
| SessionStart | Loop 3 | **New**: remind about overdue strategic reviews |
| Eval benchmarks | Loop 4 | Add trend comparison (current vs last baseline) |
| Prompt optimization | Loop 4 | No change needed |
| Cycle history | Loop 2 | Records every completed/discarded leaf for calibration |
| Pattern detector | Loop 3 | Surfaces systemic patterns from cycle data |
| Adaptive thresholds | Loop 3-4 | Calibrates ICE threshold, confidence factor from historical data |
| Framework reflexion | Loop 4 | Quarterly self-assessment of process effectiveness |
| Evidence decay | Loop 2-3 | Degrades confidence on stale evidence, triggers refresh |
| /retrospective | Loop 2-3 | No change needed |
| DORA metrics | Loop 2-3 | **Enhanced**: add trend fields for trajectory |
| BVSSH check | Loop 3 | **Enhanced**: add trend fields for trajectory |
| North Star | Loop 3 | **Enhanced**: add trend fields + Goodhart warning |
| /launch-tier | Loop 3 | **Enhanced**: L5->L2 feedback prompt |

## Vendor-Shipped Agent Loops on the Same Axis

As of 2026-04, vendor-shipped agent loops have appeared (OpenAI Codex CLI 0.128.0 ships `/goal` — user sets a goal; agent loops with two exit conditions: goal-evaluation success OR token-budget exhaustion; implementation = injected continuation/budget-limit prompts at end-of-turn). All such loops sit on the same conceptual axis as Mycelium's gates: *evaluate-and-continue with success-criterion + resource-budget exits.* What differs is **scope** and **criterion richness**.

| Scope | Codex `/goal` | Mycelium |
|---|---|---|
| Per-turn | — | Hooks (PostToolUse, SessionStart, Stop) |
| Per-skill-invocation | — | `/reflexion` (max 3 iterations) |
| Per-task | `/goal` (continuation prompt + budget_limit prompt) | — |
| Per-phase-transition | — | Theory gates (evidence, four risks, JTBD, cynefin, bias, security, privacy, BVSSH, etc.) |
| Per-diamond completion | — | Definition of Done |

Two structural differences matter:

1. **Criterion richness.** Codex `/goal` evaluates one criterion (goal text vs current state). Mycelium gates evaluate multi-criterion stacks per phase, plus DoD's executable checklist at L4 completion.
2. **Exit semantics.** Codex `/goal` exits the loop ("done"). Mycelium gates *progress* the loop to the next phase — there is no "done" until DoD is satisfied; diamonds can also *regress* on bad evidence (Codex `/goal` has no regression mechanism).

**Why this framing matters.** The loop shape (evaluate-then-continue with success + budget exits) is now table stakes — vendors will continue to ship single-loop variants. Mycelium's differentiation is NOT "we have a self-evaluating loop." It is the **multi-criterion theory-gate stack** at multiple scopes plus the **regression mechanism**. When explaining Mycelium against vendor-shipped loops, anchor on these two.

**What Mycelium borrowed from Codex's `/goal` implementation** (logged 2026-05-03 — see `${CLAUDE_PLUGIN_ROOT}/harness/security-trust.md#prompt-injection-defense-for-user-supplied-content` and `${CLAUDE_PLUGIN_ROOT}/skills/definition-of-done/SKILL.md#completion-audit-anti-bias-clauses`):
- Untrusted-content wrapping convention for user-supplied text in skill prompts
- Anti-bias clauses in the DoD completion audit (don't trust intent / partial progress / elapsed effort / plausible-final-answer)

The third pattern (per-task token-budget telemetry surfaced into the prompt) was deliberately not borrowed — Mycelium's failure modes around constraints are process-cliff shaped, not budget-blow shaped, so the cost/benefit doesn't justify infrastructure for an unproven failure (see opportunities.yml#opp-001 for the discipline applied to a similar deferred case).

## Work-Mode Mix (named 2026-05-10)

Mycelium recognizes that not all framework-improvement work fits into delivery / discovery / strategy / market modes. A fifth shape exists, made legible 2026-05-10:

- **Lived-friction-triggered**: a specific Mycelium failure surfaced and the work directly fixes it. Highest-confidence trigger class. Example: v0.23.3 bare-path sweep (the `/mycelium:metrics-pull` failure surfaced 30 sites of bare-path drift; the fix is structurally bounded by the trigger).
- **Research-while-waiting** (sometimes "research-while-here"): external feedback loops are blocked but internal-mechanism work is fruitful. Gap analysis, citation backfills, doc restructures, anti-pattern enrichments. The work is real; the trigger is opportunity, not failure. Example: v0.23.2 (CBI cognitive-bias citations), v0.23.4 (lawsofsoftwareengineering 7 citations), v0.23.5 (context-rot doc + citation backfills).
- **Maintenance-housekeeping**: version drift fixes, mechanical sweeps, hygiene. Example: v0.21.1 (plugin.json drift + Check 30).
- **Scheduled-discipline**: recurring audit (e.g., quarterly `/mycelium:framework-health`) graduating accumulated candidates.

Different rules apply per mode:

| Mode | When fine | When risky |
|---|---|---|
| Lived-friction-triggered | Always — the trigger justifies the work | If the fix scope creeps past what the trigger actually surfaced |
| Research-while-waiting | When it produces real research artifacts that survive attribution discipline | When session-velocity (multiple bumps in one session) extends one genuine trigger into a graduation streak via consistency rather than per-graduation attribution — meta-instance of anti-pattern #7 |
| Maintenance-housekeeping | Always — small, mechanical | When a "small fix" is actually a behavior change in disguise |
| Scheduled-discipline | At the scheduled cadence | When ad-hoc invocations replace the schedule's discipline |

Each version-line summary in CLAUDE.md should include the dominant attribution label (most graduations are mixed; pick the one that explains ≥60% of the work). `/mycelium:corrections-audit` can flag streaks of one type or unusual mode-shifts. `/mycelium:framework-health` can quarterly-review whether the mode mix has been healthy: too much lived-friction-triggered without any research-while-waiting suggests reactive-only operation; too much research-while-waiting without any lived-friction-triggered suggests the framework isn't being exercised against real workloads.

The category itself is honest naming of what was happening 2026-05-08 → 2026-05-10 anyway: 9 mechanism graduations in 9 days, mostly during a 6-8 week external-feedback-wait window. Naming the mode lets the framework defend it as legitimate AND surface its specific failure modes (graduation-velocity, attribution drift) cleanly. Source: 2026-05-10 in-conversation surfacing during Drew/Simon outreach session; corrections.md entry of same date for the meta-instance.

## For the Agent

When reporting feedback loop status (via `/feedback-review`), always:
1. Report in plain language using status-translations.md
2. Show trajectory (improving/stable/declining), not just current state
3. Flag any regression warning triggers that are active
4. Suggest specific skills for any overdue loops
5. Include Goodhart's Law check: is any metric improving while its counter-metric declines?
