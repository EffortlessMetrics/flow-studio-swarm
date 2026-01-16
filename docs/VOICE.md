# Voice and Style Guide

> **Purpose:** How to write Flow Studio documentation
> **Status:** Living document

## The Voice

**Industrial operator, not Silicon Valley marketer.**

Write like someone who ships systems under real constraints. Treat "proof" as a file, not a feeling. Respect the reader's time and intelligence.

## Core Characteristics

### 1. Ruthless Concision
Every word earns its place. Subject-Verb-Object. No subordinate clauses. No hedging.

### 2. Concrete Over Abstract
Numbers beat adjectives. "Exit code 0" beats "worked." "$30/run" beats "cost-effective."

### 3. Evidence-Based Claims
Don't ask to be trusted. Show receipts.

### 4. Respectful of Skepticism
Skeptics are right to be skeptical. Agree with them, then show evidence.

## Vocabulary

### Words We Use
| Word | Why |
|------|-----|
| Receipts | Concrete, auditable |
| Evidence | Forensic weight |
| Verification | Technical precision |
| Factory | Industrial, not magical |
| Grinding | Honest about automation |
| Bottleneck | Engineering precision |

### Words We Avoid
| Word | Why |
|------|-----|
| Revolutionary | Marketing speak |
| Leverage | Corporate jargon |
| Seamless | Meaningless |
| Intelligent | Anthropomorphizes |
| Powerful | Vague |
| Best-in-class | Unverifiable |
| Game-changing | Hype |
| AI-powered | Every tool claims this |

## Sentence Structure

**Lead with the point.** Every paragraph starts with its conclusion.

**Use short sentences for impact.** Then elaborate if needed.

**Tables for comparison.** Not prose.

## The Trust Thesis

**Code generation is cheap. Trust is expensive.**

The bottleneck is not "can it write code"—it's "can a human verify and trust the output faster than doing it themselves."

### What "Working Code" Means
| Claim | Meaning |
|-------|---------|
| "Working code" | Gate passed + receipts exist + panel agrees |
| "Tests pass" | pytest exit code 0 + captured output in receipt |
| "Implementation complete" | Work plan items addressed + evidence captured |

### The Trade
| Approach | Cost | Output |
|----------|------|--------|
| Developer implements | ~5 days salary | Code + implicit verification |
| Flow Studio full run | ~$30 | Code + tests + receipts + evidence panel |

## Pre-Publish Checklist

Before publishing, ask:
1. Would a tired senior engineer at 11pm get this?
2. Does every sentence earn its place?
3. Is the math concrete (~$30/run, not "faster")?
4. Is proof before philosophy?
5. Can a skeptic verify every claim?

## Examples

### Opening Lines
```
Bad:  "Welcome to Flow Studio, the next-generation AI-powered
      development platform that transforms how teams build software."

Good: "The job is moving up the stack. Again."
```

### Feature Descriptions
```
Bad:  "Our intelligent agent orchestration seamlessly coordinates
      multiple AI models to deliver optimal results."

Good: "Seven flows. Each step produces receipts. Kill it anytime.
      Resume with zero data loss."
```

## Paradigm Messaging

### The Transition We're In
```
Era 1: Humans manage machine instructions
Era 2: Humans write assembly
Era 3: Humans write high-level code
Era 4: Humans define intent (models handle implementation) ← We are here
```

### What Humans Do Now
| Old Role | New Role |
|----------|----------|
| Write implementation | Define intent |
| Debug syntax | Verify evidence |
| Grind on first drafts | Architect solutions |
| Read every line | Audit evidence panels |

### Messaging Principles
1. Never say "AI replaces developers" → Say "The job moves up the stack"
2. Never say "you don't need to code anymore" → Say "You stop grinding on first drafts"
3. Never say "trust the AI" → Say "Trust the receipts. Exit codes don't lie."
