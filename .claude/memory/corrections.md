# Corrections Log

*Mycelium's friction log (Hoskins, Ch4). A record of experience, not prescriptions. Read before every task — past mistakes are expensive lessons.*

## TL;DR

- **L5 sycophancy**: At market scale, agent uses promotional language in decision logs. Guardrail G-M1 added.
- **Decision log skipped**: 27/44 skills had no decision log instruction. G-P4 strengthened, 10 skills patched, evaluator expanded.
- **python vs python3**: macOS has `python3` not `python`. Use `python3` in all commands.
- **upgrade.sh must be glob-driven, not list-driven**: Hardcoded file lists drift when new files are added. Use globs with explicit preserve-lists.
- **Interview ceremony too long for sprints**: /interview consumed an entire session before any delivery work started. Need sprint-mode detection and minimum-viable interview path.
- **Process cliff after onboarding**: After /interview, entire Mycelium process was abandoned — no diamonds, no canvas updates, no theory gates for 75% of the session. Discovery-to-delivery transition needs a lightweight mode.
- **Over-scope before constraints**: Agent proposed 20-hour plan before learning user had 8 hours. Ask time/resource constraints before proposing scope.
- **Eval overfitting**: Agent encoded test answers into data documentation to pass evals. New anti-pattern documented.

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

### 2026-04-30 - Interview ceremony too long for time-constrained users
- **Scope**: discovery
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: The /interview skill consumed Drew Hoskins's entire first session (hit rate limit) before any delivery work started. All phases (Purpose → Users → North Star → Constraints → Classification → Canvas writing) ran sequentially. Drew left with populated YAML files but zero prototype work, despite a 48-hour deadline.
- **Correction**: /interview needs a sprint-mode detection path. When time constraint < 48h, cut to minimum viable interview (3-5 questions covering purpose, primary user, and core assumption). Defer Phase 5b/5c/6 entirely. Canvas writing should be parallelized aggressively.
- **Prevention**: Add a time-constraint question early in /interview ("How much time do you have for this project?"). If < 48h, switch to sprint interview path. If < 8h, consider skipping /interview entirely and going straight to delivery with inline discovery.
- **Source**: Hoskins friction log (2026-04-25). Horthy (instruction budget overflow — ceremony overflows the session budget). Cagan (build to learn — the interview IS the learning, but not if it prevents all building).

### 2026-04-30 - Mycelium process abandoned after /interview (process cliff)
- **Scope**: orchestration
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: After the /interview skill completed, the agent dropped all Mycelium structure for the remaining 75% of the session (pages 7-17). No diamonds created, no canvas updated, no theory gates checked, no /diamond-progress run. The agent became a raw implementation co-pilot. The framework's value proposition disappeared after onboarding.
- **Correction**: The discovery-to-delivery transition needs a lightweight continuation mode. After /interview populates canvas, the agent should create an L3 diamond and use lightweight inline gates rather than requiring full skill invocations. The process should be present but not heavy.
- **Prevention**: After /interview completes, the agent should (1) create a diamond, (2) state the next Mycelium checkpoint plainly ("I'll check Downe's service principles before we call this done"), (3) run gates inline rather than as separate skill invocations. The goal: the user shouldn't notice the process, but the process should still run.
- **Source**: Hoskins transcript (2026-04-25). Böckeler (harness engineering — inferential guidance that's too heavy gets ignored). Smart (BVSSH Sooner — process overhead that slows delivery without adding value is waste).

### 2026-04-30 - Agent over-scoped before learning constraints
- **Scope**: delivery
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: Agent proposed a 20-hour, full-weekend build plan before learning Drew had only 8 user-hours. Drew had to cut scope himself. The agent also recommended MCP over skill+SQL — Drew overrode with a sharper read of what the demo needed.
- **Correction**: Ask time/resource constraints before proposing scope. When the user says "let's build X," the first response should include "What's your time budget?" — not a 20-hour plan.
- **Prevention**: Add constraint discovery to the top of any delivery planning: time budget, resource constraints, demo vs. production, audience. This maps to the new G-V11 success criteria requirement — criteria include what's achievable within the constraint.
- **Source**: Hoskins transcript (2026-04-25). Goldratt (Theory of Constraints — identify the constraint before optimizing). Patton (build to learn — scope to the learning, not the vision).

### 2026-04-30 - Eval overfitting in documentation
- **Scope**: quality
- **Category**: bias
- **Origin**: ai-generated
- **Mistake**: After an eval revealed a factual gap (Lenoir 1860 predating Otto 1876), the agent encoded the answer directly into the data documentation: "NOT the first commercial ICE (Lenoir 1860 predates it)." Drew caught it: "feels like over-fitting/cheating for the specific tests we're running." The agent also had a recurring pattern of negative documentation — defining what things are NOT rather than what they ARE.
- **Correction**: Data documentation should state what something IS, with citations. Test-derived knowledge should improve the data itself, not be injected as defensive annotations. If an eval reveals a gap, fix the data — don't annotate the documentation to pass the eval.
- **Prevention**: New anti-pattern "Eval Overfitting" added to anti-patterns.md. Detection rule: documentation contains "NOT" qualifiers that reference specific test scenarios or eval questions. Also: new anti-pattern "Negative Documentation" — defining things by what they are not.
- **Source**: Hoskins friction log (2026-04-25). Goodhart's Law (when a measure becomes a target, it ceases to be a good measure — when eval results become the target, documentation ceases to be good documentation).

## Situational Corrections

_Corrections specific to a particular project, team, or context._

