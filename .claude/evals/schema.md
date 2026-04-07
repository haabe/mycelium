# Mycelium Eval Schema

## Scenario YAML Format

```yaml
name: "Human-readable name"
category: discovery | delivery | integration
difficulty: easy | medium | hard
description: |
  Detailed description of what this eval tests.

setup:
  files_to_read: []     # Files the agent should read for context
  canvas_state: {}      # Initial canvas state (if needed)
  setup_command: ""     # Shell command to set up test environment

task_prompt: |
  The prompt given to the agent. Should describe what needs to be done.

success_criteria:
  # Discovery evals
  opportunities_identified: 3        # Minimum opportunities in OST
  evidence_types_used: 2             # Minimum distinct evidence types
  bias_check_performed: true         # Was bias-check run?
  jtbd_dimensions: [functional, emotional]  # Required JTBD dimensions

  # Delivery evals
  tests_must_pass: ["src/**/*.test.*"]
  typecheck_must_pass: true
  lint_must_pass: true
  security_scan_must_pass: true
  a11y_check_must_pass: true         # For UI work

  # Integration evals
  diamond_progressed: true           # Did the diamond advance?
  theory_gates_logged: true          # Were all gates checked?
  canvas_updated: true               # Was the canvas updated?
  decision_logged: true              # Was the decision logged?

  # Custom
  custom_command: ""                 # Custom validation command
  files_must_exist: []
  files_must_contain: {}

budget:
  max_iterations: 3
  max_time_seconds: 300

tags: []
```

## Result JSON Format

```json
{
  "eval_name": "scenario-name",
  "category": "delivery",
  "difficulty": "medium",
  "timestamp": "2026-04-07T10:00:00Z",
  "passed": true,
  "iterations_used": 2,
  "time_seconds": 120,
  "validators": {
    "tests": true,
    "typecheck": true,
    "lint": true,
    "security": true,
    "a11y": null
  },
  "theory_gates_checked": 8,
  "theory_gates_passed": 8,
  "corrections_generated": 1,
  "bias_check_performed": true,
  "failure_reason": null
}
```

## Creating New Scenarios

1. Identify what aspect of Mycelium to benchmark
2. Create YAML in appropriate category directory
3. Define clear, measurable success criteria
4. Set realistic budgets
5. Run with `/eval-runner run category/name`
