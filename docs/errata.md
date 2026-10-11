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
re-check decisions that turned on them.** (A7 was added later and covers `ice-score` from v0.229.0
to v0.318.x.)

### A1 · `ice-score` multiplied where Ellis averages
- **Framework said:** `ICE = Impact × Confidence × Ease`, cited to Sean Ellis.
- **Source says:** *"Then those ratings are **averaged** to provide an aggregate score for each
  idea"* — `Hacking Growth`.
- **Output changed:** yes. On a 1-10 scale, (10,10,1) and (7,7,7) both average 7.0 but multiply to
  100 and 343. **A bold idea that was hard to build was systematically demoted** relative to a
  balanced one, by arithmetic the cited author does not use.
- Also: a scale note said Confidence was `0.0-1.0` while the step above and the bands below both
  said `1-10`. All three now say 1-10.
- **Corrected in part on 2026-10-11: see A7.** This entry is true of Ellis and says nothing of
  Gilad, the skill's other cited author, who multiplies. It is left as written.

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
- **A second copy survived the fix.** `jtbd-map` step 5 still stated `importance − satisfaction` until
  0.317.1 (found 2026-10-08 by a skill survey for the reading-for-meaning release). It now points to
  `user-needs-map` for the formula rather than carrying its own copy.

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

### A7 · `ice-score` averaged where Gilad multiplies, and described a Confidence Meter that is not his

**Added 2026-10-11, v0.319.0. This entry corrects A1, which is left as it was written.** The
sources were read again, both authors this time: Ellis & Brown, *Hacking Growth*, ch. 4; Gilad,
*Evidence-Guided*, ch. 3 and ch. 4; Gilad's ebook *ICE Done Right* in full; and his Confidence
Meter spreadsheet. The two books are cited by chapter because the copies read carry no reliable
print page numbers; the ebook's page numbers are its own.

- **What 0.229.0 got right.** Sean Ellis invented ICE and averages the three ratings: *"Then those
  ratings are averaged to provide an aggregate score for each idea"* (*Hacking Growth*, ch. 4). The
  skill had multiplied and cited him for it. That citation was wrong and A1 says so.
- **What 0.229.0 got half right.** A1 calls multiplying *"arithmetic the cited author does not
  use"*. That is true of Ellis. The skill also cites Itamar Gilad, for the Confidence Meter and for
  GIST, and Gilad multiplies: *"With ICE, each idea is assigned three numeric attributes: Impact,
  Confidence, and Ease, each in the range 0–10. A fourth value holds the ICE score, which is simply
  the three values multiplied together"* (*Evidence-Guided*, ch. 3). His ebook allows either:
  *"We multiply (or average) Impact, Confidence and Ease to get the ICE score."* (*ICE Done Right*,
  p. 4). A1 did not mention him. So from 0.229.0 to 0.318.x the skill used Ellis's arithmetic
  beside a description of Gilad's meter, and matched neither author.
- **Framework said (0.229.0 to 0.318.x):**
  - `ICE = the average of Impact, Confidence and Ease`, each rated 1-10.
  - Confidence in bands: 1-3 gut feel or desk research, 4-6 some direct evidence, 7-10 strong
    evidence; *"Confidence of 7+ requires test-validated evidence"*.
  - *"Gilad's original Confidence Meter uses 0-10 non-linear (0.01=opinion, 1=anecdotal, 5=market
    data, 8=A/B test, 10=launch data)"*.
  - Impact *"derived from value + usability + viability risks"*, Ease *"derived from feasibility
    risk"*: *"the risks are the inputs, ICE is the output"*.
  - An ICE "sequencing reference" of 100, with bounds 50-300 and a rule to calibrate it against
    outcomes (`engine/adaptive-thresholds.md`); and in `/gist-plan`, *"Kill ideas below threshold"*.
- **Sources say:**
  - **The meter.** In Gilad's spreadsheet each piece of evidence adds a weight, and groups of
    evidence are capped: self conviction 0.01, pitch deck 0.02, thematic support 0.05 (0.1 at most
    for the three); other's opinion 0.1, estimates and plans 0.3 (0.5 at most); anecdotal evidence
    0.5 (1.0 at most); market data 1.0, user/customer evidence 2.0 (3.0 at most); test results 3.0
    (5.0 at most). Confidence is the sum, and launch data is the 10 on his dial. Market data is 1.0,
    not 5, and no version of the meter has an 8. His versions also differ from each other: the dial
    in *Evidence-Guided* has a ring mark at 5 where the dial in *ICE Done Right* (p. 6) has 7. The
    1-3 / 4-6 / 7-10 bands were Mycelium's own. On his scale, evidence short of a test sums to 4.6
    at most; the bands put "user tests, prototypes, data" at 7-10.
  - **The factors.** Impact is *"an estimate of how much the idea will improve the target
    metric"*; Ease is *"an estimation of how hard or easy it is going to be to implement this idea
    in full"* (*Evidence-Guided*, ch. 3). The range starts at 0. Neither author derives Impact or
    Ease from Cagan's four risks; that derivation was Mycelium's own.
  - **The total.** *"The scores themselves are meaningless — they’re just a way to compare ideas,
    but sorting ideas by ICE scores gives us an order of priority."* (*ICE Done Right*, p. 4). No
    source read gives the total a threshold. The one cutoff is on Confidence, before delivery:
    *"With most ideas you want to reach at least medium-high confidence levels (3.0+ on the
    confidence scale) before you switch into delivery mode"* (*Evidence-Guided*, ch. 4). Mycelium
    already held that one, as the L4 entry lock. Ideas that lose are kept: his Parked bank *"can be
    as long as needed and hold ideas indefinitely"* (*ICE Done Right*, p. 9).
- **What changes in 0.319.0.** The maintainer chose Gilad's version, because what Mycelium scores
  is a product idea, on evidence. `ICE = Impact x Confidence x Ease`, each 0-10. Confidence is
  summed from his meter (the spreadsheet weights and caps, stated in the skill with the note that
  his versions differ). Impact is measured against a named metric and Ease is the effort to build
  the idea in full. The four risks are still read before scoring, and that is now labelled as
  Mycelium's addition. The threshold on the total (`ice_advance`) is retired, and `/gist-plan`
  parks an idea where it used to kill one.
- **Output changed:** yes, a second time. On the skill's own 1-10 ratings the average tied an
  untested idea at (10, 1, 10) with a tested one at (7, 7, 7), both 7.0; the skill's note said so
  itself from 0.318.2. And take the two ideas in Gilad's own example (*ICE Done Right*, p. 5): an
  untested idea at Impact 9, Confidence 0.6, Ease 5 and a tested one at Impact 5, Confidence 3.5,
  Ease 5. Multiplied they score 27 and 87.5, and the tested idea leads. Averaged they would score
  4.87 and 4.5, and the untested idea would lead. **From 0.229.0 to 0.318.x the skill ranked on the
  average, so the evidence behind an idea moved its rank far less than it does under Gilad's
  method.**
- **What this means for an existing project.**
  - **Rankings change again.** A ranking made with the average will not come out the same when the
    same leaves are scored now.
  - **Old scores are left as they are.** Nothing rewrites them, and you should not either: a score
    on a closed decision is the record of how that call was made, whether it is a product from
    before 0.229.0 or an average from 0.229.0 to 0.318.x. `check_ice_aggregate.py` holds them in a
    baseline. On its first run after the upgrade it says it cannot tell old averages from new ones
    and asks for `--write-baseline` once; after that it fails only on a new or changed total that
    is not the product of its factors.
  - **A score from before 0.319.0 cannot be ranked against a score from after.** A leaf that is
    still a live candidate is rescored from its evidence when it is next compared; that is the
    rescoring Gilad asks for whenever ideas are chosen, not a conversion of the old number.
  - **`thresholds.yml` may still carry `ice_advance`.** It still validates. One line says the key
    is retired and can be removed.
  - **If you used `ice-score` between 0.229.0 and 0.318.x,** the decisions to re-check are the ones
    where a leaf with little evidence ranked above, or level with, a tested one.

## B. Misattributions that did NOT change behaviour

Real, and worth correcting, but nothing computed from them.

| claim | what the source says |
|---|---|
| `launch-tier`'s Tier 1/2/3 table, cited to Lauchengco | Her instrument is a **Release Scale built from your own past releases**, not a fixed table. Relabelled. |
| **The same table, still asserted by the SCHEMA** — `go-to-market.yml#launch_tier`, `enum: [1,2,3,null]` | **v0.229.0 corrected the skill and left the schema.** One project-wide integer, overwritten by each later release, capped at three bands, read by nothing — so it could not say WHICH release was a major launch, and it re-imposed the fixed table this very row retracts. Her worked example runs to **Level 5**, unrecordable in it. Retired in **v0.233.0 (BREAKING)** and replaced by `releases[]`, where the band names are the team's and one boolean carries the trigger. **Third instance of fix-the-skill-leave-another-surface**, after the five stale ICE descriptions and `canvas-guidance.yml`'s "64+ patterns". |
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
- **ICE is genuinely Ellis's** — *"At GrowthHackers, Sean developed the ICE score system"*. Only the arithmetic diverged. *(2026-10-11: more than the arithmetic turned out to differ from the sources, and the version Mycelium uses since v0.319.0 is Gilad's; see A7.)*
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
