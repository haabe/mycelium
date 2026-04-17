# Engineering Principles

Reference guide for all engineering decisions. Apply consistently, violate consciously.

**Product type note** (v0.11.0): These principles are written with software examples but the underlying concepts apply to all product types. For non-software products, translate the principles: DRY = don't duplicate content across modules (courses), don't repeat the same service step (services). KISS = simplest curriculum that teaches the concept (courses), simplest prompt that gets the right output (AI tools). YAGNI = don't create content for topics students haven't asked about yet (courses), don't add service tiers nobody's requested (services). SoC = each lesson covers one concept (courses), each prompt handles one task (AI tools).

## ETC — Easy to Change (The Unifying Principle)

**Definition**: Good design is easier to change than bad design. A thing is well designed if it adapts to the people who use it. For code, that means it must adapt by changing.

**Why it matters**: ETC is the meta-principle that subsumes DRY, KISS, YAGNI, SoC, and SOLID. When principles conflict (DRY vs readability, KISS vs extensibility), ETC is the tiebreaker: which choice makes the system easier to change?

**How to apply**: Before choosing between competing principles, ask: "Which option leaves the system easier to change tomorrow?" This applies to code, documentation, canvas files, and team processes alike.

*Source: Hunt & Thomas (The Pragmatic Programmer, 20th Anniversary Edition, 2019)*

## DRY - Don't Repeat Yourself

**Definition**: Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.

**Why it matters**: Duplication creates maintenance burden, inconsistency risk, and bugs when one copy is updated but not others.

**How to apply**:
- Extract shared logic into functions, modules, or services.
- Use configuration over hardcoding repeated values.
- Create shared types/interfaces for common data structures.
- Reference single source of truth for business rules.
- Documentation: don't restate code in comments or READMEs that duplicate inline docs.
- Schemas: avoid duplicating definitions across files (canvas YAML, API specs).
- Processes: eliminate duplicated build/deployment steps.
- Knowledge: team knowledge siloed in one person's head is a DRY violation — the knowledge is duplicated nowhere accessible.

Note: Hunt & Thomas explicitly state DRY applies to "every piece of knowledge" — not just code.

**How to detect violations**:
- Similar code blocks in multiple files.
- Same business rule implemented in multiple places.
- Copy-pasted code with minor variations.
- Multiple sources of truth for the same concept.

**Exceptions**: Sometimes a little duplication is preferable to premature abstraction. If two pieces of code look similar but represent different concepts that may diverge, keep them separate. "A little copying is better than a little dependency."

## KISS - Keep It Simple, Stupid

**Definition**: The simplest solution that meets the need is the best solution.

**Why it matters**: Complex solutions are harder to understand, test, debug, and maintain. Complexity is the primary enemy of reliability.

**How to apply**:
- Start with the simplest possible implementation.
- Add complexity only when a concrete need demands it.
- Prefer standard library over framework over custom solution.
- Optimize for readability over cleverness.

**How to detect violations**:
- You need a diagram to explain the code flow.
- New team members can't understand the code within minutes.
- The solution handles edge cases that don't exist yet.
- Abstraction layers with only one implementation.

**Exceptions**: Some domains are inherently complex (compilers, distributed systems). Simplicity means managing essential complexity well, not pretending it doesn't exist.

## YAGNI - You Aren't Gonna Need It

**Definition**: Don't build functionality until it is actually needed, not when you foresee it might be needed.

**Why it matters**: Speculative features add maintenance cost, increase complexity, and are often wrong about what will actually be needed.

**How to apply**:
- Implement only what is required by current acceptance criteria.
- Resist "while I'm here, I might as well..." temptation.
- Design for extension without implementing the extension.
- Delete dead code. It's in version control if you need it.

**How to detect violations**:
- Code paths with no tests because no feature uses them.
- Configuration options nobody uses.
- "Future-proofing" abstractions without current consumers.
- Comments like "we might need this later."

**Exceptions**: Architectural decisions that are genuinely expensive to change later (database schema, public API contracts) may warrant some forward thinking. But be honest about what is truly expensive to change.

## SoC - Separation of Concerns

**Definition**: Each module, class, or function should address a single concern. A concern is a set of information that affects the code.

**Why it matters**: Separated concerns can be developed, tested, and modified independently. Changes to one concern don't ripple through unrelated code.

**How to apply**:
- UI logic separate from business logic separate from data access.
- Each file/module has a clear, single responsibility.
- Side effects isolated from pure logic.
- Configuration separate from code.

**How to detect violations**:
- A function that does formatting AND calculation AND persistence.
- Changes to the UI require changes to the database layer.
- A module that is imported by everything.
- Difficulty testing one thing without setting up everything else.

**Exceptions**: Performance-critical paths sometimes benefit from co-locating concerns. Document the trade-off.

**Relationship to Orthogonality**: SoC is about organizing concerns; orthogonality is about measuring independence. A system can separate concerns but still have non-orthogonal components if they share hidden state.

## Orthogonality

**Definition**: Components should be independent — changes in one should not require changes in others.

**Why it matters**: Non-orthogonal systems amplify the cost of change. One change ripples through unrelated components.

**How to apply**:
- Test: "If I change X, how many other things must change?" Fewer = more orthogonal.
- Eliminate coupling between unrelated components.
- Each component should have a single, well-defined purpose.

**How to detect violations**:
- Changing a UI label requires changing a database column.
- Adding a feature to one module breaks tests in another.
- Components share mutable state.

*Source: Hunt & Thomas (The Pragmatic Programmer)*

## SOLID Principles

### S - Single Responsibility Principle (SRP)
**Definition**: A module should be responsible to one, and only one, actor. (Clean Architecture, 2017 revision — originally formulated as "one reason to change" (2003); the "actor" framing shifts from ambiguous reasons to concrete stakeholders who might request changes.)

**How to apply**: If you can describe what a module does with "and" (it validates AND saves AND notifies), it has multiple responsibilities. Ask: "Which actor would request this change?" If the answer is more than one actor, split.

**Detection**: Class has multiple unrelated methods. Changes for different features touch the same file.

### O - Open/Closed Principle (OCP)
**Definition**: Software entities should be open for extension but closed for modification.

**How to apply**: Use abstractions (interfaces, plugins, strategy pattern) so new behavior can be added without changing existing code.

**Detection**: Adding a new feature type requires modifying a switch statement or if-else chain.

### L - Liskov Substitution Principle (LSP)
**Definition**: Objects of a superclass should be replaceable with objects of a subclass without breaking the program.

**How to apply**: Subtypes must honor the contract of their parent type. Don't override methods to throw "not implemented."

**Detection**: Instanceof checks. Subclasses that override methods to do nothing or throw errors.

### I - Interface Segregation Principle (ISP)
**Definition**: No client should be forced to depend on methods it doesn't use.

**How to apply**: Prefer small, focused interfaces over large, general-purpose ones. A class can implement multiple small interfaces.

**Detection**: Implementations that leave methods empty or throw "not supported." Clients importing large interfaces but using 1-2 methods.

### D - Dependency Inversion Principle (DIP)
**Definition**: High-level modules should not depend on low-level modules. Both should depend on abstractions.

**How to apply**: Depend on interfaces, not implementations. Inject dependencies rather than creating them.

**Detection**: Direct instantiation of dependencies. Import of concrete implementations in high-level modules. Difficulty testing without real database/API.

### Component Principles (Martin, Clean Architecture)

Six principles governing how classes group into components — bridges SOLID (class-level) and architecture (system-level):

**Cohesion (what goes together):**
- **REP** (Reuse-Release Equivalence): The granule of reuse is the granule of release.
- **CCP** (Common Closure): Classes that change together belong together. (Maps to bounded context cohesion in DDD.)
- **CRP** (Common Reuse): Don't force users to depend on things they don't use. (Component-level ISP.)

**Coupling (how components relate):**
- **ADP** (Acyclic Dependencies): No cycles in the component dependency graph. (Validates context-map relationships in DDD.)
- **SDP** (Stable Dependencies): Depend in the direction of stability.
- **SAP** (Stable Abstractions): Stable components should be abstract; unstable components concrete.

### Clean Architecture (Martin, 2017)

The **Dependency Rule**: source code dependencies must point inward, toward higher-level policies. Concentric layers: Entities → Use Cases → Interface Adapters → Frameworks & Drivers. Business logic is independent of UI, database, and frameworks. Related: Cockburn's Hexagonal Architecture (Ports and Adapters), which Clean Architecture builds upon.

## LoD - Law of Demeter (Principle of Least Knowledge)

**Definition**: A method should only call methods on: itself, its parameters, objects it creates, its direct components. Don't talk to strangers.

**Why it matters**: Reduces coupling. Changes to internal structures don't ripple through the codebase.

**How to apply**:
- Avoid chaining: `a.getB().getC().doThing()` -- instead, `a.doThing()` delegates internally.
- Tell, don't ask: tell objects what to do rather than extracting their internals and deciding for them.

**How to detect violations**:
- Long method chains.
- Functions that navigate deep object structures.
- Changes to an internal class break unrelated code.

**Exceptions**: Fluent APIs and builder patterns intentionally chain. Data transfer objects (DTOs) are meant to be accessed directly.

## Composition Over Inheritance

**Definition**: Prefer composing objects from smaller, focused pieces over building deep inheritance hierarchies.

**Why it matters**: Inheritance creates tight coupling and is hard to change. Composition is flexible and testable.

**How to apply**:
- Use interfaces and delegation instead of class hierarchies.
- Combine behaviors through composition (mixins, traits, higher-order functions).
- Favor has-a over is-a relationships.

**How to detect violations**:
- Inheritance depth > 2-3 levels.
- "God classes" that inherit from multiple base classes.
- Difficulty understanding what a class does without reading all parent classes.

**Exceptions**: Framework-required inheritance (e.g., React class components in legacy code). Language features that work well with inheritance (e.g., Rust traits, Go interface embedding).

*Source: Gamma, Helm, Johnson, Vlissides (Design Patterns, 1994) — "Favor object composition over class inheritance."*

## Clean Code

**Definition**: Code is clean when it is easy to understand and easy to change (Robert C. Martin).

**Why it matters**: Code is read far more often than it is written. Readability directly impacts maintenance cost and defect rate.

**How to apply**:
- **Meaningful names**: Variables, functions, and classes describe their purpose. No abbreviations unless universally understood.
- **Small functions**: Each function does one thing. If it needs a comment to explain what it does, it should be split or renamed.
- **Minimal comments**: Code should be self-documenting. Comments explain why, not what. Delete commented-out code.
- **Consistent formatting**: Follow the project's style guide. Use automated formatters.
- **No magic numbers/strings**: Use named constants.
- **Error handling**: Handle errors explicitly. Don't swallow exceptions. Return meaningful error messages.
- **No side effects**: Functions should do what their name says and nothing more.

**How to detect violations**:
- Functions longer than ~20 lines.
- Names like `data`, `temp`, `x`, `handle`, `process`.
- Comments that restate the code.
- Functions with boolean parameters (usually doing two things).
- Try-catch blocks that catch and ignore.

For a comprehensive catalog of code smells, see Fowler (*Refactoring*, 2nd ed., 2018): Long Method, Large Class, Feature Envy, Data Clumps, Primitive Obsession, Divergent Change, Shotgun Surgery, and ~18 more. Named smells give precise vocabulary for identifying improvement opportunities.

**Exceptions**: Performance-critical code may sacrifice readability. Document the trade-off and keep a readable version available for understanding.

---

## XP Values (Beck)

Extreme Programming's five values reinforce the principles above:

- **Communication**: Make thinking visible. Canvas, decision log, corrections -- all forms of communication.
- **Simplicity**: Do the simplest thing that works (= KISS). Build only what's needed now (= YAGNI).
- **Feedback**: Tight feedback loops at every level. Tests, validation, reflexion, DORA metrics.
- **Courage**: Refactor fearlessly when design is wrong. Regress diamonds when evidence says so. Delete code that's not earning its keep.
- **Respect**: Sustainable pace. No chronic overtime. BVSSH "Happier" dimension -- customers, colleagues, citizens, and climate. Not faster at any human or climatic cost.

### TDD: Test-First as Target Practice

Test-first (write the test, then the code) is the target practice. Test-alongside satisfies G-V7 but misses TDD's design benefits. In the AI era, agents generate code with unknown quality -- the test suite is the safety net.

### Refactoring as Continuous Practice

After each delivery increment, look for: duplicated logic (DRY), unnecessary complexity (KISS), poor naming (Clean Code), tight coupling (LoD). Refactoring is engineering discipline, not optional polish.

For micro-refactorings smaller than Fowler-style refactoring, see Beck (*Tidy First?*, 2023): guard clauses, extract helper, normalize symmetries, and other "tidyings" — structural changes so small they can precede any behavioral change. The key question is *when* to tidy: before (if it makes the behavioral change easier), after (if you notice during review), later (if it's not blocking), or never (if it doesn't matter).

*Source: Beck (XP, TDD, Tidy First?), Fowler (Refactoring)*
