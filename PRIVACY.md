# Privacy Policy

**Last updated: 2026-06-19**

Mycelium is a local plugin for AI coding agents (Claude Code and Claude Cowork). It runs entirely inside your own agent, on your own machine. It has no servers, no accounts, and no data-processing backend.

## What Mycelium collects

Nothing. Mycelium does not collect, store, or transmit any personal data, usage data, or telemetry. There is no analytics, no phone-home, no tracking of any kind. The author receives nothing about whether or how you use it.

## Where your data lives

Everything Mycelium creates (your canvas, diamonds, memory, decision log, and evaluations) is written to plain files under `.claude/` in your own project directory. Those files stay on your machine. They never leave it unless you choose to commit or share them yourself. Mycelium has no way to read them outside your local session.

## Network activity

Mycelium makes no automatic network calls. Its hooks and skills run against your local toolchain only.

There is one user-initiated exception: the `/mycelium:metrics-pull` skill, which you run deliberately. When you do, it fetches metrics from third-party services you have configured yourself (for example GitHub, Plausible, or Stripe) using your own credentials. This connects your machine directly to those services to retrieve your own data. The credentials stay in your environment, are never written to logs or reports, and are never sent to the author or anyone else. If you never run that skill, Mycelium makes no network calls at all.

## Third parties

Mycelium shares no data with anyone. When you use the metrics skill above, you are interacting directly with the third-party service you configured, under that service's own privacy policy, not under Mycelium's.

## Children

Mycelium is a developer tool and is not directed at children.

## Changes

This policy may be updated as Mycelium evolves. Changes are tracked in the project's git history and `docs/changelog.md`.

## Contact

Questions or concerns: open an issue at <https://github.com/haabe/mycelium/issues>.
