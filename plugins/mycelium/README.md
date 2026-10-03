# Mycelium plugin

This folder is the plugin form of [Mycelium](https://github.com/haabe/mycelium): the skills, hooks,
engine, schemas and scripts Claude Code loads when you install it. It also runs on Codex, Cursor and
opencode; see [install paths](https://github.com/haabe/mycelium/blob/main/docs/install-paths.md).

## Install

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```

Then run `/mycelium:start` in your project. [Get started](https://github.com/haabe/mycelium/blob/main/docs/get-started.md) walks through it.

## What it adds

- **Skills** under `skills/`, invoked as `/mycelium:<name>`.
- **Hooks** registered in `hooks/hooks.json`, which Claude Code runs on its own events. Some can
  refuse a tool call; the rest warn or log. [`hooks/README.md`](hooks/README.md) describes each one.
- No agents, no MCP servers, no binaries.

It does not edit your project's own files (CLAUDE.md, README.md, LICENSE). Its state goes in a
`.claude/` folder in your project, which the hooks create on first use. `/mycelium:setup` offers an
`AGENTS.md` at your project root. Everything it runs, reads, writes and connects to is stated in
[`PRIVACY.md`](https://github.com/haabe/mycelium/blob/main/PRIVACY.md).

## Architecture cut

| Lives in the plugin (versioned, replaced on update) | Lives in your project (state, yours, committed) |
|---|---|
| `skills/` | `.claude/canvas/*.yml` |
| `hooks/` | `.claude/diamonds/` |
| `engine/`, `harness/` | `.claude/memory/`, `.claude/harness/decision-log.md` |
| `schemas/` | `.claude/evals/` |
| `scripts/` | `.claude/jit-tooling/active-metrics.yml` |

`/mycelium:setup` creates the project-state folders from templates shipped with the plugin.

## Local testing

From the `haabe/mycelium` repo:

```
claude --plugin-dir ./plugins/mycelium
```

Then `/mycelium:ping` should return `MYCELIUM_PLUGIN_LOAD_OK`.

## Sources

- [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
