# Token Compression

Summarize, point, structure. Never transcribe.

## Heavy Loaders Compress
- One agent reads 50k tokens, produces 2k summary
- Ten downstream agents each get 2k instead of 50k
- Math: 50k + (10 × 2k) = 70k vs 10 × 50k = 500k

Heavy loading is a multiplier, not waste.

## Patterns
| Instead of | Use |
|------------|-----|
| Inline content | Path reference |
| Full file | Diff or excerpt |
| Prose explanation | Structured JSON |
| Test output | Summary + evidence path |
| Full reasoning | Key decisions only |

## The Rule
- Summarize before loading (> 10k = always summarize)
- Use paths, not contents
- Structured over prose
- Evidence pointers over inline evidence

> Docs: docs/execution/TOKEN_BUDGETS.md
