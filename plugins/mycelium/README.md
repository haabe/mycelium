# Mycelium plugin

This is the Claude Code plugin form of [Mycelium](https://github.com/haabe/mycelium). It is brownfield-safe by design: install adds skills, agents, and hooks via Claude Code's plugin mechanism without modifying any project root files (CLAUDE.md, README.md, CONTRIBUTORS.md, LICENSE).

## Status: bootstrapping (v0.20.0 in progress)

The plugin shell ships first; full skill/agent/hook migration follows in subsequent commits. Today's contents:

- `.claude-plugin/plugin.json` — manifest (`name: mycelium`, version 0.20.0)
- `skills/ping/SKILL.md` — smoke-test skill that validates the plugin loads (`/mycelium:ping` returns a deterministic marker string)

Coming next (tracked in `feat/plugin-form` branch):

- All 45 framework skills migrated into `skills/`
- Mandatory protocols (Pre-Task, Pre-Ship, Post-Task) re-shaped as `hooks/hooks.json` with SessionStart, PreToolUse, Stop event handlers
- `agents/` for Mycelium subagents
- `mycelium:setup` skill that creates project-state directories (canvas, diamonds, memory) on first run
- AGENTS.md template that the setup skill writes for cross-agent portability

## Install (once published)

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```

After install, run `/mycelium:setup` to create project-state files.

## Local testing during development

From the upstream `haabe/mycelium` repo:

```
claude --plugin-dir ./plugins/mycelium
```

Then in Claude Code:

```
/mycelium:ping
```

Should return `MYCELIUM_PLUGIN_LOAD_OK_v0.20.0`.

## Why a plugin

- **Brownfield-safe install**: project root stays user-owned. Daniel Bentes surfaced the contamination problem 2026-05-08; install model rebuilt as a result.
- **Multi-agent portability via AGENTS.md**: Mycelium ships canonical instructions in AGENTS.md (cross-agent open standard, read by Codex / Cursor / Aider / Copilot). Plugin form is the Claude Code distribution layer; AGENTS.md preserves portability.
- **Versioned, replaceable**: `/plugin update` swaps framework versions without modifying user project state.
- **Discovery surface**: future listing on Anthropic's official marketplace and `synaptiai/synapti-marketplace`.

## Architecture cut

| Lives in plugin (versioned, replaceable) | Lives in user project (state, writable, gitted) |
|---|---|
| `skills/` | `canvas/*.yml` |
| `agents/` | `diamonds/active.yml` |
| `hooks/hooks.json` | `memory/corrections.md`, `memory/patterns.md` |
| `harness/` (mostly) | `harness/decision-log.md`, `harness/warnings-log.md` |
| `engine/` | `evals/` |
| `schemas/` | `jit-tooling/active-metrics.yml` |
| `scripts/` (validators) | |

The setup skill creates the project-state directories from templates shipped with the plugin.

## Sources

- [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- Receipts case (forthcoming): `docs/receipts/cases/2026-05-08-bentes-install-model.md`
