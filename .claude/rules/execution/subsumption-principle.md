# Subsumption Principle

When a backend lacks a capability, the kernel compensates.

## Core Idea
The orchestrator sees a uniform interface. The kernel bridges capability gaps.

## Subsumption Table
| Missing Capability | Kernel Compensation |
|--------------------|---------------------|
| `output_format` | Parse markdown, extract JSON from fences |
| `hooks` | Wrap execution with logging |
| `interrupts` | Graceful timeout, health check |
| `hot_context` | Inject summaries into prompts |
| `streaming` | Buffer complete, emit as single |

## Example: output_format
- With Claude SDK: `result.structured_output` (native)
- With Claude CLI: Kernel parses markdown fences, validates schema

## The Rule
- Orchestrator code has no `if backend == X` checks
- Capability gaps are bridged at transport layer
- Stubs can simulate any backend

> Docs: docs/execution/SUBSUMPTION.md
