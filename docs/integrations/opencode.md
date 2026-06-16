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

# 5. Pull a model that emits STRUCTURED tool calls (see "Choosing a model" — this,
# not size, is the gate). llama3.1:8b is verified-working; stock qwen2.5-coder is NOT.
ollama pull llama3.1:8b
# Verify it before relying on it (FAIL = unusable in opencode):
#   python3 plugins/mycelium/integrations/opencode/check-tool-calling.py llama3.1:8b
# And avoid Ollama's 4K context default (overflows agentic prompts -> tool-calls fail).
# IMPORTANT: this must be set on the SERVE PROCESS, not just your shell — a GUI/brew
# launchd `ollama serve` won't inherit a shell export. Stop that server and run:
#   env OLLAMA_CONTEXT_LENGTH=32768 ollama serve   (verify: ps shows llama-server -c 32768)
export OLLAMA_CONTEXT_LENGTH=32768

# 6. Run
# (Optional) on a weak local model (≈8B), disable the preflight injection if it derails
# tool-calling — see "Choosing a model": export MYCELIUM_PREFLIGHT=off
opencode
```

## Choosing a model — tool-calling first, then context, then size

The load-bearing decision is **NOT model size** — it's whether the model emits **structured `tool_calls`** through Ollama. opencode (like Roo Code) is native-tool-call-only: it has no client-side text/XML fallback (unlike Cline). A model that emits the tool-call JSON as plain text — which many do, because their Ollama Modelfile `TEMPLATE` doesn't parse it — silently does nothing in opencode: it "knows" to call the tool, but the call never executes. **Runtime-verified 2026-06-16** (direct Ollama API, both `/v1` and native):

| Model | Structured tool_calls on Ollama? | Note |
|---|---|---|
| **`llama3.1:8b`** | ✅ **PASS** (verified) | Clean structured calls on `/v1` *and* native — **at 8B**. Size is not the gate. |
| stock `qwen2.5-coder` (`:14b`, `:32b`) | ❌ **FAIL** | Emits the call as text content; Ollama template gap (known qwen-coder-family bug). Unusable in opencode as-is, any size. |
| `qwen3` (e.g. `:32b`) | ❌ FAIL (reported, [opencode#1034](https://github.com/anomalyco/opencode/issues/1034)) | Generates tool JSON, never executes — same failure at 32B. |
| Dolphin 3 · Qwen3-Coder (unsloth tool-calling-fix template) · `hhao/qwen2.5-coder-tools` · DeepSeek-Coder | ↗ community-reported good | Tool-fixed templates exist; **verify before relying** (next row). |

**Check any model before trusting it:** `python3 plugins/mycelium/integrations/opencode/check-tool-calling.py <model>` → PASS = usable, FAIL = it leaks tool calls as text.

**Then fix context (the silent killer): `export OLLAMA_CONTEXT_LENGTH=32768`** (or a Modelfile `PARAMETER num_ctx 32768`). Ollama defaults to **4K** even when the model supports more; a Mycelium skill like `interview` is ~10k tokens, so its prompts overflow 4K and tool-calling fails. Necessary even with a working-template model. **Critical: set it on the SERVE PROCESS, not just your shell** — a GUI/brew/launchd `ollama serve` won't inherit a shell export (verified 2026-06-16, the #1 setup gotcha). Stop that server and run `env OLLAMA_CONTEXT_LENGTH=32768 ollama serve`; confirm with `ps … | grep llama-server` showing `-c 32768` (not `-c 4096`).

**On a weak local model (≈8B), the preflight injection can distract it** into summarising the reminder instead of calling tools (e2e 2026-06-16: an 8B followed the skill 3/3 with preflight off vs 1/3 on — not fatal, but real). Disable it with **`export MYCELIUM_PREFLIGHT=off`** (the plugin reads this and skips the injection); the read-before-edit guard is independent and still fires. Capable models can leave it on.

**Only then does size/quality matter** — and only *among models that tool-call at all.* Bigger = better instruction-following + fewer skipped gates, but a working-template 8B beats a broken-template 32B (which scores zero). On Apple Silicon the ceiling is unified memory (16 GB ≈ an 8–14B Q4 model with headroom; 32 GB+ ≈ up to ~32B) — pick the **largest model that (a) passes the tool-calling check and (b) fits**.

| Claude / GPT-4 via API | Use [Claude Code](https://claude.com/claude-code) instead — you get the structural enforcement Mycelium was designed against. opencode-as-frontend with an API model in the back works, but it's the worst-of-both: API cost without runtime enforcement. |

> **History:** an earlier version of this page recommended `qwen2.5-coder:14b/32b` as the "self-hosted sweet spot." That was wrong — runtime testing (2026-06-16) found the qwen-coder family doesn't emit structured tool calls on Ollama at any size, while `llama3.1:8b` does. Tool-template support, not size, is the gate.

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
