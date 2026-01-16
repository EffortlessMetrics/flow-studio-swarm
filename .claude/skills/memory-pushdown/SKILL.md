---
name: memory-pushdown
description: Refactor project guidance out of CLAUDE.md into thin always-on rules, on-demand skills, and canonical docs. Use when reducing context bloat, reorganizing rules, cleaning documentation, or deciding where new guidance belongs.
---
# Memory Pushdown

Classify content and move it to the right layer.

## Classification Rubric

### Rule (always-on axiom)
Content that is:
- An invariant the model must obey even when inconvenient
- A safety boundary, trust hierarchy, closed vocabulary, or MUST/MUST NOT constraint
- Expressible in <=30 lines with no procedures

**Transform**: Compress to axioms. Remove steps, examples, galleries.

### Skill (procedure)
Content that is:
- A workflow with ordered steps
- Something where sequence matters or artifacts are produced
- Something that should auto-trigger from user phrasing

**Transform**: Steps + outputs/evidence contract. Depth goes to reference.md.

### Doc (curriculum)
Content that is:
- Rationale, tradeoffs, examples, narrative explanation
- Teaching material for humans
- Reference larger than a card

**Transform**: Create canonical doc. Duplicates become redirect stubs.

## Workflow

1. Inventory candidate content (CLAUDE.md sections or rule files that feel procedural/explanatory)
2. Classify each as Rule vs Skill vs Doc using rubric above
3. Apply transforms:
   - Rule: compress to axioms, <=30 lines
   - Skill: create `.claude/skills/<name>/SKILL.md`
   - Doc: create `docs/<domain>/<topic>.md` as canonical
4. Replace removed text with index-style pointer (not transcluded content)
5. Validate: rules stay small, skills exist with matching descriptions, docs are canonicalized

## Signals for Each Layer

| Signal | Rule | Skill | Doc |
|--------|------|-------|-----|
| Numbered steps | No | Yes | Maybe |
| "When X do Y" tables | Short only | Yes | Full |
| Examples/galleries | No | Brief | Full |
| Rationale paragraphs | No | No | Yes |
| MUST/NEVER constraints | Yes | Brief | Ref |

## Output

- File change list (created/updated/deleted)
- Rationale per move (why rule vs skill vs doc)
- Follow-up gaps (missing canonical doc, missing skill triggers)
