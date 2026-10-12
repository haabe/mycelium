# Privacy Policy

**Last updated: 2026-10-12**

Mycelium is a local plugin for AI coding agents (Claude Code, and also Codex, Cursor and opencode). It runs entirely inside your own agent, on your own machine. It has no servers, no accounts, and no data-processing backend.

## What Mycelium collects

Mycelium sends no personal data, usage data or telemetry to anyone. There is no analytics, no phone-home, no tracking of any kind. The author receives nothing about whether or how you use it. One request does leave your machine without you starting it: Mycelium asks GitHub, through your own `gh` login, for the latest CI result on your branch (Network activity, below, says when, and how to turn it off). What Mycelium keeps stays on your own disk, in your own project: its hooks write activity logs and a few small state files there, listed below.

## What runs on your machine

Mycelium is a set of shell hooks, Python scripts and markdown skills, all inside the plugin's own folder. Claude Code (or Codex or Cursor) runs the hooks on its own events: before and after tool calls, when you send a prompt, when a response ends, and when a session starts. opencode does not run them. There, `/mycelium:setup` can copy a small plugin of Mycelium's into your project (below). It gives the agent Mycelium's reminders, and it refuses an edit or a write to a file the agent has not read in that session, a new file included. On opencode 2.x it also adds a line to the error text of every tool call that fails, telling the agent not to retry blindly and to record a project mistake in `.claude/memory/corrections.md`. The build and release gates, the scope check and the secret scan do not run on opencode. The hooks run `bash` and `python3`, local `git` commands, and in one place the GitHub CLI (`gh`, below). The full list, with which hooks can refuse a tool call and which only warn, is in [`plugins/mycelium/hooks/README.md`](plugins/mycelium/hooks/README.md). Mycelium ships no MCP servers, no binaries and no agents.

To do their work the hooks read what the agent is about to do. Before a tool call they read the call itself: the file path and the text being written, and for a shell command the whole command. The secret scan runs on both, so a shell command whose own text carries something shaped like a password or a key is refused, as a write of it to a file would be. The scan covers every file inside your project, your canvas and notes under `.claude/` included (from 0.322.3; until then nothing under `.claude/` was scanned), except Mycelium's own `.claude/state/` folder. It does not cover a file outside the project. And it knows a fixed set of shapes: a quoted password or key, common token prefixes, a database address that carries a password. A secret in another shape is not caught. When you send a prompt a hook reads it, to match a few phrases. When a response ends a hook reads the session's transcript (below). All of this is read in memory, on your machine. What is kept of it is listed in the tables below.

Nothing installs itself. `/mycelium:setup` offers to install PyYAML from PyPI into the plugin's own data folder, and does it only if you say yes. The build and release gates need PyYAML to judge a project that uses Mycelium, and refuse rather than allow without it. In a project without Mycelium the hooks do nothing, so neither gate runs. In one that uses Mycelium but has no `.claude/diamonds/active.yml` yet, the release gate has nothing to judge and allows, with or without PyYAML.

## Where your data lives

Everything Mycelium keeps about your project (your canvas, diamonds, memory, decision log, and evaluations) is written to plain files under `.claude/` in your own project directory. At session start a hook also updates the next steps it derives for your open diamonds, in `.claude/diamonds/` and the canvas; `MYCELIUM_CLOSING_PATH_WRITE=off` turns that off. Session start also adds one to the `sessions` number in each open counter file under `.claude/evals/assumption-tests/` (`*.count.json`). A counter exists only where you or the agent made one, to count sessions for a test, and it stops being counted once it is marked closed. These are ordinary project files that git tracks, so the change shows in `git status`. (Until 0.322.3 a session start on Claude Code added two, because the hook runs in two passes and both counted.)

### The logs the hooks keep

Only in a project that uses Mycelium. That means one with a `.claude/canvas/` or `.claude/diamonds/` folder, which `/mycelium:start` and `/mycelium:setup` create. Anywhere else the hooks do nothing and write nothing. The one exception sits outside the project, a timestamp in your temp folder (`mycelium-hooks-alive-<your user id>`), so setup can tell whether its hooks run at all.

In a project that uses Mycelium, the hooks keep logs in `.claude/state/`. That is how Mycelium checks its own guards. Every line is dated, and most carry the id Claude Code gave the session.

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
| `advisory-ledger.jsonl` | Mostly one record per session: which of Mycelium's standing reminders were present at session start, by reminder name and count, and which had cleared since the session before, with the session id. Also each reminder it muted, and your rulings on those, with the note given. |
| the other `*-fires.jsonl`, `gate-block-log.jsonl`, `denied-calls.jsonl` | Which hook fired, what it decided, and the tool call's id. |

The same folder holds a few small files that are not logs. They are how a hook remembers something from one moment to the next.

| File | What it holds |
|---|---|
| `session-checks.json`, `session-checks.pending` | The text of the reminders that the slower session-start checks produced, kept until your next prompt delivers it, with the session id and the time. The text is Mycelium's own findings about your project, so it names your canvas entries and files. Replaced when the checks run again. |
| `next-item.json` | The one next item session start picked: its id, the text shown to the agent and to you, the session id and the date. Rewritten at session start. |
| `next-item-log.jsonl`, `diamond-rulings.json` | Per next item that left: its id, dates and how many sessions it was shown. Per diamond: its id and scale, a short signature of its recorded decisions, a time, the session id and a count of its evidence. For a diamond that delivers (L3 to L5), also a copy of its exposure records as your diamonds file holds them: who the work reaches, through what channel, what class of data, until when. That part is your own canvas text, kept so that a repair of a broken diamonds file can be judged against the last good state. |
| `reflexion-ledger.json`, `reflexion-dismissed.jsonl` | Two counts and a date, used to match failed commands against new corrections. And each failure someone dismissed, with the reason typed. |
| `interview-in-progress.md` | Your answers to the opening questions so far, in your own words, so an interrupted interview can resume. Removed when the brief is written. |
| `nudge-seen.jsonl`, `canvas-check-skipped`, `exposure-line-said`, `conditional-snoozes-said`, `stop-check-counts-shown`, `exposure-last` | Markers that keep a reminder to once per session: a session id with a date, a file name or a count. `exposure-last` is one word, `ready` or `not-ready`. |
| `hooks-alive`, `log-prune-last`, `skip-ack-legacy-since` | Empty, or one date. What is read is how old the file is. |
| `scale-lock-ack` | One line for each scale lock you chose to open past, in your own words. A decision of yours, so it is kept in git with the four named below (from 0.322.2; until then it was ignored, which was an oversight). |
| `active-execution.json` | The paths a delivery cycle said it would touch, which the scope check holds writes to. Working state for that one cycle, and not committed. |

`.claude/state/bash-guard/` holds a copy of `.claude/diamonds/active.yml` from before the last shell command, replaced each time, so that a shell edit to it can be judged. Since 0.321.1 it also holds, while a shell command runs, a copy of each file that switches one of Mycelium's stops off (the skip and lock files under `.claude/state/`, `.claude/manifest.yml`), so that a change you were not asked about can be put back; the copies are removed when the command ends. Beside the copies it keeps a time stamp, and for each running command a small index: which of those files existed, and which the command was seen to write.

**Commands.** One log keeps part of a command by default: `exposure-uses.jsonl`, above, keeps up to 80 characters of a release command, with obvious secrets masked. No other log keeps a command or its output unless you ask it to. Set `MYCELIUM_LEDGER_TRIGGER=on` and the reflexion log also keeps the first 160 characters of each failed command and 200 of its error output, and the shell-safety log the first 200 characters of each command it warned about. All of it with obvious secrets masked. Masking knows token prefixes, auth headers, secret-named variables and flags, and passwords in URLs. A secret in any other shape is kept as typed, which is why it is off. Before 0.318.0 the reflexion log kept failed commands and their error output, unmasked, by default. The first session on 0.318.0 or later removes that text.

**How long.** 90 days. At session start, at most once a day, Mycelium removes activity lines older than that. Set `MYCELIUM_LOG_RETENTION_DAYS` to another number of days, or to `0` to keep everything. A line with no readable date stays, since its age is unknown. Records of decisions are never trimmed. `advisory-ledger.jsonl`, `reflexion-dismissed.jsonl`, `exposure-uses.jsonl`, `skip-ack-uses.jsonl`, `next-item-log.jsonl` and `nudge-seen.jsonl` keep every line until you delete them. Deleting a log loses its history and nothing else; the hooks start a new one. Keep `delivery-skip-ack`, `discovery-skip-ack`, `brownfield-ack`, `scale-lock-ack` and `upstream.json`. Those are decisions too.

**Switches.** Some environment variables change what the hooks do, and [`docs/environment.md`](docs/environment.md) lists every one. Three of them loosen a stop. `MYCELIUM_GUARD_STATE_EDIT=1` lets the files that switch a stop off be written without you being asked. `MYCELIUM_NEXT_ACTION_CHECK=off` stops the check that a turn ends by saying what comes next. `MYCELIUM_TODAY` sets the date Mycelium treats as today, and a date in the past makes an expired skip-ack count as current. They are there for you to set, in the environment you start your agent from. A hook cannot tell who set a variable. Unset, which is the default, every stop is on.

**Not committed.** From 0.318.0 any hook that finds `.claude/state/` without an ignore file writes one. Before that only `/mycelium:setup` did, from 0.226.0. The logs stay out of git and the five decision files stay in. An ignore file that already exists is never rewritten, so one written by an earlier version may ignore a decision file that a later version keeps. From 0.322.2 session start tells you when a decision file of yours is ignored by that file, and gives the line to add. It asks git (`git check-ignore`) about those few files and changes nothing; whether to commit one is yours to decide. On an earlier version? Run `git ls-files .claude/state` to see whether a log is already tracked. Versions before 0.318.0 also wrote logs in projects that never used Mycelium. A `.claude/state/` folder in one of those is left over from that, and safe to delete.

A few things are written or read outside `.claude/`:

- Two small stamp files in your system's temporary folder, one recording that the preflight ran and one caching the last CI result.
- `/mycelium:setup` offers an `AGENTS.md` at your project root (in non-interactive mode it writes one by default), and the optional PyYAML install above goes in the plugin's data folder.
- `/mycelium:setup` also looks for signs that you use opencode: an `opencode.json` or a `.opencode/` folder in the project, a `~/.config/opencode` folder in your home directory, or `opencode` on your PATH. It checks only whether they exist. Finding one, it offers a starter scaffold: an `opencode.json` and a `.opencode/` folder at your project root, and a copy of Mycelium's skills and reference files under `.claude/skills/` and `.claude/mycelium/`. With nobody to ask (a non-interactive run) it writes none of this, unless the request asked for opencode support by name; until 0.322.3 a sign was enough. It never overwrites an `opencode.json` or a `.opencode/` file you already have. A skill folder already in `.claude/skills/` that the scaffold did not put there is left alone, nothing in it is edited, and it is named in the report; until 0.322.3 a skill of yours with the same name as one of Mycelium's was replaced, and plugin paths were rewritten in every skill file there. The folders the scaffold copies carry a marker file, and a re-run replaces only those. The starter `opencode.json` sets a local model as the project's default and lets Mycelium's own skills load without asking; any other skill is asked about.
- `install-runtime-hooks.sh`, if you run it for Cursor or Codex, writes `.cursor/hooks.json` or `.codex/hooks.json` in your project. It also leaves one line saying that it ran, in `.claude/state/install-runtime-hooks-fires.jsonl`, and creates that folder and its ignore file if they are not there, whether or not the project uses Mycelium.
- At session start a check reads Claude Code's own transcripts for this project (under `~/.claude/projects/`) to see whether its hooks were delivered. It only reads them, and only on your machine.
- When a response ends, a hook reads the current session's transcript, the file Claude Code names to it, to see whether a Mycelium skill ran in that turn and whether the reply ends by saying what comes next. This happens at the end of every turn. It keeps the skill's name and what it decided, in its fire log, and nothing of the conversation.
- If you set `release_repo`, a check reads the version tags of that other repository, or its commit subjects when it has no version tags. If you set `MYCELIUM_CROSS_REPO_WATCH`, a check reads the full commit messages, subject and body, from the last 24 hours in each repository you list, and looks in them for ids from your canvas. A commit that mentions one is shown in the session's reminders by its short hash and subject. Unset, the default, only this project is read.
- At session start a check reads your git `user.name` and `user.email` and the address of your `origin` remote (`git config`, `git remote get-url`). It uses them to recognise your own name and account among the sources your canvas cites, so that it does not report you as an outside source that needs checking. They are held in memory for that one check and written nowhere.
- `/mycelium:metrics-detect`, and the longer path through `/mycelium:interview`, have the agent look for signs of where your product's numbers live: the git remote, the packages your project depends on, and whether certain environment variables are set (`PLAUSIBLE_DOMAIN`, `STRIPE_SECRET_KEY` and the like). It proposes a source for each sign and asks you to confirm each one. What it writes is `.claude/jit-tooling/active-metrics.yml`, which names the sources and what each points at (a repository, a domain). It does not hold a credential.
- At session start a check looks in your project for the files that show it deploys: whether a host's config file exists (`vercel.json`, `fly.toml`, a `Procfile` and the like, or a `Dockerfile` beside a compose file), and the text of the workflows in `.github/workflows/`, searched for a deploy command. It does this to ask you whether something is already live. It keeps the name of the file it found, in the question it shows you, and nothing of any file's contents. The release gate already reads some of the same files when the agent runs `git push`.
- When you have snoozed one of Mycelium's reminders "until asked", session start lists your project's files and when each last changed (`git ls-files`), to see whether the product has changed since, so that the reminder can come back. It says how many files changed and keeps none of their names.

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
- **`/mycelium:migrate-from-legacy`**: for a project that still has the old, copied-in install. It runs the `upgrade.sh` that install left in your project, and that script can download Mycelium's files from GitHub with `npx degit` (`npx` may fetch `degit` itself from the npm registry).
- **`/mycelium:a11y-check`**: may suggest accessibility tools (`npx axe`, `lighthouse`, `pa11y`) for you to run; it does not run them itself.

## Third parties

Mycelium shares no data with anyone. When a skill above contacts a service (GitHub, PyPI, a metrics service you configured, Hacker News search, or the sites your canvas cites), you are interacting directly with that service, under its own privacy policy, not under Mycelium's.

## Children

Mycelium is a developer tool and is not directed at children.

## Changes

This policy may be updated as Mycelium evolves. Changes are tracked in the project's git history and `docs/changelog.md`.

## Contact

Questions or concerns: open an issue at <https://github.com/haabe/mycelium/issues>.
