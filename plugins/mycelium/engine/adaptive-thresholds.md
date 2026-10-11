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

### ICE Sequencing Reference (RETIRED in 0.319.0)

> **Why this note exists.** Until 0.319.0 this section defined a threshold on the ICE total,
> `ice_advance` in `canvas/thresholds.yml`: default 100, adjusted from cycle data, bounds 50-300.
> **It is retired. There is no threshold on an ICE total anywhere in Mycelium.** The note stays so
> a reader who meets the key in an older `thresholds.yml`, canvas or decision log knows what it was
> and why it went.

**What it was, in three stages.**

1. Until 2026-07-01, an advancement gate: `minimum ICE to advance, below this the leaf is
   archived`. Removed in v0.54.0 because it is scoring-for-selection, which Torres cautions
   against. `leaf-lifecycle.md` Phase 5 states the actual gate: **the riskiest assumption has a
   recorded test verdict of `validated`**, and a leaf is archived only when that assumption is
   **invalidated**, never by ICE. The correction reached `theories.md` and `leaf-lifecycle.md` and
   did not reach this file for four weeks (corrected here in v0.71.0), during which an agent
   reading here would have archived leaves on a score.
2. From v0.71.0 to 0.318.x, a "sequencing reference": the same number, 100, said to order leaves
   that had already passed Phase 5, with a calibration rule (adjust it "to the score where
   historical success rate exceeds 50%") and an example that moved it to 120.
3. Since 0.319.0, nothing. The number, its bounds, its calibration rule and its example are gone.

**Why it was retired.**

- **No source gives an ICE total a threshold, or any meaning on its own.** Gilad: *"The scores
  themselves are meaningless — they’re just a way to compare ideas, but sorting ideas by ICE scores
  gives us an order of priority."* (*ICE Done Right*, p. 4). Ellis: *"The score is to be used for
  relative prioritization and will not be perfect."* (Ellis & Brown, *Hacking Growth*, ch. 4), and
  his book warns *"against tossing away all ideas that don’t have high scores"* (same chapter).
  Tuning a cutoff on the score against later outcomes is described in none of the twelve sources
  read for the 2026-10-11 review, to the extent each was read (the ICE sections of both books in
  full, the rest of both books by keyword search).
- **The number never fitted the arithmetic.** Under the average `/mycelium:ice-score` used from
  0.229.0 to 0.318.x the largest possible score is 10, so 100 could not be reached. Under Gilad's
  product with his Confidence Meter, which the skill uses since 0.319.0, the totals in his own
  ebook examples are 27, 87.5 and 90 (*ICE Done Right*, pp. 5 and 7).

**What does the work instead.**

- **Order among leaves** is the ranking itself, read as a hint and always with its three factors:
  `/mycelium:ice-score` Step 3. A leaf that ranks low is sequenced later and stays on the tree
  (parked); it is not archived.
- **Whether a leaf moves on** is the Phase 5 gate above (the assumption-test verdict).
- **The one cutoff the literature has is on Confidence, before delivery**: *"With most ideas you
  want to reach at least medium-high confidence levels (3.0+ on the confidence scale) before you
  switch into delivery mode, and with bigger or riskier ideas you should go further."* (Gilad,
  *Evidence-Guided*, ch. 4). Mycelium already holds it as the L4 entry lock
  (`scripts/scale_locks.py`; `diamond-rules.md`, the entry locks). It is not a threshold in this
  file and is not calibrated.

**If your `thresholds.yml` still has `ice_advance`:** nothing reads it and it can be removed. The
file still validates with the key in it (`thresholds.schema.json` accepts it in any shape), and
`validate_canvas.py` prints one WARN line saying it is retired, from
`check_cycle_recording.py`. `calibration.ice_accuracy` in `cycle-history.yml` is still recorded.
Until 0.320.0 the bakeoff delta read it; that threshold is retired too (below), and since then no
threshold in this file is calibrated from it.

### Confidence Calibration

**What it controls**: Whether stated confidence scores match actual outcomes.

| Parameter | Value |
|-----------|-------|
| Default | Assume calibrated (no adjustment) |
| Calibration rule | Track confidence at time of decision vs actual outcome. If confidence 0.7 items succeed only 40% of the time, all confidence values need systematic deflation. |
| Minimum N | 10 completed cycles |
| Adjustment | Calibration factor applied to all confidence values (e.g., 0.85 = deflate by 15%) |

**Example**: After 20 cycles, confidence 0.7+ items succeed 55% of the time (should be ~70%). Calibration factor = 0.55/0.70 = 0.79. Surface warning: "Confidence scores are systematically optimistic. Consider applying a 0.8x correction factor."

> **Which confidence this is (note added 0.319.0).** The numbers in this section (0.7, the factor)
> are on a 0.0-1.0 scale read as a chance of success. That is the scale of a DIAMOND's confidence
> (`confidence-thresholds.yml`). It is **not the ICE Confidence**, which since 0.319.0 is the value
> of Gilad's Confidence Meter on 0-10 (`/mycelium:ice-score` Step 2). A meter value is a sum of
> evidence weights, not a probability: 3.0 does not mean a 30% chance. **Do not deflate, rescale or
> band a meter value with this factor.** The calibration procedure in this section is Mycelium's
> own; no source read describes one.

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

### Bakeoff ICE Delta (RETIRED in 0.320.0)

> **Why this note exists.** Until 0.320.0 this section defined `bakeoff_delta` in
> `canvas/thresholds.yml`: the ICE score difference that made a "clear winner" in a leaf bakeoff,
> default 20%, to be adjusted from bakeoff outcomes, bounds 10%-40%. **It is retired. No ICE gap
> decides anything in a leaf bakeoff.** The note stays so a reader who meets the key in an older
> `thresholds.yml`, canvas or decision log knows what it was and why it went.

**What it decided.** Two things, both in `orchestration/leaf-bakeoff.md`: competing leaves were
compared in parallel only when their ICE scores were within 20% of each other, and a leaf more
than 20% ahead won while the others were archived.

**Why it was retired.**

- **No source has the number, or any ICE gap that picks a winner.** The 20% was Mycelium's own;
  the 0.319.0 release notes say so and left it for a ruling. Gilad: *"The one number you should be
  most suspicious of is the ICE score."* (*Evidence-Guided*, ch. 3). Torres compares a small set
  of ideas by testing their assumptions and does not score them to choose (*Continuous Discovery
  Habits*).
- **It contradicted the archive rule.** A leaf is archived only when its riskiest assumption is
  invalidated by a test, never by ICE (`leaf-lifecycle.md`, Phase 5). Under the bakeoff's old
  Rule 1 a leaf whose assumption test passed was archived when another leaf scored more than 20%
  higher.
- **The number did not fit the arithmetic.** Since 0.319.0 a total is the product of three
  factors, so one step in one factor is the whole gap or more: Impact 5 to 6 moves the total by
  20%, and a second piece of anecdotal evidence that takes a Confidence of 0.5 to 1.0 doubles it.

**What does the work instead.**

- **When leaves are compared**: whenever two or more leaves on one opportunity each have an
  untested riskiest assumption. No score gap is consulted.
- **Which leaf wins**: the assumption-test verdicts. A leaf whose riskiest assumption failed is
  archived. If one passes and the others fail, it advances. If several pass, the tiebreak and
  segment-split rules apply. If all fail, all are archived and the opportunity is re-evaluated
  (`orchestration/leaf-bakeoff.md`, section 4).
- **What the ICE total is for**: ordering which assumption is tested first. It never decides.

**If your `thresholds.yml` still has `bakeoff_delta`:** nothing reads it and it can be removed. The
file still validates with the key in it (`thresholds.schema.json` accepts it in any shape), and
`validate_canvas.py` prints one WARN line saying it is retired, from
`check_cycle_recording.py`. No calibration is owed for it.

## `canvas/thresholds.yml` Format

```yaml
schema_version: 1

thresholds:
  # ice_advance (default 100, bounds 50-300) was here until 0.319.0. Retired: see
  # "ICE Sequencing Reference (RETIRED in 0.319.0)" above. A file that still has it validates.
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
    
  # bakeoff_delta (default 0.20, bounds 0.10-0.40) was here until 0.320.0. Retired: see
  # "Bakeoff ICE Delta (RETIRED in 0.320.0)" above. A file that still has it validates.

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

**Safety**: Calibrated values have bounds. The system cannot set confidence deflation to 0.1, or an evidence staleness threshold to less than half its default. Bounds prevent runaway calibration.

## Theory Citations

- Gilad: *Evidence-Guided* (confidence comes from evidence; the Confidence Meter, ch. 3; a team metric he proposes, *"Percent of ideas launched at least with a medium Confidence level (per the Confidence Meter)"*, ch. 9). Until 0.319.0 this line read "confidence calibration from actual outcomes"; the parts of the book read on 2026-10-11 describe no procedure for deflating confidence by a factor computed from outcomes, so that procedure is Mycelium's own.
- Gilad: *ICE Done Right*; Ellis & Brown: *Hacking Growth*, ch. 4 (no threshold on an ICE total; why `ice_advance` was retired)
- Gilad: *Evidence-Guided*, ch. 3; Torres: *Continuous Discovery Habits* (the ICE score is the number to be most suspicious of; ideas are compared by testing their assumptions; why `bakeoff_delta` was retired)
- Deming: Statistical process control (thresholds adjusted from data, not opinion)
- Meadows: Thinking in Systems (parameters as the lowest-leverage but easiest intervention point)
- Kahneman: Thinking, Fast and Slow (systematic miscalibration of predictions)
