# Purpose stance — does this contradict what you said you were building?

Mycelium asks you for a `why`, a `how` and a `what` at L0. Until v0.120.0 **nothing below ever
checked anything against them.** A solution could contradict your product's own definition and pass
every gate the framework had.

## The problem, in two examples

**A healthcare app.** *Why*: people deserve care without anxiety about their records. *How*:
accessible and secure. *What*: full medical history across providers.
An OST solution that stores records unencrypted **contradicts** what you said you were building.

**A microblog.** *What*: anonymous users post short strings of emoji. *Why*: your own reasons.
A solution that requires login **contradicts** it.

Neither is a matter of taste. Neither needs anyone to judge whether the solution is *good*. Each is a
solution doing something the product definition rules out.

## What this does, and what it deliberately does not

**It does not decide whether a solution serves your purpose.** That judgement is unreliable — the
published benchmarks put frontier models at 39–77% factual accuracy when asked to verify claims
against sources — and a checker that accurate on its own subject is a second opinion wearing a gate's
clothes.

**It checks that somebody said something.** Every solution declares a stance against each binding
property, and **silence is the finding.** The insecure login is not caught by judging it. It is
caught because nothing said anything about the constraint that forbids it.

## How it works

**1. Properties are extracted from your why/how/what at L0.** The agent proposes; you confirm. They
are stored in `purpose.yml`:

```yaml
purpose_properties:
  derived_from_hash: "<sha256 of your why + how + what>"
  confirmed_by: human
  properties:
    - id: pp-001
      property: anonymous
      verbatim: "anonymous users only can post"
      source: what
      binding: true
      contradicted_by: ["sign-in with Google before posting"]
```

**`binding` is yours to set.** A why/how/what yields many adjectives; you mark the few whose
violation would break the product. Nothing else is ever checked.

**2. Words that cannot be checked are caught at the door.** Measured with a blind test on 2026-08-23:
*"accessible and secure"* yields **no checkable property**, because every candidate solution claims
to satisfy it. So the extractor asks you:

> You said "secure". Name one thing a solution could do that would make you say "no, that's not secure."

Pick from what it offers or give your own. **If you cannot answer, the word is an aspiration rather
than a constraint** — it is recorded as one, and excluded from every check. Skipping is fine, and the
skip is recorded with its consequence: *"'secure' was left undefined, so no solution will be checked
against it."*

**3. Solutions declare a stance.**

```yaml
purpose_stance:
  pp-001: { verdict: preserves,      note: "no account required; posts are session-scoped" }
  pp-002: { verdict: not_applicable, note: "storage layer only, no posting surface" }
```

Three verdicts: `preserves`, `not_applicable`, `contradicts`. **Every one needs a note, including
`not_applicable`** — otherwise the field fills with whatever makes the record look complete.

**4. A contradiction can be accepted, but only by you.**

```yaml
  pp-001: { verdict: contradicts, note: "requires login",
            override: { human: "your-name", decision: "DL-1234" } }
```

**An agent may not clear a contradiction.** Without a human on the override, an agent could declare
one and clear it in the same run, and the mechanism would nullify itself while every record looked
complete. A solution may knowingly contradict your definition — it may not do so silently.

**5. Change your purpose and every stance below it is superseded.** The hash stops matching, and the
check says so. Your reasons for a solution were given under a definition you have since changed.

## When it runs

| Where | What it asserts | Tier |
|---|---|---|
| `validate_canvas.py`, CI | stances present, notes present, hash fresh | **warn, never fails** |
| `check_purpose_stance.py --strict` | the same, as a gate | **exit 1** |

**If your project has no `purpose_properties`, every check is silent.** Nothing you already have
breaks, and nothing nags you into adopting this.

## Why it is worth the friction

The failure it prevents is not exotic. It is building the thing you said you would not build, one
reasonable-looking solution at a time, with every individual step passing review.
