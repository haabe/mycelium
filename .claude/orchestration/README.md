# Orchestration — Multi-Agent Coordination

Orchestration defines how Mycelium works in different team configurations, how parallel exploration is managed, and how day-to-day operations run.

## What's Here

### Usage Patterns
- **[modes.md](modes.md)** — Three modes: solo developer (canvas as shared memory with AI), team (canvas committed to git as shared docs), paired (AI as XP pair partner). **Start here.**

### Parallel Exploration
- **[fan-out-fan-in.md](fan-out-fan-in.md)** — How to explore multiple solution branches in parallel using worktree-isolated agents. Diverge, explore independently, converge with structured comparison.
- **[leaf-bakeoff.md](leaf-bakeoff.md)** — When multiple solution leaves compete for the same opportunity, this protocol runs a structured A/B comparison.
- **[agent-teams.md](agent-teams.md)** — Patterns for coordinating multiple agents: scout/builder split, specialist delegation, consensus protocols.

### Operations
- **[operations.md](operations.md)** — Day-to-day patterns: session resumption, canvas maintenance, diamond lifecycle management, memory pruning.
- **[canvas-sync.md](canvas-sync.md)** — Keeping canvas files synchronized across repositories (e.g., framework repo and project repo).
- **[escape-hatch.md](escape-hatch.md)** — Legitimate process bypass for emergencies. Must be documented and "paid back." Not a shortcut — an explicit safety valve.

## When to Use What

| Situation | Use |
|-----------|-----|
| Starting a new session | [operations.md](operations.md) — session resumption |
| Exploring 3 possible solutions | [fan-out-fan-in.md](fan-out-fan-in.md) — parallel worktrees |
| Two solutions look equally good | [leaf-bakeoff.md](leaf-bakeoff.md) — structured comparison |
| Need to skip a gate in an emergency | [escape-hatch.md](escape-hatch.md) — documented bypass |
| Setting up for a team | [modes.md](modes.md) — team mode patterns |
