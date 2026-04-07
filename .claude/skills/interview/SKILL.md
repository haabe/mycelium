---
name: interview
description: "Use when onboarding a new product/project. Progressive interview to understand purpose, vision, north star, and competitive landscape."
---

# Interview Skill

Progressive onboarding through structured discovery conversation.

## When to Use

- Starting a new product or project.
- Joining an existing product that lacks documented context.
- Context has changed significantly and needs refreshing.

## Workflow

### Phase 1: Purpose & Vision
1. Ask: "What problem does this product/organization solve? Who suffers without it?"
2. Ask: "What does success look like in 3 years? What would change in the world?"
3. Ask: "What will you never do, even if it would be profitable?" (ethical boundaries)
4. Synthesize into a purpose statement. Validate with the user.

### Phase 2: Users & Jobs
5. Ask: "Who are your primary users? Describe a specific person."
6. Ask: "What are they trying to accomplish? What job are they hiring your product to do?"
7. Map JTBD (functional, emotional, social) per user type.
8. Ask: "What workarounds do they currently use?"

### Phase 3: North Star & Metrics
9. Ask: "What is the single metric that best indicates you're fulfilling your purpose?"
10. Ask: "What leading indicators predict movement in that metric?"
11. Construct a north star framework: metric + input metrics.

### Phase 4: Landscape & Strategy
12. Ask: "Who else solves this problem? How are you different?"
13. Ask: "What are you betting on strategically right now?"
14. Ask: "What is your biggest uncertainty or risk?"
15. Sketch initial Wardley map positioning if sufficient context exists.

### Phase 5: Current State
16. Ask: "What has been tried and failed? What did you learn?"
17. Ask: "What's the team structure? How do decisions get made?"
18. Ask: "What are the immediate priorities?"

## Output

- Purpose statement
- JTBD map per user type
- North star metric + input metrics
- Strategic context summary
- Initial opportunity areas (from what was shared, not assumed)

## Phase 6: Project Classification (NEW in v0.2)

At the end of the interview, classify the project to determine which canvas files are required:

Ask: "Let me understand the project scope to tailor the framework:"
- Is this a solo or team project?
- Is this a hobby/learning project, a real product, or enterprise?
- Will it have external users?
- Will it handle user data?

Classify into one of:
- **solo_hobby**: Personal project, no commercial intent
- **solo_product**: Solo developer, real product with users
- **team_startup**: Small team (2-10), product with users/revenue
- **team_enterprise**: Larger team, regulatory/compliance needs

Load canvas guidance from `.claude/engine/canvas-guidance.yml` for the classified type.

Report to user: "Based on this being a [type] project, here's what we'll focus on:"
- **Required canvas files**: [list] -- "These will be populated as we work."
- **Recommended**: [list] -- "Worth doing if time allows."
- **Optional**: [list] -- "You can skip these for this project type."

Store classification in `diamonds/active.yml` as `project_type`.

## After the Interview: What Happens Next

The interview creates an **L0 Purpose diamond** in Discover phase. Here's the bridge to ongoing work:

1. **Tell the user**: "Interview complete. I've created your L0 Purpose diamond and populated the initial canvas files."
2. **Suggest next step**: "Run `/diamond-assess` to see your starting state and what to work on next."
3. **The typical flow from here**:
   - `/diamond-progress` to advance L0 through its phases
   - L0 spawns L1 (Strategy) when purpose is solid -- unless project type is solo_hobby (skip L1, go to L2)
   - L1 spawns L2 (Opportunity) when landscape is mapped
   - Each progression runs theory gates automatically

**Do NOT leave the user without a clear next action.** Always end the interview with a specific recommendation.

## Theory Citations

- Sinek: Start with Why (purpose)
- Christensen: Jobs to Be Done
- Torres: Continuous Discovery Habits (opportunity identification)
- Wardley: Wardley Mapping (landscape)
- Cagan: Empowered (vision, strategy)
