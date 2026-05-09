# CI/CD Patterns (Language-Agnostic)

## Principles (from Forsgren/Accelerate)

1. **Trunk-based development**: Short-lived branches (< 1 day ideally), frequent integration
2. **Automated everything**: Build, test, lint, security scan, deploy -- zero manual steps
3. **Small batches**: Each change is small, independently deployable, testable
4. **Fast feedback**: CI pipeline should complete in < 10 minutes for fast feedback loop
5. **Progressive rollout**: Feature flags, canary releases, blue/green deployments where applicable
6. **Automated rollback**: If deployment fails, rollback is automatic, not manual

## Universal Pipeline Stages

```
1. Checkout code
2. Install dependencies (cached)
3. Lint + Format check
4. Type check (if typed language)
5. Unit tests
6. Integration tests
7. Security scan (SAST + dependency audit)
8. Build
9. Accessibility scan (if frontend)
10. Deploy to staging (if applicable)
11. E2E tests against staging (if applicable)
12. Deploy to production (with rollback)
```

## Branch Strategy

**Trunk-based (recommended for teams < 20):**
- `main` is always deployable
- Short-lived feature branches (< 1 day)
- PRs reviewed and merged quickly
- Feature flags for incomplete work

**GitHub Flow (common alternative):**
- `main` is always deployable
- Feature branches with PRs
- Merge after review + CI pass

## DORA Metrics Connection

The CI/CD pipeline directly affects all four DORA metrics:
- **Deployment Frequency**: Automated deployment enables frequent releases
- **Lead Time for Changes**: Fast CI + automated deploy = short lead time
- **Change Failure Rate**: Comprehensive CI catches issues before production
- **Time to Restore**: Automated rollback reduces restore time

## WIP Limits

Enforce Work In Progress limits:
- Maximum concurrent PRs per developer: 1 (ideally)
- Maximum age of open PR: 1 day (target)
- If WIP is exceeded: finish existing work before starting new
