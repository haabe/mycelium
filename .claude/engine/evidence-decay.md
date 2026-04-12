# Evidence Decay and Refresh

Evidence ages. A user need validated 6 months ago may no longer hold. A competitive analysis from last quarter may be outdated. This document defines how Mycelium handles evidence staleness.

## Core Principle

Evidence has a shelf life. The confidence attached to evidence should decay over time unless refreshed. This is not pessimism — it's epistemic hygiene.

## Staleness Thresholds

Different evidence types age at different rates:

| Evidence Category | Default Staleness Threshold | Rationale |
|-------------------|-----------------------------|-----------|
| User needs / interviews | 90 days | User behavior and preferences shift |
| Competitive intelligence | 90 days | Competitors ship constantly |
| Strategic assumptions (L0-L1) | 180 days | Purpose and strategy are slower to change |
| Technical feasibility | 120 days | Tech landscape evolves, but not as fast as user needs |
| Market positioning | 90 days | Market conditions shift with competitive moves |
| DORA / delivery metrics | 30 days | Delivery health is a current snapshot, not historical |
| Regulatory assessment | 365 days | Regulation changes slowly (unless a new law passes) |

These are defaults. Override per-project in `canvas/thresholds.yml` (when it exists, see adaptive-thresholds.md).

## How Decay Works

### 1. Timestamp Requirement

Every evidence citation in canvas files should include a `validated_at` or `captured_at` timestamp. This is already part of the provenance schema (`_common.schema.json#/$defs/provenance`).

If `validated_at` is missing, the evidence is treated as having been validated at `captured_at`. If both are missing, the evidence is treated as stale immediately.

### 2. Confidence Degradation

When evidence passes its staleness threshold without being refreshed:

- **First period past threshold**: Confidence drops by 0.1
- **Second period past threshold**: Confidence drops by another 0.1
- **Third period past threshold**: Evidence flagged as "stale — refresh required before using in decisions"

Example: User interview evidence with confidence 0.6, validated 90 days ago, threshold 90 days:
- Day 91-180: Confidence degrades to 0.5
- Day 181-270: Confidence degrades to 0.4
- Day 271+: Flagged as stale, not usable for decisions without refresh

### 3. Refresh Protocol

To refresh stale evidence, re-run the original research method:

| Original Method | Refresh Method | Minimum Viable Refresh |
|----------------|----------------|------------------------|
| User interview | New interview or follow-up | 1 conversation confirming/updating the finding |
| Survey | New survey or spot-check | 5-response pulse check |
| Analytics data | Pull fresh data | New data pull from same source |
| Competitive analysis | Re-analyze competitor | Check competitor changelog/releases since last analysis |
| Feasibility spike | Quick revalidation | Confirm assumptions still hold (dependencies, APIs, etc.) |
| Assumption test | Re-run test | If conditions changed, re-run; if stable, extend timestamp |

After refresh, update `validated_at` to the current date and reset confidence to the evidence-appropriate level.

### 4. Cascade Effect

When evidence decays, it affects everything downstream:

```
Stale user need evidence
  → OST opportunity confidence degrades
    → Solution leaf ICE confidence degrades
      → GIST idea confidence degrades
```

This cascade is the system working correctly. If foundational evidence is stale, downstream confidence should reflect that uncertainty.

## Integration with Canvas Health

`/canvas-health` should include evidence decay checking:

1. **Scan all provenance blocks** across canvas files
2. **Compare `validated_at` (or `captured_at`)** against the staleness threshold for that evidence category
3. **Flag stale evidence** with severity:
   - **Warning**: 1 period past threshold (confidence should be degraded)
   - **Critical**: 3+ periods past threshold (evidence not usable for decisions)
4. **Suggest refresh actions**: "User need evidence in opportunities.yml is 120 days old (threshold: 90 days). Run `/user-interview` or `/log-evidence` to refresh."

## Integration with Diamond Progress

When `/diamond-progress` checks the Evidence Gate, it should also check evidence freshness:
- If any key evidence supporting the transition is past its staleness threshold, surface a warning
- This is a NUDGE, not a BLOCK — stale evidence doesn't prevent progress, but it should be acknowledged

## What This Does NOT Do

- **Does not auto-delete evidence.** Evidence is never deleted — it decays in confidence but remains for historical context.
- **Does not block progress mechanically.** Staleness is a NUDGE that degrades confidence, not a BLOCK that prevents action.
- **Does not apply to corrections/patterns.** Process learnings don't decay — a mistake from 6 months ago is still a mistake to avoid.

## Theory Citations

- Gilad: Evidence Guided (confidence must reflect evidence quality, including freshness)
- Torres: Continuous Discovery Habits (continuous = ongoing, not one-time)
- Kahneman: Thinking, Fast and Slow (recency bias is bad, but so is anchoring on stale data)
