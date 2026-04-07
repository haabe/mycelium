# Mycelium Hooks System

## 5-Layer Enforcement Architecture

Hooks are registered in `.claude/settings.json` (shared, committed to git). Personal overrides go in `.claude/settings.local.json` (gitignored). Mycelium uses a layered approach where faster/cheaper hooks run first, and expensive semantic checks are reserved for skill-level invocation.

```
Layer 1: PreToolUse gate     (command, ~30 tokens)  — Blocks bad writes before they happen
Layer 2: PostToolUse nudge   (command, ~50 tokens)  — Context-aware reminders after changes
Layer 3: PostToolUseFailure  (prompt, ~200 tokens)  — Reflexion analysis on failures
Layer 4: Stop check          (command, ~50 tokens)  — Guardrail + feedback loop compliance
Layer 5: SessionStart check  (command, ~50 tokens)  — Overdue strategic loop reminders
Layer 6: Skill-level gates   (on-demand, varies)    — Full theory gate evaluation
```

Total hook overhead: ~6,000 tokens/session (negligible vs typical 50K-200K session).

## Active Hooks

### Layer 1: PreToolUse -> Write/Edit/MultiEdit (`gate.sh`)
**Triggers**: Before any code edit to source files
**Type**: `command` (5s timeout)
**Enforces**:
- G-P5: Preflight stamp freshness (corrections.md read recently)
- G-P5: Corrections.md hash consistency (re-read if changed)
- G-S1: Secret detection — regex scan for API keys, tokens, passwords, connection strings in content being written

**Important on secret detection**: The regex patterns in gate.sh are a **fast first-pass tripwire** (~5ms, catches the obvious 80%). For thorough secret scanning, the validation suite should use proper tools (semgrep, gitleaks, trufflehog) which are JiT-detected and configured per tech stack. Both layers are needed:
- gate.sh catches secrets BEFORE they're written to disk
- Validation suite tools catch what regex misses BEFORE commit
- CI/CD pipeline is the final safety net

**Excludes**: `.claude/` directory edits (always allowed)
**Only gates**: `src/`, `scripts/`, `tests/`, `lib/`, `app/`, `pages/`, `components/`, `server/`, `api/`

### Layer 2: PostToolUse -> Write/Edit/MultiEdit (`post-write-nudge.sh`)
**Triggers**: After any successful code edit
**Type**: `command` (3s timeout)
**Does**: Returns context-aware `additionalContext` based on file type:
- UI files (*.tsx, *.jsx, *.vue, *.svelte, *.html) -> Accessibility + error states reminder
- API/server files (*/api/*, */routes/*, */server/*) -> Input validation + OWASP reminder
- Test files -> Positive reinforcement ("Tests updated. Good.")
- Other source -> Generic validation suite reminder

Does NOT block. Nudges the agent toward quality checks by injecting reminders into context.

### Layer 3: PostToolUseFailure -> Bash (reflexion trigger)
**Triggers**: After any Bash command failure
**Type**: `prompt` (15s timeout, ~200 tokens)
**Does**: Forces structured failure analysis:
1. What failed and why?
2. Is this a known pattern from corrections.md?
3. What is the root cause?
4. What specific fix is needed?
5. Should this be logged as a new correction?

Prevents blind retry. Diagnosis first, then fix.

### Layer 4: Stop (`stop-check.sh`)
**Triggers**: When Claude finishes responding
**Type**: `command` (5s timeout)
**Checks**:
- If active diamond is L4 Delivery but `threat-model.yml` is empty -> GUARDRAIL WARNING with `/threat-model` suggestion
- If Downe's 15 principles all "not-assessed" -> GUARDRAIL WARNING with `/service-check` suggestion
- If BVSSH or DORA checks are overdue (>30 days) -> FEEDBACK LOOP WARNING with skill suggestion
- Corrections and decisions count for session summary

Returns warnings via `additionalContext` (does not block). This is the "hybrid" pattern: hook detects the condition, injects a message that tells Claude to run the appropriate skill.

### Layer 5: SessionStart (`session-start.sh`)
**Triggers**: When a session starts or resumes
**Matcher**: `startup|resume`
**Type**: `command` (5s timeout)
**Checks**:
- If BVSSH health check is overdue (>30 days or never done) -> Reminder to run `/bvssh-check`
- If DORA metrics are overdue (>30 days since last measurement) -> Reminder to run `/dora-check`
- Reports corrections count for awareness

Returns `additionalContext` so the agent knows about overdue strategic feedback loops from the start of the session. Part of the four-speed feedback loop system (see `.claude/engine/feedback-loops.md`).

### Layer 6: Skill-Level Gates (not hooks)
**Triggers**: When `/diamond-progress` is explicitly invoked
**Does**: Full theory gate evaluation across all 11 gates (Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, DORA, Corrections). Requires judgment, context, and multiple canvas file reads.

## Hook Types (by cost)

| Type | Cost | Latency | Use For |
|------|------|---------|---------|
| `command` | ~30 tokens | <100ms | File checks, regex, deterministic rules |
| `http` | ~30 tokens + network | <500ms | Centralized enforcement services |
| `prompt` | ~200 tokens | 2-5s | Semantic evaluation (is this safe?) |
| `agent` | ~500-3000 tokens | 10-60s | Multi-step verification with tool access |

## Design Principles

1. **Hooks nudge, skills judge** -- Hooks catch binary violations and inject reminders. Skills have full judgment for nuanced evaluation.
2. **Never block on semantics at PreToolUse** -- False positive blocks infuriate users. Use PostToolUse additionalContext to nudge instead.
3. **Use `if` field for zero-overhead filtering** -- Evaluated before the hook process spawns. Non-matching calls cost nothing.
4. **command > prompt > agent** -- Always prefer the cheapest handler that does the job.
5. **Stop hooks for hybrid enforcement** -- Detect conditions mechanically, suggest skills for resolution.

## Available Hook Events (28 in Claude Code 2026)

Key ones for Mycelium:
- `PreToolUse` -- Can block (exit 2 or permissionDecision: deny)
- `PostToolUse` -- Can inject additionalContext
- `PostToolUseFailure` -- Can trigger reflexion
- `Stop` -- Can block Claude from stopping (exit 2) or inject warnings
- `TaskCompleted` -- Can block task completion (DoD enforcement)
- `SubagentStop` -- Can prevent subagents from finishing prematurely
- `SessionStart` -- Can inject session context

Full reference: https://code.claude.com/docs/en/hooks

## Helper Scripts (Not Standalone Hooks)

### preflight.sh
Called BY `gate.sh` when the preflight stamp is expired/missing. Creates a stamp file with corrections.md hash and timestamp. NOT a standalone hook -- it's a helper that gate.sh invokes internally. Users can also run it manually: `bash .claude/hooks/preflight.sh`
