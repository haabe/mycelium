# Auto-Dogfood

Automated agent-to-agent dogfood testing for Mycelium. Runs full-session scenarios
by alternating between a Mycelium Agent and a User Simulator, then evaluates the
framework's safety properties against success criteria.

## Quick Start

```bash
# Run a single scenario
python .claude/auto-dogfood/orchestrator.py run .claude/auto-dogfood/scenarios/sw-cli-solo-value-risk.yml -v

# Run all scenarios
python .claude/auto-dogfood/orchestrator.py run-all .claude/auto-dogfood/scenarios/ -v

# Generate report from results
python .claude/auto-dogfood/orchestrator.py report .claude/auto-dogfood/results/

# Compare two runs (A/B testing)
python .claude/auto-dogfood/orchestrator.py compare results/baseline.json results/variant.json
```

## Three Operating Modes

| Mode | Trigger | Purpose | Speed |
|------|---------|---------|-------|
| **Regression** | PR to `.claude/` | Catch regressions | ~10 min (4 scenarios) |
| **Exploration** | Weekly schedule / manual | Surface new gaps | ~45 min (all scenarios) |
| **Self-Learning** | On-demand | Fix → re-run → measure | Varies |

## Scenario Format

See `schema.md` for the full YAML format. Each scenario defines:
- **Product**: What the simulated user is building
- **Persona**: Who they are and how they answer questions
- **Planted failures**: Conditions the framework should catch
- **Journey**: Which skills to exercise in sequence
- **Success criteria**: What constitutes a passing scenario

## Current Scenarios

| Scenario | Product Type | Failure Mode | Key Test |
|----------|-------------|-------------|----------|
| `sw-cli-solo-value-risk` | software | Value risk | Stop condition + confidence downgrade |
| `sw-web-team-skip-discovery` | software | Skip discovery | Multi-layered skip resistance |
| `ai-agent-solo-confidence-inflate` | ai_tool | Confidence inflation | Sympathetic NPC detection |
| `course-solo-value-risk` | content_course | Value risk | Content-type gate routing |
| `sw-solo-evidence-decay` | software | Evidence decay | Stale evidence blocks progression |
| `sw-solo-perspective-conflict` | software | Perspective conflict | Trio resolution framework |
| `sw-solo-lifecycle-cycle-recording` | software | — (happy path) | Cycle-history recording at delivery |

## Adding Scenarios

1. Create a YAML file in `scenarios/` following `schema.md`
2. Add it to the `matrix.scenario` list in `.github/workflows/dogfood.yml`
3. Run locally first: `python orchestrator.py run scenarios/your-scenario.yml -v`

## Architecture

Each scenario runs in an isolated temp directory with a fresh Mycelium template.
The orchestrator alternates between:
1. **Mycelium Agent** — executes skills following framework protocols
2. **User Simulator** — plays the persona, answers interview questions

Results are evaluated against success criteria by parsing workspace state
(canvas YAML, diamond state, decision log).

## CI Integration

The GitHub Actions workflow (`.github/workflows/dogfood.yml`) runs:
- **On PR**: Regression suite (4 core scenarios in parallel)
- **Weekly**: Full exploration battery (all scenarios)
- **Manual**: Either mode via `workflow_dispatch`

## Dependencies

- Python 3.12+
- PyYAML (`pip install pyyaml`)
- Claude Code CLI (`claude` must be on PATH)
- `ANTHROPIC_API_KEY` environment variable (or Claude Code auth)
