# Support & Maintenance

> This document sets expectations for how to engage with Flow Studio.

---

## What This Is

Flow Studio is a **UI and runtime harness** for visualizing agentic SDLC flows.

It's a **reference implementation**, not a product. It demonstrates patterns for governed AI-assisted SDLC. You're meant to fork it, copy patterns, and adapt to your stack.

**Related repos:**
- [`EffortlessMetrics/demo-swarm`](https://github.com/EffortlessMetrics/demo-swarm) — Portable `.claude` pack for using the swarm in your own repo

---

## Maintenance Posture

The maintainers:

- **Read issues** (bugs, questions, feature requests)
- **Don't promise SLAs** — this is a demo repo, not a production service
- **Bias toward fixes that**:
  - Keep governance green (selftest, validation)
  - Improve clarity (docs, checklists, error messages)
  - Improve adoptability (golden examples, onboarding paths)

---

## How to Engage

### Found a Bug?

Open an issue using the **[Bug Report template](../../issues/new?template=bug_report.md)**.

Include:
- What you expected
- What happened
- Steps to reproduce
- `make selftest` output (if relevant)

### Found a Security Vulnerability?

**Do not open a public issue.** Report it privately — see
[SECURITY.md](./SECURITY.md).

### Have a Question?

Open an issue using the **[Adoption Question template](../../issues/new?template=adoption_question.md)**.

Good questions:
- "How do I wire this into my CI?"
- "What's the expected token cost per flow?"
- "Can I use this with [other orchestrator]?"

### Want to Contribute?

PRs are welcome! Before submitting:

1. Run `make dev-check` — must pass
2. Keep governance green — don't break selftest
3. Update docs if you change behavior
4. Prefer small, focused changes over large refactors

**Good PR targets:**
- Doc clarifications and typo fixes
- New evaluation recipes or golden examples
- Bug fixes with test coverage
- Improvements to error messages

**Not accepting:**
- Large architectural changes without discussion
- New agent types without ADR
- Features that break existing contracts

---

## What You Can Expect

| Type | Response |
|------|----------|
| **Bug affecting selftest/validation** | High priority, will investigate |
| **Doc clarity issues** | Welcome, usually quick to merge |
| **Feature requests** | Will consider for roadmap |
| **"Can you build X for me?"** | No — this is a pattern library, not a service |

---

## Escalation

There is no formal escalation path. If something is genuinely blocking adoption:

1. Open an issue with `[BLOCKING]` prefix
2. Explain what you're trying to do and why it's blocked
3. Include workarounds you've tried

We'll prioritize based on impact and alignment with the project's goals.

---

## See Also

- [EVALUATION_CHECKLIST.md](docs/EVALUATION_CHECKLIST.md) — 1-hour guided evaluation
- [ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md) — Full adoption guide
- [docs/INDEX.md](docs/INDEX.md) — Complete documentation map
