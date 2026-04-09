# Mycelium Dogfood Reports

Reports from sessions where Mycelium was run end-to-end on a product (real or fictional) with explicit intent to surface framework gaps. Each report follows the pattern established by the first dogfood session (macos-fileviewer, 2026-04-09).

## Purpose

Unit evals at `.claude/evals/scenarios/` test individual skills and behaviors in isolation. Dogfood reports test the **emergent** behavior of the framework across a full session — the kind of gaps that only surface when multiple skills, gates, and hooks interact under real conditions.

Per LangChain's guidance on agent evals (2025), dogfooding is one of three canonical eval sources alongside public benchmarks and hand-crafted scenarios. It catches behaviors that parameterized evals would miss because they were unexpected.

## When to Run a Dogfood Session

- **Before each minor release** (v0.x.0) — catch regressions and surface new gaps introduced by recent changes
- **After a large theoretical addition** — verify the new frameworks integrate cleanly with existing ones
- **When invited by community feedback** — external critique often reveals blind spots; a dogfood session can validate whether the critique holds in practice

## How to Run a Dogfood Session

1. **Pick an object project** — a plausible product idea unrelated to Mycelium itself (macos-fileviewer, a CLI tool, a data pipeline, etc.)
2. **Bootstrap from the template** — clone Mycelium, initialize a new project
3. **Run as a real session** — don't shortcut. Invoke skills when you would in a real project. Let the framework catch you when it should.
4. **Document everything** — decisions, deviations, mishaps, discoveries. The report is the deliverable.
5. **File the report** here with a dated filename: `YYYY-MM-DD-<project-name>.md`

## Report Structure

The macos-fileviewer report is the reference template. Key sections:

- **Executive summary** — headline finding
- **The journey** — turn-by-turn narrative
- **What worked (wins)** — things to preserve
- **Gaps** — situations the framework didn't anticipate
- **Mishaps** — agent errors (not framework errors) worth noting
- **Threats** — structural risks surfaced by the session
- **Tightening recommendations, ranked** — action items ordered by value÷cost
- **Meta-success notes** — what should not be broken in subsequent tightening

## Reports

| Date | Session | Object Project | Key Finding |
|---|---|---|---|
| 2026-04-09 | [macos-fileviewer](2026-04-09-macos-fileviewer.md) | Native macOS file viewer | Framework relies on agent discipline not enforced (T2) — 12 gaps identified |
