# Mycelium Prompt Optimization

A/B test instruction changes against eval benchmarks to continuously improve agent behavior.

## How It Works

1. **Capture baseline**: Run `/prompt-optimizer baseline` to record current performance
2. **Create variant**: Document a hypothesis in `variants/` (e.g., "v001-stronger-bias-prompts.md")
3. **Test variant**: Run `/prompt-optimizer test v001` to apply changes and measure
4. **Compare**: Run `/prompt-optimizer report` to see variant vs baseline
5. **Keep or revert**: Based on data, not opinion

## Directory Structure

```
optimization/
  baseline.json          # Current performance baseline (from /eval-runner run-all)
  README.md              # This file
  variants/              # Documented instruction change hypotheses
    v001-example.md      # Each variant describes what changed and why
  results/               # Test results per variant (gitignored)
  exemplars/             # Winning trajectories from clean eval runs (gitignored)
```

## Variant Format

```markdown
# Variant: v001-[short-name]

## Hypothesis
[What you believe will improve and why]

## Changes
[Specific CLAUDE.md or skill instruction changes]

## Expected Impact
[Which eval categories should improve]
```
