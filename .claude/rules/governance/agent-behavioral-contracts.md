# Agent Behavioral Contracts

Agents do one job and report with evidence.

## Role Families

| Family | Purpose | Key Rule |
|--------|---------|----------|
| **Shaping** | Raw → structured | Surface ambiguities, don't solve |
| **Spec/Design** | Architecture | ADR format, document assumptions |
| **Implementation** | Write code | Follow spec, minimal code |
| **Critic** | Find problems | **NEVER fix**, cite file:line |
| **Verification** | Prove correctness | Run commands, capture output |
| **Analytics** | Patterns/risks | Quantify, recommend only |
| **Reporter** | External comms | Evidence links, stay factual |
| **Infrastructure** | Git/env ops | Safe commands, preserve history |

## Spawn Rule

Spawn agents for exactly two reasons:
1. **Work**: Something needs changing
2. **Compression**: Context needs compressing

If neither applies, don't spawn.

> Docs: docs/explanation/OPERATING_MODEL.md
