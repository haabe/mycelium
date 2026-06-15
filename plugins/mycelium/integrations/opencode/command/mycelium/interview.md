---
description: Mycelium progressive product-discovery interview (entry point)
agent: build
subtask: false
---
Run the Mycelium interview flow.

Topic / idea (if provided): $ARGUMENTS

Follow the methodology in the `interview` skill (model-invoked via opencode-agent-skills),
or in @.opencode/skills/interview/SKILL.md if present. Honor the project's discipline:
discovery before delivery, evidence gates, Read before Write on canvas files.

Project state for orientation:
!`ls .claude/canvas 2>/dev/null && echo "---" && cat .claude/diamonds/active.yml 2>/dev/null | head -40`
