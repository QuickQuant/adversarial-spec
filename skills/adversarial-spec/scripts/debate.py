#!/usr/bin/env python3
"""
Adversarial spec debate script.
Sends specs to multiple LLMs for critique using LiteLLM.

Usage:
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --doc-type spec --depth product
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --doc-type spec --depth technical
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --doc-type debug
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --focus security
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --persona "security engineer"
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --context ./api.md --context ./schema.sql
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --profile strict-security
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --preserve-intent
    echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --session my-debate
    python3 debate.py critique --resume my-debate
    echo "spec" | python3 debate.py diff --previous prev.md --current current.md
    echo "spec" | python3 debate.py export-tasks --doc-type spec --depth product
    python3 debate.py providers
    python3 debate.py profiles
    python3 debate.py sessions

Supported providers (set corresponding API key):
    OpenAI:     OPENAI_API_KEY       models: gpt-5.2, o3-mini, gpt-5.2-mini
    Anthropic:  ANTHROPIC_API_KEY    models: claude-opus-4-5-20251124, claude-sonnet-4-5-20250929
    Google:     GEMINI_API_KEY       models: gemini/gemini-3-pro, gemini/gemini-3-flash
    xAI:        XAI_API_KEY          models: xai/grok-4, xai/grok-4.1-fast
    Mistral:    MISTRAL_API_KEY      models: mistral/mistral-large-3, mistral/mistral-medium-3
    Groq:       GROQ_API_KEY         models: groq/llama-4-maverick, groq/llama-3.3-70b-versatile
    OpenRouter: OPENROUTER_API_KEY   models: openrouter/openai/gpt-5.2, openrouter/anthropic/claude-sonnet-4.5
    Codex CLI:  (ChatGPT subscription) models: codex/gpt-5.2-codex, codex/gpt-5.1-codex-max
                Install: npm install -g @openai/codex && codex login
                Reasoning: --codex-reasoning xhigh (minimal, low, medium, high, xhigh)

Document types:
    spec  - Specification (default). Use --depth to control focus:
            --depth product    Product focus (user stories, stakeholders, metrics)
            --depth technical  Technical focus (architecture, APIs, data models)
            --depth full       Both product and technical sections
    debug - Debug Investigation (evidence-based diagnosis, proportional fixes)

Exit codes:
    0 - Success
    1 - API error
    2 - Missing API key or config error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
os.environ["LITELLM_LOG"] = "ERROR"

try:
    from litellm import completion
except ImportError:
    print(
        "Error: litellm package not installed. Run: pip install litellm",
        file=sys.stderr,
    )
    sys.exit(1)

from models import (  # noqa: E402
    ModelResponse,
    call_models_parallel,
    cost_tracker,
    extract_tasks,
    generate_diff,
    get_critique_summary,
    is_o_series_model,
    load_context_files,
)
from prompts import EXPORT_TASKS_PROMPT, get_doc_type_name  # noqa: E402
from providers import (  # noqa: E402
    DEFAULT_CODEX_REASONING,
    get_bedrock_config,
    get_default_model,
    handle_bedrock_command,
    list_focus_areas,
    list_personas,
    list_profiles,
    list_providers,
    load_profile,
    save_profile,
    validate_bedrock_models,
    validate_model_credentials,
)
from session import SESSIONS_DIR, SessionState, save_checkpoint  # noqa: E402
from gauntlet import (  # noqa: E402
    ADVERSARIES,
    format_gauntlet_report,
    get_adversary_leaderboard,
    get_medal_leaderboard,
    run_gauntlet,
)

# Optional task tracking - only import if needed
_task_manager = None


def get_task_manager():
    """Lazy-load task manager to avoid import overhead when not used."""
    global _task_manager
    if _task_manager is None:
        try:
            from task_manager import TaskManager
            _task_manager = TaskManager()
        except ImportError:
            return None
    return _task_manager


def _create_round_task(
    tm, round_num: int, models: list[str], doc_type: str, session_id: Optional[str]
) -> Optional[str]:
    """Create a task for a debate round."""
    try:
        task = tm.create_task(
            subject=f"Debate round {round_num}",
            description=f"Send spec to {', '.join(models)}, receive critiques, synthesize",
            active_form=f"Running debate round {round_num}",
            owner="adv-spec:debate",
            metadata={
                "phase": "debate",
                "round": round_num,
                "models": models,
                "doc_type": doc_type,
                "session_id": session_id or "standalone",
            },
        )
        tm.start_task(task.id, owner="adv-spec:debate")
        return task.id
    except Exception as e:
        print(f"Warning: Failed to create round task: {e}", file=sys.stderr)
        return None


def _complete_round_task(tm, task_id: str, all_agreed: bool) -> None:
    """Mark a round task as completed."""
    try:
        tm.update_task(
            task_id,
            status="completed",
            metadata={"outcome": "consensus" if all_agreed else "continuing"},
        )
    except Exception as e:
        print(f"Warning: Failed to complete round task: {e}", file=sys.stderr)

# Import execution planner if available
try:
    from execution_planner import (
        # FR-1: Spec Intake
        SpecIntake,
        # FR-2: Scope Assessment
        ScopeAssessor,
        # FR-3: Task Plan Generation
        TaskPlanner,
        # FR-4: Test Strategy Configuration
        TestStrategyManager,
        # FR-5: Over-Decomposition Guards
        OverDecompositionGuard,
        # FR-6: Parallelization Guidance
        ParallelizationAdvisor,
        # Gauntlet concerns
        GauntletConcernParser,
        load_concerns_for_spec,
    )
    EXECUTION_PLANNER_AVAILABLE = True
except ImportError:
    EXECUTION_PLANNER_AVAILABLE = False


def send_telegram_notification(
    models: list[str], round_num: int, results: list[ModelResponse], poll_timeout: int
) -> Optional[str]:
    """Send Telegram notification with all model responses and poll for feedback.

    Args:
        models: List of model identifiers used.
        round_num: Current round number.
        results: List of model responses.
        poll_timeout: Seconds to wait for user reply.

    Returns:
        User feedback text if received, None otherwise.
    """
    try:
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))
        import telegram_bot

        token, chat_id = telegram_bot.get_config()
        if not token or not chat_id:
            print(
                "Warning: Telegram not configured. Skipping notification.",
                file=sys.stderr,
            )
            return None

        summaries = []
        all_agreed = True
        for r in results:
            if r.error:
                summaries.append(f"`{r.model}`: ERROR - {r.error[:100]}")
                all_agreed = False
            elif r.agreed:
                summaries.append(f"`{r.model}`: AGREE")
            else:
                all_agreed = False
                summary = get_critique_summary(r.response, 200)
                summaries.append(f"`{r.model}`: {summary}")

        status = "ALL AGREE" if all_agreed else "Critiques received"
        notification = f"""*Round {round_num} complete*

Status: {status}
Models: {len(results)}
Cost: ${cost_tracker.total_cost:.4f}

"""
        notification += "\n\n".join(summaries)

        last_update = telegram_bot.get_last_update_id(token)

        full_notification = (
            notification
            + f"\n\n_Reply within {poll_timeout}s to add feedback, or wait to continue._"
        )
        if not telegram_bot.send_long_message(token, chat_id, full_notification):
            print("Warning: Failed to send Telegram notification.", file=sys.stderr)
            return None

        feedback = telegram_bot.poll_for_reply(
            token, chat_id, poll_timeout, last_update
        )
        return feedback

    except ImportError:
        print(
            "Warning: telegram_bot.py not found. Skipping notification.",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"Warning: Telegram error: {e}", file=sys.stderr)
        return None


def send_final_spec_to_telegram(
    spec: str, rounds: int, models: list[str], doc_type: str, depth: Optional[str] = None
) -> bool:
    """Send the final converged spec to Telegram.

    Args:
        spec: The final spec content.
        rounds: Number of rounds completed.
        models: List of model identifiers used.
        doc_type: Document type (prd or tech).

    Returns:
        True on success, False on failure.
    """
    try:
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))
        import telegram_bot

        token, chat_id = telegram_bot.get_config()
        if not token or not chat_id:
            print(
                "Warning: Telegram not configured. Skipping final spec notification.",
                file=sys.stderr,
            )
            return False

        doc_type_name = get_doc_type_name(doc_type, depth)
        models_str = ", ".join(f"`{m}`" for m in models)
        header = f"""*Debate complete!*

Document: {doc_type_name}
Rounds: {rounds}
Models: Claude vs {models_str}
Total cost: ${cost_tracker.total_cost:.4f}

Final document:
---"""

        if not telegram_bot.send_message(token, chat_id, header):
            return False

        return telegram_bot.send_long_message(token, chat_id, spec)

    except Exception as e:
        print(f"Warning: Failed to send final spec to Telegram: {e}", file=sys.stderr)
        return False


def add_core_arguments(parser: argparse.ArgumentParser) -> None:
    """Add core critique arguments to parser."""
    parser.add_argument(
        "--models",
        "-m",
        default=None,
        help="Comma-separated list of models (e.g., codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview)",
    )
    parser.add_argument(
        "--doc-type",
        "-d",
        choices=["spec", "debug"],
        default="spec",
        help="Document type: spec or debug (default: spec)",
    )
    parser.add_argument(
        "--depth",
        choices=["product", "technical", "full"],
        default="technical",
        help="Spec depth: product, technical, or full (default: technical). Only used with --doc-type spec.",
    )
    parser.add_argument(
        "--round", "-r", type=int, default=1, help="Current round number"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Total rounds completed (used with send-final)",
    )


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add output formatting arguments to parser."""
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--show-cost", action="store_true", help="Show cost summary after critique"
    )


def add_telegram_arguments(parser: argparse.ArgumentParser) -> None:
    """Add Telegram notification arguments to parser."""
    parser.add_argument(
        "--telegram",
        "-t",
        action="store_true",
        help="Send Telegram notifications and poll for feedback",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=60,
        help="Seconds to wait for Telegram reply (default: 60)",
    )


def add_critique_modifiers(parser: argparse.ArgumentParser) -> None:
    """Add critique modification arguments to parser."""
    parser.add_argument(
        "--press",
        "-p",
        action="store_true",
        help="Press models to confirm they read the full document (anti-laziness check)",
    )
    parser.add_argument(
        "--focus",
        "-f",
        help="Focus area for critique (security, scalability, performance, ux, reliability, cost)",
    )
    parser.add_argument(
        "--persona",
        help="Persona for critique (security-engineer, oncall-engineer, junior-developer, etc.)",
    )
    parser.add_argument(
        "--context",
        "-c",
        action="append",
        default=[],
        help="Additional context file(s) to include (can be used multiple times)",
    )
    parser.add_argument(
        "--preserve-intent",
        action="store_true",
        help="Require explicit justification for any removal or substantial modification",
    )


def add_session_arguments(parser: argparse.ArgumentParser) -> None:
    """Add session management arguments to parser."""
    parser.add_argument(
        "--session",
        "-s",
        help="Session ID for state persistence (enables checkpointing and resume)",
    )
    parser.add_argument("--resume", help="Resume a previous session by ID")


def add_profile_arguments(parser: argparse.ArgumentParser) -> None:
    """Add profile management arguments to parser."""
    parser.add_argument("--profile", help="Load settings from a saved profile")


def add_diff_arguments(parser: argparse.ArgumentParser) -> None:
    """Add diff command arguments to parser."""
    parser.add_argument("--previous", help="Previous spec file (for diff action)")
    parser.add_argument("--current", help="Current spec file (for diff action)")


def add_codex_arguments(parser: argparse.ArgumentParser) -> None:
    """Add Codex CLI arguments to parser."""
    parser.add_argument(
        "--codex-reasoning",
        default=DEFAULT_CODEX_REASONING,
        choices=["low", "medium", "high", "xhigh"],
        help=f"Reasoning effort for Codex CLI models (default: {DEFAULT_CODEX_REASONING})",
    )
    parser.add_argument(
        "--codex-search",
        action="store_true",
        help="Enable web search for Codex CLI models",
    )


def add_bedrock_arguments(parser: argparse.ArgumentParser) -> None:
    """Add Bedrock arguments to parser."""
    parser.add_argument("--region", help="AWS region for Bedrock (e.g., us-east-1)")
    parser.add_argument(
        "bedrock_arg",
        nargs="?",
        help="Additional argument for bedrock subcommands (model name or alias target)",
    )


def add_misc_arguments(parser: argparse.ArgumentParser) -> None:
    """Add miscellaneous arguments to parser."""
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for model API/CLI calls (default: 600 = 10 minutes)",
    )
    parser.add_argument(
        "--track-tasks",
        action="store_true",
        help="Enable MCP Tasks integration: create/update tasks in .claude/tasks.json",
    )


def add_gauntlet_arguments(parser: argparse.ArgumentParser) -> None:
    """Add adversarial gauntlet arguments to parser."""
    parser.add_argument(
        "--gauntlet",
        "-g",
        action="store_true",
        help="Run adversarial gauntlet before/during debate",
    )
    parser.add_argument(
        "--gauntlet-adversaries",
        default="all",
        help="Comma-separated adversaries or 'all' (paranoid_security,burned_oncall,lazy_developer,pedantic_nitpicker,asshole_loner)",
    )
    parser.add_argument(
        "--gauntlet-model",
        help="Model for adversary attacks (default: auto-select free model)",
    )
    parser.add_argument(
        "--gauntlet-frontier",
        help="Model for evaluation (default: auto-select frontier model)",
    )
    parser.add_argument(
        "--no-rebuttals",
        action="store_true",
        help="Skip adversary rebuttal phase in gauntlet",
    )
    parser.add_argument(
        "--final-boss",
        action="store_true",
        help="Run Phase 5 Final Boss UX review (uses Opus 4.5, expensive but thorough)",
    )


def add_execution_plan_arguments(parser: argparse.ArgumentParser) -> None:
    """Add execution plan generation arguments to parser."""
    parser.add_argument(
        "--spec-file",
        help="Path to spec file (alternative to stdin)",
    )
    parser.add_argument(
        "--concerns-file",
        help="Path to gauntlet concerns JSON (auto-detected if not specified)",
    )
    parser.add_argument(
        "--plan-format",
        choices=["json", "markdown", "summary"],
        default="json",
        help="Output format for execution plan (default: json)",
    )
    parser.add_argument(
        "--plan-output",
        help="Output path for execution plan (default: stdout)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Adversarial spec debate with multiple LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex
  echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --focus security
  echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --persona "security engineer"
  echo "spec" | python3 debate.py critique --models codex/gpt-5.2-codex --context ./api.md
  echo "spec" | python3 debate.py critique --profile my-security-profile
  python3 debate.py diff --previous old.md --current new.md
  echo "spec" | python3 debate.py export-tasks --doc-type spec --depth product
  python3 debate.py providers
  python3 debate.py focus-areas
  python3 debate.py personas
  python3 debate.py profiles
  python3 debate.py save-profile myprofile --models codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview --focus security

Gauntlet commands (adversarial attack on specs):
  echo "spec" | python3 debate.py gauntlet                   # Run gauntlet with all adversaries
  echo "spec" | python3 debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall
  python3 debate.py gauntlet-adversaries                     # List available adversaries

Bedrock commands:
  python3 debate.py bedrock status                           # Show Bedrock config
  python3 debate.py bedrock enable --region us-east-1        # Enable Bedrock mode
  python3 debate.py bedrock disable                          # Disable Bedrock mode
  python3 debate.py bedrock add-model claude-3-sonnet        # Add model to available list
  python3 debate.py bedrock remove-model claude-3-haiku      # Remove model from list
  python3 debate.py bedrock alias mymodel anthropic.claude-3-sonnet-20240229-v1:0  # Add custom alias

Execution plan commands (generate implementation plans from specs):
  python3 debate.py execution-plan --spec-file spec.md                              # Generate plan from file
  echo "spec" | python3 debate.py execution-plan                                    # Generate plan from stdin
  python3 debate.py execution-plan --spec-file spec.md --concerns-file concerns.json # With gauntlet concerns
  python3 debate.py execution-plan --spec-file spec.md --plan-format markdown       # As markdown
  python3 debate.py execution-plan --spec-file spec.md --plan-format summary        # Brief summary

Document types:
  spec  - Specification (use --depth product, technical, or full)
  debug - Debug Investigation (evidence-based diagnosis, proportional fixes)
        """,
    )

    # Positional arguments
    parser.add_argument(
        "action",
        choices=[
            "critique",
            "gauntlet",
            "gauntlet-adversaries",
            "adversary-stats",
            "medal-leaderboard",
            "adversary-versions",
            "providers",
            "send-final",
            "diff",
            "export-tasks",
            "execution-plan",
            "focus-areas",
            "personas",
            "profiles",
            "save-profile",
            "sessions",
            "bedrock",
        ],
        help="Action to perform",
    )
    parser.add_argument(
        "profile_name",
        nargs="?",
        help="Profile name (for save-profile action) or bedrock subcommand",
    )

    # Add argument groups
    add_core_arguments(parser)
    add_output_arguments(parser)
    add_telegram_arguments(parser)
    add_critique_modifiers(parser)
    add_session_arguments(parser)
    add_profile_arguments(parser)
    add_diff_arguments(parser)
    add_codex_arguments(parser)
    add_bedrock_arguments(parser)
    add_gauntlet_arguments(parser)
    add_execution_plan_arguments(parser)
    add_misc_arguments(parser)

    return parser


def handle_info_command(args: argparse.Namespace) -> bool:
    """Handle info commands (providers, focus-areas, personas, profiles, sessions).

    Args:
        args: Parsed command-line arguments.

    Returns:
        True if command was handled, False otherwise.
    """
    if args.action == "providers":
        list_providers()
        return True

    if args.action == "focus-areas":
        list_focus_areas()
        return True

    if args.action == "personas":
        list_personas()
        return True

    if args.action == "profiles":
        list_profiles()
        return True

    if args.action == "sessions":
        sessions = SessionState.list_sessions()
        print("Saved Sessions:\n")
        if not sessions:
            print("  No sessions found.")
            print(f"\n  Sessions are stored in: {SESSIONS_DIR}")
            print("\n  Start a session with: --session <name>")
        else:
            for s in sessions:
                print(f"  {s['id']}")
                print(f"    round: {s['round']}, type: {s['doc_type']}")
                print(
                    f"    updated: {s['updated_at'][:19] if s['updated_at'] else 'unknown'}"
                )
                print()
        return True

    if args.action == "gauntlet-adversaries":
        print("Available Gauntlet Adversaries:\n")
        for name, desc in ADVERSARIES.items():
            first_line = desc.strip().split("\n")[0][:60]
            print(f"  {name:20} {first_line}...")
        print()
        print("Use with: --gauntlet-adversaries paranoid_security,burned_oncall")
        print("Or use all: --gauntlet-adversaries all")
        return True

    if args.action == "adversary-stats":
        print(get_adversary_leaderboard())
        return True

    if args.action == "medal-leaderboard":
        print(get_medal_leaderboard())
        return True

    if args.action == "adversary-versions":
        from adversaries import print_version_manifest
        print_version_manifest()
        return True

    return False


def handle_utility_command(args: argparse.Namespace) -> bool:
    """Handle utility commands (bedrock, save-profile, diff).

    Args:
        args: Parsed command-line arguments.

    Returns:
        True if command was handled, False otherwise.
    """
    if args.action == "bedrock":
        subcommand = args.profile_name or "status"
        handle_bedrock_command(subcommand, args.bedrock_arg, args.region)
        return True

    if args.action == "save-profile":
        if not args.profile_name:
            print("Error: Profile name required", file=sys.stderr)
            sys.exit(1)
        config = {
            "models": args.models,
            "doc_type": args.doc_type,
            "focus": args.focus,
            "persona": args.persona,
            "context": args.context,
            "preserve_intent": args.preserve_intent,
        }
        save_profile(args.profile_name, config)
        return True

    if args.action == "diff":
        if not args.previous or not args.current:
            print("Error: --previous and --current required for diff", file=sys.stderr)
            sys.exit(1)
        try:
            prev_content = Path(args.previous).read_text()
            curr_content = Path(args.current).read_text()
            diff = generate_diff(prev_content, curr_content)
            if diff:
                print(diff)
            else:
                print("No differences found.")
        except OSError as e:
            print(f"Error reading files: {e}", file=sys.stderr)
            sys.exit(1)
        return True

    return False


def handle_execution_plan(args: argparse.Namespace) -> bool:
    """Handle execution-plan command.

    Runs the full execution planning pipeline:
    1. FR-1: Spec Intake - Parse the specification
    2. FR-2: Scope Assessment - Recommend single-agent vs multi-agent
    3. FR-3: Task Plan Generation - Create tasks with concerns linked
    4. FR-4: Test Strategy Configuration - Assign test strategies
    5. FR-5: Over-Decomposition Guards - Warn if plan is too granular
    6. FR-6: Parallelization Guidance - Identify workstreams

    Args:
        args: Parsed command-line arguments.

    Returns:
        True if command was handled, False otherwise.
    """
    if args.action != "execution-plan":
        return False

    if not EXECUTION_PLANNER_AVAILABLE:
        print(
            "Error: execution_planner module not available.",
            file=sys.stderr,
        )
        print("Install with: pip install -e .", file=sys.stderr)
        sys.exit(1)

    # Get spec content from stdin or file
    spec_path = None
    if args.spec_file:
        spec_path = Path(args.spec_file)
        if not spec_path.exists():
            print(f"Error: Spec file not found: {spec_path}", file=sys.stderr)
            sys.exit(1)
        spec_content = spec_path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        spec_content = sys.stdin.read()
    else:
        print("Error: Provide spec via stdin or --spec-file", file=sys.stderr)
        sys.exit(1)

    print("=" * 60, file=sys.stderr)
    print("EXECUTION PLANNING PIPELINE", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # =========================================================================
    # FR-1: Spec Intake
    # =========================================================================
    print("\n[1/6] Spec Intake...", file=sys.stderr)
    try:
        doc = SpecIntake.parse(spec_content)
        if spec_path:
            doc.source_path = str(spec_path)
    except Exception as e:
        print(f"Error parsing spec: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Document type: {doc.doc_type.value}", file=sys.stderr)
    print(f"  Title: {doc.title}", file=sys.stderr)
    if doc.is_tech_spec():
        print(f"  Data models: {len(doc.data_models)}", file=sys.stderr)
        print(f"  API endpoints: {len(doc.api_endpoints)}", file=sys.stderr)
        print(f"  Scheduled functions: {len(doc.scheduled_functions)}", file=sys.stderr)
    else:
        print(f"  Functional requirements: {len(doc.functional_requirements)}", file=sys.stderr)
        print(f"  User stories: {len(doc.user_stories)}", file=sys.stderr)

    # Load gauntlet concerns if available
    gauntlet_report = None
    if args.concerns_file:
        concerns_path = Path(args.concerns_file)
        if concerns_path.exists():
            try:
                gauntlet_report = GauntletConcernParser.parse_file(concerns_path)
                GauntletConcernParser.link_to_spec(gauntlet_report, doc)
                print(f"  Gauntlet concerns: {len(gauntlet_report.concerns)}", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: Could not load concerns: {e}", file=sys.stderr)
    elif spec_path:
        gauntlet_report = load_concerns_for_spec(spec_path)
        if gauntlet_report:
            GauntletConcernParser.link_to_spec(gauntlet_report, doc)
            print(f"  Gauntlet concerns: {len(gauntlet_report.concerns)} (auto-loaded)", file=sys.stderr)

    # =========================================================================
    # FR-2: Scope Assessment
    # =========================================================================
    print("\n[2/6] Scope Assessment...", file=sys.stderr)
    scope_assessment = ScopeAssessor.assess(doc)
    print(f"  Recommendation: {scope_assessment.recommendation.value}", file=sys.stderr)
    print(f"  Confidence: {scope_assessment.confidence.value}", file=sys.stderr)
    print(f"  Effort estimate: {scope_assessment.effort_estimate}", file=sys.stderr)
    if scope_assessment.fast_path_eligible:
        print("  Fast-path eligible: Yes", file=sys.stderr)

    # =========================================================================
    # FR-3: Task Plan Generation
    # =========================================================================
    print("\n[3/6] Task Plan Generation...", file=sys.stderr)
    if doc.is_tech_spec():
        plan = TaskPlanner.generate_from_tech_spec(doc, gauntlet_report)
    else:
        plan = TaskPlanner.generate(doc)
    print(f"  Generated {len(plan.tasks)} tasks", file=sys.stderr)

    # =========================================================================
    # FR-4: Test Strategy Configuration
    # =========================================================================
    print("\n[4/6] Test Strategy Configuration...", file=sys.stderr)
    strategy_plan = TestStrategyManager.assign_strategies(plan)
    test_first_count = len([a for a in strategy_plan.assignments.values() if a.strategy.value == "test-first"])
    test_after_count = len([a for a in strategy_plan.assignments.values() if a.strategy.value == "test-after"])
    print(f"  Test-first: {test_first_count} tasks", file=sys.stderr)
    print(f"  Test-after: {test_after_count} tasks", file=sys.stderr)

    # =========================================================================
    # FR-5: Over-Decomposition Guards
    # =========================================================================
    print("\n[5/6] Over-Decomposition Check...", file=sys.stderr)
    guard = OverDecompositionGuard()
    guard_result = guard.check(plan, doc)
    if guard_result.exceeds_threshold:
        print("  WARNING: Plan may be over-decomposed!", file=sys.stderr)
        print(f"  Tasks: {guard_result.task_count}, Threshold: {guard_result.threshold}", file=sys.stderr)
        if guard_result.suggestions:
            print(f"  Consolidation suggestions: {len(guard_result.suggestions)}", file=sys.stderr)
    else:
        print(f"  OK: {guard_result.task_count} tasks (threshold: {guard_result.threshold})", file=sys.stderr)

    # =========================================================================
    # FR-6: Parallelization Guidance
    # =========================================================================
    print("\n[6/6] Parallelization Analysis...", file=sys.stderr)
    advisor = ParallelizationAdvisor()
    parallel_plan = advisor.analyze(plan)
    print(f"  Workstreams: {len(parallel_plan.streams)}", file=sys.stderr)
    print(f"  Merge points: {len(parallel_plan.merge_sequence)}", file=sys.stderr)
    print(f"  Branch pattern: {parallel_plan.branch_pattern.value}", file=sys.stderr)

    # =========================================================================
    # Output
    # =========================================================================
    print("\n" + "=" * 60, file=sys.stderr)

    # Format output
    output_format = args.plan_format or "json"
    if output_format == "json":
        output = _format_full_plan_json(
            plan, doc, gauntlet_report, scope_assessment,
            strategy_plan, guard_result, parallel_plan
        )
    elif output_format == "markdown":
        output = _format_full_plan_markdown(
            plan, doc, gauntlet_report, scope_assessment,
            strategy_plan, guard_result, parallel_plan
        )
    else:  # summary
        output = _format_full_plan_summary(
            plan, doc, scope_assessment, guard_result, parallel_plan
        )

    # Write output
    if args.plan_output:
        Path(args.plan_output).write_text(output, encoding="utf-8")
        print(f"Wrote execution plan to: {args.plan_output}", file=sys.stderr)
    else:
        print(output)

    # Export to MCP Tasks if enabled
    if getattr(args, 'track_tasks', False):
        tm = get_task_manager()
        if tm:
            try:
                session_id = getattr(args, 'session', None)
                id_map = plan.export_to_mcp_tasks(tm, session_id=session_id)
                print(
                    f"Created {len(id_map)} MCP Tasks in .claude/tasks.json",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"Warning: Failed to export to MCP Tasks: {e}", file=sys.stderr)

    # Print final summary
    high_risk = len([t for t in plan.tasks if t.risk_level == "high"])
    medium_risk = len([t for t in plan.tasks if t.risk_level == "medium"])
    with_concerns = len([t for t in plan.tasks if t.concerns])
    print(
        f"\nPipeline complete: {len(plan.tasks)} tasks "
        f"({high_risk} high risk, {medium_risk} medium risk, {with_concerns} with concerns)",
        file=sys.stderr,
    )

    return True


def _format_full_plan_json(plan, doc, report, scope, strategy, guard, parallel) -> str:
    """Format full pipeline output as JSON."""
    import json as json_module

    output = {
        "spec": {
            "title": doc.title,
            "doc_type": doc.doc_type.value,
            "source_path": doc.source_path,
        },
        "scope_assessment": {
            "recommendation": scope.recommendation.value,
            "confidence": scope.confidence.value,
            "explanation": scope.explanation,
            "estimated_effort": scope.effort_estimate,
            "fast_path_eligible": scope.fast_path_eligible,
        },
        "task_plan": json_module.loads(plan.to_json()),
        "test_strategy": {
            "assignments": {
                task_id: {
                    "strategy": a.strategy.value,
                    "reason": a.reason.value,
                    "confidence": a.confidence,
                }
                for task_id, a in strategy.assignments.items()
            },
        },
        "over_decomposition": {
            "exceeds_threshold": guard.exceeds_threshold,
            "task_count": guard.task_count,
            "threshold": guard.threshold,
            "requires_confirmation": guard.requires_confirmation,
            "warnings": guard.warnings,
            "suggestions": [
                {"task_ids": s.task_ids, "reason": s.reason}
                for s in guard.suggestions
            ] if guard.suggestions else [],
        },
        "parallelization": {
            "branch_pattern": parallel.branch_pattern.value,
            "streams": [
                {
                    "stream_id": w.stream_id,
                    "task_ids": w.task_ids,
                    "branch_name": w.branch_name,
                    "depends_on_streams": w.depends_on_streams,
                }
                for w in parallel.streams
            ],
            "merge_sequence": [
                {
                    "source_stream": m.source_stream,
                    "target_stream": m.target_stream,
                    "merge_order": m.merge_order,
                    "conflict_risk": m.expected_conflict_risk,
                }
                for m in parallel.merge_sequence
            ],
            "execution_order": parallel.execution_order,
        },
        "concerns_summary": {
            "total": len(report.concerns) if report else 0,
            "high_severity": len(report.by_severity.get("high", [])) if report else 0,
            "medium_severity": len(report.by_severity.get("medium", [])) if report else 0,
        } if report else None,
    }

    return json_module.dumps(output, indent=2, default=str)


def _format_full_plan_markdown(plan, doc, report, scope, strategy, guard, parallel) -> str:
    """Format full pipeline output as markdown."""
    lines = [
        f"# Execution Plan: {doc.title}",
        "",
        f"**Generated from:** {doc.source_path or 'stdin'}",
        f"**Document type:** {doc.doc_type.value}",
        "",
    ]

    # Scope Assessment
    lines.extend([
        "## Scope Assessment",
        "",
        f"**Recommendation:** {scope.recommendation.value}",
        f"**Confidence:** {scope.confidence.value}",
        f"**Estimated effort:** {scope.effort_estimate}",
    ])
    if scope.fast_path_eligible:
        lines.append("**Fast-path eligible:** Yes (can skip decomposition)")
    lines.extend([
        "",
        "**Analysis:**",
        scope.explanation[:500] if len(scope.explanation) > 500 else scope.explanation,
        "",
    ])

    # Over-decomposition warning
    if guard.exceeds_threshold:
        lines.extend([
            "## Over-Decomposition Warning",
            "",
            f"**Task count ({guard.task_count}) exceeds threshold ({guard.threshold})**",
            "",
        ])
        if guard.warnings:
            for w in guard.warnings[:3]:
                lines.append(f"- {w}")
        if guard.suggestions:
            lines.append("")
            lines.append("Consider consolidating:")
            for s in guard.suggestions[:3]:
                lines.append(f"- {s.reason}")
        lines.append("")

    # Parallelization
    lines.extend([
        "## Parallelization",
        "",
        f"**Pattern:** {parallel.branch_pattern.value}",
        f"**Workstreams:** {len(parallel.streams)}",
        f"**Merge points:** {len(parallel.merge_sequence)}",
        "",
    ])

    # Concerns summary
    if report:
        high_sev = len(report.by_severity.get("high", []))
        med_sev = len(report.by_severity.get("medium", []))
        lines.extend([
            "## Gauntlet Concerns",
            "",
            f"**Total:** {len(report.concerns)}",
            f"**High severity:** {high_sev}",
            f"**Medium severity:** {med_sev}",
            "",
        ])

    # Summary stats
    high_risk = len([t for t in plan.tasks if t.risk_level == "high"])
    medium_risk = len([t for t in plan.tasks if t.risk_level == "medium"])
    with_concerns = len([t for t in plan.tasks if t.concerns])
    test_first = len([a for a in strategy.assignments.values() if a.strategy.value == "test-first"])

    lines.extend([
        "## Task Summary",
        "",
        f"- **Total tasks:** {len(plan.tasks)}",
        f"- **High risk:** {high_risk}",
        f"- **Medium risk:** {medium_risk}",
        f"- **With concerns:** {with_concerns}",
        f"- **Test-first:** {test_first}",
        "",
        "## Tasks",
        "",
    ])

    # Tasks
    for i, task in enumerate(plan.tasks, 1):
        # Find strategy assignment
        task_strategy = (
            strategy.assignments[task.id].strategy.value
            if task.id in strategy.assignments
            else task.validation_strategy.value
        )

        lines.extend([
            f"### {i}. {task.title}",
            "",
            f"**Effort:** {task.effort_estimate} | **Risk:** {task.risk_level} | **Validation:** {task_strategy}",
            "",
        ])

        if task.spec_refs:
            refs = ", ".join(f"Section {r.section_number}" for r in task.spec_refs)
            lines.append(f"**Spec Reference:** {refs}")
            lines.append("")

        # Truncated description
        desc = task.description
        if len(desc) > 500:
            desc = desc[:500] + "..."
        lines.append(desc)
        lines.append("")

        lines.append("**Acceptance Criteria:**")
        for ac in task.acceptance_criteria.split(" | ")[:5]:
            lines.append(f"- {ac}")
        lines.append("")

        if task.concerns:
            lines.append(f"**Related Concerns ({len(task.concerns)}):**")
            for c in task.concerns[:3]:
                lines.append(f"- [{c.severity}] {c.title} ({c.adversary})")
            if len(task.concerns) > 3:
                lines.append(f"- ... and {len(task.concerns) - 3} more")
            lines.append("")

        if task.test_cases:
            lines.append("**Test Cases:**")
            for tc in task.test_cases[:3]:
                lines.append(f"- {tc[:150]}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_full_plan_summary(plan, doc, scope, guard, parallel) -> str:
    """Format full pipeline output as brief summary."""
    lines = [
        "=" * 60,
        f"EXECUTION PLAN: {doc.title}",
        "=" * 60,
        "",
        "SCOPE ASSESSMENT",
        f"  Recommendation: {scope.recommendation.value}",
        f"  Confidence: {scope.confidence.value}",
        f"  Effort: {scope.effort_estimate}",
        "",
    ]

    if guard.exceeds_threshold:
        lines.extend([
            "OVER-DECOMPOSITION WARNING",
            f"  Tasks: {guard.task_count} (threshold: {guard.threshold})",
            "",
        ])

    lines.extend([
        "PARALLELIZATION",
        f"  Pattern: {parallel.branch_pattern.value}",
        f"  Workstreams: {len(parallel.streams)}",
        "",
        "TASK BREAKDOWN",
        f"  Total: {len(plan.tasks)}",
    ])

    # By effort
    effort_counts: dict[str, int] = {}
    for task in plan.tasks:
        effort_counts[task.effort_estimate] = effort_counts.get(task.effort_estimate, 0) + 1
    effort_str = ", ".join(f"{k}: {v}" for k, v in sorted(effort_counts.items()))
    lines.append(f"  By effort: {effort_str}")

    # By risk
    risk_counts: dict[str, int] = {}
    for task in plan.tasks:
        risk_counts[task.risk_level] = risk_counts.get(task.risk_level, 0) + 1
    risk_str = ", ".join(f"{k}: {v}" for k, v in risk_counts.items())
    lines.append(f"  By risk: {risk_str}")

    lines.extend([
        "",
        "TASKS",
    ])

    for i, task in enumerate(plan.tasks, 1):
        risk_marker = "[HIGH]" if task.risk_level == "high" else "[MED]" if task.risk_level == "medium" else "[LOW]"
        concern_marker = f" ({len(task.concerns)}c)" if task.concerns else ""
        lines.append(f"  {i:2}. [{task.effort_estimate}] {risk_marker} {task.title}{concern_marker}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def _format_plan_as_markdown(plan, doc, report) -> str:
    """Format plan as markdown document."""
    lines = [
        f"# Execution Plan: {doc.title}",
        "",
        f"Generated from: {doc.source_path or 'stdin'}",
        f"Document type: {doc.doc_type.value}",
        f"Total tasks: {len(plan.tasks)}",
        "",
    ]

    if report:
        lines.extend([
            f"Concerns linked: {len(report.concerns)}",
            "",
        ])

    # Summary stats
    high_risk = len([t for t in plan.tasks if t.risk_level == "high"])
    medium_risk = len([t for t in plan.tasks if t.risk_level == "medium"])
    with_concerns = len([t for t in plan.tasks if t.concerns])

    lines.extend([
        "## Summary",
        "",
        f"- High risk tasks: {high_risk}",
        f"- Medium risk tasks: {medium_risk}",
        f"- Tasks with linked concerns: {with_concerns}",
        "",
        "## Tasks",
        "",
    ])

    for i, task in enumerate(plan.tasks, 1):
        lines.extend([
            f"### {i}. {task.title}",
            "",
            f"**Effort:** {task.effort_estimate} | **Risk:** {task.risk_level} | **Validation:** {task.validation_strategy.value}",
            "",
        ])

        if task.spec_refs:
            refs = ", ".join(f"Section {r.section_number}" for r in task.spec_refs)
            lines.append(f"**Spec Reference:** {refs}")
            lines.append("")

        lines.append("**Description:**")
        lines.append("")
        # Truncate long descriptions
        desc = task.description
        if len(desc) > 500:
            desc = desc[:500] + "..."
        lines.append(desc)
        lines.append("")

        lines.append("**Acceptance Criteria:**")
        lines.append("")
        for ac in task.acceptance_criteria.split(" | "):
            lines.append(f"- {ac}")
        lines.append("")

        if task.concerns:
            lines.append(f"**Related Concerns ({len(task.concerns)}):**")
            lines.append("")
            for concern in task.concerns[:5]:
                lines.append(f"- [{concern.severity}] {concern.title} ({concern.adversary})")
            if len(task.concerns) > 5:
                lines.append(f"- ... and {len(task.concerns) - 5} more")
            lines.append("")

        if task.test_cases:
            lines.append("**Test Cases:**")
            lines.append("")
            for tc in task.test_cases[:3]:
                lines.append(f"- {tc[:200]}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_plan_as_summary(plan) -> str:
    """Format plan as brief summary."""
    lines = [
        "Execution Plan Summary",
        "=====================",
        "",
        f"Total tasks: {len(plan.tasks)}",
        "",
        "By effort:",
    ]

    effort_counts: dict[str, int] = {}
    for task in plan.tasks:
        effort_counts[task.effort_estimate] = effort_counts.get(task.effort_estimate, 0) + 1
    for effort in ["XS", "S", "M", "L", "XL"]:
        if effort in effort_counts:
            lines.append(f"  {effort}: {effort_counts[effort]}")

    lines.extend([
        "",
        "By risk:",
    ])

    risk_counts: dict[str, int] = {}
    for task in plan.tasks:
        risk_counts[task.risk_level] = risk_counts.get(task.risk_level, 0) + 1
    for risk in ["high", "medium", "low"]:
        if risk in risk_counts:
            lines.append(f"  {risk}: {risk_counts[risk]}")

    lines.extend([
        "",
        "Tasks:",
    ])

    for i, task in enumerate(plan.tasks, 1):
        risk_marker = "[HIGH]" if task.risk_level == "high" else "[MED]" if task.risk_level == "medium" else "[LOW]"
        concern_marker = f" ({len(task.concerns)} concerns)" if task.concerns else ""
        lines.append(f"  {i}. [{task.effort_estimate}] {risk_marker} {task.title}{concern_marker}")

    return "\n".join(lines)


def apply_profile(args: argparse.Namespace) -> None:
    """Apply profile settings to args if --profile specified.

    Args:
        args: Parsed command-line arguments (modified in place).
    """
    if not args.profile:
        return

    profile = load_profile(args.profile)
    if "models" in profile and args.models is None:
        args.models = profile["models"]
    if "doc_type" in profile and args.doc_type == "spec":
        args.doc_type = profile["doc_type"]
    if "focus" in profile and not args.focus:
        args.focus = profile["focus"]
    if "persona" in profile and not args.persona:
        args.persona = profile["persona"]
    if "context" in profile and not args.context:
        args.context = profile["context"]
    if profile.get("preserve_intent") and not args.preserve_intent:
        args.preserve_intent = profile["preserve_intent"]


def parse_models(args: argparse.Namespace) -> list[str]:
    """Parse and validate models list from args.

    Args:
        args: Parsed command-line arguments.

    Returns:
        List of model identifiers.
    """
    # If no models specified, use default based on available API keys
    if args.models is None:
        default_model = get_default_model()
        if default_model is None:
            print(
                "Error: No API keys configured and no models specified.",
                file=sys.stderr,
            )
            print("\nAvailable providers:", file=sys.stderr)
            print(
                "  Codex CLI: Install codex CLI for codex/gpt-5.2-codex (FREE with ChatGPT subscription)", file=sys.stderr
            )
            print(
                "  Gemini CLI: Install gemini CLI for gemini-cli/gemini-3-pro-preview (FREE)", file=sys.stderr
            )
            print(
                "  OpenAI:    Set OPENAI_API_KEY for gpt-5.2, o3-mini", file=sys.stderr
            )
            print(
                "  Anthropic: Set ANTHROPIC_API_KEY for claude-opus-4-5, claude-sonnet-4-5",
                file=sys.stderr,
            )
            print(
                "  Google:    Set GEMINI_API_KEY for gemini/gemini-3-pro, gemini/gemini-3-flash",
                file=sys.stderr,
            )
            print("  xAI:       Set XAI_API_KEY for xai/grok-4", file=sys.stderr)
            print(
                "  Mistral:   Set MISTRAL_API_KEY for mistral/mistral-large-3",
                file=sys.stderr,
            )
            print(
                "  Groq:      Set GROQ_API_KEY for groq/llama-4-maverick",
                file=sys.stderr,
            )
            print(
                "  Deepseek:  Set DEEPSEEK_API_KEY for deepseek/deepseek-r1",
                file=sys.stderr,
            )
            print(
                "  Zhipu:     Set ZHIPUAI_API_KEY for zhipu/glm-4-plus",
                file=sys.stderr,
            )
            print("\nOr specify models explicitly: --models codex/gpt-5.2-codex", file=sys.stderr)
            print(
                "\nRun 'python3 debate.py providers' to see which keys are set.",
                file=sys.stderr,
            )
            sys.exit(2)
        args.models = default_model

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        print("Error: No models specified", file=sys.stderr)
        sys.exit(1)
    return models


def setup_bedrock(
    args: argparse.Namespace, models: list[str]
) -> tuple[list[str], bool, Optional[str]]:
    """Configure Bedrock mode and validate models.

    Args:
        args: Parsed command-line arguments.
        models: List of model identifiers.

    Returns:
        Tuple of (validated_models, bedrock_mode, bedrock_region).
    """
    bedrock_config = get_bedrock_config()
    bedrock_mode = bedrock_config.get("enabled", False)
    bedrock_region = bedrock_config.get("region")

    if not bedrock_mode or args.action != "critique":
        return models, bedrock_mode, bedrock_region

    available = bedrock_config.get("available_models", [])
    if not available:
        print(
            "Error: Bedrock mode is enabled but no models are configured.",
            file=sys.stderr,
        )
        print(
            "Add models with: python3 debate.py bedrock add-model claude-3-sonnet",
            file=sys.stderr,
        )
        print("Or disable Bedrock: python3 debate.py bedrock disable", file=sys.stderr)
        sys.exit(2)

    valid_models, invalid_models = validate_bedrock_models(models, bedrock_config)

    if invalid_models:
        print(
            "Error: The following models are not available in your Bedrock configuration:",
            file=sys.stderr,
        )
        for m in invalid_models:
            print(f"  - {m}", file=sys.stderr)
        print(f"\nAvailable models: {', '.join(available)}", file=sys.stderr)
        print(
            "Add models with: python3 debate.py bedrock add-model <model>",
            file=sys.stderr,
        )
        print("Or disable Bedrock: python3 debate.py bedrock disable", file=sys.stderr)
        sys.exit(2)

    print(
        f"Bedrock mode: routing through AWS Bedrock ({bedrock_region})",
        file=sys.stderr,
    )
    return valid_models, bedrock_mode, bedrock_region


def handle_send_final(args: argparse.Namespace, models: list[str]) -> None:
    """Handle send-final action.

    Args:
        args: Parsed command-line arguments.
        models: List of model identifiers.
    """
    spec = sys.stdin.read().strip()
    if not spec:
        print("Error: No spec provided via stdin", file=sys.stderr)
        sys.exit(1)
    if send_final_spec_to_telegram(spec, args.rounds, models, args.doc_type, getattr(args, "depth", None)):
        print("Final document sent to Telegram.")
    else:
        print("Failed to send final document to Telegram.", file=sys.stderr)
        sys.exit(1)


def handle_export_tasks(args: argparse.Namespace, models: list[str]) -> None:
    """Handle export-tasks action.

    Args:
        args: Parsed command-line arguments.
        models: List of model identifiers.
    """
    spec = sys.stdin.read().strip()
    if not spec:
        print("Error: No spec provided via stdin", file=sys.stderr)
        sys.exit(1)

    doc_type_name = get_doc_type_name(args.doc_type, getattr(args, "depth", None))
    prompt = EXPORT_TASKS_PROMPT.format(doc_type_name=doc_type_name, spec=spec)

    try:
        # Build completion kwargs
        completion_kwargs = {
            "model": models[0],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
        }

        # O-series models don't support custom temperature
        if not is_o_series_model(models[0]):
            completion_kwargs["temperature"] = 0.3

        response = completion(**completion_kwargs)
        content = response.choices[0].message.content
        tasks = extract_tasks(content)

        if args.json:
            print(json.dumps({"tasks": tasks}, indent=2))
        else:
            print(f"\n=== Extracted {len(tasks)} Tasks ===\n")
            for i, task in enumerate(tasks, 1):
                print(
                    f"{i}. [{task.get('type', 'task')}] [{task.get('priority', 'medium')}] {task.get('title', 'Untitled')}"
                )
                if task.get("description"):
                    print(f"   {task['description'][:100]}...")
                if task.get("acceptance_criteria"):
                    print(
                        f"   Acceptance criteria: {len(task['acceptance_criteria'])} items"
                    )
                print()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_gauntlet(args: argparse.Namespace) -> None:
    """Handle gauntlet action - run adversarial gauntlet on a spec.

    Args:
        args: Parsed command-line arguments.
    """
    spec = sys.stdin.read().strip()
    if not spec:
        print("Error: No spec provided via stdin", file=sys.stderr)
        sys.exit(1)

    # Parse adversaries
    adversaries = None
    if args.gauntlet_adversaries != "all":
        adversaries = [a.strip() for a in args.gauntlet_adversaries.split(",")]
        # Validate adversary names
        invalid = [a for a in adversaries if a not in ADVERSARIES]
        if invalid:
            print(f"Error: Unknown adversaries: {', '.join(invalid)}", file=sys.stderr)
            print(
                f"Available: {', '.join(ADVERSARIES.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        # Parse eval models (can be comma-separated for multi-model)
        eval_models = None
        if args.gauntlet_frontier:
            eval_models = [m.strip() for m in args.gauntlet_frontier.split(",")]

        result = run_gauntlet(
            spec=spec,
            adversaries=adversaries,
            adversary_model=args.gauntlet_model,
            eval_models=eval_models,
            allow_rebuttals=not args.no_rebuttals,
            run_final_boss=args.final_boss,
            timeout=args.timeout,
        )

        if args.json:
            output = {
                "concerns": [
                    {"adversary": c.adversary, "text": c.text}
                    for c in result.concerns
                ],
                "evaluations": [
                    {
                        "concern": {
                            "adversary": e.concern.adversary,
                            "text": e.concern.text,
                        },
                        "verdict": e.verdict,
                        "reasoning": e.reasoning,
                    }
                    for e in result.evaluations
                ],
                "final_concerns": [
                    {"adversary": c.adversary, "text": c.text}
                    for c in result.final_concerns
                ],
                "adversary_model": result.adversary_model,
                "eval_model": result.eval_model,
                "total_time": result.total_time,
                "total_cost": result.total_cost,
            }
            print(json.dumps(output, indent=2))
        else:
            print()
            print(format_gauntlet_report(result))

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def load_or_resume_session(
    args: argparse.Namespace, models: list[str]
) -> tuple[str, Optional[SessionState], list[str]]:
    """Load session from resume or stdin, optionally creating new session.

    Args:
        args: Parsed command-line arguments.
        models: List of model identifiers.

    Returns:
        Tuple of (spec, session_state, models).
    """
    session_state = None

    if args.resume:
        try:
            session_state = SessionState.load(args.resume)
            print(
                f"Resuming session '{args.resume}' at round {session_state.round}",
                file=sys.stderr,
            )
            spec = session_state.spec
            args.round = session_state.round
            args.doc_type = session_state.doc_type
            args.models = ",".join(session_state.models)
            if session_state.focus:
                args.focus = session_state.focus
            if session_state.persona:
                args.persona = session_state.persona
            if session_state.preserve_intent:
                args.preserve_intent = session_state.preserve_intent
            models = session_state.models
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
    else:
        spec = sys.stdin.read().strip()
        if not spec:
            print("Error: No spec provided via stdin", file=sys.stderr)
            sys.exit(1)

    if args.session and not session_state:
        session_state = SessionState(
            session_id=args.session,
            spec=spec,
            round=args.round,
            doc_type=args.doc_type,
            models=models,
            focus=args.focus,
            persona=args.persona,
            preserve_intent=args.preserve_intent,
            created_at=datetime.now().isoformat(),
        )
        session_state.save()
        print(f"Session '{args.session}' created", file=sys.stderr)

    return spec, session_state, models


def run_critique(
    args: argparse.Namespace,
    spec: str,
    models: list[str],
    session_state: Optional[SessionState],
    context: Optional[str],
    bedrock_mode: bool,
    bedrock_region: Optional[str],
) -> None:
    """Execute the critique workflow and output results.

    Args:
        args: Parsed command-line arguments.
        spec: The specification to critique.
        models: List of model identifiers.
        session_state: Optional session state for persistence.
        context: Optional context string.
        bedrock_mode: Whether Bedrock mode is enabled.
        bedrock_region: AWS region for Bedrock.
    """
    # Task tracking: create/update round task
    round_task_id = None
    if getattr(args, 'track_tasks', False):
        tm = get_task_manager()
        if tm:
            session_id = session_state.session_id if session_state else args.session
            round_task_id = _create_round_task(
                tm, args.round, models, args.doc_type, session_id
            )

    mode = "pressing for confirmation" if args.press else "critiquing"
    focus_info = f" (focus: {args.focus})" if args.focus else ""
    persona_info = f" (persona: {args.persona})" if args.persona else ""
    preserve_info = " (preserve-intent)" if args.preserve_intent else ""
    search_info = " (search)" if args.codex_search else ""
    print(
        f"Calling {len(models)} model(s) ({mode}){focus_info}{persona_info}{preserve_info}{search_info}: {', '.join(models)}...",
        file=sys.stderr,
    )

    results = call_models_parallel(
        models,
        spec,
        args.round,
        args.doc_type,
        args.press,
        args.focus,
        args.persona,
        context,
        args.preserve_intent,
        args.codex_reasoning,
        args.codex_search,
        args.timeout,
        bedrock_mode,
        bedrock_region,
        getattr(args, "depth", None),
    )

    errors = [r for r in results if r.error]
    for err_result in errors:
        print(
            f"Warning: {err_result.model} returned error: {err_result.error}",
            file=sys.stderr,
        )

    successful = [r for r in results if not r.error]
    all_agreed = all(r.agreed for r in successful) if successful else False

    session_id = session_state.session_id if session_state else args.session
    if session_id or args.session:
        save_checkpoint(spec, args.round, session_id)

    latest_spec = spec
    for r in successful:
        if r.spec:
            latest_spec = r.spec
            break

    if session_state:
        session_state.spec = latest_spec
        session_state.round = args.round + 1
        session_state.history.append(
            {
                "round": args.round,
                "all_agreed": all_agreed,
                "models": [
                    {"model": r.model, "agreed": r.agreed, "error": r.error}
                    for r in results
                ],
            }
        )
        session_state.save()

    user_feedback = None
    if args.telegram:
        user_feedback = send_telegram_notification(
            models, args.round, results, args.poll_timeout
        )
        if user_feedback:
            print(f"Received feedback: {user_feedback}", file=sys.stderr)

    # Task tracking: mark round complete
    if round_task_id and getattr(args, 'track_tasks', False):
        tm = get_task_manager()
        if tm:
            _complete_round_task(tm, round_task_id, all_agreed)

    output_results(args, results, models, all_agreed, user_feedback, session_state)


def output_results(
    args: argparse.Namespace,
    results: list[ModelResponse],
    models: list[str],
    all_agreed: bool,
    user_feedback: Optional[str],
    session_state: Optional[SessionState],
) -> None:
    """Output critique results in JSON or text format.

    Args:
        args: Parsed command-line arguments.
        results: List of model responses.
        models: List of model identifiers.
        all_agreed: Whether all models agreed.
        user_feedback: Optional user feedback from Telegram.
        session_state: Optional session state.
    """
    if args.json:
        output: dict[str, Any] = {
            "all_agreed": all_agreed,
            "round": args.round,
            "doc_type": args.doc_type,
            "models": models,
            "focus": args.focus,
            "persona": args.persona,
            "preserve_intent": args.preserve_intent,
            "session": session_state.session_id if session_state else args.session,
            "results": [
                {
                    "model": r.model,
                    "agreed": r.agreed,
                    "response": r.response,
                    "spec": r.spec,
                    "error": r.error,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost": r.cost,
                }
                for r in results
            ],
            "cost": {
                "total": cost_tracker.total_cost,
                "input_tokens": cost_tracker.total_input_tokens,
                "output_tokens": cost_tracker.total_output_tokens,
                "by_model": cost_tracker.by_model,
            },
        }
        if user_feedback:
            output["user_feedback"] = user_feedback
        print(json.dumps(output, indent=2))
    else:
        doc_type_name = get_doc_type_name(args.doc_type, getattr(args, "depth", None))
        print(f"\n=== Round {args.round} Results ({doc_type_name}) ===\n")

        for r in results:
            print(f"--- {r.model} ---")
            if r.error:
                print(f"ERROR: {r.error}")
            elif r.agreed:
                print("[AGREE]")
            else:
                print(r.response)
            print()

        if all_agreed:
            print("=== ALL MODELS AGREE ===")
        else:
            successful = [r for r in results if not r.error]
            agreed_models = [r.model for r in successful if r.agreed]
            disagreed_models = [r.model for r in successful if not r.agreed]
            if agreed_models:
                print(f"Agreed: {', '.join(agreed_models)}")
            if disagreed_models:
                print(f"Critiqued: {', '.join(disagreed_models)}")

        if user_feedback:
            print()
            print("=== User Feedback ===")
            print(user_feedback)

        if args.show_cost:
            print(cost_tracker.summary())


def validate_models_before_run(models: list[str], bedrock_mode: bool) -> None:
    """
    Validate that models have required credentials before running critique.

    Args:
        models: List of model identifiers.
        bedrock_mode: Whether Bedrock mode is enabled.
    """
    if bedrock_mode:
        # Bedrock validation is handled in setup_bedrock
        return

    valid, invalid = validate_model_credentials(models)

    if invalid:
        print("Error: The following models lack required API keys:", file=sys.stderr)
        for model in invalid:
            # Determine which key is needed
            if model.startswith("gpt-") or model.startswith("o1"):
                print(f"  - {model} (requires OPENAI_API_KEY)", file=sys.stderr)
            elif model.startswith("claude-"):
                print(f"  - {model} (requires ANTHROPIC_API_KEY)", file=sys.stderr)
            elif model.startswith("gemini/"):
                print(f"  - {model} (requires GEMINI_API_KEY)", file=sys.stderr)
            elif model.startswith("xai/"):
                print(f"  - {model} (requires XAI_API_KEY)", file=sys.stderr)
            elif model.startswith("mistral/"):
                print(f"  - {model} (requires MISTRAL_API_KEY)", file=sys.stderr)
            elif model.startswith("groq/"):
                print(f"  - {model} (requires GROQ_API_KEY)", file=sys.stderr)
            elif model.startswith("deepseek/"):
                print(f"  - {model} (requires DEEPSEEK_API_KEY)", file=sys.stderr)
            elif model.startswith("zhipu/"):
                print(f"  - {model} (requires ZHIPUAI_API_KEY)", file=sys.stderr)
            elif model.startswith("codex/"):
                print(
                    f"  - {model} (requires Codex CLI: npm install -g @openai/codex && codex login)",
                    file=sys.stderr,
                )
            else:
                print(f"  - {model} (unknown provider)", file=sys.stderr)

        print(
            "\nRun 'python3 debate.py providers' to see which API keys are configured.",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> None:
    """Entry point for the debate CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if handle_info_command(args):
        return

    if handle_utility_command(args):
        return

    if handle_execution_plan(args):
        return

    # Gauntlet action has its own model selection, handle before parse_models
    if args.action == "gauntlet":
        handle_gauntlet(args)
        return

    apply_profile(args)
    models = parse_models(args)
    context = load_context_files(args.context) if args.context else None
    models, bedrock_mode, bedrock_region = setup_bedrock(args, models)

    # Validate models have required credentials
    validate_models_before_run(models, bedrock_mode)

    if args.action == "send-final":
        handle_send_final(args, models)
        return

    if args.action == "export-tasks":
        handle_export_tasks(args, models)
        return

    spec, session_state, models = load_or_resume_session(args, models)
    run_critique(
        args, spec, models, session_state, context, bedrock_mode, bedrock_region
    )


if __name__ == "__main__":
    main()
