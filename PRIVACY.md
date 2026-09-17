# Privacy Policy

**Last updated: 2026-06-19**

Mycelium is a local plugin for AI coding agents (Claude Code and Claude Cowork). It runs entirely inside your own agent, on your own machine. It has no servers, no accounts, and no data-processing backend.

## What Mycelium collects

Nothing. Mycelium does not collect, store, or transmit any personal data, usage data, or telemetry. There is no analytics, no phone-home, no tracking of any kind. The author receives nothing about whether or how you use it.

## Where your data lives

Everything Mycelium creates (your canvas, diamonds, memory, decision log, and evaluations) is written to plain files under `.claude/` in your own project directory. That includes small local logs of which guard rules fired. By default those logs record the rule and never your command; if you set `MYCELIUM_LEDGER_TRIGGER=on` yourself, they also keep the first 200 characters of the command with obvious secrets masked. They are plain files under `.claude/state/` and go wherever you take that directory: if you commit it, they are committed with it. Those files stay on your machine. They never leave it unless you choose to commit or share them yourself. Mycelium has no way to read them outside your local session.

## Network activity

Mycelium sends nothing to its author or to any service the author runs. Its hooks and skills run against your local toolchain.

There is one automatic network call, and it goes to GitHub on your behalf. If your project has a `.github/workflows/` directory and you have the GitHub CLI (`gh`) installed and logged in, a hook asks GitHub for the result of the latest CI run on your current branch, at the start of a session and occasionally when a response ends, so that a failed build is reported in the session that caused it. It uses your own `gh` login, asks only about your own repository, is rate-limited, and does nothing at all when there are no workflows, no `gh`, or no login. To turn it off, set `MYCELIUM_CI_SIGNAL=off` in your environment.

There is one user-initiated network feature: the `/mycelium:metrics-pull` skill, which you run deliberately. When you do, it fetches metrics from third-party services you have configured yourself (for example GitHub, Plausible, or Stripe) using your own credentials. This connects your machine directly to those services to retrieve your own data. The credentials stay in your environment, are never written to logs or reports, and are never sent to the author or anyone else. If you never run that skill, the CI check above is the only network activity.

## Third parties

Mycelium shares no data with anyone. When you use the metrics skill above, you are interacting directly with the third-party service you configured, under that service's own privacy policy, not under Mycelium's.

## Children

Mycelium is a developer tool and is not directed at children.

## Changes

This policy may be updated as Mycelium evolves. Changes are tracked in the project's git history and `docs/changelog.md`.

## Contact

Questions or concerns: open an issue at <https://github.com/haabe/mycelium/issues>.
