---
id: 2026-05-16-phase0-substrate-audit
date: 2026-05-16
contributor: Håvard Bartnes (founder)
contributor_link: CONTRIBUTORS.md
project: mycelium
mechanism_or_status: audit-with-queued-rewrites
commits: []
subclass: substrate-neutralization
related: [2026-05-16-opencode-port-feasibility, 2026-05-16-opencode-phase1-runtime]
---

# phase0-substrate-audit — how Claude-Code-coupled is Mycelium's substrate?

**Audience**: maintainers + contributors weighing whether Mycelium's substrate (canvas, memory, harness, validators, SKILL.md tree, decision-log, CLAUDE.md) is actually harness-portable or just claims to be.
**Time to read**: 4 min.
**Last updated**: 2026-05-16.

## Why this audit

The 2026-05-16 decision-log entry "Adopt two-lane harness path" graduated Mycelium's substrate from "Claude Code plugin assets" to "harness-neutral source-of-truth." That's a claim about the substrate's portability. Claims without verification are the same epistemic class as the opencode runtime-claims that got overturned by Phase 1 testing earlier the same day. The audit is the verification.

A read-only subagent (Explore) swept 37 substrate files for four classes of Claude-Code coupling: tool-surface references, primitive names (hook events, slash-command syntax, auto-memory path), path/directory assumptions, and vocabulary/framing. The scan deliberately excluded `plugins/mycelium/` (the per-harness adapter is *meant* to be Claude-specific) and `docs/receipts/cases/` (immutable historical artefacts).

## What the audit found

**Substrate coupling is mostly visible and documented, not silently baked in.** AGENTS.md already labels 11 of 13 load-bearing Claude-Code-specific references with explicit "Claude-Code-specific" markers. Decision-log already graduated "harness-portable framework with Claude Code as first runtime" vocabulary. The substrate didn't fail neutralization through hidden coupling — it just hasn't been explicitly de-coupled yet.

**Four categories, condensed:**

| Category | Findings | Disposition |
|---|---|---|
| **A. Tool-surface references** | 13 load-bearing; concentrated in CLAUDE.md + corrections.md. "Read before Write" rule appears 3× and conflates Claude Code's tool-identity model with canvas-discipline doctrine. | Decouple the principle from the mechanism. |
| **B. Primitive names** | Hook event names (`PostToolUseFailure`, `PreToolUse`), slash-command namespace (`/mycelium:<name>`), auto-memory path (`~/.claude/projects/<id>/memory/`). | Already labelled Claude-Code-specific in AGENTS.md; no surprises. |
| **C. Path/directory** | `.claude/` referenced 203 times. Treated as a location convention, not a semantic constraint. | No remapping work needed. Locations are conventions. |
| **D. Vocabulary/framing** | "Mycelium is a Claude Code plugin" appears 3× (accurate for v0.20+, decision-log already graduated to broader framing). | Transitional; will rewrite when next major arc opens. |

**Estimated total remediation effort: 8–12 hours of documentation rewrites.** All PATCH-class (doc-only, no schema/skill/behaviour change).

## Three rewrites queued

The audit recommended three specific changes that, taken together, would shift Mycelium's substrate from "documented as harness-portable" to "structurally harness-portable." All three are **queued, not executed** — deferred until either (a) the opencode adapter becomes demand-pulled by a real cohort participant adopting opencode as their harness, OR (b) a quiet maintainer block opens up post-Juniors.dev cohort signal close.

### Rewrite 1 — Decouple Read-before-Write rule (CLAUDE.md lines 123–132)

**Current**: "Claude Code's `Write`/`Edit` tools require a prior `Read` tool invocation (same tool, same session) on existing files. `cat` / `head` / `grep` via Bash do NOT satisfy this check — different tool surfaces."

**Target**: extract the principle ("verify file state before mutation; ad-hoc shell reads lack the same safeguard as a dedicated read-tool because the tooling is different") and write it harness-agnostically. Add a small adapter section noting which tool surfaces satisfy "read" on each harness (Claude Code: Read tool; opencode: investigate).

**Effort**: ~2 hours.

### Rewrite 2 — Externalize hook event names to a mapping table

**Current**: `PostToolUseFailure`, `PreToolUse`, `SessionStart` referenced directly in CLAUDE.md (line 152), corrections.md (multiple), patterns.md (line 73). If opencode replaces these (e.g., `tool.execute.after` instead of `PostToolUseFailure` — already verified imperfect via 2026-05-16 Phase 1), substrate docs become inaccurate.

**Target**: create `.claude/harness/hooks-mapping.md` (a harness-adaptive lookup table mapping abstract Mycelium hook concepts to per-harness event names). Replace substrate-level references to specific hook names with references to the abstract concept + a pointer to the mapping table.

**Effort**: ~1.5 hours.

### Rewrite 3 — Rename "auto-memory" to "per-session user memory"

**Current**: CLAUDE.md and `.claude/memory/README.md` describe a memory tier at `~/.claude/projects/<id>/memory/`. The path is Claude-Code-specific.

**Target**: rename the section header to a principle-focused term ("Per-Session User Memory"). Keep `.claude/projects/...` as the current concrete path but add a per-harness note. The concept (user-local, per-project, not committed to git, complements project memory in `.claude/memory/`) is fully portable.

**Effort**: ~1 hour.

## What this case proves

- Mycelium's substrate-neutralization claim is **verifiable** (37 files scanned, four coupling categories, all findings located by file:line).
- The substrate is **closer to neutral than its current naming suggests** — `.claude/` paths are conventions, not semantics; coupling is concentrated in <5 specific rule statements; vocabulary is already graduated in the right direction by AGENTS.md and the 2026-05-16 decision-log.
- The remediation cost is **bounded and small** — 8–12 hours of doc rewrites, no schema or skill changes.

## What it does NOT prove

- That the rewrites would survive contact with the opencode adapter without further refinement. The audit identified *where* coupling lives; whether the proposed rewrites are sufficient is a downstream question.
- That the substrate is portable beyond Claude Code + opencode. The audit framed coupling against opencode's known surfaces; a third harness (Codex, Cursor, Aider) would need its own pass.
- That coupling is the only obstacle to portability. Behavioural questions (does the framework actually *work* on opencode end-to-end?) remain gated on the upstream issues filed today (anomalyco/opencode #27899, #27900, #27901).

## Snapshot

- Files scanned: 37 substrate markdown files
- Load-bearing findings: 13 (concentrated in 4 files)
- Findings already labelled Claude-Code-specific in substrate docs: 11/13
- Rewrites queued: 3, total ~4.5 hours
- Rewrites executed in this case: 0 (queued, not executed)

Sources: Explore subagent audit 2026-05-16; AGENTS.md section "What's available"; decision-log entry 2026-05-16 "Adopt two-lane harness path" and its 2026-05-16 supersession.
