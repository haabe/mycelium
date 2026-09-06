# Nobody used it. Now what.

**Audience**: builders who shipped something the agent built, and nothing happened. Practitioners.
**Time to read**: 5 min.
**Last updated**: 2026-09-06.

It has been three weeks. The launch post got eleven upvotes and two comments, one of them yours. You have rewritten the landing page four times and you still cannot say in one sentence what it is for. The thing works. That was never the problem.

I went looking for how common this is, because I had a feeling and a feeling is not a number. I read 46 posts by people in exactly that spot. I could only count what they chose to write down, so treat this as a floor. In 37 of them, nobody who had the problem was ever asked. Not before, not after. In six, someone was asked sideways, a sales call, a favour. In three there were existing users. Whether any of the nine asked before they built, the posts do not say. [The read is here](receipts/cases/2026-08-16-l1-population-read.md), all 46.

I do not think anyone in those posts believed asking was optional. I have been on teams for more than fifteen years and I never met anyone who did. There was always something in the way, and it was usually reasonable. What has changed is that the agent removed the last reason to wait. It is ready now, and asking takes days.

## What I did about it, for myself

I put four questions in the agent's way. What is the problem. Who has it. What are you assuming. What would show you wrong. They come up the first time the agent reaches for a new source file in a repo where nothing has been written down, and your answers go into the repo as a file the agent is then held to. Ten minutes, once per project. After that it is quiet.

That is the whole mechanism, and it is worth being plain about what it is not. It will not stop a running agent from rewriting your service. There is a scope check that holds writes outside the paths a cycle said it would touch, and that is as far as it goes. People on the same forums have built better leashes than that, and if a leash is what you came for, go and find theirs.

## The one time I know it worked

It stopped me. The first project it ever ran on was a file viewer for macOS that I wanted. It never got a line of code, because when I went and asked, nobody else wanted it, including the one person I had been picturing the whole time. I do not know what building it would have cost me. Nobody does, which is the honest shape of evidence about a thing that did not happen. What I can count is that [the write-up](receipts/cases/2026-04-macos-fileviewer.md) lists ten mechanisms that came out of that kill, and the framework runs on them.

One kill, on my own idea, is not proof. I know that. It is the only case where I was there for both halves.

## Before you install anything

Someone I have never met ran it on [a Lisp interpreter](https://github.com/dagfinndybvig/minilisp/blob/main/.claude/canvas/gist.yml) and left his ten minutes in the repo. He is not a developer. Read what he got out of it first. It costs about six thousand tokens a session, always on, measured on my own machine, and four hooks can hold work back. The README lists all four.

If you want to try it, this is all of it.

```
/plugin marketplace add haabe/mycelium
/plugin install mycelium@haabe-mycelium
/mycelium:start
```

Then run it on three real projects. Not one. If it never once changed what you built, say so and uninstall it. I can be given that result and I cannot argue with it.

[README](../README.md)
