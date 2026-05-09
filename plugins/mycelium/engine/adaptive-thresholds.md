# Adaptive Thresholds

Replace hardcoded thresholds with calibrated ones that improve as Mycelium accumulates cycle data. All thresholds start at sensible defaults and adjust based on historical outcomes.

## Threshold Registry

All configurable thresholds live in `canvas/thresholds.yml`. Each threshold has:
- A **default value** (used until calibration kicks in)
- A **calibrated value** (adjusted from cycle data, when available)
- A **calibrated_at** timestamp
- A **based_on_n** sample size (how many cycles informed this calibration)
- A **minimum_n** before calibration overrides the default

## Thresholds

### ICE Advance Threshold

**What it controls**: The minimum ICE score for a leaf to advance from Phase 3 (ICE Scoring) to Phase 5 (GIST Entry). Below this, the leaf is archived.

| Parameter | Value |
|-----------|-------|
| Default | 100 (I×C×E) |
| Calibration rule | Track the ICE scores of leaves that were launched and succeeded vs those that failed. Adjust threshold to the score where historical success rate exceeds 50%. |
| Minimum N | 10 completed cycles |
| Adjustment bounds | 50-300 (never below 50, never above 300) |

**Example**: After 15 cycles, data shows leaves with ICE ≥ 120 succeeded 70% of the time, while leaves with ICE 80-119 succeeded only 30%. Threshold adjusts to 120.

### Confidence Calibration

**What it controls**: Whether stated confidence scores match actual outcomes.

| Parameter | Value |
|-----------|-------|
| Default | Assume calibrated (no adjustment) |
| Calibration rule | Track confidence at time of decision vs actual outcome. If confidence 0.7 items succeed only 40% of the time, all confidence values need systematic deflation. |
| Minimum N | 10 completed cycles |
| Adjustment | Calibration factor applied to all confidence values (e.g., 0.85 = deflate by 15%) |

**Example**: After 20 cycles, confidence 0.7+ items succeed 55% of the time (should be ~70%). Calibration factor = 0.55/0.70 = 0.79. Surface warning: "Confidence scores are systematically optimistic. Consider applying a 0.8x correction factor."

### WIP Limit Adjustment

**What it controls**: Recommended working WIP per scale.

| Parameter | Value |
|-----------|-------|
| Default | Per diamond-rules.md WIP table |
| Calibration rule | If leaves are consistently bottlenecked at a specific lifecycle phase (>3 leaves waiting at the same phase), suggest WIP reduction upstream. If flow is smooth (no phase has >1 waiting leaf), WIP can be maintained or cautiously increased. |
| Minimum N | 5 concurrent cycles observed |
| Adjustment | NUDGE only — WIP changes require human approval |

### Evidence Staleness Threshold

**What it controls**: When evidence is flagged as stale (from evidence-decay.md).

| Parameter | Value |
|-----------|-------|
| Default | Per evidence-decay.md category table |
| Calibration rule | Track how often refreshed evidence actually changed the conclusion. If evidence refreshed at 90 days rarely changes anything, threshold can be extended. If evidence refreshed at 90 days frequently reveals changed conditions, threshold should be shortened. |
| Minimum N | 10 refresh events per category |
| Adjustment bounds | 50%-200% of default (never less than half, never more than double) |

### Bakeoff ICE Delta

**What it controls**: The ICE score difference that constitutes a "clear winner" in leaf bakeoff (from leaf-bakeoff.md).

| Parameter | Value |
|-----------|-------|
| Default | 20% delta |
| Calibration rule | Track bakeoff outcomes. If leaves within 20% delta frequently produce the same outcome (both succeed or both fail), the delta is too narrow — widen it. If leaves just above 20% delta frequently diverge in outcome, the delta is well-calibrated. |
| Minimum N | 5 completed bakeoffs |
| Adjustment bounds | 10%-40% |

## `canvas/thresholds.yml` Format

```yaml
schema_version: 1

thresholds:
  ice_advance:
    default: 100
    calibrated: null
    calibrated_at: null
    based_on_n: 0
    minimum_n: 10
    bounds: {min: 50, max: 300}
    
  confidence_calibration:
    default: 1.0  # No deflation
    calibrated: null
    calibrated_at: null
    based_on_n: 0
    minimum_n: 10
    bounds: {min: 0.5, max: 1.2}
    
  evidence_staleness:
    user_needs: {default_days: 90, calibrated_days: null, based_on_n: 0, minimum_n: 10}
    competitive: {default_days: 90, calibrated_days: null, based_on_n: 0, minimum_n: 10}
    strategic: {default_days: 180, calibrated_days: null, based_on_n: 0, minimum_n: 10}
    feasibility: {default_days: 120, calibrated_days: null, based_on_n: 0, minimum_n: 10}
    delivery_metrics: {default_days: 30, calibrated_days: null, based_on_n: 0, minimum_n: 10}
    
  bakeoff_delta:
    default: 0.20
    calibrated: null
    calibrated_at: null
    based_on_n: 0
    minimum_n: 5
    bounds: {min: 0.10, max: 0.40}

last_calibrated: null
```

## Calibration Protocol

Calibration runs as part of `/framework-health` (quarterly or every 20 cycles):

1. Read `canvas/cycle-history.yml`
2. For each threshold with `based_on_n >= minimum_n`:
   - Apply calibration rule
   - If new calibrated value differs from current by >10%, update
   - Log calibration change in decision-log.md
3. For thresholds with insufficient data: report "N more cycles needed for [threshold]"

**Safety**: Calibrated values have bounds. The system cannot set ICE threshold to 0 or confidence deflation to 0.1. Bounds prevent runaway calibration.

## Theory Citations

- Gilad: Evidence Guided (confidence calibration from actual outcomes)
- Deming: Statistical process control (thresholds adjusted from data, not opinion)
- Meadows: Thinking in Systems (parameters as the lowest-leverage but easiest intervention point)
- Kahneman: Thinking, Fast and Slow (systematic miscalibration of predictions)
