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

### 2. Fan-Out: Spawn Workers
```
For each solution needing parallel exploration:
  Spawn subagent or Agent Team member with:
    - Clear task: "Test assumption X for solution Y"
    - Read-only canvas context
    - Worktree isolation (if code is involved)
    - Time bound: max N minutes
    - Deliverable: assumption test result + updated confidence
```

### 3. Workers Execute Independently
Each worker:
- Runs their assumption test (survey, prototype, data analysis, etc.)
- Records evidence found
- Updates their local ICE confidence assessment
- Reports back to lead agent

### 4. Fan-In: Lead Agent Collects
```
Collect results from all workers
For each solution:
  - Update ICE score in canvas/opportunities.yml
  - Record evidence in experiment log
Compare solutions using updated scores
Select winner(s) for progression
Log decision in decision-log.md
```

### 5. Advance Diamond
- Progress winning solution(s) to next diamond phase
- Archive losing solutions (don't delete -- they're learning)
- Update corrections.md if patterns were discovered

## Rules
- Workers NEVER update canvas files (lead agent does)
- Workers NEVER progress diamonds (lead agent does)
- Lead agent ALWAYS runs bias check on combined results
- Time bounds are enforced -- workers that exceed time are stopped
- Minimum 2 workers for meaningful comparison (don't fan-out for a single solution)
