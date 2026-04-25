# JiT Tooling — Just-in-Time Tech Stack Detection

Mycelium is language-agnostic and product-type-agnostic. It doesn't ship pre-configured linters, test runners, or CI pipelines. Instead, when a delivery diamond begins, it detects what you're building with and generates the right tooling configuration on the fly.

## How It Works

1. **Detection** ([detector.md](detector.md)) — Scans for package manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.) and non-software indicators (course outlines, prompt files, service contracts)
2. **Generation** — Produces validation suites, testing strategies, and CI patterns matched to the detected stack
3. **Confirmation** — Presents the detected config to the user before applying

## What's Here

### Detection
- **[detector.md](detector.md)** — The main detection engine. Identifies language, framework, test runner, linter, and product type from project files. **Start here.**
- **[metrics-detector.md](metrics-detector.md)** — Detects available metric sources (GitHub traffic, analytics platforms, review sites) for the `/metrics-pull` system.

### Strategy Templates
- **[testing-strategy.md](testing-strategy.md)** — Testing patterns adapted per detected stack (unit, integration, e2e, property-based)
- **[security-scanning.md](security-scanning.md)** — Security tool selection per stack (semgrep, gitleaks, bandit, etc.)
- **[cicd-patterns.md](cicd-patterns.md)** — CI/CD pipeline patterns per platform (GitHub Actions, GitLab CI, etc.)
- **[definition-of-done.md](definition-of-done.md)** — DoD checklist adapted per product type

### Metrics Adapters
- **[metrics-adapters/](metrics-adapters/)** — Per-source adapters for the metrics pull system (GitHub, etc.). Each adapter defines how to pull, normalize, and compute deltas for its source.

### Examples
- **[active-stack.example.yml](active-stack.example.yml)** — Example of a detected and confirmed tech stack
- **[active-metrics.example.yml](active-metrics.example.yml)** — Example of configured metric sources

## Philosophy

The JiT approach means:
- **No opinions shipped** — Mycelium doesn't force ESLint vs Biome, pytest vs unittest, or any other tool choice
- **Zero handover** — A new user clones the repo and the agent figures out the stack automatically
- **Detect-and-generate over pre-shipped catalogs** — If the stack isn't recognized, the agent researches it and generates appropriate tooling rather than failing
