---
name: canvas-sync
description: "Synchronize canvas state across team sessions via git. Ensures all team members see the same product knowledge."
---

# Canvas Sync

## When to Use
- Starting a new session (pull latest canvas)
- Ending a session (commit canvas changes)
- After team discussion that changes product direction
- When canvas conflicts arise from parallel work

## Workflow

### Pull Latest
```
git pull origin main
```
Then run `/diamond-assess` to see what changed.

### Commit Changes
```
git add .claude/canvas/ .claude/harness/decision-log.md .claude/memory/
git commit -m "canvas: [brief description of what changed and why]"
```

### Conflict Resolution
- Different canvas files: auto-merges (no conflict)
- Same file, different sections: usually auto-merges
- Same field conflicting: person with MORE evidence wins
- When uncertain: discuss as team, log decision
