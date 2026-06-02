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

When Mycelium is the product (this repo dogfoods itself), framework improvements ship as commits and graduate through `.claude/memory/corrections.md` → mechanism (validator check, guardrail, skill update). They do **not** populate `cycle-history.yml`.

**Why**: The cycle schema (`feasibility_risk`, `dora_metrics`, `user_metrics`, ICE prediction) does not map cleanly to "added a validator check" or "graduated a recurring correction to a mechanism." Forcing framework work through the cycle ledger would produce mostly-null rows and mix product-cycle signal with framework-meta signal in `calibration_summary`, degrading both.

**Where framework calibration lives instead**:
- `corrections.md` — recurrence count is the prediction-error signal
- Graduation criterion in `cluster-instances.md` — the "actual vs expected" trigger
- Commit history of `plugins/mycelium/engine/validator.sh` and `harness/anti-patterns.md` — the mechanism ledger

**Canonical source for this discipline**: Mitchell Hashimoto (HashiCorp co-founder, blog post early Feb 2026): *"Anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again."* The corrections.md → cluster → mechanism loop is Mycelium's direct implementation. The term "harness engineering" — given formal definition by Ryan Lopopolo (OpenAI, 2026-02-11) and crystallized as the fourth paradigm of AI engineering across the industry by mid-2026 — names the broader discipline Mycelium has been building toward since v0.1.

**Detection** (used by `/mycelium:framework-health` Step 1): the project root contains `plugins/mycelium/plugin.json` AND `CLAUDE.md` begins with `# Mycelium:`. When both hold, the skill routes to the corrections-graduation summary instead of returning early on N=0 cycles.

**Reconsider this exemption if**: Mycelium gains a second product surface (e.g., a hosted service) whose delivery does fit the OST→ICE→launch shape. At that point, the framework-meta work could move to a parallel `framework-cycle-history.yml`. Until then, the existing corrections graduation is the ledger.

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
