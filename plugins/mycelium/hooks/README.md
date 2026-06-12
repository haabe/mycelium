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

**Sibling PreToolUse hooks (same Write/Edit/MultiEdit matcher, run alongside `gate.sh`):**
- **`scope-gate.sh`** — scope enforcement (keeps edits within the declared work scope).
- **`framework-guard.sh`** — blocks edits to FRAMEWORK-classified files in *dogfood instances* of an upstream Mycelium repo (active only when `.claude/state/upstream.json` exists). Also wired on `Bash` and MCP-filesystem matchers.
- **`autonomous-evidence-guard.sh`** (v0.42.0) — evidence-integrity enforcement. **Only fires in a DECLARED autonomous run** (env `MYCELIUM_AUTONOMOUS_RUN`, or `autonomous: true` in `diamonds/active.yml`); a strict no-op in every interactive session. Hard-blocks (`permissionDecision: deny`) any write that introduces `source_class: external_human|external_data`, `validated: true`, or `evidence_type` above `speculation` into `.claude/canvas/*.yml`, `.claude/diamonds/*.yml`, or their `mycelium-state/` mirror — the fabrication a sub-Fable-5 model committed in the opp-011 Stage A run (2026-06-11). Also wired on the MCP-filesystem write/edit matcher. **Registered on all three runtime surfaces** (`hooks.json`, `hooks.codex.json`, `hooks.cursor.json`) as of v0.44.1 — the 2026-06-12 gap analysis found the Codex/Cursor registrations missing, leaving those surfaces with zero autonomous evidence enforcement. See `engine/autonomous-mode.md`.

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
**Does**: Full theory gate evaluation across all 13 gates (Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory, Explainability). Requires judgment, context, and multiple canvas file reads.

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

---

## v0.9.0 Additions: Computational Enforcement Layer

v0.9.0 added three new hooks and one new wrapper script, all focused on closing the gap Daniel Bentes identified in the BDSK comparison: Mycelium had strong upstream thinking discipline but weak downstream execution enforcement.

### scope-gate.sh (PreToolUse — BLOCK when active)
**Triggers**: PreToolUse on Edit/Write/MultiEdit
**Type**: `command` (5s timeout)
**Tier**: BLOCK (when an active L4 execution exists)
**Fail policy**: **Fail-closed** (deny on state corruption, exit 2 on script failure)

When `.claude/state/active-execution.json` exists and declares `in_scope_paths`, this hook blocks edits to files outside the declared scope. Mirrors BDSK's `check-scope.sh` pattern. Delegates to `.claude/scripts/scope_check.py` (Python stdlib only — no PyYAML).

When no `active-execution.json` exists, the hook is a no-op (allows all edits). This is the common case before L4 delivery work begins.

### change-log.sh (PostToolUse — observability)
**Triggers**: PostToolUse on Edit/Write/MultiEdit
**Type**: `command` (3s timeout)
**Tier**: Observability (not BLOCK, not NUDGE — pure audit trail)
**Fail policy**: Fail-open (audit failures never block code changes)

Appends one JSONL line per code modification to `.claude/state/change-log.jsonl`. Each entry includes timestamp, tool, file path, session_id, and active diamond_id (if any). Mirrors BDSK's audit trail. Used for post-hoc forensic analysis: "what did the agent touch during diamond X?"

### diamond-state-audit.sh (PostToolUse — observability)
**Triggers**: PostToolUse on Edit/Write/MultiEdit (filtered to `.claude/diamonds/*.yml` paths)
**Type**: `command` (3s timeout)
**Tier**: Observability (creates friction without blocking)
**Fail policy**: Fail-open

Addresses dogfood report finding M1: "agent bypassed `/diamond-progress` by hand-editing diamonds/active.yml." This hook logs every direct edit to diamond state files in `.claude/state/diamond-state-audit.jsonl`. The `stop-check.sh` hook surfaces the count at session end as a reminder that `/diamond-progress` is the idiomatic path.

This is **not** a guardrail — it does NOT block. The hook cannot reliably distinguish between edits from `/diamond-progress` (legitimate) and direct agent edits (bypass). Observability creates traceability without false positives. The agent learns from seeing the audit count, not from being blocked.

### reflexion-gate.sh (PostToolUseFailure — filtered NUDGE)
**Triggers**: PostToolUseFailure on Bash
**Type**: `command` (10s timeout)
**Tier**: NUDGE (filtered to project-relevant failures only)
**Fail policy**: Fail-open

Replaced the inline reflexion prompt in v0.8.2. Filters out failures that are not project-relevant (cwd outside `$CLAUDE_PROJECT_DIR`, environmental introspection commands like `which`/`pwd`/`hostname`). Addresses dogfood G4 and M4: "Reflexion fired on a failure unrelated to the project, demanded writing to the wrong corrections file."

When the failure IS project-relevant, emits the reflexion prompt with two-memory-system guidance: project-relevant mistakes go in `corrections.md`, agent-user learnings go in auto-memory, environmental failures don't go anywhere.

---

## Fail-Closed vs Fail-Open Policy (v0.9.0)

Different hooks have different failure semantics. The choice is deliberate.

**Fail-closed** (block on failure) — used for **security and scope enforcement**:
- `gate.sh` — exit 2 on preflight stamp corruption
- `scope-gate.sh` — deny via JSON when state file is corrupt; exit 2 on script failure

**Rationale**: a silently disabled enforcement hook is worse than no hook. If `gate.sh` crashes, secret detection is gone. If `scope-gate.sh` cannot read state, scope enforcement is gone. These hooks must announce their failure by blocking the operation.

**Fail-open** (allow on failure) — used for **observability and nudging**:
- `post-write-nudge.sh`, `change-log.sh`, `diamond-state-audit.sh`, `reflexion-gate.sh`, `stop-check.sh`, `session-start.sh`

**Rationale**: an audit log failure should never block a code change. The cost of missing a nudge is small; the cost of blocking a legitimate edit because logging broke is large.

---

## Dependency Philosophy (v0.9.0)

**All Mycelium hooks use Python stdlib only.** No PyYAML, no jsonschema, no Ruby, no jq. The `python3` binary is the only runtime dependency, and it's already a Mycelium baseline.

Why: hooks fire on every code edit. Requiring users to `pip install` would create a silent-failure footgun on fresh clones. Stdlib-only means zero setup after `npx degit haabe/mycelium`.

**Runtime state files are JSON** (not YAML), specifically so hooks can parse them with `json.load()` from stdlib. Canvas files (which hooks don't read at runtime) stay YAML for human editing. CI validation handles canvas YAML with PyYAML (via `requirements-ci.txt`).

See `../state/README.md` for the full data format philosophy.

---

## Hook Inventory Summary (v0.9.0)

| Hook | Event | Tier | Fail policy |
|---|---|---|---|
| `gate.sh` | PreToolUse Edit/Write/MultiEdit | BLOCK | **Fail-closed** |
| `scope-gate.sh` | PreToolUse Edit/Write/MultiEdit | BLOCK (when active) | **Fail-closed** |
| `post-write-nudge.sh` | PostToolUse Edit/Write/MultiEdit | NUDGE | Fail-open |
| `change-log.sh` | PostToolUse Edit/Write/MultiEdit | Observability | Fail-open |
| `diamond-state-audit.sh` | PostToolUse Edit/Write/MultiEdit | Observability | Fail-open |
| `reflexion-gate.sh` | PostToolUseFailure Bash | NUDGE (filtered) | Fail-open |
| `stop-check.sh` | Stop | NUDGE + warning | Fail-open |
| `session-start.sh` | SessionStart startup/resume | NUDGE | Fail-open |
| `preflight.sh` | (called by gate.sh) | Helper | N/A |

---

## References

- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html) — the "computational vs inferential" distinction this whole architecture is built around
- [Daniel Bentes — BDSK comparison feedback](../../CONTRIBUTORS.md) — the inspiration for scope enforcement and trace audit patterns
- `../state/README.md` — runtime state philosophy
- `../tests/validate-template.sh` — the structural integrity validator (a different kind of computational enforcement)
