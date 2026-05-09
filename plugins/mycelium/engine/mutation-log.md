# Canvas Mutation Log

Append-only audit trail of every canvas change. Enables checkpoint-based replay when a bad assumption is discovered during diamond regression.

*Inspired by: greyhaven-ai/autocontext mutation_log.py — every knowledge change recorded as JSONL with generation, timestamp, and payload.*

## Purpose

Canvas files are edited in-place. The `_meta` block tracks version and last-validated date, but not *what changed, when, or why*. When a diamond regresses, there's no way to replay the canvas to its state at a specific decision point.

The mutation log fills this gap: every canvas write is appended as a single JSONL line, enabling:
- **Replay**: Reconstruct canvas state at any point in time
- **Audit**: See which evidence triggered which canvas change
- **Regression support**: When a diamond regresses, identify which canvas mutations to revert
- **Drift detection**: Spot canvas changes that lack evidence (mutations without `evidence_ref`)

## Format

File: `canvas/mutation_log.jsonl`

Each line is a JSON object:

```json
{
  "ts": "2026-04-21T01:30:00Z",
  "file": "canvas/opportunities.yml",
  "field": "solutions[0].confidence",
  "old": 0.3,
  "new": 0.45,
  "reason": "Assumption test validated desirability",
  "evidence_ref": "assumption-test-2026-04-21",
  "diamond": "l2-opp-discover",
  "skill": "/assumption-test",
  "session_id": "abc123"
}
```

### Required Fields

| Field | Description |
|-------|------------|
| `ts` | ISO 8601 timestamp |
| `file` | Canvas file path (relative to repo root) |
| `reason` | Why this change was made (one sentence) |

### Optional Fields

| Field | Description |
|-------|------------|
| `field` | Specific YAML path within the file (dot notation) |
| `old` | Previous value |
| `new` | New value |
| `evidence_ref` | Link to evidence source |
| `diamond` | Diamond ID and phase |
| `skill` | Skill that triggered the change |
| `session_id` | For grouping related mutations |

## When to Write

Skills that update canvas files SHOULD append a mutation log entry. Priority order:
1. **Confidence changes** — always log (these gate progression)
2. **Evidence additions** — always log (these justify confidence)
3. **Structural changes** (new components, removed entries) — always log
4. **Minor edits** (typo fixes, formatting) — skip

## Size Management

- Cap at 1000 entries. When exceeded, checkpoint: save current canvas state as a snapshot (`canvas/snapshots/YYYY-MM-DD.tar.gz`), then truncate the log to the last 200 entries.
- Checkpointing is manual (run during `/canvas-health`), not automatic.

## Integration

- `/canvas-update` and `/canvas-health` should append entries
- `/diamond-progress` regression path should read the log to identify revert candidates
- `/retrospective` can summarize mutation patterns for the delivery increment

## What This Is NOT

- Not a replacement for git history (git tracks file-level diffs; this tracks semantic changes)
- Not a database (it's append-only JSONL, not queryable beyond grep)
- Not required for Mycelium to function (it's an enhancement, not a dependency)
