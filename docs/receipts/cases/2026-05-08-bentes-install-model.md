---
id: 2026-05-08-bentes-install-model
date: 2026-05-08
contributor: Daniel Bentes
contributor_link: CONTRIBUTORS.md#v090--computational-enforcement-layer
project: bentes-install-model
mechanism_or_status: plugin-form-shipped
commits: ["a515448", "4656910", "69c00c5", "eae91b6"]
subclass: install-model
---

# bentes-install-model — what a CTO-tier reviewer caught on first install

**Audience**: evaluators understanding why Mycelium switched to plugin form, and contributors interested in how a single architectural finding from a credentialed reviewer reshaped the install model.
**Time to read**: 5 min.
**Last updated**: 2026-05-09.

## The friction

Daniel Bentes (author of [synaptiai/bdsk](https://github.com/synaptiai/bdsk), longstanding peer-practitioner contributor since v0.9.0) installed Mycelium on 2026-05-08 and surfaced an architectural finding within hours of his first install. From his Slack message (verbatim):

> "Testet nå og min første feedback er installasjonsprosessen. Den installerer filer som refererer til mycelium som om den er prosjektet man jobber på. (Claude.md, Contributors, License, readme, etc). Den bør ikke installere det om man skal bruke rammeverket på et eksisterende prosjekt."

Translation: the install process drops files at project root that describe Mycelium-the-framework as if Mycelium IS the project — CLAUDE.md, CONTRIBUTORS, LICENSE, README. Wrong for greenfield (project root reads as if Mycelium is the product), worse for brownfield (would overwrite the user's existing CLAUDE.md, README, LICENSE). Mycelium needed to be additive.

## Why this finding mattered more than its size

Two reasons.

**First**: Daniel is the author of BDSK, a competing-and-complementary agentic framework, and has reviewed Mycelium architecturally since v0.9.0 (the computational enforcement layer he helped shape). His architectural intuition is high-quality signal — when he flags a structural debt, it deserves immediate engagement.

**Second**: the finding sat at the install gate. Every new user hits it before they ever invoke a skill. If install confuses or contaminates, Mycelium loses adoption at step zero. Daniel's friction was a window into every potential first-time user's friction.

The founder's first instinct was to reach for an init.sh script that replaced framework files with project-shaped templates. That instinct was wrong-shaped: the brownfield case (existing project with its own CLAUDE.md, README, LICENSE) doesn't tolerate replacement at all. Mycelium needed to be additive, not a clean-slate installer.

## What changed

The fix took ~3 hours of architectural analysis and ~3 hours of plugin scaffolding spread across 2026-05-08 and 2026-05-09.

**Architecture**: Mycelium repackaged as a Claude Code plugin per Anthropic's plugin spec. Plugin lives in plugin cache (`~/.claude/plugins/cache/...`); user's project state (canvas, diamonds, memory, decision-log) stays in user's `.claude/`. Project root files (CLAUDE.md, README, LICENSE, CONTRIBUTORS) are NEVER touched by the install. AGENTS.md becomes the canonical cross-agent instructions surface (open Linux Foundation standard, read by Codex / Cursor / Aider / Copilot / Claude Code as fallback).

**Mechanism**: a single-plugin marketplace at `haabe/mycelium`, install via `/plugin marketplace add haabe/mycelium && /plugin install mycelium@haabe-mycelium`. The plugin contains skills, hooks, agents, MCP server configs. A new `/mycelium:setup` skill creates project-state directories on first run — idempotent, brownfield-safe, never touches user-owned root files.

**Skill namespacing**: every Mycelium skill becomes `/mycelium:<name>` (per Anthropic plugin convention). Real UX cost — every reference, every receipt, every doc that mentions `/interview` or `/diamond-assess` updates. Founder accepted the tax in exchange for plugin-form discovery, brownfield-clean install, and cross-agent portability via AGENTS.md.

## What this case taught the framework

| Lesson | Where it lives |
|---|---|
| Plugin form is the right architectural shape for distribution | This case + plugin manifest + marketplace.json |
| Architectural debt at the install gate compounds — every user hits it | This case (first such case for Mycelium) |
| Credentialed reviewers' single-day findings are worth dropping other work for | This case (next-day pivot) |
| Mycelium's portability claim (multi-agent) needs a real surface, not just AGENTS.md aspirational language | AGENTS.md migration (forthcoming) |

## Mechanism + status

**Status**: plugin-form-shipped (first commits land 2026-05-09 on `feat/plugin-form` branch in upstream `haabe/mycelium`). Full skill namespace migration, AGENTS.md content migration, README install update, validator updates pending in subsequent commits on the same branch before merge to main as v0.20.0.

**Commits cited** (this branch):
- `a515448` — 0.20.0 bootstrap (marketplace.json + plugin manifest + smoke-test skill)
- `4656910` — 45 skills migrated into plugins/mycelium/skills/
- `69c00c5` — 10 hooks migrated with hooks.json wiring all event matchers
- `eae91b6` — `/mycelium:setup` skill for first-run project init (idempotent, brownfield-safe)

## Cross-references

- Contributor: [Daniel Bentes](../../CONTRIBUTORS.md#v090--computational-enforcement-layer) (BDSK author, Produktleder.no Slack peer-practitioner, longstanding architectural reviewer)
- Related framework: [synaptiai/bdsk](https://github.com/synaptiai/bdsk) — Behavior-Driven Specification Kit; Daniel's architectural review of Mycelium runs in parallel
- Related marketplace: [synaptiai/synapti-marketplace](https://github.com/synaptiai/synapti-marketplace) — inspired the plugin-form decision; future Mycelium listing under consideration
- Plugin spec: [Anthropic Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference)
- Cross-agent standard: [AGENTS.md](https://agents.md/) — Linux Foundation open standard
