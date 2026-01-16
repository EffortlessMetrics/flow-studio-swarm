# Capability Registry

Claims require evidence. The registry prevents narrative drift.

## Status Meanings
| Status | Meaning | Evidence Required |
|--------|---------|-------------------|
| **implemented** | Has code + test evidence | code + tests |
| **supported** | Has code, incomplete tests | code only |
| **aspirational** | Design exists, NOT shipped | none |

## Evidence Types
- **Code**: path + symbol pointing to implementation
- **Tests**: kind (unit/integration/bdd) + ref to test file
- **Design**: path to design doc (aspirational only)

## Validation Rules
- `implemented` MUST have ≥1 test pointer AND ≥1 code pointer
- `@cap:<id>` tags in BDD MUST reference valid capabilities
- `aspirational` MUST NOT be claimed as shipped

## The Rule
- If it's not in `specs/capabilities.yaml` with proper evidence, it's not a capability
- "Not measured" is valid; false certainty is not
- Claims without evidence are unverified

> Docs: docs/artifacts/CAPABILITY_REGISTRY.md
