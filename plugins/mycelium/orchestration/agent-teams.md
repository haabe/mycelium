# Agent Orchestration Patterns

## When to Use Multi-Agent Orchestration

Single-agent is sufficient for most work, and the default. Split work off to another agent only when
one of these holds:
- **The pieces need little from each other and return something compact**: independent research
  questions, delivery slices that touch different files behind a clean interface, solution branches whose
  tests run on disk or network (see `fan-out-fan-in.md` for why a `human` test never goes to a worker).
- **The check must not inherit the reasoning it checks**: a blind reader, judge or adversarial pass
  (`harness/context-management.md`, the blind subagent pattern).
- **The session itself shows it is degrading**: it loses track of earlier results, contradicts its own
  instructions, or picks the wrong tool, and a fresh context would fix it. Name what you saw.

Do not split work because the team is large, because the work belongs to different teams or domains,
or to go faster. Every handback is a summary the lead did not see being made, and details are lost at
each one; work that needs coordination is the work least suited to splitting. When unsure, run it in
the one session first and split only the part that the session demonstrably handles worse.

*(Changed 0.330.0. The list read "Research needs to cover multiple domains simultaneously" and "Time
pressure requires parallel rather than sequential progress". Anthropic's 2026-10-22 article "Building
agents: When to fold subagents into your main agent loop" reports single-loop agents beating subagent
designs on quality, cost and latency in several enterprise deployments, splits by context rather than
by team or problem type, and keeps a subagent only where folding it in scores worse. Its evidence is
enterprise customer-facing agents; it does not cover solo discovery work, where much of the work is
human-time that no agent design runs. The criteria above are the ones that hold in both.)*

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
- Each worker gets clear deliverables, and a turn cap where the runtime has one (`maxTurns` in a Claude
  Code agent definition; there is no time or cost cap, so a time bound is advice)

**What enforces these.** On Claude Code, the guard-state gate refuses a subagent's or in-process
teammate's write to `.claude/canvas/` or `.claude/diamonds/` (0.330.0), which covers "ONLY the lead agent
updates canvas and diamond state" for writes made inside the session. Claude Code documents `agent_id` for
subagents and in-process teammates; a teammate run as a separate process may carry none, and is then not
refused. The other rules, here and in the patterns
below, are the lead's discipline: no hook checks worktree isolation, file overlap, deliverables or
caps.

### Leaf Bakeoff (Structured A/B Testing)

When multiple OST leaves compete for the same opportunity, use the **leaf bakeoff protocol** for structured comparison. Each worker returns a scorecard; the lead agent applies winner selection rules.

See `leaf-bakeoff.md` for: scorecard format, winner selection rules, which read the assumption-test verdicts and never an ICE gap (clear winner, several pass in one segment, segment split, both fail), loser archival, and anti-patterns.

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
// In .claude/settings.json (shared) or .claude/settings.local.json (personal override)
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Agent Teams vs Subagents:
- **Subagents**: Quick, focused, report back to main agent. Good for research, bounded tasks.
- **Agent Teams**: Full sessions that can communicate with each other. For parallel delivery whose slices are independent but large enough to need a session each. Work that needs a lot of coordination between slices is a reason to keep it in one session, not to give each slice a session and pass messages (0.330.0; the line read "Good for complex parallel delivery where coordination is needed").
