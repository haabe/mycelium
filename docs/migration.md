# Migrating from legacy install to plugin form

**Audience**: existing Mycelium users who installed via `npx degit haabe/mycelium`. Skip if you installed via `/plugin install mycelium@haabe-mycelium` — you're already on plugin form.

**Time to read**: 5 minutes.
**Time to migrate**: ~5 minutes for a typical project; reversible via git.
**Last updated**: 2026-05-09.

## What changed and why

Mycelium 0.20.0 repackaged the framework as a Claude Code plugin per Anthropic's plugin spec. The architectural reason: the legacy `npx degit` install copied framework reference files (skills, hooks, engine rules, schemas) directly into your project's `.claude/` directory alongside your project state (canvas, diamonds, memory, decision log). That created two problems:

1. **Brownfield contamination** — running `npx degit haabe/mycelium .` in a project with an existing `CLAUDE.md` would overwrite it. Daniel Bentes (Produktleder.no, BDSK author) flagged this on 2026-05-08; receipts case at [`docs/receipts/cases/2026-05-08-bentes-install-model.md`](receipts/cases/2026-05-08-bentes-install-model.md).
2. **Upgrade ambiguity** — the upgrade script had to distinguish framework files from project state on every refresh, with manifest-driven preserved-paths logic. Mistakes in the manifest could silently nuke project state.

Plugin form solves both: framework reference content lives in plugin cache (`~/.claude/plugins/cache/...`), the user's `.claude/` holds only project state, and upgrades happen via `/plugin update` — Claude Code's atomic plugin replacement, not a script-driven refresh.

The legacy install path is supported during the v0.20.x transition. Plugin form is recommended for all new installs and the migration path below for existing installs.

## What does and doesn't change

| Surface | Legacy form | Plugin form | Migration impact |
|---|---|---|---|
| Project state (canvas, diamonds, memory, decision log, evals, active-metrics) | `.claude/` in your project | `.claude/` in your project | **No change** — preserved untouched |
| Framework reference (skills, hooks, engine, schemas, scripts) | `.claude/` in your project | `~/.claude/plugins/cache/...` | Deleted from your project; lives in plugin cache |
| Skill invocation | `/interview`, `/diamond-assess`, ... | `/mycelium:interview`, `/mycelium:diamond-assess`, ... | Namespace prefix added (Anthropic's plugin convention) |
| Upgrade command | `bash .claude/scripts/upgrade.sh` | `/plugin update mycelium@haabe-mycelium` | New surface |
| Hooks | `.claude/hooks/` + `.claude/settings.json` | Plugin manifest (`hooks.json`) | Plugin auto-wires; settings.json `"hooks"` block needs manual removal |
| CLAUDE.md / README.md / AGENTS.md | Possibly created/modified at install | Never touched | Plugin install is brownfield-safe |

The skill prefix is the friction point most users notice first. Two ergonomics that take the typing tax down:

- **Tab completion**: `/myc<Tab>` expands to `/mycelium:`. Then a few letters of the skill + `<Tab>` finishes it. `/mycelium:diamond-assess` is six keystrokes.
- **Natural-language invocation**: "run mycelium setup" or "have mycelium assess where we are" routes to the right skill via Claude Code's built-in command resolution.

There's no alias mechanism in Anthropic's plugin spec — `myc:foo` as a shortcut isn't on the table. Tab-complete + prose is the realistic answer.

## Migration paths

Pick the one that fits.

### Path A: agent-driven (recommended)

The fastest path. Inside Claude Code, with your existing legacy-install project as the working directory:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:migrate-from-legacy
```

The skill walks you through detection, plugin verification, working-tree check, the explicit "what will and will not change" preview, the script invocation, and verification. It refuses to proceed if your working tree is dirty (so the migration is reversible via git).

### Path B: shell-driven

If you prefer to run things yourself:

```bash
# 1. Inside Claude Code, install the plugin first
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium

# 2. From your project root, in a terminal:
cd /path/to/your/project
git status                                 # must be clean
bash .claude/scripts/upgrade.sh --migrate-to-plugin

# 3. Inspect what changed (project state should be intact):
git status
ls .claude/                                # canvas/, diamonds/, memory/, evals/, harness/{decision-log,warnings-log}.md, jit-tooling/active-metrics.yml

# 4. Manual: open .claude/settings.json and remove any "hooks" block referencing
#    .claude/hooks/. Plugin form provides hooks automatically.

# 5. Verify the plugin reads project state correctly:
#    Inside Claude Code: /mycelium:diamond-assess

# 6. Commit the migration:
git add -A
git commit -m "chore: migrate from legacy Mycelium to plugin form"
```

The `--migrate-to-plugin` flag is interactive when run from a terminal — it shows you exactly what it will delete and asks for confirmation. If your `upgrade.sh` is older than v0.20.10 (predates the flag), refresh the legacy install once first with `bash .claude/scripts/upgrade.sh` (without args), then re-invoke with the flag.

### Path C: manual

If you'd rather not run the script:

```bash
cd /path/to/your/project
git status   # must be clean

# Delete legacy framework directories (project state preserved):
rm -rf .claude/skills .claude/engine .claude/hooks .claude/scripts
rm -rf .claude/schemas .claude/domains .claude/orchestration
rm -rf .claude/templates .claude/tests .claude/agents

# Prune jit-tooling (preserve active-metrics.yml):
find .claude/jit-tooling -mindepth 1 -maxdepth 1 \
    ! -name 'active-metrics.yml' ! -name '.gitkeep' -exec rm -rf {} +

# Prune harness (preserve decision-log.md, warnings-log.md):
find .claude/harness -mindepth 1 -maxdepth 1 \
    ! -name 'decision-log.md' ! -name 'warnings-log.md' -exec rm -rf {} +

# Manually edit .claude/settings.json: remove the "hooks" block if present.

# Then install the plugin (inside Claude Code):
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium

# Verify:
/mycelium:diamond-assess

# Commit:
git add -A && git commit -m "chore: migrate from legacy to plugin Mycelium"
```

## What if it goes wrong

The migration commits nothing — the script (and the skill) require a clean working tree before proceeding, so the deletion lands in your working directory but not in git history until you commit. To roll back:

```bash
git reset --hard HEAD
```

This restores the legacy framework files. If you also installed the plugin, it doesn't conflict with the legacy files (different locations) — but if both are present and Claude Code loads both, you'd see duplicate skill firings. Either uninstall the plugin (`/plugin uninstall mycelium@haabe-mycelium`) or re-run the migration cleanly.

If the issue is more subtle — say `/mycelium:diamond-assess` reads your canvas but reports an unexpected state — that's almost certainly a project-state read issue, not a migration issue. Check `.claude/canvas/*.yml` and `.claude/diamonds/active.yml` are intact (they should be, by construction), then file a GitHub issue.

## Recovering from a broken legacy refresh

As of v0.20.x, upstream's `.claude/` no longer ships framework reference content (skills, hooks, engine, schemas live in the plugin cache only). If you tried to run `bash .claude/scripts/upgrade.sh` and hit one of these failures, you've found the deprecated-legacy edge:

### Failure: "Failed to pull upstream. Check version/tag exists"

Your local `upgrade.sh` predates v0.20.10 (it doesn't recognize the `--migrate-to-plugin` flag, OR the flag misparses as a version). Two fixes, in order:

1. Run **without arguments** first to refresh `upgrade.sh` from upstream main:
   ```bash
   bash .claude/scripts/upgrade.sh
   ```
2. Then re-invoke with the flag:
   ```bash
   bash .claude/scripts/upgrade.sh --migrate-to-plugin
   ```

If the no-args refresh fails too, see the next failure.

### Failure: "Upstream Mycelium no longer ships framework files in .claude/"

This is the v0.20.10+ stale-upstream detector firing — upstream main has moved past legacy form. Your project's `.claude/` framework tree is the most recent legacy snapshot you have locally; refresh from upstream is no longer possible. The script's recommendation is correct: migrate to plugin form.

```bash
bash .claude/scripts/upgrade.sh --migrate-to-plugin
```

This deletes your local legacy framework tree and preserves project state. Then install the plugin in Claude Code:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```

### Failure: "no such file or directory" on bash .claude/scripts/upgrade.sh

You don't have a local `upgrade.sh` at all — your install predates the script (very old) or you cloned a v0.20.x+ tree where upstream no longer ships it. Use the agent-driven path (Path A above) instead:

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:migrate-from-legacy
```

The skill detects the install state and walks the migration explicitly. It works without `upgrade.sh` being present locally.

### Failure: framework files missing after a successful refresh

Your refresh ran, but `.claude/skills/`, `.claude/engine/`, etc. are empty or absent. You're now on plugin-form-shape but without the plugin installed. Install the plugin (commands above) and verify with `/mycelium:diamond-assess`. If your canvas reads correctly, the migration is complete; commit the empty-tree state.

## Why we kept legacy supported during transition

Three reasons. First, abrupt removal would strand existing users mid-project. Second, plugin form depends on Claude Code's plugin runtime — agents that don't speak the plugin spec (Codex, Cursor, Aider, Copilot) still get framework value via `AGENTS.md` orientation, but the legacy npx-degit path remains useful as a portable installation channel for projects that don't want to depend on the plugin runtime. Third, dogfooding: the maintainer's own Mycelium repo runs both forms in parallel during the transition window, so smoke-testing happens on the same surface real users see.

The transition window closes at the canonical 0.20.0 bump on merge to main. After that, `npx degit haabe/mycelium` still works, but the legacy `.claude/` framework tree gets removed from upstream — fresh installs default to plugin form, and migration becomes mandatory for existing installs.

## Related

- [`docs/get-started.md`](get-started.md) — install for new projects (plugin form)
- [`docs/receipts/cases/2026-05-08-bentes-install-model.md`](receipts/cases/2026-05-08-bentes-install-model.md) — the architectural finding that drove the plugin pivot
- [`AGENTS.md`](../AGENTS.md) — cross-agent install guidance
- [`/mycelium:migrate-from-legacy`](../plugins/mycelium/skills/migrate-from-legacy/SKILL.md) — the agent-driven migration skill
- [`.claude/scripts/upgrade.sh`](../.claude/scripts/upgrade.sh) — the shell script with `--migrate-to-plugin` and `--check-migration` flags
