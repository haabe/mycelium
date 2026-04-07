# Corrections Log

## Format

Each correction entry follows this structure:

```
### [DATE] - [SHORT TITLE]
- **Scope**: [discovery | delivery | orchestration | quality]
- **Category**: [bias | security | engineering | process | communication]
- **Mistake**: What went wrong.
- **Correction**: What should have happened instead.
- **Prevention**: How to prevent this in the future (checklist item, gate, etc.).
- **Source**: Theory or principle that applies (e.g., "Torres - continuous discovery", "OWASP - input validation").
```

## Generalizable Corrections

_Corrections that apply broadly across projects and contexts._

### 2026-04-07 - Use settings.json not settings.local.json for shared config
- **Scope**: delivery
- **Category**: process
- **Mistake**: Put hook configuration in `.claude/settings.local.json` which is globally gitignored by Claude Code (`~/.config/git/ignore`). This meant the hooks couldn't be committed and distributed with the boilerplate.
- **Correction**: Shared hook configuration belongs in `.claude/settings.json` (project-level, committable). Per-developer permission overrides go in `.claude/settings.local.json` (local, gitignored). Claude Code cascades settings: local overrides project.
- **Prevention**: When creating shareable Claude Code configurations (boilerplates, templates, team configs), always use `.claude/settings.json`. Reserve `.claude/settings.local.json` for personal overrides only.
- **Source**: Claude Code settings cascade documentation. PostToolUseFailure reflexion hook caught this.



## Situational Corrections

_Corrections specific to a particular project, team, or context._

