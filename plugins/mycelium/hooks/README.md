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
- G-S1: Secret detection. Since v0.323.0: a scan of what a `git commit` or `git push` would take (`scripts/commit_scan.py`, gitleaks when installed, Mycelium's own short list otherwise), and a regex scan of the text of every shell command. A file write is no longer scanned

**Logs (v0.204.0)**: every block on the stamp or hash path appends one JSON line (`ts`, `hook`, `reason` = `stale-stamp` | `corrections-hash`, `session_id`) to `.claude/state/gate-block-log.jsonl`, gitignored with the rest of `state/`. `scripts/check_hook_delivery.py` reports blocks per session beside hook delivery, so "does the gate cost more than it catches" (opp-072) is a count.

**Secrets are stopped at the commit and the push (v0.323.0)**, by the maintainer's rulings of 2026-10-12 ("Don't let passwords into the repo"; "using established scanners are the way to go"; "Stop refusing writes"; "Fall back, and say so"; "Agent must ask you first").
- `gate.sh` no longer scans a file write. For a Bash call it scans the command's text with the short list in `scripts/_secret_patterns.sh` (a key on a command line ends up in logs), and when the command runs `git commit` or `git push` it calls `scripts/commit_scan.py --pre`, which scans what the commit would take or what the push would send and answers with a deny, a once-a-session note that no scanner is installed, or nothing.
- `bash-state-guard.sh` notes the commit pointer and the length of HEAD's reflog before each shell command; afterwards `commit_scan.made_commits` reads the new reflog entries (commit, amend, cherry-pick, revert, rebase; a pull, checkout or reset is arrival, not making) and those commits are scanned. A finding is said to the person and blocks the agent's turn; the commit is not rewritten.
- The scanner is gitleaks (`gitleaks git --pre-commit --staged`, `--log-opts`), run with `--redact` and its own exit code for "found" so a scan error stays distinct. With none on PATH, `scripts/_secret_grep.sh` runs the short list over the lines a diff or a log adds.
- Where the repository's own pre-commit hook already runs gitleaks, a commit that honours hooks is not scanned twice; one with `--no-verify` or `-n` is scanned here.
- `.gitleaksignore` and `.gitleaks.toml` are in `_hook_input.GUARD_STATE_REL`, and a write that adds a `gitleaks:allow` comment asks the person too. `guard-state-gate.sh`'s cheap exit has an arm for them.
- `scripts/install_git_secret_hook.py`, offered by `/mycelium:setup` and never run unasked, writes a pre-commit hook for commits made by hand; it never overwrites one that is there.

**A scan that cannot run refuses (v0.319.1; since v0.323.0 the command, the commit or the push)**: each pattern is one `grep -E`, and grep has three answers: a line matched, none did, or it could not run the pattern at all (exit status 2 or more: a pattern this grep rejects, no `grep` on `PATH`). Until 0.319.1 the last two were read as one, with grep's own complaint discarded, so a scan that never ran passed every write, credentials included, and said nothing. Now a scan error is a refusal of its own, worded apart from the "potential secret" one: it says the secret scan could not run, grep's exit status, which pattern, and grep's own first line, and that nothing was detected in the content. It goes to the denial ledger like any refusal. On a machine whose grep cannot run these patterns, every write of non-empty content outside `.claude/` is therefore refused until the grep is fixed; before, that machine had no secret scan and no way to know it. Tests, through the hook with a substituted `PATH`: `tests/python/test_gate_secret_scan.py`.

**Excludes**: `.claude/` directory edits (always allowed)
**Gates every real path inside the project that is not under `.claude/`** (until 0.196.0 a directory list; `config.py`, `source/` and `Src/` all fell outside it, adversarial pass 2026-09-11). Reads the tool call through `scripts/_hook_input.py`: every path key, resolved to its real location, MultiEdit edits included, Bash write targets scanned; a write to guard state (`upstream.json`, `manifest.yml`, `active-execution.json`, the discovery, delivery, brownfield and scale-lock ack files) returns `ask` so the person decides, with `MYCELIUM_GUARD_STATE_EDIT=1` in the human's own shell as the setup-time override.

**Sibling PreToolUse hooks (same Write/Edit/MultiEdit matcher, run alongside `gate.sh`):**
- **`discovery-gate.sh`** (v0.56.0) — blocks scaffolding NEW source files in a project where discovery has never been engaged (no diamond in `active.yml`, no populated `purpose.yml`). The teeth for the deliver-framed-opening routing gap: router-discipline prose alone did not stop "build me X" first messages from producing code on an empty canvas (founder dogfood 2026-06-08/09; mechanically reproduced by roadmap auto-dogfood 2026-07-02). Deliberately narrow to avoid a friction wall: new files on Write; since v0.291.0 also edits to product code once discovery is engaged (outside declared `prototype_paths`, which are free; brownfield projects with no discovery stay untouched),  source/infra shapes only, and a one-time on-the-record escape hatch (`.claude/state/discovery-skip-ack`, written after the USER explicitly declines discovery; since v0.307.6 it lifts the cold-project gate only, so once discovery starts the delivery stage applies, and an ack's scope and the declared prototypes are judged against every file a command writes). Block message routes to `/mycelium:start`. Tests: `tests/bash/test_discovery_gate.sh` (13 asserts, scenario-per-guardpost).
  **Second stage, the delivery gate (v0.245.0):** once discovery IS engaged, a new source file is blocked until an open L3, L4 or L5 diamond **whose entry-lock chain holds and which is in Develop or Deliver with Four Risks and Privacy passed** (phase follows the work, v0.246.0) (a purpose, a desired outcome, a target opportunity with evidence above it; `scripts/scale_locks.py --delivery-state`), or the user records `.claude/state/delivery-skip-ack` (guard state: the agent cannot write it without asking). Any open L3 was not enough, because `/mycelium:start` leaves only a purpose, so an L3 opened after it builds on a guess; an end-to-end dogfood run shipped a release under an L0 in discover. The block names what is missing. Without PyYAML the locks cannot be read and the gate allows; `preflight.sh` then says so on every prompt, and otherwise prints the `MYCELIUM DELIVERY STATE` pre-warning.
- **`exposure-gate.sh`** (v0.246.0, Bash) — blocks a command that puts the work in front of real people unless an exposure record covers it now (`scale_locks.py --exposure-hook`): one current record allows, several ask the person which, none refuses and says why each is not current (v0.295.0; since v0.306.0 with no phase fallback). A release is a listed deploy (a host CLI's deploy verb, a package publish, a remote shell or copy that pulls, restarts or syncs onto a host, a tunnel) or, since v0.307.3 (DL-1370), a command named for one: a tool's `deploy`/`publish` subcommand, a package script (`npm run deploy`, `make deploy`) or a script named for it (`./deploy.sh`), at a command's start. Found by E2E run 10: an SMS app holding phone numbers and link tokens went live under an L3 in define with every gate pending. Other commands exit before python (`git push origin`, `ssh host tail`, local rsync, `docker compose up`, `grep deploy` are not deploys); a project with no diamonds at all is not judged (since v0.318.0 a project with no `diamonds/active.yml` is answered before anything needs PyYAML, so a machine without it no longer refuses releases in projects that never used Mycelium), and since v0.307.3 one whose diamonds have all completed is; a deploy the USER runs is outside any hook, so operating contract rule 14 and `/mycelium:preflight` carry it. Escape hatch: `delivery-skip-ack`. Logs blocks to `.claude/state/exposure-gate-fires.jsonl`. Tests: `tests/bash/test_exposure_gate.sh`, `tests/python/test_scale_locks.py`.
- **`guard-state-gate.sh`** (v0.281.0, PreToolUse on writes, shell commands and the filesystem MCP writes) — blocks. The files that switch a gate off (`_hook_input.GUARD_STATE_REL`: the four ack files, `upstream.json`, `manifest.yml`, `active-execution.json`) are the user's to write, in every project: a write asks the human in `default`, `acceptEdits` and `plan`, and is REFUSED in any mode where nobody is asked (permissions bypassed, an automated mode), with the words to write it yourself; an absent mode (another runtime) keeps the ask. **Since 0.318.0 removing `.claude`, `.claude/canvas` or `.claude/diamonds`** (`rm`, `rmdir`, `mv`, `git rm`, or an MCP move whose source is one of them; `_hook_input.MARKER_DIRS_REL`) is judged the same way, because with neither folder every hook exits at once and that is the widest off-switch there is. (From 0.318.0 to 0.318.2 only the Python helper judged it: this hook's cheap exit passed the removal before the helper saw it. Fixed in 0.318.3, with tests that run the hook.) Writing or copying into them, or deleting one file inside, is not asked. Before 0.281.0 the three guards that asked were each conditional (autonomous runs, a scope, the framework repo), so an ordinary project had no guard on the ack files at all. Found by the E2E relay on 0.280.0: under bypassed permissions the builder wrote its own `scale-lock-ack` ("My judgment call, my override") and opened an L4 past its lock. `MYCELIUM_GUARD_STATE_EDIT=1` in your own shell skips it for setup. Tests: `tests/python/test_guard_state_everywhere.py`.
- **`exposure-change.sh`** (v0.279.0, PostToolUse on writes; also on MCP filesystem writes since v0.289.0, in its own group so the `file_path` hooks are not fed MCP input) — advisory. Right after a write to `.claude/diamonds/active.yml` that takes the work from "may meet its audience" to "nothing may meet real people", tells the agent so, with what is missing, as additionalContext (`scale_locks.py --exposure-change`). The prompt-time line in `preflight.sh` sets the baseline in `.claude/state/exposure-last`; the change is said once. Found by E2E rung L4-open on 0.278.0: one turn completed the L3 as handed to a new L4 still in discover, then called the founder's public launch post "ready to post". Exit 0 always. Tests: `tests/python/test_scale_locks.py`.
- **`gate-override-check.sh`** (v0.316.0, PostToolUse on every tool the gates cover: writes, Bash, MCP filesystem writes) — advisory, says when a refusal did not hold. Claude Code 2.1.287 shipped Mods, and a mod's `tool.check` "can also approve a call that a `PreToolUse` hook outside managed settings blocked"; every Mycelium gate is such a hook. Each gate now writes the refused call's `tool_use_id` to a denial ledger (`.claude/state/denied-calls.jsonl`, through `scripts/_hook_fire_log.sh`: a `blocked*` fire, `hi_deny`, or `mycelium_note_refusal` on a helper's verdict). A call that then RUNS with a refused id was overridden by another extension: this hook logs it (`gate-override-fires.jsonl`, outcome `overridden`) and tells the person (`systemMessage`) and the agent (`additionalContext`) that the gate was overruled, so no record or report says it held. It cannot undo the call or name the mod: PostToolUse input does not say who approved. An `ask` the person answered is not an override; asks never reach the ledger. Registered for Claude Code only: Codex and Cursor have no mods. Organisations that need the gates to hold can set `allowManagedModsOnly` or register the hooks in managed settings. `tests/python/test_gate_override_check.py` also holds every refusal site in a PreToolUse hook to one of the three recorders, with a positive control.
- **`scale-lock-gate.sh`** (v0.245.0) — blocks a write to `.claude/diamonds/active.yml` that OPENS a diamond (a new id, a rescaled one, or one moved back into the active list) whose parent has not yet established what it builds on: L1 on a purpose, L2 on a strategy (an L1 diamond, a North Star, the landscape) and a desired outcome, L3 on a target opportunity with evidence in an L2 diamond, L4 on an L3 at medium confidence, L5 on launch data; since v0.247.0 it also refuses a new diamond written past discover, and since v0.248.0 a FORWARD phase move whose transitions lack their matrix gates or a `progression_history` entry (`engine/diamond-rules.md`, Entry locks; one implementation in `scripts/scale_locks.py`). The founder's dependency tree, which three releases had undone by opening every door "whether or not the parent has progressed". Narrow: a diamond already open at its scale is never re-judged on edit (`scale_locks.py --check` reports it, and the delivery gate reads its chain before new code), a Bash write to the file is not parsed (it cannot unlock code: the delivery gate re-reads the chain), and any other write exits before python starts (case-insensitively). An unparseable proposed file and a crash of the checker both refuse. Escape hatch: `<id> <scale> <YYYY-MM-DD> <the user's own words>` in `.claude/state/scale-lock-ack`, guard state, so only the user can grant it. Logs blocks to `.claude/state/scale-lock-fires.jsonl`. Tests: `tests/bash/test_scale_lock_gate.sh`, `tests/python/test_scale_locks.py`.
- **`scope-gate.sh`** — the scope hold: keeps the agent's writes inside the folders an open delivery cycle named, and asks the person about a write outside them (its section below).
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
- **`lesson-triggers.sh`** (v0.327.0, wired on `Bash`, `Write|Edit|MultiEdit` and the web tools) — OFF unless `MYCELIUM_LESSON_TRIGGERS=on`. Reads the project's `.claude/memory/lesson-triggers.yml`, where each entry is a lesson already on record as one rule line with a `match` on the call, and shows the matching rule lines at the call (at most three); an entry with `refuse: true` refuses the call, with its rule line as the reason. Why a hook: on the dogfood project 86 of 96 corrections in a month repeated a lesson already written down, and a replay of them found that showing the lesson at the call reached the most. Fails open (`continue`); refusals go in the denial ledger. Its fire log names the tool and the ids of the lessons shown or refused, never the call or the rule line (v0.327.1). Reads Claude Code's tool names only, so on Codex and Cursor it stays silent. Matching, privacy and `--check` are in `scripts/lesson_triggers.py`.
- **`shell-safety-guard.sh`** (v0.81.0, wired on `Bash`) — warns on `$?` after a pipeline, backticks, `grep` gating an `&&` chain, and a canvas write followed by an ungated `git commit`. Since v0.326.0 it REFUSES two shapes the warning was measured not to stop: a scripted multi-file edit that can half-apply without `safe_replace.py` (v0.223.0's rule 5), and a pipeline ending in a filter joined by `&&` to `git commit` or `git push` (rule 6). Each refusal names a one-line rewrite. See `scripts/shell_safety_guard.py`.
- **`correction-attribution-guard.sh`** (PreToolUse on Write/Edit/MultiEdit/NotebookEdit and Bash, 10s) — WARNS, never blocks. Fires when a new entry in `.claude/memory/corrections.md` does not name who caught the mistake. Fires are logged since v0.236.0.
- **`discovery-trigger-guard.sh`** (UserPromptSubmit, 10s) — ADVISES, never blocks. Fires when the person states something whose truth depends on other people's wants or behaviour ("users want X", "they'd pay for it"). It never proposes a study: the first response it asks for is to type the claim, which costs seconds. Same advisory shape as `absence-claim-guard.sh`.

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
- If an open L4 is in develop or deliver (read from the YAML since v0.289.0; before, the substrings "L4" and "deliver" anywhere in the file) but `threat-model.yml` is empty -> GUARDRAIL WARNING with `/threat-model` suggestion
- If Downe's 15 principles all "not-assessed" -> GUARDRAIL WARNING with `/service-check` suggestion
- If BVSSH or DORA checks are overdue (>30 days) -> FEEDBACK LOOP WARNING with skill suggestion
- Corrections and decisions count for session summary

Returns warnings via `additionalContext` (does not block). This is the "hybrid" pattern: hook detects the condition, injects a message that tells Claude to run the appropriate skill.

- **`ci-signal.sh`** (v0.85.0, on **Stop** and on **SessionStart** with `--session-start`) — reports ONCE when the workflow for the currently checked-out commit has failed. Closes a hole that let the dogfood workflow stay red for **thirteen consecutive pushes**: the flow was one-way — local push, CI runs, verdict lives on GitHub and never returns — and none of the five hook points looked outward. A pull request forces you to look; `main` does not ask. **Tracks no pushes by design**: GitHub already knows, so it matches the newest run's `headSha` against local HEAD and speaks only about the commit actually checked out. That match is load-bearing — reading `gh run list --limit 1` without it reports the PREVIOUS commit's run, which is how a failed push got reported as "CI: success" the same day. Stop is the warm catch (one session, thirteen pushes, needs to hear it mid-session); SessionStart is the cold catch and bypasses the dedupe, because a new session is a new agent with no memory of what the last one was told. Silent on green, in-progress, another commit's failure, detached HEAD, missing `gh`, no auth, no network, no workflows. One network call per 90s, one report per run. Tests: `tests/python/test_ci_signal.py` (22 asserts; the rate-limit test counts `gh` invocations directly, and was verified to fail with the guard removed).

### Layer 4b: Stop (`next-action-check.sh`) — a framework turn ends on one next action
**Triggers**: When Claude finishes responding, after `stop-check.sh`
**Type**: `command` (5s timeout)
**Check**: if a `mycelium:*` skill ran in this turn (a `Skill` tool_use in the transcript) and the closing message (`last_assistant_message`, transcript fallback) has no line beginning `Next:`, returns `{"decision":"block","reason":...}` so the agent ends on exactly one next action. Since 0.311.0 it also blocks, once, a `Next:` line that carries no `(per: <source>)` (contract rule 4: as prose the citation appeared in 3 of 12 dogfood sessions, measured twice), logged as outcome `blocked-no-per`; and a turn started by a `/mycelium:` slash command the person typed counts as a skill run (meta transcript entries no longer start a new turn). Silent on turns with no framework skill run. Honours `stop_hook_active`; reports via `systemMessage` when it cannot read its input or the transcript (Cursor, Codex) rather than failing silently. Person override `MYCELIUM_NEXT_ACTION_CHECK=off`. Downe P10; operating-contract rule 12; dogfood opp-006/sol-006b. Gate blocks (PreToolUse denies) are not yet in scope.

- **`next-item-repeat.sh`** (v0.188.0, Stop, 5s) — repeats the session's NEXT ITEM (the one item `session-start.sh` emitted and recorded in `.claude/state/next-item.json`) ONCE, at the first Stop where nothing has followed it. Never blocks.

### Layer 5: SessionStart (`contract-part.sh`, `session-start.sh`)
**Triggers**: When a session starts, resumes, clears or forks; the contract parts also after compaction
**Matchers**: `startup|resume|clear|compact|fork` (contract parts), `startup|resume|clear|fork` (the rest)

- **`contract-part.sh 1` to `4`** (10 s each, v0.310.16) deliver `engine/agent-operating-contract.md`
  in parts. Claude Code caps one hook's `additionalContext` at 10,000 characters and shows only a
  2,000-character preview of anything longer, so `scripts/contract_parts.py` splits the contract
  between its sections into parts that each fit, numbers them (the handlers run in parallel), and
  replaces the literal `${CLAUDE_PLUGIN_ROOT}` with the real plugin path, which part 1 also states.
  `contract_parts.py --check` (validator Check 47, `tests/python/test_contract_parts.py`) fails when
  the contract would need more parts than there are handlers.
- **`session-start.sh --fast`** (60 s) returns the feedback-loop reminders as `additionalContext`,
  capped under 10,000 characters with a visible note when cut; **`--async`** runs the heavier checks
  in the background and their result is delivered at the next prompt. Part of the four-speed feedback
  loop system (see `../engine/feedback-loops.md`).
- **`ci-signal.sh --session-start`** reports a failed CI run on the current branch (see PRIVACY.md).

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

### scope-gate.sh (PreToolUse — ASK outside the named folders)
**Triggers**: PreToolUse on Write/Edit/MultiEdit/NotebookEdit, on Bash, and on `mcp__filesystem__` write_file/edit_file/move_file
**Type**: `command` (30s timeout)
**Tier**: ASK for a write outside the folders, or one that names or changes them; BLOCK where nobody can be asked, for a commitment to build with nothing said, and while an old state file exists
**Fail policy**: **Fail-closed** (a diamonds file that cannot be read refuses product writes with the reason; so does a helper that cannot run, PyYAML missing included)

**Where the folders live (v0.324.0).** On the delivery cycle's own record: an L4 in `.claude/diamonds/active.yml` carries `in_scope_paths`, a list of folders, files or globs (`app/billing/`, `tests/billing/**`). An empty list is "no hold for this one". Absent is "nobody has decided". The hold is on for a cycle that has committed to build and has not closed; with several such cycles a write is inside when it is inside any of their lists. Nothing is stored beside the record. Mirrors BDSK's `check-scope.sh` pattern. Delegates to `${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py` (Python stdlib plus PyYAML to read the record).

**What it does on a write.**
- A write under `.claude/` is never held.
- A write outside every list in force is put to the person, with the file named by its path from the project's top folder. A yes lets that one write through. Where nobody can be asked (a permission mode that asks no one, or Codex) it is refused, and the refusal says the two ways a person can allow it.
- A write to the diamonds file that names, changes, empties or removes a cycle's folders is put to the person the same way: where the agent may write is theirs to say.
- A write to the diamonds file that would commit a delivery cycle to build with no `in_scope_paths` at all is refused. A cycle that had committed before 0.324.0 is left as it is, and session start names it.
- A close that moves the cycle to `completed_diamonds` with its folders as they were is not a question; the hold simply ends.

**What it cannot see.** A command that writes files itself (a scaffolder, a clone) names no target a hook can read. The same limit as the build gate. If such a command changes the folders themselves, `bash-state-guard.sh` puts the diamonds file back afterwards and tells the person (its section below). That is a check on drift and not a sandbox: a process the command leaves running, or a script written to rewrite Mycelium's copy as well, gets past it.

**The old state file.** Until 0.324.0 the folders were read from `.claude/state/active-execution.json`. No skill, script or hook that Mycelium ships wrote that file, so in a plugin install the hold was never on (found by a blind reader of the installed plugin, dogfood 2026-10-11). It is no longer read. So that a hold someone set by hand is not dropped in silence, product writes are refused while the file exists, and the refusal says what to do: move its folders to the delivery cycle's `in_scope_paths` and delete the file. It stays one of the files that are the person's to write, so the agent's write or removal of it asks. `out_of_scope_paths`, the old file's list of exceptions, has no counterpart on the record.

**Cost.** With no folder named anywhere the hook leaves before starting Python (about 25 ms measured on one Mac). With a hold on it reads the diamonds file on each write: about 80 ms on a small project and about 280 ms on a 6,000-line diamonds file.

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

### read-log.sh (PostToolUse — observability)
**Triggers**: PostToolUse on Read and Bash (Bash reads inferred since v0.143.0)
**Type**: `command` (3s timeout)
**Fail policy**: Fail-open

Appends one JSONL line per file the agent opened to `.claude/state/read-log.jsonl`. This is the capture half of the citation-fidelity instrument the system card describes (§5): a citation to a file that was never read shows up against this log. Does not block or advise.

### canvas-schema-check.sh (PostToolUse — schema feedback, v0.250.0)
**Triggers**: PostToolUse on Edit/Write/MultiEdit (filtered to `.claude/canvas/*.yml` and `.claude/diamonds/*.yml`)
**Type**: `command` (10s timeout)
**Tier**: Feedback (tells the agent; does not block the write, which has already happened)
**Fail policy**: Fail-open, spoken: without PyYAML/jsonschema it says once per session that it could not run

Runs `validate_canvas.py`'s schema functions on the file just written (`scripts/canvas_write_check.py`) and, if it fails, returns the errors as `decision: block` so the agent sees them in the same turn. Found by E2E run 19: an invalid `privacy-assessment.yml` stood after the post-write nudge had already said "validate with validate_canvas.py". A reminder to run a check is not the check.

**v0.253.2: `bash-state-guard.sh`** (PreToolUse and PostToolUse on Bash). Before: refuses a shell command that visibly writes `.claude/diamonds/active.yml` (the scale-lock gate only judges Edit and Write), except Mycelium's own `derive_closing_path.py`, and snapshots the file. After: schema-checks every canvas or diamonds file the command changed and judges a changed diamonds file against the snapshot with the scale locks (`scale_locks.violations_between`), telling the agent. Fails open on a crash and says so, because it runs before every shell command. Found by E2E run 24, which wrote the privacy canvas through a shell command. **Since 0.321.1 it also guards the files that switch a stop off** (`_hook_input.GUARD_STATE_REL`): `guard-state-gate.sh` can only ask about a write target it can read, and a shell write through a variable or a command substitution went through unasked. Before: copies each of those files that exists (per tool call, under `.claude/state/bash-guard/guard-state/`) and notes which the command writes visibly, since the person is asked about those. After: a file the command created, changed or removed without the person being asked is put back as it was, and the person (`systemMessage`) and the agent are told. Until 0.324.0 this was the only thing the hook undid; it never restores code or canvas. **Since 0.324.0 it also puts the diamonds file back when a shell command changed where a delivery cycle may write** (`in_scope_paths`, the scope hold's folders). `scope-gate.sh` asks about a write to that field and the before half refuses a command that visibly writes the file, but a script whose command line names no file could delete the record, take the folders off it or empty the list, and afterwards nothing was said and the hold was gone (found by trying it while the hold was being built; the fourteen steps it had been held to did not cover it). Before: a copy of the diamonds file is kept with the call's snapshot. After: what each delivery cycle names is compared (`scope_check.changed_between`), and if the command changed it the whole file is put back as that copy, and the person and the agent are told (maintainer's ruling 2026-10-13, "Put it back, tell me"; anything else the command changed in that file is undone with it). A write that came through the edit tools while the command ran is not the command's: `diamond-state-audit.sh` calls `bash_state_guard.py edited`, which refreshes the copy in every snapshot still open. That hook is registered on Write, Edit and MultiEdit; a write to the diamonds file through another tool that lands while a shell command is running is taken for the command's, put back, and said. Said and left: a record the command created where there was none. Left alone: the person's own terminal, `MYCELIUM_GUARD_STATE_EDIT=1`, and Mycelium's `upgrade.sh` run on its own. The after half is also registered on `PostToolUseFailure` (Claude Code, Cursor), because a command that writes the file and then fails is otherwise never compared. Not covered: a write that happens after the command has returned (a background job). **Since 0.325.0 any change a shell command makes to the diamonds file is put back, not only the folders.** Dogfood 2026-10-14: `python3 newbar.py values.yml`, a script that opened the file itself, replaced a whole definition of done; the scale locks found nothing to object to (a changed bar breaks no lock) and the change stood, unsaid. Minutes later a heredoc appending to another file was refused because its text mentioned the path. So the file is judged, not the command. After: if the command changed the file at all, it is put back as the copy, the command's version is kept under `.claude/state/bash-guard/put-back/` and named, and the person and the agent are told which diamonds it touched (by the `- id:` entry each changed line falls in) and what the scale locks would have said. Before: only a command whose write target IS the file is refused (a redirect, `sed -i`, `tee`, `mv` naming it); the guess that refused any command naming the file beside an unseen write is gone. Not put back: Mycelium's own writers (`derive_closing_path.py`, `migrate_phase.py`) run on their own, when the script run is the plugin's own copy (a path inside its `scripts/` folder, `${CLAUDE_PLUGIN_ROOT}` read as that folder's parent; by name alone a script the agent wrote would pass); `MYCELIUM_GUARD_STATE_EDIT=1`; git leaving the file as it is committed at HEAD (a pull, a checkout, a reset, a stash) or stopped mid-merge, mid-rebase, mid-cherry-pick or mid-revert, unless the command itself made a commit that changed the file. Put back although the person may want it: `git stash pop` of their own changes (the popped version is the one kept). Not covered: a file committed by one command and restored from HEAD by the next. **Since 0.325.1 Mycelium's own write while a command runs is not the command's.** Session start runs `derive_closing_path.py --all --write` in the background, and on 0.325.0 a read-only `git log` running at the same time was told it had changed the file, which was put back while the script went on writing (dogfood 2026-10-15). Now the script applies its own edit to the copy in every snapshot still open (`bash_state_guard.own_writer_writes`), before it writes the file, so the comparison sees only what the command did; a command that also changed the file is put back as before, to a version that keeps the script's change. The edit is applied rather than the file copied, so running the script after a change of the command's own does not pass that change off as the script's.

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

**What it logs (v0.318.0).** One line per firing in `.claude/state/reflexion-log.jsonl`, written by `scripts/reflexion_record.py` from the payload on stdin: time, exit code, the program's name and, for a documented non-failure, why. Never the command or its error output, unless the user sets `MYCELIUM_LEDGER_TRIGGER=on`, and then masked by `scripts/_secret_mask.py`. Until 0.318.0 it kept 160 characters of the command and 200 of the error output, unmasked (Anthropic directory review of v0.317.4); `session-start.sh` strips those fields from older lines (`reflexion_record.py scrub`). Tests: `tests/python/test_reflexion_record.py`.

### A Mycelium switch in a Claude Code settings file is the person's to set (v0.322.6)

`scripts/settings_switches.py` reads a settings text and returns the Mycelium switches in it: every `MYCELIUM_*` variable, `CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_ROOT` in `env`, `disableAllHooks: true`, and the plugin set to `false` in `enabledPlugins`. Text that is not a JSON object is read by its words. Two callers. `guard-state-gate.sh` (through `_hook_input._settings_check`) works out the text a file tool would leave in `.claude/settings.json`, `.claude/settings.local.json` or `~/.claude/settings.json`; a switch that is new, or whose value changed, asks the person, and is refused where nobody is asked (the same modes and runtimes as the other guard-state files); a result it cannot work out asks too. `bash-state-guard.sh` notes the switches before a shell command (their names and values in the snapshot index, never the file) and compares afterwards: a new one is taken out again with the rest of the file kept, and the person and the agent are told; the plugin switched off in `enabledPlugins` is reported and left, because Claude Code's own plugin commands write it. Whether the person's override (`MYCELIUM_GUARD_STATE_EDIT`) lifts the comparison is decided by its value BEFORE the command, noted in the same index: Claude Code re-reads the `env` block mid-session, so read afterwards the override could be the one the command just wrote. `guard-state-gate.sh` has a cheap exit in front of its helper; the settings files are named in it, and a new guarded file needs an arm there.

### A diamonds file that cannot be read is a refusal (v0.322.5)

`scripts/_hook_input.py` answers `--discovery-state` with **4** when `.claude/diamonds/active.yml` is there and cannot be read (git conflict markers, invalid YAML, not a mapping, `active_diamonds` not a list, or emptied where `diamond-rulings.json` shows the project had diamonds), and `--diamonds-unreadable-why` prints the reason. `discovery-gate.sh` and `exposure-gate.sh` refuse on it with that reason; `brownfield-gate.sh` stands aside so there is one refusal; `preflight.sh` tells the agent at the prompt (always for conflict markers, which one grep finds; for the other shapes only once the file no longer looks engaged). Until 0.322.5 a YAML error escaped the engagement check, whose crash read as "not engaged". **A gate that reads the diamonds file treats "cannot read" as its own answer, never as "nothing there".** `exposure-gate.sh`'s word filter runs over the whole hook input, the project's path included, before the checker starts: a release command with none of its words never reaches the checker, which is how `vercel --prod` was missed until 0.322.5. A new kind of release needs a word there and a sample in `tests/python/test_an_unreadable_diamonds_file_does_not_open_the_gates.py`.

### Every hook: its Python imports nothing from the project (v0.322.4)

`python3 -c` and `python3 -` put the current directory first on the import path, and a hook's current directory is the project. Until 0.322.4 a project file named like a module a hook imports (`json.py`, `yaml.py`, `re.py`) was loaded in its place: 19 of the 56 registered hook entries did so on 0.322.3, with the plugin root set. `scripts/_hook_prelude.sh` now exports `PYTHONSAFEPATH=1` (Python 3.11 and later) and defines `python3`, `python` and `_mycelium_py`, which hand inline code to `scripts/_safe_c.py` (every version: a file gets its own folder on the path, not the current one). **Write inline Python as `python3 -c` or `python3 -`, never through an interpreter path in a variable at command position; where the interpreter is in a variable, call `_mycelium_py "$py" -c ...`.** `tests/python/test_hooks_import_nothing_from_the_project.py` plants modules for every registered hook and fails on either.

### Every hook: its helpers come from beside it, never from the project (v0.322.3, completed in v0.322.4)

`scripts/_hook_prelude.sh` sets `_MYCELIUM_ROOT` to the folder above itself: the plugin's root in a plugin install, the project's `.claude/` only in an old copied-in install, where the hooks themselves live in the project. A hook with no `CLAUDE_PLUGIN_ROOT` (Cursor, Codex) resolves its helper under `_MYCELIUM_ROOT`. Until 0.322.3 the fallback was the same helper's name under the project's own `.claude/` (its scripts folder, or its hooks folder for `preflight.sh`), by absolute path or relative to the working directory (41 lines in 12 files), so on those runtimes a repository that carried a file by the right name had it run: `tests/python/test_hooks_run_only_their_own_scripts.py` plants one and shows `gate.sh` and `session-start.sh` ran it on 0.322.2. **Do not add a lookup in the project for anything a hook executes or sources**; that test fails on the line.

**The secret scan (`gate.sh`) covered `.claude/` except `.claude/state/` from v0.322.3 to v0.322.7**, by the maintainer's ruling of 2026-10-12; since v0.323.0 no file write is scanned and the commit is (above). **One session start counts once (v0.322.3)**: the assumption-test counter is written by the `--fast` pass (or the single unflagged pass on Codex and Cursor) and only read by `--async`.

### Every hook: nothing outside a Mycelium project, and the state folder's ignore file (v0.318.0)

**The ignore file keeps five decision files in git (v0.322.2): `discovery-skip-ack`, `brownfield-ack`, `delivery-skip-ack`, `scale-lock-ack`, `upstream.json`.** `scale-lock-ack` was missing from the rules until 0.322.2. An ignore file that exists is never rewritten, so one written earlier can ignore a decision file the current rules keep; `session-start.sh` reports that (`_state_dir.py --ignored-decisions`, `DECISION FILE NOT IN GIT`) with the line to add and changes nothing. A rule from anywhere else (a root `.gitignore` that leaves out `.claude/`) is the person's choice and is not reported.

Every script in this folder sources `scripts/_hook_prelude.sh` on line 2. **In a project with neither `.claude/canvas/` nor `.claude/diamonds/` the hook exits 0 right there**: no gate, no output, no log, nothing written in the project (founder ruling 2026-10-10, after Anthropic's directory review of v0.317.4 found the hooks logging in every repo the plugin ran in). `.claude/state/` alone does not count, because versions before 0.318.0 created it everywhere. The one write is outside the project, a timestamp at `$TMPDIR/mycelium-hooks-alive-<uid>`, which the entry skills read beside `.claude/state/hooks-alive` to tell "hooks ran" from "hooks are off". Consequence, by design of the ruling: a fresh repo where `/mycelium:start` or `/mycelium:setup` never ran is not gated at all, including by `discovery-gate.sh`'s cold-project stage. `install-runtime-hooks.sh`, a setup script rather than a hook, sets `MYCELIUM_PRELUDE_ANY_PROJECT=1` first. Since 0.322.1 the nine blocking PreToolUse hooks are not started at all in such a project: their commands in `hooks.json` make the same test before `bash` is started (see the fail-closed section below). In a Mycelium project, when the hook exits and `.claude/state/` exists without `.gitignore`, it writes one from `scripts/state-gitignore.txt` (the same rules `/mycelium:setup` writes, through `scripts/_state_dir.py`), so the logs above are never committed by accident in a project where setup never ran. It never creates the folder, never rewrites an existing ignore file, writes nothing to stdout and leaves the hook's exit status alone. Python scripts create folders through `_state_dir.prepare`/`prepare_dir`, which does the same for a folder inside `.claude/state/`. `tests/python/test_state_ignore.py` runs every hook registered in `hooks.json` in an empty project and checks the result; on 0.317.5, 7 of 55 registered entries left the folder without the file.

---

## Fail-Closed vs Fail-Open Policy (v0.9.0)

Different hooks have different failure semantics. The choice is deliberate.

**Fail-closed** (block on failure) — used for **security and scope enforcement**:
- `gate.sh` — exit 2 on preflight stamp corruption; since v0.319.1 a deny when the secret scan itself cannot run (until then a grep error read as "no secret" and the write passed); since v0.323.0 that covers the scan of a shell command, a commit and a push
- `scope-gate.sh` — deny via JSON when the diamonds file cannot be read or the helper cannot run; since 0.324.0 it reads the delivery cycle's record and no longer a state file

**Rationale**: a silently disabled enforcement hook is worse than no hook. If `gate.sh` crashes, secret detection is gone. If `scope-gate.sh` cannot read state, scope enforcement is gone. These hooks must announce their failure by blocking the operation.

**When the gate's own process cannot run (v0.322.1).** A script's fail-closed branch only runs when the script does. Claude Code lets a tool call through when a hook cannot start, reaches its timeout, exits with a status other than 0 or 2, or prints JSON it cannot read. So until 0.322.1 every gate let the call through in those cases, whatever its script said. Since 0.322.1 every PreToolUse hook that can refuse carries `"onFailure": "block"` in `hooks.json`, and Claude Code then refuses the call and names the hook (maintainer ruling 2026-10-11, "Block the write"; the setting is in the hooks reference linked above, under "Block the action when a hook fails").

Which hooks carry it is one list, `hooks/pretooluse-on-failure.txt`, in three classes: `block` (the nine gates), `continue` (`bash-state-guard.sh`, which can refuse and is left to let the call through when it cannot run, for the reason in its header) and `advisory` (hooks that never refuse and never carry the setting). `tests/python/test_pretooluse_on_failure.py` reads that list and fails when `hooks.json` disagrees with it, when a hook registered on PreToolUse is not in it, or when a script's own text contradicts its class. Add a PreToolUse hook and that test asks for its line.

What it costs and what it does not cover:
- **A gate that reaches its timeout stops the work.** On a slow or busy machine where a gate takes longer than its timeout (10 s or 30 s), every write that gate covers is refused until that is fixed, and shell commands too, because eight of the nine gates are also registered on Bash. The same holds where the hook cannot start (no `bash`, a broken plugin path). The maintainer accepted this cost.
- **Only in a project that uses Mycelium.** Since 0.318.0 Mycelium does nothing in a project with neither `.claude/canvas/` nor `.claude/diamonds/`. That exit is on line 2 of each script, so it needs the script to start: with the setting alone, a machine where the hooks cannot start would have had every write refused in every project the plugin is enabled in. Shown that, the maintainer ruled again the same day: "Block only in Mycelium projects." So each `block` command in `hooks.json` begins with one shell test, the `prefix` line of the same list, which leaves with status 0 before `bash` is started when the project has neither folder. In such a project these hooks are no longer started at all. The prefix is never narrower than the script's own test (`scripts/_hook_prelude.sh`): it leaves only when `CLAUDE_PROJECT_DIR` is set and names a folder with neither marker, which is exactly where the script leaves too; when the variable is not set it goes on, and the script decides by walking up from the working directory as before. The test runs the prefix and the script's test over one matrix of cases, through `sh` and `bash`, and fails if any `block` command is not exactly the prefix followed by its script.
- **What is left: a machine with no POSIX shell.** Claude Code passes a command to `sh -c` on macOS and Linux and to Git Bash on Windows. On Windows without Git Bash it passes it to PowerShell, which cannot read it: the command fails before the test for the two folders is made, and the call is refused in every project the plugin is enabled in, Mycelium or not. The maintainer accepted that limit. The way out there is to install Git Bash, which the hooks need in any case, or to turn the plugin off.
- **Claude Code 2.1.295 or later.** An older version does not have the setting, and there a gate that cannot run lets the call through as before.
- **Exit 0 with nothing printed is an allow, with or without the setting.** It changes what happens when a script fails, not what a script decides. `scale-lock-gate.sh` without PyYAML still allows, by its own design, and `preflight.sh` says so. One such case was closed in 0.322.1: `hi_deny` and `hi_ask` (`scripts/_hook_input_read.sh`) print a refusal or a question as JSON through `python3`, and when `python3` could not run they printed nothing and exited 0, so `gate.sh`, `discovery-gate.sh` and `brownfield-gate.sh` allowed in silence. They now write the reason to stderr and exit 2 (`tests/python/test_refusal_without_python.py`).
- **Any other exit status now refuses.** A gate that means to allow has to leave with status 0 and at most one JSON object on stdout. Three paths that did not were fixed in 0.322.1: `scope-gate.sh` and `framework-guard.sh` fed the tool call to their helper through a pipe under `set -eo pipefail`, and left with `printf`'s broken-pipe status on a call larger than the pipe when the helper answered before reading it (`"active": false`, a corrupt state file); `exposure-gate.sh` printed an expired skip-ack's warning and its own answer as two JSON objects. The same test runs every `block` gate over six kinds of call and checks both.
- **Codex CLI and Cursor.** Codex documents no such setting. Cursor's is `failClosed`, with different rules (there "no output" counts as a failure), and `hooks.cursor.json` carries it on `gate.sh` only, as before. Neither manifest carries `onFailure`, and the test holds them to that.

**Fail-open** (allow on failure) — used for **observability and nudging**:
- `post-write-nudge.sh`, `change-log.sh`, `diamond-state-audit.sh`, `reflexion-gate.sh`, `stop-check.sh`, `session-start.sh`, `next-action-check.sh` (fail-open on a missing transcript by design: a Stop hook that blocked on its own read errors would trap the session; the validator checks its wiring instead)

**Rationale**: an audit log failure should never block a code change. The cost of missing a nudge is small; the cost of blocking a legitimate edit because logging broke is large.

---

## Dependencies

The hooks need `bash` and `python3`. Most use only the Python standard library and read JSON state.
The gates that read the diamonds and the canvas (`discovery-gate.sh`, `scale-lock-gate.sh`,
`exposure-gate.sh`) need PyYAML, through `scripts/_python.sh`, which uses the `python3` on `PATH` or
the environment `/mycelium:setup` offers to create in `${CLAUDE_PLUGIN_DATA}/pyenv` (PyYAML from
PyPI, installed only if the user says yes). Without PyYAML those gates refuse with the reason rather
than allow. `git` and `gh` are optional: the hooks that use them carry on without them. Nothing in
the hooks installs software or reaches the network except `ci-signal` (Stop, SessionStart), which
asks GitHub for the latest CI result through the user's own `gh` login; `MYCELIUM_CI_SIGNAL=off`
turns it off. What Mycelium reads, writes and connects to is stated in full in
[`PRIVACY.md`](../../../PRIVACY.md).

**Runtime state files are JSON** (not YAML), so most hooks parse them with the standard library.
See `../state/README.md` for the data format.

---

## Every registered hook

`hooks.json` is the source of truth, and the sections above describe each hook with its tier
(BLOCK, NUDGE, observability) and its fail policy. Read the manifest for the current list rather
than a table here: the table that stood in this place listed the hooks of v0.9.0 and went stale as
hooks were added.

---

## References

- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html) — the "computational vs inferential" distinction this whole architecture is built around
- [Daniel Bentes — BDSK comparison feedback](../../../CONTRIBUTORS.md) — the inspiration for scope enforcement and trace audit patterns
- `../state/README.md` — runtime state philosophy
- `../tests/validate-template.sh` — the structural integrity validator (a different kind of computational enforcement)

## One reading of the tool call (0.196.0)

The blocking hooks of 0.196.0 (`gate.sh`, `discovery-gate.sh`, `brownfield-gate.sh`, `scope-gate.sh`,
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

