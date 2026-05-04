# Agents

This repository uses Mycelium, a theory-guided harness for AI-assisted product development. See README.md for what it is and why.

## If you are operating in this repo

**Claude Code agents:** your operating manual is CLAUDE.md. Read it first.

**Other agents (Codex, Cursor, Aider, Copilot, etc.):** Mycelium's active enforcement (hooks, gates, reflexion loops) is Claude-Code-specific today. You can still read and contribute to the canvas — see "Minimal path" below.

## What's available

| Surface | What it is | Where |
|---|---|---|
| Skills | 45 invocable workflows (interview, ost-builder, security-review, xai-check, etc.) | `.claude/skills/*/SKILL.md` |
| Upgrade | Update Mycelium framework files in this project | `bash .claude/scripts/upgrade.sh` (see also `docs/ai-system-card.md` for what's running and `engine/version-discipline.md` for what version bumps mean) |
| Canvas | Source-of-truth product knowledge (YAML) | `.claude/canvas/*.yml` |
| Diamonds | Active work state (which scale/phase the project is in) | `.claude/diamonds/active.yml` |
| Memory | Accumulated corrections + patterns | `.claude/memory/` |
| Hooks | Event-triggered behavior (Claude Code only) | `.claude/hooks/` |
| Schemas | Validation contracts for canvas YAML | `.claude/schemas/canvas/*.schema.json` |
| Conventions | Canvas guidance: source_class enum, confidence scoring, evidence types, action_flags | `.claude/engine/canvas-guidance.yml` |

## Minimal path (any agent)

1. Read `.claude/diamonds/active.yml` to know where the project is
2. Read the relevant `.claude/canvas/*.yml` files to know what's already established
3. Read `.claude/memory/corrections.md` to avoid past mistakes
4. Before adding evidence, read 2-3 recent entries in the same canvas section to match voice (concrete + sourced + hedged, not interpretive)
5. Before actioning a flagged item in canvas (anything with "candidate / worth considering / next step / refresh"), check its status marker (OPEN / ON HOLD / RESERVED). Unmarked = ON HOLD by convention. See `.claude/engine/canvas-guidance.yml#action_flags`.
6. Make changes; record evidence with provenance in canvas; log decisions

## Upgrading Mycelium

When asked to "update Mycelium" or "pull the latest version": run `bash .claude/scripts/upgrade.sh`. The script pulls from `haabe/mycelium` upstream via `npx degit`, requires a clean git tree (`git stash -u && bash .claude/scripts/upgrade.sh && git stash pop` if you have WIP), and reports what changed.

The framework version is in `CLAUDE.md` first-line frontmatter. **A version bump that looks like a no-op (e.g., 0.15.1 → 0.15.1) means the upstream main branch drifted without a release tag** — either the maintainer hadn't bumped (which is now caught by `validate-template.sh` Check 26) or the upgrade ran from a tagged release. Read the Version line summary to see what changed; if the line itself didn't change but file count is high, that's a discipline gap and worth a corrections.md entry on the user's project side.

## Conventions for contributors

- Canvas changes: include provenance (url/source, captured_at, confidence). For schema details, see `.claude/schemas/canvas/`. For enum values, evidence types, confidence calibration, and action_flags, see `.claude/engine/canvas-guidance.yml`.
- Decisions: log to `.claude/harness/decision-log.md`
- Commits: conventional-commits style; reference scale (L0-L5) when relevant
- Tests: `bash .claude/tests/validate-template.sh` and `python3 .claude/scripts/validate_canvas.py`

## Note for non-Claude agents

Mycelium's full value (gate enforcement, reflexion, hook-driven discoverability) requires Claude Code today. We treat agent-class consumers as a distinct persona (`go-to-market.yml#buyer_personas` schema comment). If you're integrating Mycelium into another agent harness, open an issue — interest validates the L5 work.
