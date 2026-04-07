# Mycelium Feedback Loop System

Feedback loops are how Mycelium learns, corrects, and improves. They operate at four speeds, mapped to Argyris's learning levels and Meadows's leverage points.

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

**Health signal**: If confidence isn't increasing after 3+ incremental loops on the same diamond, escalate to Loop 3 (the assumptions may be wrong).

**Cadence**: After every diamond phase transition and every delivery increment.

### Loop 3: Strategic (Double-Loop -- "Question the Assumptions")
**Speed**: Weekly to monthly. Fires on schedule.
**Learning type**: Double-loop (Argyris) -- question the governing variables, not just the outputs.
**Meadows leverage**: Level 7-5 (feedback loop gain, information flows, rules).

| Signal | Source | Action | Mechanism |
|--------|--------|--------|-----------|
| BVSSH dimension declining | /bvssh-check | Investigate root cause, adjust strategy | Monthly BVSSH review |
| North Star metric flat | Product metrics | Re-evaluate opportunities, consider pivot | Monthly North Star review |
| DORA metrics degrading | /dora-check | Investigate delivery bottlenecks | Per-delivery-cycle DORA check |
| Confidence stagnant | OST stagnation | Re-evaluate opportunity, consider regression | Diamond stale detection |
| Competitive landscape shift | Market intelligence | Update Wardley map, reassess positioning | Monthly /wardley-map review |
| Win/loss pattern emerging | GTM feedback | Adjust positioning or product direction | /launch-tier -> L2 feedback |
| Corrections patterns repeating | corrections.md themes | Graduate to guardrails or anti-patterns | Corrections pruning |

**Health signal**: If strategic corrections don't improve the trajectory after 2+ cycles, escalate to Loop 4 (the framework itself may need adjustment).

**Cadence**:
- Weekly: /diamond-assess + corrections review
- Monthly: /bvssh-check + /wardley-map + stale diamond cleanup
- Per-delivery: /dora-check + /retrospective

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
| BVSSH Safer declining while Sooner improving | "Trading safety for speed. This is the BVSSH anti-pattern Smart warns about." | Run /bvssh-check, pause delivery to address safety |

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

**"When a measure becomes a target, it ceases to be a good measure."** (Goodhart)

Every metric in Mycelium must have a **counter-metric** to prevent gaming:

| Metric | Risk if Gamed | Counter-Metric |
|--------|--------------|---------------|
| Deployment frequency | Deploy empty changes | Change failure rate + actual value delivered |
| Lead time | Skip reviews/testing | Change failure rate + defect density |
| Confidence score | Self-inflate without evidence | Evidence TYPE must match level (Gilad's meter) |
| Test coverage | Write meaningless tests | Mutation testing score or defect leakage |
| Diamond velocity | Rush through gates | Regression rate (how often do diamonds regress?) |
| Correction count | Log trivial corrections | Correction IMPACT (did prevention rules prevent recurrence?) |

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
| /retrospective | Loop 2-3 | No change needed |
| DORA metrics | Loop 2-3 | **Enhanced**: add trend fields for trajectory |
| BVSSH check | Loop 3 | **Enhanced**: add trend fields for trajectory |
| North Star | Loop 3 | **Enhanced**: add trend fields + Goodhart warning |
| /launch-tier | Loop 3 | **Enhanced**: L5->L2 feedback prompt |

## For the Agent

When reporting feedback loop status (via `/feedback-review`), always:
1. Report in plain language using status-translations.md
2. Show trajectory (improving/stable/declining), not just current state
3. Flag any regression warning triggers that are active
4. Suggest specific skills for any overdue loops
5. Include Goodhart's Law check: is any metric improving while its counter-metric declines?
