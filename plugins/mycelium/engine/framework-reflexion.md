# Framework Reflexion

Mycelium evaluates its own process effectiveness. This is triple-loop learning (Argyris) — questioning the learning system itself, not just the outputs or governing variables.

## What It Measures

Five health dimensions that tell you whether the framework is getting better at its job:

### 1. Cycle Velocity
**Question**: Are diamonds completing faster over time?
**Signal**: Average time from diamond creation to completion, tracked per scale.
**Healthy**: Velocity improves or stays stable (learning curve effect).
**Unhealthy**: Velocity degrades — the framework may be adding overhead without value.
**Source**: `canvas/cycle-history.yml` timestamps.

### 2. Discard Rate Trend
**Question**: Are fewer leaves being discarded late in the pipeline?
**Signal**: Average phase at which leaves are discarded, tracked over rolling windows.
**Healthy**: Discards shift earlier (Phase 3-4 instead of Phase 7-9). Early filtering saves effort.
**Unhealthy**: Late discards persist or increase — gates are not catching problems early enough.
**Source**: `canvas/cycle-history.yml` discard_phase and `canvas/archived-solutions.yml`.

### 3. Confidence Calibration
**Question**: Are high-confidence predictions actually succeeding?
**Signal**: Correlation between stated confidence and actual outcomes.
**Healthy**: Confidence 0.7 items succeed ~70% of the time (well-calibrated).
**Unhealthy**: Confidence is systematically optimistic or pessimistic.
**Source**: `canvas/cycle-history.yml` predicted vs actual + `canvas/thresholds.yml` calibration data.

### 4. Gate Effectiveness
**Question**: Which gates are catching real issues vs creating busywork?
**Signal**: Per-gate hit rate — how often does each gate actually block a problematic transition vs rubber-stamp a healthy one?
**Healthy**: Gates catch real issues and have a meaningful rejection rate (not 0% and not 100%).
**Unhealthy**: A gate always passes (rubber stamp) or always fails (too strict) — neither adds value.
**Source**: Diamond state history in `diamonds/active.yml` theory_gates status.

### 5. Regression Rate
**Question**: How often do diamonds regress? Is it decreasing?
**Signal**: Percentage of diamonds that regress at least once, tracked per quarter.
**Healthy**: Regression rate decreases over time (evidence quality improving, earlier filtering working).
**Unhealthy**: Regression rate stays flat or increases — upstream discovery isn't improving.
**Source**: `diamonds/active.yml` phase history, decision-log.md regression entries.

## `/framework-health` Skill

See `.claude/skills/framework-health/SKILL.md` for the skill definition that generates the dashboard.

## Cadence

- **Quarterly**: Full framework health review (all 5 dimensions + threshold calibration)
- **Every 20 completed cycles**: Trigger interim review if cycle volume is high
- **On demand**: Run `/framework-health` any time process friction is suspected

## What To Do With Results

| Finding | Action |
|---------|--------|
| Velocity degrading | Audit: are gates adding overhead? Are skills too complex? Consider simplifying. |
| Late discards increasing | Tighten earlier gates (ICE threshold, assumption testing requirements). |
| Confidence miscalibrated | Apply calibration factor from adaptive-thresholds.md. Review evidence standards. |
| Gate always passes | Consider demoting from REVIEW to NUDGE, or removing if truly useless. |
| Gate always fails | Consider if the criteria are too strict, or if the problem is systemic (not gate-fixable). |
| Regression rate increasing | Investigate: is discovery quality declining? Are assumptions being tested? |

## Goodhart's Law Protection

Framework health metrics are themselves subject to Goodhart's Law. Counter-metrics:

| Metric | Counter-Metric |
|--------|---------------|
| Cycle velocity (target: faster) | Quality of outcomes (are faster cycles producing worse results?) |
| Discard rate (target: earlier discards) | False positive rate (are good ideas being killed too early?) |
| Confidence calibration (target: accurate) | Decision speed (is over-calibration causing analysis paralysis?) |
| Gate effectiveness (target: meaningful rejection rate) | Flow speed (are effective gates slowing delivery unacceptably?) |
| Regression rate (target: decreasing) | Innovation rate (are fewer regressions because fewer risks are being taken?) |

## Theory Citations

- Argyris: Triple-loop learning (learning how to learn)
- Meadows: Thinking in Systems (leverage points for system change)
- Senge: The Fifth Discipline (the learning organization)
- Forsgren: Accelerate (measuring and improving organizational capabilities)
- Goodhart/Strathern: "When a measure becomes a target, it ceases to be a good measure" (Strathern's 1997 generalization of Goodhart's 1975 law; counter-metrics)
