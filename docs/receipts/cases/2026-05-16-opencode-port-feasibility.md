---
id: 2026-05-16-opencode-port-feasibility
date: 2026-05-16
contributor: Håvard Bartnes (founder)
contributor_link: CONTRIBUTORS.md
project: mycelium
mechanism_or_status: research-with-hands-on-verification
commits: []
subclass: port-feasibility
---

# opencode-port-feasibility — does Mycelium run on a second harness?

**Audience**: evaluators asking whether Mycelium is bound to Claude Code or portable; contributors weighing a second-harness adapter.
**Time to read**: 3 min.
**Last updated**: 2026-05-16.

## The question

Mycelium ships as a Claude Code plugin. opencode (sst/opencode) is the most-cited Claude Code alternative in the 2026 agent-CLI category. If a second harness can host Mycelium with low marginal cost, the framework's positioning shifts from "Claude Code accelerator" to "theory-grounded harness layer that several runtimes can host." That's a different artifact.

## Two-phase verification

**Phase 1 — desk research.** A general-purpose subagent mapped opencode's documented surfaces (CLAUDE.md fallback, AGENTS.md primary, native skill tool, plugin hooks, MCP, tool inventory) against Mycelium's runtime dependencies. Estimate at the end of desk research: **1–2 weeks of focused work** for parity, with two real gaps flagged — Read-before-Write enforcement, and a per-project memory tier.

**Phase 2 — hands-on test (this case).** A worktree-isolated subagent installed opencode 1.15.1 (`npm install opencode-ai`, no global), set up a test project with Mycelium symlinked in, and ran nine concrete tests. Auth failed at OpenRouter (401 "User not found"), so model-driven tests fell back to static and binary inspection.

## What changed from desk to hands-on

| Desk-research claim | Hands-on result |
|---|---|
| Read-before-Write "not documented, probable gap" | **Confirmed enforced** — opencode uses the verbatim same string-match precondition as Claude Code (binary inspection). Not a gap. |
| Skills auto-discovered from `.claude/skills/` | **False natively** — opencode only scans `.opencode/skills/`. But the third-party plugin `joshuadavidthomas/opencode-agent-skills` adds `.claude/skills/`, `~/.claude/plugins/cache/`, and `~/.claude/plugins/marketplaces/` to the scan list — one config line restores full discovery. |
| "Port commands" task | Collapses to zero — Mycelium has no `commands/` directory; all slash commands derive from SKILL.md frontmatter. |
| Plugin packaging | ESM only, not CommonJS. ctx exposes `client`, `project`, `worktree`, `$` shell, more. |
| Validators portable | Confirmed — `validate-template.sh` and `validate_canvas.py` run unchanged. |

**Revised effort: ~1–3 days** for a thin adapter, not 1–2 weeks. The portable substrate (canvas, memory, harness docs, validators, SKILL.md tree) is what Mycelium actually is; the harness-specific surface is thinner than the source tree's `.claude/` naming suggested.

## What this receipt is evidence of

Not "the port is done." The port hasn't started. What this case shows is that the **verify-by-installing-the-thing** discipline graduated 2026-05-15/16 (the per-claim verification protocol for external-agent landscape analyses) applied to a *port plan*. Desk research produced a usable map and missed two load-bearing claims; the hands-on test corrected both within ~30 minutes of real work. The cost of running the test was less than the cost of building one wrong week.

The remaining unknowns are now smaller and named: (a) `tui.prompt.append` actually reaches the model verbatim, (b) `tool.execute.after` failure signal shape vs Claude Code's `PostToolUseFailure`, (c) runtime Read-before-Edit error path (vs binary-confirmed enforcement). All three are gated on a working API key in opencode, not on opencode architecture.

## What it does NOT prove

- Mycelium runs *well* on opencode — only that it loads. Behaviour-validation needs a real session with model auth.
- The two-lane maintenance cost is bounded — that's a function of how disciplined the harness-neutral substrate stays as Mycelium grows, not just current-state portability.
- opencode users will adopt Mycelium — adoption is a separate, market-side question (L1 landscape, not L0 portability).

## Snapshot

- Worktree: `.claude/worktrees/agent-a9930760253193c94` (test artifacts; safe to remove once reviewed)
- opencode version tested: 1.15.1
- Tests executed: 8 of 9 (Test 7 MCP smoke skipped — out of scope for portability question)
- Tests that needed auth: 4 (marked UNVERIFIED in test report)
- Footprint left on host: `~/.local/share/opencode/` SQLite db (opencode auto-created); no global installs

Sources: subagent test report at `test-sandbox/PORT-TEST-RESULTS.md` inside the agent's worktree; opencode docs at opencode.ai/docs/{rules,skills,agents,commands,plugins,tools,mcp-servers,config,custom-tools}; third-party plugin at github.com/joshuadavidthomas/opencode-agent-skills.
