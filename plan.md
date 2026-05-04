Oh, I see why the `make test-gating` failed!
It failed on `make lint-routing-strict`:

```
Checking for deprecated routing field patterns (strict mode)...
uv run python swarm/tools/lint_routing_fields.py --strict

------------------------------------------------------------
WARNINGS: Transitional/legacy patterns found
Consider removing these fields entirely.
------------------------------------------------------------

  swarm/prompts/agentic_steps/self-reviewer.md:167
    Pattern: mention of deprecated route_to_flow (verify this is deprecation documentation)

  swarm/prompts/agentic_steps/self-reviewer.md:167
    Pattern: mention of deprecated route_to_agent (verify this is deprecation documentation)

  docs/RELEASE_CHECKLIST.md:99
    Pattern: mention of deprecated route_to_flow (verify this is deprecation documentation)

  docs/RELEASE_CHECKLIST.md:99
    Pattern: mention of deprecated route_to_agent (verify this is deprecation documentation)

  docs/RELEASE_CHECKLIST.md:102
    Pattern: mention of deprecated route_to_flow (verify this is deprecation documentation)

  docs/RELEASE_CHECKLIST.md:102
    Pattern: mention of deprecated route_to_agent (verify this is deprecation documentation)


Summary: 0 legacy errors, 0 malformed V3 errors, 6 warnings
V3 routing patterns found: 202 valid usages

FAILED (strict mode): Remove transitional patterns
```

Wait, `lint_routing_fields.py` fails if there are warnings and `--strict` is passed.
```python
FAILED (strict mode): Remove transitional patterns
```
Let's see what is on those lines in `swarm/prompts/agentic_steps/self-reviewer.md` and `docs/RELEASE_CHECKLIST.md`.
Wait, why did my PR fail this? Did my PR add these? I didn't edit `self-reviewer.md` or `RELEASE_CHECKLIST.md`. It must have been broken in `main` by a previous commit!

But since I need to make the CI pass, I'll fix this too.
I can either edit `swarm/tools/lint_routing_fields.py` to add `docs/RELEASE_CHECKLIST.md` to `SKIP_PATTERNS` or fix the files by removing `route_to_flow` / `route_to_agent` mentions.
