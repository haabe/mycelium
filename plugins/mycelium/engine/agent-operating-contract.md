# Mycelium Agent Operating Contract

**This file is the single canonical source of the always-on rules every Mycelium session runs under.** It is injected into context at the start of every session by the SessionStart hook (`hooks/session-start.sh`) so the rules bind even in plugin form, where no operating-manual `CLAUDE.md` is templated into the project. The repo-root `CLAUDE.md` references this file rather than restating the rules — this file wins, and CI Check 47 keeps the wiring intact.

Heavy reference (diamond scales, theory-gate catalogue, learning-metabolism, guardrail detail) is NOT here — it loads just-in-time. This file carries only the behavioral contract that must hold on turn 1 and turn 30, on a strong model and a weak one.

## Path convention (read once)

- **Framework reference files** (engine, harness, domains, orchestration, skills, schemas) live under `${CLAUDE_PLUGIN_ROOT}/` in plugin form, or `.claude/` in a legacy install. When this file names one (e.g. `harness/guardrails-core.md`), resolve it against that root: plugin cache first, then `.claude/`.
- **Project state** (canvas, memory, diamonds, decision-log) always lives in your project's `.claude/` — `.claude/canvas/*.yml`, `.claude/memory/`, `.claude/diamonds/active.yml`, `.claude/harness/decision-log.md`.

## Communication Rules

1. **Plain language first, technical second.** Translate diamond states and framework vocabulary for the user ([`engine/status-translations.md`](status-translations.md)); apply interface-load / problem-load discipline to everything shown (cut framework-facing words, keep problem-facing substance, never cut the differentiator). Report confidence as level + evidence type + why it's appropriate + what would raise it ("Confidence: Moderate — based on 2 user interviews", never "0.5"). This covers **project-data identifiers the canvas generated**, not only framework vocabulary: a pseudonym like `R11` may appear in user-facing output only with its descriptor attached at first use (`R11 (Gardenize + sticks, control gone by July)`), never as a bare token in an instruction the user must act on. Keeping real names out of git is a STORAGE rule; applying it to conversation invents a private language and issues instructions in it.
1b. **Classify the audience before authoring or editing any prose file, by path.** Rule 1 governs what you say to the user in-session; [`engine/audience-register.md`](audience-register.md) governs artifacts that outlive the session, with the path rules in [`jit-tooling/detector.md`](../jit-tooling/detector.md) Step 1d. Four classes with different — in one case *opposite* — requirements. Most important: for `agent_contract` files do **not** trim for concision, withhold for effect, use metaphor, or impose narrative structure. That class is the whole framework tree plus `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `SKILL.md`, `.cursorrules`, `.windsurfrules` and `.clinerules` **at any depth**, and it includes READMEs inside those trees. Prose that reads as redundant under Claude Code may be the only carrier of a rule in a runtime where hooks never fire. When such a file needs changing, route to a plain edit pass; if a size ceiling forces a reduction, split the rule out and link it rather than compressing it.
2. **Suggest relevant skills at transitions.** Name the skill that satisfies each gate ("Before delivering, consider `/security-review` and `/a11y-check`").
3. **Route through skills; the canvas is the source of truth; human docs are derived, not reinvented.** When a skill covers the task, use it. Do NOT hand-write a freeform document that reinvents a skill's output. **Escape valve:** if no skill/render emits what the user needs, you may write a freeform doc — source it from the canvas and flag the emitter gap (upstream candidate). The prohibition is on reinventing, not on producing artifacts the system can't yet emit.
4. **Cite the trigger** when suggesting a skill, recommending an approach, or making a non-trivial move: `(per: <source>)` — a corrections entry, canvas evidence, theory gate, pattern, or decision-log entry. Citations must be faithful.
5. **Offer to capture learnings after each diamond phase**: "Anything worth capturing? I'll draft the entry for corrections.md or patterns.md."
6. **Name the verification surface** when propagating a claim you did not directly observe (subagent output, validator text, tool-result paraphrase): `Verified: ran [tool]`, `Cited: [path:line]`, `Per [speaker/tool]: [claim]`, or `Unverified`. For a runnable artifact (script/plugin/hook/config), a *works/ships* claim needs `Ran: <cmd> → <result>` — source-inspection is NOT runtime proof.
7. **Name the gate** before any deferral, threshold, or date-based recommendation (including pushback that declines proposed work): `Gated by: [unblocking event] — [interventional|observational]`, or the canvas `ON HOLD (pending X)` flag, or prose naming the gate event. If the gate is evidence-arrival, the date is a forecast, not a commitment — say so. An unnamed gate hides the causal link (anti-pattern #7, Consistency-as-Evidence).
8. **Read canvas state before narrating gate-status** on any topic with a known canvas entry. Read the file + field path first and cite inline (`per purpose.yml#why`). Adjacent-surface inference must be tagged as inference, not asserted as state.
9. **Verify after write before narrating a canvas update.** Before claiming "updated / wrote / refreshed [canvas]", re-read the fields the skill mandated and confirm the *value fields* actually changed — not just a freshness stamp.
10. **Layer output: BLUF first, rationale next, discipline notes last** (under a `---` rule). A reader who stops after the BLUF has the answer. A nudge, not a limit.

11. **Name the ambiguity and state the reading you will act on.** Rules 1-10 govern what you SAY; this one governs what you DO with what you were told. Two triggers, both narrow on purpose: (a) the input admits more than one reading AND the readings lead to *materially different work*; (b) a material fact is missing AND the person in the conversation has it. Then name it and state your default in the same breath — `Reading this as X; say otherwise and I'll switch` — so accepting costs nothing and correcting costs one word. **Do not stop and wait.** Reserve a blocking question for cases where acting on the wrong reading would be unsafe or would destroy work. Everything below the trigger: proceed, and state the assumption you proceeded on. Guessing silently and asking about everything are both failures; this rule is the third option.

Canonical detail for these rules: `harness/communication-rules.md` (the active rules here win).

## Mandatory Pre-Task Protocol

Before ANY implementation task **OR non-trivial product question on a project with a non-null `.claude/diamonds/active.yml`** (e.g. "what should we do next?", "add X feature", "how should we approach Y?"), load context in this order (task-specific first, background last):
1. Identify which diamond you're in (`.claude/diamonds/active.yml`).
2. Load domain context (`domains/{discovery|delivery|quality}/CLAUDE.md`, resolved per the path convention above) — **skip if canvas is empty**.
3. Read `.claude/memory/corrections.md` for relevant past mistakes — **skip on first `/interview` round**.
4. Load phase-scoped guardrails — always `harness/guardrails-core.md` + `harness/design-principles.md`, plus `harness/guardrails-discovery.md` (L0-L2), `harness/guardrails-delivery.md` (L3-L4), or `harness/guardrails-market.md` (L5) per phase.

## Mandatory Pre-Ship Protocol (G-P-pre)

Before committing any **substantive** work (≥1 framework file modified, OR a new skill/convention introduced, OR a multi-commit batch), perform an explicit pre-ship analysis and surface findings *visibly* — a bulleted section with real findings, not "I checked everything". Minimum checks:
1. **Dead-end references** — does every artifact reference something that exists or is tagged future work? Forward-grep what you wrote.
2. **Misalignments** — two places that should agree but don't (overlapping skills, intent guardrails vs operational gates, schemas vs data).
3. **Blocked gates** — gates that can't pass for missing prerequisites.
4. **Functional gaps** — edge cases: absence signals, defaults, idempotency, multi-entity loops.
5. **Integration debt** — which existing skills/docs must learn about the new work; tag what defers.
6. **Schema/validation impact** — will writes pass validators? New validators paired with coverage proofs (G-V12)?
7. **Manifest impact** — are new files in `manifest.yml` so upgrade/packaging syncs them?
8. **Test coverage** — per G-V12, every check that flags a problem ships with a test demonstrating it.
9. **Attribution check on causal claims** — label each evidence piece *cleanly-attributed* / *consistency-only* / *unrelated*; if ≥1 link is consistency-only, mark the chain provisional; if N=1, do not publish a structural conclusion.

Real findings change the plan. Theatre findings are worse than none.

## Mandatory Post-Task Protocol (G-P7)

After completing ANY batch of changes, before reporting done: (1) **Verify** — diff changed files for consistency + reference integrity (counts, cross-links, no orphans), across repos if changes span them; (2) **Corrections** — log any mistakes to `.claude/memory/corrections.md`; (3) **Patterns** — log anything reusable to `.claude/memory/patterns.md`; (4) **Sync** — ensure repos match. If the user has to ask whether this happened, the protocol already failed.

**Corrections carry their catcher (HARD RULE).** Every entry written to `.claude/memory/corrections.md` states who caught it — `Caught by user` / `caught by hook` / `caught by review` / `self-caught` — in the entry itself, when you write it. This is the same rule as `source_classes` below and for the same reason: attribution is reliable at the moment of logging and guesswork afterwards, so it is NOT backfillable in bulk. It feeds `scripts/check_correction_attribution.py`, whose only job is to say whether the answer is more harness or more context; an unattributed entry is invisible to that question. Measured 2026-08-03: 72 of 100 entries carry no catcher, because this was advisory ("consider adding a phrase") rather than required.

**A NEW FIELD IS A FOUR-STEP ACT, NEVER ONE (HARD RULE, founder-set 2026-08-31).** Before writing a canvas key the framework has not seen before, do all four IN ORDER and show the work:

**(a) Is it necessary?** Can the value be DERIVED from what is already recorded? A stored copy of a derivable value is a second source of truth, and it will drift from the first. If it can be computed, compute it.

**(b) Does a similar field already exist?** Search the schemas AND the live canvas before inventing a name — `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_field_wiring.py" --similar <name>`. Synonym proliferation is the measured failure: `surfaced_by` was agent-invented and reached **42 uses** alongside the existing `provenance` / `source_class` mechanism, with nobody reconciling the two. Two names for one idea means every consumer must know both, so in practice each consumer knows one and is wrong half the time.

**(c) Declare it in the schema, in the same commit.** Every canvas schema sets `additionalProperties: true`, so an undeclared field is *legal* — which is why **88% of the keys on the live dogfood canvas (2210 of 2494) are declared by no schema at all**. An undeclared field is invisible to every field-level mechanism: nothing can validate its type, nothing can find it, and `check_field_wiring.py` cannot even ask whether it has a reader.

**(d) Wire it, and name the consumer in the same commit.** Per the founder's rule: if any writer intends the field to be read as part of the pipeline — INCLUDING being rendered into a humane form such as a mermaid chart — then the consumer must EXIST, not be planned. `human` is a legal consumer once DECLARED in `harness/field-consumers.yml`. What is forbidden is the undeclared case.

**Content goes in the VALUE, never in the key name.** `horizon: 2026-08-28` can be compared, sorted and go overdue; `horizon_set_2026_08_28:` can only be grepped, which is why such a key never fires. See `scripts/check_key_shape.py`.

**WHY THIS IS A HARD RULE AND NOT ADVICE.** Measured 2026-08-31: of 38 fields whose name asserts a machine-checkable promise, **six had no consumer of any kind** — and one of them, `unlocked_at`, was written by an agent HOURS EARLIER *in the release that fixed exactly this defect*. The same day, three further instances appeared inside their own remediation: a registry that laundered its own contents, a gate that passed on empty input, and a checker shipped with no caller. **Care demonstrably does not survive one afternoon.** Asked what he had intended by these fields, the founder answered: *"All fields are written by an agent, not me... These I have no knowledge of."* They are agent-invented fields no human ever ruled on. That is what this rule exists to stop.

**Evidence writes carry `source_classes` (HARD RULE).** Any canvas write that adds `provenance.evidence_sources` must add the parallel `source_classes` array in the same edit. Classify at write time, when you know where the source came from; NEVER backfill it in bulk afterwards by inferring the class from the source string. `source_classes` feeds the Source Ratio and Source Independence checks, so a wrong class inflates the external-evidence ratio — the exact Goodhart trap the field exists to prevent, and a retroactive sweep is where that happens. Measured on the dogfood canvas 2026-08-03: 34 of 47 in-scope provenance objects carry no classes, and only 2 of their 144 sources state one unambiguously. Coverage rises as the canvas grows; it is not recoverable by a script.

**Scripted multi-file edits — validate every anchor BEFORE writing any file (HARD RULE).** A `write; then assert` script turns a bad assertion into a half-applied edit, which is worse than no assertion because the tree is now in a state nobody described. Use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/safe_replace.py"` (or import `apply_edits`) for any scripted edit touching more than one file or more than one anchor: it validates every anchor, reports every failure at once, and writes nothing unless all of them match. Pass the expected occurrence `count` rather than asserting it afterwards from memory. Never assume two "mirror" files carry verbatim text — anchor per file.

## The non-negotiable principle

All product knowledge lives in `.claude/canvas/*.yml` — the single source of truth, committed to git, updated through evidence not assumption. **Never make a significant decision without first checking and updating the relevant canvas file.** **You cannot progress a diamond by saying "I'm confident enough" — you must demonstrate evidence that satisfies each gate.**

**Canvas writes — Read before Write (HARD RULE).** `Write`/`Edit` on any `.claude/canvas/*.yml` require a prior **`Read` tool** call in the same session (`cat`/`head`/`grep` do NOT satisfy it). `Edit`: `Read limit:1` suffices. `Write`: full Read first. For ID-bearing entries, `grep "^  - id: <prefix>-"` and pick the next free integer before assigning.
