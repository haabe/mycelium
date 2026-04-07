# Mycelium Usage Modes

## Solo Developer Mode

A single developer interacting with the Mycelium agent.

### How It Works
- The canvas IS your shared product knowledge (between you and the agent)
- All diamonds are managed in a single Claude Code session
- The decision log serves as your memory across sessions
- The agent is your product thinking partner -- it challenges assumptions and enforces discipline
- Corrections.md accumulates learning across your sessions

### Workflow
1. Start: `/interview` (first time) or `/diamond-assess` (continuing)
2. Work through diamonds at your own pace
3. Canvas files are your documentation
4. Commit canvas changes alongside code changes

### Tips
- Don't skip discovery diamonds even as a solo developer -- bias is strongest when unchecked
- Use `/devils-advocate` before major decisions -- you don't have teammates to challenge you
- Use `/bias-check` before user research -- without a team, confirmation bias goes unchallenged
- The decision log is especially valuable solo -- future-you will thank present-you

## Team Mode

Multiple developers sharing the same Mycelium-enabled repository.

### How It Works
- Canvas files are committed to git -- they ARE the team's product documentation
- Any team member starting a Claude Code session gets full product context from the canvas
- The decision log captures WHY decisions were made (critical for onboarding)
- Corrections.md and patterns.md capture team-level learning
- Different team members can work on different diamonds simultaneously

### Knowledge Synchronization
- The canvas + decision log + memory files REPLACE traditional wikis and Confluence pages
- When any team member runs `/diamond-assess`, they see the same state
- Canvas updates are PR-reviewed just like code changes
- BVSSH health and DORA metrics are team-level indicators

### Parallel Work Patterns

**Different diamonds (most common):**
```
Developer A: L4 delivery diamond (Feature X)
Developer B: L2 discovery diamond (Opportunity Y)
Developer C: L3 solution design (Problem Z)
```
No conflicts because different diamonds touch different canvas sections.

**Same diamond (needs coordination):**
- Use Claude Code Agent Teams or worktree isolation
- Lead session manages diamond state
- Worker sessions get their own branches
- Merge via PR review

### Canvas Conflict Resolution
- Canvas files are YAML -- merge conflicts are visible and resolvable
- Rule: the person with MORE evidence wins a conflict
- When in doubt: discuss as a team, log the decision

### Onboarding New Team Members
1. New member reads CLAUDE.md (system overview)
2. Reads canvas/purpose.yml (why we exist)
3. Reads canvas/north-star.yml (what success looks like)
4. Reads canvas/opportunities.yml (what we've discovered)
5. Reads harness/decision-log.md (why decisions were made)
6. Runs `/diamond-assess` (where are we now, what needs attention)

The onboarding IS reading the canvas. No separate onboarding docs needed.

## Scaling Patterns

| Team Size | Orchestration | Canvas Management | Agent Pattern |
|-----------|--------------|-------------------|---------------|
| 1 (solo) | Sequential diamonds, subagents for research | Direct edits | Single session |
| 2-4 (small) | Parallel diamonds per person | PR-reviewed canvas changes | Independent sessions |
| 5-10 (medium) | Lead coordinates, parallel delivery | PR-reviewed, diamond ownership | Agent Teams for shared delivery |
| 10+ (large) | Multiple leads per domain, platform team | Domain-owned canvas sections | Full agent orchestration |

## Ceremony Adaptation

### Solo
- No ceremonies needed -- the canvas IS the ceremony
- `/bvssh-check` weekly (self-discipline)
- `/retrospective` after each delivery diamond completes

### Small Team (2-4)
- Weekly `/diamond-assess` as a team (async or sync)
- PR reviews include canvas changes
- `/bvssh-check` bi-weekly
- `/retrospective` after major milestones

### Medium+ Team (5+)
- Weekly `/diamond-assess` per domain area
- Canvas sections owned by specific teams
- Monthly `/bvssh-check` across the whole product
- Sprint-level `/retrospective` per stream-aligned team
- Quarterly `/wardley-map` review for strategic alignment
