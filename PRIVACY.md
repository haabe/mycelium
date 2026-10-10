# Privacy Policy

**Last updated: 2026-10-10**

Mycelium is a local plugin for AI coding agents (Claude Code, and also Codex, Cursor and opencode). It runs entirely inside your own agent, on your own machine. It has no servers, no accounts, and no data-processing backend.

## What Mycelium collects

Nothing. Mycelium does not collect, store, or transmit any personal data, usage data, or telemetry. There is no analytics, no phone-home, no tracking of any kind. The author receives nothing about whether or how you use it.

## What runs on your machine

Mycelium is a set of shell hooks, Python scripts and markdown skills, all inside the plugin's own folder. Claude Code (or Codex, Cursor or opencode) runs the hooks on its own events: before and after tool calls, when you send a prompt, when a response ends, and when a session starts. The hooks run `bash` and `python3`, local `git` commands, and in one place the GitHub CLI (`gh`, below). The full list, with which hooks can refuse a tool call and which only warn, is in [`plugins/mycelium/hooks/README.md`](plugins/mycelium/hooks/README.md). Mycelium ships no MCP servers, no binaries and no agents.

Nothing installs itself. `/mycelium:setup` offers to install PyYAML from PyPI into the plugin's own data folder, and does it only if you say yes. The build and release gates need PyYAML to judge a project that uses Mycelium, and refuse rather than allow without it. In a project with no `.claude/diamonds/active.yml` the release gate has nothing to judge and allows, with or without PyYAML.

## Where your data lives

Everything Mycelium keeps about your project (your canvas, diamonds, memory, decision log, and evaluations) is written to plain files under `.claude/` in your own project directory. At session start a hook also updates the next steps it derives for your open diamonds, in `.claude/diamonds/` and the canvas; `MYCELIUM_CLOSING_PATH_WRITE=off` turns that off.

### The logs the hooks keep

The hooks also keep logs in `.claude/state/`, in every project the plugin runs in, including one where `/mycelium:setup` never ran. They are how Mycelium checks its own guards. Every line is dated, and most carry the id Claude Code gave the session.

| Log | What one line holds |
|---|---|
| `read-log.jsonl` | The path of a file the agent opened, or that a shell command read when Mycelium can tell. |
| `change-log.jsonl` | The path of a file the agent created or edited, and the tool it used. |
| `diamond-state-audit.jsonl` | That `.claude/diamonds/active.yml` was edited directly, and by which tool. |
| `read-before-research-log.jsonl` | Up to six names or quoted phrases from a web search the agent ran, and whether your canvas already mentioned them. |
| `reflexion-log.jsonl` | That a command failed: its exit code and the program's name (`git`, `npm`). Never the command or its output. |
| `shell-safety-guard-log.jsonl` | Which shell-safety rule fired. Never the command. |
| `absence-claim-guard-log.jsonl`, `key-shape-guard-log.jsonl` | Which rule fired, the file name, and up to 120 characters of the text it matched in what the agent was writing. |
| `discovery-trigger-log.jsonl` | That a prompt matched a discovery phrase, as a hash and a length. Never the words. |
| `exposure-uses.jsonl` | A release the gate allowed or asked you about: up to 80 characters of the release command, obvious secrets masked, and the exposure it was approved under. |
| `skip-ack-uses.jsonl` | The paths a skip-ack of yours let through. |
| `advisory-ledger.jsonl` | Your rulings on Mycelium's advisories, with the note given. |
| the other `*-fires.jsonl`, `gate-block-log.jsonl`, `denied-calls.jsonl` | Which hook fired, what it decided, and the tool call's id. |

`.claude/state/bash-guard/` holds a copy of `.claude/diamonds/active.yml` from before the last shell command, replaced each time, so that a shell edit to it can be judged.

**Commands.** No log keeps a command or its output by default. If you set `MYCELIUM_LEDGER_TRIGGER=on` yourself, the reflexion log also keeps the first 160 characters of each failed command and 200 of its error output, and the shell-safety log the first 200 characters of each command it warned about, all with obvious secrets masked. Masking knows token prefixes, auth headers, secret-named variables and flags, and passwords in URLs; a secret in any other shape is kept as typed, which is why this is off by default. Before version 0.318.0 the reflexion log kept failed commands and their error output, unmasked, by default. The first session on 0.318.0 or later removes that text from the log.

**How long.** Nothing trims or deletes these logs: each line stays until you delete it. Deleting a log loses only its history, and the hooks start a new one. Keep `delivery-skip-ack`, `discovery-skip-ack`, `brownfield-ack` and `upstream.json` in that folder: they record decisions you made.

**Not committed.** Since version 0.318.0, any hook that finds `.claude/state/` without an ignore file writes one; before that only `/mycelium:setup` did (from 0.226.0). It keeps the logs out of git and the four decision files above in. If you used an earlier version, run `git ls-files .claude/state` to see whether a log is already tracked.

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
