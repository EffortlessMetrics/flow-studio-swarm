# Minimal Handoffs: Critic to Author

## Purpose

Minimal handoffs are used in microloops where a critic returns focused feedback to an author for iteration. Target: <500 tokens.

## The Rule

> Minimal handoffs focus on ONE issue with file:line location and actionable recommendation.
> Verbose prose wastes tokens. Missing line numbers waste author time.

## Good Example

```json
{
  "status": "UNVERIFIED",
  "summary": {
    "what_i_found": "1 HIGH issue"
  },
  "concerns": [
    {
      "severity": "HIGH",
      "description": "Missing input validation",
      "location": "src/auth.py:42",
      "recommendation": "Add validation before database query"
    }
  ],
  "routing": {
    "recommendation": "LOOP",
    "can_further_iteration_help": true
  }
}
```

**Why it works:**
- Focused on one issue
- Clear location with file and line number
- Actionable recommendation
- ~200 tokens

## Bad Example

```json
{
  "status": "UNVERIFIED",
  "summary": {
    "what_i_did": "I carefully reviewed the entire codebase looking for issues...",
    "what_i_found": "After extensive analysis of the authentication module, I discovered that there are several concerns that need to be addressed. The first issue relates to input validation which is critically important for security. The second issue involves error handling which could be improved. The third issue..."
  },
  "concerns": [
    {
      "severity": "HIGH",
      "description": "The validate_token function in the auth module does not properly validate user input before passing it to the database query, which could potentially lead to SQL injection vulnerabilities if an attacker were to craft malicious input...",
      "location": "src/auth.py",
      "recommendation": "You should add proper input validation by sanitizing the input, checking for malicious characters, and using parameterized queries..."
    }
  ]
}
```

**Why it fails:**
- Verbose prose wastes tokens
- Missing line number makes fixing harder
- Over-explained concerns dilute focus
- ~800 tokens for the same information

## Common Mistakes

### Prose Instead of Structure

```json
// BAD - hard to parse
{
  "summary": "Well, I did a bunch of things today. First I looked at the code..."
}

// GOOD - structured and scannable
{
  "summary": { "what_i_found": "1 issue" },
  "concerns": [
    { "severity": "HIGH", "description": "Missing validation", "location": "src/auth.py:42" }
  ]
}
```

### Missing Location Details

```json
// BAD - vague location
{ "location": "src/auth.py" }

// GOOD - precise location
{ "location": "src/auth.py:42" }
```

## Size Reference

| Handoff Type | Target Tokens | Typical JSON Lines |
|--------------|---------------|-------------------|
| Minimal | <500 | 15-25 lines |

## See Also

- [handoff-standard-heavy.md](./handoff-standard-heavy.md) - Standard and heavy handoff examples
- [handoff-patterns.md](./handoff-patterns.md) - Sizing guidelines and compression patterns
- [microloop-rules.md](./microloop-rules.md) - When minimal handoffs are used
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope schema definition
