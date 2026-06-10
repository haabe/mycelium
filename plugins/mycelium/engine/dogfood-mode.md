# Dogfood mode

The pattern for running Mycelium end-to-end on a product (real or fictional) with explicit intent to surface framework gaps. When `dogfood: true` is set in `.claude/diamonds/active.yml`, stop conditions become Mycelium learnings rather than project deaths — a killed diamond generates a report in `.claude/evals/dogfood-reports/` and the framework gap caught is the real deliverable.

## Purpose

Unit evals at `.claude/evals/scenarios/` test individual skills and behaviors in isolation. Dogfood reports test the **emergent** behavior of the framework across a full session — the kind of gaps that only surface when multiple skills, gates, and hooks interact under real conditions.

Per LangChain's guidance on agent evals (2025), dogfooding is one of three canonical eval sources alongside public benchmarks and hand-crafted scenarios. It catches behaviors that parameterized evals would miss because they were unexpected.

## When to run a dogfood session

- **Before each minor release** (v0.x.0) — catch regressions and surface new gaps introduced by recent changes
- **After a large theoretical addition** — verify the new frameworks integrate cleanly with existing ones
- **When invited by community feedback** — external critique often reveals blind spots; a dogfood session can validate whether the critique holds in practice

## How to run a dogfood session

1. **Pick an object project** — a plausible product idea unrelated to Mycelium itself (a CLI tool, a course, an AI agent, etc.)
2. **Bootstrap from the plugin** — `/plugin install mycelium@haabe-mycelium` in a fresh directory, then `/mycelium:start`
3. **Set dogfood mode** — when the interview asks whether this is a real product or a learning vehicle, say "learning Mycelium itself." This sets `dogfood: true` and changes how stop conditions are interpreted.
4. **Run as a real session** — don't shortcut. Invoke skills when you would in a real project. Let the framework catch you when it should.
5. **Document everything** — decisions, deviations, mishaps, discoveries. The report is the deliverable.
6. **File the report** at `.claude/evals/dogfood-reports/YYYY-MM-DD-<project-name>.md` in the dogfood project (not the upstream Mycelium repo unless you are the maintainer).

## Report structure

Key sections:

- **Executive summary** — headline finding
- **The journey** — turn-by-turn narrative
- **What worked (wins)** — things to preserve
- **Gaps** — situations the framework didn't anticipate
- **Mishaps** — agent errors (not framework errors) worth noting
- **Threats** — structural risks surfaced by the session
- **Tightening recommendations, ranked** — action items ordered by value/cost
- **Meta-success notes** — what should not be broken in subsequent tightening

## Anonymization

Dogfood reports are committed to git and may be public. **Always anonymize before committing:**
- Refer to the operator as "solo developer", "team lead", etc. — never by name, age, or personal circumstances
- Product vehicle names are fine to include (they describe the test scenario, not the person)
- Remove or genericize any outreach targets, contact names, LinkedIn handles, or DM content
- If in doubt, ask: "Could someone identify the operator from this sentence?" If yes, rewrite it.

## Dogfood mode vs autonomous mode

Dogfood mode reframes **stop conditions** (a killed diamond becomes a Mycelium learning). It does **not** authorize substituting human input at blocking interaction points — that authority lives exclusively in `autonomous-mode.md` (declaration, substitution ladder, mandatory ledger, evidence-integrity boundary). The two are orthogonal and compose: a fully automated dogfood run declares both `dogfood: true` and autonomous mode. A dogfood session with a human at the keyboard needs nothing from autonomous mode. (Per opp-011: the 2026-06-11 Fable 5 evaluation found runs improvising substitution rules because this distinction was undocumented.)

## Automated dogfood

For automated agent-to-agent dogfood testing, see the **roadmap-repo** at `mycelium-roadmap/.claude/auto-dogfood/REBUILD-PLAN.md`. The auto-dogfood orchestrator was deleted in framework legacy cleanup (commit a5cabd3, ~2026-04) and is being reinstated as roadmap-private tooling per founder direction 2026-05-22 — not as framework-shared infrastructure at this stage. The orchestrator runs full-session scenarios with planted failure conditions and evaluates the framework's safety properties programmatically. Manual dogfood sessions (documented per this pattern) remain valuable for discovering gaps that automated sessions miss.
