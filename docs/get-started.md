# Get started

**Audience**: you have a project, new or already running, and want to try Mycelium on it.
**Time to read**: 5 min. The first run takes about ten minutes more.
**Last updated**: 2026-10-02.

Mycelium is a Claude Code plugin that asks who a project is for before the agent writes code for it.
This page takes you from installing it to running it on a real project. The first ten minutes, four
questions about your idea, are a milestone on the way. The goal is the project.

You need Claude Code, installed and signed in (a Claude account or an API key). Using a different
agent? See [install paths](install-paths.md).

## Step 1: install

Inside Claude Code:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```

## Step 2: check it loaded

```
/mycelium:ping
```

You should get back exactly `MYCELIUM_PLUGIN_LOAD_OK`. If you get nothing, or an unknown-command error,
the install did not take: run `/reload-plugins` and try again.

## Step 3: the four questions

Open the project you want to use it on, then:

```
/mycelium:start
```

It sets up a `.claude/` folder and asks four questions: what the problem is, who has it, what you are
assuming, and what would show you wrong. From your answers it writes a short brief into the project,
in `.claude/canvas/purpose.yml` and `.claude/canvas/jobs-to-be-done.yml`. It also asks where the
product's own files will live, and which of the things you said must never be contradicted.

You now have, in your repo, a written answer to "who is this for", and the assumption most likely to
sink it. That is the milestone.

## Step 4: run it on the project

The four questions end with a menu. Most people should take the first option.

- **Test the biggest assumption.** It designs the smallest test that could prove you wrong, which is
  usually a conversation with someone who has the problem. Go and have it, then come back and say what
  you heard.
- **Go deeper.** More discovery: what you are aiming at, who else is in the space, what limits you.
  You choose how deep.
- **Stop for now.** Everything is saved in the repo.

Building is open whichever you pick. The agent works as it always does, and the brief is what it is
held to. The discovery gate only fires in a project where nothing has been written down, so after the
four questions it stays quiet.

When you come back to the project, each new session puts one next step in front of you. To see where
the project stands at any time:

```
/mycelium:diamond-assess
```

**How to tell whether it is working for you:** run it on three real projects, not one. Writing anything
down feels clarifying the first time, and that proves nothing. If across three projects the brief never
once changed what you built, it did not work for you.

## What it changes, and what it costs

- **Adds**: `/mycelium:<skill>` commands, and a `.claude/` folder the agent reads and writes as it works.
- **Leaves alone**: your source files, your build config, and every file at the project root.
- **Costs**: about six thousand tokens of context a session, and four hooks that can hold work back.
  [What it costs](../README.md#what-it-costs) lists all four.

## Keeping it current, or removing it

Plugin auto-update is on by default. To update by hand:

```
/plugin marketplace update haabe-mycelium
/reload-plugins
```

To take it out again, see [uninstall](uninstall.md).

## Where to go next

- **A word you did not recognise:** the [glossary](glossary.md).
- **Not convinced it is worth ten minutes:** [what discovery before the build gives you](mental-model.md).
- **Using it with a team, or agent to agent:** [usage modes](usage-modes.md).

---

## Only if these apply to you

**Running Codex, Cursor, Aider, or Copilot.** Agents that do not speak the Claude Code plugin spec still
get the framework through [`AGENTS.md`](../AGENTS.md). Details in [install paths](install-paths.md).

**Coming from a legacy `.claude/` tree.** See the [legacy-to-plugin migration guide](migration.md) and
the [`/mycelium:migrate-from-legacy`](../plugins/mycelium/skills/migrate-from-legacy/SKILL.md) skill.

**The old `npx degit` channel is gone.** On the current layout it lands an empty `.claude/` with no
skills to invoke and no hooks to fire. See [install paths](install-paths.md).
