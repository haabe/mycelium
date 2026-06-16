# Mycelium Documentation

**Audience**: contributors, evaluators, and operators who want depth past the README. Public.
**Time to read**: 5 min for this index; pages link to longer reads.
**Last updated**: 2026-06-12

This directory is the **spoke** to the README's **hub**. The README is the landing page (≤200 lines, scannable in 30s). Everything that doesn't fit in 30s lives here.

This file (`docs/README.md`) is the metadocumentation: it sets the rules every other doc in this tree must respect. Read it before adding or rewriting a page.

## Where to start

Three common entry paths, each anchored on a specific user task. Pick the one that matches what you arrived here to do.

- **Install and try it on a real project.** [Step-by-step first-run walkthrough](get-started.md), or [install variants and migration paths](install-paths.md) if you're already running an older form.
- **Understand how it thinks before adopting it.** [Mental model: scales, diamonds, gates, taught through one worked example](mental-model.md), then [why opinionated discipline, theory-grounded, in-loop preventive](philosophy.md).
- **Evaluate fit for your team or your project.** [Evaluate Mycelium for your team in ~1 hour, anti-promotional](evaluate.md), with the [30+ theory frameworks Mycelium integrates](theories.md) and the [case files of how Mycelium got smarter](receipts/) for evidence.

## Contents

- `get-started.md` — install (plugin or legacy) + first-run for a new or existing project
- `mental-model.md` — how to think in Mycelium: scales, diamonds, gates, taught through one worked example
- `philosophy.md` — why opinionated discipline, why theory-grounded, why in-loop preventive
- `glossary.md` — Mycelium-specific vocabulary (diamond, scale, canvas, gate, ...)
- `faq.md` — frequently asked questions, including the six that surfaced at the 2026-05-07 Juniors.dev presentation
- `evaluate.md` — how to evaluate Mycelium for your team in ~1h, anti-promotional
- `theories.md` — the 30+ frameworks Mycelium integrates, mechanism-mapped
- `usage-modes.md` — solo, team, agent orchestration, JIT tooling
- `autonomous-mode.md` — declared headless / agent-to-agent runs: declaration, evidence guard, model-tier restriction
- `environment.md` — every `MYCELIUM_*` environment variable in one place (all opt-in)
- `uninstall.md` — uninstall, downgrade, rollback; what stays (your `.claude/` state) and what goes
- `jit-tooling.md` — language-agnostic and product-type-agnostic detection
- `regulatory.md` — EU AI Act mapping (pointer to `ai-system-card.md`)
- `changelog.md` — version history extracted from `CLAUDE.md`
- `ai-system-card.md` — Mycelium's own AI System Card (Mitchell et al. 2019 format)
- `context-surface.md` — what data the agent reads under Mycelium
- `skills/` — index of all 55 skills
- `receipts/` — case files of how Mycelium got smarter (per project, per cycle)
- `contributing/` — how to contribute to the framework

## Audience markers (required on every doc)

Every public doc opens with three lines:

```markdown
**Audience**: <who this is for>
**Time to read**: <30s | 5 min | 30 min | deep>
**Last updated**: <YYYY-MM-DD>
```

Audience names match the segments in `.claude/canvas/jobs-to-be-done.yml` plus generic categories: *evaluators*, *contributors*, *practitioners*, *operators*, *researchers*, *non-developers* (designers, PMs).

Internal docs (`.claude/memory/cluster-instances.md`, `.claude/harness/decision-log.md`) carry an internal-audience marker instead:

```markdown
**Audience**: internal — published as audit trail, not as public reading.
```

## Voice rules

1. **No first-person plural.** Mycelium is one person and a framework. "Mycelium does X", not "we do X".
2. **Hedged confidence.** State evidence type behind any claim of effectiveness. "In one outside-user session..." beats "Mycelium reduces wrong-build risk."
3. **Specifics over abstractions.** Name the project, the commit, the date. Anonymous "users have reported" fails.
4. **No emojis** outside diagrams. README mermaid diagrams use them as visual hooks; prose does not.
5. **Anti-promotional on evaluation surfaces.** `evaluate.md`, `faq.md`, the README's "Who it's not for": disclose tradeoffs before benefits.
6. **No marketing voice.** No "powerful", "comprehensive", "robust". Show the receipt; let the reader judge.
7. **Cite the trigger.** When recommending a move, link to the source (decision-log entry, corrections.md row, theory gate, evidence in canvas) — same discipline as agent-side `(per: <source>)` citations in CLAUDE.md.

## Information scent rules (Pirolli/Card)

Every link must signal what's behind it. Audit each link before merging:

- **Bad**: "click [here](evaluate.md)"
- **Bad**: "see [evaluate.md](evaluate.md)" (filename leaks structure, not content)
- **Good**: "[Evaluate Mycelium for your team in 1 hour](evaluate.md)"

Link text should answer "what will I see if I follow this?" — readers scan link text without reading surrounding prose.

## Progressive disclosure layers (Nielsen)

The doc tree assumes four layers of attention:

| Layer | Time | Surface |
|---|---|---|
| 30s | landing | README headline + 5-line pitch + nav cards |
| 5 min | overview | README full read OR one of `evaluate.md` / `philosophy.md` |
| 30 min | considered | `theories.md`, `usage-modes.md`, `receipts/`, deep skill reads |
| deep | operating | `CLAUDE.md`, `.claude/engine/`, `.claude/harness/` |

Don't write a 30-min page when a 5-min page is the right surface. Don't bury 30s scent under 5-min text.

## Length budgets

| Surface | Soft cap | Hard cap |
|---|---|---|
| README | 200 lines | 250 lines |
| `docs/<page>.md` | 250 lines | 400 lines |
| `docs/receipts/cases/<case>.md` | 150 lines | 250 lines |
| `docs/skills/README.md` | 250 lines | 400 lines |

Over-cap = split, not shrink. A 300-line page that needs all 300 lines is a sign the content has two pages in it.

## Cross-link discipline

Each fact lives in one place. Other docs link to it.

- **Theory definitions**: `theories.md` is canonical. `glossary.md` links to it. SKILL.md files link to it on first occurrence.
- **Vocabulary**: `glossary.md` is canonical. Theory pages link out for definitions of theory-specific terms (e.g., "JTBD" links to `theories.md#jobs-to-be-done`).
- **Versions**: `changelog.md` is canonical. `CLAUDE.md` first-line frontmatter is the live version.
- **Receipts**: `docs/receipts/cases/` is canonical. README excerpts headlines + closing thesis only.
- **Contributors**: `CONTRIBUTORS.md` (people view) is canonical. `docs/receipts/cases/` cross-link in frontmatter.

If you find yourself writing the same paragraph twice, link instead.

## Maintenance discipline

Every doc carries a `Last updated` line. `/canvas-health` (extended in Phase 3) reads docs against an 180-day staleness threshold. When a doc references a mechanism that has been renamed, removed, or replaced — fix the doc, don't add a "removed" comment.

The `docs/contributing/style.md` page applies these rules in operating form. Read it before authoring a doc.
