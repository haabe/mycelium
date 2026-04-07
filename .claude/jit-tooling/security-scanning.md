# Security Scanning Tool Selection

Security scanning tools are selected based on the detected tech stack.

## By Stack

| Stack | SAST | Dependency Audit | Secrets Detection | Container Scan |
|-------|------|-----------------|-------------------|---------------|
| TypeScript/JS | semgrep, eslint-plugin-security | npm audit, snyk | gitleaks, trufflehog | trivy |
| Python | bandit, semgrep | safety, pip-audit | gitleaks, trufflehog | trivy |
| C# / .NET | roslyn-analyzers, semgrep | dotnet audit, snyk | gitleaks, trufflehog | trivy |
| Go | gosec, semgrep | govulncheck | gitleaks, trufflehog | trivy |
| Rust | cargo-audit, semgrep | cargo audit | gitleaks, trufflehog | trivy |
| Java | spotbugs, semgrep | dependency-check (OWASP) | gitleaks, trufflehog | trivy |
| Ruby | brakeman, semgrep | bundler-audit | gitleaks, trufflehog | trivy |

## Universal (All Stacks)

- **semgrep**: Multi-language SAST, runs locally, free for OSS
- **gitleaks**: Detects secrets in git history
- **trivy**: Container and filesystem vulnerability scanner

## Integration Points

1. **Pre-commit**: gitleaks (catch secrets before they enter git)
2. **CI pipeline**: SAST + dependency audit + secrets scan
3. **Scheduled**: Full dependency audit weekly
4. **Pre-deploy**: Container scan (if containerized)

## OWASP Top 10 Coverage

Each security scan should cover:
1. Injection -- SAST rules for SQL/command/LDAP injection
2. Broken Auth -- SAST rules for auth patterns
3. Sensitive Data Exposure -- Secrets detection + data classification
4. XXE -- SAST rules for XML parsing
5. Broken Access Control -- SAST rules for authorization checks
6. Security Misconfiguration -- Config scanning
7. XSS -- SAST rules for output encoding
8. Insecure Deserialization -- SAST rules per language
9. Known Vulnerabilities -- Dependency audit
10. Insufficient Logging -- Manual review (not automatable easily)
