# Explanation Documents

This directory contains teaching documents that explain the **why** behind Flow Studio's design.

These are "textbook" documents—they teach concepts. For the actual rules that are
enforced, see `.claude/rules/`.

## Document Index

| Document | Purpose |
|----------|---------|
| [ATTENTION_ARBITRAGE.md](./ATTENTION_ARBITRAGE.md) | The economic engine (trade tokens for senior attention) |
| [TRUTH_HIERARCHY.md](./TRUTH_HIERARCHY.md) | What counts as evidence (physics > receipts > narrative) |
| [BOUNDARY_PHYSICS.md](./BOUNDARY_PHYSICS.md) | Why isolation enables autonomy (sandbox + publish gates) |
| [ADVERSARIAL_LOOPS.md](./ADVERSARIAL_LOOPS.md) | How opposition creates reliability (author ⇄ critic) |
| [OPERATING_MODEL.md](./OPERATING_MODEL.md) | The PM/IC organization (kernel/navigator/agents) |
| [PORTS_AND_ADAPTERS.md](./PORTS_AND_ADAPTERS.md) | Engine-agnostic architecture (transport abstraction) |
| [CLAIMS_VS_EVIDENCE.md](./CLAIMS_VS_EVIDENCE.md) | The Sheriff pattern (forensics over narrative) |
| [OBSERVABLE_BY_DEFAULT.md](./OBSERVABLE_BY_DEFAULT.md) | Everything leaves a trace (receipts + artifacts) |
| [FORENSICS_OVER_TESTIMONY.md](./FORENSICS_OVER_TESTIMONY.md) | Legal epistemology applied to AI trust |
| [FORENSIC_SCANNERS.md](./FORENSIC_SCANNERS.md) | The Sheriff's tools (diff scanner, test parser) |
| [CLAIMS_REGISTER.md](./CLAIMS_REGISTER.md) | Meta-honesty: what's implemented vs aspirational |
| [WISDOM_PIPELINE.md](./WISDOM_PIPELINE.md) | How learnings become rules (governance evolution) |
| [SCARCITY_AS_DESIGN.md](./SCARCITY_AS_DESIGN.md) | Why token limits are features, not bugs (constraint-driven design) |
| [STAGED_PUBLICATION.md](./STAGED_PUBLICATION.md) | The draft/publish paradigm (lab vs journal) |

## The Core Philosophy

These documents encode Steven Zimmerman's AI-native development vision:

### The Economic Thesis
> Code generation is fast, good, and cheap. The bottleneck is trust.

### The Trade
> Spend compute to save senior engineer attention.

### The Posture
> Autonomy inside containment; gated publishing at exits.

## Reading Order

For newcomers:
1. **ATTENTION_ARBITRAGE.md** - Understand the core economic trade
2. **OPERATING_MODEL.md** - Understand the hierarchy
3. **TRUTH_HIERARCHY.md** - Understand what counts as evidence
4. **BOUNDARY_PHYSICS.md** - Understand containment
5. **ADVERSARIAL_LOOPS.md** - Understand microloops
6. **CLAIMS_VS_EVIDENCE.md** - Understand the Sheriff pattern
7. **OBSERVABLE_BY_DEFAULT.md** - Everything leaves a trace
8. **FORENSICS_OVER_TESTIMONY.md** - Legal epistemology applied to AI trust
9. **FORENSIC_SCANNERS.md** - The tools that implement forensics
10. **PORTS_AND_ADAPTERS.md** - Understand the transport layer
11. **WISDOM_PIPELINE.md** - Understand how the factory improves itself
12. **SCARCITY_AS_DESIGN.md** - Understand why limits are features
13. **STAGED_PUBLICATION.md** - Understand the draft/publish paradigm
14. **CLAIMS_REGISTER.md** - See what's actually implemented vs designed

## Related Documents

- [docs/AGOPS_MANIFESTO.md](../AGOPS_MANIFESTO.md) - The full AgOps philosophy
- [docs/ROUTING_PROTOCOL.md](../ROUTING_PROTOCOL.md) - V3 routing specification
- [docs/LEXICON.md](../LEXICON.md) - Canonical vocabulary
- [.claude/rules/](../../.claude/rules/) - Enforced rules

## Flow Studio vs DemoSwarm

**Flow Studio** (this repo): The harness/pipeline running on top of Claude Code.
Implements the kernel, transports, and orchestration.

**DemoSwarm** (sister repo): Portable `.claude/` pack for embedding in other repos.
Teaches agent design patterns.

Same core AgOps concepts. Different focus:
- Flow Studio teaches **factory physics**
- DemoSwarm teaches **agent craft**
