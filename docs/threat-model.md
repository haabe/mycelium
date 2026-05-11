# Mycelium Threat Model

**Audience**: security reviewers, plugin auditors, downstream maintainers, contributors evaluating Mycelium for adoption.
**Time to read**: 8 min.
**Last updated**: 2026-05-11.

This document consolidates Mycelium's threat model. The pieces previously lived scattered across `plugins/mycelium/harness/security-trust.md` (per-stage controls), `docs/ai-system-card.md` (transparency / accountability), and the cognitive/security anti-pattern catalog (`plugins/mycelium/harness/anti-patterns.md`). This page is the canonical entry point for "what attacks does Mycelium worry about, and what does it do about them" — primary audience is external reviewers who shouldn't have to assemble the answer from five files.

## What Mycelium is and is not (for threat-modeling purposes)

Mycelium is **a Claude Code plugin** that ships skills, hooks, harness directives, and a canvas state model. It is **not** a code-execution runtime, not a sandbox, not a credentials manager, not an MCP server. It does not host models, does not transmit user data anywhere it didn't originate, does not mediate network access. Threats around runtime sandboxing, network egress, model hosting, and credentials live with the host (Claude Code) or the substrate (Anthropic's API / model layer), not with Mycelium.

What Mycelium DOES own as security surface:
- Framework files (skills, hooks, engine docs) shipped via the Anthropic plugin marketplace
- A hook layer that runs with user shell privileges on PreToolUse / PostToolUse / SessionStart events
- Conventions for canvas writes, decision logs, and structured external memory that flow user-supplied content into subsequent skill prompts
- An audit trail (decision-log, corrections.md, cluster-instances) that downstream reviewers depend on for trustworthiness signals

## Reference frameworks

This threat model is structured against two canonical taxonomies:

- **OWASP Top 10 for LLM Applications 2025** (genai.owasp.org/llm-top-10/) — for LLM-only threats. LLM01/02/05/06 are the load-bearing four for an agentic developer-tool harness.
- **OWASP Agentic AI: Threats and Mitigations** (Feb 2025, genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) — for threats specific to agent loops with tool use, memory, and sub-agent dispatch. T1 (Memory Poisoning), T2 (Tool Misuse), and T15 (Human Manipulation) are the load-bearing three for Mycelium.

Where the two overlap, the Agentic catalog's framing dominates because Mycelium is structurally an agent harness, not an LLM application.

## The seven Mycelium-specific threats

| # | Threat | OWASP source | Defense status |
|---|---|---|---|
| **T-M1** | Memory Poisoning via PR-able files | OWASP Agentic T1 | NEW v0.23.6: SessionStart hook Check 7 surveillance (observability, not block) |
| **T-M2** | Indirect prompt injection via canvas/interview content | OWASP LLM01 + Anthropic 2026 | `<untrusted_user_content>` tag convention on 16 at-risk skills (folklore-grade alone, compounds with substrate-layer RL refusal) |
| **T-M3** | Secret leakage into canvas/memory | GitGuardian + VSCode 2025 incidents | Gap — tracked in `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` Tier 2 |
| **T-M4** | Hook tampering post-install | VSCode supply-chain 2025 | Gap — relies on Anthropic marketplace integrity; SHA-pinning is Tier 2 candidate |
| **T-M5** | Excessive agency via skill chaining / sub-agent escalation | OWASP LLM06 + Cursor CVE class | `/mycelium:fan-out` ships read-only canvas snapshot (structural mitigation, not formally named); capability manifest is Tier 2 candidate |
| **T-M6** | Audit-trail laundering (agent writes the log it audits) | OWASP Agentic + MCP token-passthrough anti-pattern | Append-only convention; cryptographic integrity in Tier 3 (architecturally sound, expensive) |
| **T-M7** | Marketplace-install trust (third-party clone) | PromptArmor "Hijacking Claude Code" | Outside Mycelium's surface; canonical marketplace identifier pinning is Tier 2 candidate |

### T-M1: Memory Poisoning via PR-able files

**Vector.** `corrections.md`, `patterns.md`, `cluster-instances.md`, `harness/decision-log.md` are all read on every session start per the Mandatory Pre-Task Protocol. They are also explicitly designed to accept external contribution: the receipts/contributors-as-recognition GTM mechanism (landscape.yml#strategic_frame) deliberately creates an inbound pathway for external content into memory. A malicious PR adding a poisoned correction with instruction-shaped content (imperative-mood verbs at the start of bullets) would survive code review (correction entries are prose; reviewers focus on whether the lesson is real, not whether the prose contains hidden instructions) and get loaded into agent context every session forever after.

**Defense (v0.23.6).** SessionStart hook Check 7 surveils recently-changed memory files for imperative-shaped bullet content (`Run`, `Execute`, `Delete`, `Send`, `Curl`, `Wget`, `Push`, `Force`, `Disable`, `Bypass`, `Skip`, `Ignore`, `Override`, `Fetch`, `Download`, `Install`, `Eval`, `Exec`). Surfaces a warning, not a block — false positives are expected (legitimate prevention prose looks imperative). The warning prompts the agent to verify the recent diff before treating the content as authoritative.

**What this does NOT cover.** Sophisticated injection that avoids imperative-mood verbs (e.g., descriptive prose that sets up a conditional the agent later interprets as instruction). Detection is conservative — designed for low FP at the cost of missed catches. Full coverage requires structured input validation at PR-merge time, which is outside the framework layer (it's a repo CI concern). Tracked as Tier 2 candidate.

### T-M2: Indirect prompt injection via canvas/interview content

**Vector.** Interview transcripts, scraped landscape research, support tickets, MCP tool outputs, and any other user-supplied text flow through the canvas into subsequent skill prompts. An attacker can plant instructions in any of these surfaces (hostile interview answer, poisoned web page Mycelium scrapes for landscape evidence, malicious MCP server response).

**Defense.** The `<untrusted_user_content>` tag wrapping convention (`harness/security-trust.md`, 16 at-risk skills audited 2026-05-03). Per Microsoft Research Spotlighting (arXiv 2403.14720), tag-wrapping alone is folklore-grade — but it compounds with Anthropic's substrate-layer RL-trained refusal of embedded instructions (anthropic.com/research/prompt-injection-defenses, ~1% attack success on Opus 4.5 for browser agents). The combined defense is materially better than either alone.

**What this does NOT cover.** Plugin output flowing back into the agent's loop (PostToolUse content), which is a different surface than canvas writes. The Lasso `claude-hooks` PostToolUse convention (github.com/lasso-security/claude-hooks) is the practitioner reference; documenting it as recommended user-side configuration is Tier 2.

### T-M3: Secret leakage into canvas/memory

**Vector.** User pastes `.env` content into an interview transcript → captured in canvas → committed to git → published in OSS dogfood. Or: a hook emits stdout containing `$AWS_SECRET_ACCESS_KEY` for debugging; the harness includes that in additional context. Or: a MCP tool returns rows containing a token column.

**Defense.** None at framework layer. Tracked as Tier 2 candidate (PreToolUse hook on canvas/memory writes scanning for high-entropy strings + .env-shaped patterns; gitleaks-style rules). Mature tools exist (TruffleHog, gitleaks, detect-secrets); GitGuardian shipped `ggshield`'s AI-hook in 2026-04 specifically for this product class.

### T-M4: Hook tampering post-install

**Vector.** `hooks/hooks.json` references shell scripts in the plugin tree. Plugin install pulls the marketplace tree into a cache; if that cache is mutated post-install (malicious dependency in another plugin escalating, local malware modifying the cache), hooks execute attacker code with user shell privileges on every event match.

**Defense.** Plugin install integrity relies on Anthropic marketplace verification (which verifies publisher domain, not code safety — same structural limit as VSCode "Verified Publisher" badges). Mycelium itself does not verify hook script integrity at invocation time. Tier 2 candidate: SHA-pinning hook scripts in `plugin.json` and verifying expected SHAs in `framework-guard.sh` would be ahead of every peer plugin.

### T-M5: Excessive agency via skill chaining / sub-agent escalation

**Vector.** A skill invocation that spawns sub-agents via `/mycelium:fan-out`. A compromised sub-agent (memory-poisoned, prompt-injected, or simply hallucinating with confidence) returns crafted output that re-injects the parent. This is OWASP Agentic's sub-agent escalation pattern.

**Defense.** `/mycelium:fan-out` ships read-only canvas snapshots to sub-agents and accepts only summarized return values. Each sub-agent gets a clean attention budget (per `harness/context-management.md`); the parent receives compressed result, not full reasoning trace. **However, this defense is structural, not enforced** — a compromised sub-agent can still return a value that the parent incorporates without verification. The 2026-05-11 BDSK-fabrication instance (corrections.md entry, anti-pattern #7 sub-class `subagent-output-verification`) is a worked example of this exact failure mode firing on a benign sub-agent. Capability manifest (Tier 2 candidate, Synaptiai's angle) would let `framework-guard.sh` validate intent vs. declared scope.

### T-M6: Audit-trail laundering

**Vector.** The agent writes the decision-log it audits. If the agent itself is compromised (memory-poisoned via T-M1, prompt-injected via T-M2), the audit trail launders the compromise — entries appear consistent and provenance fields look populated, but the underlying decisions don't reflect what actually happened. MCP's "token passthrough" pattern is the canonical name for this anti-pattern.

**Defense.** Append-only convention (decision-log.md is treated as growing file; entries are not edited). Cluster-instances.md provides cross-reference for recurring patterns, partly mitigating single-entry compromise. Cryptographic integrity (HMAC-chained entries) is architecturally sound but expensive — Tier 3 (deferred until evidence audit-trail laundering happens in dogfood).

### T-M7: Marketplace-install trust

**Vector.** A third-party Claude Code marketplace can ship a malicious "mycelium" clone with the same skill names. PromptArmor's "Hijacking Claude Code via Injected Marketplace Plugins" is the published attack write-up.

**Defense.** Outside Mycelium's surface — this is Anthropic's marketplace verification responsibility. Mycelium can request the canonical marketplace identifier (`haabe-mycelium`) be pinned in any official documentation referencing the plugin, which Tier 2 tracks.

## Defense layers (summary)

1. **Substrate (Anthropic / Claude / Claude Code)**: model-level prompt-injection defenses, sandbox model, marketplace verification, hook trust model. Mycelium inherits these; cannot extend or override.
2. **Framework (Mycelium plugin)**: tag wrapping convention, framework-guard hook, SessionStart memory-poisoning surveillance (v0.23.6), per-graduation attribution discipline (v0.23.5), externalize-everything to canvas + decision-log.
3. **Project state (user's `.claude/`)**: corrections.md / patterns.md / cluster-instances.md / decision-log.md — user-owned, PR-reviewable, version-controlled.
4. **User behavior**: pre-ship gap analysis (G-P-pre), devil's advocate (Technique 4 attribution-labeling), `/mycelium:security-review` + `/mycelium:threat-model` + `/mycelium:privacy-check` skills.

The framework layer's job is to make defense layer 3 (project state) and defense layer 4 (user behavior) easier to do well than to do poorly. The discipline shipped 2026-05-09 (anti-pattern #7 + Validator Check 31), 2026-05-10 (per-graduation attribution + Work-Mode Mix), and 2026-05-11 (memory-poisoning surveillance + this threat model) are progressively harder structural surfaces around the same epistemic shape: attribution discipline at every boundary where evidence flows.

## What this threat model does NOT cover

- **Sandbox escape**: Mycelium is not a sandbox. If you need code-execution isolation, that's the host (Claude Code) layer or OpenHands-class sandbox (Docker + cap-drop ALL).
- **Network egress controls**: not Mycelium's surface. Use host-agent enterprise controls.
- **Cryptographic plugin signing**: Anthropic marketplace responsibility. Mycelium can request, can't implement.
- **MCP server vetting**: Mycelium does not currently ship MCP servers. If it adds them, this section needs to grow.
- **Model alignment / training-time risk**: Anthropic's responsibility.

For comprehensive AI Act / GDPR / regulatory awareness, see `plugins/mycelium/harness/security-trust.md` § Regulatory Awareness.

## Related artifacts

- `plugins/mycelium/harness/security-trust.md` — per-stage security controls (L0 → L5), prompt-injection defense convention, EU AI Act regulatory awareness, secrets management, dependency security
- `plugins/mycelium/harness/anti-patterns.md` — security cluster (8 entries) + cognitive/drift cluster (Cognitive Offloading Loop, Knowledge Reconstruction Tax, Eval Overfitting, Negative Documentation)
- `plugins/mycelium/harness/context-management.md` — context-rot defense layer (sister to this doc; together they cover the substrate-layer concerns the framework structurally addresses)
- `docs/ai-system-card.md` — transparency / accountability / recourse path
- `mycelium-roadmap/.claude/drafts/security-strengthening-followups.md` — Tier 1/2/3 candidates with attribution labels and trigger conditions (canonical backlog for security work)

## Source citations

- **OWASP Top 10 for LLM Applications 2025** — genai.owasp.org/llm-top-10/
- **OWASP Agentic AI Threats and Mitigations** (Feb 2025) — genai.owasp.org/resource/agentic-ai-threats-and-mitigations/
- **OWASP Top 10 for Agentic Applications 2026** — genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- **MCP Security Best Practices** — modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices
- **Anthropic Prompt-Injection Defenses** (Feb 2026) — anthropic.com/research/prompt-injection-defenses
- **Microsoft Research Spotlighting** (arXiv 2403.14720) — three techniques: delimiting / datamarking / encoding
- **PromptArmor: Hijacking Claude Code via Marketplace Plugins** — promptarmor.com/resources/hijacking-claude-code-via-injected-marketplace-plugins
- **Lasso `claude-hooks`** (PostToolUse prompt-injection defense reference) — github.com/lasso-security/claude-hooks
- **GitGuardian `ggshield` AI-hook** — helpnetsecurity.com/2026/04/15/product-showcase-gitguardian-ggshield-ai-hook
- **Wiz: VSCode marketplace supply chain risk** (550+ leaked secrets) — wiz.io/blog/supply-chain-risk-in-vscode-extension-marketplaces
- **The Vulnerable MCP Project** (running CVE list) — vulnerablemcp.info

## Honest caveats

- Tag-wrapping `<untrusted_user_content>` alone is folklore-grade; works only when paired with substrate-layer training (which Anthropic ships).
- Memory-poisoning surveillance (v0.23.6 Check 7) is observability, not enforcement — designed for low false-positive rate at the cost of missed catches.
- Anti-pattern #7 fires across multiple sub-classes (canvas-write / graduation-velocity / subagent-output-verification); each new sub-class to date has been caught only after firing, not preceded by structural prevention. Documentation alone has been insufficient at every surface.
- This document itself is `research-while-here` graduation per the v0.23.5 attribution discipline. Connection to lived-friction: medium (today's BDSK-fabrication anti-pattern #7 instance is the lived-friction trigger for the consolidated threat model + the memory-poisoning hook).
