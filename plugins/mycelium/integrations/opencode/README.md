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
- **Small-model caveat**: the preflight injection can distract weak models (≈8B) into
  summarising the reminder instead of calling tools, and some thinking-models stall
  headless. If your local model derails, trim/drop the preflight text — the guard is
  independent of it. 32B+ / capable open-weight is the sweet spot (see the model-size
  table in `docs/integrations/opencode.md`).

## What's here

| File | Purpose |
|---|---|
| `opencode.json` | Minimal opencode config: local-model provider (Ollama example), `AGENTS.md` as instructions, skill permission. Edit the `model` / provider to your setup. |
| `plugin/mycelium.ts` | Enforcement plugin **skeleton**. Covers the two clean hooks: preflight context injection (`chat.message`, fires headless too — #27899) and read-before-edit guard (`tool.execute.before` throw — #27901). Gate/scope/secret-scan and post-write nudge are TODO. |
| `command/mycelium/interview.md` | Example user-typed entry command (`/mycelium:interview`). Copy this shape for other typed entry points. |
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
