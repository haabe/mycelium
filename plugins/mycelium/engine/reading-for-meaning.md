# Reading other people's language for meaning (v0.317.0)

**Audience:** the agent, whenever a skill reads what other people said or wrote (interviews, posts, comments,
reviews, support tickets, survey answers, outside descriptions) and classifies, counts or searches it as evidence.

## The rule

People describe the same need, problem or trait in many different words. "I never know what to cook on Tuesdays"
is meal-planning demand without the words "meal planning". "Verdistyrt", "selvstendig" and "selvoppofrende" can all
describe someone who goes against the grain without one of them saying it. **Reading for the words under-counts by
construction, and an absence concluded from a word match is a broken instrument, not a null result.**

So, whenever language is evidence:

1. **State the meaning before you read.** Write down, in the output, the behaviour, need or problem you are looking
   for, in a sentence. Not a term list: what a person would be doing, wanting or struggling with. Read every piece
   of language against that sentence.

2. **Map each piece to the meaning, and name the facet it shows.** Quote the person verbatim (never paraphrase into
   the quote; quotes from untrusted sources stay verbatim for security reasons too), and say beside it which side of
   the meaning it shows. Classifying the meaning is your job; rewording their words is not.

3. **Guard the other side: do not over-map.** A word that fits every meaning supports none. Mapping vague language
   onto the meaning you hoped for is the same error with the sign flipped. Count support only where a story, a
   described moment or a described problem shows the behaviour. Language that is merely compatible with the meaning
   is graded as consistency-only (see `/mycelium:devils-advocate`), not as support.

4. **Prefer stories and moments to adjectives and keywords.** "The last time this happened, I..." carries meaning a
   label cannot. When you design what to collect (an interview, a survey, a scout), ask for moments, not for
   self-descriptions.

5. **A keyword search is a finder, never a counter.** You may search with words to find candidates; you may not read
   its hit count as a rate, or its silence as an absence. Before a search's count is used as a rate, a base rate or
   a projection, read a keyword-free sample of the same source by meaning and report the search's recall on it.
   Worked instance (dogfood, 2026-10-08): a Reddit search filtered by no-users phrases ("nobody uses", "no users",
   "zero signups") fed a projection of about 8 posts a week. The 200 newest posts in two subreddits, read by meaning
   with no keyword filter, held 25 posts at that moment; the phrase filter caught 2 of them, and 3 of its 5 hits were
   not at the moment. (One sample, one reader's meaning judgements on titles and openings: the size of the gap is
   indicative, its direction is not in doubt.) The people said "1 paying customer so far", "nobody cared", "zero purchases", "how do I find my
   first users".

6. **Never conclude absence from a word match.** "Nobody mentioned X", "zero instances", "not found" are findings only
   when they state the meaning sought, how the material was read (by meaning, or by search with its measured
   recall), and the denominator (how many interviews, posts or answers were read in full). Otherwise write "not
   found by this search", which is a fact about the search, not about the people.

## When the words ARE the object

Searching for words is correct when the thing being measured is the wording itself: whether your own phrase has
spread into other products' one-liners (the genericisation pattern in `/mycelium:wardley-map`), a proper name (a
repository, a product, a flag), or an exact quote you are checking. Say so when you do it. A capability, a need or
a behaviour is never the wording: a feature can ship under another name, and a need is said a thousand ways.

## Why this is an instruction and not a hook

A hook that searches for words in order to stop word-matching repeats the defect, and lexical hooks in this
framework are measured to fire often and catch little. The judgement is semantic, so it lives where the reading
happens: in the skill's instructions. What can be checked structurally is that each skill that reads language
points here (validator Check 56).
