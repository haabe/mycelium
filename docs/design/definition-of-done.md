# Design: outcome-based Definition of Done as a forcing function

**Status:** design (not built). **Date:** 2026-06-11. **Origin:** roadmap dogfood —
the L0 "Mycelium Purpose" diamond reached Deliver with its success bar still
implicit; the founder pinned it ("fits, not ships") only reactively during
`/diamond-assess`, and named the gap: *a Definition of Done should be forced
explicit at diamond birth, not discovered late.* This doc designs the fix,
grounded in two adversarially-verified deep-research passes.

> Authoring home: upstream (this repo). Evidence trail + the worked L0 instance
> live in the roadmap repo (`purpose.yml#definition_of_done`, decision-log
> 2026-06-11). Build when fresh — building a DoD mechanism while tired is how you
> get checklist theatre instead of the educational version.

---

## 1. The problem

Classic agile DoD is an output/quality checklist (tests written, peer-reviewed,
docs updated) with **zero criterion that user behaviour changed or value was
delivered** (verified, Agile Pain Relief checklist; Seiden/Cagan/Amplitude
outcome school). Mycelium inherited the implicit version: each diamond's "done"
lived in people's heads, defaulting to the harshest, least-controllable bar
("a user shipped a product"), which is both wrong for validating *purpose* and a
demotivation engine. The fix is a **forcing function** that pins an explicit,
measurable, **outcome-based** done-criterion when a diamond is born — and
retrofits it when missing.

## 2. What the research settles (verified, with evidence grade)

**Dive 1 — DoD canon + outcome school** (24/25 claims confirmed 3-0):
- DoD is a **team-agreed, displayed, explicit** exit gate — not implicit. [primary/canonical]
- DoD ≠ Definition of Ready (entry) ≠ Acceptance Criteria (per-item correctness). A diamond's done is **validated value**, not per-feature correctness. [strong]
- **Done = "a change in human behaviour that creates value" (Seiden), not "feature shipped"; you're done when it ships AND has impact (Amplitude).** [primary, unanimous]
- **Specify WHOSE behaviour** changes (user vs customer vs business) — maps to scale altitude. [primary, Seiden]
- **Problem-and-whom FIRST, metric SECOND** (Cagan: "most measurement problems are clarity problems"). Never lead with the number. [primary]
- A number is **optional, not mandatory** — directional outcomes are legitimate (the over-strict "must be a numeric threshold" claim was REFUTED 0-3). [refutation]
- The strongest existing forcing-function is **SAFe's Epic Hypothesis Statement**: state a measurable signal *before* approval; done = hypothesis **confirmed OR invalidated-and-cancelled**. A software framework can make this a true mechanical gate (SAFe's is human review). [strong]

**Dive 2 — rules for the four open questions** (23/25 confirmed):

### Q1 Laddering [HIGH — primary: Adzic Impact Mapping, Microsoft Research]
- **Contribution-not-summation**: a child's done-criterion only COUNTS when it produces a corresponding move in the PARENT outcome. "Improvement at an intermediate step is of no use until it leads to a corresponding improvement in primary success metrics." A child that doesn't roll up is discarded, not summed.
- **Distinct altitude per level** (Goal→Actor→behaviour-change Impact→Deliverable).
- **Mechanical cascade is the anti-pattern** — children are divergent hypotheses/options, not summed contributions.

### Q2 Leading vs lagging by altitude [HIGH, one conflict]
- **Lower/activity altitude → LEAD measures** (predictive + team-influenceable); **higher value-validation → LAG measures** (already realized, no longer influenceable). Direct most attention to lead measures (4DX Discipline 2).
- **One Metric That Matters per stage** (Lean Analytics): focus one governing signal tied to the goal's lifecycle stage, not the full set; type shifts by stage (Empathy→Stickiness→Virality→Revenue→Scale). [practitioner heuristic]
- CONFLICT — do NOT codify a universal three-tier (leading/North-Star/lagging) vocabulary: mainstream North Star literature treats the North Star itself as leading. Pick a two-axis mapping instead (below).

### Q3 Kill-criteria (done-by-invalidation, non-gameable) [HIGH]
- **State AND date**: pre-commit BOTH an objective benchmark and a time bound — "if not X by Y, kill" (Annie Duke). 
- **Pre-commit BEFORE the data** (pre-registration / anti-HARKing — Experimentology, primary). Confirmatory criteria trusted; post-hoc not.
- **Concreteness + conditionality, not timing alone** (Schweitzer et al. 2024, N=7,759, preregistered): vague pre-commitments still leak bias. Non-gameability needs a concrete state conditional on a future event.
- **Institutionalize as a scheduled go/KILL gate** at predetermined intervals, decided on merit — not in-the-moment judgment (Stage-Gate).
- **Generate the kill-criteria by pre-mortem** at goal birth: "assume this has already failed — list why" (past tense, not "might it?"). ~30% better at identifying outcome reasons (Mitchell/Russo/Pennington 1989 via Klein). [only Q3 item with hard experimental backing]

### Q4 Teaching prompts [THIN — under-evidenced, treat as provisional]
- Only survivor: the **Impact Mapping why → who → how-should-behaviour-change → what** sequence (forces an observable behaviour-change before any deliverable is named). [medium]
- Example Mapping colour-taxonomy claims were REFUTED (1-2, 0-3).
- Seiden's "we'll know we're right when [behaviour]" template, Torres story-based, Socratic prompts: named but **no claim survived verification** — not disproven, just unsupported in this pass.
- **Verdict:** adopt the why-who-how-what scaffold; treat exact wording as PROVISIONAL and validate it with Mycelium's own `/prompt-optimizer` A/B rather than codifying unverified phrasing.

## 3. Mycelium fit — most of this already exists (map before adding)

| Research pattern | Existing Mycelium mechanism |
|---|---|
| Hypothesis stated upfront, confirmed-or-invalidated | `/assumption-test` (pre-registered prediction + success/failure criteria) |
| Pre-commit before data (anti-HARKing) | `/assumption-test` Step 5 prediction; cluster `consistency-as-evidence` discipline |
| Kill-by-criterion = also done | `dogfood-mode` kill-as-learning + `diamond-progress kill` |
| DoD as exit gate | `diamond-progress` Deliver→Complete checklist |
| Pre-mortem | `/devils-advocate`, `/bias-check` (premortem is namable there) |
| Validate provisional prompt wording | `/prompt-optimizer` |

**The gap is connective tissue, not a new subsystem:** a `definition_of_done`
pinned per diamond at birth, that these mechanisms reference.

## 4. The design

### 4.1 Canvas field (per diamond / scale)
```yaml
definition_of_done:
  outcome:   "<what changes, for WHOM — a behaviour, not a feature>"   # required; problem-first
  signal:    "<the ONE observable thing you'd see them DO>"            # required; OMTM — one, not many
  kind:      leading | lagging                                        # defaulted by scale (4.3)
  threshold: "<a target IF one genuinely fits>"                       # OPTIONAL (numbers not mandatory)
  rolls_up_to: "<parent diamond id + which parent outcome this serves>"  # child diamonds; contribution-not-summation
  kill_criterion:
    state: "<concrete benchmark that means this goal is WRONG>"
    date:  "<the review date by which state must hold>"              # state AND date, pre-committed
    premortem: "<the failure it was generated from>"
  provenance: { source_class, validated, captured_at }
```

### 4.2 The educational sequence — `/define-done` (Socratic, problem-first)
1. **"When this is done, what's different — and for WHOM?"** → outcome + whose-behaviour. *Reject "what you'll build."* (Bad: "the onboarding flow ships." Good: "non-fluent users get through the brief without hitting the vocabulary wall.")
2. **"What's the ONE thing you'd SEE them do that proves it?"** → single observable signal (OMTM). (Bad: "it feels better." Good: "they came back for a second session.")
3. *(optional)* **"Is there a point where it's ENOUGH?"** → threshold only if it fits; skippable.
4. **Pre-mortem for the kill-criterion**: *"It's [review date]. This diamond failed. What happened?"* → derive a concrete **state + date** that means *kill, not finish*.

Each step carries a good/bad contrast — the teaching is in the **sequencing**
(problem→signal→maybe-number→kill) and the contrast, not a help doc. **Wording is
provisional → A/B via `/prompt-optimizer`.**

### 4.3 Per-scale "done" + lead/lag defaults
| Scale | "Done" means | kind default |
|---|---|---|
| L0 Purpose | people **keep choosing it** ("fits, not ships") | lagging |
| L1 Strategy | a where-to-play **bet validated** | lagging |
| L2 Opportunity | a real user need **confirmed worth solving** | mixed |
| L3 Solution | the solution **actually solves it for users** (not just built) | leading |
| L4 Delivery | shipped **AND has the intended impact** | leading |
| L5 Market | **adoption/business outcome** at scale | lagging |

**Ladder rule (Q1):** a child's Deliver→Complete checks that the **parent outcome
moved / parent assumption validated**, not just that the child shipped.
Contribution-not-summation.

### 4.4 Mechanism — birth + retrofit (founder requirement)
- **Birth:** `/interview` (L0) and child-diamond spawn (`/diamond-progress`) call `/define-done` → write the field before the diamond is "live."
- **Retrofit (detect-and-prompt, never silent-fill):** `/canvas-health` lints diamonds missing a DoD; `/diamond-assess` flags + offers inline; SessionStart nudge. All route to the **same** `/define-done` question (retrofitting L0 today proved the question is what produced "fits, not ships," not a back-filled field).
- **Gate:** `diamond-progress` Deliver→Complete passes only when the DoD `signal` is met **OR** the `kill_criterion` (state+date) **fired with evidence** — routed through `dogfood-mode` + decision-log so done-by-invalidation can't become "declare failed work done."

### 4.5 Failure-mode guards (baked in)
- **No checklist theatre:** the field is an OUTCOME, step 1 rejects "what you built."
- **No Goodhart:** number optional; when set, pair with a qualitative guard ("3 warm bodies who bounce ≠ done").
- **Kill-path honesty:** done-by-invalidation requires the pre-committed state+date to have actually fired with evidence at the scheduled gate.
- **Problem-first sequencing** prevents the metric-availability trap.

## 5. Adoptable rules (codifiable as conventions)
1. Done is an explicit, displayed, **outcome** criterion — never implicit, never a build-list. [HIGH]
2. Elicit **problem + whose-behaviour first, signal second**; a number is optional. [HIGH]
3. **One** observable signal per diamond (OMTM), typed **leading** at low scales / **lagging** at high. [HIGH / heuristic]
4. A child is done only when its outcome **rolls up** to move the parent — contribution, not summation; no mechanical cascade. [HIGH]
5. Every diamond carries a **state+date kill-criterion**, pre-committed at birth via **pre-mortem**, checked at a scheduled gate; invalidation-with-evidence is a legitimate "done." [HIGH]
6. **Retrofit** missing DoD by detect-and-prompt with the same educational question — never silent-fill. [founder requirement]
7. Teaching-prompt wording is **provisional** → validate with `/prompt-optimizer`. [Q4 thin]

## 6. Open questions (carry into build)
- Q4 wording needs a dedicated re-run OR an in-house `/prompt-optimizer` A/B — no prompt-pattern claim survived verification.
- The boundary where a parent roll-up legitimately IS summation (e.g. aggregate revenue) vs only contribution-validation — unspecified by the sources.
- Three-tier vs two-tier North Star indicator vocabulary — sources conflict; pick one for the convention (recommend the lead-low / lag-high two-axis above).
- Meta-rule preventing the scheduled kill-gate from itself becoming a goalpost-moving ritual (reassessing the reassessment cadence) — unspecified.

## 7. Build plan (phased)
1. Schema + `/define-done` skill (question + field).
2. Retrofit detector (`/canvas-health` lint + `/diamond-assess` flag + SessionStart nudge).
3. Birth wiring (`/interview` + spawn).
4. Gate wiring (Deliver→Complete references the DoD; kill-path through dogfood-mode).
5. Backfill L0 (reformat today's ad-hoc field to schema) + L1; `/prompt-optimizer` A/B on the question wording.
