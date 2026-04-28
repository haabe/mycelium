# Corrections Log

*Mycelium's friction log (Hoskins, Ch4). A record of experience, not prescriptions. Read before every task — past mistakes are expensive lessons.*

## TL;DR

- **L5 sycophancy**: At market scale, agent uses promotional language in decision logs. Guardrail G-M1 added.
- **Decision log skipped**: 27/44 skills had no decision log instruction. G-P4 strengthened, 10 skills patched, evaluator expanded.
- **python vs python3**: macOS has `python3` not `python`. Use `python3` in all commands.
- **upgrade.sh must be glob-driven, not list-driven**: Hardcoded file lists drift when new files are added. Use globs with explicit preserve-lists.

## Format

Each correction entry follows this structure:

```
### [DATE] - [SHORT TITLE]
- **Scope**: [discovery | delivery | orchestration | quality]
- **Category**: [bias | security | engineering | process | communication]
- **Origin**: [ai-generated | human-written | ai-assisted | unknown]
- **Mistake**: What went wrong.
- **Correction**: What should have happened instead.
- **Prevention**: How to prevent this in the future (checklist item, gate, etc.).
- **Source**: Theory or principle that applies (e.g., "Torres - continuous discovery", "OWASP - input validation").
```

**Origin field (APEX alignment)**: Track whether the mistake was in AI-generated, human-written, or AI-assisted code. Over time this reveals whether AI code has different quality patterns than human code. If AI-origin corrections dominate, it signals the AI needs better context (sharper canvas, updated corrections.md, more specific instructions). See APEX framework in `canvas/dora-metrics.yml`.

## Generalizable Corrections

_Corrections that apply broadly across projects and contexts._

### 2026-04-20 - L5 market scale produces sycophantic decision log entries
- **Scope**: quality
- **Category**: bias
- **Origin**: ai-generated
- **Mistake**: At L5 Market scale, the agent wrote overly optimistic phrases ("mostly positive", "strong validation", "confirms product-market fit") in the decision log. The go-to-market context primes promotional framing that bleeds into internal records.
- **Correction**: Decision log language must remain evidence-specific and hedged. "3 of 5 users mentioned X" not "strong validation from users."
- **Prevention**: Added guardrail G-M1 to `guardrails-market.md`. The `decision_log_honest` evaluator criterion catches forbidden phrases. Agent should use specific counts and hedged language at all scales, but especially L5.
- **Source**: Kahneman (optimism bias), Shotton (social proof bias). Detected by dogfood scenario `content-solo-l5-market`.

### 2026-04-20 - 27 of 44 skills had no decision log instruction
- **Scope**: process
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: Core guardrail G-P4 says "always log decisions" but 27 skills never mentioned the decision log. The agent sometimes skipped writing it, requiring evaluator retries (observed in 3 of 18 dogfood scenarios: `service-team-multiscale-l2-l4`, `saas-solo-l1-strategy`, `content-solo-l5-market`).
- **Correction**: Strengthened G-P4 with explicit skill list. Added `## Decision Log (MANDATORY per G-P4)` section to 10 high-impact skills (`team-shape`, `wardley-map`, `cynefin-classify`, `launch-tier`, `service-check`, `bias-check`, `privacy-check`, `security-review`, `bvssh-check`). Expanded evaluator `require_after` set from 2 to 14 skills.
- **Prevention**: When creating new skills, always include a decision log section. G-P4 now lists skills explicitly rather than relying on "significant decisions."
- **Source**: Dogfood finding F2. Argyris (double-loop learning — the instruction was present but not specific enough to change behavior).



### 2026-04-28 - upgrade.sh harness sync was hardcoded, not manifest-driven
- **Scope**: delivery
- **Category**: engineering
- **Origin**: ai-generated
- **Mistake**: upgrade.sh hardcoded 6 harness filenames for sync. When new harness files were added (guardrails-core.md, guardrails-delivery.md, guardrails-discovery.md, guardrails-index.md, guardrails-market.md, README.md), they were never added to the hardcoded list or the manifest. The `tests/` and `auto-dogfood/` directories were also in the manifest but missing from the directory loop. Result: downstream projects silently drifted from upstream over upgrades.
- **Correction**: (1) Replaced hardcoded harness list with glob + explicit preserve-list. (2) Added missing directories to framework replace loop. (3) Added README sync step for preserved directories. (4) Updated manifest.yml.
- **Prevention**: When adding new framework files, verify upgrade.sh coverage. The harness glob pattern now handles new files automatically — no list to maintain. For new preserved-directory READMEs, add to manifest `preserved_dir_readmes`.
- **Source**: DRY (hardcoded lists diverge from reality). Forsgren (change failure rate — silent drift is a deployment risk).

## Situational Corrections

_Corrections specific to a particular project, team, or context._

