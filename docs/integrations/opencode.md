# Using Mycelium with opencode (self-hosted)

**Audience**: developers who want Mycelium's product-thinking discipline without committing to Claude Code as the runtime — typically because of pricing, vendor lock-in, or a preference for self-hosted local models.
**Time to read**: 6 min.
**Last updated**: 2026-06-15.
**Status**: Mycelium works on opencode as a substrate-portable framework. Of the three runtime safety mechanisms that Mycelium relies on in Claude Code, **one genuine hard gap remains** (reflexion / tool-failure events, #27900); the other two now have clean structural paths — headless context injection is effectively addressed upstream (#27899), and read-before-edit is solvable by a thin plugin guard (#27901). Honest details below. (Gap re-assessment 2026-06-15: the headless-injection (#27899) and read-before-edit (#27901) paths are **runtime-verified on opencode 1.17.7** — the starter scaffold loads and both hooks fire live; reflexion (#27900) remains the gap. Behaviour on other opencode versions may differ; re-verify against your build.)

## Why this might fit

The AI coding scene in mid-2026 has visible tension around pricing: subscription tiers shifting, per-token costs accumulating, and a steady drift toward self-hosted setups (laptop, VPS, dedicated inference box). [opencode](https://github.com/anomalyco/opencode) is the most-cited Claude Code alternative — provider-agnostic, TUI-first, runs against Anthropic, OpenAI, Google, or local providers via Ollama or LM Studio.

If you're already moving toward self-hosted AI development workflow, Mycelium can come along — but with one real caveat about skills (below). The file substrate — canvas YAML, memory, decision-log, and the Python/Bash validators — is harness-neutral and runs verbatim. The skills are discovered natively (opencode 1.17.7 reads `.claude/skills/` directly — no extra plugin needed), **but 36 of the 55 skills reference `${CLAUDE_PLUGIN_ROOT}/engine/…` and `/harness/…` files that opencode does not resolve** (it never sets that variable). Runtime-verified 2026-06-15: those references are dead on opencode unless the referenced files are vendored into the project and the paths rewritten. **`/mycelium:setup` now automates this** (`provision-skills.sh`): it copies the skills + their `engine/`/`harness/`/`jit-tooling/`/`domains/` reference files into your project's `.claude/` and rewrites `${CLAUDE_PLUGIN_ROOT}/…` to project-relative paths opencode resolves. The rewrite is verified to produce resolvable paths; full skill *execution* on a local model isn't yet end-to-end-verified (the available local models were too weak to drive it). The vendored copies are a snapshot — re-run setup after a framework upgrade to refresh. The runtime-discipline mechanisms (described below) are Claude-Code-specific in their *enforcement*; on opencode they degrade to **prompt-level guidance to the model** unless a plugin re-supplies the enforcement. As of mid-2026 two of the three previously-hard gaps have structural paths (one closed upstream, one plugin-solvable), leaving reflexion-on-tool-failure as the one mechanism with no clean path today. Capable models (including open-weight Mistral-class) will follow the prose guidance; small 4B/8B models may not.

This page tells you what works, what doesn't, how to set it up, and which model sizes are worth your time.

## What works on opencode today

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Fully portable | Pure files. opencode and Claude Code both read them. |
| `CLAUDE.md` instructions | ✅ Read as fallback | `AGENTS.md` is opencode's primary, `CLAUDE.md` is the fallback. Mycelium ships both. |
| Skill discovery (55 skills) | ✅ Native | opencode 1.17.7 reads `.claude/skills/**/SKILL.md` directly — no `opencode-agent-skills` plugin required (it was needed on older builds). |
| Skill *execution* (internal references) | ✅ Automated via `/mycelium:setup` | 36 of 55 skills reference `${CLAUDE_PLUGIN_ROOT}/engine/…` + `/harness/…`; opencode never sets that variable and does no substitution. `/mycelium:setup` (`provision-skills.sh`) vendors the referenced files into `.claude/mycelium/` and rewrites the paths to project-relative ones opencode resolves. Rewrite verified to produce resolvable paths; full skill execution not yet model-verified end-to-end. Re-run setup after a framework upgrade (the copies are a snapshot). |
| Validators (`validate_canvas.py`, `validate-template.sh`) | ✅ Run unchanged | Python + Bash; harness-agnostic. |
| MCP server integrations | ✅ Native | Both runtimes speak MCP. |
| Slash command invocation | ⚠️ Flat names | opencode commands are flat (`/skill-name`), no `mycelium:` namespace prefix. Cosmetic difference. |
| Read-before-Edit safety | ⚠️ Core doesn't enforce; clean plugin path | The precondition is in the tool description, not runtime-enforced — a model that ignores the hint edits without reading. **But** a plugin can enforce it cleanly and non-fragibly: track read-history and `throw` from `tool.execute.before` on an unread edit (dev-branch source, 2026-06-15). Available once the enforcement plugin ships; not in core. See [issue #27901](https://github.com/anomalyco/opencode/issues/27901). |
| Reflexion loop (auto-retry on tool failure) | ⛔ **The one hard gap** | `tool.execute.after` is success-only; on failure **no plugin hook fires at all**, so reflexion has no structural trigger and no clean plugin workaround. This is the single gap that needs an upstream fix. See [issue #27900](https://github.com/anomalyco/opencode/issues/27900). |
| Pre-task context injection (G-P-pre) | ✅ Effectively addressed upstream | The stable `chat.message` hook fires in headless `opencode run` and mutating `output.parts` reaches the model (dev-branch source analysis, 2026-06-15 — supersedes the May `tui.prompt.append` finding; not yet runtime-verified end-to-end). `experimental.chat.system.transform` covers system-prompt injection. See [issue #27899](https://github.com/anomalyco/opencode/issues/27899). |

**Net**: Mycelium loads on opencode and the framework's *discipline* runs as model-following-instructions. One *guarantee* (reflexion on tool failure) has no clean path without an upstream fix; the other two are now structurally reachable (context injection works via the stable `chat.message` hook; read-before-edit via a plugin guard). If your model is capable enough to follow instructions reliably, the gap between "guarantee" and "guidance" is small. If your model isn't, the read-before-edit plugin guard is the piece worth having.

## Setup

**Fastest path**: run `/mycelium:setup` in your project. When it detects opencode (an `opencode.json`/`.opencode/` in the project, an `~/.config/opencode`, or `opencode` on `PATH`) — or when you ask it to — it provisions: `opencode.json`, the enforcement plugin (`.opencode/plugin/mycelium.ts`), an example `/mycelium:interview` command, AND the skills (vendored into `.claude/skills/` + reference files into `.claude/mycelium/`, with `${CLAUDE_PLUGIN_ROOT}` paths rewritten). It never overwrites your files, and it skips silently on a Claude-Code-only install. The scaffold lives in the plugin at `plugins/mycelium/integrations/opencode/` (see that directory's README). opencode 1.17.7 discovers the vendored skills natively (no `opencode-agent-skills` plugin needed). **Re-run setup after a framework upgrade** — the vendored copies are a snapshot. The manual steps below detail the same flow if you'd rather do it by hand.

Assumes you have [Bun](https://bun.sh), [Ollama](https://ollama.com) (or another provider), and a local clone of Mycelium.

```bash
# 1. Install opencode
npm install -g opencode-ai          # or curl -fsSL https://opencode.ai/install | bash

# 2. Install Mycelium in your project
git clone https://github.com/haabe/mycelium
cd mycelium
# Substrate is ready: CLAUDE.md, AGENTS.md, .claude/, plugins/mycelium/, tests/

# 3. Provision the skills into your project. Run the script FROM the clone — it
# self-locates (no CLAUDE_PLUGIN_ROOT needed) and vendors the skills + rewrites their
# ${CLAUDE_PLUGIN_ROOT} refs to project-relative paths. (/mycelium:setup does this for
# you on Claude Code; for a pure-opencode clone, run it directly.) Re-run after upgrades.
bash plugins/mycelium/integrations/opencode/provision-skills.sh .   # '.' = your project root

# 4. Configure opencode (.opencode/opencode.json or ~/.config/opencode/opencode.json).
# opencode 1.17.7 discovers .claude/skills/ natively — no opencode-agent-skills plugin needed.
# Schema is strict — no comment keys. Set the model to one your hardware can run (see below).
{
  "$schema": "https://opencode.ai/config.json",
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

# 5. Pull a model your hardware can run (see "Model size matters" — on Apple Silicon
# the binding constraint is unified memory: 16GB → 14B, 32GB+ → 32B).
ollama pull qwen2.5-coder:32b      # or qwen2.5-coder:14b on a 16GB machine

# 6. Run
opencode
```

## Model size matters

This is the load-bearing decision. Mycelium-on-opencode trades structural enforcement for model discipline; that trade only works if the model is disciplined enough.

| Model size | Mycelium-on-opencode experience |
|---|---|
| 4B – 8B local | Substrate loads. Model will often ignore the Read-before-Edit hint, skip the Pre-Task Protocol, and forget to log corrections. Verified 2026-05-16: llama3.1:8b edited a versioned file with no prior read, no warning. **Not recommended** for serious project work. Fine for trying the framework's mechanics. |
| 14B – 32B local | The instruction-following sweet spot for self-hosted. Qwen 2.5 Coder 32B, DeepSeek Coder V2, Llama 3.3 70B-quantized class. Most Mycelium discipline holds; expect occasional skips that the validators + corrections-loop catch. **Recommended** for self-hosted dogfood. |
| 70B+ local or hosted-API class | Discipline holds at the same level as Claude on Claude Code. Tradeoff is inference latency vs structural enforcement; choose based on your hardware budget. |

**On Apple Silicon, model size is bounded by unified memory** (the GPU shares RAM):

| Mac | Realistic local model (Q4_K_M) | Notes |
|---|---|---|
| **16 GB** (M1 / M1 Pro base, 13"/14" 2021) | `qwen2.5-coder:14b` (~9 GB) | The realistic ceiling — leaves headroom for the OS + editor. Better tool-calling + instruction-following than 7-8B, but still **below** the 32B sweet spot: expect some skill-driving friction. Drop to `qwen2.5-coder:7b` (~4.7 GB) only if 14B is too tight. |
| **32 GB+** (M1 Pro/Max higher config) | `qwen2.5-coder:32b` (~20 GB) | The recommended sweet spot — fits with room to spare. |

Use a model with solid **tool-calling** (Qwen 2.5 Coder is reliable here) — opencode drives edits/reads through structured tool calls, and weak tool-callers stall or malform them.
| Claude / GPT-4 via API | Use [Claude Code](https://claude.com/claude-code) instead — you get the structural enforcement Mycelium was designed against. opencode-as-frontend with an API model in the back works, but it's the worst-of-both: API cost without runtime enforcement. |

## Known runtime gaps and current workarounds

### Read-before-Edit not enforced by core — but plugin-solvable
**Gap**: opencode's `edit` tool has the precondition in its schema text only. A model that ignores the hint edits anyway. Core still does not enforce this (no config flag in `config.ts` as of `dev` 2026-06-15).

**Clean path (plugin)**: A plugin can track read-history and `throw` from `tool.execute.before` when an edit targets an unread file — non-fragile, deterministic, no message-stream scraping. This is part of the (deferred) enforcement plugin; it is not in core today.

**Workaround until that ships**: Trust the model + run validators frequently. Mycelium's `validate_canvas.py` catches most stale-state damage at commit time. For canvas writes, the "Read-before-Write HARD RULE" prose in `CLAUDE.md` / `AGENTS.md` is your discipline layer.

**Upstream**: [opencode #27901](https://github.com/anomalyco/opencode/issues/27901) requests a configurable runtime check (would let core enforce it without a plugin).

### Tool-failure event missing — the one hard gap
**Gap**: `tool.execute.after` fires only for successful calls. On failure, **no plugin hook fires at all** (the Effect short-circuits before the `after` trigger; no `tool.execute.error`, no status field — `dev` 2026-06-15). So Mycelium's reflexion loop (retry-with-self-critique on tool failure) has no structural trigger, and no clean plugin workaround exists — failure is observable only by racily correlating callIDs against the message stream.

**Workaround today**: Reflexion still works at the *model* level — the model sees the error in its message stream and can self-correct in the same turn. The automatic retry-with-explicit-self-critique pattern doesn't fire.

**Upstream**: [opencode #27900](https://github.com/anomalyco/opencode/issues/27900) requests a `tool.execute.error` event. This is the single gap whose clean fix must come from upstream; a PR draft exists. Landing it retires the need for any opencode-specific shim here.

### Pre-task context injection — effectively addressed upstream
**Status (revised 2026-06-15)**: The May finding that `tui.prompt.append` is silent in `opencode run` is superseded. Source analysis of the `dev` branch shows the stable `chat.message` hook fires in headless `opencode run`, and mutating `output.parts` reaches the model (path: `cli/cmd/run.ts` → `session.prompt` → `createUserMessage`). `experimental.chat.system.transform` covers system-prompt injection. So Mycelium's Pre-Task Protocol (`G-P-pre`) has a structural injection path in both TUI and headless modes.

**Caveat**: this is source analysis, not an end-to-end runtime test — verify against your opencode build.

**Upstream**: [opencode #27899](https://github.com/anomalyco/opencode/issues/27899) — effectively closed by the `chat.message` path.

## Roadmap

Mycelium's opencode adapter was **deferred** 2026-05-16 (decision-log) behind two triggers. Status as of 2026-06-15:

1. **One or more of the three upstream gaps closes.** ✅ **Partially met** — #27899 (headless injection) is effectively closed via the `chat.message` path, and #27901 (read-before-edit) is now plugin-solvable. Only #27900 (tool-failure event) remains a genuine hard gap needing upstream. The adapter has shrunk from "fork-scale plugin re-implementing primitives" to "thin binding over already-present primitives + one upstream PR."
2. **A real user adopts opencode as their Mycelium runtime.** ⏳ **Not yet met** — interest has been expressed but adoption (a sustained Mycelium-gated workflow run on opencode + open weights) has not been observed. Demand-pull remains the trigger for committing the adapter to maintained core support; speculative core-coupling isn't.

**What this means in practice**: the *tryable path* (this doc + a runnable plugin scaffold + an on-ramp) is low-regret and worth shipping now — it's what lets a user adopt in the first place. Committing the adapter to *maintained framework core* (coupling CI to opencode) stays paced behind trigger 2. The substrate-neutralization audit (`docs/receipts/cases/2026-05-16-phase0-substrate-audit.md`) found Mycelium's substrate is closer to harness-portable than its `.claude/` naming suggests.

## Honest summary

- Mycelium-the-substrate works on opencode today. The file substrate (canvas, memory, decision-log, validators, harness docs) ports verbatim; skills are discovered natively but 36 of 55 reference `${CLAUDE_PLUGIN_ROOT}` paths opencode can't resolve, so `/mycelium:setup` vendors them + rewrites the paths (re-run after a framework upgrade to refresh).
- Of the three runtime-enforcement mechanisms, two now have structural paths (context injection works via `chat.message`; read-before-edit via a plugin guard) and one (reflexion on tool failure, #27900) needs an upstream fix. With a capable 32B+ model — including open-weight Mistral-class — the residual gap is small. With a 4B/8B local model the read-before-edit plugin guard is worth having.
- If you'd self-host AI development workflow anyway — laptop, VPS, dedicated inference box — Mycelium fits the stack without forcing a Claude Code subscription.
- If you're choosing between Claude Code and self-hosting purely for Mycelium, Claude Code remains the better runtime today. The gap will close as upstream issues land or the adapter ships.

If you try this setup, the corrections you encounter are exactly the friction the framework wants logged. PRs on `docs/receipts/cases/` welcome.

## Related receipts

- [opencode port feasibility (Phase 0)](../receipts/cases/2026-05-16-opencode-port-feasibility.md)
- [opencode Phase 1 runtime test](../receipts/cases/2026-05-16-opencode-phase1-runtime.md)
- [Phase 0 substrate-neutralization audit](../receipts/cases/2026-05-16-phase0-substrate-audit.md)
