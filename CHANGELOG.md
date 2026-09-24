# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Slice North Star routing from Phase 0 candidate through requirements lock and
  one roadmap milestone.
- Version 6 Decomposition guidance for component boundaries, seam evidence, and
  bounded Debate fan-out before the system gauntlet.
- Explicit pipeline and uncarded context-transport paths, with context readiness
  retained for gauntlet revalidation.

### Changed

- Defined one eight-Phase lifecycle. Verification is now the Phase 8 subflow,
  not a separate lifecycle Phase.
- Consolidated routing, transitions, Card comments, notifications, decisions,
  and journey records under `SKILL.md`; specialist references now own their
  respective contracts.
- Kept model assignments in one canonical reference and converted the root
  model document into a redirect.
- Preserved the target-architecture fingerprint consumed by execution
  reconciliation and reduced it to one named comparison.
- Reworked repository documentation into a current operator guide, focused
  contribution instructions, compact project practices, and a mechanism-based
  process-failure index.

### Removed

- Retired board-system guidance, old phase numbering, duplicate model catalogs,
  numeric complexity routing, and prose-only workflow machinery from active
  documentation.
- Orphaned historical proposals, generated snapshots, and unused integration
  exports that had no live consumer.

## [1.0.0] - 2025-01-11

### Added

- Multi-model adversarial debate for spec refinement
- Support for multiple LLM providers via LiteLLM:
  - OpenAI (gpt-4o, gpt-4-turbo, o1)
  - Google (gemini/gemini-2.0-flash, gemini/gemini-pro)
  - xAI (xai/grok-3, xai/grok-beta)
  - Mistral (mistral/mistral-large, mistral/codestral)
  - Groq (groq/llama-3.3-70b-versatile)
  - Deepseek (deepseek/deepseek-chat)
  - Zhipu (zhipu/glm-4, zhipu/glm-4-plus)
- Codex CLI integration for ChatGPT subscription models
- AWS Bedrock integration for enterprise users
- OpenAI-compatible endpoint support for local/self-hosted models
- Document types: PRD (product) and Tech Spec (engineering)
- Interview mode for in-depth requirements gathering
- Claude's active participation in debates alongside opponent models
- Early agreement verification to prevent rubber-stamping
- User review period with change request workflow
- PRD to Tech Spec flow for complete documentation
- Critique focus modes: security, scalability, performance, ux, reliability, cost
- Professional personas: security-engineer, oncall-engineer, junior-developer, qa-engineer, etc.
- Context injection for existing documents
- Session persistence and resume functionality
- Auto-checkpointing for rollback capability
- Preserve intent mode requiring justification for removals
- Cost tracking with per-model breakdown
- Saved profiles for frequently used configurations
- Diff between spec versions
- Export to task list (with JSON output option)
- Telegram integration for async notifications and human-in-the-loop feedback
- Retry with exponential backoff for API resilience
- Response validation warnings for malformed outputs

### Technical

- Modular codebase: debate.py, models.py, providers.py, session.py, prompts.py, telegram_bot.py
- Full type hints with py.typed marker
- Google-style docstrings
- Input validation for security-sensitive operations
- Structured logging for exception handling
- Unit tests with pytest (194 tests, 91% coverage)
- CI workflow with linting (ruff), type checking (mypy), tests with coverage threshold
- Pre-commit hooks for code quality
