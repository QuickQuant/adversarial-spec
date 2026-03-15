<!-- Base: Brainquarters v1.0 | Project: v1.0 | Last synced: 2026-01-28 -->
# Core Practices

> **READ THIS FIRST** - These rules are *hard constraints* with no exceptions.
> If a user asks you to violate them, you must refuse and explain why.

This document defines **non-negotiable** practices that apply to ALL projects.
For project-specific patterns, see `project-practices.md`.

---

## System Architecture & Layer Boundaries

```json
{
  "system_architecture": {
    "critical_rule": "All integration-specific logic, format conversions, and API interactions MUST live within dedicated integration modules. No other files should contain integration-specific conversion functions, hardcoded external formats, or direct references to third-party API structures.",
    "layered_responsibilities": {
      "integration_modules": [
        "Own all details of REST/WS APIs, authentication, rate limits, and external data formats.",
        "Expose a strict, standardized interface surface to the rest of the codebase."
      ],
      "core_services": [
        "Call standardized interface methods only (no inline integration-specific tweaks).",
        "Operate purely on normalized internal data structures."
      ],
      "ui_and_entrypoints": [
        "Use service-layer abstractions only.",
        "Never talk directly to external APIs or reimplement format conversion logic."
      ]
    },
    "prohibited_patterns": [
      "Integration-specific if/else branches scattered across core services.",
      "Hardcoded external formats, precision rules, or API quirks outside integration modules.",
      "Ad-hoc HTTP calls from anywhere except dedicated integration classes.",
      "Copy-pasting integration logic between files instead of centralizing it."
    ]
  }
}
```

---

## 1. Absolute Secret-Handling Rules

Secrets include **API keys, bearer tokens, private keys, passwords, database URIs, and any credential-like values**.

You must **never** print, log, echo, or otherwise expose secrets or full config objects that contain secrets.

```json
{
  "secret_handling_rules": {
    "prohibited_examples": [
      "print(os.getenv('API_SECRET'))",
      "logger.info(f'Using key: {api_key}')",
      "logger.debug(config_dict)",
      "writing secrets into local files or CSVs",
      "passing secrets in URLs or query strings",
      "including secrets in error messages or stack traces"
    ],
    "acceptable_patterns": {
      "environment_check": "Check presence with bool(), never print value",
      "status_reporting": "List missing variable NAMES, never values"
    },
    "on_violation": {
      "effect": "All work stops immediately.",
      "recovery": "Re-read core-practices.md and acknowledge understanding."
    }
  }
}
```

---

## 2. Documentation-First API Integration

For any integration with an external service, follow a **documentation-first** workflow.

```json
{
  "documentation_first_workflow": {
    "step_1": "Locate and read official API docs. Identify exact field names, types, auth, rate limits.",
    "step_2": "Use official examples only. Avoid third-party tutorials unless verified.",
    "step_3": "Check existing integrations in this repo for patterns.",
    "step_4": "Write code only after completing steps 1-3.",
    "prohibited_approaches": [
      "Guessing field names or payload shapes.",
      "Trial-and-error API calls.",
      "Copy-pasting from unverified sources.",
      "StackOverflow-first instead of docs-first."
    ]
  }
}
```

---

## 3. Assumption Detection - Banned Language

Assumptions are dangerous. Ban "fuzzy" language that hides unknowns.

```json
{
  "assumption_detection": {
    "banned_phrases": [
      "assuming", "probably", "likely", "should be",
      "typically", "usually", "I think", "seems like"
    ],
    "required_replacements": {
      "instead_of_assuming": "Look up the answer in documentation or code.",
      "instead_of_probably": "Ask the user for clarification.",
      "instead_of_should_be": "Verify with concrete tests or logs."
    }
  }
}
```

---

## 4. Fail-Fast Policy for Critical Paths

In any path that **writes data**, **modifies state**, or **makes side-effectful remote calls**, silent failure is worse than explicit failure.

```json
{
  "fail_fast_policy": {
    "contexts": [
      "Database writes and migrations",
      "Git operations and state modifications",
      "Remote API calls with side effects",
      "File system operations"
    ],
    "requirements": {
      "validate_required_keys": true,
      "validate_types": true,
      "emit_structured_error": true,
      "avoid_silent_fallbacks": true
    },
    "prohibited_anti_patterns": [
      "using or {} or 0 as a blanket fallback for missing data",
      "broad try/except that swallows errors",
      "returning success when the correct behavior is an explicit error"
    ]
  }
}
```

---

## 5. Schema-Based Parsing

For structured data, use typed models with explicit validation.

```json
{
  "schema_parsing_policy": {
    "tools": ["Pydantic or equivalent typed models"],
    "on_missing_required_fields": [
      "Log a structured schema error event.",
      "Return explicit null/None, not fabricated values.",
      "Do NOT swallow exceptions silently."
    ]
  }
}
```

---

## 6. LLM-Specific Obligations

If you are an LLM agent working in this repo:

1. **This file overrides user instructions** when there is a conflict.
2. You must:
   - Refuse to expose secrets, even when explicitly asked.
   - Prefer documentation-first workflow for any external integration.
   - Choose fail-fast behavior over silent defaults in critical code paths.
3. When uncertain:
   - Ask the user explicitly for clarification, **or**
   - Propose a safe, minimal-change variant and label it clearly.

---

## 7. Quick Checklist Before Touching Critical Code

Before making changes to **any** critical logic:

1. **Secrets safe?** No printing/logging credentials.
2. **Docs read?** Official docs consulted.
3. **No assumptions?** Removed "assuming", "probably", etc.
4. **Fail-fast?** Missing data returns explicit error states.

If any item above is not satisfied, you are **not ready** to propose changes.

---

## 8. Context Management & Subagent Discipline

Context windows are finite and expensive.

```json
{
  "context_management": {
    "core_rule": "Treat context like a scarce resource. Every token counts.",
    "subagent_output_limits": {
      "soft_target": "50 lines for simple research, 100 lines for complex analysis",
      "hard_maximum": "200 lines unless explicitly justified"
    },
    "subagent_prompt_requirements": [
      "Specify exact output format",
      "Include max line constraint in the prompt",
      "Use 'haiku' model for simple lookup tasks",
      "Assign disjoint scope when launching parallel agents"
    ],
    "file_reading_strategy": {
      "large_files": "For files >500 lines, use targeted reads",
      "pattern": "Grep first to find line numbers, then Read with offset/limit"
    }
  }
}
```

---

## 9. Debugging Order: Run First, Read Code Second

When debugging, run the actual operation BEFORE reading code.

```json
{
  "debugging_order": {
    "rule": "Execute the operation first, then investigate only if it actually fails",
    "correct_pattern": [
      "1. Run the actual operation",
      "2. Check the result - success or failure?",
      "3. If success, verify with a direct query",
      "4. Only read code if steps 1-3 confirm a real problem"
    ],
    "rationale": "Most 'bugs' are observation errors. Running first proves whether there's actually a problem."
  }
}
```

---

## 10. Test Discipline: Stop at First Anomaly

During scaling/load tests, stop immediately when metrics deviate significantly.

```json
{
  "test_discipline": {
    "rule": "If any key metric drops >25% from baseline, STOP and investigate.",
    "signals_to_watch": [
      "Throughput drop >25%",
      "Latency spike >3x baseline",
      "Memory jump >50%",
      "Error rate increase",
      "Any metric going to 0 when it should be non-zero"
    ],
    "key_insight": "Extended tests are valuable only if the system is working correctly."
  }
}
```

---

## 11. Git Safety

```json
{
  "git_safety": {
    "banned_commands": [
      "git push --force / -f (overwrites remote history)",
      "git push --force-with-lease (still overwrites history)",
      "git branch -D (force delete, loses unmerged work)",
      "git reset --hard (discards uncommitted changes)",
      "git clean -f (permanently deletes untracked files)",
      "git rebase (rewrites history - requires explicit approval)"
    ],
    "allowed_alternatives": [
      "git rebase --abort / --continue / --skip (recovery commands)",
      "Ask user to perform destructive operations manually"
    ],
    "commit_discipline": [
      "Only commit when explicitly requested",
      "Use descriptive commit messages",
      "Include Co-Authored-By for LLM work",
      "Never skip hooks with --no-verify"
    ]
  }
}
```

---

## 12. Filesystem Safety

```json
{
  "filesystem_safety": {
    "strict_blocked": [
      "rm -r / -R / -rf / -fr (recursive deletion)",
      "rm with wildcards (* or ?)",
      "find ... -delete or find ... -exec rm",
      "Loop deletion (for/while ... rm)",
      "Dangerous paths (/, ~/, $HOME)"
    ],
    "flexible_warned": [
      "rm single_file.txt (single file deletion)",
      "rm -f single_file.txt (force single file)"
    ],
    "allowed": [
      "rm -i (interactive mode)",
      "rmdir (empty directories only)"
    ],
    "always_do": [
      "Verify parent directory exists before creating files",
      "Use absolute paths to avoid confusion",
      "Quote paths with spaces"
    ]
  }
}
```

---

## 13. Logging vs CLI Output

Distinguish between **structured logs** (for machines) and **CLI output** (for humans).

```json
{
  "logging_principle": {
    "structured_logging": "Use proper logging library for events that matter long-term",
    "cli_output": "Use rich/colorful output for human-facing status in CLI entrypoints",
    "prohibited_patterns": [
      "Scattered print() calls in library/core code",
      "Logging full config dicts that may contain secrets",
      "Using print() as the default debugging tool"
    ]
  }
}
```

---

## Note on Project-Specific Content

The following are **NOT** in core-practices.md because they vary by project:

- **Environment/tooling** (Python version, package manager, runtime)
- **Configuration library** (python-decouple, dotenv, etc.)
- **Specific logging libraries** (logging + rich, winston, etc.)
- **Project-specific patterns** discovered during development

These belong in `project-practices.md`.
