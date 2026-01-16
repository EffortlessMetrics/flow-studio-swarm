# Tests As Evidence

Tests are evidence only if they would fail when the requirement is not met.

## The Rule
A "tests pass" claim requires:
- **Command** run
- **Exit code**
- **Captured output path** (log)
- **Scope**: what the tests cover (requirements / files / scenarios)

If tests were not run: state **NOT MEASURED** and set **UNVERIFIED**.
Coverage without assertions is not evidence.

## Bad → Good
- "Tests pass" → `pytest …` exit 0 + `RUN_BASE/build/test_output.log`

> Skill: evidence-verification
> Docs: docs/explanation/TESTS_AS_EVIDENCE.md
