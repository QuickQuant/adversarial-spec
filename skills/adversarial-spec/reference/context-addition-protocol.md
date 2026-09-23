## Context Addition Protocol

### Purpose

Give critics enough repository evidence to validate claims without sending
irrelevant or sensitive material. Phase 3's **Context Readiness Audit** owns
`ContextInventoryV1`, including source selection, retention, and revalidation.
This reference owns the two implemented transports and the per-round selection
rule.

### Choose the transport

| Path | Transport | Implemented behavior |
|---|---|---|
| Pipeline debate round | Pass `domain_context` to `pipeline_begin_debate_round` with explicit `board_id`. | A non-empty string is appended under `## Domain Context` in the round workspace's `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`; the same value is stored in `context.json`. The MCP does not select, sanitize, or truncate it. |
| Direct/uncarded CLI | Repeat `debate.py critique --context PATH` as needed. | `load_context_files()` reads each complete file, wraps it as `### Context: PATH` under `## Additional Context`, and includes read errors in that section. It does not extract or truncate snippets. |

Use the transport owned by the entrypoint. Do not send the same source through
both paths in one round. For direct CLI use, pass only a file whose complete
contents are safe and relevant; if only an excerpt is appropriate, first create
a reviewed, scoped context note and pass that whole note. The current critique
parser still requires `--pipeline-card`; an uncarded invocation uses its
`IntentionalOverride` gate and reason.

### Round decision rule

Add context only when it can change the critique. Ask: **Would an engineer open
a specific repository artifact to validate this round's claim?**

| Round | Default | Exception or focus |
|---|---|---|
| 1 — requirements | No | Include an existing interface only when compatibility with it is a requirement. |
| 2 — architecture | Yes | Prefer actual schemas, types, boundaries, and architecture constraints. |
| 3 — implementation detail | Selective | Add only sources needed by unresolved concerns; do not resend unchanged material. |
| 4+ — refinement | Rare | Add or refresh a source only for a concrete verification question. |

### Extraction/selection allowlist

When context is warranted, select the smallest useful set from:

- relevant `.architecture/primer.md` content and source-backed component maps;
- schema, model, interface, protocol, enum, and state-machine definitions;
- signatures for functions the document changes or wraps;
- API request/response contracts and database table definitions;
- configuration shapes and named constants, without secret values;
- error types and the names/locations of relevant tests.

Never send:

- `.env` files, credentials, tokens, customer data, or secret-bearing config;
- dependency trees, lock files, generated code, vendored modules, or binaries;
- irrelevant implementation bodies or test assertion bodies;
- raw git history or diffs; or
- a whole source file merely to expose one safe declaration.

Because `--context` reads whole files, any excluded content anywhere in a file
disqualifies that file from the direct CLI transport.

### Provenance and staleness

Before dispatch, bind selected context to:

- extraction/selection time in ISO 8601;
- current git HEAD and branch;
- source paths; and
- dirty-worktree status for those paths.

Store that binding in the Phase 3 inventory or include it at the start of
`domain_context`. Reuse a source only when HEAD and relevant working-tree content
are unchanged. Re-read sources touched by later commits or local edits and warn
when a dirty file is intentionally used. Treat unreadable or unsafe sources as
context gaps; never replace them with an unverified summary.

### Inventory ownership

See `phases/03-debate.md` § **Context Readiness Audit** for the
`ContextInventoryV1` lifecycle. Retain and revalidate that inventory for the
gauntlet consumer; do not recreate its schema or lifecycle here.
