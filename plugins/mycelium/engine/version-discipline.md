# Version Discipline

Mycelium uses semver for the framework version line in `CLAUDE.md`. This document defines what triggers a bump and what tier — referenced from `validate-template.sh` Check 26 ("material framework changes require a version bump") and from the Mandatory Pre-Ship Protocol (`G-P-pre`).

## When to bump

| Tier | Trigger | Examples |
|---|---|---|
| **MAJOR** (X.0.0) | Backwards-incompatible change to mandatory user-facing behavior, or removal of a stable feature | Removing a guardrail, changing the manifest schema in a breaking way, retiring a skill that other skills depend on |
| **MINOR** (0.X.0) | New skill, new mandatory protocol, new gate, new convention with structural impact, new directory in manifest | Adding `/xai-check`; shipping G-V12; adding `agent_runtime_target` detector category; landing the warnings ingestor |
| **PATCH** (0.0.X) | Bug fixes, doc-only updates, ruff cleanup, eval-only changes, single-line typo fix in framework files | Fix to `validate_canvas.py` ID-uniqueness; doc clarification in CLAUDE.md without behavioral change; ruff lint pass |

The semver-tier choice is judgment, not arithmetic. When in doubt, **bump conservatively** (MINOR over PATCH) — overreporting a change is cheaper than underreporting it. Underreporting wastes the upgrade signal: downstream agents see "version unchanged" and assume nothing material happened, missing the actual delta.

## What counts as "material framework change"

Check 26 watches these paths:
- `.claude/skills/` — any SKILL.md or skill directory addition/modification
- `.claude/engine/` — engine docs (theory-gates, canvas-guidance, leaf-lifecycle, etc.)
- `.claude/harness/` — guardrails, anti-patterns, cognitive-biases, security-trust, etc.
- `.claude/hooks/` — runtime enforcement scripts
- `.claude/scripts/` — Python/Bash scripts (parse_manifest, validate_canvas, framework_guard, ingest_warnings, etc.)
- `.claude/jit-tooling/` — detector specs, metrics adapters, definition-of-done.md, etc.
- `.claude/templates/` — public-facing artifact templates
- `CLAUDE.md`, `AGENTS.md`, `README.md` — top-level framework docs
- `docs/` — public-facing artifacts (ai-system-card.md, context-surface.md)

Explicitly NOT material (so they don't force a bump):
- `.claude/canvas/*.yml` — project state, not framework
- `.claude/memory/*.md` — corrections/patterns/warnings logs
- `.claude/diamonds/active.yml` — diamond state
- `.claude/state/*` — runtime state
- `.claude/evals/*` — eval scenarios and results (instance data)
- `.gitignore`, `.github/workflows/` — CI plumbing (changes here are usually behind-the-scenes)

If a single PR spans both kinds, bump on the framework-side change and let the project-state edits ride along.

## What goes in the Version line summary

The line in `CLAUDE.md` (single source of truth, per `manifest.yml :: framework.version_source`) carries a one-paragraph summary of the headline changes. Keep it tight — one or two sentences per major thread, with theory citations where applicable. Downstream agents read this line on every upgrade; it's the canonical "what changed" surface.

## How the discipline is enforced

- **Pre-ship layer** (G-P-pre): the visible pre-ship analysis must include "version impact" as part of the schema/manifest checks. If the change is material, the analysis says so and proposes a tier.
- **CI layer** (Check 26 in `validate-template.sh`): comparing material file changes since the last version-line edit. FAILs if material changes exist and version is unchanged.
- **Convention layer** (this doc): explains the contract and gives examples. Read alongside `CLAUDE.md :: Mandatory Pre-Ship Protocol`.

## Why this exists (5th-instance graduation)

Sister convention to G-V12 (validator coverage proofs) — both close subclasses of the same recurring "documented rule diverges from enforcement" pattern. Five instances logged before this bump landed (corrections.md 2026-04-20 / 2026-04-28 / 2026-05-03 / 2026-05-04 ×2). Pre-committed graduation trigger fired at instance #5 (this); structural enforcement layer is now CI-tier rather than convention-tier.

## Cross-project signal that triggered this rule

Another Mycelium dogfood project ran `upgrade.sh` and saw "0.15.1 → 0.15.1, 42 files refreshed from main." The version was a no-op despite material drift. The agent in that project couldn't tell from the version line alone what had actually changed. This wasted the upgrade signal — exactly the failure mode this rule prevents.

## Example version-line shapes

```
*Version 0.16.0 -- Self-correcting harness layer: G-V12 + G-P-pre graduate two
recurring patterns to mechanism. /xai-check skill + Gate 13 + ai-system-card.
Warnings ingestor + corrections-audit cross-source pattern detection. ...*

*Version 0.16.1 -- Patch: ruff cleanup on .claude/scripts/, no behavioral change.*

*Version 1.0.0 -- Stable API guarantee. Manifest schema frozen. ...*
```

Each summary should answer: "If a downstream project's agent reads only this line on upgrade, will it know what changed?" If no, expand the line until yes.
