# Using Mycelium with opencode (self-hosted)

**Audience**: developers who want Mycelium's product-thinking discipline without committing to Claude Code as the runtime — typically because of pricing, vendor lock-in, or a preference for self-hosted local models.
**Time to read**: 6 min.
**Last updated**: 2026-05-16.
**Status**: Mycelium works on opencode as a substrate-portable framework. Three runtime safety mechanisms that Mycelium relies on in Claude Code do not fire on opencode today. Honest details below.

## Why this might fit

The AI coding scene in mid-2026 has visible tension around pricing: subscription tiers shifting, per-token costs accumulating, and a steady drift toward self-hosted setups (laptop, VPS, dedicated inference box). [opencode](https://github.com/anomalyco/opencode) is the most-cited Claude Code alternative — provider-agnostic, TUI-first, runs against Anthropic, OpenAI, Google, or local providers via Ollama or LM Studio.

If you're already moving toward self-hosted AI development workflow, Mycelium can come along. The framework's substrate — the canvas, memory, decision-log, harness docs, validators, and 49 skills — is harness-neutral. It runs verbatim on opencode. Three runtime-discipline mechanisms (described below) are Claude-Code-specific today; on opencode they degrade to **prompt-level guidance to the model** rather than structural enforcement. Capable models will follow the guidance; small models may not.

This page tells you what works, what doesn't, how to set it up, and which model sizes are worth your time.

## What works on opencode today

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Fully portable | Pure files. opencode and Claude Code both read them. |
| `CLAUDE.md` instructions | ✅ Read as fallback | `AGENTS.md` is opencode's primary, `CLAUDE.md` is the fallback. Mycelium ships both. |
| Skills (49 skills, frontmatter-driven discovery) | ✅ Via plugin | Install the [`opencode-agent-skills`](https://github.com/joshuadavidthomas/opencode-agent-skills) plugin (one config line) and opencode scans `.claude/skills/` plus `~/.claude/plugins/cache/` natively. |
| Validators (`validate_canvas.py`, `validate-template.sh`) | ✅ Run unchanged | Python + Bash; harness-agnostic. |
| MCP server integrations | ✅ Native | Both runtimes speak MCP. |
| Slash command invocation | ⚠️ Flat names | opencode commands are flat (`/skill-name`), no `mycelium:` namespace prefix. Cosmetic difference. |
| Read-before-Edit safety | ⚠️ Prompt-level only | The precondition is in the tool description shown to the model, not enforced by the runtime. A model that ignores the hint will edit without reading. See [issue #27901](https://github.com/anomalyco/opencode/issues/27901). |
| Reflexion loop (auto-retry on tool failure) | ⚠️ Failure event not fired | `tool.execute.after` is success-only; failures bypass the hook stream. Reflexion has no structural trigger today. See [issue #27900](https://github.com/anomalyco/opencode/issues/27900). |
| Pre-task context injection (G-P-pre) | ⚠️ Headless mode | `tui.prompt.append` is silent in `opencode run`. Pre-task context lives in `AGENTS.md` prose, which capable models read; structural enforcement isn't available. See [issue #27899](https://github.com/anomalyco/opencode/issues/27899). |

**Net**: Mycelium loads on opencode and the framework's *discipline* runs as model-following-instructions. The framework's *guarantees* (the three ⚠️ rows) are runtime-specific and currently Claude-Code-only. If your model is capable enough to follow instructions reliably, the gap between "guarantee" and "guidance" is small. If your model isn't, the gap matters.

## Setup

Assumes you have [Bun](https://bun.sh), [Ollama](https://ollama.com) (or another provider), and a local clone of Mycelium.

```bash
# 1. Install opencode
npm install -g opencode-ai          # or curl -fsSL https://opencode.ai/install | bash

# 2. Install Mycelium in your project
git clone https://github.com/haabe/mycelium
cd mycelium
# Substrate is ready: CLAUDE.md, AGENTS.md, .claude/, plugins/mycelium/, tests/

# 3. Install opencode-agent-skills (gives opencode skill discovery from .claude/skills/)
# In opencode config (.opencode/opencode.json or ~/.config/opencode/opencode.json):
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-agent-skills"],
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {
        "qwen2.5-coder:32b": { "name": "Qwen 2.5 Coder 32B", "tools": true }
      }
    }
  }
}

# 4. Pull a capable model (32B+ recommended for reliable instruction-following)
ollama pull qwen2.5-coder:32b

# 5. Run
opencode
```

## Model size matters

This is the load-bearing decision. Mycelium-on-opencode trades structural enforcement for model discipline; that trade only works if the model is disciplined enough.

| Model size | Mycelium-on-opencode experience |
|---|---|
| 4B – 8B local | Substrate loads. Model will often ignore the Read-before-Edit hint, skip the Pre-Task Protocol, and forget to log corrections. Verified 2026-05-16: llama3.1:8b edited a versioned file with no prior read, no warning. **Not recommended** for serious project work. Fine for trying the framework's mechanics. |
| 14B – 32B local | The instruction-following sweet spot for self-hosted. Qwen 2.5 Coder 32B, DeepSeek Coder V2, Llama 3.3 70B-quantized class. Most Mycelium discipline holds; expect occasional skips that the validators + corrections-loop catch. **Recommended** for self-hosted dogfood. |
| 70B+ local or hosted-API class | Discipline holds at the same level as Claude on Claude Code. Tradeoff is inference latency vs structural enforcement; choose based on your hardware budget. |
| Claude / GPT-4 via API | Use [Claude Code](https://claude.com/claude-code) instead — you get the structural enforcement Mycelium was designed against. opencode-as-frontend with an API model in the back works, but it's the worst-of-both: API cost without runtime enforcement. |

## Known runtime gaps and current workarounds

### Read-before-Edit not enforced
**Gap**: opencode's `edit` tool has the precondition in its schema text only. A model that ignores the hint edits anyway.

**Workaround today**: Trust the model + run validators frequently. Mycelium's `validate_canvas.py` will catch most stale-state damage at commit time. For canvas writes specifically, the existing "Read-before-Write HARD RULE" prose in `CLAUDE.md` / `AGENTS.md` is your discipline layer.

**Roadmap**: [opencode #27901](https://github.com/anomalyco/opencode/issues/27901) requests a configurable runtime check.

### Tool-failure event missing
**Gap**: `tool.execute.after` fires only for successful calls. Failures route to the message stream, not the hook stream. Mycelium's reflexion loop (retry-with-self-critique on tool failure) has no structural trigger.

**Workaround today**: Reflexion still works at the model level — the model sees the error in its message stream and can self-correct in the same turn. The Mycelium-as-Claude-Code automatic retry-with-explicit-self-critique pattern doesn't fire.

**Roadmap**: [opencode #27900](https://github.com/anomalyco/opencode/issues/27900) requests a `tool.execute.error` event.

### Pre-task context injection headless-mode silent
**Gap**: `tui.prompt.append` doesn't fire in `opencode run`. Mycelium's Pre-Task Protocol (`G-P-pre`) can't be hook-enforced in non-TUI invocations.

**Workaround today**: TUI mode has the hook (not yet runtime-verified end-to-end). For headless, the protocol lives in `AGENTS.md` prose; capable models read and follow.

**Roadmap**: [opencode #27899](https://github.com/anomalyco/opencode/issues/27899) requests a headless prompt-mutation event.

## Roadmap

Mycelium's opencode adapter is **deferred indefinitely** (decision-log 2026-05-16). Two triggers can resume the work:

1. **One or more of the three upstream issues lands.** Each closed gap shrinks the adapter from "fork-scale plugin re-implementing Claude Code primitives" to "thin binding over already-present primitives."
2. **A real user adopts opencode as their Mycelium runtime.** Demand-pull is the right trigger; speculative adapter work isn't.

The substrate-neutralization audit (`docs/receipts/cases/2026-05-16-phase0-substrate-audit.md`) found that Mycelium's substrate is closer to harness-portable than its `.claude/` naming suggests. Three doc rewrites are queued (~4.5h total) to make the portability explicit; those land when either trigger above fires.

## Honest summary

- Mycelium-the-substrate works on opencode today. Most of the framework's value (canvas, memory, decision-log, skills, validators, harness docs) ports verbatim.
- Three runtime-enforcement mechanisms don't fire on opencode. With a capable 32B+ model the gap is small. With a 4B/8B local model the gap is real.
- If you'd self-host AI development workflow anyway — laptop, VPS, dedicated inference box — Mycelium fits the stack without forcing a Claude Code subscription.
- If you're choosing between Claude Code and self-hosting purely for Mycelium, Claude Code remains the better runtime today. The gap will close as upstream issues land or the adapter ships.

If you try this setup, the corrections you encounter are exactly the friction the framework wants logged. PRs on `docs/receipts/cases/` welcome.

## Related receipts

- [opencode port feasibility (Phase 0)](../receipts/cases/2026-05-16-opencode-port-feasibility.md)
- [opencode Phase 1 runtime test](../receipts/cases/2026-05-16-opencode-phase1-runtime.md)
- [Phase 0 substrate-neutralization audit](../receipts/cases/2026-05-16-phase0-substrate-audit.md)
