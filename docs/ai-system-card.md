# AI System Card — Mycelium

**A candid description of how Mycelium uses AI, what it does and doesn't do, and how to contest its outputs.**

This card adapts Mitchell et al. (2019) *Model Cards for Model Reporting* to an `agent_runtime_target` product — a framework operated *by* an AI runtime (Claude Code, Codex, Cursor, etc.) rather than one that embeds an AI library. The model details belong to your runtime vendor; what's described here is **Mycelium's recommendation logic** layered over that model.

This is not a marketing document, a technical whitepaper, or a compliance certificate. Read it before relying on Mycelium's recommendations for substantive decisions.

---

## 1. Identity

- **System name:** Mycelium — Theory-Guided Agentic Product Development Framework
- **Version:** 0.37.0 (canonical source: the `*Version X.Y.Z` line in `CLAUDE.md`; mechanical tokens here — version, skill count — are kept in sync by `scripts/sync_derived.py`, not hand-edited)
- **Last updated:** 2026-05-30 (mechanical-token refresh; last *full* audit 2026-05-04 — see §9)
- **Maintained by:** Håvard Bartnes (haabe). Issues + correspondence: [github.com/haabe/mycelium/issues](https://github.com/haabe/mycelium/issues)
- **AI Act risk tier:** **Limited** (canonical, assessed 2026-05-04 by `/regulatory-review` — see `canvas/threat-model.yml :: regulatory_classification` for the full assessment). Mycelium is not in any EU AI Act Annex III high-risk category. AI outputs reach end users (developers) in user-affecting ways via the runtime, so Article 50 transparency obligations apply and are satisfied by this card + README + CLAUDE.md framing + runtime-level disclosure.

## 2. Intended use

- **Primary use:** Guide solo developers and small teams through the full product-development lifecycle (purpose → strategy → opportunity → solution → delivery → market) with theory citations, evidence gates, and a self-learning correction trail. Operated by an AI agent runtime; Mycelium provides the framing the agent applies.
- **Intended users:** Developers comfortable working with an AI agent (Claude Code, Codex, Cursor, etc.) who want a discovery-first, theory-grounded process with explicit evidence gates. **Risk-aware builders** — those burned by building the wrong thing OR cautious enough to want to avoid it (see `canvas/landscape.yml` strategic positioning).
- **Intended context:** Used during active product development sessions. The framework reads `CLAUDE.md` + skills + canvas state on every task; recommendations land mid-session rather than as a one-shot setup.
- **Out-of-scope use:**
  - Not a legal or compliance certification tool. `/regulatory-review`, `/privacy-check`, `/threat-model` raise awareness — they don't replace qualified counsel.
  - Not a substitute for actual user research. The framework can structure interviews and audit evidence, but the evidence has to come from real users.
  - Not for safety-critical AI decisions (medical, legal, financial). Mycelium's quality gates are appropriate to product-development work, not high-risk AI deployment.
  - Not a replacement for engineering judgment. The framework's recommendations are starting points; the developer remains the decider.

## 3. Model details

This is the agent-runtime-target case: **Mycelium does not embed an AI model.** It is operated by an AI agent runtime that the user chooses (typically Claude Code with Anthropic's Claude). Model details belong to the runtime vendor and that vendor's own documentation.

What Mycelium contributes on top of the runtime:
- **Instructions:** `CLAUDE.md` is read first on every task. Defines mandatory protocols (Pre-Task, Pre-Ship, Post-Task) and Communication Rules (plain-language-first, inline attribution, learning-capture prompts).
- **Skills:** 49 skills — markdown SKILL.md files in `plugins/mycelium/skills/` (installed to `.claude/skills/`) — define structured procedures the agent invokes by name (`/interview`, `/diamond-progress`, `/xai-check`, etc.).
- **Theory-gated state:** `.claude/canvas/*.yml` files persist evidence-supported product state; gates in `.claude/engine/theory-gates.md` block phase transitions without sufficient evidence.
- **Corrections / patterns / warnings memory:** `.claude/memory/` accumulates failures (`corrections.md`), successes (`patterns.md`), and CI signals (`warnings-log.md`). Read before every task.
- **Hooks:** runtime-level enforcement (`.claude/hooks/`): `framework-guard.sh` blocks framework edits to dogfood instances, `scope-gate.sh` enforces L4 scope discipline.

The runtime model is therefore **the actual decision-maker**; Mycelium is the harness that constrains and informs its decisions.

## 4. Performance and limitations

### What Mycelium does well

- **Discovery and strategy.** Heavy mechanism for L0 Purpose, L1 Strategy, L2 Opportunity work — JTBD, OST, Wardley, scenarios, user-needs. Strongest convergent-validity from external practitioners (Bentes/BDSK, Hoskins, Wardley, Skelton — see `corrections.md` cross-references).
- **Self-correction.** When the agent makes a mistake, the framework-guard / scope-gate / reflexion hooks catch it; corrections.md logs it; recurring patterns graduate to mechanism. The Lopopolo reframe — "every interaction is a failure of the harness" — is the load-bearing principle.
- **Evidence discipline.** Theory gates require explicit evidence types per scale; source-class taxonomy (external_human / external_data / internal_stakeholder / internal_desk / internal_simulated) prevents desk-research-only confidence climbs.

### Known limitations (honest list)

- **Prompt-shaped, not code-shaped.** The framework is markdown read by the agent, not executable code. Some checks (e.g., the `delivery-bootstrap` Step 1c detector) have no automated coverage proof. A blind spot for `agent_runtime_target` products was caught only by dogfooding `/xai-check` against Mycelium itself (corrections.md 2026-05-04).
- **Verbose first-time output.** New users can find the framework's preambles, theory citations, and protocol enumeration overwhelming. Sprint-mode interview helps but the underlying ceremony is real.
- **Process cliff after `/interview`.** A 2026-04-30 correction documented that 75% of a session can lose Mycelium structure after onboarding. Sprint-mode shipped; lightweight discovery-to-delivery continuation mode is still partial.
- **Opinionated.** Mycelium bakes in specific framework choices (Torres/CDH, Cagan/Inspired, Hoskins/Scenarios, Skelton/Team Topologies, Cynefin, GIST). Teams that prefer different frameworks will need to override — not all overrides are graceful.
- **Solo / small-team optimized.** The orchestration patterns target single-agent + single-developer dynamics. Multi-developer, multi-agent coordination is documented in `orchestration/` but less battle-tested.
- **Vendor-runtime dependent.** AI quality is upstream of Mycelium. If Claude (or whichever runtime) produces a confidently-wrong output, the framework's gates catch *some* but not all of those failures. corrections.md exists precisely because gates miss things.

### Known foreseeable misuse

- Treating skill suggestions as authoritative without applying judgment. Skills are starting points; the developer decides.
- Skipping pre-ship analysis on substantive framework work. This was identified as a recurring agent-behavior failure (corrections.md 2026-05-04 RECURRING entry); the new G-P-pre Mandatory Pre-Ship Protocol is the convention-layer fix.
- Treating corrections.md as a graveyard for issues to defer. The cleanup-cycle pattern is for *batched* cleanup, not indefinite deferral. See `feedback_no_tech_debt_deferral.md`.

### Evaluation methodology

- **Self-eval.** `.claude/evals/assumption-tests/` and `.claude/evals/scenarios/` track behavioral hypotheses with pre-committed pass/iterate/kill criteria. Currently running: `2026-05-02-relay-norms` (5/10 sessions), `2026-05-04-xai-inline-attribution` (1/10 sessions).
- **Cycle history.** `.claude/canvas/cycle-history.yml` captures completed leaf lifecycles for calibration. As of 2026-05-04: 1 completed cycle (the L4 cleanup that closed the framework-guard graduation).
- **Framework reflexion.** `/framework-health` runs quarterly self-assessment; not yet executed for v0.15.x.
- **External evaluation.** Convergent validity comes from external practitioner feedback (canvas evidence trails). Application-grounded user testing is pending — Juniors.dev pilot is the natural next test.

## 5. Explainability

- **Disclosure surface.** This system card + the README's product positioning + CLAUDE.md's frontmatter version line. Users running Claude Code with Mycelium installed know they're operating an AI runtime that's been instructed by Mycelium; the runtime itself discloses AI nature (Anthropic's own disclosure).
- **Per-decision rationale.** The framework's Communication Rule (CLAUDE.md, added 2026-05-04) requires the agent to cite the trigger of any non-trivial move with `(per: <source>)`. Sources include corrections.md entries, canvas evidence, theory gates, patterns, decision-log entries. Eval `2026-05-04-xai-inline-attribution` tests faithfulness over 10 sessions.
- **Confidence signaling.** Every confidence claim must include level + evidence type + WHY appropriate + what would increase it (CLAUDE.md Communication Rules). This is calibrated, not vibes-based.
- **Fidelity caveat.** When the agent emits rationales, they are the agent's articulation of what drove its move — not a guaranteed audit of the underlying model's computation (Lanham et al. 2023). The inline-attribution eval explicitly tests for unfaithful "plausible after-the-fact" citations and treats theatre as a kill criterion.

## 6. Recourse

- **How a user contests an agent recommendation.** File an entry in `.claude/memory/corrections.md` describing the mistake. Format defined in the file's header. The entry stays in the user's repo (committed), is read on every subsequent task ("read before every task" per CLAUDE.md), and feeds into `/corrections-audit` for pattern detection. For framework-level issues, open an issue at github.com/haabe/mycelium/issues.
- **Who reviews the contestation.** The user's own agent reads corrections.md on the next task and adjusts. For escalated patterns: Håvard Bartnes (maintainer) reviews via GitHub issues. There is no automated chatbot in the loop.
- **Service-level commitment.** Recurring entries (≥3 instances of the same root cause) graduate to mechanism on the next L4 cleanup cycle (typically every 2-4 weeks of active development; see cycle-history.yml). One-off corrections inform the next session's pre-task protocol — same-day effect on agent behavior. **Open issues on github.com/haabe/mycelium**: no formal SLA for response time; this is a solo-maintainer project. Acknowledged as a known gap (this audit, 2026-05-04).
- **Logging.** Every contestation is logged in corrections.md (committed to the user's repo). Public-graduation cases (recurring → graduated) are visible in mycelium upstream commit history.

## 7. Privacy and data handling

- **What user data Mycelium handles.** All canvas state, corrections, patterns, decision logs, and evals live in `.claude/` inside the user's own repository. **Mycelium does not transmit user data to any external service.** The runtime (Claude Code / Codex / Cursor) sends data to its own vendor per that vendor's privacy policy — Mycelium is upstream of that and has no involvement.
- **Retention.** User-side: as long as the user keeps the repo. Vendor-side: per the runtime vendor's policy.
- **Opt-out.** N/A at the Mycelium layer — Mycelium itself doesn't collect anything. The user's relationship is with the runtime vendor.
- **Sensitive content.** `.claude/.gitignore` excludes some research-private artifacts by convention (`hoskins-feedback/`, `linkedin-source.md`). For products built using Mycelium, run `/privacy-check` to assess data flows in the product itself.

## 8. Ethical considerations

- **Stakeholders affected.** Direct: developers using Mycelium. Indirect: end users of products built using Mycelium (the framework's discovery and quality gates shape what gets shipped).
- **Anticipated harms.** (a) Over-reliance on framework recommendations without judgment — mitigated by the explicit "developer remains the decider" framing throughout. (b) Theatre — performing process without substance, which the framework explicitly guards against (eval kill criteria, Goodhart's-Law commentary in patterns.md, faithfulness audits in /xai-check). (c) Opinionation lock-in — Mycelium's framework choices may not fit all teams; documentation calls this out.
- **Mitigations.** Self-correction loop (corrections.md + /corrections-audit + recurring-≥3 graduation), Lopopolo reframe applied at every recurring-failure point, explicit `validated_functionally` vs `needs_user_testing` tagging in /xai-check output.

## 9. Caveats and recommendations

- **Open questions.** Whether the discovery-first / theory-grounded approach scales beyond solo and small-team contexts (Juniors.dev pilot is the test); whether the framework's verbosity becomes friction at scale; whether agent runtimes other than Claude Code give comparable behavior (agent-agnostic aspiration; not yet tested).
- **Recommended next audit.** This card is re-reviewed annually or after any material change to the framework's recommendation logic (new mandatory protocol, major skill set change, runtime portability work).
- **Last full audit:** 2026-05-04 via `/xai-check` against `svc-mycelium` + `/regulatory-review` (canonical tier confirmed). Result: 13 of 15 items used (within `limited` tier cap); 8 of 10 Stage 2 cells pass after remediation; Stage 4 system card pass; Stage 5 recourse pass; Stage 3 fidelity partial (eval data collection ongoing). The 2026-05-30 update refreshed mechanically-derived tokens only (version, skill count, paths) — it was **not** a re-audit; the substantive findings above still date to 2026-05-04 and a fresh `/xai-check` is the next-audit trigger.

## 10. Contact and feedback

- **Issues or concerns:** [github.com/haabe/mycelium/issues](https://github.com/haabe/mycelium/issues)
- **Reporting harm:** Same channel; mark with `[harm]` prefix in the title for visibility.
- **Press / regulator inquiries:** Same channel until a separate route is established.

---

*Adapted from the scaffold at `plugins/mycelium/templates/ai-system-card.md` (installed to `.claude/templates/ai-system-card.md`; Mitchell et al. 2019 + agent_runtime_target extensions per `engine/xai-canvas-threading.md`). Maintained at `docs/ai-system-card.md` upstream; ships with the framework so any project that runs `/upgrade.sh` gets the latest version. The user's own products that contain AI should publish their own system cards, drawing from the template — Mycelium's card describes Mycelium's recommendation logic, not the products built using it.*
