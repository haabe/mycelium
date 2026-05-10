# Context Management — Mycelium's Context-Rot Defense Layer

Mycelium operates on agentic LLM substrates (primarily Claude). All such substrates degrade as conversation context grows — a phenomenon practitioners call **context rot**. This document codifies Mycelium's structural defense against context rot and names the implicit mechanisms already shipped.

Most of the mechanisms below predate this document. The document's job is to make them legible as a coherent layer rather than scattered design choices, so they can be defended, audited, and extended.

## What context rot is

Six distinct mechanisms bundled under one term — varying empirical support:

| # | Mechanism | Empirical status | Primary source |
|---|---|---|---|
| (a) | **Lost-in-the-middle** — U-curve recall, attention biased to start/end of context | Strong (peer-reviewed) | Liu et al. 2023, "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172) |
| (b) | **Attention dilution** — finite "attention budget"; n² pairwise relationships compete | Strong | Anthropic Engineering, "Effective context engineering for AI agents" (anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| (c) | **Instruction drift** — early instructions dominated by recent tool outputs | Practitioner folklore + face validity | (no canonical paper) |
| (d) | **Needle-in-haystack degradation** — vanilla NIAH saturated, but multi-needle / semantic / distractor variants show real degradation | Strong | Chroma "Context Rot" study (research.trychroma.com/context-rot); RULER (NVIDIA, NeurIPS 2024) |
| (e) | **Compaction quality loss** — each summarization pass is lossy compression | Strong (worked failure case) | Anthropic Claude Code postmortem 2026-04-23 (anthropic.com/engineering/april-23-postmortem) |
| (f) | **Prompt-cache bloat** — caches incentivize stuffing prefix; cache speeds up but doesn't fix attention | Logical, well-attested | (no canonical paper) |

**Claude-specific empirical findings** (Chroma study, 18 models including Opus 4 / Sonnet 4):
- Claude is the most **conservative abstainer** (lowest hallucination rates — says "I can't find this" rather than confabulate).
- Claude shows the **largest performance gap between focused (~300 token) and full (~113K token) prompts** on LongMemEval. **Claude is especially sensitive to irrelevant surrounding context.**
- 1M-token window is real but quality degrades materially past ~256K (Opus 4.6 ~78% MRCR at 1M, ~92-93% at 256K per Martin Alderson).

**Agent loops are the worst case.** Single-shot prompts hit context rot once; multi-turn chats accumulate it linearly; agent loops compound it multiplicatively (every tool call appends call + result; every retry appends failure trace; every sub-task pulls in reference material). Lost-in-the-middle predicts adherence to *original* instructions degrades first.

## How Mycelium structurally defends

| Rot mechanism | Mycelium-side defense | Where it lives |
|---|---|---|
| (a) Lost-in-the-middle | Mandatory Pre-Task Protocol explicit "early and late context" ordering; Recency Bias in Context entry naming the failure mode | `CLAUDE.md`, `harness/cognitive-biases.md` |
| (b) Attention dilution | Phase-scoped guardrail loading (40-instruction budget per phase, Haagsman/Horthy citations); JiT detection (load only what's needed); `instruction_budget` field on every SKILL.md | `harness/guardrails.md`, `jit-tooling/detector.md`, all SKILL.md frontmatter |
| (c) Instruction drift | Two-memory system (project memory externalized to `corrections.md`/`patterns.md`, not held in conversation); Read-before-Write hard rule (don't trust conversation memory of earlier reads); decision-log as out-of-context persistence | `CLAUDE.md` two-memory section, anti-pattern #7 |
| (d) Needle-in-haystack | Canvas as Single Source of Truth (replaces wiki/conversation history); `/canvas-health` lints for staleness; `/devils-advocate` Technique 4 attribution check forces explicit evidence sourcing | `CLAUDE.md` Canvas section, `/canvas-health`, `/devils-advocate` |
| (e) Compaction quality loss | Decision-log + corrections.md + patterns.md + receipts cases survive compaction by design; `metrics-adapters/GENERATING.md` explicitly designed for "future agent after compaction" | All memory + receipts artifacts |
| (f) Prompt-cache bloat | Not currently addressed at framework layer. Mycelium does not assume or recommend a specific caching strategy. | (gap — see below) |

The framework's "externalize-everything" philosophy is structurally context-rot mitigation. Canvas + decision-log + corrections.md + patterns.md + receipts together form a structured external memory that survives both compaction and conversation reset. This is what Anthropic recommends as the harness-layer strategy ("effective harnesses for long-running agents"). Mycelium ships it as the *default*, not a power-user pattern.

## Why this matters more for Claude than for other agents

Chroma's empirical finding that Claude is "especially sensitive to irrelevant surrounding context" makes Mycelium's phase-scoped loading + JiT detection particularly Claude-suited. The framework's discipline of **not loading discovery context during delivery work and vice versa** is exactly the variant of context discipline Claude rewards most. Conversely: deploying Mycelium on a model with weaker focus-on-relevant-context gets you back the value lost; deploying it on Claude gets you both that value AND the substrate alignment compounding.

## The blind subagent pattern

Sub-agent dispatch with read-only canvas snapshot (used by `/mycelium:fan-out` and the assumption-test workflow) is structurally a context-rot defense even when not framed as such:

- Each sub-agent gets a **clean attention budget** — fresh context window, only the task description + canvas snapshot it needs.
- Parent receives **compressed result** — sub-agent's full reasoning trace stays in its window, not the parent's.
- Drift-prevention: sub-agent doesn't see the conversation history that may already be context-rot-degraded.

This is the canonical Anthropic-recommended pattern for long-running agent loops. Mycelium's `feedback_assumption_test_method.md` (in user auto-memory) and `orchestration/fan-out-fan-in.md` document the *practice* of this pattern; this document names the *theory*.

**When to dispatch a blind subagent:**
- The current conversation has been running for many turns and you need a fresh attention budget.
- A specific task (research, validation, audit) is bounded and produces a summarized output.
- You want to avoid anchoring the sub-agent on the parent's framing (the blind subagent gets the canvas + the question, not the parent's interpretation).

**When NOT:**
- The task requires the parent's conversational context (e.g., follow-up to a specific exchange).
- The task is fast enough that subagent setup overhead exceeds savings.

## Per-graduation attribution discipline (new 2026-05-10)

Anti-pattern #7 (Consistency-as-Evidence) graduated 2026-05-09 with enforcement at canvas-write time and conversational-confirmation time. A new failure surface surfaced 2026-05-10 during the same-day session: **graduation-velocity** — multiple version bumps in one session where a single genuine lived-friction trigger extended into a graduation streak via consistency rather than each graduation having its own attribution.

The defense is per-graduation attribution labels in changelog entries:

- `lived-friction-triggered` — a specific Mycelium failure surfaced and the graduation directly fixes it. Highest-confidence trigger class.
- `research-while-here` — gap analysis or research surfaced candidates while related work was in flight. The work is real but the trigger is opportunity, not failure.
- `maintenance-housekeeping` — version drift fixes, citation backfills, doc restructures, mechanical sweeps. Trigger is hygiene, not insight.
- `scheduled-discipline` — recurring audit (e.g., quarterly `/framework-health`) graduating accumulated candidates.

Each version-line summary should include the dominant attribution label (most graduations are mixed; pick the one that explains ≥60% of the work). `/mycelium:corrections-audit` can flag streaks of one type or unusual mode-shifts; `/mycelium:framework-health` can quarterly-review whether the mode mix has been healthy.

**This document itself ships under attribution `research-while-here`** — the gap analysis (lawsofsoftwareengineering.com 2026-05-10 + Chroma context-rot study) surfaced the candidate; no specific Mycelium failure forced this doc to exist. Connection to lived-friction is medium (today's CLAUDE.md restructure was implicit attention-budget management; today's 4 bumps are the multi-turn agent-loop scenario the research describes), not strong.

## Known gaps (do not graduate without trigger)

1. **Prompt-cache strategy.** No guidance on cache invalidation tied to corrections.md/canvas changes, or the bloat-incentive that caches create. Wait for evidence Mycelium hits cache-bloat issues; the framework doesn't currently use prompt caching itself.
2. **Conversation-length detection.** No mechanism to detect "this conversation is getting context-heavy, time to compact or reset." The Knowledge Reconstruction Tax anti-pattern names the failure shape; detection would need session-token-count instrumentation that Claude Code doesn't currently expose to plugin code.
3. **Instruction-budget calculation rules.** Skills carry `instruction_budget: N` (range 6-205) but no doc explains how the budget is computed or how multi-skill sequences should be budgeted. Worked examples + composition rules are missing.
4. **Coherent-haystack risk.** Chroma's counterintuitive "coherent haystacks perform worse than shuffled" finding applies to richly-coherent canvas blocks (e.g., `landscape.yml#strategic_frame` with multiple metadata sub-blocks). No current Mycelium mechanism flags this risk.

## Theory citations

- **Liu et al. 2023**, "Lost in the Middle: How Language Models Use Long Contexts," arXiv:2307.03172. Peer-reviewed source for U-curve attention bias.
- **Chroma Research**, "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (research.trychroma.com/context-rot, 2025). 18-model empirical study including Claude Opus 4 / Sonnet 4 / 3.7 / 3.5 / Haiku 3.5; multi-needle, semantic, distractor variants.
- **NVIDIA RULER** (Hsieh et al., NeurIPS 2024, arXiv:2404.06654). NIAH extension confirming that vanilla NIAH-saturation hides real degradation.
- **Anthropic Engineering**, "Effective context engineering for AI agents" (load-bearing post on harness-level mitigations).
- **Anthropic Engineering**, "Claude Code postmortem 2026-04-23" (worked failure case where compaction logic fired every turn instead of once).
- **Anthropic Engineering**, "Effective harnesses for long-running agents" (recommends sub-agent dispatch + just-in-time retrieval + structured external memory — exactly Mycelium's three load-bearing patterns).
- **Martin Alderson**, "Why Claude's new 1M context length is a big deal" (martinalderson.com/posts/why-claudes-new-1m-context-length-is-a-big-deal) — independent measurement showing 1M context real but degrading past ~256K.

Honest caveats: lost-in-the-middle and Chroma's NIAH-extension findings are well-supported. Instruction drift, prompt-cache-induced bloat, and most agent-loop compounding claims are practitioner folklore with strong face validity but limited controlled evidence. "Context rot" is not a single peer-reviewed phenomenon; it's a useful umbrella that bundles ~6 distinct mechanisms with varying levels of empirical support.

## Cross-references

- `${CLAUDE_PLUGIN_ROOT}/harness/cognitive-biases.md` — Recency Bias in Context (the agent-side bias that lost-in-the-middle creates)
- `${CLAUDE_PLUGIN_ROOT}/harness/anti-patterns.md` — Knowledge Reconstruction Tax (the structural failure mode when context-rot defense fails); Cognitive Offloading Loop (the human-side complement)
- `${CLAUDE_PLUGIN_ROOT}/jit-tooling/detector.md` — JiT philosophy (Tesler's Law applied: complexity moves to agent at moment-of-need, reducing pre-loaded context bloat)
- `${CLAUDE_PLUGIN_ROOT}/engine/version-discipline.md` — per-graduation attribution discipline (Hyrum / Leaky Abstractions context for why the discipline exists)
- `${CLAUDE_PLUGIN_ROOT}/skills/fan-out/SKILL.md` — blind subagent dispatch implementation
