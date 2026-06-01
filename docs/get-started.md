# Get started

**Audience**: operators installing Mycelium on a new or existing project.
**Time to read**: 5 min.
**Last updated**: 2026-05-30.

Mycelium installs as a Claude Code plugin. Installation does not modify any
project-root files — it adds namespaced `/mycelium:<skill>` commands and a
`.claude/` working tree the agent reads from. You can adopt it on a live
codebase without a migration step.

## Install (plugin form — recommended)

```bash
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:start       # one command: setup + 10-minute discovery
```

`/mycelium:start` runs first-project setup and walks the opening discovery
round. On an empty canvas it routes you into [`/interview`](skills/README.md);
on a populated one it resumes via [`/diamond-assess`](skills/README.md).

Plugin auto-update is on by default. To update manually:

```bash
/plugin marketplace update haabe-mycelium
/reload-plugins
```

## Install (legacy npx — portable)

Agents that do not speak the plugin spec (Codex, Cursor, Aider, Copilot) still
get framework value through [`AGENTS.md`](../AGENTS.md) orientation. The legacy
installation channel remains available for projects that prefer not to depend
on the plugin runtime:

```bash
npx degit haabe/mycelium
```

Fresh installs default to plugin form. If you are moving an existing legacy
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

- [How to think in Mycelium — the mental model in one worked example](mental-model.md)
- [How to apply Mycelium — solo, team, or agent orchestration](usage-modes.md)
- [Evaluate Mycelium for your team in ~1 hour](evaluate.md)
- [Frequently asked questions](faq.md)
