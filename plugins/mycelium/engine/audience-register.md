# Audience Register: how to write each artifact class

`engine/status-translations.md` governs how the agent talks to the user *in a session*.
This file governs how it writes **artifacts that outlive the session**.

Communication craft is not universally good. It is good *for a reader*. Applied to the
wrong artifact class it makes the artifact worse, and for one class it makes it dangerous.
Classify first, then write.

**Classification is by path and lives in one place: `jit-tooling/detector.md` Step 1d.**
This file does not restate the globs — an earlier version did, drifted from them, and
carried a rule Step 1d had already retracted. Read Step 1d for *which class a file is*;
read this file for *what to do about it*. `artifact_audiences` in
`.claude/jit-tooling/active-stack.yml` is a project-level inventory of which classes exist;
the class of any individual file is derived per-file from Step 1d at the moment of writing.

**Out of scope entirely** (Step 1d, Step 0): executable code, CI workflows, test fixtures,
and third-party prose the project did not author. None of these has an audience class and
none is rewritten for readability.

---

## The four classes

| Class | Reader | What they arrived for |
|---|---|---|
| `agent_contract` | A model, in a future session, possibly a different runtime | An unambiguous instruction it must execute correctly |
| `human_reference` | A person who already knows what they want | To find one thing and leave |
| `human_instructional` | A person who wants to be able to do something new | To finish a task, or change what they can do |
| `human_persuasive` | A person who has not asked for this | To decide whether to care |

---

## `agent_contract` — the rules INVERT here

**Five common craft moves are actively harmful in an instruction a model must execute.**
Each is a virtue for a human reader and a defect here:

| Craft move | Why it works on a human | Why it damages an agent contract |
|---|---|---|
| **Omission** — let the reader join the dots | Respect; engagement | The model needs the clause a human would infer. An unstated condition is an unhandled branch. |
| **The organised gap** — withhold, then resolve | Draws them forward | An unresolved gap in a rule is unspecified behaviour, and the model resolves it by guessing. |
| **Metaphor** | Makes a complex idea unforgettable | Ambiguous referent. "Treat the canvas as a garden" specifies no action. |
| **Felt before understood** | Resonance can precede clarity | There is nothing to feel. Only the literal instruction survives. |
| **Cut for brevity** | Raises the chance of being read | Compression removes the sentence a runtime without hooks depends on. |

**Optimise instead for:** exhaustive branch coverage, one meaning per sentence, explicit
conditions including the ones a competent reader would infer, and the failing case stated
alongside the passing one.

**Model-variance rule.** Hooks do not fire in every runtime. Codex, Cursor, Cline, Gemini
and OSS agents read the prose and get no hook enforcement, so prose that looks redundant
under Claude Code may be the only carrier of a rule elsewhere. **Do not trim an
`agent_contract` file for concision.** If it reads as verbose to a human, that is the
correct trade.

**READMEs inside agent trees are agent contracts.** Not an exception — the load-bearing
case. `integrations/opencode/README.md` states that opencode's strict-JSON schema rejects
comment keys, "so all guidance lives in this README, not the config": it is the sole
carrier of configuration instruction for a runtime with no hooks. `hooks/README.md` is 222
lines of firing conditions and deny semantics. A draft of this change excluded READMEs by
filename on the claim that none carries executable instruction; that claim was false and
was refuted by testing.

**When an `agent_contract` file needs changing, route to a plain edit pass** — no voice
work, no structural rewriting for flow, no tightening.

### The one legitimate exception: a hard size ceiling

`CLAUDE.md` is subject to a CI line-count ceiling (Check 36, the dispatcher-size ratchet),
and `docs/contributing/style.md` sets budgets for other files. An agent obeying "do not
trim" cannot get green CI, so the conflict is real and needs a stated resolution rather
than a preference.

**Over-cap means split, not shrink.** Move a whole coherent rule into a linked file and
reference it; never compress the surviving text.

**And splitting has its own hazard, which must be handled explicitly.** Moving a rule out
of `CLAUDE.md` into a linked file is exactly the "only carrier of a rule in a runtime that
reads no further" failure the model-variance rule names — a runtime that does not follow
links loses the rule entirely. So when splitting: leave a one-line statement of the rule's
*obligation* at the original site alongside the link, not just the link. The detail moves;
the fact that a rule exists does not.

---

## `human_reference` — a lookup surface

The reader arrives knowing what they want and leaves when they have it. There is no
transformation to produce. **Story structure here is the interface-load failure**
`status-translations.md` already names.

Apply: plain language, short sentences, structural signposting.

Do not apply: narrative arc, a withheld reveal, a deliberate peak, a callback.

**Conditional, not mandatory:** an opening line stating the problem the thing solves —
*where one exists.* A 9-line directory manifest or a date-sorted link index solves no
problem and has none to state; forcing one either fabricates a problem or pads the file.
Index and manifest files are complete when they are accurate.

**This class is not a licence to trim.** "Plain language, short sentences" describes how to
*write* a reference file, not permission to compress an existing one that is long because
it is thorough. Length is a defect here only when it comes from duplication or
self-superseded content.

---

## `human_instructional` — the reader must be able to do something new afterwards

The instructional-design evidence applies at full strength here rather than by transfer,
because that literature is *about* this artifact:

- **Coherence.** Remove interesting-but-off-topic material. It does not occupy neutral
  space; it measurably reduces comprehension of what surrounds it.
- **Signalling.** Explicit cues to where the reader is in the sequence.
- **Segmenting.** Parts the reader paces themselves.
- **Personalisation.** Conversational register outperforms formal register.

**The completion test.** Can a reader who did not write this finish the task using only
this? If that has not been checked, the artifact is unverified however well it reads.

For `content_course` and `content_publication` product types this class *is* the product,
and the Definition of Done requires an efficacy criterion accordingly.

---

## `human_persuasive` — the reader has not asked for this

Full craft applies. Two checks specific to this class, both **inspectable properties of the
text** rather than judgements about the audience.

### 1. Register must match the reader's awareness stage

Unaware → problem-aware → solution-aware → product-aware → most-aware. One artifact cannot
serve two stages. The default failure is describing the product to someone who has not yet
agreed they have the problem.

For a problem-aware reader: name the problem precisely enough that they recognise
themselves, then establish that a *category* of solution exists. Not the product.

### 2. Claim type must match how saturated the market is

State the claim → enlarge it → add a mechanism → a better mechanism → switch to identity
and recognition. In a market that has heard every claim in the category, a mechanism claim
lands as one more mechanism claim.

### The honesty constraint

Persuasive technique and propaganda share their mechanics; only intent and truthfulness
differ. Legitimate here because they work on true material: real attributed testimony,
being an identifiable person including the mistakes, and association with sources that
genuinely say what you claim. Not legitimate, because the method *is* the distortion:
presenting only favourable evidence, manufacturing consensus, undefined virtue words,
attacking the reader. Those four are also the cheap ones.

**State the falsifier — where there is a claim to falsify.** Volume of evidence is not a
defence: narrowing a reader's field of view works as well inside a flood of true facts as
in their absence, so the structural difference between evidence-based persuasion and
manipulation is whether the artifact names the condition under which it would be wrong. A
piece citing forty sources that names no falsifier is doing the manipulative move.

**Conditional by length.** A two-line release note or a headline carries no falsifiable
claim and is exempt. The requirement attaches to any artifact making an argument, at any
length; it does not attach to an announcement that something exists.

---

## Mixed and collision cases

Precedence is in Step 1d: scope exclusion first, then `agent_contract` →
`human_instructional` → `human_persuasive` → `human_reference`, stopping at the first
match. `agent_contract` wins every collision it is in, including READMEs.

- **`human_reference` is the residual class** — anything in scope matching nothing else
  lands there. Reference treatment adds no narrative machinery, which is what makes it the
  safe default.
- **A file genuinely serving two human purposes** (a README that is also the landing page):
  resolve by precedence, then treat the persuasive checks as *additional*. Register and
  falsifier apply to the part making a claim; the "do not apply narrative arc" rule
  applies to the part that is reference. This is the one place the classes layer rather
  than replace, and it is why `human_reference` above lists what to apply rather than
  claiming an exhaustive "nothing else."
- **Never infer class from tone.** A chatty `SKILL.md` is an `agent_contract`. A dry
  announcement is `human_persuasive`. Path decides; if the path cannot decide, the residual
  class decides — not a reading of the prose.

### Templates: two classes inside one file

A template is scaffolding *and* prose-in-waiting, so it is classified twice (Step 0a):

- **Scaffolding never gets trimmed** — placeholders, guidance comments, how-to-use blocks,
  and above all **any token a downstream check matches on.** `templates/ai-system-card.md`
  states that its section headings must stay stable because an audit matches on them, and
  `/xai-check` Stage 4 reads its Required/Recommended markings to decide a pass. Tidying
  those breaks a real consumer, silently.
- **Prose the template emits verbatim is written for its destination's class**, not for the
  template's own. The AI-system-card template emits into a consumer's
  `docs/ai-system-card.md`, so that prose is `human_reference`.

The point of splitting it: treating the whole file as `agent_contract` freezes the output
quality forever, and treating it as `human_reference` breaks the checks. Neither single
class is right, because it is not a single kind of file.

### Structured data: no prose class, but the strings still count

JSON, YAML and TOML have no narrative to structure, so no narrative rule applies. Two
things do (Step 0c): the never-trim rule covers comments, keys and structure in
machine-read config inside an agent tree; and **any string value meant for human display —
`description`, `tagline`, `summary`, `title` — is persuasive copy** and takes the register
check. A plugin marketplace description is the same class of copy as a GitHub About field.
The falsifier requirement does not attach to a one-liner that makes no argument.

## Theory grounding

Schwartz (awareness stages, market sophistication); Mayer (coherence, signalling,
segmenting, personalisation); Ellul (propaganda operates within a flood of information,
not its absence); Institute for Propaganda Analysis (technique catalogue, used here as a
sorting device rather than a toolkit). The inversion table derives from Mycelium's own
model-variance rule, not from the communication literature, which does not consider a
non-human reader.
