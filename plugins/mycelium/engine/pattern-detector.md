# Pattern Emergence Engine

Automated detection of recurring patterns across cycle history. Turns individual learnings into systemic knowledge. This is double-loop learning (Argyris) — questioning the governing variables, not just correcting individual errors.

## How It Works

The pattern detector analyzes `canvas/cycle-history.yml` to surface:
1. **Correlation patterns** — "When X happens, Y follows"
2. **Anti-pattern signals** — "This keeps failing the same way"
3. **Success patterns** — "This approach consistently works"

It runs as part of `/retrospective` and `/diamond-assess`, not as a standalone process. Patterns are woven into existing workflows, not bolted on.

## Pattern Detection Rules

### Correlation Rules

These fire when cycle history shows a statistical pattern:

| Rule | Trigger | Action |
|------|---------|--------|
| **Perspective skip → regression** | >60% of leaves that skipped a trio perspective at L1/L2 later regressed at L3/L4 | Surface warning at L1/L2: "Historically, skipping [perspective] at this scale leads to regression later." |
| **Early spike → success** | Solutions with feasibility spikes at L3 have >2x higher final ICE accuracy | Recommend spikes earlier: "Data shows early spikes reduce late-stage surprises." |
| **Domain-specific effort** | A specific domain (e.g., ML, infrastructure) consistently takes >50% more effort than estimated | Adjust default ease score for that domain: "ML solutions historically take 1.5x estimated effort." |
| **Risk dimension blind spot** | One risk dimension is wrong >50% of the time | Flag at assessment time: "Feasibility estimates have been wrong in [X]% of past cycles. Consider a deeper spike." |

### Anti-Pattern Signals

These fire when the same failure mode recurs:

| Signal | Trigger | Action |
|--------|---------|--------|
| **Opportunity graveyard** | Same opportunity spawns >3 discarded leaves | Flag opportunity for re-evaluation: "This opportunity has produced 3+ failed solutions. The problem may be mis-framed. Consider re-running `/ost-builder` from research." |
| **Late discard pattern** | >50% of discards happen at Phase 7+ (delivery or later) | Flag pipeline weakness: "Most discards happen late. Earlier gates (ICE threshold, assumption testing) may need tightening." |
| **Confidence inflation** | Confidence scores consistently >0.2 higher than actual outcomes warrant | Flag calibration issue: "Confidence scores are systematically inflated. Review evidence standards." |
| **Single-perspective dominance** | >70% of Four Risks assessments show one perspective providing all evidence | Flag trio imbalance: "Engineering perspective is dominating risk assessments. Product and design evidence is thin." |
| **Correction recurrence** | Same correction logged 3+ times despite documented prevention | Auto-escalate: graduate the correction to a guardrail (draft G-XX entry in guardrails-core.md). The prevention strategy failed — the system needs a harder constraint, not another reminder. |

### Success Pattern Extraction

These identify what's working well:

| Pattern | Trigger | Action |
|---------|---------|--------|
| **Effective gate** | A specific gate catches >80% of issues that would have caused problems later | Document in `patterns.md`: "[Gate] is highly effective — keep it and potentially strengthen." |
| **Fast cycle domain** | A domain consistently completes cycles faster than average | Note for future planning: "Solutions in [domain] can be estimated at 0.7x typical effort." |
| **High-accuracy risk dimension** | A risk dimension is consistently well-estimated | Note calibration quality: "Value risk assessments are well-calibrated — maintain current methodology." |

## Minimum Data Requirements

Pattern detection requires sufficient data to be meaningful:

| Pattern Type | Minimum Cycles Required | Rationale |
|-------------|------------------------|-----------|
| Correlation rules | 10 completed cycles | Need enough data for >60% threshold to be meaningful |
| Anti-pattern signals | 5 completed cycles | Failure patterns surface faster |
| Success patterns | 15 completed cycles | Success requires more data to distinguish from luck |

Before minimum data is reached, the pattern detector reports: "Insufficient cycle data for pattern detection. [N] more cycles needed. Continue recording in cycle-history.yml."

## Integration Points

### `/retrospective`
After running the standard retrospective, check cycle-history.yml for any newly triggered pattern rules. Surface findings: "Pattern detected: [description]. This has happened [N] times. Recommendation: [action]."

### `/diamond-assess`
When assessing a diamond, check if any active anti-pattern signals apply to the current work. Surface relevant warnings from historical data.

### `patterns.md`
When a success pattern is confirmed (meets minimum data threshold), auto-suggest adding it to `.claude/memory/patterns.md` as a reusable insight.

### `corrections.md`
When an anti-pattern signal fires, auto-suggest adding a correction entry to `.claude/memory/corrections.md` with the systemic prevention rule.

## What This Does NOT Do

- **Does not auto-act.** Pattern detection surfaces findings — humans and the lead agent decide what to do.
- **Does not replace judgment.** Patterns are heuristics, not rules. A pattern that fires in 60% of cases is wrong 40% of the time.
- **Does not require perfect data.** Missing fields in cycle records are skipped, not errored. The detector works with whatever data exists.

## Theory Citations

- Argyris: Double-loop learning (questioning governing variables, not just outputs)
- Senge: The Fifth Discipline (systems thinking, seeing patterns across events)
- Meadows: Thinking in Systems (leverage points — patterns reveal where to intervene)
- Deming: System of Profound Knowledge (statistical thinking applied to process improvement)
