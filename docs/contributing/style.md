# Style guide for Mycelium docs

**Audience**: contributors writing or revising any file under `docs/`.
**Time to read**: 5 min.
**Last updated**: 2026-05-08

This page operationalizes the rules in [docs/README.md](../README.md) (the metadocumentation). Read that first; this page tells you how to apply it.

## Voice principles

- **First person singular or none.** Mycelium is one person plus a framework; "we" is dishonest. Use "Mycelium does X" or the imperative ("Run `/interview`").
- **Hedged confidence.** Every effectiveness claim names its evidence type. Examples:
  - "In Drew Hoskins' 8-hour take-home (2026-04-30) Mycelium's Phase 0 selector saved..." — single-session evidence.
  - "Across three small dogfood projects, the corrections log accumulated..." — small-N pattern.
  - Avoid: "Mycelium reduces wrong-build risk."
- **Specifics over abstractions.** Name the project, the commit hash, the date. Anonymous "users have reported" fails the hedged-confidence rule.
- **Anti-promotional on evaluation surfaces.** `docs/evaluate.md`, `docs/faq.md`, the README's "Who it's not for" — disclose tradeoffs before benefits. Per L5 sycophancy correction (`.claude/memory/corrections.md` 2026-04-20).
- **No marketing words.** Drop "powerful", "comprehensive", "robust", "seamless", "best-in-class". Show the receipt.
- **No emojis outside diagrams.** Mermaid blocks may use them; prose may not.

## Information scent

Every link must signal what's behind it.

- ❌ "click [here](../evaluate.md)"
- ❌ "see [evaluate.md](../evaluate.md)"
- ✅ "[Evaluate Mycelium for your team in 1 hour](../evaluate.md)"

Audit by reading link text alone, top to bottom, with the rest of the prose hidden. If the page still answers "what will I see?", scent is good.

## Audience marker

Every doc opens with three lines:

```markdown
**Audience**: <who this is for>
**Time to read**: <30s | 5 min | 30 min | deep>
**Last updated**: <YYYY-MM-DD>
```

Internal artifacts (`.claude/memory/cluster-instances.md`, `.claude/harness/decision-log.md`) use:

```markdown
**Audience**: internal — published as audit trail, not as public reading.
```

## Length budgets

| Surface | Soft cap | Hard cap |
|---|---|---|
| README | 200 | 250 |
| `docs/<page>.md` | 250 | 400 |
| `docs/receipts/cases/<case>.md` | 150 | 250 |

Over-cap = split, not shrink.

## When to link vs duplicate

Each fact lives in one place. Cross-link.

- **Theory definitions**: `theories.md` is canonical.
- **Vocabulary**: `glossary.md` is canonical.
- **Receipts**: `docs/receipts/cases/` are canonical.
- **People credits**: `CONTRIBUTORS.md` is canonical.

When two pages reference the same fact, only one defines it; the other links.

## Receipts (case file) frontmatter

Every file under `docs/receipts/cases/` opens with YAML frontmatter:

```yaml
---
id: <slug>
date: <YYYY-MM-DD>
contributor: <name or "internal-dogfood">
contributor_link: <CONTRIBUTORS.md anchor or null>
project: <project name or "framework-development">
mechanism_or_status: <graduated mechanism name | "spec" | "one-off" | "in-progress">
commits: [<hash>, <hash>]
subclass: <if part of a known cluster, e.g. "documented-rule-diverges-from-enforcement">
---
```

Frontmatter exists so future `/corrections-audit` runs can detect candidate graduations from cases without parsing prose.

## Highlights rotation

The README's "How Mycelium got smarter" section shows 5 case headers. The full list lives in `docs/receipts/`. A given case stays on the README until: (a) a more recent case displaces it, OR (b) `/framework-health` flags the receipts on the README as static for >90 days. When rotated out, the case stays in `docs/receipts/cases/` — only its README mention rotates.

## Voice drift checklist

Before merging a docs change, scan the diff for:

- [ ] No "we" / "our" / "us"
- [ ] No marketing adjectives
- [ ] Every effectiveness claim cites evidence
- [ ] Every link signals destination
- [ ] Audience marker present and current
- [ ] `Last updated` reflects today
- [ ] No emoji in prose
- [ ] Length within budget (or split)

If any of these fails, fix before merge.
