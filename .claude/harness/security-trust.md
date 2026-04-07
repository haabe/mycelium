# Security & Trust Requirements

Per-stage security requirements that scale with the diamond level.

## L0 - Purpose Stage

### Ethical Boundaries
- Define what the product/service will never do (ethical red lines).
- Establish privacy philosophy: what data will and won't be collected, and why.
- Identify vulnerable user populations and how they will be protected.
- Define transparency commitments: what will users know about how their data is used?

### Privacy Philosophy
- Data minimization as default: collect only what is needed for the stated purpose.
- Purpose limitation: data used only for the purpose it was collected for.
- User control: users can access, correct, and delete their data.
- Proportionality: data processing proportional to the benefit provided.

## L1 - Strategy Stage

### Data Classification
- Classify all data the product will handle:
  - **Public**: No restrictions.
  - **Internal**: Not for external sharing but not sensitive.
  - **Confidential**: Business-sensitive. Access controlled.
  - **Restricted**: PII, health data, financial data. Strict access controls, encryption, audit logging.

### Regulatory Landscape
- Identify applicable regulations: GDPR, CCPA, HIPAA, PCI-DSS, SOC2, etc.
- Map regulatory requirements to product features.
- Identify compliance gaps early.
- Plan for data residency requirements.
- Assess cross-border data transfer implications.

## L2 - Opportunity Stage

### Research Data Privacy
- All user research data is PII by default.
- Anonymize participant data in all artifacts (OSTs, synthesis docs, presentations).
- Informed consent required before any research activity.
- Define data retention: how long research data is kept and when it is deleted.
- Secure storage for raw research data (recordings, transcripts, notes).
- Access control: only research team members access raw data.
- Never include identifying information in shared documents.

### Privacy Impact Screening
- For each opportunity: what user data would a solution require?
- Is there a way to solve this with less data?
- What are the privacy risks if this data were breached?
- Would users expect their data to be used this way?

## L3 - Solution Stage

### STRIDE Threat Modeling
Conduct STRIDE analysis for every solution design:

| Threat | Question |
|--------|----------|
| **Spoofing** | Can an attacker impersonate a user or system? |
| **Tampering** | Can data be modified in transit or at rest? |
| **Repudiation** | Can a user deny performing an action without accountability? |
| **Information Disclosure** | Can sensitive data leak to unauthorized parties? |
| **Denial of Service** | Can the system be made unavailable? |
| **Elevation of Privilege** | Can a user gain unauthorized access or capabilities? |

### DPIA (Data Protection Impact Assessment)
For solutions handling personal data:
- What data is processed and why?
- What is the lawful basis for processing?
- Is processing proportionate to the purpose?
- What are the risks to data subjects?
- What measures mitigate those risks?
- Has the DPO (or equivalent) been consulted?

### Secure Design Principles
- Defense in depth: multiple layers of security.
- Fail secure: system fails to a safe state.
- Least privilege: minimum access required for each component.
- Separation of duties: no single point of compromise.
- Trust boundaries: explicitly define where trust transitions occur.

## L4 - Feature Stage

### OWASP Secure Coding
Apply for every feature implementation:

- **Input validation**: Server-side. Allowlist. Type, length, range, format.
- **Output encoding**: Context-specific (HTML, JS, URL, CSS, SQL).
- **Authentication**: Strong password policy. MFA where possible. Secure session handling.
- **Authorization**: Check on every request. Role-based access control. Default deny.
- **Session management**: Secure generation. Timeout. Invalidation. Secure cookie flags.
- **Error handling**: Never expose stack traces or system details. Log details server-side.
- **Logging**: Structured. Include security events. Never log secrets or PII.

### Secrets Management
- No hardcoded secrets. Ever.
- Use environment variables or dedicated secrets manager.
- Rotate secrets on a schedule.
- Different secrets per environment.
- Audit access to secrets.
- Pre-commit hooks to catch accidental secret commits.

### Dependency Security
- Pin dependency versions.
- Automated vulnerability scanning in CI.
- Review changelogs before updating dependencies.
- Remove unused dependencies.
- Assess supply chain risk for critical dependencies.

### Input Validation Checklist
- [ ] All user input validated server-side
- [ ] Allowlist validation preferred over denylist
- [ ] Type checking enforced
- [ ] Length limits enforced
- [ ] Range validation where applicable
- [ ] Format validation (regex) where applicable
- [ ] File upload validation (type, size, content)
- [ ] Parameterized queries for all database access

## L5 - Task Stage

### Transparency & Trust Signals
- Error messages are clear and helpful without leaking system details.
- Users understand what data is being collected and why.
- Automated decisions are explainable.
- Users can always reach a human for help (Downe principle 15).
- Privacy policy is understandable, not legalese.
- Trust indicators (HTTPS, security badges) are honest and verifiable.

### Code-Level Security Checks
- [ ] No secrets in code or config files
- [ ] No SQL injection vectors
- [ ] No XSS vectors
- [ ] No CSRF vulnerabilities
- [ ] Input validation at all entry points
- [ ] Output encoding at all exit points
- [ ] Authentication check on protected endpoints
- [ ] Authorization check on protected resources
- [ ] Secure headers configured (CSP, HSTS, X-Frame-Options, etc.)
- [ ] Dependencies scanned and clean
- [ ] Error handling does not leak information
- [ ] Logging does not include secrets or PII
