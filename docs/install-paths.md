# Install variants, migration, and upgrading

**Audience**: operators choosing an install path, migrating between forms, or upgrading an existing project.
**Time to read**: 10 min.
**Last updated**: 2026-06-05.

Mycelium runs as a Claude Code plugin (post-v0.20.0) and as a legacy npx-degit install (pre-v0.20.0, deprecated). This page covers all install paths, the migration between them, upgrading, and self-hosted runtimes.

## Recommended: plugin install (any project, brownfield-safe)

Inside Claude Code:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:start
```

`/mycelium:start` is the recommended first-run command. It composes `/mycelium:setup` (project-state directories under `.claude/`) and `/mycelium:interview` (10-minute discovery on your idea) into one invocation, with a short welcome to bridge the install-to-value gap. Both sub-skills remain invocable directly if you prefer piecewise. None of the steps touch your project root files (CLAUDE.md, README, LICENSE). Idempotent: re-running on an initialized project routes to `/mycelium:diamond-assess` instead.

Skills are namespaced (`/mycelium:<name>`) per Anthropic's plugin convention. Use `/myc<Tab>` to expand the prefix, or invoke in prose ("run mycelium start", "have mycelium assess current state"). Claude Code routes either form.

For a step-by-step first-run walkthrough, see [get-started.md](get-started.md).

## Legacy install (deprecated as of v0.20.x)

The `npx degit haabe/mycelium` install path is **no longer supported** for new installs. As of v0.20.x, framework reference content (skills, hooks, engine, schemas, scripts) lives in the plugin cache, not in the user's project. A fresh `npx degit` would land an empty `.claude/` with no skills to invoke and no hooks to fire.

Existing legacy installs continue to work locally. To migrate to plugin form, see the migration section below. To recover from a broken legacy refresh, see [migration.md#recovering-from-a-broken-legacy-refresh](migration.md#recovering-from-a-broken-legacy-refresh).

The legacy path is scheduled for full removal in v0.21.0 (target: 2026-06-09 or earlier).

## Migrating from legacy to plugin form

If you already installed Mycelium via `npx degit` and want to switch to plugin form, your project state (canvas, diamonds, memory, decision log) is preserved. The agent-driven path:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:migrate-from-legacy
```

The skill walks through detection, plugin verification, the explicit "what will and will not change" preview, the migration script, and verification. Migration is reversible via git (`git reset --hard HEAD` before committing).

Or run the script directly: `bash .claude/scripts/upgrade.sh --migrate-to-plugin`. Use `--check-migration` to see which form your project is on without making changes. Full guide: [migration.md](migration.md).

> **Heads-up if your install is older than v0.20.10**: the `--migrate-to-plugin` flag was added in v0.20.10. If your local `.claude/scripts/upgrade.sh` predates it, the script will treat the flag as a version arg and fail with "Failed to pull upstream. Check version/tag exists: --migrate-to-plugin". Fix: run `bash .claude/scripts/upgrade.sh` (no args) once first to refresh your `upgrade.sh` from upstream main, then re-invoke with the flag. Surfaced during the maintainer's own self-migration on 2026-05-09.

## Upgrading

Mycelium is not a software library; it's instructions that reshape agent behavior. Upgrading replaces framework files while preserving your project state.

**Plugin form** (recommended, post-v0.20.0):

```
/plugin update mycelium@haabe-mycelium
```

Plugin auto-update is on by default for the official-style marketplace. Manual update: `/plugin marketplace update haabe-mycelium` followed by `/reload-plugins`.

**Legacy form**:

```bash
bash .claude/scripts/upgrade.sh          # latest
bash .claude/scripts/upgrade.sh v0.12.0  # specific version
```

After upgrading, run `/mycelium:diamond-assess` (plugin form) or `/diamond-assess` (legacy) to see your work through the new version's lens.

## Self-hosted runtimes

Mycelium runs on [opencode](https://github.com/anomalyco/opencode) with local models (Ollama, LM Studio) for users who want to escape Claude Code's pricing model. The substrate ports verbatim; three runtime safety mechanisms degrade to model-following-instructions rather than structural enforcement. Honest support matrix and setup steps: [integrations/opencode.md](integrations/opencode.md).

Other integrations: [Codex](integrations/codex.md), [Cursor](integrations/cursor.md).
