# `.claude/state/` — Runtime Ephemeral State

This directory holds **ephemeral runtime state** that hooks and skills update during active sessions. It is **not committed to version control** (see `.gitignore`).

## Data Format Philosophy

Mycelium separates human-editable product knowledge from machine-readable runtime state:

| Store | Format | Why |
|---|---|---|
| **Canonical state** (`.claude/canvas/`, `.claude/diamonds/`, `.claude/harness/decision-log.md`) | YAML + Markdown | Humans edit these — comments, multi-line strings, and readable structure matter |
| **Runtime state** (this directory) | JSON + JSONL | Machines read these — hooks need zero-dependency parsing via Python stdlib `json` |

This keeps hooks dependency-free (no PyYAML at runtime) while preserving canvas readability. CI-time validation (which has richer dependencies) handles YAML canvas files with PyYAML + jsonschema.

## Distinction from Canonical State

| Store | Location | Purpose | Committed to git? |
|---|---|---|---|
| **Canonical state** | `.claude/diamonds/active.yml`, `.claude/canvas/*.yml`, `.claude/harness/decision-log.md` | Versioned product knowledge and diamond state | Yes |
| **Runtime state** | `.claude/state/*` (this directory) | Session-level transient state that hooks read/write | No |

## Files in This Directory

| File | Format | Written by | Read by | Purpose |
|---|---|---|---|---|
| `active-execution.json` | JSON | `/diamond-progress` (L4 only) | `scope-gate.sh` (PreToolUse) | Declares `in_scope_paths` for the current L4 delivery work |
| `change-log.jsonl` | JSONL | `change-log.sh` (PostToolUse) | Manual review + `stop-check.sh` | Append-only audit trail of code modifications |
| `diamond-state-audit.jsonl` | JSONL | `diamond-state-audit.sh` (PostToolUse) | `stop-check.sh` | Append-only log of direct edits to diamond state files |
| `preflight-stamp` | Text | `preflight.sh` | `gate.sh` | Tracks corrections.md read freshness (TTL 4 hours) |

## Fail-Closed Policy

Hooks that depend on state files should **fail closed** when state is corrupt: prefer blocking the edit over silently allowing it. This protects against scenarios where broken infrastructure silently disables enforcement.

Exceptions: observability-only hooks (change-log, diamond-state-audit) may fail open, since their purpose is to create an audit trail, not to enforce policy.

## When State Gets Cleared

- `active-execution.yml` is overwritten by each `/diamond-progress` call when entering L4
- `change-log.jsonl` and `diamond-state-audit.jsonl` are append-only; rotate manually at 100MB or drop at session boundaries
- `preflight-stamp` is regenerated every 4 hours when corrections.md is re-read

## Do Not Commit

This directory is in `.gitignore`. If you see it in `git status`, something is wrong. Canvas files and decision logs are the canonical, committable state — not these files.
