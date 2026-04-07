# Agent Orchestration Patterns

## When to Use Multi-Agent Orchestration

Single-agent is sufficient for most work. Use multi-agent when:
- The OST has multiple solution branches that need parallel exploration
- A delivery diamond has independent work items that can be parallelized
- Research needs to cover multiple domains simultaneously
- Time pressure requires parallel rather than sequential progress

## Pattern 1: Fan-Out / Fan-In (OST Exploration)

When the Opportunity Solution Tree has multiple solutions to explore for the same opportunity:

```
Lead Agent (main session)
  |
  |-- Reads OST from canvas/opportunities.yml
  |-- Identifies solutions needing parallel exploration
  |
  |-- Spawns Worker Agent 1 (subagent or Agent Team member)
  |     Task: "Explore Solution A: [description]"
  |     Context: Relevant canvas sections (read-only)
  |     Isolation: Worktree (own branch)
  |     Deliverable: Assumption test results, updated ICE score
  |
  |-- Spawns Worker Agent 2
  |     Task: "Explore Solution B: [description]"
  |     (same pattern)
  |
  |-- Spawns Worker Agent 3
  |     Task: "Explore Solution C: [description]"
  |     (same pattern)
  |
  |-- Collects results from all workers
  |-- Updates ICE scores in canvas/opportunities.yml
  |-- Selects winning solution(s) based on evidence
  |-- Logs decision in decision-log.md
```

### Rules for Fan-Out
- Workers get READ-ONLY access to canvas files
- Workers get their own worktree (isolated branch)
- Workers report results back to lead agent
- ONLY the lead agent updates canvas and diamond state
- Each worker gets clear deliverables and time bounds

## Pattern 2: Parallel Delivery (Feature Implementation)

When a delivery diamond has independent work items:

```
Lead Agent
  |
  |-- Decomposes delivery work into independent slices
  |-- Each slice must be:
  |     - Independently testable
  |     - Non-overlapping in files touched
  |     - Connected to a single acceptance criterion
  |
  |-- Worker Agent per slice (in worktrees)
  |     Each worker:
  |     - Reads corrections.md (own copy)
  |     - Runs reflexion loop independently
  |     - Creates PR when done
  |
  |-- Lead reviews PRs
  |-- Merges in dependency order
  |-- Runs integration validation
  |-- Updates DORA metrics
```

### Rules for Parallel Delivery
- Workers must not touch the same files (use worktree isolation)
- Each worker runs the full reflexion loop independently
- Workers accumulate their own corrections -- lead merges corrections.md after
- Integration testing happens AFTER merge, not per-worker
- If a worker's PR fails integration: fix before merging the next

## Pattern 3: Parallel Research (Discovery Acceleration)

For discovery phases when multiple research streams are needed:

```
Lead Agent
  |
  |-- Identifies research questions from current diamond phase
  |
  |-- Spawns Research Agent 1 (subagent, lightweight)
  |     Task: "Research competitive landscape for [area]"
  |     Tools: WebSearch, WebFetch
  |     Deliverable: Structured findings
  |
  |-- Spawns Research Agent 2
  |     Task: "Analyze user feedback data for [pattern]"
  |     Tools: Read, Grep
  |     Deliverable: Pattern analysis
  |
  |-- Synthesizes findings
  |-- Updates canvas/opportunities.yml or canvas/landscape.yml
  |-- Runs bias check on combined findings
```

### Rules for Parallel Research
- Use subagents (lightweight) rather than Agent Teams (heavy) for research
- Each research agent gets a specific, bounded question
- Lead agent must triangulate across research agents' findings
- Run `/bias-check` on the COMBINED findings (not just individual)

## Anti-Patterns in Orchestration

**Never parallelize diamond transitions**
Only the lead agent (or human) can progress a diamond through theory gates. Workers never advance diamonds.

**Never let workers write to shared canvas**
Workers read canvas for context but never write. All canvas updates go through the lead agent.

**Never skip integration validation after parallel merge**
Individual worker tests passing does not guarantee integration works. Always test the merged result.

**Never assume worker isolation means independence**
Workers in separate worktrees can still have logical dependencies (shared database schemas, API contracts). Map dependencies before parallelizing.

## Claude Code Agent Teams Setup

To enable Agent Teams (experimental feature):
```json
// In .claude/settings.local.json or environment
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Agent Teams vs Subagents:
- **Subagents**: Quick, focused, report back to main agent. Good for research, bounded tasks.
- **Agent Teams**: Full sessions that can communicate with each other. Good for complex parallel delivery where coordination is needed.
