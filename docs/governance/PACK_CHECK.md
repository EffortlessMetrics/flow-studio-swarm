# Pack-Check Philosophy

Validate competence, not compliance.

## Competence vs Compliance

| Competence (Do Check) | Compliance (Don't Check) |
|-----------------------|--------------------------|
| Does it have one job? | Specific wording |
| Does it know its inputs? | Input format |
| Does it know its outputs? | Output format |
| Does it handle stuck? | Specific actions |

## Validation Levels

1. **Structure**: Files exist, YAML parses (always)
2. **Integrity**: References resolve, no dangling pointers (always)
3. **Competence**: Clear purpose, inputs/outputs declared (default)
4. **Style**: Naming conventions, sections present (optional, --strict)

## Warning-First

- Warnings don't block, they inform
- Errors block, they prevent breakage

## Rules

- Validate competence, not compliance
- Warn about gaps, error on breakage
- Form follows function, not the reverse
- Schema religion is an anti-pattern
