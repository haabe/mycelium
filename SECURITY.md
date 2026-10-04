# Security Policy

**Last updated: 2026-10-04**

Mycelium is built and maintained by one person. This page says plainly what that means for reporting a security problem. There is a private way to reach me, I answer it, and I do not promise round-the-clock cover.

## What counts

Mycelium runs on your own machine, inside your own coding agent. It has no servers, no accounts and collects nothing (see [PRIVACY.md](PRIVACY.md)). So the problems worth reporting here are about what runs locally and how it reaches you:

- A hook or script in the plugin that can be made to do something harmful on the machine it runs on.
- The supply chain: anything that would let someone other than me publish code that installers then run.
- Prompt injection through files Mycelium reads into the agent's context, such as canvas or memory files.
- Mycelium leaking something it should not, for example a file or a secret written where it does not belong.

Not here: vulnerabilities in Claude Code, Codex, Cursor or opencode themselves (report those to their makers), and the general behaviour of the AI model.

## How to report

Use **"Report a vulnerability"** on the [Security tab](https://github.com/haabe/mycelium/security) of this repository. The report stays private between you and me until a fix is out.

Please do not open a public issue for a vulnerability.

## What to expect

- **I acknowledge within 7 days.** Best effort, since this is a solo project and not a staffed security team.
- **I aim to fix or mitigate serious issues within 30 days**, and will tell you if it will take longer and why.
- **Only the latest release is supported.** Fixes ship as a new release.
- **Credit is yours if you want it** in the advisory and the changelog.
- **If you hear nothing within 14 days,** open a public issue that says only "security report pending", with no details. That reaches me without disclosing anything.

There is no bug bounty.

## If you need stability meanwhile

Pin the plugin to a release tag rather than following `main`. Every release is tagged at the commit that set its version, and `main` only accepts signed commits that have passed CI.
