# Using Mycelium with OpenAI Codex CLI

**Audience**: developers using [Codex CLI](https://github.com/openai/codex) as their primary AI coding runtime who want Mycelium's product-thinking discipline and runtime enforcement.
**Time to read**: 4 min.
**Last updated**: 2026-05-26.
**Status**: Mycelium's full hook surface runs on Codex CLI. One minor gap (no native `PostToolUseFailure` event) is covered by a shim script.

## Why this fits cleanly

Codex CLI's hook system uses Claude Code's exact event vocabulary — `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, plus `PermissionRequest`. The stdin payload field names (`tool_name`, `tool_input`, `cwd`, `tool_response`, `hook_event_name`) match Claude Code's byte-for-byte (verified against [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks) 2026-05-26). Mycelium's twelve hook scripts run unmodified.

The one surface difference: Codex has no native `PostToolUseFailure`. Failures still surface in `PostToolUse` with the error captured in `tool_response`. A small shim script (`codex-postfailure-shim.sh`) inspects `tool_response` and delegates to `reflexion-gate.sh` only on failure.

## What works on Codex today

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Fully portable | Pure files. |
| `AGENTS.md` instructions | ✅ Read natively | Codex's primary; Mycelium ships it. |
| Skills (58 skills, frontmatter-driven discovery) | ⚠️ Depends on Codex skill discovery | Codex has plugin manifests (`.codex-plugin/plugin.json`); skill-discovery glue may be needed for full parity. Substrate loads either way. |
| Validators (`validate_canvas.py`, `validate-template.sh`) | ✅ Run unchanged | Harness-agnostic. |
| MCP server integrations | ✅ Native | Both speak MCP. |
| Pre-task gate (Read-before-Edit, preflight, scope, framework-guard) | ✅ Hook-enforced | `PreToolUse` identical event + payload. |
| Post-write nudge / change-log / diamond-audit | ✅ Hook-enforced | `PostToolUse` identical. |
| Reflexion loop (auto-retry on tool failure) | ✅ Hook-enforced via shim | `codex-postfailure-shim.sh` filters `PostToolUse` for error in `tool_response`. |
| Pre-task context injection (G-P-pre) | ✅ Hook-enforced | `UserPromptSubmit` identical. |
| Session-start preflight | ✅ Hook-enforced | `SessionStart` identical. |
| Stop check (Mycelium guardrails + feedback loops) | ✅ Hook-enforced | `Stop` identical. |

**Net**: Mycelium-on-Codex is functionally equivalent to Mycelium-on-Claude-Code at the hook layer once the shim is in place.

## Setup

```bash
# 1. Install Codex CLI (see github.com/openai/codex for current method)
# 2. Install Mycelium in your project (or use the plugin install)
git clone https://github.com/haabe/mycelium
cd mycelium

# 3. Wire the Codex hook config
mkdir -p .codex
ln -s "$PWD/plugins/mycelium/hooks/hooks.codex.json" .codex/hooks.json
#   OR copy:
#   cp plugins/mycelium/hooks/hooks.codex.json .codex/hooks.json

# 4. Codex does NOT auto-export CLAUDE_PROJECT_DIR. Set it once in your shell:
#    (add to ~/.zshrc or ~/.bashrc; or wrap each codex invocation)
export CLAUDE_PROJECT_DIR="$(pwd)"

# 5. Verify hook discovery
codex --help  # confirm CLI is installed
# Hook scripts will fire on first tool call.
```

For user-level (cross-project) install, drop the same file at `~/.codex/hooks.json`. If you prefer TOML, the same definitions can be inlined under `[[hooks.PreToolUse]]` etc. in `~/.codex/config.toml`.

## The PostToolUseFailure gap

Codex's hook events list does not include a dedicated failure event. Tool failures still produce a `PostToolUse` invocation; the `tool_response` field carries the error.

Mycelium ships [`codex-postfailure-shim.sh`](../../plugins/mycelium/hooks/codex-postfailure-shim.sh) which:
1. Receives Codex's `PostToolUse` JSON on stdin.
2. Inspects `tool_response` for any of: `success: false`, non-empty `error`, non-zero `exit_code`, `is_error: true`.
3. On success, exits 0 immediately (no-op).
4. On failure, pipes the original stdin through to `reflexion-gate.sh` for the standard project-relevance filter and reflexion prompt.

This is mechanically equivalent to a native `PostToolUseFailure` for Mycelium's purposes. The shim is ~25 lines; the only risk is false-negatives if Codex emits a failure shape the shim doesn't recognize. If that happens, extend the field list at the top of the shim.

## Event-name mapping

No mapping needed — Codex uses PascalCase event names identical to Claude Code.

| Claude Code | Codex | Notes |
|---|---|---|
| `PreToolUse` | `PreToolUse` | Identical. |
| `PostToolUse` | `PostToolUse` | Identical. |
| `PostToolUseFailure` | — | Emulated via `PostToolUse` + shim. |
| `SessionStart` | `SessionStart` | Identical. |
| `Stop` | `Stop` | Identical. |
| `UserPromptSubmit` | `UserPromptSubmit` | Identical. |
| `PreCompact` / `PostCompact` | `PreCompact` / `PostCompact` | Codex adds `PostCompact`; Mycelium doesn't use it yet. |
| (n/a) | `PermissionRequest` | Codex-only; out of scope for Mycelium today. |

## Honest gaps

- **No native `PostToolUseFailure`** — covered by the shim above. If/when Codex adds the event, drop the shim and point the hook at `reflexion-gate.sh` directly.
- **Skill discovery** — Codex's plugin manifest format (`.codex-plugin/plugin.json`) differs from Claude Code's; the 58 skills load as files but `/skill-name` invocation parity may require a Codex-side skill loader. Mycelium's slash commands work; full parity needs verification.
- **`CLAUDE_PROJECT_DIR` not auto-exported** — set it in your shell. (Cursor exports this alias automatically; Codex doesn't.)

Verified primitives match against [Codex hooks docs](https://developers.openai.com/codex/hooks) 2026-05-26. End-to-end Mycelium-on-Codex run not yet executed — adopt and report friction back via PR on `docs/receipts/cases/`.

## Related receipts

- [Cursor integration](cursor.md) — sibling adapter; calibration on "trivial port"
- [opencode integration](opencode.md) — calibration on "harder port" (deferred behind 3 upstream issues)
