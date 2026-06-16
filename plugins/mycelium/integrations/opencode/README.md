# Mycelium → opencode scaffold (starter)

This directory is the **starter scaffold** that `/mycelium:setup` provisions into a
user's project when opencode is the runtime. It is the opencode analogue of the
`hooks.codex.json` / `hooks.cursor.json` per-agent adapters under
`plugins/mycelium/hooks/` — a shipped starter, **not** a CI-tested guaranteed
surface.

## Status — read this before relying on it

- **Runtime-verified on opencode 1.17.7 (2026-06-15).** Plugin loads; `chat.message`
  preflight injection works headless; `tool.execute.before` fires and a thrown error
  blocks the tool; the read-before-edit guard fired live against `llama3.1:8b`; a
  clean end-to-end `opencode run` completes (EXIT 0). The two clean hooks work — but
  this is still a **starter** (gate/scope/secret-scan, post-write nudges, and the Stop
  relocation are TODO), and verification was on 1.17.7 specifically; other versions may
  differ.
- **The one hard gap is not covered.** Reflexion-on-tool-failure (opencode
  [#27900](https://github.com/anomalyco/opencode/issues/27900)) fires no plugin
  hook on failure; there is no clean workaround until the upstream `tool.execute.error`
  event lands. Everything else has a clean path.

## Config notes (runtime-verified on 1.17.7)

- `opencode.json` is **strict JSON** — opencode's schema rejects unrecognized keys
  (including `//` "comment" keys), so all guidance lives in this README, not the config.
- A custom `@ai-sdk/openai-compatible` provider needs an explicit `provider.<name>.models`
  map; a bare provider block fails with `ProviderModelNotFoundError`. Edit `model` + the
  `models` entry for your local model.
- **Model choice is gated by tool-calling, NOT size** (runtime-verified 2026-06-16):
  opencode needs structured `tool_calls`; a model whose Ollama template emits them as
  text silently does nothing. `llama3.1:8b` PASSES (at 8B); stock `qwen2.5-coder`
  (`:14b`/`:32b`) FAILS, any size. Run `python3 check-tool-calling.py <model>` to verify
  before relying on a model. Full table + fixes (Dolphin 3 / Qwen3-Coder tool-fix
  template / `hhao/qwen2.5-coder-tools`): `docs/integrations/opencode.md`.
- **Context (the silent killer)**: Ollama defaults to 4K (`num_ctx`), which overflows
  Mycelium's system+skill+tool-schema prompts and breaks tool-calling. Set
  `OLLAMA_CONTEXT_LENGTH=32768` (or a Modelfile `PARAMETER num_ctx 32768`).
- **Small-model caveat**: the preflight injection can distract weak models into
  summarising the reminder instead of calling tools. If your model derails, trim/drop the
  preflight text in `plugin/mycelium.ts` — the read-before-edit guard is independent of it.

## What's here

| File | Purpose |
|---|---|
| `opencode.json` | Minimal opencode config: local-model provider (Ollama example), `AGENTS.md` as instructions, skill permission. Edit the `model` / provider to your setup. |
| `plugin/mycelium.ts` | Enforcement plugin **skeleton**. Covers the two clean hooks: preflight context injection (`chat.message`, fires headless too — #27899) and read-before-edit guard (`tool.execute.before` throw — #27901). Gate/scope/secret-scan and post-write nudge are TODO. |
| `command/mycelium/interview.md` | Example user-typed entry command (`/mycelium:interview`). Copy this shape for other typed entry points. |
| `check-tool-calling.py` | Diagnostic: asks a model to call a tool and reports whether Ollama returns structured `tool_calls` (PASS = usable in opencode) or leaks it as text (FAIL). Run `python3 check-tool-calling.py <model>` before relying on any local model — the #1 cause of "nothing happens" on opencode. |
| `provision-skills.sh` | Vendors the Mycelium skills + their `engine/`/`harness/`/`jit-tooling/`/`domains/` reference files into the project's `.claude/`, and rewrites `${CLAUDE_PLUGIN_ROOT}/…` references to project-relative paths. opencode does NO `${...}` interpolation of skill content and never sets that variable, so without this the 36 reference-heavy skills load but misfire. Idempotent + re-runnable (the vendored copies are a snapshot — re-run after a framework upgrade). `/mycelium:setup` invokes it; or run `bash provision-skills.sh <project-root>` by hand. Self-locates the plugin root from its own path when run from a clone (no `CLAUDE_PLUGIN_ROOT` needed). |

opencode 1.17.7 discovers skills natively from `.claude/skills/` — the
`opencode-agent-skills` plugin is no longer required. The skills come from
`provision-skills.sh` above (which also rewrites their internal references). See
`docs/integrations/opencode.md` for the full setup, model-size guidance, and gap details.

## Finishing the skeleton (the work before it's turnkey)

1. Extend `plugin/mycelium.ts` with the remaining `tool.execute.before` guards
   (scope-gate, secret-scan) and the `tool.execute.after` nudges (post-write,
   change-log, read-log).
2. Add `session.idle` + `chat.message` relocation for the Stop guardrail.
3. Add the remaining user-typed entry commands under `command/mycelium/`.
4. **Verify skill *execution* on a real opencode + capable-model box.** `provision-skills.sh`
   is verified to produce resolvable project-relative paths, but a full Mycelium-gated
   workflow following the rewritten references has not been model-verified end-to-end
   (local 8B/9B models were too weak to drive it). This pairs with the first real cohort run.
