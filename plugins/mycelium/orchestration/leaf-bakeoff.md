# Leaf Bakeoff Protocol

Structured A/B testing of competing OST solution leaves. When multiple leaves target the same opportunity, this protocol determines which advances and which is archived.

## When to Trigger a Bakeoff

A bakeoff is warranted when:
- 2+ solution leaves target the **same opportunity** in `canvas/opportunities.yml`
- Each of those leaves has a riskiest assumption that is **untested** (no test verdict recorded for it). No ICE gap is consulted.
- Both have completed Four Risks assessment (Phase 2 of leaf lifecycle)

If only one leaf has an untested riskiest assumption, test that one with `/assumption-test`: there is nothing to run in parallel. If the test verdicts are already recorded, apply the winner selection rules in section 4 to them without running a bakeoff. No leaf wins on its ICE score, whatever the gap to the others.

**What the ICE total is for here.** It orders which leaf's assumption is tested first when they cannot all be tested at once. It does not decide whether leaves are compared and it does not pick the winner. Gilad: *"The one number you should be most suspicious of is the ICE score."* (*Evidence-Guided*, ch. 3). Torres compares a small set of ideas by testing their assumptions and does not score them to choose (*Continuous Discovery Habits*; `engine/leaf-lifecycle.md`, Phase 5).

*(Changed 0.320.0. Until then a bakeoff was warranted when the ICE scores were "within 20%" of each other, and a leaf with an ICE score more than 20% higher than all others won outright once its riskiest assumption had been tested. The 20% was Mycelium's own number and no source has it. The threshold that held it, `bakeoff_delta`, is retired: `engine/adaptive-thresholds.md`.)*

## Bakeoff Workflow

### 1. Prepare (Lead Agent)

The lead agent (main session) orchestrates the bakeoff:

```
1. Read canvas/opportunities.yml — identify competing leaves
2. For each leaf: identify the riskiest assumption (from /ice-score step 4)
3. Design the cheapest test for each leaf's riskiest assumption, and write its `runs_on`
   (disk | network | human, as in /mycelium:assumption-test)
4. For each `human` test (a survey, a fake door, interviews, a paid pilot): register it through
   /mycelium:handoff. No subagent runs it; its verdict arrives through /mycelium:log-evidence.
5. Confirm with user: "Running bakeoff for [opportunity]. Leaves: A, B. Tests: [describe, with who
   runs each]. Proceed?"
```

**Why a worker never runs a `human` test (0.330.0).** Until then each worker was told to run its leaf's
riskiest assumption test, and the scorecard example was a fake-door test. A subagent cannot put a fake
door in front of customers or survey anyone; it can only report what such a test might show. Since
0.320.0 the test verdict is what picks the winner, so a simulated verdict could archive a leaf on a
result no customer produced. A bakeoff with a `human` test waits for that verdict before section 4.

### 2. Fan-Out (Spawn Workers)

For each leaf whose test runs on disk or network, spawn a sub-agent in worktree isolation. A leaf whose
test is `human` gets no worker: its scorecard is filled by the lead from the logged verdict.

```
Lead Agent
  |
  ├─ Worker 1 (worktree): Leaf A
  |    Task: Run Leaf A's disk or network test; fill the scorecard from the Four Risks
  |          and ICE already recorded for the leaf (the prerequisites above)
  |    Context: Read-only canvas, leaf details
  |    Deliverable: Completed scorecard, with the test's evidence and source
  |
  └─ Worker 2 (worktree): Leaf B
       (same pattern)
```

*(Changed 0.330.0. The worker task read "Run Four Risks → ICE → riskiest assumption test", which re-ran
the Four Risks the prerequisites require to be done already, and asked a subagent for test verdicts only
people can give.)*

**Rules**:
- Maximum 3 leaves per bakeoff (WIP ceiling from diamond-rules.md)
- Workers get READ-ONLY access to canvas files
- Workers NEVER update canvas or progress diamonds
- Workers NEVER run a `human` test
- Each worker runs independently with no inter-worker communication

On Claude Code the guard-state gate refuses a subagent's write to `.claude/canvas/` or `.claude/diamonds/`
(0.330.0). The other rules here are the lead's discipline; no hook checks them, and the 3-leaf ceiling is
advisory (`engine/diamond-rules.md`).

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
  runs_on: human          # disk | network | human; a human test is run through /mycelium:handoff
  result: passed|failed   # from the logged verdict; a bakeoff with a human test unlogged waits
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

The lead agent collects all scorecards and applies winner selection rules. **The assumption-test verdicts decide.** A leaf whose riskiest assumption failed is archived. The ICE totals on the scorecards are not compared to pick a winner.

#### Rule 1: Clear Winner
**Condition**: One leaf's assumption test passed AND every other leaf's assumption test failed
**Action**: Advance winner to GIST (Phase 5). Archive loser. Rule 5 says what to note about a failing leaf that served a different segment.

#### Rule 2: Several Pass, Same Segment
**Condition**: More than one leaf's assumption test passed AND they serve the same segment
**Action**: Run the cheaper assumption test to break the tie. If both assumptions pass, advance the one with lower feasibility risk (faster to ship). If both assumptions fail, archive both — return to opportunity.

#### Rule 3: Several Pass, Different Segments
**Condition**: More than one leaf's assumption test passed AND the leaves serve different user segments
**Action**: Both advance as separate GIST entries tagged with their target segment. This is a segment split, not a tie.

*(Changed 0.320.0. Until then Rules 1 to 3 each carried an ICE condition: "ICE delta > 20%" in Rule 1 and "ICE delta ≤ 20%" in Rules 2 and 3, which were named "Close Race". Under the old Rule 1 a leaf whose assumption test passed could be archived because another leaf scored more than 20% higher. The conditions now read the test verdicts and the segments, and nothing else.)*

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

**Bakeoff Theater**: Running a bakeoff when only one leaf has an untested riskiest assumption, or when the test verdicts are already recorded. Test the one assumption, or apply the winner selection rules to the verdicts you have. *(Until 0.320.0 this read "Running a bakeoff when one leaf is clearly superior (ICE >20% higher). Just advance the winner.", which advanced a leaf on its score.)*

**Endless Bakeoff**: Running more than 2 rounds of bakeoff for the same opportunity. If 2 rounds haven't produced a winner, the opportunity itself may need re-evaluation.

**Ignoring Segment Data**: Discarding a leaf that serves a different segment without noting the unserved need.

## Theory Citations

- Torres: Continuous Discovery Habits (parallel solution exploration; ideas are compared by testing their assumptions, not by scoring them)
- Ellis: ICE scoring. Gilad: Evidence-Guided (ICE with the Confidence Meter; the total is a hint for ordering: *"The one number you should be most suspicious of is the ICE score."*, ch. 3)
- Cagan: Inspired (Four Risks as evaluation framework)
- Ries: Lean Startup (cheapest viable test for assumptions)
