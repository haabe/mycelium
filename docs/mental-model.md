# How to think in Mycelium

**Audience**: practitioners on their first or second project — people who have installed Mycelium and want the mental model before the vocabulary piles up.
**Time to read**: 8 min.
**Last updated**: 2026-06-01.

This page teaches the model. It is not a reference (that is [the skills index](skills/README.md)), not a defense of the design (that is [philosophy.md](philosophy.md)), and not a dictionary (that is [glossary.md](glossary.md)). It walks you through one real project so the concepts arrive while you watch them work, instead of as a list to memorize.

If you have not installed yet, do [the install and first round](get-started.md) first — this reads better once you have run `/mycelium:start` once.

## The problem you already know

Point an AI agent at an idea and it will build. It will scaffold the repo, write the component, open the pull request — fast, and often before anyone has asked *why this*, *who for*, or *whether the thing is wanted at all*. The cost of that jump is not the agent's. It is yours, paid later, when you throw the wrong build away.

Mycelium exists to make the agent **earn the right to start**. That single idea is the whole model. Everything below is mechanism in service of it.

## The one move: a gate asks for evidence

When the agent wants to move from "exploring a problem" to "committing to a build," it hits a **gate**. A gate is not a checklist the agent fills in to look thorough. It is the agent stopping and saying: *show me the evidence that this next step is worth it.* If the evidence is not there, the agent does not proceed — it tells you what is missing and what would satisfy it.

That is the move you will see over and over. Learn to recognize it and the rest of the framework stops feeling like ceremony, because every other part is either feeding a gate or acting on what a gate let through.

## The two questions you are always answering

At any moment in a Mycelium project you are answering two questions. Hold these two and you can place yourself anywhere in the framework without a map.

**1. What am I deciding right now?** — This is the **scale**. There are six, from the most fundamental to the most concrete:

- **Purpose** (why this exists at all)
- **Strategy** (where to play)
- **Opportunity** (which problem to solve)
- **Solution** (how to solve it)
- **Delivery** (build and ship)
- **Market** (reach the people)

You do not march through all six every time. A weekend project might decide its purpose is obvious and jump toward a solution. A company-shaping bet might spend weeks at strategy. The framework reads your project and tells you which scales earn their cost — [more on that below](#the-one-heuristic).

**2. Am I opening up or closing down?** — This is the **diamond**. Whatever you are deciding, you do it in four phases that widen, then narrow, twice:

- **Discover** — go wide, gather evidence, resist deciding
- **Define** — narrow to the real problem
- **Develop** — go wide again on possible answers
- **Deliver** — narrow to the one you will build, and ship it

The shape is a diamond because you diverge before you converge. The same diamond runs at every scale — deciding your *purpose* and deciding your *delivery* both move Discover → Define → Develop → Deliver. That self-similarity is the thing to internalize: once you know the diamond, you know how decisions are made at every level.

Between phases sit the gates. You do not slide from Discover to Define because you feel ready; you pass when the evidence says you may.

## Watch it work: a project that never shipped

Abstract so far. Here is the model running on one real Mycelium project — a planned macOS file viewer. Watch the two questions and the one move do their job.

**Scale: Purpose. Phase: Discover.** The idea was a better file viewer for macOS. An unharnessed agent would have started scaffolding a window. Mycelium instead held the project at the *purpose* scale and asked the Discover question: who is this for, and would they actually switch?

There were no real users to interview yet, so the work used **mocked personas** — explicitly invented stand-in users, tagged as speculation, not evidence, so nobody mistakes them for the real thing. Six personas, asked one question: would you switch from your current default file viewer?

**The gate.** To move from Discover toward building anything, the project hit the evidence gate. The gate asked for a reason to believe the build was wanted. The answer that came back: **four of the six personas would not switch — including the modal user, the one most people resembled.**

That is not a passing grade. The gate held. The project was **killed in Discovery, before a line of code was written.**

And here is the part the model is built to make visible: the kill was the framework *succeeding*, not failing. The project that did not ship produced a twelve-finding report that the framework then turned into mechanism — more durable value than either project that did ship in the same period. (The full receipt: [what Mycelium stopped, and what that gave it](receipts/cases/2026-04-macos-fileviewer.md).)

You just watched the whole model in one story: the project sat at a **scale** (Purpose), inside a **phase** (Discover), and a **gate** asked for **evidence** the build was wanted. The evidence said no, so the agent did not get the right to start.

## What this lets you do

Read that story again and notice what became possible. Not "ship faster" — every tool promises that. What Mycelium makes possible is **killing the wrong build before you build it**, with a reason you can point to. The mocked-persona exercise cost an afternoon. The file viewer would have cost weeks, and you would have learned the same thing at the end instead of the start.

That is the art of the possible here: the expensive mistakes move from *after* the work to *before* it, where they are cheap. A gate that stops you is not friction for its own sake — it is the cost of the wrong build, paid early and small.

## The one heuristic

If you remember one rule for *how much* framework to use:

> The rougher the idea, the more scales earn their cost. The clearer the idea, the fewer you need.

If you already know who it is for, what "done" means, and that the problem is real, the discovery scales (Purpose, Strategy, Opportunity) have little to add — you are past the part Mycelium is built for, and lighter execution tools fit better ([who it is not for](../README.md#who-its-not-for)). If your idea is a rough hunch, those scales are exactly where the wrong-build risk hides, and the gates earn their keep.

The framework recommends a depth from how you answer `/interview`; you can always override it. It scales to your project, not the other way around.

## Where to go next

- Why the framework is opinionated rather than optional: [philosophy.md](philosophy.md)
- A term you hit and want the two-sentence answer for: [glossary.md](glossary.md)
- The 30+ frameworks behind the gates: [theories.md](theories.md)
- Apply it solo, on a team, or with parallel agents: [usage-modes.md](usage-modes.md)
- More stories of the framework catching itself: [docs/receipts/](receipts/README.md)
</content>
</invoke>
