---
id: 2026-06-23-dagfinn-minilisp-vibe-mistral
date: 2026-06-23
contributor: Dagfinn Dybvig
contributor_link: https://github.com/dagfinndybvig/minilisp
project: MiniLisp (a Lisp interpreter, forked from Norvig's lis.py and extended)
mechanism_or_status: first-arms-length-full-run / no-Claude-in-the-loop / context-budget friction documented
subclass: external-user / cross-runtime / sovereign-stack
---

# minilisp — someone I had never met ran the whole thing on Mistral, and told me where it hurt

**Audience**: anyone wondering whether Mycelium works away from Claude, or whether the discipline survives contact with a person who is not a product developer.
**Time to read**: 4 min.
**Last updated**: 2026-07-25.

## The session

In June 2026 I cold-messaged Dagfinn Dybvig — AI team lead at a university library in Trondheim, mathematician by background — because he posts about Mistral and I wanted to know whether Mycelium's files were portable to a stack with no Claude in it. I asked him to try something small.

He ran a complete project instead. [MiniLisp](https://github.com/dagfinndybvig/minilisp): a Lisp interpreter forked from Peter Norvig's `lis.py` and extended, taken end to end on **Vibe CLI + Mistral** — canvas, diamond tracking, decision log, discovery through to a converged solution, tests, performance targets met. Then he published it as a public repo with the Mycelium development files included, and credited the framework without being asked.

Three things about that are worth stating plainly, because each one is a claim I could not have made for myself.

## What it settled

**Portability, with no Claude anywhere in the loop.** The skills, the canvas format, the gates — all of it ran on a Mistral model through a different CLI. Up to that point "harness-neutral, not Claude-specific" was a design intention I had never watched anyone else exercise. He generated the right files at three separate serving tiers, including Devstral running locally on his own machine.

**That the discipline is light enough for someone who is not a routine product developer.** He is a mathematician and a team lead, not a PM. He still landed a working artifact through the full discovery sequence. Before this it was something I hoped was true.

**That the prior-art step does what it claims.** MiniLisp's `gist.yml` reached for SICP and Norvig. Dagfinn knows both firsthand — which makes him the rare reader who could check rather than be impressed. He confirmed the references were genuine. That is not the model being clever: the gist step forces "what already exists, and how strong is the evidence" before anything gets built, following Gilad's evidence ladder and Torres's discovery work. The going-and-looking is by design. The references landing real is the design working on a capable model, and his check is what turned that from an assumption into a verified one.

## What it cost him — the friction, in his words

He hit the context budget hard, and the useful part is that it has **two distinct faces**, which I had been treating as one:

1. **Window size.** Even Devstral Small 2, even quantised, left limited room once the framework files and his own source were both loaded.
2. **Rate limit × number of file operations.** On the university HPC, serving is strictly rate-limited per unit time by a time-sharing tradition. In busy periods the binding constraint was not the window at all — it was *"for mange filer å lese og oppdatere"*, too many files to read and update.

The second one is not a smaller version of the first. A bigger context window does nothing for it. That distinction came from someone running the thing under real institutional constraints, and I would not have found it on Claude's large window, where I do most of my own work.

He also observed that Vibe and Devstral appear to have been built more or less together, so the model↔CLI fit is tighter than the model list suggests — not every Mistral model is guaranteed to work in Vibe.

## The honest boundary

MiniLisp is an educational project, not his own real work. That distinction matters and I am not going to blur it: running the framework on a Lisp interpreter proves the discipline is *usable*, not that it has been *adopted*. Whether it becomes part of how he actually works is a different signal, and it has not happened. The framework's own definition of done for this stage counts "tried it and it fit" — this counts, at full weight, and it stops there.

I also asked, and he agreed, before naming him here.

## What this case taught the framework

- **The context-budget friction is two problems, not one.** Window size and rate-limit × file-count need different answers. Just-in-time skill loading helps the first. Only reducing the number of file operations helps the second.
- **Verification beats endorsement.** The most valuable thing he did was not the praise, it was knowing SICP well enough to check the citations. A domain expert who can falsify a claim is worth more than ten readers who cannot.
- **The reachable proof was portability, not adoption.** I went looking for whether the files worked elsewhere. I got that, plus a friction report I could not have generated, plus a public artifact. None of it is adoption, and pretending otherwise would be the exact self-flattery this framework is built to interrupt.

---

**Have you run Mycelium on something?** I would genuinely like to know, whether it worked or whether it fell over. This case is both at once: a finished interpreter and the friction report that came with it. Open an issue, start a [discussion](https://github.com/haabe/mycelium/discussions), or just tell me.
