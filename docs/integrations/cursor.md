# Using Mycelium with Cursor (1.7+)

**Audience**: developers using [Cursor](https://cursor.com) as their primary AI coding runtime who want Mycelium's product-thinking discipline and runtime enforcement on top.
**Time to read**: 4 min.
**Last updated**: 2026-05-26.
**Status**: Mycelium's full hook surface runs on Cursor 1.7+. No degraded primitives — Cursor's hook model is a superset of Claude Code's.

## Why this fits cleanly

Cursor 1.7 (released 2025-Q4) added a hook system that closely mirrors Claude Code's, including the native `postToolUseFailure` event that opencode still lacks. Cursor explicitly exports `CLAUDE_PROJECT_DIR` as an environment alias to signal that Claude Code hook scripts are intended to run unmodified. Mycelium's twelve hook scripts use that env var plus stdin JSON fields (`tool_name`, `tool_input`, `file_path`, `cwd`, `command`) that match Cursor's payload field names byte-for-byte (verified against [cursor.com/docs/agent/hooks](https://cursor.com/docs/agent/hooks) 2026-05-26).

The only translation needed is event-name casing (Claude Code `PreToolUse` → Cursor `preToolUse`) and Claude Code's `UserPromptSubmit` → Cursor's `beforeSubmitPrompt`. Ship as a parallel `hooks.cursor.json`; the scripts themselves are reused verbatim.

## What works on Cursor today

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Fully portable | Pure files. |
| `CLAUDE.md` / `AGENTS.md` instructions | ✅ Read | Cursor reads `.cursorrules` and `AGENTS.md`; Mycelium ships both. |
| Skills (58 skills, frontmatter-driven discovery) | ✅ Native | Cursor honors skill discovery from `.claude/skills/` when configured. |
| Validators (`validate_canvas.py`, `validate-template.sh`) | ✅ Run unchanged | Harness-agnostic. |
| MCP server integrations | ✅ Native | Both speak MCP. |
| Pre-task gate (Read-before-Edit, preflight, scope, framework-guard) | ✅ Hook-enforced | `preToolUse` ≡ Claude `PreToolUse`. |
| Post-write nudge / change-log / diamond-audit | ✅ Hook-enforced | `postToolUse` ≡ Claude `PostToolUse`. |
| Reflexion loop (auto-retry on tool failure) | ✅ Hook-enforced | `postToolUseFailure` fires natively. |
| Pre-task context injection (G-P-pre) | ✅ Hook-enforced | `beforeSubmitPrompt` ≡ Claude `UserPromptSubmit`. |
| Session-start preflight | ✅ Hook-enforced | `sessionStart` ≡ Claude `SessionStart`. |
| Stop check (Mycelium guardrails + feedback loops) | ✅ Hook-enforced | `stop` ≡ Claude `Stop`. |

**Net**: Mycelium-on-Cursor is functionally equivalent to Mycelium-on-Claude-Code at the hook layer. No degraded primitives.

## Setup

```bash
# 1. Install Cursor 1.7 or later from https://cursor.com
# 2. Install Mycelium in your project (or use the plugin install)
git clone https://github.com/haabe/mycelium
cd mycelium

# 3. Wire the Cursor hook config
mkdir -p .cursor
ln -s "$PWD/plugins/mycelium/hooks/hooks.cursor.json" .cursor/hooks.json
#   OR copy it if you prefer to detach:
#   cp plugins/mycelium/hooks/hooks.cursor.json .cursor/hooks.json

# 4. Confirm CLAUDE_PROJECT_DIR is exported (Cursor 1.7 sets this automatically;
#    fall back to a shell-level export if you run hooks from a non-Cursor terminal)
echo "$CLAUDE_PROJECT_DIR"

# 5. Restart Cursor. Hooks fire on first tool call.
```

For user-level (cross-project) install, drop the same file at `~/.cursor/hooks.json`.

## Event-name mapping

| Claude Code (PascalCase) | Cursor (camelCase) |
|---|---|
| `PreToolUse` | `preToolUse` |
| `PostToolUse` | `postToolUse` |
| `PostToolUseFailure` | `postToolUseFailure` |
| `SessionStart` | `sessionStart` |
| `Stop` | `stop` |
| `UserPromptSubmit` | `beforeSubmitPrompt` |
| `PreCompact` | `preCompact` |

Stdin payload fields (`tool_name`, `tool_input`, `file_path`, `cwd`, `command`, `tool_response`) align. Cursor adds `workspace_roots`, `conversation_id`, `generation_id`, `cursor_version` — Mycelium scripts don't read those today.

## Differences from Claude Code

- `failClosed: true` on safety-critical hooks (gate, scope-gate, framework-guard) is recommended; it's Cursor's explicit fail-closed switch. Set in `hooks.cursor.json`.
- Cursor's `beforeShellExecution` / `beforeReadFile` / `afterFileEdit` are *more granular* than Claude Code's tool-level hooks. Mycelium doesn't currently use them; future tightening (e.g., per-file pre-edit Read-state checks) could land here without re-architecting.
- Tab-completion hooks (`beforeTabFileRead`, `afterTabFileEdit`) are Cursor-only and out of scope for Mycelium today.

## Honest gaps

None at the hook layer as of 2026-05-26. If Cursor changes its event vocabulary or payload field names in a future release, the `hooks.cursor.json` mapping will need a touch-up but the scripts won't.

The framework-side gaps (substrate naming bias toward `.claude/`, skill namespacing) are tracked in the [substrate-neutralization audit](../receipts/cases/2026-05-16-phase0-substrate-audit.md) and apply equally across runtimes.

## Related receipts

- [opencode integration](opencode.md) — calibration baseline for "what a harder port looks like"
- [Phase 0 substrate-neutralization audit](../receipts/cases/2026-05-16-phase0-substrate-audit.md)
