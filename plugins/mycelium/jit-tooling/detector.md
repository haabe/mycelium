# JiT Tooling: Language-Agnostic Tech Stack Detection

Mycelium is language-agnostic. When a delivery diamond begins, the agent auto-detects the tech stack and generates appropriate tooling configuration.

## Detection Process

### Step 1: Scan for Package Manifests

| File Found | Language/Runtime |
|-----------|-----------------|
| `package.json` | JavaScript/TypeScript (Node.js) |
| `tsconfig.json` | TypeScript |
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | Python |
| `Cargo.toml` | Rust |
| `*.csproj`, `*.sln`, `Directory.Build.props` | C# / .NET |
| `go.mod` | Go |
| `Gemfile`, `*.gemspec` | Ruby |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | Java / Kotlin |
| `Package.swift` | Swift |
| `mix.exs` | Elixir |
| `composer.json` | PHP |
| `pubspec.yaml` | Dart / Flutter |

### Step 1b: Scan for Non-Software Product Indicators (v0.11.0)

If no software package manifests are found, OR if the user specified a non-software `product_type` during `/interview`, check for these patterns:

| File/Pattern Found | Product Type | Delivery Canvas |
|-------------------|--------------|-----------------|
| Curriculum outline, lesson plans, `*.lms`, Teachable/Thinkific config, learning objectives doc | `content_course` | content-metrics.yml |
| `manuscript/`, `chapters/`, `*.epub`, `*.docx` with chapter structure, editorial calendar | `content_publication` | content-metrics.yml |
| Video scripts, `*.srt`, `*.vtt`, episode outlines, podcast RSS, media production pipeline | `content_media` | content-metrics.yml |
| Prompt templates, `*.prompt`, agent definitions, model configs, fine-tuning scripts | `ai_tool` | ai-tool-metrics.yml |
| Service blueprints, pricing docs, client onboarding docs, proposal templates | `service_offering` | service-metrics.yml |

If non-software indicators are found:
1. Set `product_type` in `active-stack.yml`
2. Skip software-specific tooling detection (Steps 3-6 for test runners, linters, etc.)
3. Instead, configure product-type-appropriate validation:
   - **Content**: spell checker, readability scorer, link checker, accessibility scanner (captions/alt text)
   - **AI tool**: eval harness, red-team script, bias testing framework
   - **Service**: no automated tooling (service quality is assessed via `/service-check`)

If BOTH software and non-software indicators are found (e.g., an AI tool with a web frontend), detect as a **hybrid**: set `product_type: ai_tool` (or whichever non-software type) but also detect the software stack for the code components. Both sets of quality frameworks apply.

### Step 1c: AI Component Detection (v0.16)

AI-component presence is **orthogonal to product_type**: a `software` product can contain AI (LLM-backed feature), an `ai_tool` product is itself AI. Both raise XAI obligations downstream (`/xai-check`, AI-aware Definition of Done, threat-model extensions). Detect imports across all language manifests; categorize, don't just yes/no.

| Category | What it implies | Signals (selected packages — match by name, version-agnostic) |
|---|---|---|
| `llm_api_client` | Generative/conversational AI; triggers AI Act Art. 50 disclosure when user-facing | JS/TS: `@anthropic-ai/sdk`, `openai`, `@google/generative-ai`, `cohere-ai`, `@mistralai/mistralai`, `groq-sdk`, `replicate`, `together-ai`, `@ai-sdk/*`, `ai` (Vercel), `@aws-sdk/client-bedrock-runtime`, `@azure/openai`. Python: `anthropic`, `openai`, `google-generativeai`, `cohere`, `mistralai`, `groq`, `replicate`, `together`, `litellm`, `boto3` (when bedrock client used). Go: `sashabaranov/go-openai`, `anthropics/anthropic-sdk-go`. Java/Kotlin: `theokanning.openai-gpt3-java`. Ruby: `ruby-openai`, `anthropic`. C#: `OpenAI`, `Anthropic.SDK`. |
| `agent_framework` | Multi-step reasoning; explanation-fidelity risk amplified (Lanham 2023) | Python: `langchain`, `langchain-*`, `llama-index`, `instructor`, `dspy`, `guidance`, `autogen`, `crewai`. JS/TS: `langchain`, `@langchain/*`, `llamaindex`, `mastra`, `agentkit`. C#: `Microsoft.SemanticKernel`. Java/Kotlin: `dev.langchain4j:*`. |
| `classical_ml` | Automated decisions; AI Act Art. 22 / GDPR right-to-explanation if user-affecting | Python: `scikit-learn` / `sklearn`, `xgboost`, `lightgbm`, `catboost`, `tensorflow`, `torch`, `pytorch`, `keras`, `jax`, `pyspark.ml`. R: `caret`, `mlr3`. JVM: `weka`, `smile`, `tribuo`. |
| `embedding_retrieval` | Information retrieval; lower XAI tier unless retrieved info gates a user-affecting decision | Python: `sentence-transformers`, `chromadb`, `weaviate-client`, `pinecone-client`, `qdrant-client`, `pymilvus`, `faiss-cpu`, `faiss-gpu`. JS/TS: `@pinecone-database/pinecone`, `weaviate-ts-client`, `@qdrant/js-client`, `chromadb`. |
| `nlp_traditional` | Lower XAI tier; mostly text processing, not user-facing decisions | Python: `spacy`, `nltk`, `gensim`, `transformers` (when used for embeddings/classification only — overlaps `agent_framework` if used for generation). |
| `prompt_assets` | Prompt templates / agent configs present; signals AI is in the build, not just the deps | Filesystem: `prompts/`, `.prompts/`, `*.prompt`, `agents.yml`, `agent.yml`. |
| `mcp_servers` | Model Context Protocol servers — agent extension surface | `mcp-*` packages, `@modelcontextprotocol/*` deps, `mcpServers` block in claude config. |
| `agent_runtime_target` | Project is structurally designed to be **operated by** an AI agent runtime (Claude Code, Codex, Cursor, Windsurf, Cline, etc.) — not embedding AI as a dependency, but hosting the framework an AI runtime reads. The runtime IS the user-facing surface. Caught the Mycelium-as-product gap (corrections.md 2026-05-04). | Filesystem at project root: `CLAUDE.md`, `AGENTS.md`, `.claude/manifest.yml`, `.claude/skills/` (populated), `.cursor/rules/` (populated), `.windsurf/`, `.cline/`, `.github/copilot-instructions.md`. The presence of *any one* signals — these projects don't necessarily import AI libraries. |

**Detection method:** parse each detected language's manifest dependencies (Step 1) and match package names against the lists above. Filesystem signals (last three rows) are matched by glob/path scan. Match is name-only — version-agnostic, so the detector keeps working as packages bump majors.

**Category overlap rules:**
- `prompt_assets` and `agent_runtime_target` can co-fire — a project with `prompts/` AND `CLAUDE.md` matches both. Emit both categories in `active-stack.yml`. They convey different information: prompt_assets = "prompts exist somewhere"; agent_runtime_target = "the project IS the runtime context."
- `agent_runtime_target` without any dependency-based category (no `llm_api_client` / `agent_framework` / etc.) is the framework-shaped product case. The AI is the runtime that consumes the project, not a dependency the project consumes. Mycelium itself.
- `agent_runtime_target` + dependency categories together = the project is BOTH agent-operated AND embeds AI itself. Common in agent-engineered products that ship their own LLM features alongside the harness configuration.

**Honesty rule (don't overclaim).** Imports tell us AI components exist; they do **not** tell us whether AI outputs reach end users in a user-affecting way. That is the classifying question for `/xai-check`. The detector emits a hint, not a verdict.

**Output additions to `active-stack.yml`:**

```yaml
ai_components:
  detected: true                    # false if no signals match
  categories:
    - type: llm_api_client
      packages: ["@anthropic-ai/sdk", "openai"]
    - type: agent_framework
      packages: ["langchain"]
  user_facing_decisions: unknown    # unknown | yes | no — confirm with user during Step 6
  xai_tier_hint: limited            # minimal | limited | high — provisional, /xai-check classifies definitively
  detected_via: ["package.json", "requirements.txt", "prompts/"]
```

If `detected: false`, the block can be omitted entirely. Downstream skills (`/xai-check`, AI-aware DoD, threat-model XAI extension) treat absence as "no AI"; presence triggers their AI overlays. The `user_facing_decisions` field stays `unknown` until the user answers Step 6's confirmation prompt — never inferred silently.

### Step 2: Identify Project Shape

| Signal | Classification |
|--------|---------------|
| Single package manifest at root | Single app |
| `pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `lerna.json` | Monorepo |
| Multiple `Dockerfile`s, `docker-compose.yml` | Multi-service |
| `packages/` or `apps/` directories | Monorepo (workspace) |
| Single `*.sln` with multiple `*.csproj` | .NET solution (multi-project) |
| `*.csproj` only | Single .NET project |

### Step 3: Detect Existing Tooling

| Category | Files to Check |
|----------|---------------|
| Testing | `vitest.config.*`, `jest.config.*`, `pytest.ini`, `conftest.py`, `*.test.*`, `*.spec.*`, `xunit.*`, `nunit.*`, `MSTest.*` |
| Linting | `.eslintrc*`, `biome.json`, `.prettierrc*`, `ruff.toml`, `.rubocop.yml`, `.editorconfig`, `stylecop.*` |
| Type checking | `tsconfig.json`, `mypy.ini`, `pyright` config |
| Security | `.semgrep*`, `.snyk`, `dependabot.yml`, `.github/workflows/*security*` |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci/` |
| Accessibility | `axe` config, `pa11y` config, lighthouse config |

### Step 4: Classify Complexity Tier

| Tier | Signals | Ceremony Level |
|------|---------|---------------|
| Solo/Simple | Single app, < 20 files, no CI/CD | Lightweight validation |
| Team/Standard | Monorepo or multi-service, CI/CD present, testing framework | Full validation suite |
| Enterprise | Multiple services, security scanning, compliance configs | Full validation + security + compliance |

### Step 5: Generate Stack Configuration

Write to `.claude/jit-tooling/active-stack.yml`:

```yaml
# Auto-generated by Mycelium delivery-bootstrap
detected_at: "YYYY-MM-DDTHH:MM:SSZ"
confirmed_by_user: false  # Set to true after user confirms

language: "typescript"  # detected primary language
runtime: "node"
shape: "monorepo"  # single-app | monorepo | multi-service
complexity_tier: "team"  # solo | team | enterprise

commands:
  test: "pnpm test"
  typecheck: "pnpm tsc --noEmit"
  lint: "pnpm biome check"
  lint_fix: "pnpm biome check --apply"
  format: "pnpm biome format --write ."
  build: "pnpm build"
  security_scan: "pnpm audit"
  a11y_test: ""  # filled if frontend detected

validation_suite: "pnpm test && pnpm tsc --noEmit && pnpm biome check"

existing_ci: true
existing_tests: true
existing_linting: true
existing_security_scanning: false
```

### Step 6: Confirm with User

After detection, present findings and ask user to confirm/adjust:
- "I detected [language] [shape] project with [tooling]. Is this correct?"
- "I'll use [test command] for testing. Should I adjust?"
- "No security scanning detected. Should I set up [recommended tool]?"
- If `ai_components.detected` (Step 1c): "I detected [llm_api_client / agent_framework / classical_ml / ...] AI components. Does the AI's output reach end users in a way that affects them — deny, recommend, rank, generate content shown to them, or otherwise drive their experience?" Set `ai_components.user_facing_decisions` to `yes` / `no` / `partially` based on the answer. The XAI tier (`/xai-check` Stage 1) depends on this; never infer it silently.

## What Stays Universal (All Product Types)

These apply regardless of detected stack or product_type:
- Diamond engine and all discovery/strategy frameworks
- Delivery metrics gate (product-type-routed: DORA for software, content-metrics for content, etc.)
- Definition of Done checklist (adapted per product_type -- see definition-of-done.md)
- Downe's 15 service design principles (applied to the consumption experience for all product types)
- DRY, KISS, YAGNI, SoC, SOLID (product-type-agnostic concepts -- see engineering-principles.md)
- Reflexion loop pattern (validate -> critique -> retry -- adapted per product_type)
- Corrections memory and pattern library

These apply conditionally based on product_type:
- OWASP/STRIDE security principles (software, ai_tool, service with digital infra)
- WCAG 2.1 AA accessibility (software UI); content accessibility for courses/publications/media
- DORA metrics specifically (software only; other product types use their own metrics canvas)
- Testing pyramid (software, ai_tool code components)

These apply conditionally based on `ai_components.detected` (Step 1c):
- `/xai-check` (XAI gate for AI-containing products — disclosure, decision-explanation, recourse, fidelity, system card, tier-scaled)
- AI-aware Definition of Done items (disclosure copy reviewed, fidelity sample audited, recourse path tested, system card published)
- Threat-model XAI extension (misleading-explanation manipulation, prompt-injection causing false rationales, explanation side-channel leakage)
- See `.claude/engine/xai-canvas-threading.md` for which existing canvas files thread XAI signals.

## What Varies (Stack-Specific)

These are discovered and configured per stack:
- Test runners and commands
- Linting and formatting tools
- Type checking approach
- Build and compile commands
- Dependency management
- Security scanning tools
- CI/CD pipeline syntax
- Deployment patterns
- Accessibility testing tools (e.g., axe for React, not relevant for CLI tools)

## Polyglot / Multi-Language Projects

When multiple package manifests are found for different languages:

### Detection
- `package.json` + `requirements.txt` = TypeScript frontend + Python backend
- `package.json` + `*.csproj` = TypeScript frontend + C# backend
- `package.json` + `go.mod` = TypeScript frontend + Go backend
- Multiple `package.json` in monorepo = multi-package TypeScript

### Handling
1. Detect ALL languages present, not just the "primary" one
2. `active-stack.yml` uses a `languages` array (not single `language` field)
3. Create separate validation commands per language:
   ```yaml
   languages:
     - name: "typescript"
       runtime: "node"
       commands: { test: "npm test", lint: "npx eslint ." }
     - name: "python"
       runtime: "python3"
       commands: { test: "pytest", lint: "ruff check ." }
   ```
4. Validation suite runs ALL language validators
5. Security scanning uses multi-language tools (semgrep covers most)

### Common Patterns
| Pattern | Detection | Approach |
|---------|-----------|----------|
| SPA + API | Frontend package.json + backend manifest | Separate commands, shared CI |
| Monorepo | Workspace config (pnpm/nx/turbo) | Per-package validation |
| Microservices | Multiple Dockerfiles | Per-service validation |
| Mobile + API | Flutter/RN config + backend manifest | Platform-specific tooling |

## GitOps / Infrastructure-as-Code Detection

When Kubernetes or infrastructure manifests are detected:

| File Found | Stack |
|-----------|-------|
| `argocd-*.yml`, `applicationset.yml` | ArgoCD (GitOps) |
| `flux-system/`, `gotk-components.yml` | Flux (GitOps) |
| `terraform/`, `*.tf` | Terraform |
| `pulumi/`, `Pulumi.yaml` | Pulumi |
| `helmfile.yaml`, `Chart.yaml` | Helm |

For GitOps projects, the canvas system's git-based workflow aligns naturally — treat infrastructure definitions with the same evidence-based change process as product canvas files.

## Fallback Behavior

If no package manifest is found (new/empty project):
1. Ask the user what they're building
2. Ask preferred language/framework
3. Recommend appropriate tooling
4. Generate initial project structure if requested

## Theory grounding

- **Tesler's Law of Conservation of Complexity** ("every application has an inherent amount of complexity that cannot be removed or hidden — it can only be moved"). Mycelium's JiT philosophy ("detect-and-generate over pre-shipped catalogs") is Tesler's Law applied: a pre-shipped catalog of every language × every test runner × every CI provider would shift the complexity onto framework maintenance (Cartesian-product growth, stale entries, "my stack isn't in your catalog" friction). Detect-then-generate moves the same complexity to the agent at the moment of need, where it has the project's actual context to resolve correctly. Same total complexity; different bearer. Source: Larry Tesler (1980s, attributed via Saffer, *Designing for Interaction*).
