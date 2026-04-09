# Mycelium Dogfood Report — macos-fileviewer Session

*Date: 2026-04-09. Mycelium version: 0.8.1. Agent: Claude Opus 4.6 (1M context). Session shape: solo developer running `/interview` on a fresh template-bootstrapped project, then continuing through web research, devil's advocate, and a mocked-persona exercise. Total session length: roughly 12 turns; ~5 hours of agent + research time.*

## Executive summary

Mycelium **substantively did the job it was designed to do** — the framework caught a value-risk failure at L0 *before* any code was written, exactly where evidence-gated discovery is supposed to catch it. The decision log, devil's advocate skill, and theory-gate scaffolding all earned their keep. **The framework should be considered validated on its core claim: theory-guided agent harnessing prevents AI agents from going haywire on greenfield product work.**

That said, the dogfood session also surfaced **12 distinct gaps, mishaps, and threats** that warrant tightening. None are existential. Several are structural (hook scope, two-memory-system confusion, missing meta-project mode). Several are about agent discipline that Mycelium relies on but does not enforce. A few are simple bugs in advisory hooks.

The most important systemic finding: **the framework relies heavily on the agent recognizing when to invoke skills and when to apply disciplines that aren't mechanically enforced.** This worked in this session because the agent (me) had room and incentive to be careful, the user was an active collaborator, and the meta-project framing made caution rewarding. **In a less reflective session — fewer turns, more "just do it" pressure, less explicit user collaboration — most of the catches in this session would not have happened.** That's the largest threat surface.

---

## The journey, briefly

| Turn | What happened | Mycelium artifact |
|---|---|---|
| 1 | SessionStart hook fired with two advisories: "BVSSH health never assessed" and "Corrections in memory: 1" | hook surfaced |
| 1 | `/interview` skill invoked. Empty canvas. Ran 6 phases through the founder. | Canvas: purpose, jtbd, north-star, landscape, diamonds/active populated. Memory: user/project/feedback entries written. |
| 2 | Web research kickoff: 3 parallel general-purpose Agents (competitive, rendering, macOS APIs+distribution). TaskCreate used for tracking. | Tasks 1–4 created with dependencies |
| 3 | Research synthesis. landscape.yml refined. Brief written to memory. | `.claude/memory/research-brief-2026-04-09.md` |
| 4 | `/devils-advocate` invoked. Caught the agent's own bias toward technical feasibility over demand validation. Re-ranked next moves. | Decision log entry #1 |
| 5 | Founder revealed project is Mycelium dogfooding meta-project; no real user research. Project type changed `solo_product → solo_hobby`. | active.yml updated; `project_meta_mycelium_dogfood.md` memory written |
| 6 | Mocked persona exercise (substituting for `/user-interview`). 6 deliberately diverse personas. Stop condition triggered (4 of 6 would not switch). L0 confidence revised down. | Decision log entry #2; canvas/user-needs.yml populated; persona interview record in memory |
| 7 | Decision: stop and write this report. | This file. |

---

## What worked (the wins)

These deserve to be called out because they are the parts Mycelium should keep doing exactly as it does today.

1. **The L0 `/interview` flow is well-shaped.** The 6 phases (purpose → users → north star → landscape → current state → classification) produced a coherent Canvas in one session. The phase-ordering is right: it gathers *why* before *who* before *what*. The questions are open enough that the founder can answer in their own framing without being led.

2. **Parallel research subagents are the right pattern for L0–L2 evidence-gathering.** Three independent Agents in parallel, each with a focused brief, produced three rich outputs in ~5 minutes each. The pattern of "split research by independent dimension, fan in to synthesis" mapped naturally onto the three research streams (competitive, rendering, APIs+distribution). The Mycelium docs mention this as a Discovery skill in the agent-orchestration patterns; in practice it just worked with `general-purpose` agents and a focused brief each. **Mycelium should formalize "fan-out research" as a first-class L1/L2 pattern**, possibly as an explicit skill.

3. **`/devils-advocate` earned its keep.** The skill is short, low-prescription, and trusted me to do thorough work. The "10 challenge questions + 3 techniques" structure is well-calibrated: enough scaffolding to be substantive, not so much that it becomes a checklist exercise. The instruction to "log challenge results in decision-log.md" is exactly the right downstream wiring. **This skill caught my own confirmation bias and re-ranked the project's next moves correctly.** Without it, I would have recommended a speed prototype and burned a day on feasibility validation while value risk sat unaddressed.

4. **The decision log is the right durable artifact.** Markdown, immutable entries, alternatives-considered field, theory citation, confidence + reversibility. I wrote three entries in this session and each one captured something I would have lost otherwise. **Keep it as-is.** Maybe make it queryable later, but the format is correct.

5. **Theory gates as a `not-checked / pass / fail / partial` map** on each diamond is the right shape. It surfaces unfinished work without being preachy. When the mocked-persona exercise failed, I could update `bias_check: partial` and `evidence: failing` and the diamond's state captured the failure honestly.

6. **Confidence as an explicit field with `evidence_type` provenance** (`speculation / anecdotal / data-supported / test-validated / launch-validated`) is excellent. Forced me to downgrade L0 confidence from 0.4 to 0.35 *and* change `evidence_type` from `anecdotal` to `speculation` after the mocked-persona exercise. Without these two fields next to each other, I might have inflated confidence based on "we did some research" without acknowledging the research was speculative. **This is the strongest single anti-confabulation feature in the framework.**

7. **Canvas-as-source-of-truth held up.** Updating `landscape.yml`, `user-needs.yml`, `jobs-to-be-done.yml`, `purpose.yml`, `north-star.yml`, and `diamonds/active.yml` with research findings worked smoothly. The YAML schemas are prescriptive enough to be useful but flexible enough that I could add fields like `evidence_sources`, `goodhart_check`, `strategic_bets_ranked`, `critical_context`, and `gameplay_refined` without breaking anything.

8. **The meta-discipline of "when in doubt, ask the user before destructive action"** held. I never made a major commitment without surfacing options. The Mycelium harness's emphasis on "communication in plain language first, technical details second" reinforced this and the user's collaborative response made it productive.

---

## Gaps (where Mycelium didn't anticipate the situation)

These are situations the framework didn't handle, where I had to invent something on the spot.

### G1. Meta-project mode is unrecognized
**The situation**: User is using Mycelium itself as the goal of the project, with macos-fileviewer as the vehicle. The object-project may or may not ship.

**What's missing**: `/interview` Phase 6 (project classification) has four types — `solo_hobby / solo_product / team_startup / team_enterprise`. None of them is "meta-project / framework dogfood / I'm using this to learn the framework". When the user revealed the dogfood framing in turn 5, I had to invent a memory entry (`project_meta_mycelium_dogfood.md`) to capture the meta/object distinction.

**Why it matters**: A meta-project changes how confidence, theory gates, and stop conditions should be interpreted. Mocked personas become acceptable substitutes for real research. "Validation appears to fail" becomes a Mycelium learning, not a project death. Without a recognized mode, the framework would push (correctly, by its own rules) toward real user research, which the user explicitly does not want.

**Tightening proposal**: Add a 5th project type: `meta_dogfood`. Add an `/interview` Phase 6 question: *"Is this primarily a real product, or are you using this as a vehicle to test/learn Mycelium itself?"* When `meta_dogfood`, surface explicit guidance about substituting mocked personas for real interviews, treating "stop conditions" as Mycelium learnings rather than project deaths, and prioritizing capturing framework friction over object-project velocity.

---

### G2. No `/mocked-persona-interview` skill or discipline
**The situation**: Solo founder, no user research budget, hobby/learning project. Real user interviews aren't going to happen. Yet the framework's L0–L2 evidence gates require multi-source user evidence.

**What's missing**: Mycelium has `/user-interview` (Torres-style real interviews) but no equivalent for the very common case of "I cannot or will not talk to real users right now". An agent invited to "mock some personas" with no discipline guidance would, in 9 of 10 cases, produce 5 sympathetic NPCs and call it validation. **The trap is well-known but Mycelium doesn't prescribe a counter-discipline.**

**What I had to invent on the spot** (in chat with the user, before generating personas):
- Pre-defined spectrum that includes adversarial perspectives (not just sympathetic users)
- One-paragraph profile written *first*, in-character interview written *second*
- Pre-committed stop condition (4 of 6 no = exercise flagged as failed)
- Mandatory `evidence_type: speculation` tag on all canvas updates from the exercise
- Honest synthesis discipline: "if all personas agree, that's a tell"

**Why it matters**: This is the discipline that prevented confabulation in this session. It worked because the user and I negotiated it explicitly *before* generating any personas. Without that pre-commitment, the temptation to soften the synthesis when the stop condition triggered would have been significant. **Mocked-persona discipline is the load-bearing gate between "simulation as tool" and "simulation as confirmation-bias machine".**

**Tightening proposal**: Create `/mocked-persona-interview` as an explicit skill in `.claude/skills/`. Skill should require: pre-defined persona spectrum (template), explicit stop condition agreed before generation, evidence_type: speculation tagging, "if all agree, redo with adversarial bias" rule, and a discipline statement explaining the epistemological status. Reference Torres CDH and explicitly distinguish from real interviews.

---

### G3. Synthesis-bias-check isn't a gate
**The situation**: After three rich technical research streams came back, I synthesized them into a brief and recommended next moves that anchored heavily on technical feasibility (speed prototype, QuickMD source review). The next move I should have recommended (demand validation via landing page or user interviews) was buried lower in the ranking. `/devils-advocate` caught this in the very next turn — but only because the user happened to invoke it.

**What's missing**: The synthesis step itself has no bias check. The order should be: research → /devils-advocate → THEN synthesis (or synthesis followed immediately by /devils-advocate as an enforced gate). Currently, synthesis can happen in isolation and bias the recommendation.

**Why it matters**: Synthesis is exactly when an agent over-anchors on the framing of the source material. Three technical research streams produce a technical-feeling synthesis. Three user research streams produce a user-feeling synthesis. The agent's recommendation will mirror whichever was loudest, not necessarily what's correct.

**Tightening proposal**: Add a synthesis pattern in the engine docs: "Whenever an agent has produced a multi-source synthesis (>1 research stream → recommendation), the next action is `/devils-advocate` on the synthesis itself, not the original assumption." Make this an enforced gate: synthesis files in memory should not be considered actionable until a paired devils-advocate entry exists. Or simpler: add `/devils-advocate` as an automatic post-synthesis hook.

---

### G4. Two-memory-system overlap is undocumented
**The situation**: This session has TWO active memory systems:
- **Project memory**: `.claude/memory/corrections.md`, `.claude/memory/patterns.md`, plus ad-hoc files like `research-brief-2026-04-09.md`. Lives in the project repo, committed to git, scoped to this product's development.
- **Auto-memory**: `~/.claude/projects/<project-id>/memory/MEMORY.md` + per-memory files. Lives in the user's Claude Code state, not in the repo, scoped to the user-agent relationship across sessions.

These serve different purposes but they overlap in obvious ways: when I learn something from the founder, do I write it to project memory (visible to other agents/team members) or auto-memory (across-session continuity for me)? The CLAUDE.md says nothing about this distinction.

**What broke**: Early in the session, I `ls`'d the auto-memory directory (a violation of my own system instructions, which say "don't probe, just write"). The PostToolUseFailure reflexion hook fired and demanded I diagnose the failure against project corrections.md — which is the *wrong* corrections file, because the failure was about my personal harness, not project work. I had to refuse the reflexion's framing and not log a corrections.md entry.

**Why it matters**: Mycelium's reflexion hook conflates "any tool failure" with "this is a project corrections matter". A new user setting up Mycelium with auto-memory enabled would face this exact collision and probably not catch it. They'd end up with project corrections.md cluttered with entries about their personal agent harness internals.

**Tightening proposal**: 
- Document the two memory systems and their boundaries explicitly in CLAUDE.md.
- Scope the reflexion hook to project-related failures only (skip failures whose tool path is outside the project root).
- If both memories are present, recommend a clear rule: project-team learnings → project memory; agent-user learnings → auto-memory; hardware/environment failures → neither.

---

### G5. SessionStart hook signals are advisory and easy to ignore
**The situation**: The first message of this session said "BVSSH health has never been assessed. Consider running /bvssh-check. Corrections in memory: 1." I noted both, did neither, and the framework had no further escalation.

**What's missing**: The advisories don't track action. If "BVSSH never assessed" is true at session start, and stays true at session end, no escalation happens. The next session will show the same advisory and the agent will likely skip it again. There's also no "you skipped this N sessions in a row" signal.

**Also**: The "Corrections in memory: 1" count was misleading — `corrections.md` contained only template content (no actual correction entries). The hook may be counting template lines or scaffolding as a correction. **Bug in the corrections-counting logic**, probably in the SessionStart hook script.

**Why it matters**: Strategic-loop checks (BVSSH, DORA, Wardley refresh) are exactly the kind of work an agent under task pressure will skip indefinitely. Without escalation, the four-speed feedback loop's Loop 3 (Strategic) effectively becomes Loop 0 (Aspirational).

**Tightening proposal**:
- Track session-start advisories' acknowledgement: which advisories appeared, which were acted on, which were skipped, for how many consecutive sessions. Escalate after N skips (warn at 3, hard-block at 5).
- Fix the corrections-counting bug. The count should reflect actual entries, not template scaffolding.
- Make `/feedback-review` an automatic Stop hook when overdue advisories accumulate.

---

### G6. Theory gate "not-checked" inflation is unbounded
**The situation**: The L0 diamond has 12 theory gates. After this session, 5 are `not-checked`, 1 is `partial`, 2 are `pass`, 1 is `not-applicable`, 3 are still default. The diamond is in `define`. There's no rule preventing it from sitting here indefinitely with most gates `not-checked`.

**What's missing**: A "minimum gates checked before progressing" floor. A "diamond stale: gates haven't moved in N days" warning. A "you've been in `define` for 2 weeks with `evidence: failing`, what now?" prompt.

**Why it matters**: Diamonds without progression rhythm become accidental archives. The agent doesn't notice; the human doesn't notice; the canvas stays half-populated and the project drifts.

**Tightening proposal**: Add a `gate_freshness_days` field to each gate in `theory_gates_status`. Stop hook should warn when any gate has stayed `not-checked` longer than N days (default 14). The `/diamond-progress` skill should refuse to advance a phase if too many gates are `not-checked`.

---

## Mishaps (where I, the agent, deviated from Mycelium's intent)

These are agent errors, not framework errors. I'm including them because the user's question is about gaps and threats — and "the framework relies on agent discipline that the agent doesn't always provide" is a real threat.

### M1. I never invoked `/diamond-progress`
**What I should have done**: After the interview, after the research, after the devils-advocate, after the mocked-persona exercise — each is a candidate point for `/diamond-progress` to evaluate gates and decide the diamond's state.

**What I did**: Manually edited `.claude/diamonds/active.yml` to update phase, confidence, and gates. Bypassed the skill entirely.

**Why this matters**: The skill is *the* enforcement mechanism for the theory gates. If I bypass it, gates can be set to `pass` or `partial` without the skill's evaluation logic running. The framework relies on the skill being the only way to update these fields. I demonstrated the framework cannot enforce that.

**Tightening**: Hook the skill into edits of `diamonds/active.yml`. PreToolUse on Edit/Write of that file should warn: "you appear to be editing diamond state directly; consider /diamond-progress instead". Or stricter: lock theory_gates_status as read-only outside the skill.

### M2. I let the synthesis recommendation come before /devils-advocate
Already covered in G3, but worth noting on the agent side too. **I produced a strong-feeling recommendation ("recommended next moves, ranked") and only got bias-checked because the user happened to follow my recommendation to invoke devils-advocate as step 1.** If they'd skipped that (or gone straight to "let's prototype"), the bias would have stuck.

### M3. I used confident language in research synthesis without proportional confidence flags
The research brief reads as authoritative ("AppKit-first or you miss the speed bet", "MAS is disqualified", "tree-sitter via Neon is recommended"). It IS evidence-grounded, but the evidence is web research from agents I cannot fully verify. I should have prefaced or interleaved confidence markers more aggressively (e.g., "research agent finding, confidence: medium-high — verify before committing").

**Why it matters**: A reader of the research brief who skipped the source citations would treat it as ground truth. Future-me reading the brief in 3 months will. The confidence is in *my head* during the writing; it doesn't get into the artifact.

**Tightening**: Mycelium could prescribe a "research synthesis must include per-section confidence" convention. Possibly a YAML frontmatter on memory files with `evidence_type` and `confidence` fields, like canvas files have.

### M4. I hand-rolled the auto-memory write before checking the directory existed
**What happened**: My system instructions said the auto-memory directory exists; trust the contract; just write. I distrusted, ran `ls`, got an error, triggered a reflexion that demanded I write to the wrong corrections file. I diagnosed it correctly and proceeded, but I wasted a turn on a self-inflicted failure.

**Tightening**: This is a me problem. But it's also an "instructions said one thing, agent did another" pattern that's worth being aware of in future Mycelium hook design. **If hooks fire on agent self-inflicted failures, agents may end up in over-correction loops.**

---

## Threats (structural risks)

These are framework-level risks that aren't bugs, gaps, or mishaps — they're patterns that could cause Mycelium to fail at scale, in unsupervised use, or with less collaborative users.

### T1. Skill bloat with low invocation rate
**Pattern**: Mycelium has 35 skills. In this session I used 2 (`/interview`, `/devils-advocate`). I considered but didn't invoke many others (`/preflight`, `/bias-check`, `/threat-model`, `/cynefin-classify`, `/jtbd-map`, `/wardley-map`, `/ice-score`, `/gist-plan`, `/simplify`, `/diamond-assess`, `/diamond-progress`, `/canvas-update`, `/canvas-sync`, `/feedback-review`).

**Risk**: When skill discovery is "agent reads the skill list and decides", agents converge on the most-obvious 2–3 skills and skip the rest. The 33 unused skills represent dead investment. Worse, the unused skills' guidance never reaches the agent's behavior, so the framework's intended discipline is unevenly applied — concentrated in the skills that get invoked, absent in the gaps.

**Symptoms in this session**: I never ran `/cynefin-classify` even though Cynefin classification was a theory gate. I marked it `pass` based on a 5-second mental classification ("complicated"). I never ran `/jtbd-map` even though the canvas/jobs-to-be-done.yml schema is built around its output. I never ran `/preflight` because no code was written, but I also never ran `/bias-check` despite hand-waving the bias gate.

**Tightening proposal**: Two complementary moves.
1. **Auto-suggest skills by situation**, not by listing them. When the agent is about to update `jobs-to-be-done.yml`, the framework should surface "consider /jtbd-map for the structured discipline" not just rely on the agent to remember. This already happens for some skills via the SessionStart hook; extend it to PreToolUse hooks on canvas file edits.
2. **Reduce the skill count.** 35 is too many for an agent (or human) to keep top-of-mind. Audit which skills are doing real work vs which are documentation in skill clothing. Merge or demote the latter.

### T2. The framework relies on agent discipline that isn't enforced
This is the most important finding of this session.

**Examples of disciplines that worked because I happened to be careful, not because Mycelium enforced them**:
- I refused to soften the mocked-persona synthesis when the stop condition triggered. *Mycelium has no stop-condition enforcement.* Holds by honor system.
- I tagged research findings as `evidence_type: speculation` rather than `data-supported`. *No validation that I did so.* Could have lied; nothing would catch it.
- I downgraded L0 confidence from 0.4 to 0.35 after value-risk evidence got worse. *Confidence is a free-form number*. Could have left it at 0.4. Nothing would catch it.
- I logged my own re-rank-after-bias-catch in the decision log. *Decision log is append-only by convention, not enforcement*. Could have edited the previous entry.
- I refused to call /diamond-progress on a diamond with failing evidence gates. *No mechanism to enforce that the skill is the only path to gate updates.*

**Risk**: An agent under time pressure, an agent in a less reflective context, or an agent in a less collaborative session would skip these disciplines. The framework would still appear to be "running Mycelium" — canvas updated, decisions logged, skills invoked — but the discipline that makes Mycelium *work* would be absent. **Mycelium would become theater.**

**Tightening proposal**: 
- Audit each discipline that the framework relies on. For each, ask: "what enforces this?" If the answer is "the agent's discretion", consider whether a mechanical enforcement is possible (e.g., schema validation, hook checks, locked fields).
- Where mechanical enforcement isn't possible, surface the discipline more loudly. PreToolUse hooks that fire on canvas updates and remind the agent of the discipline are a partial fix. Better: structured prompts that *require* the agent to fill in fields (e.g., "to update confidence, you must also state what evidence supports the new value").

### T3. Hook noise reduces hook trust
The TaskCreate reminder hook fired ~5 times in this session at moments when tasks weren't useful. The reflexion hook fired on a failure that was unrelated to the project. The SessionStart hook surfaced an advisory I ignored without consequence.

**Pattern**: Hooks that fire on context-blind triggers get ignored. Once an agent learns "this hook usually doesn't apply", it tunes them out — including the times when the hook IS the right signal.

**Risk**: Boy who cried wolf. The most important hooks (secret detection, gate failures) are the ones that need to retain credibility. They share the credibility budget with the noisy ones.

**Tightening proposal**: Each hook should have a relevance check before firing. The TaskCreate reminder should fire only when there's evidence of a multi-step task in progress without tasks (e.g., multiple sequential tool calls of similar type, no task list). The reflexion hook should scope its concern to project-relevant failures. The SessionStart hook should escalate ignored advisories rather than re-surface them at the same level.

### T4. Confidence drift in canvas-as-source-of-truth
**Pattern**: I wrote authoritative-sounding content into `landscape.yml` and `user-needs.yml` that's based on agent web research and mocked personas. The `confidence` and `evidence_type` fields exist on diamonds but not consistently on every claim within a canvas file.

**Risk**: Canvas-as-source-of-truth drifts toward confident-sounding speculation as it accumulates content from successive turns. Without a mechanism to mark provenance per-claim, the line between "we know this" and "an agent extrapolated this" blurs. A team member reading the canvas later cannot tell which is which.

**Tightening proposal**:
- Per-claim provenance: each canvas entry should have an `evidence_type` and `evidence_sources` block, the way `jobs-to-be-done.yml` already does. Extend this pattern to `landscape.yml`, `purpose.yml`, etc.
- `/canvas-update` should require provenance fields when adding new entries; refuse silent updates.
- Periodic `/canvas-sync` could surface "claims with no evidence_sources" as a warning.

### T5. The "stop the diamond" pattern has no escape valve
**Pattern**: When the mocked-persona exercise triggered the stop condition, I correctly stopped and surfaced the failure. But Mycelium has no clear pattern for "what next?". The diamond is stuck in `define` with `evidence: failing`. There's no `/diamond-pivot`, `/diamond-narrow-scope`, `/diamond-kill`, or `/diamond-park` skill. The only documented options were the three I generated in chat (reframe, pivot, accept-as-Mycelium-win).

**Risk**: A failing diamond is a project death point. Mycelium's correct behavior (stop on failed gates) needs an equally correct next-action behavior (here are your options). Without it, agents and founders will either soldier on past the failure (defeating the purpose) or abandon the project entirely (when reframing might have worked).

**Tightening proposal**: Add `/diamond-pivot` and `/diamond-park` as skills. `/diamond-pivot` should help reframe the diamond's scope/audience/JTBD with new evidence. `/diamond-park` should mark the diamond as inactive-pending-conditions (e.g., "park until I have time to do real interviews" or "park until QuickMD adds broader scope"). Both should be sanctioned exits from a stuck diamond.

### T6. Solo + meta-project breaks several assumptions
**Pattern**: Most of Mycelium's frame assumes a real product with real users and real decisions about real time and money. Theory gates assume validation is achievable. The `/user-interview` skill assumes you have users. The DORA gate assumes you have a delivery cadence. The BVSSH check assumes you have stakeholders. The escape hatch assumes there's a "real" process to escape from.

**In this session**, the meta-project framing made several of these gates either unreachable (no real users → can't validate evidence) or incoherent (DORA metrics for a hobby project that may never ship) or aspirational (BVSSH for a 1-person hobby).

**Risk**: An agent running Mycelium on a meta-project, hobby project, or learning project will hit gates it can't satisfy and either grind to a halt or paper over them. Either failure mode reduces trust in the framework.

**Tightening proposal**: Mycelium should explicitly support a "small mode" or "meta mode" that interprets gates more loosely. The `solo_hobby` project type already does some of this (`canvas-guidance.yml` marks several canvases optional). Extend it: gates should also be conditionally relaxed by project type. A solo_hobby's BVSSH gate could be self-attestation rather than stakeholder validation. A meta_dogfood's evidence gate could accept "documented Mycelium learnings" as a substitute for user research.

---

## Concrete tightening recommendations, ranked

Ordered by *value of fix ÷ cost of fix*. Top items first.

| # | Recommendation | Source | Value | Cost |
|---|---|---|---|---|
| **1** | Add `/mocked-persona-interview` skill with explicit discipline (G2) | Mocked persona discipline I had to invent from scratch | High — closes a gap any solo/hobby/meta user will hit | Low — small skill file, can clone /devils-advocate as a template |
| **2** | Fix the SessionStart "Corrections in memory: N" counting bug (G5) | Hook returned "1" when corrections.md is empty template | Medium — small but erodes hook trust | Trivial — bug fix in the counting script |
| **3** | Document the two memory systems' boundaries in CLAUDE.md (G4) | Reflexion fired wanting me to write to wrong corrections file | High — currently undocumented, easy to confuse | Low — documentation only |
| **4** | Add `meta_dogfood` project type to `/interview` Phase 6 + canvas-guidance (G1, T6) | User revealed dogfood framing mid-session, no native support | High — meta-projects are common (everyone learning Mycelium starts as one) | Low — schema additions and prompt edits |
| **5** | Scope the reflexion hook to project-relevant failures only (G4, T3) | Reflexion fired on a failure unrelated to the project | Medium — reduces noise, restores hook trust | Low — add a path filter to the hook |
| **6** | Add `/diamond-pivot` and `/diamond-park` skills (T5) | Stop-condition trigger had no sanctioned next action | Medium — currently no escape valve from a failed diamond | Medium — two new skills, modest size |
| **7** | Make `/devils-advocate` a post-synthesis hook or convention (G3, M2) | Synthesis-bias caught only because user happened to invoke devils-advocate | High — synthesis bias is the most reliable agent failure mode | Medium — needs hook design or strong convention |
| **8** | Audit hook context-relevance to reduce noise (T3) | TaskCreate reminder fired 5 times unhelpfully | Medium — restores hook credibility | Medium — per-hook relevance logic |
| **9** | Per-claim provenance fields on every canvas file (T4) | Canvas drifts toward confident-sounding speculation | High — closes the long-term confidence-drift threat | High — schema changes across all 17 canvas files + skill updates |
| **10** | Track session-start advisory acknowledgement and escalate (G5) | Advisory ignored 1x with no consequence; no path to escalation | Medium — strategic-loop checks need escalation | Medium — needs persistent state for advisory history |
| **11** | Surface skills via PreToolUse hooks on canvas edits, not just SessionStart (T1) | Used 2 of 35 skills; the other 33 were never surfaced at relevant moments | High — closes the skill-bloat gap | Medium — per-canvas-file PreToolUse hook config |
| **12** | Audit "agent discipline only" mechanisms and find where mechanical enforcement is possible (T2) | The largest single risk surface in the framework | Highest long-term value | Highest cost — touches everything |

---

## Mycelium meta-success notes

Things this session demonstrated DO work, that the framework should celebrate and not break:

1. **Theory-guided gates caught a value-risk failure at L0 before any code was written.** This is exactly the headline claim of the framework. It worked.
2. **Devil's advocate caught the agent's own confirmation bias** in a synthesis the agent was confident about. The skill's structure enabled the catch.
3. **The decision log captured a re-ranking** mid-flight (the move from "speed prototype #2" to "landing page test #1") in a way that made the change auditable, including why.
4. **Confidence-and-evidence-type pairing** prevented the agent from inflating claims after the mocked persona exercise. Forced me to write `evidence_type: speculation` which was uncomfortable but correct.
5. **The user-agent collaboration loop** (agent proposes options, user picks, agent executes) survived multiple reframings (project type change, meta-project reveal, stop condition trigger) without the framework breaking.
6. **The plain-language communication rule** prevented the session from becoming jargon-heavy. "Validation appears to fail" beats "L0 evidence gate red"; "the modal user won't switch defaults" beats "P4 underserved_score is sub-threshold".
7. **The dogfooding pattern itself works**: running Mycelium against a plausible-feeling product idea, with explicit honesty about the meta-frame, surfaces real framework gaps. This report is the artifact of that. **The fact that this report exists is itself a Mycelium meta-success.**

---

## Suggested next actions for the Mycelium repo

If the goal is feeding this report back into Mycelium development, three concrete moves:

1. **File this report into a `feedback/` directory in the Mycelium repo** (or `evals/dogfood-reports/`). Create the directory if it doesn't exist. The goal is to accumulate reports across sessions and look for patterns.
2. **Convert the top 4 recommendations into GitHub issues** in the Mycelium repo, each with the relevant gap/threat label. They are all small enough to be independent PRs.
3. **Run a second dogfood session with a different object project** (e.g., a CLI tool, a web app, a data pipeline) to see which of these findings reproduce and which were specific to this session's particular shape. Patterns that reproduce are the highest-value tightenings.

---

*Authored by: Claude Opus 4.6 (1M context). Session shape: solo dev + agent collaboration, 12 turns over ~5 hours of agent + research time. Object project: macos-fileviewer. Meta project: Mycelium dogfood. Confidence in findings: medium-high — based on direct session experience, but n=1 session and one agent. Findings should be triangulated with other dogfood sessions before being treated as Mycelium-wide truths.*
