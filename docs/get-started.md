# Get started

**Audience**: operators installing Mycelium on a new or existing project.
**Time to read**: 5 min.
**Last updated**: 2026-07-30.

Mycelium installs as a Claude Code plugin. It adds namespaced `/mycelium:<skill>`
commands and a `.claude/` working tree the agent reads from, and it changes none
of your project-root files. You can adopt it on a live codebase with no migration
step.

Three steps below, then a check that it worked. Everything after that is optional
reading.

## Step 1 — install

**Prerequisite:** Claude Code, installed and signed in (a Claude account or API
key). Using a different agent? See [install paths](install-paths.md). Then, inside
Claude Code:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```

## Step 2 — confirm it loaded

Before spending ten minutes on discovery, check the plugin is actually live:

```
/mycelium:ping
```

You should get back exactly `MYCELIUM_PLUGIN_LOAD_OK`. That confirms the whole
chain works — manifest, marketplace, install, and namespaced invocation. If you
get nothing, or an unknown-command error, the install did not take: run
`/reload-plugins` and try again before going further.

## Step 3 — run your first round

```
/mycelium:start       # setup + 10-minute discovery, one command
```

`/mycelium:start` handles first-project setup and walks the opening discovery
round. On an empty canvas it routes you into [`/interview`](skills/README.md); on
a populated one it resumes via [`/diamond-assess`](skills/README.md).

## What the install touched

- **Added**: namespaced `/mycelium:<skill>` commands, and a `.claude/` working
  tree (canvas, diamonds, memory, harness) the agent reads and writes as it works.
  Skills are namespaced per Anthropic's plugin convention.
- **Left alone**: your source files, your build config, and every project-root
  file.

## Keeping it current

Plugin auto-update is on by default. To update by hand:

```
/plugin marketplace update haabe-mycelium
/reload-plugins
```

## Where to go next

- [How to think in Mycelium: the mental model in one worked example](mental-model.md)
- [How to apply Mycelium: solo, team, or agent orchestration](usage-modes.md)
- [Evaluate Mycelium for your team in ~1 hour](evaluate.md)
- [Frequently asked questions](faq.md)

---

## Asides — only if they apply to you

**Running Codex, Cursor, Aider, or Copilot.** Agents that don't speak the Claude
Code plugin spec still get framework value through
[`AGENTS.md`](../AGENTS.md) orientation. Details in
[install paths](install-paths.md).

**Coming from a legacy `.claude/` tree.** See
[the legacy→plugin migration guide](migration.md) and the agent-driven
[`/mycelium:migrate-from-legacy`](../plugins/mycelium/skills/migrate-from-legacy/SKILL.md)
skill.

**The old `npx degit` channel is gone.** On the current layout it lands an empty
`.claude/` with no skills to invoke and no hooks to fire — see
[install paths](install-paths.md).
