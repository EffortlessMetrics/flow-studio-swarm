# Security Policy

> Flow Studio is a **reference implementation**, not a hosted service. See
> [SUPPORT.md](./SUPPORT.md) for the general maintenance posture.

---

## Reporting a Vulnerability

**Do not open a public issue for a security vulnerability.**

Report it privately through GitHub Security Advisories:

1. Go to the [Security tab](../../security/advisories/new) of this repository
2. Click **Report a vulnerability**
3. Fill in the advisory form

This creates a private thread visible only to you and the maintainers. If
Private Vulnerability Reporting is not enabled for the repository, contact a
maintainer listed in [`.github/CODEOWNERS`](./.github/CODEOWNERS) directly and
ask them to open an advisory on your behalf.

### What to Include

| Field | Why it matters |
|-------|----------------|
| Affected version / commit SHA | Pins the report to real code |
| Component | e.g. `swarm/api`, `swarm/runtime`, Flow Studio UI |
| Impact | What an attacker gains (read files, execute commands, exfiltrate secrets) |
| Reproduction | Minimal steps or a proof-of-concept |
| Environment | OS, Python version, how you invoked it |

Concrete reproduction beats severity assertions. A report we can run is worth
more than a report we have to interpret.

### What Not to Include

Do not attach real credentials, tokens, or customer data to a report. If a
secret is already exposed, say so and rotate it — see
[Exposed Secrets](#exposed-secrets) below.

---

## Response Expectations

This is a demo repository maintained on a best-effort basis. There are **no
SLAs and no bug bounty**.

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 7 days |
| Initial assessment | Within 14 days |
| Fix or documented mitigation | Depends on severity and complexity |

We will tell you if a report is rejected and why. Reports that turn out to be
non-issues still get an answer.

### Disclosure

We prefer coordinated disclosure: hold public details until a fix or
documented mitigation is available. If you plan to publish on a fixed
timeline, say so in the report so we can plan around it. Reporters are
credited in the advisory unless they ask not to be.

---

## Scope

### In Scope

- Command injection, path traversal, or arbitrary file write in `swarm/`
  tooling and the Flow Studio API
- Secrets leaking into receipts, logs, run artifacts, or committed files
- Sandbox and boundary escapes — anything letting a flow write outside
  `RUN_BASE/` or push to upstream without passing the publish boundary
  (see [`.claude/rules/safety/sandbox.md`](./.claude/rules/safety/sandbox.md))
- Vulnerabilities in pinned dependencies that are reachable from repo code

### Out of Scope

- Findings that require an attacker to already control the machine running a flow
- Prompt injection against an LLM agent that stays inside the sandbox
  boundary — this is an assumed condition of the design, not a defect. A
  prompt injection that *escapes* the boundary is in scope
- Missing hardening on the local-only Flow Studio dev server (default binding
  is localhost)
- Automated scanner output with no demonstrated impact

---

## Triage Process

Findings — reported or from automated scanning — are handled as incidents.
See [`.claude/rules/safety/incidents.md`](./.claude/rules/safety/incidents.md)
for the full severity ladder.

| Severity | Examples | Response |
|----------|----------|----------|
| **SEV1** | Secret exposure, remote code execution, sandbox escape | Immediate |
| **SEV2** | Privilege or boundary weakness with a viable path to impact | Same-day triage |
| **SEV3** | Vulnerable dependency with a reachable call path | Next business day |
| **SEV4** | Vulnerable dependency with no reachable path; defense-in-depth | Backlog |

Steps: **Detect → Contain → Diagnose → Fix → Verify → Document.** Contain
first; diagnose second. Every fix lands with a regression test where the
defect is testable.

### Dependency Alerts

Dependency findings are triaged on the same ladder. Reachability decides
priority: a CVE in a package no repo code calls is SEV4, not SEV1. Record the
reachability judgement in the advisory or issue — "not reachable" is a valid
outcome, but it has to be stated, not assumed.

---

## Exposed Secrets

If a credential reaches the repository, logs, or run artifacts, assume
compromise. Do not assess first.

**Revoke → Rotate → Audit → Remediate.**

Removing the commit is not sufficient — Git history and any fork or clone
retain it. Rotation is what closes the exposure.

See [`.claude/rules/safety/secrets.md`](./.claude/rules/safety/secrets.md).

---

## Supported Versions

Only `main` is supported. Fixes land on `main`; older tags are not backported.
