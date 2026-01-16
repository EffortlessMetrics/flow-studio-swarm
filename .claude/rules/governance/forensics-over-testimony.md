# Forensics Over Testimony

**"Don't listen to the worker; measure the bolt."**

## The Rule

Route based on forensic evidence, not agent claims.

- **Physical evidence** (exit codes, file hashes) beats testimony
- **Captured output** (logs, scan results) beats claims
- **"Not measured"** is valid; assumed pass is dangerous

## Cross-Examination Test

Before trusting a claim:
1. Is there physical evidence?
2. Can it be reproduced?
3. Does evidence corroborate the claim?
4. Is it fresh (this commit)?

If any answer is "no," the claim is **unverified**.

## Evidence Requirements

| Claim | Evidence Required |
|-------|-------------------|
| "Tests pass" | exit code 0 + captured output |
| "Lint clean" | exit code 0 + captured output |
| "Secure" | scanner exit code 0 + output |

> Full documentation: docs/explanation/FORENSICS_OVER_TESTIMONY.md
