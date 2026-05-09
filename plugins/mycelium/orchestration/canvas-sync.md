# Canvas Synchronization for Teams

## How Canvas Sync Works

Canvas files are YAML files committed to git. This means:
- Every team member's agent reads the same state
- Changes are tracked, diffable, and PR-reviewable
- Merge conflicts are visible and resolvable
- History shows how product understanding evolved

## Sync Protocol

### Starting a Session
1. `git pull` to get latest canvas state
2. Run `/diamond-assess` to see current state
3. Identify which diamond(s) you'll work on
4. Proceed with your work

### During a Session
- Canvas updates happen as you work (the agent updates yml files)
- Your changes are local until committed

### Ending a Session
1. Commit canvas changes: `git add .claude/canvas/ .claude/harness/decision-log.md .claude/memory/`
2. Push or create PR
3. Canvas + decision log + memory = complete session record

## Conflict Resolution

### Low-Risk Conflicts (Auto-Resolvable)
- Different diamonds updated different canvas files -- no conflict
- Same canvas file but different sections -- YAML merge usually works
- Timestamps or counters -- take the newer value

### High-Risk Conflicts (Human Review Needed)
- Same opportunity updated with contradicting evidence -- team discusses
- Confidence scores differ for the same idea -- use the evidence-backed one
- Strategy changes that affect multiple canvas files -- team alignment meeting

### Resolution Rule
**The person with MORE evidence wins.** If both parties have evidence, discuss and log the decision.

## Best Practices for Teams

1. **Own your diamonds**: Each person works on specific diamonds. Minimizes canvas conflicts.
2. **Commit canvas changes frequently**: Don't batch up a week of canvas updates.
3. **PR-review canvas changes**: They're as important as code changes.
4. **Use decision log**: When others see your canvas changes, the decision log explains WHY.
5. **Run `/diamond-assess` after pulling**: See what changed and what needs attention.
