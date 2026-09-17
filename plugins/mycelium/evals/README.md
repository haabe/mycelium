# Plugin evals (`claude plugin eval`)

A small suite for Claude Code's first-party plugin eval runner (Claude Code 2.1.269+). It is
separate from the project-state scenarios under `.claude/evals/`: those are authored and scored
by this framework, and their scores are never evidence that the framework works. This suite is
scored by the runtime, against a **no-plugin baseline**, so the number that matters is `Δ`:
what loading the plugin changed.

## What the three cases ask

| Case | Claim under test | Wrong answer |
|---|---|---|
| `deliver-framed-opening-routes-to-discovery` | A build request with no who, problem or evidence gets a discovery question before a data model | Schema first |
| `stated-certainty-gets-a-test-before-a-build` | "I'm sure they'll pay" is treated as an assumption, given a concrete smaller-than-the-product test and a failing condition | Accepts the claim, or says "validate it" in general terms |
| `unrelated-question-is-just-answered` | A plain technical question is answered without discovery interrogation (the interface-load check) | Process before the answer, or a skill invoked |

The third case is the one that can embarrass the plugin: a harness that interrogates every
prompt scores well on the first two and fails it.

## Run it

```bash
cd plugins/mycelium
claude plugin eval . --no-publish --max-cost-usd 10          # 3 cases x 3 runs x 2 arms
claude plugin eval . --case <name> --runs 1 --ablation none   # iterate on one case cheaply
```

Runs call the model on your credentials and cost money; `--max-cost-usd` is a ceiling on the
list-price estimate. Every case is read-only (`Read, Glob, Grep, Skill`), so no tool grants are
needed and nothing is written outside `evals/results/`, which is git-ignored.

## First pilot, 2026-09-17 (one run per arm, so noise-level)

| Case | WITH | W/OUT | Δ |
|---|---|---|---|
| `deliver-framed-opening-routes-to-discovery` | 0.00 | 0.00 | 0.00 |
| `stated-certainty-gets-a-test-before-a-build` | 1.00 | 1.00 | 0.00 |
| `unrelated-question-is-just-answered` | 1.00 | 1.00 | 0.00 |

Mean Δ 0.00, $1.64, no skill invoked in any with-plugin run. A second with-plugin run of the
first case, with the trace kept, also scored 0.00. That trace shows the plugin loaded, three
`SessionStart` hooks ran and exited 0, and the Agent Operating Contract was in context; the
model still opened with a PostgreSQL schema. Two readings, and the pilot cannot separate them:

1. **The runner under-represents the plugin.** Only `SessionStart` hook events appear in the
   trace. No `UserPromptSubmit` hook fired, and `discovery-trigger-guard.sh`, the hook built to
   catch exactly this opening, is a `UserPromptSubmit` hook. The case measures the contract and
   the skills without the prompt-level router.
2. **The contract alone does not route a build-framed opening in an empty project.** That is
   the claim the case was written to test, and on two runs it failed it.

The cases were not adjusted after the result. A case that fails is the suite working.

## What it does not cover

- **The hooks.** Eval runs remove `Write` and `Edit` unless granted, and each run starts in an
  empty workspace, so the PreToolUse gates never fire here. This suite measures routing and
  method, which travel through the SessionStart contract and the skills. The gates are covered
  by `tests/bash/`.
- **Not in CI.** A CI run needs credentials and a budget; that is a decision, not a default.
  The `Run evals in CI` section of the Claude Code docs has the flags when it is made.
- Three cases, judge-scored by a small model. Read the per-run explanations in `report.html`
  before trusting a `Δ`, and confirm any change at the default three runs.
