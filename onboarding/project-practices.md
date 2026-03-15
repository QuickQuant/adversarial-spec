<!-- Base: Brainquarters v1.0 | Project: v1.0 | Last synced: 2026-01-22 -->
# Project-Specific Practices

This document contains patterns and rules specific to **adversarial-spec**.
For universal rules, see `core-practices.md`.

---

## 1. Environment and Tooling (Python 3.10+ / pip)

This project uses Python 3.10+ with standard pip and pyproject.toml.

```json
{
  "python_environment": {
    "python_version": ">=3.10",
    "dependency_manager": "pip with pyproject.toml",
    "commands": {
      "install_deps": "pip install -e .[dev]",
      "run_script": "python3 skills/adversarial-spec/scripts/debate.py",
      "tests": "pytest",
      "lint": "ruff check --fix",
      "type_check": "mypy"
    },
    "notes": [
      "The skill installs to ~/.claude/skills/adversarial-spec/",
      "For development, run scripts directly from repo",
      "litellm is the core dependency for multi-model orchestration"
    ]
  }
}
```

---

## 2. Configuration (Environment Variables)

API keys are loaded from environment variables. No .env file parsing library is used.

```json
{
  "config_loading": {
    "pattern": "os.environ.get('API_KEY_NAME')",
    "api_keys": [
      "OPENAI_API_KEY",
      "ANTHROPIC_API_KEY",
      "GEMINI_API_KEY",
      "XAI_API_KEY",
      "MISTRAL_API_KEY",
      "GROQ_API_KEY",
      "OPENROUTER_API_KEY",
      "DEEPSEEK_API_KEY",
      "ZHIPUAI_API_KEY",
      "TELEGRAM_BOT_TOKEN",
      "TELEGRAM_CHAT_ID"
    ],
    "user_config_location": "~/.claude/adversarial-spec/config.json",
    "session_storage": "~/.config/adversarial-spec/sessions/",
    "rules": [
      "Never log or print API keys",
      "Check key presence with bool(), never expose values",
      "Use the providers.py module for key detection"
    ]
  }
}
```

---

## 3. Logging vs CLI Output

CLI tool with user-facing output. No structured logging library.

```json
{
  "logging_and_output": {
    "cli_output": {
      "pattern": "print() for user-facing messages",
      "cost_tracking": "Display token counts and estimated costs after each round"
    },
    "prohibited_patterns": [
      "Logging API keys or full config dicts",
      "Silent failures during model calls"
    ]
  }
}
```

---

## 4. Project-Specific Patterns

> **This section grows over time via SmartCompact.**
> When you discover a pattern unique to adversarial-spec, add it here.

### Code Organization

```json
{
  "code_organization": {
    "skill_code": "skills/adversarial-spec/scripts/",
    "skill_definition": "skills/adversarial-spec/SKILL.md",
    "execution_planner": "execution_planner/",
    "tests": "tests/ and skills/adversarial-spec/scripts/tests/"
  }
}
```

### Model Integration Pattern

```json
{
  "model_integration": {
    "library": "litellm",
    "provider_detection": "providers.py handles API key detection",
    "cli_adapters": [
      "codex/ prefix routes to Codex CLI",
      "gemini-cli/ prefix routes to Gemini CLI"
    ],
    "enterprise": "AWS Bedrock mode for enterprise compliance"
  }
}
```

### Debate Loop Architecture

```json
{
  "debate_architecture": {
    "flow": [
      "1. User provides spec or concept",
      "2. Optional interview mode for requirements",
      "3. Claude drafts initial document",
      "4. Opponent models critique in parallel",
      "5. Claude synthesizes + adds own critique",
      "6. Revise and repeat until ALL agree",
      "7. User review period",
      "8. Final document output"
    ],
    "convergence": "All models must agree before exiting loop",
    "early_agreement_check": "Press models that agree too quickly"
  }
}
```
