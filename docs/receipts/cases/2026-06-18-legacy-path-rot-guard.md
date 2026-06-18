---
id: 2026-06-18-legacy-path-rot-guard
date: 2026-06-18
contributor: Håvard Bartnes (founder, dogfood-session sweep)
contributor_link: CONTRIBUTORS.md
project: mycelium-roadmap (private; the dogfood project) → upstream framework
mechanism_or_status: shipped. v0.49.6–v0.49.8 repoint stale `.claude/{engine,orchestration,schemas}/` references across docs, plugin-internal docs, and runtime strings; a new `plugins/mycelium/scripts/check_legacy_paths.py` guards the code-span class and is wired into `validate.yml`.
commits: [0c3f951, 588d91d, b8d09eb]
subclass: dogfood-surfaces-rot-the-frameworks-own-checker-missed
---

# legacy-path-rot-guard: the link checker passed, the paths were still dead

**Audience**: contributors and operators who care about how migration debt hides from the checks built to catch it. Also: anyone who has run a "dead link" audit, watched it go green, and assumed the docs were clean.

**Time to read**: 4 min.
**Last updated**: 2026-06-18.

## The trigger

A routine house-cleaning of the dogfood roadmap. No bug report, no failing test — just a sweep for "everything dead, miswired, or stale." It found the same thing in two places: references to `.claude/engine/…`, `.claude/orchestration/…`, and `.claude/schemas/…` — directories that moved into `plugins/mycelium/` at the 2026-05-12 plugin migration and no longer exist in either tree at those paths. In a plugin-form install they live in the plugin cache (`${CLAUDE_PLUGIN_ROOT}/…`), never in the user's `.claude/`.

The uncomfortable part: the framework had **already run a dead-link sweep two days earlier** (v0.49.5, `check_doc_references.py`), and it had passed clean — 387 markdown links, zero dead. The rot was still there.

## Why the checker missed it (and why that is correct)

`check_doc_references.py` follows **markdown links only** — `[text](target)`. That scope is deliberate and documented: an earlier reference-graph recon that scanned bare path tokens produced ~377 hits at ~95% false positives. Restricting to author-intended links is what made the checker trustworthy.

But the legacy-path rot doesn't live in links. It lives in **code-spans and prose**: `` `.claude/engine/theory-gates.md` ``, `Defined in .claude/engine/diamond-rules.md`, a docstring, a hook's deny message. None of those are markdown links, so a link checker — correctly scoped — will never see them. A green link audit said nothing about this class. The absence of a signal got read as a clean bill of health.

That is the load-bearing lesson: **a check passing means the thing it checks is clean, not that the surface is clean.** Two checks with disjoint scopes can both pass while rot sits in the gap between them.

## The cheap path, and why we did not take it

The cheap reading: these are just doc typos, fix the handful you can see and move on. Two problems. First, "the handful you can see" undercounted — the sweep found the class across docs prose, plugin-internal engine docs, *and* runtime-surfaced strings (a hook deny message telling the user to check a path that doesn't exist; a `post-write-nudge.sh` schema check that resolved `$PROJECT_DIR/.claude/schemas/` and so silently never fired in plugin form). Stale runtime guidance is worse than a stale doc: it misleads at the moment of use.

Second, fixing the visible instances without a guard guarantees recurrence. The migration was six weeks and ~30 minors ago; the rot accrued the whole time precisely because nothing watched for it. Fix-without-guard is a promise to re-find it later.

## What shipped

Three patches, each a faithful slice rather than one big sweep:

- **v0.49.6** — doc-prose repoints to `plugins/mycelium/…` (`CLAUDE.md`, glossary, theories, ai-system-card, usage-modes, regulatory, skills index), and relative repoints in plugin-internal docs (which ship in the cache without the `plugins/mycelium/` prefix). New **`check_legacy_paths.py`** guards the code-span class the link checker excludes by design; wired into `validate.yml`.
- **v0.49.7** — the runtime-surfaced layer: hook/guard message strings, a generated `warnings-log.md` header, two docstrings, and the descriptive `surfaces.yml` registry. Plus the real bug: `post-write-nudge.sh` now resolves `${CLAUDE_PLUGIN_ROOT:-$PROJECT_DIR/.claude}/schemas/canvas/`, so the schema-validation nudge fires in plugin form again.
- **v0.49.8** — closed a flagged judgment call: the dogfood guard's "run `.claude/scripts/upgrade.sh` to sync" message was rewritten to be **install-form-aware** (Claude plugin: `/plugin update`; legacy: `upgrade.sh`; opencode: re-run `/mycelium:setup`), because there is no universal upgrade command across harnesses.

The guard's scope is the three dirs with **no** plugin-form runtime path (`engine|orchestration|schemas`). `skills` and `harness` are deliberately excluded — they *do* have legitimate runtime references (`.claude/skills/` after opencode vendoring; `.claude/harness/` holds user project state), and policing them would re-introduce the false-positive problem the link checker was scoped around. Intentional legacy mentions (`AGENTS.md`, `migration.md`, `migrate-from-legacy` SKILL) are allowlisted.

## What this case taught the framework

1. **A passing check is a scoped claim, not a global one.** `check_doc_references.py` going green meant "no dead markdown links" — full stop. The instinct to read it as "docs are clean" is the trap. The fix was a *second* checker with a complementary scope (code-spans / prose, narrow high-signal pattern), not a broadening of the first (which would have re-imported its false positives).
2. **Runtime-surfaced staleness outranks doc staleness.** A stale doc misleads a reader who goes looking. A stale hook message or a dead schema-path check misleads at the moment of action, silently. The v0.49.7 slice was prioritized for exactly that reason.
3. **Fix-with-guard, or expect recurrence.** The rot accrued for six weeks because nothing watched the class. Shipping `check_legacy_paths.py` into CI is what makes this a graduation rather than a one-time cleanup — the next reference that drifts fails the build instead of waiting for the next manual sweep.

## Mechanism + status

**Status**: shipped across v0.49.6–v0.49.8 (framework) alongside a sibling `check_doc_drift.py` guard in the dogfood roadmap's own CI. `validate-template.sh` green at HEAD; both doc guards pass; the roadmap's 7/7 behavioral battery passed against the updated framework.

Known follow-up, surfaced by writing this case: the receipts indexes (`by-date.md`, `by-mechanism.md`) have lagged since 2026-05-30 and are missing several recent cases — a `/framework-health` Step 4c maintenance item, not this commit's scope.

## Attribution note

Internal dogfood case. Sources are the live house-cleaning session and the three upstream commits (`0c3f951`, `588d91d`, `b8d09eb`) plus the version commit that ships this case. The dogfood project is private; the framework changes and this case are public.
