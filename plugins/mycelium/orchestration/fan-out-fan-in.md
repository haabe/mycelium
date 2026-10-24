# Fan-Out / Fan-In Pattern for OST Exploration

## When to Use
When the Opportunity Solution Tree has multiple solution branches at L3 that need parallel assumption testing or prototype exploration.

## Prerequisites
- OST must have 2+ solutions for the same opportunity
- Each solution must be independent (no shared dependencies)
- Lead agent has identified the riskiest assumption per solution

## Workflow

### 1. Lead Agent Prepares
```
Read canvas/opportunities.yml
Identify target opportunity and its solutions
For each solution: identify riskiest assumption
Design assumption test per solution
```

### 2. Classify Each Test by Who Can Run It
For each test, write its `runs_on`, the field `/mycelium:assumption-test` already uses:
- `disk`: the data is in the repo or the plugin tree (data analysis, a feasibility spike, a blind review).
- `network`: public data an agent can fetch (competitor pages, public datasets, a docs read).
- `human`: a send, a call, a survey, a fake door, a paid pilot, a ruling. Real people over days.

**A subagent runs only `disk` and `network` tests.** A `human` test goes out through
`/mycelium:handoff`, and its verdict is the one the person brings back through
`/mycelium:log-evidence`. A subagent asked for a survey or fake-door result can only simulate it, and a
simulated verdict is `internal_simulated` evidence, never a test result (*changed 0.330.0*: until then
this pattern asked workers to run "their assumption test (survey, prototype, data analysis, etc.)" in
"max N minutes", and the leaf bakeoff picks its winner on that verdict).

### 3. Fan-Out: Spawn Workers (disk and network tests only)
```
For each solution with a disk or network test:
  Spawn subagent or Agent Team member with:
    - Clear task: "Run test T for assumption X of solution Y"
    - Read-only canvas context
    - Worktree isolation (if code is involved)
    - A turn cap (a plugin or project agent definition's `maxTurns`), if the runtime has one
    - Deliverable: the test's result, its evidence and its source, in the report
```
Claude Code has a turn cap for a subagent (`maxTurns`) and no time or cost cap. A time bound written
into a brief is advice to the worker, not a limit anything enforces.

### 4. Workers Execute Independently
Each worker:
- Runs its disk or network test
- Records the evidence found, with its source
- Reports back to the lead agent. The report is a summary: the lead reads the evidence, not only the
  verdict, before writing anything

### 5. Fan-In: Lead Agent Collects
```
Collect results from all workers, and the human tests' verdicts once they are logged
For each solution:
  - Update ICE score in canvas/opportunities.yml
  - Record evidence in experiment log
Compare solutions by their assumption-test verdicts (the updated scores are hints, not the decision)
Select winner(s) for progression
Log decision in decision-log.md
```

### 6. Advance Diamond
- Progress winning solution(s) to next diamond phase
- Archive losing solutions (don't delete -- they're learning)
- Update corrections.md if patterns were discovered

## Rules
- Workers NEVER update canvas files (lead agent does)
- Workers NEVER progress diamonds (lead agent does)
- Workers NEVER run a `human` test; it goes out through `/mycelium:handoff`
- Lead agent ALWAYS runs bias check on combined results
- Minimum 2 workers for meaningful comparison (don't fan-out for a single solution)

**Which of these anything enforces.** On Claude Code, the guard-state gate refuses a subagent's write to
`.claude/canvas/` or `.claude/diamonds/` (since 0.330.0; it reads the `agent_id` Claude Code puts on a
subagent's tool calls). That covers the first two rules for file writes. The rest are the lead's
discipline: no hook checks them. On a runtime that sends no `agent_id`, none of them is enforced.
*(Until 0.330.0 this list said "Time bounds are enforced -- workers that exceed time are stopped". Nothing
enforced it, and Claude Code has no time limit for a subagent.)*
