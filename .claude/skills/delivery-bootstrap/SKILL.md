---
name: delivery-bootstrap
description: "Use when starting implementation on a new or unfamiliar codebase. Auto-detects tech stack and sets up development context."
---

# Delivery Bootstrap Skill

Just-in-Time tech stack detection and setup.

## Workflow

1. **Scan project root** for technology indicators:
   - Package files: package.json, Cargo.toml, go.mod, requirements.txt, pyproject.toml, Gemfile, pom.xml, build.gradle
   - Config files: tsconfig.json, .eslintrc, .prettierrc, rustfmt.toml, .editorconfig
   - CI/CD: .github/workflows, .gitlab-ci.yml, Jenkinsfile, Dockerfile
   - Framework indicators: next.config.js, nuxt.config.ts, angular.json, etc.

2. **Identify stack components**:
   - Language(s) and version(s)
   - Framework(s)
   - Package manager
   - Test runner and framework
   - Linter and formatter
   - Build tool
   - CI/CD platform
   - Database (if detectable)
   - Deployment target

3. **Verify tooling works**:
   - Run build command
   - Run test command
   - Run lint command
   - Note any failures or warnings

4. **Document existing patterns**:
   - Code organization (monorepo, src layout, etc.)
   - Naming conventions
   - Test patterns
   - Error handling patterns
   - API patterns

5. **Output**:
   ```
   ## Stack Profile
   - Language: [x] v[y]
   - Framework: [x]
   - Package manager: [x]
   - Test: [command] ([framework])
   - Lint: [command]
   - Build: [command]
   - CI/CD: [platform]

   ## Commands
   - Install: [command]
   - Dev server: [command]
   - Test: [command]
   - Build: [command]
   - Lint: [command]

   ## Observed Patterns
   - [list of patterns detected]

   ## Issues Found
   - [any broken tooling or warnings]
   ```

## Rules
- Use the project's established patterns. Don't impose external preferences.
- Be language-agnostic in principles, language-specific in implementation.
- If tooling is broken, flag it rather than silently working around it.

## Theory Citations
- Forsgren: Accelerate (tooling and automation)
- Smart: Sooner Safer Happier (remove friction)
