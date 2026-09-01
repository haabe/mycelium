# Cycle-Over-Cycle Learning

When a leaf completes the full lifecycle pipeline (shipped or discarded), Mycelium extracts process learnings. This is how the framework gets smarter over time — not just connecting pipes correctly, but learning from what flows through them.

## What Gets Recorded

Every leaf that reaches a terminal state (launched, archived, or killed) generates a cycle record in `canvas/cycle-history.yml`.

### Cycle Record Format

```yaml
- cycle_id: cycle-001
  leaf_id: opp-001-sol-A
  opportunity_id: opp-001
  started_at: "2026-04-12T10:00:00Z"
  completed_at: "2026-04-20T15:00:00Z"
  terminal_state: launched | archived | killed
  cycle_class: product-leaf | meta-dogfood | observation  # REQUIRED — see Cycle Class below

  # Predicted vs actual — the calibration data
  predicted:
    ice_score: {i: 8, c: 6, e: 7, total: 336}  # REQUIRED non-zero when cycle_class=product-leaf
    feasibility_risk: medium
    estimated_effort: "2 sprints"
  actual:
    outcome: success | partial | failure
    actual_effort: "3 sprints"
    dora_metrics: {deploy_freq: "daily", lead_time: "2 days", cfr: "5%", mttr: "1 hour"}
    user_metrics: {adoption: "15%", satisfaction: "4.2/5", retention: "85%"}
  
  # Calibration delta — how far off were we?
  calibration:
    ice_accuracy: -2  # Predicted ICE total vs outcome-adjusted score
    effort_accuracy: "+50%"  # Actual vs estimated effort
    risk_accuracy: "feasibility underestimated"  # Which risk dimension was most wrong?

  # Gate effectiveness — which theory gates fired this cycle and whether they caught a real problem.
  # Closes the /framework-health "Gate effectiveness" dimension (was unInstrumented in cycle records).
  gates_fired:
    - gate: "Evidence (L0→L1)"   # gate name / id
      result: pass               # pass | fail  (fail = gate blocked progression, i.e. caught a gap)
      caught: ""                 # what the gate surfaced when it failed; "" when it passed clean
  # In-cycle regression — the diamond moved back a phase DURING this cycle (assumption invalidated mid-flight).
  # Distinct from rework.post_delivery_regressions below (those are post-launch defects within 14 days).
  # Closes the /framework-health "Regression rate" dimension.
  regressions:
    in_cycle_count: 0            # times the diamond regressed to an earlier phase during this cycle
    from_phase: null             # deepest phase regressed FROM (e.g., Deliver)
    to_phase: null               # phase regressed TO (e.g., Define)
    trigger: ""                  # what invalidated the assumption / forced the step back

  # Demand type — WHY this cycle exists at all. Seddon: VALUE demand is work a user
  # or goal actually asked for; FAILURE demand is work caused by earlier work being
  # wrong, missing or incomplete. "Five cycles" reads as throughput; "two value, three
  # failure" reads as a system generating its own work, and only the second is a
  # measurement.
  #
  # SET AT CYCLE OPEN, NOT AT RETROSPECTIVE. Seddon classifies demand as it ARRIVES,
  # and origin is knowable when a cycle starts and progressively less knowable
  # afterwards. A demand type assigned weeks later reports on the assessor.
  #
  # NOT AN EXTENSION OF `rework` BELOW. That block is post-delivery-defect scoped — a
  # 14-day window after completion. Work begun because earlier work was incomplete is
  # not a post-delivery regression; it is the reason the cycle exists. Different
  # question, different field.
  demand_type: value             # REQUIRED — value | failure
  demand_origin: ""              # REQUIRED when failure: what earlier work caused this cycle.
                                 # "" when value. A failure cycle that cannot name its cause
                                 # is usually mis-classed.
  demand_cost_class: null        # OPTIONAL refinement (Crosby/Juran cost-of-quality):
                                 # prevention | appraisal | internal-failure | external-failure.
                                 # null is a fine answer; the binary above is the required unit.

  # What was learned
  learnings:
    process: ""  # What would we do differently next time?
    domain: ""   # What did we learn about this problem domain?
    framework: ""  # Did the Mycelium process help or hinder?
  
  # Rework tracking (populated 14 days after completion via /retrospective rework-check)
  rework:
    post_delivery_corrections: 0    # corrections logged within 14 days of completion
    post_delivery_regressions: 0    # regressions within 14 days of completion
    days_to_first_regression: null  # null = no regression observed
  
  # Discard-specific (if archived/killed)
  discard_reason: ""  # low-ice-score | failed-assumption | feasibility-block | etc.
  discard_phase: null  # Which lifecycle phase the leaf died at
```

## Cycle Class

Every cycle record carries a `cycle_class` field. The class determines which calibration dimensions apply:

| Class | Definition | ICE required? | Calibration dimensions that apply |
|---|---|---|---|
| `product-leaf` | OST solution leaf shipped or discarded — the canonical cycle shape | **yes**, non-zero `predicted.ice_score` | ICE accuracy, effort accuracy, risk accuracy, rework rate, discard timing |
| `meta-dogfood` | Framework-self-development (validator check shipped, anti-pattern graduated, harness layer added) — no impact/confidence/ease tradeoff was scored | no — `ice_score: {i:0, c:0, e:0, total:0}` permitted with `notes:` line stating why | Effort accuracy only |
| `observation` | First-week observation, cohort log capture, evidence harvesting — no design decision was made | no | None (record for audit trail only; excluded from calibration_summary aggregates) |

**Rule**: A `product-leaf` cycle with `predicted.ice_score.total == 0` is a validator failure (Check 38). Either the cycle is mis-classed, or the ICE step was skipped at opp-selection — see `skills/ice-score/SKILL.md` for the gate.

**Why this matters**: without `cycle_class`, framework-meta cycles (no ICE possible) and product-leaf cycles (ICE required) end up in the same bucket. `calibration_summary` then says "0/N cycles carry ICE" forever — a permanently dark dimension. Classing makes the dark dimension narrow correctly: "0/0 product-leaf cycles" is honest and actionable; "0/N total cycles" is theater.

## When to Record

| Event | Trigger | What to Record |
|-------|---------|----------------|
| Leaf archived | `/ice-score` discard, `/assumption-test` failure | Predicted ICE, discard reason, discard phase, learnings |
| Leaf launched | L5 Deliver complete | Full predicted vs actual comparison |
| Post-launch review | 30 days after launch | User metrics, actual outcome, calibration delta |
| Rework follow-up | 14 days after completion | Post-delivery corrections, regressions, days to first regression |
| **Framework work shipped** | **A release arc closes — see below** | **`meta-dogfood` record: effort accuracy, learnings, gates fired. ICE/DORA/user-metrics exempt.** |

**The release-arc trigger (added 2026-08-06, v0.98.0).** Every row above this one is keyed to the *leaf* lifecycle, so until now a `meta-dogfood` cycle could only open where a leaf-shaped event happened to occur — in practice `diamond-progress` at a phase transition, the single opener in the codebase. Framework work does not move diamonds through phases. It ships releases. So framework work was recordable in principle and unrecordable in practice, and the ledger filled only while sessions happened to be thinking about it.

**The trigger**: a `meta-dogfood` cycle is owed when **≥5 minor releases** (`v0.X.0`) have shipped since the newest `completed_at` in `cycle-history.yml`. Minor, not patch — a patch is maintenance, and the 2026-06-18 ruling that steady-state ops gets no cycle still stands. Five is a starting threshold, not a measured one; it is registered in `canvas/thresholds.yml` as `cycle_recording_arc` so it calibrates like every other threshold rather than staying a number someone once typed.

**Enforced by** `scripts/check_cycle_recording.py`, which counts minor-release commits since the newest cycle and fails loud when the arc is owed. It does **not** write the record or guess its boundaries — deciding where an arc begins and ends is a judgement, and a script that guessed would fabricate the effort estimate that is the record's only required calibration field. It asserts the arc was *considered*, the same shape as `check_bvssh_reconcile.py`.

**Worked failure this trigger exists for**: the dogfood project shipped 29 minor releases across 49 days (2026-06-18 → 2026-08-06) — two validator checks, two engine layers, three skills, four guards — with zero diamond phase transitions, therefore zero triggers, therefore zero cycles. Nine of its twelve prior cycles had landed in a single 19-day window while cycle machinery was being built. Attention was the only mechanism, so the ledger tracked attention rather than work.

## Post-Mortem Trigger

After every **5th** completed or discarded leaf (tracked via `canvas/cycle-history.yml` count), the system prompts:

> "5 leaves have completed since last review. Run `/retrospective` to extract process patterns. Focus on: Are predictions improving? Which risk dimension is most frequently wrong? Are discards happening earlier or later in the pipeline?"

This ensures pattern extraction happens regularly without being per-leaf overhead.

## Calibration Metrics

The cycle history enables these calibration questions:

### ICE Accuracy
Compare predicted ICE scores with actual outcomes. Over time:
- Are high-ICE items actually succeeding? (If not: ICE methodology needs tuning)
- Are low-ICE discards actually low-value? (If revivals succeed: threshold may be too aggressive)

### Effort Accuracy
Compare estimated effort (from feasibility risk) with actual effort:
- Consistent overestimation → ease scores are too conservative
- Consistent underestimation → ease scores are too generous
- Domain-specific patterns → some domains always take longer

### Risk Dimension Accuracy
Track which risk dimension is most frequently the one that surprises:
- If value risk is consistently wrong → user research methodology needs improvement
- If feasibility risk is consistently wrong → engineering spikes need more depth
- If usability risk is consistently wrong → prototype testing needs to be earlier/deeper

### Rework Rate
Track post-delivery corrections and regressions within 14 days of completion:
- High rework rate with passing DoD → success criteria were too loose or didn't cover the right dimensions
- High rework rate on AI-assisted code → cross-reference with APEX `ai_rework_rate` in `dora-metrics.yml`
- Low rework rate → delivery quality is genuine, not just velocity theater

*Source: Paddo (the denominator problem — velocity gains consumed by invisible rework).*

### Discard Timing
Track at which lifecycle phase leaves are most often discarded:
- Early discards (Phase 3-4) are healthy — the pipeline is filtering efficiently
- Late discards (Phase 7-9) are expensive — earlier gates should catch these
- If most discards happen at the same phase, that gate may be too lenient or the previous gate too easy

## Framework-on-Framework Exemption

**NARROWED 2026-08-06 (v0.98.0). It used to exempt the whole record; it now exempts only the fields that genuinely do not apply.** Read the history before applying it, because the old form is still quoted in older decision logs.

When Mycelium is the product (a repo dogfooding itself), framework improvements ship as commits and graduate through `.claude/memory/corrections.md` → mechanism. That graduation ledger is unchanged and remains the primary framework calibration surface.

**What is exempt: fields, not records.** Framework-self-development IS recorded, as `cycle_class: meta-dogfood` (see [Cycle Class](#cycle-class)). On such a record:

- `predicted.ice_score` — **exempt**, permitted zero with a `notes:` line. No impact/confidence/ease tradeoff was scored, so a number here would be invented.
- `actual.dora_metrics`, `actual.user_metrics` — **exempt**, permitted null. Delivery-health and adoption belong to the L4 delivery diamond and to `dora-metrics.yml`, not to a per-cycle row.
- `calibration.ice_accuracy`, `calibration.risk_accuracy` — **exempt**, permitted null. They are derived from the exempt fields.
- `calibration.effort_accuracy` — **REQUIRED, and it is the point**, except on a reconstructed record (see below). This is the one dimension the schema does fit framework work, and it is the one that has paid: effort accuracy across meta-dogfood cycles surfaced *scope-expansion-blind-to-user* at N=4, the dogfood project's most consistent calibration miss, which graduated to guardrail **G-P9**. The corrections → cluster path did not produce that finding and structurally could not — a correction records a mistake, not an estimate that was wrong.

**The one exemption from the required field: `reconstructed_post_hoc: true`.** A cycle reconstructed after the fact — a backfill of work that shipped before the trigger existed — carries `effort_accuracy: null` and is EXCLUDED from every calibration aggregate. This is not a loophole, it is the only honest option: no estimate was ever set on that arc, so there is nothing for the actual to be wrong about, and a reconstructed estimate is a number invented today to grade work done months ago. Fabricating it would corrupt the single dimension the record exists to protect.

**The exemption extends to the two OBSERVATIONAL fields, added 2026-09-01 (v0.161.0).**
`gates_fired` and `regressions` — and `rework`, which is derived over the following fortnight —
are also permitted absent on a reconstructed record, and `check_cycle_recording.py` excludes those
records from their coverage counts rather than reporting them as gaps. The reason is the one
stated above, one step further out: nobody was watching that arc, so the observation was never
made and cannot be recovered. Writing `gates_fired: []` there would not record a measurement; it
would add a fabricated zero to framework-health's Gate-effectiveness denominator and deflate the
very number the field exists to produce. The coverage line names how many records it excluded, so
a clean result is never read as full coverage.

**`demand_type` is NOT exempt, and that is the line.** The exemption is per-FIELD, not
per-RECORD. Seddon's type classifies *why the work was asked for*, not what was observed while it
ran, and that stays determinable from the record long afterwards — the dogfood project filled it
on three reconstructed cycles by tracing them to the opportunity that caused them, which moved its
demand mix to 13 failure / 7 value. Exempting the whole record would have silently lost a real
measurement. The test suite pins both halves.

**What a reconstructed record IS worth**: an audit trail, and a measurement baseline for `check_cycle_recording.py`, which measures from the newest `completed_at`. It restores continuity and produces zero calibration data. Record it that way rather than counting it as a win.

**Why this clause exists at all** (added v0.98.1, hours after v0.98.0): the dogfood project backfilled three arcs immediately on shipping the trigger, and every one of them had to leave the newly-required field null. Without this clause the framework would have shipped a rule and instantly created three violating rows, with nothing to distinguish "exempt by design" from "someone skipped the field" — which is the `documented-rule-diverges-from-enforcement` cluster reproducing itself inside the release meant to close a different gap.

**Why the old whole-record form was wrong, kept because the reasoning was half right.** The original (v0.23.16, 2026-05-14) argued that forcing framework work through the ledger "would produce mostly-null rows". That prediction was CORRECT — all ten meta-dogfood records in the dogfood project carry null ICE, null DORA and null user-metrics. The error was the remedy: it dropped the record to avoid the nulls, when the fix was to stop *requiring* the null fields. Nineteen days later `cycle_class: meta-dogfood` (v0.39.0, 2026-06-02) was added saying the opposite, and neither rule was reconciled with the other — so from 2026-06-02 to 2026-08-06 this file contained two contradicting answers sixty lines apart, and which one applied was decided by a detection test (below) that a dogfood-consumer repo fails on a technicality. Surfaced by `/mycelium:framework-health` 2026-08-06.

**Where the rest of framework calibration lives**:
- `corrections.md` — recurrence count is the prediction-error signal
- Graduation criterion in `cluster-instances.md` — the "actual vs expected" trigger
- Commit history of `plugins/mycelium/engine/validator.sh` and `harness/anti-patterns.md` — the mechanism ledger

**Canonical source for this discipline**: Mitchell Hashimoto (HashiCorp co-founder, blog post early Feb 2026): *"Anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again."* The corrections.md → cluster → mechanism loop is Mycelium's direct implementation. The term "harness engineering" — given formal definition by Ryan Lopopolo (OpenAI, 2026-02-11) and crystallized as the fourth paradigm of AI engineering across the industry by mid-2026 — names the broader discipline Mycelium has been building toward since v0.1.

**Detection** (used by `/mycelium:framework-health` Step 1): the project root contains `plugins/mycelium/plugin.json` AND `CLAUDE.md` begins with `# Mycelium:`. When both hold, the skill routes to the corrections-graduation summary instead of returning early on N=0 cycles.

**What the detection does and does NOT gate — the distinction the pre-2026-08-06 form got wrong.** It gates ONLY the `/framework-health` routing: whether that skill reports through the corrections-graduation lens or the five-dimension lens. It does **not** gate whether cycles are recorded. Framework work is recorded as `meta-dogfood` in every repo, matched or not. A repo that fails the detection is not thereby a repo whose framework work is unrecordable — that inference is what produced the contradiction described above, and it is why a dogfood-consumer repo (framework installed as a plugin, own `CLAUDE.md`) spent two months following whichever rule the reading session happened to reach first.

**Reconsider this narrowing if**: effort accuracy stops paying. The whole case for keeping the record rests on one dimension producing real findings; if several consecutive meta-dogfood cycles yield no effort-calibration signal, the original whole-record exemption was right after all and this should revert rather than accumulate ceremony. Log that judgement in the decision log rather than letting the records thin out silently — a ledger that stops being written is indistinguishable from a ledger nothing happened in, which is the failure class this narrowing exists inside (see `harness/anti-patterns.md` #9).

## Connecting to Existing Systems

| System | Connection |
|--------|-----------|
| `corrections.md` | Calibration errors become correction entries ("We consistently underestimate feasibility for ML features") |
| `patterns.md` | Calibration successes become pattern entries ("Technical spikes at L3 reduced late-stage feasibility surprises by 60%") |
| `feedback-loops.md` | Cycle learning is a Loop 2 (incremental) mechanism |
| `archived-solutions.yml` | Discard records link to archive entries |
| `leaf-lifecycle.md` | Cycle records are the data layer under the structural pipeline |

## Theory Citations

- Argyris: Single-loop and double-loop learning (cycle learning is single-loop; pattern emergence from cycles is double-loop)
- Forsgren: Accelerate (measuring and improving delivery capabilities)
- Gilad: Evidence Guided (confidence calibration from actual outcomes)
- Kahneman: Thinking, Fast and Slow (calibration of prediction accuracy)
