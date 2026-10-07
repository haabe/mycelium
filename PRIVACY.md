# Privacy Policy

**Last updated: 2026-10-03**

Mycelium is a local plugin for AI coding agents (Claude Code, and also Codex, Cursor and opencode). It runs entirely inside your own agent, on your own machine. It has no servers, no accounts, and no data-processing backend.

## What Mycelium collects

Nothing. Mycelium does not collect, store, or transmit any personal data, usage data, or telemetry. There is no analytics, no phone-home, no tracking of any kind. The author receives nothing about whether or how you use it.

## What runs on your machine

Mycelium is a set of shell hooks, Python scripts and markdown skills, all inside the plugin's own folder. Claude Code (or Codex, Cursor or opencode) runs the hooks on its own events: before and after tool calls, when you send a prompt, when a response ends, and when a session starts. The hooks run `bash` and `python3`, local `git` commands, and in one place the GitHub CLI (`gh`, below). The full list, with which hooks can refuse a tool call and which only warn, is in [`plugins/mycelium/hooks/README.md`](plugins/mycelium/hooks/README.md). Mycelium ships no MCP servers, no binaries and no agents.

Nothing installs itself. `/mycelium:setup` offers to install PyYAML from PyPI into the plugin's own data folder, and does it only if you say yes. The build and release gates need PyYAML and refuse rather than allow without it.

## Where your data lives

Everything Mycelium keeps about your project (your canvas, diamonds, memory, decision log, and evaluations) is written to plain files under `.claude/` in your own project directory. That includes small local logs of which guard rules fired. By default those logs record the rule and never your command; if you set `MYCELIUM_LEDGER_TRIGGER=on` yourself, they also keep the first 200 characters of the command with obvious secrets masked. They are plain files under `.claude/state/`. Since version 0.226.0, `/mycelium:setup` adds an ignore file there so they are not committed; if your project was set up earlier, run `git ls-files .claude/state` to see whether any are tracked. At session start a hook also updates the next steps it derives for your open diamonds, in `.claude/diamonds/` and the canvas; `MYCELIUM_CLOSING_PATH_WRITE=off` turns that off.

A few things are written or read outside `.claude/`:

- Two small stamp files in your system's temporary folder, one recording that the preflight ran and one caching the last CI result.
- `/mycelium:setup` offers an `AGENTS.md` at your project root (in non-interactive mode it writes one by default), and the optional PyYAML install above goes in the plugin's data folder.
- `install-runtime-hooks.sh`, if you run it for Cursor or Codex, writes `.cursor/hooks.json` or `.codex/hooks.json` in your project.
- At session start a check reads Claude Code's own transcripts for this project (under `~/.claude/projects/`) to see whether its hooks were delivered. It only reads them, and only on your machine.
- If you set `release_repo` (or `MYCELIUM_CROSS_REPO_WATCH`), a check reads the commit subjects of that other repository. Unset, the default, it reads only this project.

None of it leaves your machine unless you commit or share it yourself.

## Network activity

Mycelium sends nothing to its author or to any service the author runs. It reads no credential on its own; the one place credentials are used is `/mycelium:metrics-pull`, which, when you run it, uses the credentials you set up for each source you confirmed (below).

There is one automatic network call, and it goes to GitHub on your behalf. If your project has a `.github/workflows/` directory and you have the GitHub CLI (`gh`) installed and logged in, a hook asks GitHub for the result of the latest CI run on your current branch, at the start of a session and occasionally when a response ends, so that a failed build is reported in the session that caused it. It uses `gh`'s own login, sends only your repository and branch name, is rate-limited, and does nothing at all when there are no workflows, no `gh`, or no login. To turn it off, set `MYCELIUM_CI_SIGNAL=off` in your environment.

Everything else that touches the network runs only when you start it:

- **`/mycelium:setup`**: the PyYAML install from PyPI, if you accept it.
- **`/mycelium:metrics-pull`**: fetches metrics from services you have configured yourself (for example GitHub, Plausible, or Stripe) with your own credentials, and asks Hacker News's search API (hn.algolia.com) for mentions of your repository by name. Your credentials stay in your environment and are never written to logs or reports.
- **`/mycelium:canvas-health`**: checks that the links cited in your canvas and docs still resolve, by requesting each one, at most once every 14 days. No credentials are sent.
- **`/mycelium:theory-fidelity`**: uses your agent's own web search and fetch tools to check sources.
- **`/mycelium:canvas-sync`**: runs `git pull` on your repository.
- **`/mycelium:a11y-check`**: may suggest accessibility tools (`npx axe`, `lighthouse`, `pa11y`) for you to run; it does not run them itself.

## Third parties

Mycelium shares no data with anyone. When a skill above contacts a service (GitHub, PyPI, a metrics service you configured, Hacker News search, or the sites your canvas cites), you are interacting directly with that service, under its own privacy policy, not under Mycelium's.

## Children

Mycelium is a developer tool and is not directed at children.

## Changes

This policy may be updated as Mycelium evolves. Changes are tracked in the project's git history and `docs/changelog.md`.

## Contact

Questions or concerns: open an issue at <https://github.com/haabe/mycelium/issues>.
