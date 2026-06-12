# Environment variables

**Audience**: operators configuring Mycelium beyond defaults; contributors writing hooks/scripts.
**Time to read**: 5 min.
**Last updated**: 2026-06-12

Every `MYCELIUM_*` environment variable in one place. All are **opt-in** — unset means default behavior; nothing here is required for normal use. Until this page (2026-06-12 gap analysis), these were documented only in the individual skill/hook files that read them.

| Variable | What it does | Read by | Default when unset |
|---|---|---|---|
| `MYCELIUM_AUTONOMOUS_RUN` | Declares an autonomous (headless / agent-to-agent) run — activates the substitution discipline and the `autonomous-evidence-guard` write-block. Consent surface, never auto-detected. See [autonomous-mode.md](autonomous-mode.md). | `hooks/autonomous-evidence-guard.sh`, `engine/autonomous-mode.md` discipline | Interactive behavior; guard is a no-op |
| `MYCELIUM_ATTRIBUTION_REGISTRY` | Path to a consent/attribution registry kept OUTSIDE the public repo (e.g. in a private companion repo). Used to check that personal identifiers in publicly-shipped files have naming consent, and by render skills' consent gate. | validate-template.sh Check 33; render-fleet skills; `/canvas-health` 8c(c) | Checks fail-open (skip with a note) |
| `MYCELIUM_CROSS_REPO_WATCH` | Colon-separated list of sibling repo paths. SessionStart scans their last-24h commit messages for canvas IDs (`opp-XXX`, `sol-XXX`, …) and surfaces matches — the cross-repo stale-state nudge (anti-pattern #8). | `hooks/session-start.sh` CHECK 8 | No cross-repo scanning |
| `MYCELIUM_BVSSH_CANVAS` | Overrides the path to `bvssh-health.yml` for the SessionStart cadence reminder — for setups where the assessment canvas lives in a sibling repo (framework self-hosting). | `hooks/session-start.sh` CHECK 1 | `$PROJECT/.claude/canvas/bvssh-health.yml` |
| `MYCELIUM_MIGRATE_AUTO` | Set to `cancel` to make the legacy-migration script abort instead of proceeding when it runs without a TTY (Claude Code's Bash tool has no TTY, so the script's interactive confirmation can't fire). | `migrate-from-legacy` migration script | Non-interactive runs proceed (the skill confirms with you first) |

Internal (not operator-facing): `MYCELIUM_PLUGIN_LOAD_OK` — deterministic marker emitted by `/mycelium:ping` for plugin-shape smoke tests.

## Conventions

- **Fail-open**: every variable degrades gracefully when unset — checks skip with a note rather than failing. The framework never requires environment setup to function.
- **Where to set them**: your shell profile, the project's `.claude/settings.json` `env` block, or per-invocation for headless runs (`MYCELIUM_AUTONOMOUS_RUN=1 claude -p "..."`).
- **Adding one** (contributors): follow the existing naming (`MYCELIUM_` prefix, SCREAMING_SNAKE), make it opt-in + fail-open, document it in the reading hook/skill AND in this table.
