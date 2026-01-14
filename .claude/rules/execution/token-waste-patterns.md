# Token Waste Patterns

## Purpose

Token waste indicates design problems, not just cost issues. These anti-patterns cause context pollution, reduced reasoning quality, and budget overruns.

## The Rule

> Tokens are cheap but not free. Waste indicates design problems.
> Every token should earn its place.

## Why Waste Matters

Bloated context causes:
- Model drift from instructions
- Reduced reasoning quality
- Slower execution
- Budget overruns on long runs

## The Four Anti-Patterns

### The Kitchen Sink

Loading everything "just in case."

```python
# Bad: Load everything
context = load_all_artifacts() + load_history() + load_related_files()
```

**Problem:** Dilutes focus, wastes tokens, causes confusion.
**Fix:** Load only what teaching notes require.

### The Narrator

Verbose explanations instead of structured output.

```
# Bad: Verbose explanation
"Let me explain in detail what I'm about to do and why..."
```

**Problem:** Wastes output tokens, obscures key information.
**Fix:** Use structured output schemas.

### The Repeater

Re-stating instructions or context.

```
# Bad: Re-stating instructions
"As you asked me to do, I will now implement..."
```

**Problem:** Teaching notes are loaded once at step start.
**Fix:** Trust that the kernel handles instruction loading.

### The Copy-Paster

Full output inline instead of evidence pointers.

```
# Bad: Full output inline
"Here are the complete test results: [500 lines of output]"
```

**Problem:** Evidence belongs in files, not in handoffs.
**Fix:** Write to file, include pointer.

## Input Waste Patterns

### Loading Conversation History

**Wrong:** Rely on chat history for context
**Right:** Rehydrate from artifacts on disk

Session amnesia is a feature. Each step starts fresh and loads from artifacts.

### Full File Reads When Grep Would Do

**Wrong:** Read entire file to find one function
**Right:** Grep for function, read only relevant section

```bash
# Good: Targeted search
grep -n "def authenticate" src/auth.py

# Bad: Full file read
cat src/auth.py  # Then search in prompt
```

## Monitoring for Waste

### Alert on Outliers

| Condition | Alert Level | Action |
|-----------|-------------|--------|
| Step > 2× flow average | Warning | Investigate bloat |
| Step > 3× flow average | Error | Redesign step |
| Coordination > 30% | Warning | Simplify handoffs |

### Identify Bloated Prompts

Common bloat sources:
- Full file contents instead of paths
- Repeated instructions across messages
- Verbose system prompts
- Unused context "just in case"

## Design Signal Interpretation

| Signal | Problem | Fix |
|--------|---------|-----|
| Steps consistently over budget | Step scope too broad | Split into smaller steps |
| High coordination overhead | Flow has too many steps | Consolidate steps |
| Repeated content | Context discipline failing | Enforce loading hierarchy |
| Verbose outputs | Structured schemas missing | Add output schema |

---

## See Also
- [token-budgets.md](./token-budgets.md) - Budget allocation
- [token-compression.md](./token-compression.md) - Compression patterns
- [context-discipline.md](./context-discipline.md) - Session amnesia rules
- [scarcity-enforcement.md](../governance/scarcity-enforcement.md) - Budgets as design
