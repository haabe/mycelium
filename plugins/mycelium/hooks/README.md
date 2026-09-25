# Mycelium Hooks System

## 5-Layer Enforcement Architecture

Hooks are registered in `.claude/settings.json` (shared, committed to git). Personal overrides go in `.claude/settings.local.json` (gitignored). Mycelium uses a layered approach where faster/cheaper hooks run first, and expensive semantic checks are reserved for skill-level invocation.

```
Layer 1: PreToolUse gate     (command, ~30 tokens)  — Blocks bad writes before they happen
Layer 2: PostToolUse nudge   (command, ~50 tokens)  — Context-aware reminders after changes
Layer 3: PostToolUseFailure  (prompt, ~200 tokens)  — Reflexion analysis on failures
Layer 4: Stop check          (command, ~50 tokens)  — Guardrail + feedback loop compliance
Layer 5: SessionStart check  (command, ~50 tokens)  — Overdue strategic loop reminders
Layer 6: Skill-level gates   (on-demand, varies)    — Full theory gate evaluation
```

Total hook overhead: ~6,000 tokens/session (negligible vs typical 50K-200K session).

## Active Hooks

### Layer 1: PreToolUse -> Write/Edit/MultiEdit (`gate.sh`)
**Triggers**: Before any code edit to source files
**Type**: `command` (5s timeout)
**Enforces**:
- G-P5: Preflight stamp freshness (corrections.md read recently)
- G-P5: Corrections.md hash consistency (re-read if changed)
- G-S1: Secret detection — regex scan for API keys, tokens, passwords, connection strings in content being written

**Logs (v0.204.0)**: every block on the stamp or hash path appends one JSON line (`ts`, `hook`, `reason` = `stale-stamp` | `corrections-hash`, `session_id`) to `.claude/state/gate-block-log.jsonl`, gitignored with the rest of `state/`. `scripts/check_hook_delivery.py` reports blocks per session beside hook delivery, so "does the gate cost more than it catches" (opp-072) is a count.

**Important on secret detection**: The regex patterns in gate.sh are a **fast first-pass tripwire** (~5ms, catches the obvious 80%). For thorough secret scanning, the validation suite should use proper tools (semgrep, gitleaks, trufflehog) which are JiT-detected and configured per tech stack. Both layers are needed:
- gate.sh catches secrets BEFORE they're written to disk
- Validation suite tools catch what regex misses BEFORE commit
- CI/CD pipeline is the final safety net

**Excludes**: `.claude/` directory edits (always allowed)
**Gates every real path inside the project that is not under `.claude/`** (until 0.196.0 a directory list; `config.py`, `source/` and `Src/` all fell outside it, adversarial pass 2026-09-11). Reads the tool call through `scripts/_hook_input.py`: every path key, resolved to its real location, MultiEdit edits included, Bash write targets scanned; a write to guard state (`upstream.json`, `manifest.yml`, `active-execution.json`, the discovery, delivery, brownfield and scale-lock ack files) returns `ask` so the person decides, with `MYCELIUM_GUARD_STATE_EDIT=1` in the human's own shell as the setup-time override.

**Sibling PreToolUse hooks (same Write/Edit/MultiEdit matcher, run alongside `gate.sh`):**
- **`discovery-gate.sh`** (v0.56.0) — blocks scaffolding NEW source files in a project where discovery has never been engaged (no diamond in `active.yml`, no populated `purpose.yml`). The teeth for the deliver-framed-opening routing gap: router-discipline prose alone did not stop "build me X" first messages from producing code on an empty canvas (founder dogfood 2026-06-08/09; mechanically reproduced by roadmap auto-dogfood 2026-07-02). Deliberately narrow to avoid a friction wall: Write tool only (Edit/MultiEdit never gated — brownfield untouched), new files only, source/infra shapes only, and a one-time on-the-record escape hatch (`.claude/state/discovery-skip-ack`, written after the USER explicitly declines discovery). Block message routes to `/mycelium:start`. Tests: `tests/bash/test_discovery_gate.sh` (13 asserts, scenario-per-guardpost).
  **Second stage, the delivery gate (v0.245.0):** once discovery IS engaged, a new source file is blocked until an open L3, L4 or L5 diamond **whose entry-lock chain holds and which is in Develop or Deliver with Four Risks and Privacy passed** (phase follows the work, v0.246.0) (a purpose, a desired outcome, a target opportunity with evidence above it; `scripts/scale_locks.py --delivery-state`), or the user records `.claude/state/delivery-skip-ack` (guard state: the agent cannot write it without asking). Any open L3 was not enough, because `/mycelium:start` leaves only a purpose, so an L3 opened after it builds on a guess; an end-to-end dogfood run shipped a release under an L0 in discover. The block names what is missing. Without PyYAML the locks cannot be read and the gate allows; `preflight.sh` then says so on every prompt, and otherwise prints the `MYCELIUM DELIVERY STATE` pre-warning.
- **`exposure-gate.sh`** (v0.246.0, Bash) — blocks a command that puts the work in front of real people (a deploy CLI's deploy verb, a package publish, a remote shell or copy that pulls, restarts or syncs onto a host) unless an open L3/L4/L5 whose chain holds is in **Deliver** with Security, Privacy and Service Quality passed (`scale_locks.py --exposure-hook`). Found by E2E run 10: an SMS app holding phone numbers and link tokens went live under an L3 in define with every gate pending. Narrow: other commands exit before python (`git push origin`, `ssh host tail`, local rsync and `docker compose up` are not deploys); projects with no diamonds are not judged; a deploy the USER runs is outside any hook, so operating contract rule 14 and `/mycelium:preflight` carry it. Escape hatch: `delivery-skip-ack`. Logs blocks to `.claude/state/exposure-gate-fires.jsonl`. Tests: `tests/bash/test_exposure_gate.sh`, `tests/python/test_scale_locks.py`.
- **`scale-lock-gate.sh`** (v0.245.0) — blocks a write to `.claude/diamonds/active.yml` that OPENS a diamond (a new id, a rescaled one, or one moved back into the active list) whose parent has not yet established what it builds on: L1 on a purpose, L2 on a strategy (an L1 diamond, a North Star, the landscape) and a desired outcome, L3 on a target opportunity with evidence in an L2 diamond, L4 on an L3 that names the test its delivery carries, L5 on launch data and the L3 at medium confidence (v0.256.0); since v0.247.0 it also refuses a new diamond written past discover, and since v0.248.0 a FORWARD phase move whose transitions lack their matrix gates or a `progression_history` entry (`engine/diamond-rules.md`, Entry locks; one implementation in `scripts/scale_locks.py`). The founder's dependency tree, which three releases had undone by opening every door "whether or not the parent has progressed". Narrow: a diamond already open at its scale is never re-judged on edit (`scale_locks.py --check` reports it, and the delivery gate reads its chain before new code), a Bash write to the file is not parsed (it cannot unlock code: the delivery gate re-reads the chain), and any other write exits before python starts (case-insensitively). An unparseable proposed file and a crash of the checker both refuse. Escape hatch: `<id> <scale> <YYYY-MM-DD> <the user's own words>` in `.claude/state/scale-lock-ack`, guard state, so only the user can grant it. Logs blocks to `.claude/state/scale-lock-fires.jsonl`. Tests: `tests/bash/test_scale_lock_gate.sh`, `tests/python/test_scale_locks.py`.
- **`scope-gate.sh`** — scope enforcement (keeps edits within the declared work scope).
- **`framework-guard.sh`** — blocks edits to FRAMEWORK-classified files in *dogfood instances* of an upstream Mycelium repo (active only when `.claude/state/upstream.json` exists). Also wired on `Bash` and MCP-filesystem matchers.
- **`autonomous-evidence-guard.sh`** (v0.42.0) — evidence-integrity enforcement. **Only fires in a DECLARED autonomous run** (env `MYCELIUM_AUTONOMOUS_RUN`, or `autonomous: true` in `diamonds/active.yml`); a strict no-op in every interactive session. Hard-blocks (`permissionDecision: deny`) any write that introduces `source_class: external_human|external_data`, `validated: true`, or `evidence_type` above `speculation` into `.claude/canvas/*.yml`, `.claude/diamonds/*.yml`, or their `mycelium-state/` mirror — the fabrication a sub-Fable-5 model committed in the opp-011 Stage A run (2026-06-11). Also wired on the MCP-filesystem write/edit matcher. **Registered on all three runtime surfaces** (`hooks.json`, `hooks.codex.json`, `hooks.cursor.json`) as of v0.44.1 — the 2026-06-12 gap analysis found the Codex/Cursor registrations missing, leaving those surfaces with zero autonomous evidence enforcement. See `engine/autonomous-mode.md`.
- **`read-before-research-guard.sh`** (v0.127.0) — WARNS, never blocks. Fires when an agent is about
  to search externally (`WebSearch`, `WebFetch`, brave-search, fetch) for an entity that already
  appears in `.claude/canvas/*.yml`, and surfaces the existing entries with `file:line`.
  **NOT a token-efficiency check — a constraint-loss check.** Research conducted without the canvas
  is analysis without the constraints the canvas already recorded: quarantine entries, values gates,
  prior judgements, source caveats. Found by the i-productified dogfood 2026-08-24, where an agent
  recommended a company as "a genuine find" that the canvas recorded the founder rejecting on ethical
  grounds — minutes after writing down the rule against exactly that. Prose was falsified in the same
  turn, which is why this is a hook. Every firing is logged to
  `.claude/state/read-before-research-log.jsonl` so the tier is set by a measured action rate.
- **`absence-claim-guard.sh`** (v0.83.0) — WARNS, never blocks. Fires when an assertive absence ("no need covers", "nothing checks", "was never routed", "nowhere to go", "does not exist") is written into a `.claude/` evidence surface (canvas, memory, harness, evals, diamonds) without a search named in the same sentence. Five claims of this shape were made in one dogfood session (2026-08-04) and two were pushed to the canvas before being caught; an auto-memory rule against exactly this already existed and never fired, because notes are read at session start and decay. **Calibrated against 60,010 real corpus sentences**: the first draft fired on 0.42% and half were ledger prose ("No confidence gate moved") — records of what a session did rather than claims about what exists — so the patterns now require an existence or coverage verb, giving 0.175%. It cannot verify a search happened or that a claim's scope matches it; the sentence that caused the 2026-08-04 error *carried* a citation. **Also wired on the shell matcher** (`Bash` in `hooks.json`/`hooks.codex.json`, `Shell` in `hooks.cursor.json`) as of v0.84.0 — the v0.83.0 version watched `Write|Edit|MultiEdit` only, and every correction appended during the session that produced it went in as `cat >> .claude/memory/corrections.md <<'EOF'`, which no write matcher sees. The shell half watches `>`/`>>`, `tee` and `sed -i` into evidence surfaces, and strips the redirect target before scanning, because the scope suppressor counts a named file as showing your work and the destination is a named file. Reads, unwatched destinations and `git commit -m` prose stay silent — the last is a fixture, since this project writes long prose commit messages and warning on them would make the guard noise within a day. Tests: `tests/python/test_absence_claim_guard.py` (56 asserts, scenario-per-guardpost, including calibration regressions).
- **`key-shape-guard.sh`** (v0.214.0) — WARNS, never blocks. Fires when a Write/Edit/MultiEdit into `.claude/canvas/**` or `.claude/diamonds/**` introduces a key whose NAME carries a date or an entity id (`promoted_2026_09_02`, `ht_010_status`), or a second spelling of a stem the target file already holds (`reply-sent` beside `reply_sent`). The write-time half of the near-duplicate-keys row; `check_key_shape.py --stems` (v0.212.0) is the sweep half, and the two share the same regexes and stem function so they cannot disagree. Founder, 2026-09-02: a sweep finds the collision after the key exists and forces a second decision nobody wanted; the guard catches it while the author still holds the reason. **Calibrated by replaying 60 dogfood commits (2026-09-10..15)**: 141 dated or entity-scoped keys were added in that window, every one of which the guard would have named at the keystroke; the spelling half fired on prose (`Date:` inside a block scalar) four times in five before block scalars, quoted strings and case-only variants were excluded, so those three are left to the sweep. Writing the plain spelling beside a dated twin is the fix, not a finding. Cannot see a heredoc. Logs to `.claude/state/key-shape-guard-log.jsonl`. Tests: `tests/python/test_key_shape_guard.py`.
- **`shell-safety-guard.sh`** (v0.81.0, wired on `Bash`) — warns on `$?` after a pipeline, backticks, `grep` gating an `&&` chain, a canvas write followed by an ungated `git commit`, and (v0.223.0) a scripted multi-file edit that can half-apply without `safe_replace.py`. See `scripts/shell_safety_guard.py`.

**Runtime matcher vocabularies differ, and are not interchangeable** (verified against vendor docs 2026-08-04, after a dogfood question about whether the runtimes had moved since registration):

| Runtime | Event names | Write-side tool names | Shell |
|---|---|---|---|
| Claude Code | `PreToolUse` | `Write`, `Edit`, `MultiEdit` | `Bash` |
| Codex | `PreToolUse` (same case) | **`apply_patch`** | `Bash` |
| Cursor | **`preToolUse`** (camelCase) | `Write` | **`Shell`** |

Two live defects were found and fixed at v0.83.0. `hooks.cursor.json` carried a `PreToolUse` block in Claude Code's nested shape — an event name Cursor does not have, and JSON keys are literal rather than regexes, so **`shell-safety-guard` had never fired in Cursor** despite v0.81.0 recording it as registered on all three surfaces. And the Codex write-side matcher named only Claude Code's tools; `MultiEdit` appears **zero** times in the whole `openai/codex` repository, so every write-side guard was matching nothing there. When adding a hook, read the target manifest's existing entries and copy their shape — the three files use different event casing, different entry structures (Cursor is flat, the others nest under `hooks`), and different `CLAUDE_PLUGIN_ROOT` fallbacks.

**UNVERIFIED, and it is the load-bearing half for Cursor: nothing here has been observed running in Cursor.** Both v0.83.0 fixes are correct *against the vendor documentation* and neither has been watched execute. Cursor's docs place hooks at `.cursor/hooks.json` (project) or `~/.cursor/hooks.json` (user); this plugin ships `hooks/hooks.cursor.json` inside the plugin tree, and whether anything copies it to a path Cursor reads is unknown from inside this repository. If nothing does, Cursor consumers get **no** Mycelium hooks at all and the corrected registration sits in a file the runtime never opens — necessary but not sufficient. This cannot be closed by inspecting the manifest again: reading our own file for the presence of an entry is precisely the check that produced the original dead registrations. It needs one person running Cursor to trigger any warning once. Tracked as the second question on roadmap `ht-053`.

### Layer 2: PostToolUse -> Write/Edit/MultiEdit (`post-write-nudge.sh`)
**Triggers**: After any successful code edit
**Type**: `command` (3s timeout)
**Does**: Returns context-aware `additionalContext` based on file type:
- UI files (*.tsx, *.jsx, *.vue, *.svelte, *.html) -> Accessibility + error states reminder
- API/server files (*/api/*, */routes/*, */server/*) -> Input validation + OWASP reminder
- Test files -> Positive reinforcement ("Tests updated. Good.")
- Other source -> Generic validation suite reminder

Does NOT block. Nudges the agent toward quality checks by injecting reminders into context.

### Layer 3: PostToolUseFailure -> Bash (reflexion trigger)
**Triggers**: After any Bash command failure
**Type**: `prompt` (15s timeout, ~200 tokens)
**Does**: Forces structured failure analysis:
1. What failed and why?
2. Is this a known pattern from corrections.md?
3. What is the root cause?
4. What specific fix is needed?
5. Should this be logged as a new correction?

Prevents blind retry. Diagnosis first, then fix.

### Layer 4: Stop (`stop-check.sh`)
**Triggers**: When Claude finishes responding
**Type**: `command` (5s timeout)
**Checks**:
- If active diamond is L4 Delivery but `threat-model.yml` is empty -> GUARDRAIL WARNING with `/threat-model` suggestion
- If Downe's 15 principles all "not-assessed" -> GUARDRAIL WARNING with `/service-check` suggestion
- If BVSSH or DORA checks are overdue (>30 days) -> FEEDBACK LOOP WARNING with skill suggestion
- Corrections and decisions count for session summary

Returns warnings via `additionalContext` (does not block). This is the "hybrid" pattern: hook detects the condition, injects a message that tells Claude to run the appropriate skill.

- **`ci-signal.sh`** (v0.85.0, on **Stop** and on **SessionStart** with `--session-start`) — reports ONCE when the workflow for the currently checked-out commit has failed. Closes a hole that let the dogfood workflow stay red for **thirteen consecutive pushes**: the flow was one-way — local push, CI runs, verdict lives on GitHub and never returns — and none of the five hook points looked outward. A pull request forces you to look; `main` does not ask. **Tracks no pushes by design**: GitHub already knows, so it matches the newest run's `headSha` against local HEAD and speaks only about the commit actually checked out. That match is load-bearing — reading `gh run list --limit 1` without it reports the PREVIOUS commit's run, which is how a failed push got reported as "CI: success" the same day. Stop is the warm catch (one session, thirteen pushes, needs to hear it mid-session); SessionStart is the cold catch and bypasses the dedupe, because a new session is a new agent with no memory of what the last one was told. Silent on green, in-progress, another commit's failure, detached HEAD, missing `gh`, no auth, no network, no workflows. One network call per 90s, one report per run. Tests: `tests/python/test_ci_signal.py` (22 asserts; the rate-limit test counts `gh` invocations directly, and was verified to fail with the guard removed).

### Layer 4b: Stop (`next-action-check.sh`) — a framework turn ends on one next action
**Triggers**: When Claude finishes responding, after `stop-check.sh`
**Type**: `command` (5s timeout)
**Check**: if a `mycelium:*` skill ran in this turn (a `Skill` tool_use in the transcript) and the closing message (`last_assistant_message`, transcript fallback) has no line beginning `Next:`, returns `{"decision":"block","reason":...}` so the agent ends on exactly one next action. Silent on turns with no framework skill run. Honours `stop_hook_active`; reports via `systemMessage` when it cannot read its input or the transcript (Cursor, Codex) rather than failing silently. Person override `MYCELIUM_NEXT_ACTION_CHECK=off`. Downe P10; operating-contract rule 12; dogfood opp-006/sol-006b. Gate blocks (PreToolUse denies) are not yet in scope.

### Layer 5: SessionStart (`session-start.sh`)
**Triggers**: When a session starts or resumes
**Matcher**: `startup|resume`
**Type**: `command` (5s timeout)
**Checks**:
- If BVSSH health check is overdue (>30 days or never done) -> Reminder to run `/bvssh-check`
- If DORA metrics are overdue (>30 days since last measurement) -> Reminder to run `/dora-check`
- Reports corrections count for awareness

Returns `additionalContext` so the agent knows about overdue strategic feedback loops from the start of the session. Part of the four-speed feedback loop system (see `../engine/feedback-loops.md`).

### Layer 6: Skill-Level Gates (not hooks)
**Triggers**: When `/diamond-progress` is explicitly invoked
**Does**: Full theory gate evaluation across all 15 gates (Evidence, Four Risks, JTBD, Cynefin, Bias, Security, Privacy, BVSSH, Service Quality, Delivery Metrics, Corrections, Regulatory, Explainability, Landscape, Capacity). Requires judgment, context, and multiple canvas file reads.

## Hook Types (by cost)

| Type | Cost | Latency | Use For |
|------|------|---------|---------|
| `command` | ~30 tokens | <100ms | File checks, regex, deterministic rules |
| `http` | ~30 tokens + network | <500ms | Centralized enforcement services |
| `prompt` | ~200 tokens | 2-5s | Semantic evaluation (is this safe?) |
| `agent` | ~500-3000 tokens | 10-60s | Multi-step verification with tool access |

## Design Principles

1. **Hooks nudge, skills judge** -- Hooks catch binary violations and inject reminders. Skills have full judgment for nuanced evaluation.
2. **Never block on semantics at PreToolUse** -- False positive blocks infuriate users. Use PostToolUse additionalContext to nudge instead.
3. **Use `if` field for zero-overhead filtering** -- Evaluated before the hook process spawns. Non-matching calls cost nothing.
4. **command > prompt > agent** -- Always prefer the cheapest handler that does the job.
5. **Stop hooks for hybrid enforcement** -- Detect conditions mechanically, suggest skills for resolution.

## Available Hook Events (28 in Claude Code 2026)

Key ones for Mycelium:
- `PreToolUse` -- Can block (exit 2 or permissionDecision: deny)
- `PostToolUse` -- Can inject additionalContext
- `PostToolUseFailure` -- Can trigger reflexion
- `Stop` -- Can block Claude from stopping (exit 2) or inject warnings
- `TaskCompleted` -- Can block task completion (DoD enforcement)
- `SubagentStop` -- Can prevent subagents from finishing prematurely
- `SessionStart` -- Can inject session context

Full reference: https://code.claude.com/docs/en/hooks

## Helper Scripts (Not Standalone Hooks)

### preflight.sh
Registered on `UserPromptSubmit` (5 s timeout) AND called by `gate.sh` when the preflight stamp is expired or missing. Creates a stamp file with the corrections.md hash and a timestamp, prints the corrections count, and delivers the background session-start checks once per session (v0.186.0). This section said "NOT a standalone hook" until 0.222.0; it has been registered in `hooks.json` for a long time and the text had not followed.

**Discovery pre-warning (v0.222.0).** While the project has no discovery state and no `discovery-skip-ack`, it also prints one line telling the model that `discovery-gate.sh` will refuse new source files, so it should ask who, what problem and what evidence before drafting a design, and to ignore the line when the prompt is not a build request. The condition is `hi_discovery_engaged`, the function the gate itself calls, so the warning and the block cannot disagree. State-keyed: it reads nothing from the prompt. Advisory: it never blocks. Why it exists: the gate fires only after the model has drafted the work it refuses.

---

## v0.9.0 Additions: Computational Enforcement Layer

v0.9.0 added three new hooks and one new wrapper script, all focused on closing the gap Daniel Bentes identified in the BDSK comparison: Mycelium had strong upstream thinking discipline but weak downstream execution enforcement.

### scope-gate.sh (PreToolUse — BLOCK when active)
**Triggers**: PreToolUse on Edit/Write/MultiEdit
**Type**: `command` (5s timeout)
**Tier**: BLOCK (when an active L4 execution exists)
**Fail policy**: **Fail-closed** (deny on state corruption, exit 2 on script failure)

When `.claude/state/active-execution.json` exists and declares `in_scope_paths`, this hook blocks edits to files outside the declared scope. Mirrors BDSK's `check-scope.sh` pattern. Delegates to `${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py` (Python stdlib only — no PyYAML).

When no `active-execution.json` exists, the hook is a no-op (allows all edits). This is the common case before L4 delivery work begins.

### change-log.sh (PostToolUse — observability)
**Triggers**: PostToolUse on Edit/Write/MultiEdit
**Type**: `command` (3s timeout)
**Tier**: Observability (not BLOCK, not NUDGE — pure audit trail)
**Fail policy**: Fail-open (audit failures never block code changes)

Appends one JSONL line per code modification to `.claude/state/change-log.jsonl`. Each entry includes timestamp, tool, file path, session_id, and active diamond_id (if any). Mirrors BDSK's audit trail. Used for post-hoc forensic analysis: "what did the agent touch during diamond X?"

### diamond-state-audit.sh (PostToolUse — observability)
**Triggers**: PostToolUse on Edit/Write/MultiEdit (filtered to `.claude/diamonds/*.yml` paths)
**Type**: `command` (3s timeout)
**Tier**: Observability (creates friction without blocking)
**Fail policy**: Fail-open

Addresses dogfood report finding M1: "agent bypassed `/diamond-progress` by hand-editing diamonds/active.yml." This hook logs every direct edit to diamond state files in `.claude/state/diamond-state-audit.jsonl`. The `stop-check.sh` hook surfaces the count at session end as a reminder that `/diamond-progress` is the idiomatic path.

This is **not** a guardrail — it does NOT block. The hook cannot reliably distinguish between edits from `/diamond-progress` (legitimate) and direct agent edits (bypass). Observability creates traceability without false positives. The agent learns from seeing the audit count, not from being blocked.

### canvas-schema-check.sh (PostToolUse — schema feedback, v0.250.0)
**Triggers**: PostToolUse on Edit/Write/MultiEdit (filtered to `.claude/canvas/*.yml` and `.claude/diamonds/*.yml`)
**Type**: `command` (10s timeout)
**Tier**: Feedback (tells the agent; does not block the write, which has already happened)
**Fail policy**: Fail-open, spoken: without PyYAML/jsonschema it says once per session that it could not run

Runs `validate_canvas.py`'s schema functions on the file just written (`scripts/canvas_write_check.py`) and, if it fails, returns the errors as `decision: block` so the agent sees them in the same turn. Found by E2E run 19: an invalid `privacy-assessment.yml` stood after the post-write nudge had already said "validate with validate_canvas.py". A reminder to run a check is not the check.

**v0.253.2: `bash-state-guard.sh`** (PreToolUse and PostToolUse on Bash). Before: refuses a shell command that visibly writes `.claude/diamonds/active.yml` (the scale-lock gate only judges Edit and Write), except Mycelium's own `derive_closing_path.py`, and snapshots the file. After: schema-checks every canvas or diamonds file the command changed and judges a changed diamonds file against the snapshot with the scale locks (`scale_locks.violations_between`), telling the agent. Fails open on a crash and says so, because it runs before every shell command. Found by E2E run 24, which wrote the privacy canvas through a shell command.

**v0.252.2.** `preflight.sh` passes the prompt payload to `next_item.py --prompt-line`, which, when the prompt looks like the user's answer to the open next item, names the item and the `advisory_ledger.py rule` command that records it. Nothing of the prompt is stored.

**v0.252.0 additions.** `preflight.sh` prints `MYCELIUM EXPOSURE STATE` (from `scale_locks.py --exposure-line`) when a delivering diamond is open and not ready for real people: once per sitting, and on prompts about going live. The exposure gate sees only the agent's own deploy commands; this reaches the agent when someone else deploys. `stop-check.sh` shows the session counts once per sitting.

**v0.250.0 additions to existing hooks.** `diamond-state-audit.sh` also runs `scripts/diamond_rulings.py`, which records the machine time a diamond's phase or ruling changed, so `next_item.py` judges "evidence since the last assessment" on one clock. `preflight.sh` prints the next item once per session, beside the first request, when it has gone unanswered for three sessions (`next_item.py --prompt-line`); silent otherwise and with `MYCELIUM_NEXT_ITEM=off`.

### reflexion-gate.sh (PostToolUseFailure — filtered NUDGE)
**Triggers**: PostToolUseFailure on Bash
**Type**: `command` (10s timeout)
**Tier**: NUDGE (filtered to project-relevant failures only)
**Fail policy**: Fail-open

Replaced the inline reflexion prompt in v0.8.2. Filters out failures that are not project-relevant (cwd outside `$CLAUDE_PROJECT_DIR`, environmental introspection commands like `which`/`pwd`/`hostname`). Addresses dogfood G4 and M4: "Reflexion fired on a failure unrelated to the project, demanded writing to the wrong corrections file."

When the failure IS project-relevant, emits the reflexion prompt with two-memory-system guidance: project-relevant mistakes go in `corrections.md`, agent-user learnings go in auto-memory, environmental failures don't go anywhere.

---

## Fail-Closed vs Fail-Open Policy (v0.9.0)

Different hooks have different failure semantics. The choice is deliberate.

**Fail-closed** (block on failure) — used for **security and scope enforcement**:
- `gate.sh` — exit 2 on preflight stamp corruption
- `scope-gate.sh` — deny via JSON when state file is corrupt; exit 2 on script failure

**Rationale**: a silently disabled enforcement hook is worse than no hook. If `gate.sh` crashes, secret detection is gone. If `scope-gate.sh` cannot read state, scope enforcement is gone. These hooks must announce their failure by blocking the operation.

**Fail-open** (allow on failure) — used for **observability and nudging**:
- `post-write-nudge.sh`, `change-log.sh`, `diamond-state-audit.sh`, `reflexion-gate.sh`, `stop-check.sh`, `session-start.sh`, `next-action-check.sh` (fail-open on a missing transcript by design: a Stop hook that blocked on its own read errors would trap the session; the validator checks its wiring instead)

**Rationale**: an audit log failure should never block a code change. The cost of missing a nudge is small; the cost of blocking a legitimate edit because logging broke is large.

---

## Dependency Philosophy (v0.9.0)

**All Mycelium hooks use Python stdlib only.** No PyYAML, no jsonschema, no Ruby, no jq. The `python3` binary is the only runtime dependency, and it's already a Mycelium baseline.

Why: hooks fire on every code edit. Requiring users to `pip install` would create a silent-failure footgun on fresh clones. Stdlib-only means zero setup after `npx degit haabe/mycelium`.

**Runtime state files are JSON** (not YAML), specifically so hooks can parse them with `json.load()` from stdlib. Canvas files (which hooks don't read at runtime) stay YAML for human editing. CI validation handles canvas YAML with PyYAML (via `requirements-ci.txt`).

See `../state/README.md` for the full data format philosophy.

---

## Hook Inventory Summary (v0.9.0)

| Hook | Event | Tier | Fail policy |
|---|---|---|---|
| `gate.sh` | PreToolUse Edit/Write/MultiEdit | BLOCK | **Fail-closed** |
| `scope-gate.sh` | PreToolUse Edit/Write/MultiEdit | BLOCK (when active) | **Fail-closed** |
| `post-write-nudge.sh` | PostToolUse Edit/Write/MultiEdit | NUDGE | Fail-open |
| `change-log.sh` | PostToolUse Edit/Write/MultiEdit | Observability | Fail-open |
| `diamond-state-audit.sh` | PostToolUse Edit/Write/MultiEdit | Observability | Fail-open |
| `canvas-schema-check.sh` | PostToolUse Edit/Write/MultiEdit | Feedback | Fail-open, spoken |
| `reflexion-gate.sh` | PostToolUseFailure Bash | NUDGE (filtered) | Fail-open |
| `stop-check.sh` | Stop | NUDGE + warning | Fail-open |
| `session-start.sh` | SessionStart startup/resume | NUDGE | Fail-open |
| `preflight.sh` | UserPromptSubmit (also called by gate.sh) | Advisory | N/A |

---

## References

- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html) — the "computational vs inferential" distinction this whole architecture is built around
- [Daniel Bentes — BDSK comparison feedback](../../../CONTRIBUTORS.md) — the inspiration for scope enforcement and trace audit patterns
- `../state/README.md` — runtime state philosophy
- `../tests/validate-template.sh` — the structural integrity validator (a different kind of computational enforcement)

## One reading of the tool call (0.196.0)

The six blocking hooks (`gate.sh`, `discovery-gate.sh`, `brownfield-gate.sh`, `scope-gate.sh`,
`framework-guard.sh`, `autonomous-evidence-guard.sh`) read the tool call through
`scripts/_hook_input.py` (Python helpers import it; shell gates source
`scripts/_hook_input_read.sh`, which calls it). It resolves every path key to its real location
inside the project (`..`, symlinks, the other case on a case-insensitive disk), includes MultiEdit
`edits[]` in the written content, scans a Bash command for write targets across newlines, `cd`,
`./`, `$PWD`, absolute paths and the writers a regex tends to forget (perl -i, dd of=, ed, awk -i
inplace, rsync, python open()), refuses a tool call whose fields are not the documented type instead
of crashing into an allow, and turns a write to guard state into an `ask`. All six are registered
on `Write|Edit|MultiEdit|NotebookEdit`, `Bash` and the filesystem MCP tools in all three manifests.
`tests/bash/test_hooks_adversarial.sh` replays the 2026-09-11 blind pass's demonstrated bypasses and
expects every one to block or ask.

