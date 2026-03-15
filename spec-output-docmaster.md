# Technical Specification: docmaster (Local Targeted Documentation Lookup CLI)

## Overview / Context

docmaster is a local-first CLI that indexes a small set of local documentation files and returns exact, token-bounded chunks to reduce LLM context usage.

**v1 Scope:** 3 existing files in this repo:
- `docs/raw/coinroutes_api.json` (OpenAPI v2, 142KB)
- `docs/raw/context7_kalshi_docs.txt` (markdown-ish dump, 432KB)
- `docs/raw/context7_polymarket_docs.txt` (markdown-ish dump, 419KB)

No network calls are required or allowed in v1.

## Goals

1. Return the most relevant chunk in ≤500 tokens by default
2. Enable first successful query within 5 minutes from repo checkout
3. Deterministic output ordering for identical inputs
4. Local-only operation with zero network access
5. Simple CLI suitable for shell usage and LLM tool integration

## Non-Goals (v1)

- Network fetching or Context7 integration
- MCP servers or always-on services
- Automatic summarization or generative responses
- Cross-source queries
- Complex configuration hierarchies or environment variables

---

## Getting Started (Bootstrap)

### Prerequisites

- Python 3.11+ (no 3.11-specific features required; 3.11 chosen for tomllib stdlib support)
- `uv` installed

### First-Run Workflow

```bash
# 1. Install dependencies
uv sync

# 2. Initialize sources (updates docmaster.toml)
uv run docmaster init coinroutes --file docs/raw/coinroutes_api.json --format openapi
uv run docmaster init kalshi --file docs/raw/context7_kalshi_docs.txt --format markdown
uv run docmaster init polymarket --file docs/raw/context7_polymarket_docs.txt --format markdown

# 3. Index all sources
uv run docmaster index --all

# 4. Verify setup works
uv run docmaster verify --all

# 5. First query
uv run docmaster search kalshi "place order"
```

**Expected time to first task:** <5 minutes including indexing (~2 seconds for 1MB total).

### Failure Cases

| Condition | Error Code | Resolution |
|-----------|------------|------------|
| Python < 3.11 | `PYTHON_VERSION_ERROR` | Upgrade Python |
| Invalid source ID | `INVALID_SOURCE_ID` | Use only `a-z`, `0-9`, `_`, `-` |
| File not found | `FILE_NOT_FOUND` | Check file path |
| Unsupported format | `UNSUPPORTED_FORMAT` | Use `openapi` or `markdown` |
| Invalid config syntax | `CONFIG_INVALID` | Fix TOML syntax in docmaster.toml |
| Config write failed | `CONFIG_WRITE_ERROR` | Check file permissions |
| Source not in config | `SOURCE_NOT_FOUND` | Run `docmaster init` first |
| Source not indexed | `SOURCE_NOT_INDEXED` | Run `docmaster index <source>` |
| Parse error in source | `PARSE_ERROR` | Check source file format/encoding |
| File not UTF-8 | `ENCODING_ERROR` | Convert file to UTF-8 |
| File too large (>10MB) | `FILE_TOO_LARGE` | Split file or increase limit |
| Index corrupted | `INDEX_CORRUPT` | Run `docmaster index --force` |
| Index stale (source changed) | `INDEX_STALE` | Run `docmaster index <source>` |
| Empty query (no tokens) | `EMPTY_QUERY` | Add meaningful search terms |
| Item not found | `ITEM_NOT_FOUND` | Check item ID with `docmaster list` |
| Path outside docs_root | `PATH_TRAVERSAL` | Use path within docs_root |
| Symlink rejected | `SYMLINK_REJECTED` | Use regular file, not symlink |

---

## Configuration

`docmaster.toml` at repo root is the **source of truth** for registered sources.

```toml
[project]
docs_root = "docs"
default_detail = "signature"
default_max_tokens = 500

# Sources are managed by `init` and `remove` commands
[sources.kalshi]
enabled = true
file = "docs/raw/context7_kalshi_docs.txt"
format = "markdown"

[sources.coinroutes]
enabled = true
file = "docs/raw/coinroutes_api.json"
format = "openapi"

[sources.polymarket]
enabled = true
file = "docs/raw/context7_polymarket_docs.txt"
format = "markdown"
```

**Behavior:**
- `docmaster init` creates/updates entries in `[sources.*]`
- `docmaster remove` deletes entries from `[sources.*]`
- Indexer reads `docmaster.toml` to find enabled sources

**Precedence:** CLI flags override `docmaster.toml`. No environment variables in v1.

**Project root discovery:** Walk upward from CWD to find `docmaster.toml`. Stop at filesystem root or first match (nearest ancestor wins). If none found, use CWD. An explicit `--root PATH` flag overrides discovery entirely.

---

## Data Models

**Verbatim Preservation Principle:** Every item includes a `source_text` field containing the exact, unmodified text from the source document. This field is never synthesized or summarized. "No information lost" means the original text is always recoverable.

### OpenAPI Submodels

```python
class Parameter(BaseModel):
    name: str
    in_: Literal["path", "query", "header", "body", "formData"]
    required: bool = False
    description: str | None = None
    type: str | None = None
    schema: dict | None = None   # For body parameters

class RequestBody(BaseModel):
    description: str | None = None
    required: bool = False
    schema: dict | None = None

class Response(BaseModel):
    code: str                    # "200", "404", etc.
    description: str | None = None
    schema: dict | None = None
```

### EndpointItem (for OpenAPI sources)

```python
class EndpointItem(BaseModel):
    kind: Literal["endpoint"] = "endpoint"
    id: str                      # source_id:operation_id
    operation_id: str
    name: str                    # summary or operationId
    method: str                  # GET, POST, etc.
    path: str                    # /orders, /markets/{id}
    summary: str
    description: str | None = None
    parameters: list[Parameter] = []
    request_body: RequestBody | None = None
    responses: list[Response] = []
    tags: list[str] = []
    source_path: str             # relative path to raw file
    source_anchor: str | None    # JSON pointer
    source_text: str             # NORMALIZED: operation JSON re-serialized with sorted keys
    token_counts: dict[str, int] # {"signature": 42, "excerpt": 120, "full": 350}
```

**Note on source_text for OpenAPI:** The `source_text` field contains the operation's JSON object re-serialized with sorted keys and consistent formatting. This is "normalized" rather than byte-for-byte verbatim because JSON parsers do not preserve original whitespace or key order. The content is semantically identical to the source.

### DocChunkItem (for markdown sources)

```python
class DocChunkItem(BaseModel):
    kind: Literal["doc"] = "doc"
    id: str                      # source_id:section_hash#n
    title: str                   # leaf heading or "Overview"
    section_path: list[str]      # ["Trading", "Orders", "Place Order"]
    summary: str                 # first sentence or 200 chars
    content: str                 # full text for the chunk
    tags: list[str] = []
    source_path: str
    source_anchor: str | None    # heading slug
    source_text: str             # VERBATIM: exact text from source (same as content)
    token_counts: dict[str, int] # {"signature": 25, "excerpt": 80, "full": 400}
```

**ID Generation for DocChunkItem:** IDs are `source_id:hash#n` where `hash` is the first 8 characters of SHA256(full section_path joined by `/`), and `n` is the chunk number within that section (0-indexed). This ensures stable, collision-resistant IDs even when section names repeat.

### Detail Levels

| Level | Endpoint | DocChunk |
|-------|----------|----------|
| `signature` | name, method, path, summary | title, summary |
| `excerpt` | + parameters, request_body | + first 200 tokens of content |
| `full` | + description, responses, **source_text** | + full content, **source_text** |

**Note:** `source_text` at `full` detail contains the exact verbatim text from the source document, enabling "no information lost" retrieval.

---

## Parser Strategies

### OpenAPIV2Strategy

- Input: Swagger/OpenAPI v2 JSON
- Output: `EndpointItem` per (method, path)
- `name` = summary if present, else operationId
- `operation_id` = operationId if present, else `{method}_{path_slug}` where path_slug is the path with `/` replaced by `_` and `{param}` replaced by `param`
- `source_anchor` = JSON pointer (e.g., `/paths/~1orders/post`)
- **ID collision handling:** If generated operation_id collides, append `_2`, `_3`, etc. Emit warning to stderr.

### Context7MarkdownStrategy

- Input: markdown-ish text dumps
- **File preprocessing:** Strip UTF-8 BOM if present. Normalize line endings to `\n`.
- Parse headings by lines starting with `#` (ATX-style only). Lines inside fenced code blocks (``` or ~~~) are excluded from heading detection.
- Underlined headers (`===` or `---`) are **not** supported in v1. Document this limitation.
- Text before first heading → "Overview" section
- Each section yields one or more `DocChunkItem` records
- **Chunk splitting:** If section exceeds 800 tokens, split by paragraph (double newline). If no paragraph breaks exist, split at sentence boundaries (`. ` followed by capital letter). If still >800 tokens, hard-split at 800-token boundary.
- Each chunk beyond the first includes a context prefix: `[{section_path joined by " > "}]\n\n` to preserve context.
- `section_path` = heading stack (e.g., `["Trading", "Orders"]`)
- `summary` = first sentence or first 200 chars

---

## Indexer

1. Read `docmaster.toml` to find sources
2. For each enabled source:
   - Validate source_id matches `^[a-z0-9_-]+$`
   - Instantiate appropriate strategy
   - Parse raw file → list of items
   - Compute `token_counts` for each detail level
   - Build inverted index: `token → [item_ids]`
3. Write to `docs/indexed/{source_id}/` using atomic writes:
   - Write to temp files (`*.tmp`) first
   - Atomically rename to final names only after all files written successfully
   - On interruption (SIGINT), clean up temp files and leave prior index intact
   - Files written:
     - `metadata.json` - index info (written last, acts as commit marker)
     - `items.json` - all items (sorted by `id` for determinism)
     - `inverted_index.json` - keyword lookup (tokens sorted lexicographically, posting lists sorted by `id`)

**Determinism:** Index files use stable JSON key ordering. Identical inputs produce identical outputs.

**Metadata schema (metadata.json):**
```json
{
  "index_version": 1,
  "source_id": "kalshi",
  "source_path": "docs/raw/context7_kalshi_docs.txt",
  "source_sha256": "abc123...",
  "source_size": 432123,
  "source_mtime": 1706400000.0,
  "format": "markdown",
  "created_at": "2026-01-28T12:00:00Z",
  "tokenizer": "tiktoken|char4",
  "item_count": 210
}
```

### Tokenization

- Lowercase, regex `[a-z0-9_]+`, length ≥2
- Stopwords removed: a, an, the, and, or, to, of, in, on, for, with, by, from, is, are
- **Limitation:** v1 tokenization is ASCII-only. CJK, emoji, and symbol-heavy content will have reduced search quality.

### Token Counting

Token counting determines how tokens are estimated for budget enforcement:

- **Index-time:** The tokenizer used at index time is recorded in `metadata.json` (`"tiktoken"` or `"char4"`). Token counts stored in `token_counts` use this tokenizer.
- **Search-time:** The searcher uses the same tokenizer indicated in metadata. If metadata says `tiktoken` but tiktoken is unavailable at search time, return `INDEX_STALE` error with hint to reindex.
- **tiktoken:** If installed, use `tiktoken` with `cl100k_base` encoding. Requires pre-downloaded model files (no network at runtime).
- **Fallback:** If tiktoken unavailable at index time, use `ceil(len(text) / 4)`. This is approximate and may undercount for non-Latin text.

---

## Searcher

### Staleness Detection

Before search/get/list:
1. **Fast path:** Compare `source_mtime` and `source_size` in metadata to current file stats. If both match, index is fresh.
2. **Slow path:** If mtime or size differs, compute `source_sha256` and compare. If hash matches, update cached mtime/size in memory (no disk write). If hash differs, return `INDEX_STALE` with hint to reindex.

### Query Validation

If query tokenizes to zero tokens (all stopwords or empty), return `EMPTY_QUERY` error.

### Candidate Generation

1. Tokenize query
2. Union postings from inverted index
3. If >200 candidates, keep top 200 by token hit count

### Scoring (Deterministic)

| Match Type | Score |
|------------|-------|
| Exact id match | +100 |
| Exact name/title match | +70 |
| Exact method+path (endpoint) | +50 |
| All query tokens in name/title | +40 |
| All query tokens in summary | +30 |
| Per token match in name/title | +8 |
| Per token match in summary/content | +4 |

**Tie-break:** (-score, title_lower, id)

### Token Budgeting (Greedy Packing)

```
remaining_budget = max_tokens (default 500)
results = []

for item in candidates_sorted_by_score:
    cost = token_counts[requested_detail]

    # Downgrade if needed
    if cost > remaining_budget:
        for fallback in [excerpt, signature]:
            if token_counts[fallback] <= remaining_budget:
                cost = token_counts[fallback]
                detail = fallback
                break

    # Skip if doesn't fit even at signature
    if cost > remaining_budget:
        truncated = true
        continue

    results.append(item at detail level)
    remaining_budget -= cost

    if len(results) >= limit:
        break
```

- `truncated`: true if any items skipped due to budget or limit
- Budget is consumed greedily by highest-scoring items first
- **Design note:** Greedy packing prioritizes the highest-relevance items over maximizing result count. This is intentional per Goal 1 ("most relevant chunk"). Users who prefer breadth can request `--detail signature` to fit more items.

---

## CLI Commands

**Source ID constraints:** Must match `^[a-z0-9_-]+$` (lowercase alphanumeric, underscore, hyphen).

```bash
# Initialize a source (updates docmaster.toml)
docmaster init <source_id> --file PATH --format openapi|markdown [--name NAME]

# Remove a source (updates docmaster.toml, deletes index)
docmaster remove <source_id>

# Index sources
docmaster index <source|--all> [--force]

# Verify setup works (run after init+index)
docmaster verify <source|--all> [--query "test query"]

# Search
docmaster search <source> "query" [--detail signature|excerpt|full] [--max-tokens N] [--limit N] [--json]

# Get single item
docmaster get <source> <item_id> [--detail signature|excerpt|full] [--json]

# List all items
docmaster list <source> [--limit N] [--json]

# Show sources
docmaster sources [--json]

# Override project root discovery
docmaster --root PATH <command>
```

---

## JSON Output

All commands support `--json` for machine-readable output.

### Success Envelope (all commands)

```json
{
  "ok": true,
  "command": "search",
  "source": "kalshi",
  "data": { ... },
  "timing_ms": 12
}
```

**Note on timing_ms:** This measures wall-clock time from after Python initialization and imports complete until output is ready. It does **not** include Python startup or import time. The `<100ms` search target applies to this internal timing.

### Error Envelope (all commands)

```json
{
  "ok": false,
  "command": "search",
  "error": {
    "code": "SOURCE_NOT_FOUND",
    "message": "Source 'kalshi' not indexed",
    "hint": "Run: docmaster index kalshi"
  }
}
```

### Command-Specific Data

**init:**
```json
{
  "source_id": "kalshi",
  "file": "docs/raw/context7_kalshi_docs.txt",
  "format": "markdown",
  "config_updated": true
}
```

**remove:**
```json
{
  "source_id": "kalshi",
  "config_updated": true,
  "index_deleted": true
}
```

**index:**
```json
{
  "source_id": "kalshi",
  "items_indexed": 210,
  "index_path": "docs/indexed/kalshi"
}
```

**verify:**
```json
{
  "source_id": "kalshi",
  "status": "ok",
  "items_count": 210,
  "test_query": "place order",
  "test_results": 3
}
```

**search:**
```json
{
  "query": "place order",
  "total_found": 12,
  "returned_count": 3,
  "total_token_count": 320,
  "truncated": false,
  "results": [
    {
      "item": {
        "kind": "endpoint",
        "id": "coinroutes:post_orders",
        "name": "Place Order",
        "method": "POST",
        "path": "/orders",
        "summary": "Submit a new order",
        "source_text": "..."
      },
      "score": 87.2,
      "detail_level": "signature",
      "token_count": 42
    }
  ]
}
```

**get:**
```json
{
  "item": {
    "kind": "endpoint",
    "id": "coinroutes:post_orders",
    "name": "Place Order",
    "source_text": "{ full verbatim JSON from source }"
  },
  "detail_level": "full",
  "token_count": 350
}
```

**list:**
```json
{
  "total_items": 210,
  "returned_count": 20,
  "items": [
    { "kind": "doc", "id": "kalshi:a1b2c3d4#0", "title": "Trading", "summary": "..." }
  ]
}
```

**sources:**
```json
{
  "sources": [
    {
      "id": "kalshi",
      "name": "Kalshi API",
      "file": "docs/raw/context7_kalshi_docs.txt",
      "format": "markdown",
      "enabled": true,
      "indexed": true,
      "item_count": 210
    }
  ]
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Source not found / not indexed |
| 4 | Item not found |
| 5 | Parse/index error |
| 6 | I/O error (file read/write) |
| 7 | Config error (invalid TOML) |
| 8 | Security error (path traversal, symlink) |

---

## Storage Layout

```
project-root/
├── docmaster.toml
└── docs/
    ├── raw/                          # User-provided files
    │   ├── coinroutes_api.json
    │   ├── context7_kalshi_docs.txt
    │   └── context7_polymarket_docs.txt
    └── indexed/                      # Generated
        ├── coinroutes/
        │   ├── metadata.json
        │   ├── items.json
        │   └── inverted_index.json
        ├── kalshi/
        └── polymarket/
```

---

## Infrastructure

### Dependencies

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "orjson>=3.0",
    "tomli>=2.0;python_version<'3.11'",
    "rich>=13.0",
]

[project.optional-dependencies]
tokens = ["tiktoken>=0.5"]
```

**tiktoken setup:** If using the `tokens` extra, users must pre-download the BPE model files before first use in an offline environment. Run `python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"` once with network access to cache the model.

### Requirements

- Memory: <100MB during indexing (v1 file limit ensures this)
- Disk: ~1.5x raw file size per indexed source (due to verbatim source_text + metadata)
- No network dependencies at runtime

---

## Security

- All file operations confined to project root
- Reject symlinks in `docs/` (simplifies path validation; may relax in future versions)
- Max raw file size: 10MB (reduced from 50MB to ensure <100MB memory during indexing)
- No network I/O in v1

---

## Performance

| Operation | Target |
|-----------|--------|
| Index (3 files, 1MB) | <2 seconds |
| Search (internal) | <100ms |
| Memory (indexing) | <100MB |

**Defaults:**
- `max_tokens`: 500
- `limit`: 5
- `detail`: signature

---

## Testing Strategy

- Unit: tokenization, ID generation, scoring
- Parser: OpenAPI and Context7Markdown fixtures, including BOM handling, code blocks with `#`
- Indexer: atomic writes, item counts, interruption recovery
- Search: deterministic ordering, token budgets, staleness detection
- CLI: JSON envelopes, exit codes

---

## Known Limitations (v1)

1. **ASCII-only tokenization:** Search quality degraded for CJK, emoji, or symbol-heavy content
2. **No underlined headers:** Markdown parser only recognizes ATX-style (`#`) headings
3. **Symlinks rejected:** Symlinks in docs/ are not followed (security simplification)
4. **tiktoken network:** First-time tiktoken setup requires network to download BPE model
5. **Greedy packing:** May skip smaller relevant items after a large one fills the budget

---

## Future Considerations (Not in v1)

- Network fetch for new sources
- MCP server for long sessions
- SQLite backend for >100k items
- Cross-source queries
- OpenAPI v3 support
- Unicode tokenization
- Symlink support with canonical path validation
