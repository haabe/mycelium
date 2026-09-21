# Errata — corrections to what Mycelium claimed about its sources

**Why this file exists.** Mycelium's pitch is that it is grounded in established product-thinking
frameworks. On **2026-09-20** every Tier-1 source was read at the primary source for the first time,
and a number of the framework's citations turned out to misdescribe the works they name. **Some of
those errors changed what the framework told a user to do.**

This page lists them. It is written for someone who used an affected skill and wants to know whether
a decision they made was influenced by a defect — so each entry says **what the framework said, what
the source says, and whether output changed.**

**None of these were deliberate.** Most came from citing a summary, a secondary source or a
recollection rather than the book. One came from the framework's own prose being quoted back as if
it were the author's. All were found by reading the sources; none by any gate.

---

## A. Errors that CHANGED WHAT THE FRAMEWORK TOLD YOU TO DO

These affected rankings, classifications or advice. **If you used these skills before v0.229.0,
re-check decisions that turned on them.**

### A1 · `ice-score` multiplied where Ellis averages
- **Framework said:** `ICE = Impact × Confidence × Ease`, cited to Sean Ellis.
- **Source says:** *"Then those ratings are **averaged** to provide an aggregate score for each
  idea"* — `Hacking Growth`.
- **Output changed:** yes. On a 1-10 scale, (10,10,1) and (7,7,7) both average 7.0 but multiply to
  100 and 343. **A bold idea that was hard to build was systematically demoted** relative to a
  balanced one, by arithmetic the cited author does not use.
- Also: a scale note said Confidence was `0.0-1.0` while the step above and the bands below both
  said `1-10`. All three now say 1-10.

### A2 · `user-needs-map` subtracted where Ulwick adds and clamps
- **Framework said:** `underserved = importance − satisfaction`, cited to Ulwick's ODI.
- **Source says:** *"opportunity = [importance + max (importance − satisfaction, 0)]"* — `What
  Customers Want`. Importance is weighted **twice**.
- **Output changed:** yes, and it can invert a ranking. A trivial need slightly unmet (3,1) scored
  **2**; a critical need mostly met (9,8) scored **1** — so the trivial one ranked higher. Under
  Ulwick they are 5 and 10.
- **Also newly documented:** Ulwick's inputs are **population percentages**, not one person's rating
  — *"the percentage of people rating that attribute a 4 or a 5 on a scale of 1 to 5"*. The skill now
  says the instrument needs a sample and that the bands are meaningless without one.

### A3 · `cynefin-classify` offered a liminal transition out of Clear
- **Framework said:** a `Clear → Complicated` liminal row.
- **Source says:** the liminal line *"intersects all domains **except Clear**. Liminality in the
  Clear domain is not visible, making the boundary between Clear and Chaotic a cliff or catastrophic
  fold."*
- **Output changed:** yes, and in the riskiest direction. **Clear has no liminal zone precisely
  because its exit is a cliff.** A user told they were easing out of Clear through a transition held
  the exact belief the fold punishes. Row removed.
- Also: the section was dated "Snowden, 2022+"; liminal arrived in **2019**, Confused in 2020.

### A4 · `wardley-map` had no doctrine step
- **Framework said:** a Climate step and a Gameplay step.
- **Source says:** three classes with opposite selection semantics — climate applies *"regardless of
  your choice"*, doctrine is *"universally applicable... **Don't pick and choose, apply them all**"*,
  gameplay is *"not universal"*.
- **Output changed:** by omission. The framework shipped the two classes you select from and omitted
  the one you are told not to select from. A doctrine step is added.

### A5 · `diamond-assess` asked Rother's questions in a fixed order
- **Framework said:** always ask "what is the target condition?" first.
- **Source says:** *"**before a target condition has been established, the order of questions 1 and 2
  is reversed**."*
- **Output changed:** yes, on any diamond without a target condition — which is every diamond at its
  start. The order is now conditional, and the freeze rule is documented: *"Once a target condition
  is established... its content and achieve-by date are not easily changed."*

### A6 · A theory gate read a field nothing wrote
- **Framework said:** the competitive gate compares the landscape's newest entry against the
  diamond's `last_progressed`.
- **The defect:** nothing in the plugin wrote `last_progressed`. As it decayed, the gate's threshold
  moved into the past and **the gate got easier to pass the longer it was neglected.**
- **Output changed:** yes — silently, in the passing direction. `diamond-progress` now writes the
  field, and the gate fails closed on a stale one.

---

## B. Misattributions that did NOT change behaviour

Real, and worth correcting, but nothing computed from them.

| claim | what the source says |
|---|---|
| `launch-tier`'s Tier 1/2/3 table, cited to Lauchengco | Her instrument is a **Release Scale built from your own past releases**, not a fixed table. Relabelled. |
| JTBD described as "tripartite" with "Four Forces" (Christensen) | **Both phrases appear zero times** in `Competing Against Luck`. The book says *"Let's not separate those three things"*, and the forces are the *"Forces of Progress"*. |
| Wardley gaps ranked as "4-5 of **64+** gameplay patterns", "zero of **~30** climatic", "**~40** doctrine" | **None of those numbers is in the book.** The only "64"s in 709 pages are figure numbers and the year 1964 — and the author states the sets are **open**: doctrine's list is *"not an exhaustive list"*, gameplay has *"a constant pipeline of new forms"*. A coverage ratio against a fixed denominator was never possible. |
| A DORA band of 5/10/15% | In neither `Accelerate` nor the framework's own `/dora-check`. Locally invented. |
| *"if you can't state a prediction, you don't understand the assumption well enough to test it"* — quoted as Rother | **Not in `Toyota Kata`** (12 phrasings searched). It is **Mycelium's own prose**, from the `assumption-test` skill, which correctly cited Rother for the *idea* and was then quoted back as his words. |
| "Scenarios as connective tissue" linking needs to "acceptance criteria" (Hoskins) | Both phrases appear **zero times**. The mechanism is squarely his — *"Scenarios should thread through every aspect of software development"* — but the vocabulary is ours. |
| `corrections.md` described as "Mycelium's friction log (Hoskins, Ch4)" | His friction log is written **as you use a product**, reports confusion, and is **handed to whoever is responsible**. Ours records build-time mistakes and is read by its author. Different object; the chapter reference is right. |

---

## C. What was checked and found FAITHFUL

Recorded because a list of only failures misrepresents the state.

- **Cagan's four risks** — *"the four big risks that every product team needs to consider"* (EMPOWERED). The framework's four match, and the phrasing-as-questions is faithful.
- **ICE is genuinely Ellis's** — *"At GrowthHackers, Sean developed the ICE score system"*. Only the arithmetic diverged.
- **Cynefin's vocabulary is current** — `Clear` (not Simple/Obvious), `Confused` (not Disorder), aporetic, and the catastrophic fold are all correct.
- **Hoskins's scenario schema** — `simulation`, `persona` and `motivation` are all present, which is the part he says everyone drops: *"Agile methodologies emphasize scenarios... but give scant attention to the simulation aspect."*
- **The 2026-04 ODI/Allen correction** landed and held — though its *replacement* wording was itself wrong and is fixed in A2.

---

## D. What this does not cover

**Roughly a third of the cited theories have now been verified against a primary source.** The rest
are **unverified — not known to be wrong, but unchecked**, and a reader cannot currently tell the
difference. Per-claim provenance marking is the next step.

**Two of eight Tier-1 sources had an edition problem** (the `INSPIRED` on the shelf is the 2008 first
edition and contains no four risks; Team Topologies' 2nd edition retracts "platform team"). **Five of
nine had a currency problem overall**, and in two cases the current thinking lives in a *different
title by the same author* — which a citation carrying edition and year still would not catch.
