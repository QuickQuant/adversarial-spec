# Context Directory

This directory stores SmartCompact chunks - compressed knowledge extracted at session end.

## Structure

```
context/
├── _index.json           # Deduplication index
├── meta/<domain>/        # Narrative/conceptual chunks
│   └── *.md
└── code/<domain>/        # Code-related chunks
    └── *.code
```

## How It Works

1. At session end, SmartCompact extracts valuable patterns
2. New chunks are written here with domain tags
3. `_index.json` tracks chunk hashes to prevent duplicates
4. `context_loader.sh` includes relevant chunks in `.active_context.md`

## Guidelines

- Chunks should be self-contained and reusable
- Use clear filenames that describe the content
- Don't duplicate content that's in task-summary.md or project-practices.md
