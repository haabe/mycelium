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
