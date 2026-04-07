# Testing Strategy (Language-Agnostic)

## The Testing Pyramid

Applies to ALL tech stacks. The specific tools vary; the principles don't.

### Foundation: Unit Tests (70-80% of tests)
- Fast, isolated, test single units of behavior
- Mock external dependencies
- Run in milliseconds
- High coverage of business logic
- Property-based testing for algorithmic code (generates random inputs to find edge cases)

### Middle: Integration Tests (15-20% of tests)
- Test boundaries between components
- API contract testing (does the API return what consumers expect?)
- Database integration (do queries work with real data shapes?)
- External service integration (with stubs/containers)
- Run in seconds

### Top: End-to-End Tests (5-10% of tests)
- Test critical user journeys only
- Full stack, including UI if applicable
- Slow, brittle -- minimize count
- Focus on: can a user complete the core jobs-to-be-done?

### Cross-Cutting: Security Tests
- Static analysis (SAST) in CI pipeline
- Dependency vulnerability scanning
- Input validation testing
- Authentication/authorization boundary testing

### Cross-Cutting: Accessibility Tests
- Automated scanning (axe, lighthouse, pa11y)
- Keyboard navigation testing
- Screen reader compatibility (manual or automated)
- Color contrast validation

## Stack-Specific Tooling (discovered by JiT detector)

| Stack | Unit | Integration | E2E | Security | A11y |
|-------|------|------------|-----|----------|------|
| TypeScript/React | vitest/jest | vitest | playwright/cypress | semgrep, npm audit | axe, lighthouse |
| TypeScript/Node | vitest/jest | vitest/supertest | playwright | semgrep, npm audit | N/A (API) |
| Python | pytest | pytest | playwright | bandit, safety | N/A or axe |
| C# / .NET | xunit/nunit | xunit + TestServer | playwright | roslyn analyzers, dotnet audit | axe |
| Go | go test | go test | playwright | gosec, govulncheck | N/A |
| Rust | cargo test | cargo test | playwright | cargo audit | N/A |
| Java | JUnit | JUnit + TestContainers | selenium/playwright | spotbugs, dependency-check | axe |

## Principles

1. **Write tests alongside code, not after** -- tests document behavior
2. **Test behavior, not implementation** -- tests should survive refactoring
3. **Every bug gets a regression test** -- never fix a bug without adding a test that catches it
4. **Don't test the framework** -- test YOUR code, not the libraries you use
5. **Failing tests are information, not obstacles** -- diagnose, don't exclude
