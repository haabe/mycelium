# Mycelium Hooks System

Hooks are registered in `.claude/settings.local.json` under the `"hooks"` key.

## Active Hooks

### 1. PreToolUse -> Write/Edit/MultiEdit (preflight gate)
- **Triggers**: Before any code edit to source files
- **Type**: `command` (lightweight, 5s timeout)
- **What it does**: Checks if preflight stamp exists and is fresh. If expired or missing, blocks the edit and reminds agent to read corrections.md and run validation.
- **Excludes**: `.claude/` directory edits (always allowed)
- **Only gates**: `src/`, `scripts/`, `tests/`, `lib/`, `app/`, `pages/`, `components/`

### 2. PostToolUse -> Write/Edit/MultiEdit (validation reminder)
- **Triggers**: After any code edit
- **Type**: `command` (2s timeout)
- **What it does**: Reminds agent to run validation and check Definition of Done

### 3. PostToolUseFailure -> Bash (reflexion trigger)
- **Triggers**: After any Bash command failure
- **Type**: `prompt` (15s timeout)
- **What it does**: Forces structured failure analysis: what failed, why, root cause, fix needed, should it be logged as a correction

### 4. Stop (session end logger)
- **Triggers**: When session ends
- **Type**: `command` (5s timeout)
- **What it does**: Counts corrections accumulated during session

## Hook Types (lightest to heaviest)
1. **command** -- Runs shell script (~30 tokens overhead)
2. **prompt** -- Single-turn LLM eval (~200 tokens overhead)
3. **agent** -- Spawns subagent with tools (~500-3000 tokens overhead)

## Performance Rules
- Use `if` field to filter before spawning processes
- Use `once: true` for one-shot reminders
- Use `async: true` for non-blocking side effects
- Prefer `command` over `prompt` over `agent`
