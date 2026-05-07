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
- **provenance singular/plural mismatch**: `_common.schema.json` accepted only `source_classes` (plural array) inside provenance, but framework convention uses singular `source_class` everywhere else. Writers (especially `/interview`) reached for the singular form and got rejected. Schema now accepts both + `notes`.
- **Canvas Write trips Claude Code's read-before-write check**: Canvas files ship pre-populated as templates, so they exist on every fresh project. `Write` tool requires prior `Read` (same tool); `cat` via Bash doesn't count. Every canvas-writing skill (/interview, /canvas-update, /log-evidence, etc.) hit this. Documented in CLAUDE.md "Canvas writes — Read before Write."
- **Wayfinding map improvised against spec**: Agent rendered `You Are Here — Wayfinding Map` with vertical box-drawing characters instead of `YOUR JOURNEY` template with horizontal phase progression. Doc was descriptive, not prescriptive. Tightened wayfinding.md with explicit "STRICT — reproduce the template literally" + a list of common deviations.
- **`/diamond-progress` re-invocation interpreted as approval**: when a previous `/diamond-progress` left the diamond in pending-approval state, typing `/diamond-progress` again was silently treated as "yes, advance" rather than as a fresh evaluation request. Implicit behavior nowhere in SKILL.md. Surfaced during Juniors.dev pre-run dogfood (2026-05-06).
- **`/diamond-progress` is phase-transition-shaped, not child-spawn-aware**: skill assumes "current phase → next phase" and treats spawning a child diamond as a side-effect bullet under step 9. Real spawn operations need first-class workflow handling — perspective-conflict check on parent's canvases, parent-confidence-vs-effective-threshold check, child-confidence initialization rules, dual-state output (parent + child). Surfaced 2026-05-07 spawning L1 from L0 in dogfood.

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

### 2026-05-07 - `/diamond-progress` is phase-transition-shaped, treats child-spawn as side-effect
- **Scope**: orchestration
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: Spawning L1 Strategy from L0 Develop on 2026-05-07 surfaced that `/diamond-progress` SKILL.md is structured around phase transitions (step 1: "From [current phase] to [next phase] at [scale]"). Child-diamond spawning is mentioned only as a single-line bullet under step 9 ("If progressing: ... Identify if child diamonds should be spawned"). The full apparatus (cognitive forcing, perspective conflict check, gate evaluation, confidence threshold, counter-argument, mutation) is phase-transition-coded. When the actual operation is "L0 stays in Develop, spawn L1 in Discover," the agent has to interpret-around-the-skill-text rather than follow it. Several specifically-spawn-shaped checks aren't run because they're not specified: (a) is the parent's effective threshold met for spawn (not for parent completion)? (b) what initial confidence should the child have, and is there a rule connecting it to parent confidence? (c) which canvas files transfer/inherit vs. which are owned by the child scale? (d) how does the trio perspective coverage carry forward from parent to child? In dogfood mode the agent improvised reasonable answers; in less self-documenting projects this would create silent variance across spawn operations.
- **Correction**: Add a Step 1.5 "Identify operation type" to `/diamond-progress` SKILL.md that branches on transition (existing flow) vs. spawn (new flow) vs. pivot/park/kill (existing subcommand flow). Spawn flow needs: (1) perspective-conflict check on PARENT's canvases (already correct as-is), (2) explicit parent-readiness gate ("is parent at-or-above effective threshold AND are there strategic events warranting a child?" — see patterns.md "Spawn child diamonds at strategic-events density"), (3) child-initialization rules (which gates go pending per scale, what initial confidence to use, which canvas files to reference), (4) dual-state mutation (update parent's last_progressed + notes + spawned-child reference; create child entry with parent_id), (5) updated wayfinding showing both parent and child active.
- **Prevention**: Skills that handle multiple operation shapes should branch on operation-type at step 1, not bury alternate operations as bullets under "if progressing." Anti-pattern shape: skill text optimized for the most-common case treats the rarer-but-equally-real cases as exceptional rather than first-class. If a third instance of "skill structured around dominant case, alternate cases handled implicitly" surfaces, graduate to a meta-rule: skills with multiple operation modes must declare them explicitly at step 1.
- **Source**: Self-detected during 2026-05-07 L1 spawn in dogfood. Theory: Norman (visible affordances — alternate operations need visible structure, not implicit interpretation). Lopopolo (every interaction is a failure of the harness to provide enough context — when the agent has to infer the workflow from skill structure, the harness has under-served it).

### 2026-05-06 - `/diamond-progress` silently interprets re-invocation as approval
- **Scope**: orchestration
- **Category**: communication
- **Origin**: ai-generated
- **Mistake**: During Juniors.dev pre-run dogfood, the user ran `/diamond-progress` to evaluate L0 Discover→Define. Gates passed-with-caveats; the agent paused and asked for explicit human approval before mutating state ("Pending your explicit approval: progress L0 Purpose from Discover → Define?"). The user re-invoked `/diamond-progress` rather than typing "yes." The agent interpreted the re-invocation as approval and advanced the diamond, rendering `"Reading your re-invocation as approval — executing the progression now."` on screen. The user expected a fresh gate evaluation. The behavior is reasonable as a UX shortcut but is documented nowhere in `skills/diamond-progress/SKILL.md` — neither in the workflow steps, the human-approval section, nor a "shortcuts and conventions" subsection. Implicit harness behavior is a footgun: in this case it cost the user one round of confused re-running before the next `/diamond-progress` invocation finally produced the Define→Develop refusal moment.
- **Correction**: At minimum, document the convention in `skills/diamond-progress/SKILL.md` step 4 (human approval): "If the user re-invokes `/diamond-progress` while a previous invocation is awaiting approval, that re-invocation is treated as approval. To force a fresh evaluation instead, the user should type `evaluate again` or modify state and then re-invoke." Better: add a line to the agent's pending-approval prompt that names the convention explicitly ("Reply 'yes' to advance, 'no' to stay, or re-invoke `/diamond-progress` to approve. Type 'evaluate again' to re-run gates."). The mechanism is fine; surfacing it removes the footgun.
- **Prevention**: Audit other skills with deferred-action patterns for similar implicit conventions. `/diamond-progress pivot|park|kill` subcommands and `/preflight` are the most likely candidates. If a second instance of "implicit interaction convention" surfaces, graduate to a meta-rule: skills with multi-turn workflows must document interaction conventions in the prompt that asks for them, not in the skill text.
- **Source**: Detected during 2026-05-07 Juniors.dev presentation pre-run. Theory: Norman (Design of Everyday Things — affordances must be visible, not implicit). Lopopolo (every interaction is a failure of the harness to provide enough context).

### 2026-05-06 - Wayfinding map: agent improvised layout against template
- **Scope**: discovery
- **Category**: communication
- **Origin**: ai-generated
- **Mistake**: After `/interview` populated the canvas, the agent rendered the post-interview wayfinding map as a vertical tree (`L0 Purpose ●──┐ │ L1 Strategy ○─┤ │ ...`) with title `You Are Here — Wayfinding Map`, `●` symbol, no phase progression, and inline confidence on the active line (`← YOU ARE HERE (Discover, confidence 0.3, anecdotal)`). The wayfinding.md spec called for a different layout: title `YOUR JOURNEY`, horizontal phase progression (`Discover ✓ → Define → Develop → Deliver`), `◆` for active, plain-language description per scale, footer with confidence + next-action. Root cause: wayfinding.md described the rendering rules and showed a template, but didn't forbid alternative layouts. The agent had latitude to "interpret" and used it.
- **Correction**: Tightened `engine/wayfinding.md` with a "STRICT — reproduce the template literally" header at the top of "How to Render," plus a list of common improvisations to forbid (vertical box-drawing, `●` instead of `◆`, inline confidence, missing descriptions, alternate titles). Same template, but no room to redesign.
- **Prevention**: When a doc is descriptive but the agent has visual latitude, expect it to improvise. For rendering specs, lead with "reproduce verbatim, do not redesign" and enumerate common deviations. If this recurs (≥3 instances of layout-improvisation across other rendering docs), graduate to a meta-pattern: "rendering specs must be prescriptive, not descriptive."
- **Source**: Detected during 2026-05-07 Juniors.dev presentation pre-run dogfood. Theory: NNGroup (You-Are-Here pattern depends on consistency for orientation; improvised layouts defeat the purpose). Lopopolo (the harness must remove latitude where consistency matters).

### 2026-05-06 - Canvas Write fails on fresh projects — read-before-write tool quirk
- **Scope**: orchestration
- **Category**: process
- **Origin**: ai-generated
- **Mistake**: During Juniors.dev presentation pre-run, a fresh `npx degit haabe/mycelium test-demo1` followed by `/interview` failed at the canvas-write step with "Error writing file" on `purpose.yml` and `jobs-to-be-done.yml`. Reproduced reliably on a second fresh project. Root cause: canvas files ship pre-populated as templates (header comments + placeholder fields), so every `.claude/canvas/*.yml` already exists on a fresh project. Claude Code's `Write` tool requires a prior `Read` (same tool, same session) on existing files; `cat` via Bash does NOT satisfy the check. The agent had `cat`-ed the file during interview synthesis but never invoked the Read tool, so Write was rejected. No skill in the framework instructed the agent to use Read before Write on canvas files — a structural assumption baked into Mycelium's tooling that wasn't surfaced.
- **Correction**: Added a "Canvas writes — Read before Write" paragraph to `CLAUDE.md` under "The Canvas (Source of Truth)." Spells out the tool-quirk explicitly, names the affected skills (every canvas-writing skill), and tells the agent to use the Read tool before Write. Edit also requires prior Read but is the right tool for partial updates.
- **Prevention**: Future skills that populate canvas files inherit this guidance from CLAUDE.md without per-skill duplication. If this recurs as a per-skill failure (≥3 instances), graduate to a PreToolUse hook on `.claude/canvas/*.yml` that injects "use Read tool first" into the deny reason — converts the quirk into a self-explaining harness rule.
- **Source**: Detected during 2026-05-07 Juniors.dev presentation pre-run dogfood. Theory: Lopopolo ("every interaction is a failure of the harness to provide enough context") — the agent's behavior was correct given the context it had; the harness was missing the tool-quirk context. Brooks (No Silver Bullet — accidental complexity from tool quirks should be absorbed by the harness, not pushed to the user).

### 2026-05-06 - provenance schema rejected the framework's own canonical evidence vocabulary
- **Scope**: quality
- **Category**: engineering
- **Origin**: ai-generated
- **Mistake**: During pre-run dogfooding for the 2026-05-07 Juniors.dev presentation, `/interview` populated `jobs-to-be-done.yml` and `opportunities.yml`. Validation failed three times with `Additional properties are not allowed ('source_class' was unexpected)` and `('notes' was unexpected)` inside `provenance` blocks. Root cause: the framework convention uses singular `source_class` at the top level of every evidence entry across `purpose.yml`, `landscape.yml`, `metrics-pull` snapshots, and 5+ skills — the agent generalized that convention into provenance blocks. But the provenance sub-schema (`_common.schema.json#/$defs/provenance`) accepted only `source_classes` (plural array) and had `additionalProperties: false`. Same concept, two field names depending on schema depth — a structural footgun. The agent also reached for `notes` as a natural free-text field; schema rejected it without offering a sanctioned alternative.
- **Correction**: Schema now accepts singular `source_class` (single enum value, applying to all `evidence_sources`) AND `notes` (optional free-text string) inside provenance, alongside the existing plural `source_classes`. Strict mode preserved for everything else — typos still caught. If both `source_class` and `source_classes` are present, `source_classes` (per-source) takes precedence.
- **Prevention**: When `additionalProperties: false` is used, audit whether the rejected fields are typos or natural-feeling fields the rest of the framework conventions point toward. If the latter, accept them rather than fight the convention. Sister pattern to "documented rule diverges from enforcement" (5th-instance graduation Check 26, 2026-05-04) — same shape: schema layer disagrees with the convention the rest of the framework teaches.
- **Source**: Self-detected during dogfood pre-run for Juniors.dev presentation. Theory: DRY (one canonical name per concept across schema depths), POLA (Principle of Least Astonishment — Saltzer & Schroeder; what the rest of the framework teaches should also work in narrower scopes).

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

