# Commits

One logical change per commit. Tests pass at each commit.

## Format

Subject: `<type>: <description>` (50 chars, imperative, no period)
Types: feat | fix | refactor | docs | test | chore
Body: What and why, not how. Reference issues: `Fixes #123`

## Never Commit

- Multiple unrelated changes
- Generated files without source
- Secrets, credentials, API keys
- Large binaries (use LFS)

## Agent Commits

- Include receipt reference in body
- Never bypass hooks (`--no-verify`)
- Standard types only (no [AUTO] or AI: markers)

## The Rule

Every commit must be valid for `git bisect`. Evidence in body, not subject.

> Docs: docs/safety/COMMIT_GUIDELINES.md
