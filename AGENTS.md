# Agents

This repository uses Mycelium, a theory-guided harness for AI-assisted product development. See [README.md](README.md) for what it is and why.

## If you are operating in this repo

**Claude Code agents (plugin install — recommended as of v0.20.0):**
```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
```
After install, run `/mycelium:start` (the recommended first-run command — composes setup + 10-minute discovery interview into one invocation). Skills are namespaced as `/mycelium:<name>` (e.g., `/mycelium:interview`, `/mycelium:diamond-assess`). Hooks (PreToolUse / PostToolUse / Stop / SessionStart / PostToolUseFailure) auto-fire. Plugin lives in `~/.claude/plugins/cache/...` — your project root stays user-owned.

**Invoking namespaced skills.** Anthropic's plugin convention requires `/<plugin>:<skill>`. Two ergonomics make the prefix tax cheap:
- **Tab completion** in Claude Code: `/myc<Tab>` expands to `/mycelium:`, then a few letters + `<Tab>` finishes the skill name.
- **Natural-language invocation**: prose like "run mycelium start" or "have mycelium assess where we are" routes to the right skill. Use whichever form is faster for you.

**Claude Code agents (legacy `npx degit` install — pre-v0.20.0):** your operating manual is [CLAUDE.md](CLAUDE.md). Read it first. Skills invoke as `/<name>` without namespace. Mycelium's full enforcement layer (hooks, gates, reflexion loops, framework-guard, secret detection) is Claude-Code-specific. Both install paths supported during transition; plugin form is the recommended path.

**Other agents (Codex, Cursor, Aider, Copilot, etc.):** active enforcement is not yet portable. You can still read and contribute to the canvas — see "Minimal path" below. The portable surface is **canvas reading + writing + decision logging**; Claude-Code-specific is **everything that fires automatically** (PreToolUse hooks, PostToolUseFailure reflexion, secret-detection, framework-guard). For non-Claude-Code agents, the canonical instructions surface is THIS file (AGENTS.md) — Codex / Cursor / Aider / Copilot read it natively. Claude Code falls back to AGENTS.md when no CLAUDE.md exists. The framework canonical content lives at `plugins/mycelium/` in the upstream haabe/mycelium repo (skill SKILL.md files are pure markdown — readable by any agent).

Agent-class consumers are tracked as a distinct persona in `.claude/canvas/jobs-to-be-done.yml#non_consumption.segments[1]`. If you're integrating Mycelium into another agent harness, open an issue — interest validates the L5 work.

## What's available

Two install forms during v0.20.x transition: **plugin form** (recommended, post-v0.20.0) ships under `plugins/mycelium/` in upstream and installs to `~/.claude/plugins/cache/...`; **legacy** ships at `.claude/` directly via `npx degit`. Both are supported until plugin form is canonical.

| Surface | What it is | Where | Claude-Code-specific? |
|---|---|---|---|
| Skills | 45 invocable workflows (interview, ost-builder, security-review, xai-check, etc.). Plugin form: namespaced as `/mycelium:<name>`. Legacy: `/<name>`. | Plugin: `plugins/mycelium/skills/*/SKILL.md`. Legacy: `.claude/skills/*/SKILL.md` | Auto-discovery is, prose is portable |
| Upgrade | Update Mycelium framework files in this project | Plugin: `/plugin update mycelium@haabe-mycelium`. Legacy: `bash .claude/scripts/upgrade.sh` (see [docs/ai-system-card.md](docs/ai-system-card.md), [.claude/engine/version-discipline.md](.claude/engine/version-discipline.md)) | No — pure shell or plugin command |
| Canvas | Source-of-truth product knowledge (YAML) — project state, lives in user project | `.claude/canvas/*.yml` (user's project, both install forms) | No — pure data |
| Diamonds | Active work state — project state, lives in user project | `.claude/diamonds/active.yml` (user's project, both install forms) | No — pure data |
| Memory | Accumulated corrections + patterns — project state, lives in user project | `.claude/memory/` (user's project, both install forms) | No — pure data |
| Hooks | Event-triggered behavior | Plugin: `plugins/mycelium/hooks/` with `hooks.json`. Legacy: `.claude/hooks/` with `.claude/settings.json` | **Yes** |
| Schemas | Validation contracts for canvas YAML | `.claude/schemas/canvas/*.schema.json` (legacy); migrating to plugin in subsequent commits | No — pure JSON Schema |
| Conventions | Canvas guidance (source_class, confidence, evidence types, action_flags) | Plugin: `plugins/mycelium/engine/canvas-guidance.yml`. Legacy: `.claude/engine/canvas-guidance.yml` | No |
| Receipts | Per-cycle case files of how Mycelium got smarter | [docs/receipts/](docs/receipts/README.md) | No — read-only doc |
| Style guide | Voice + scent rules for any doc edit | [docs/contributing/style.md](docs/contributing/style.md) | No |

## Minimal path (any agent)

For agents without Mycelium's hook layer, the operating loop is:

1. Read `.claude/diamonds/active.yml` to know which scale + phase the project is in
2. Read the relevant `.claude/canvas/*.yml` files to see what evidence has already been gathered
3. Read `.claude/memory/corrections.md` to avoid past mistakes
4. Before adding evidence, read 2-3 recent entries in the same canvas section to match voice (concrete + sourced + hedged, not interpretive)
5. Before actioning a flagged item in canvas (anything with "candidate / worth considering / next step / refresh"), check its status marker (OPEN / ON HOLD / RESERVED). Unmarked = ON HOLD by convention. See `canvas-guidance.yml#action_flags` — three install forms carry it: **plugin** at `~/.claude/plugins/cache/haabe-mycelium/mycelium/<version>/engine/canvas-guidance.yml` (where `<version>` matches the installed plugin; `/plugin list` shows it); **in-repo plugin** at `plugins/mycelium/engine/canvas-guidance.yml`; **legacy** at `.claude/engine/canvas-guidance.yml`. The fallback search order if you're unsure which install form is in use: in-repo plugin → legacy → plugin cache.
6. Make changes; record evidence with provenance; log decisions to `.claude/harness/decision-log.md`

### Concrete operating model per agent class

**Codex / Cursor / Aider / Copilot:**

- Treat the canvas as the spec. Before generating code, read the canvas section that defines what's being built (typically `gist.yml`, `services.yml`, `bounded-contexts.yml`).
- Treat `corrections.md` as a known-bad-patterns list. Avoid the shapes documented there.
- Mycelium's gates won't fire automatically; the user must run `/diamond-progress` (or its equivalent prompt) manually to check transition readiness.
- Decision-log entries are still valuable — they create the audit trail Phase 3 of the docs restructure will surface.

**Multi-agent orchestrators:**

- Treat the canvas as shared memory. Workers read; lead writes. The same discipline as `/fan-out` enforces in Claude Code.
- See [docs/usage-modes.md](docs/usage-modes.md) for the fan-out / fan-in pattern.

## Examples (minimal path in action)

**Adding evidence after an external interview** (any agent):

```yaml
# In the relevant canvas file (e.g., opportunities.yml#opp-007.evidence)
- date: "2026-05-08"
  type: external_human
  source_class: external_human
  source: "https://linkedin.com/in/...  message thread"
  captured_at: "2026-05-08T14:30:00Z"
  confidence: 0.6
  notes: "Verbatim quote: ..."
```

Before writing: skim 2-3 nearby evidence entries to match voice. After writing: validate with `python3 .claude/scripts/validate_canvas.py`.

**Logging a decision** (any agent):

Append to `.claude/harness/decision-log.md` with the structured fields documented at the top of that file (decision, context, alternatives + per-alternative `why_not`, theory, evidence, confidence). The contrastive `why_not_alternatives` field is required (Liao et al. 2020 — contrastive explanations land harder than purely positive ones).

## Upgrading Mycelium

When asked to "update Mycelium" or "pull the latest version": run `bash .claude/scripts/upgrade.sh`. The script pulls from `haabe/mycelium` upstream via `npx degit`, requires a clean git tree (`git stash -u && bash .claude/scripts/upgrade.sh && git stash pop` if you have WIP), and reports what changed.

The framework version is in `CLAUDE.md` first-line frontmatter. **A version bump that looks like a no-op (e.g., 0.15.1 → 0.15.1) means the upstream main branch drifted without a release tag** — either the maintainer hadn't bumped (which is now caught by `validate-template.sh` Check 26) or the upgrade ran from a tagged release. Read the Version line summary to see what changed; if the line itself didn't change but file count is high, that's a discipline gap and worth a corrections.md entry on the user's project side.

## Conventions for contributors

- **Canvas changes**: include provenance (url/source, captured_at, confidence). Schema: `.claude/schemas/canvas/`. Enums + evidence types + action_flags: `plugins/mycelium/engine/canvas-guidance.yml` (plugin form) or `.claude/engine/canvas-guidance.yml` (legacy install).
- **Decisions**: log to `.claude/harness/decision-log.md` (structured fields, contrastive `why_not_alternatives`).
- **Commits**: conventional-commits style; reference scale (L0–L5) when relevant.
- **Tests**: `bash .claude/tests/validate-template.sh` and `python3 .claude/scripts/validate_canvas.py`.
- **Docs voice**: [docs/contributing/style.md](docs/contributing/style.md) is authoritative for any edit under `docs/` or to README/AGENTS/CONTRIBUTORS.
