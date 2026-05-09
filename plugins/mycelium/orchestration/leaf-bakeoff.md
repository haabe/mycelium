# Leaf Bakeoff Protocol

Structured A/B testing of competing OST solution leaves. When multiple leaves target the same opportunity, this protocol determines which advances and which is archived.

## When to Trigger a Bakeoff

A bakeoff is warranted when:
- 2+ solution leaves target the **same opportunity** in `canvas/opportunities.yml`
- Their ICE scores are **within 20%** of each other (no clear winner)
- Both have completed Four Risks assessment (Phase 2 of leaf lifecycle)

If one leaf has an ICE score >20% higher than all others AND its riskiest assumption has been tested, it wins outright — no bakeoff needed.

## Bakeoff Workflow

### 1. Prepare (Lead Agent)

The lead agent (main session) orchestrates the bakeoff:

```
1. Read canvas/opportunities.yml — identify competing leaves
2. For each leaf: identify the riskiest assumption (from /ice-score step 4)
3. Design the cheapest test for each leaf's riskiest assumption
4. Confirm with user: "Running bakeoff for [opportunity]. Leaves: A, B. Tests: [describe]. Proceed?"
```

### 2. Fan-Out (Spawn Workers)

For each leaf, spawn a sub-agent in worktree isolation:

```
Lead Agent
  |
  ├─ Worker 1 (worktree): Leaf A
  |    Task: Run Four Risks → ICE → riskiest assumption test
  |    Context: Read-only canvas, leaf details
  |    Deliverable: Completed scorecard
  |
  └─ Worker 2 (worktree): Leaf B
       Task: Run Four Risks → ICE → riskiest assumption test
       Context: Read-only canvas, leaf details
       Deliverable: Completed scorecard
```

**Rules**:
- Maximum 3 leaves per bakeoff (WIP ceiling from diamond-rules.md)
- Workers get READ-ONLY access to canvas files
- Workers NEVER update canvas or progress diamonds
- Each worker runs independently with no inter-worker communication

### 3. Scorecard Format

Each worker returns a structured scorecard:

```yaml
leaf_id: opp-001-sol-A
opportunity_id: opp-001
four_risks:
  value: {level: low, evidence: "...", perspective: product}
  usability: {level: medium, evidence: "...", perspective: design}
  feasibility: {level: low, evidence: "...", perspective: engineering}
  viability: {level: low, evidence: "...", perspective: cross-cutting}
ice_score: {impact: 8, confidence: 6, ease: 7, total: 336}
assumption_test:
  assumption: "Users will switch from manual tracking"
  risk_dimension: value
  method: fake-door
  result: passed|failed
  details: "..."
  confidence_delta: +0.15
estimated_effort: "2 sprints"
target_segments: ["power-users", "new-users"]
segment_fit:
  - segment: power-users
    fit: strong
    reason: "..."
  - segment: new-users
    fit: moderate
    reason: "..."
```

### 4. Fan-In (Winner Selection)

The lead agent collects all scorecards and applies winner selection rules.

#### Rule 1: Clear Winner
**Condition**: ICE delta > 20% AND assumption test passed
**Action**: Advance winner to GIST (Phase 5). Archive loser.

#### Rule 2: Close Race, Same Segment
**Condition**: ICE delta ≤ 20% AND both serve the same segment
**Action**: Run the cheaper assumption test to break the tie. If both assumptions pass, advance the one with lower feasibility risk (faster to ship). If both assumptions fail, archive both — return to opportunity.

#### Rule 3: Close Race, Different Segments
**Condition**: ICE delta ≤ 20% AND leaves serve different user segments
**Action**: Both advance as separate GIST entries tagged with their target segment. This is a segment split, not a tie.

#### Rule 4: Both Fail
**Condition**: Both assumption tests fail
**Action**: Archive both leaves. Return to the opportunity with new evidence (what was learned from the failures). The opportunity may need re-framing — the failures are evidence.

#### Rule 5: One Passes, One Fails
**Condition**: One assumption test passes, the other fails
**Action**: Advance the passing leaf. Archive the failing leaf. If the failing leaf served a different segment, note this in the archive — the segment's need is still unmet.

### 5. Post-Bakeoff

1. **Update canvas**: Lead agent writes results to `canvas/opportunities.yml` (update ICE scores, confidence) and `canvas/archived-solutions.yml` (loser archival)
2. **Log decision**: Entry in `.claude/harness/decision-log.md` with: both scorecards, selection rule applied, rationale
3. **Bias check**: Run `/bias-check` on the combined bakeoff results — are you favoring the familiar option?

## Connecting to Fan-Out Skill

The `/fan-out` skill handles the mechanical orchestration. This protocol adds:
- Scorecard format (structured comparison data)
- Winner selection rules (decision framework)
- Segment-aware evaluation (multi-segment handling)
- Loser archival (learning preservation)

When running `/fan-out` for a leaf bakeoff, specify `bakeoff: true` and the lead agent will apply this protocol's rules during fan-in.

## Anti-Patterns

**Bakeoff Theater**: Running a bakeoff when one leaf is clearly superior (ICE >20% higher). Just advance the winner.

**Endless Bakeoff**: Running more than 2 rounds of bakeoff for the same opportunity. If 2 rounds haven't produced a winner, the opportunity itself may need re-evaluation.

**Ignoring Segment Data**: Discarding a leaf that serves a different segment without noting the unserved need.

## Theory Citations

- Torres: Continuous Discovery Habits (parallel solution exploration)
- Ellis: ICE scoring. Gilad: Evidence-Guided (ICE-based comparison with Confidence Meter)
- Cagan: Inspired (Four Risks as evaluation framework)
- Ries: Lean Startup (cheapest viable test for assumptions)
