# Uninstall, downgrade, rollback

**Audience**: operators removing Mycelium or moving between versions.
**Time to read**: 5 min.
**Last updated**: 2026-06-12

The short version: **uninstalling the plugin never touches your project state.** Your canvas, diamonds, memory, and decision log live in `.claude/` inside *your* repo and belong to you — the plugin only ships the framework (skills, hooks, engine docs) into Claude Code's plugin cache.

## Uninstall (plugin form)

```
/plugin uninstall mycelium@haabe-mycelium
```

What this removes: the framework — all `/mycelium:*` skills, hooks, engine docs — from the plugin cache.

What this leaves: everything under your project's `.claude/` — `canvas/`, `diamonds/`, `memory/`, `harness/decision-log.md`, `evals/`. These are plain YAML/markdown, readable without Mycelium installed. They are your product's documentation; deleting them is a separate, deliberate decision (`rm -rf .claude/` if you truly want it gone — consider archiving the canvas first, it's the record of what you learned).

Optional cleanup after uninstall:
- `.claude/settings.json` — remove any Mycelium-specific `env` entries (see [environment.md](environment.md)) or permission rules you added for it.
- `.claude/state/` — runtime state (read-log, change-log, plugin state); safe to delete.

## Uninstall (legacy form)

Legacy installs (pre-v0.20 npx-degit) templated framework files directly into `.claude/`. There the framework and your state are interleaved: framework files are the ones listed in `.claude/manifest.yml` (`framework.*` sections); everything else is yours. Either remove the manifest-listed framework files by hand, or — easier — run `/mycelium:migrate-from-legacy` first (it separates the two cleanly), then `/plugin uninstall`.

## Downgrade / version pinning

Plugin versions track the marketplace. To pin or roll back: uninstall, then install a specific ref from the marketplace/repo at the version you want. Your project state is forward-compatible by design (schemas validate permissively, `additionalProperties: true`) — but state written by a *newer* framework may reference mechanisms an older version lacks (e.g., a `definition_of_done` field from v0.43+ is simply ignored by older gates, not an error).

## Rollback after a bad upgrade

Project state is git-committed (the canvas is documentation-as-code), so a bad state migration rolls back with git: `git checkout <last-good> -- .claude/`. The framework itself rolls back by reinstalling the prior plugin version. The two are independent — that separation is the point of plugin form.

## Reinstalling later

`/plugin marketplace add haabe/mycelium` + `/plugin install mycelium@haabe-mycelium`, then run `/mycelium:diamond-assess` — a populated `.claude/` is picked up where you left off; nothing needs re-initialization.
