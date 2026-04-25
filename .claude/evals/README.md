# Evals — Framework Self-Evaluation

Evals test whether Mycelium itself works correctly. They're integration tests for the framework — verifying that skills produce the right outputs, gates catch the right violations, and the system behaves as designed.

## What's Here

### Evaluation System
- **[schema.md](schema.md)** — The evaluation scenario format: inputs, expected behaviors, pass criteria
- **[pass-history.json](pass-history.json)** — Historical pass rates across eval runs

### Scenarios
- **[scenarios/](scenarios/)** — Test scenarios organized by domain:
  - `adversarial/` — Edge cases and attack vectors (can the agent be tricked into skipping gates?)
  - `delivery/` — Delivery phase scenarios (does the DoD checklist work?)
  - `discovery/` — Discovery phase scenarios (does the interview skill gather good evidence?)
  - `integration/` — Cross-skill integration (do skills compose correctly?)
  - `lifecycle/` — Full diamond lifecycle (can a diamond complete L0 through L5?)

### Results
- **[results/](results/)** — Raw output from eval runs

### Metrics
- **[metrics/](metrics/)** — Normalized metric snapshots from `/metrics-pull` (GitHub traffic, etc.), organized by source and date

### Dogfood Reports
- **[dogfood-reports/](dogfood-reports/)** — Findings from using Mycelium on itself. Framework gaps discovered through real usage.

### Overhead Measurements
- **[overhead-measurements/](overhead-measurements/)** — Token cost and latency measurements for hooks, skills, and guardrails

## Running Evals

Use `/eval-runner` to execute scenarios against the current framework state. Results are compared to `pass-history.json` to detect regressions.

The [auto-dogfood](../auto-dogfood/) system can run evals automatically and generate reports.
