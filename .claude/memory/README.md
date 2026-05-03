# Memory — Self-Learning System

Memory is how Mycelium gets smarter over time. Every mistake, every successful pattern, every delivery insight is captured here so future sessions start with accumulated wisdom instead of a blank slate.

## What's Here

### Learning Artifacts
- **[corrections.md](corrections.md)** — Accumulated learning from mistakes. Every error the agent makes is logged with root cause, fix, and prevention rule. **Read before every task** (enforced by the preflight hook).
- **[patterns.md](patterns.md)** — Successful patterns worth reusing. When something works well, it's captured here so the agent applies it again.

### Journals
- **[product-journal.md](product-journal.md)** — Discovery-phase insights: what we learned about users, opportunities, and the problem space.
- **[delivery-journal.md](delivery-journal.md)** — Delivery-phase insights: technical decisions, implementation learnings, what surprised us during build.

## Two Memory Systems

Mycelium has two distinct memory systems. Don't confuse them:

| System | Location | Scope | Git? |
|--------|----------|-------|------|
| **Project memory** (this directory) | `.claude/memory/` | Team-level learnings about the product | Yes — shared |
| **Auto-memory** | `~/.claude/projects/<id>/memory/` | Per-user learnings between the human and the agent | No — personal |

**Routing rule**: If it's about the product or project, it goes here. If it's about how a specific user prefers to work with the agent, it goes in auto-memory.

## How Memory Grows

1. **Corrections**: After any mistake, the agent logs what went wrong, why, and how to prevent it. The preflight hook checks that corrections.md has been read before any implementation task.
2. **Patterns**: After successful work, the agent captures reusable approaches. Suggested at every phase transition.
3. **Journals**: Product and delivery insights are captured continuously, prompted at phase transitions.

Over time, corrections accumulate into a project-specific knowledge base that prevents recurring mistakes. When a correction appears 3+ times, `/feedback-review` suggests graduating it to a guardrail.

## Optional Field: detection_origin

Beyond the standard `Origin` field (whose output the failure was IN — `ai-generated` / `human-written` / `ai-assisted`), corrections may include an optional `Detection_origin` field naming WHO OR WHAT CAUGHT the failure:

| detection_origin | Meaning |
|---|---|
| `user` | The human user noticed and surfaced it |
| `agent_self` | The agent caught its own mistake mid-task |
| `hook` | A PreToolUse / PostToolUse hook intercepted it |
| `evaluator` | An eval scenario or gate evaluator detected it |
| `eval_runner` | `/eval-runner` flagged regression vs baseline |
| `external_review` | A code review, peer feedback, or user-of-the-product surfaced it |

### Why this distinction matters

`Origin` and `detection_origin` are independent. A 100% `ai-generated` Origin distribution might look like "AI is the only source of failures" — but if `detection_origin` is also 100% `user`, the real signal is "AI generates failures that the user catches." That's a harness-detection gap, NOT a code-quality problem. Adding more context to AI prompts wouldn't help; adding more harness checks would.

Surfaced 2026-05-03 via /corrections-audit (Action 4 origin investigation): the 100% ai-generated Origin in mycelium-roadmap dogfood was an artifact of the solo+AI workflow (every commit Claude-co-authored, user catches everything). Without `detection_origin`, the audit's interpretation defaulted to "improve AI prompt context" — which would have been the wrong intervention.

### Backward compatibility

The field is OPTIONAL. Existing entries without it remain valid. `/corrections-audit` ignores the field when absent and computes the additional distribution when present. Add to new entries going forward; do not retroactively backfill.
