# Get started

**Audience**: operators installing Mycelium on a new or existing project.
**Time to read**: 5 min.
**Last updated**: 2026-07-04.

Mycelium installs as a Claude Code plugin. Installation does not modify any
project-root files. It adds namespaced `/mycelium:<skill>` commands and a
`.claude/` working tree the agent reads from. You can adopt it on a live
codebase without a migration step.

## Install (plugin form, recommended)

**Prerequisite:** Claude Code, installed and signed in (a Claude account or API key). Other supported agents: see [install paths](install-paths.md). Then, inside Claude Code:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:start       # one command: setup + 10-minute discovery
```

`/mycelium:start` runs first-project setup and walks the opening discovery
round. On an empty canvas it routes you into [`/interview`](skills/README.md);
on a populated one it resumes via [`/diamond-assess`](skills/README.md).

Plugin auto-update is on by default. To update manually:

```
/plugin marketplace update haabe-mycelium
/reload-plugins
```

## Other agents (Codex, Cursor, Aider, Copilot)

Agents that do not speak the Claude Code plugin spec still get framework value
through [`AGENTS.md`](../AGENTS.md) orientation. The old `npx degit` channel is
no longer supported — on the current layout it lands an empty `.claude/` with no
skills to invoke and no hooks to fire (see [install paths](install-paths.md)).

If you are moving an existing legacy
`.claude/` tree onto plugin form, see
[the legacy→plugin migration guide](migration.md) and the agent-driven
[`/mycelium:migrate-from-legacy`](../plugins/mycelium/skills/migrate-from-legacy/SKILL.md)
skill.

## What plugin install touches

- **Adds**: namespaced `/mycelium:<skill>` commands; a `.claude/` working tree
  (canvas, diamonds, memory, harness) the agent reads and writes as it works.
- **Does not touch**: your source files, build config, or any project-root file.

Skills are namespaced as `/mycelium:<name>` per Anthropic's plugin convention.

## Where to go next

- [How to think in Mycelium: the mental model in one worked example](mental-model.md)
- [How to apply Mycelium: solo, team, or agent orchestration](usage-modes.md)
- [Evaluate Mycelium for your team in ~1 hour](evaluate.md)
- [Frequently asked questions](faq.md)
