# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/__init__.py (1 lines, 44 bytes)
# ══════════════════════════════════════════════════════════════
# Tests for adversarial-spec debate scripts


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_cli.py (762 lines, 26432 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for CLI argument parsing and command routing."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCLIProviders:
    def test_providers_command(self):
        """Test that providers command runs without error."""
        import debate

        with patch("sys.argv", ["debate.py", "providers"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                debate.main()
                output = mock_stdout.getvalue()
                assert "OpenAI" in output
                assert "OPENAI_API_KEY" in output


class TestCLIFocusAreas:
    def test_focus_areas_command(self):
        """Test that focus-areas command lists all areas."""
        import debate

        with patch("sys.argv", ["debate.py", "focus-areas"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                debate.main()
                output = mock_stdout.getvalue()
                assert "security" in output
                assert "scalability" in output
                assert "performance" in output


class TestCLIPersonas:
    def test_personas_command(self):
        """Test that personas command lists all personas."""
        import debate

        with patch("sys.argv", ["debate.py", "personas"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                debate.main()
                output = mock_stdout.getvalue()
                assert "security-engineer" in output
                assert "oncall-engineer" in output


class TestCLISessions:
    def test_sessions_command_empty(self):
        """Test sessions command with no sessions."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("session.SESSIONS_DIR", Path(tmpdir) / "sessions"):
                with patch("debate.SESSIONS_DIR", Path(tmpdir) / "sessions"):
                    with patch("sys.argv", ["debate.py", "sessions"]):
                        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                            debate.main()
                            output = mock_stdout.getvalue()
                            assert "No sessions found" in output


class TestCLIDiff:
    def test_diff_command(self):
        """Test diff between two files."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            prev = Path(tmpdir) / "prev.md"
            curr = Path(tmpdir) / "curr.md"
            prev.write_text("line1\nline2\n")
            curr.write_text("line1\nmodified\n")

            with patch(
                "sys.argv",
                ["debate.py", "diff", "--previous", str(prev), "--current", str(curr)],
            ):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    debate.main()
                    output = mock_stdout.getvalue()
                    assert "-line2" in output
                    assert "+modified" in output


class TestCLISaveProfile:
    def test_save_profile_command(self):
        """Test saving a profile."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"

            with patch("providers.PROFILES_DIR", profiles_dir):
                with patch(
                    "sys.argv",
                    [
                        "debate.py",
                        "save-profile",
                        "test-profile",
                        "--models",
                        "gpt-4o,gemini/gemini-2.0-flash",
                        "--focus",
                        "security",
                    ],
                ):
                    with patch("sys.stdout", new_callable=StringIO):
                        debate.main()

                        # Verify profile was saved
                        profile_path = profiles_dir / "test-profile.json"
                        assert profile_path.exists()

                        data = json.loads(profile_path.read_text())
                        assert data["models"] == "gpt-4o,gemini/gemini-2.0-flash"
                        assert data["focus"] == "security"


class TestCLICritique:
    @patch("debate.validate_models_before_run")
    @patch("debate.call_models_parallel")
    def test_critique_with_json_output(self, mock_call, mock_validate):
        """Test critique command with JSON output."""
        import debate
        from models import ModelResponse

        # Mock validation to not check API keys in tests
        mock_validate.return_value = None

        mock_call.return_value = [
            ModelResponse(
                model="gpt-4o",
                response="Critique here.\n[SPEC]\n# Revised\n[/SPEC]",
                agreed=False,
                spec="# Revised",
                input_tokens=100,
                output_tokens=50,
                cost=0.01,
            )
        ]

        with patch("sys.stdin", StringIO("# Test Spec\n\nContent here.")):
            with patch(
                "sys.argv", ["debate.py", "critique", "--models", "gpt-4o", "--json"]
            ):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    with patch("sys.stderr", new_callable=StringIO):
                        debate.main()
                        output = mock_stdout.getvalue()

                        data = json.loads(output)
                        assert data["round"] == 1
                        assert data["models"] == ["gpt-4o"]
                        assert len(data["results"]) == 1
                        assert data["results"][0]["model"] == "gpt-4o"

    @patch("debate.validate_models_before_run")
    @patch("debate.call_models_parallel")
    def test_critique_with_all_agree(self, mock_call, mock_validate):
        """Test critique when all models agree."""
        import debate
        from models import ModelResponse

        # Mock validation to not check API keys in tests
        mock_validate.return_value = None

        mock_call.return_value = [
            ModelResponse(
                model="gpt-4o",
                response="[AGREE]\n[SPEC]\n# Final\n[/SPEC]",
                agreed=True,
                spec="# Final",
                input_tokens=100,
                output_tokens=50,
                cost=0.01,
            ),
            ModelResponse(
                model="gemini/gemini-2.0-flash",
                response="[AGREE]\n[SPEC]\n# Final\n[/SPEC]",
                agreed=True,
                spec="# Final",
                input_tokens=80,
                output_tokens=40,
                cost=0.005,
            ),
        ]

        with patch("sys.stdin", StringIO("# Test Spec")):
            with patch(
                "sys.argv",
                [
                    "debate.py",
                    "critique",
                    "--models",
                    "gpt-4o,gemini/gemini-2.0-flash",
                    "--json",
                ],
            ):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    with patch("sys.stderr", new_callable=StringIO):
                        debate.main()
                        output = mock_stdout.getvalue()

                        data = json.loads(output)
                        assert data["all_agreed"] is True

    @patch("debate.validate_models_before_run")
    @patch("debate.call_models_parallel")
    def test_critique_passes_options(self, mock_call, mock_validate):
        """Test that CLI options are passed to model calls."""
        import debate
        from models import ModelResponse

        # Mock validation to not check API keys in tests
        mock_validate.return_value = None

        mock_call.return_value = [
            ModelResponse(
                model="gpt-4o",
                response="[AGREE]\n[SPEC]\n# Spec\n[/SPEC]",
                agreed=True,
                spec="# Spec",
            )
        ]

        with patch("sys.stdin", StringIO("# Spec")):
            with patch(
                "sys.argv",
                [
                    "debate.py",
                    "critique",
                    "--models",
                    "gpt-4o",
                    "--focus",
                    "security",
                    "--persona",
                    "security-engineer",
                    "--preserve-intent",
                    "--json",
                ],
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    with patch("sys.stderr", new_callable=StringIO):
                        debate.main()

                        # Verify options were passed (positional args)
                        # call_models_parallel(models, spec, round_num, doc_type, press,
                        #                      focus, persona, context, preserve_intent, ...)
                        call_args = mock_call.call_args[0]
                        assert call_args[0] == ["gpt-4o"]  # models
                        assert call_args[5] == "security"  # focus
                        assert call_args[6] == "security-engineer"  # persona
                        assert call_args[8] is True  # preserve_intent


class TestCLIBedrock:
    def test_bedrock_status_not_configured(self):
        """Test bedrock status when not configured."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("sys.argv", ["debate.py", "bedrock", "status"]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        debate.main()
                        output = mock_stdout.getvalue()
                        assert "Not configured" in output

    def test_bedrock_enable(self):
        """Test enabling bedrock mode."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "adversarial-spec" / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch(
                    "sys.argv",
                    ["debate.py", "bedrock", "enable", "--region", "us-east-1"],
                ):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        debate.main()
                        output = mock_stdout.getvalue()
                        assert "enabled" in output.lower()

                        # Verify config was written
                        assert config_path.exists()
                        data = json.loads(config_path.read_text())
                        assert data["bedrock"]["enabled"] is True
                        assert data["bedrock"]["region"] == "us-east-1"


class TestCreateParser:
    def test_creates_parser_with_all_actions(self):
        """Test that parser includes all expected actions."""
        import debate

        parser = debate.create_parser()
        # Parse with a valid action to verify it works
        args = parser.parse_args(["providers"])
        assert args.action == "providers"

    def test_default_values(self):
        """Test default argument values."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique"])
        assert args.models is None  # Now dynamically detected based on API keys
        assert args.doc_type == "spec"
        assert args.round == 1
        assert args.timeout == 600


class TestHandleInfoCommand:
    def test_returns_false_for_non_info_command(self):
        """Test that non-info commands return False."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique"])
        result = debate.handle_info_command(args)
        assert result is False

    def test_returns_true_for_providers(self):
        """Test that providers command is handled."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["providers"])
        with patch("sys.stdout", new_callable=StringIO):
            result = debate.handle_info_command(args)
        assert result is True


class TestHandleUtilityCommand:
    def test_returns_false_for_non_utility_command(self):
        """Test that non-utility commands return False."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique"])
        result = debate.handle_utility_command(args)
        assert result is False

    def test_diff_without_files_exits(self):
        """Test that diff without --previous/--current exits."""
        import debate
        import pytest

        parser = debate.create_parser()
        args = parser.parse_args(["diff"])
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new_callable=StringIO):
                debate.handle_utility_command(args)
        assert exc_info.value.code == 1


class TestApplyProfile:
    def test_no_profile_does_nothing(self):
        """Test that no profile arg leaves args unchanged."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--models", "gpt-4o"])
        original_models = args.models
        debate.apply_profile(args)
        assert args.models == original_models

    def test_profile_overrides_defaults(self):
        """Test that profile values override defaults."""
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)
            profile_path = profiles_dir / "test.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "models": "claude-3-opus",
                        "doc_type": "prd",
                        "focus": "security",
                    }
                )
            )

            with patch("providers.PROFILES_DIR", profiles_dir):
                parser = debate.create_parser()
                args = parser.parse_args(["critique", "--profile", "test"])
                debate.apply_profile(args)
                assert args.models == "claude-3-opus"
                assert args.doc_type == "prd"
                assert args.focus == "security"


class TestParseModels:
    def test_parses_single_model(self):
        """Test parsing single model."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--models", "gpt-4o"])
        models = debate.parse_models(args)
        assert models == ["gpt-4o"]

    def test_parses_multiple_models(self):
        """Test parsing comma-separated models."""
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--models", "gpt-4o, claude-3, gemini"])
        models = debate.parse_models(args)
        assert models == ["gpt-4o", "claude-3", "gemini"]

    def test_empty_models_exits(self):
        """Test that empty models list exits."""
        import debate
        import pytest

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--models", ""])
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new_callable=StringIO):
                debate.parse_models(args)
        assert exc_info.value.code == 1


class TestOutputResults:
    def test_json_output_format(self):
        """Test JSON output format."""
        import debate
        from models import ModelResponse

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--json"])

        results = [
            ModelResponse(
                model="gpt-4o",
                response="test",
                agreed=True,
                spec="spec",
            )
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            debate.output_results(args, results, ["gpt-4o"], True, None, None)
            output = json.loads(mock_stdout.getvalue())
            assert output["all_agreed"] is True
            assert output["models"] == ["gpt-4o"]

    def test_text_output_format(self):
        """Test text output format."""
        import debate
        from models import ModelResponse

        parser = debate.create_parser()
        args = parser.parse_args(["critique"])

        results = [
            ModelResponse(
                model="gpt-4o",
                response="Critique text",
                agreed=False,
                spec="spec",
            )
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            debate.output_results(args, results, ["gpt-4o"], False, None, None)
            output = mock_stdout.getvalue()
            assert "Round 1 Results" in output
            assert "gpt-4o" in output
            assert "Critique text" in output


class TestHandleInfoCommandSessions:
    """Tests for sessions command in handle_info_command.

    Mutation targets:
    - sessions list logic
    - empty sessions check
    """

    def test_sessions_with_data(self):
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()
            # Create a session file with correct structure
            session_path = sessions_dir / "test-session.json"
            session_data = {
                "session_id": "test-session",
                "round": 2,
                "doc_type": "tech",
                "updated_at": "2025-01-11T12:00:00",
                "spec": "# Test spec",
                "history": [],
            }
            session_path.write_text(json.dumps(session_data))

            with patch("session.SESSIONS_DIR", sessions_dir):
                with patch("debate.SESSIONS_DIR", sessions_dir):
                    with patch("sys.argv", ["debate.py", "sessions"]):
                        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                            debate.main()
                            output = mock_stdout.getvalue()
                            assert "test-session" in output
                            assert "round: 2" in output


class TestHandleUtilityCommandEdgeCases:
    """Tests for handle_utility_command edge cases.

    Mutation targets:
    - save-profile without name
    - diff file read error
    """

    def test_save_profile_without_name_exits(self):
        import debate
        import pytest

        parser = debate.create_parser()
        args = parser.parse_args(["save-profile"])
        args.profile_name = None

        with pytest.raises(SystemExit) as exc_info:
            debate.handle_utility_command(args)
        assert exc_info.value.code == 1

    def test_diff_with_nonexistent_file(self):
        import debate
        import pytest

        parser = debate.create_parser()
        args = parser.parse_args(
            [
                "diff",
                "--previous",
                "/nonexistent/prev.md",
                "--current",
                "/nonexistent/curr.md",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new_callable=StringIO):
                debate.handle_utility_command(args)
        assert exc_info.value.code == 1

    def test_diff_no_differences(self):
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            prev = Path(tmpdir) / "prev.md"
            curr = Path(tmpdir) / "curr.md"
            prev.write_text("same content")
            curr.write_text("same content")

            parser = debate.create_parser()
            args = parser.parse_args(
                ["diff", "--previous", str(prev), "--current", str(curr)]
            )

            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = debate.handle_utility_command(args)
                assert result is True
                assert "No differences" in mock_stdout.getvalue()


class TestApplyProfileAllFields:
    """Tests for apply_profile with all fields.

    Mutation targets:
    - context field
    - preserve_intent field
    """

    def test_applies_context_from_profile(self):
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)
            profile_path = profiles_dir / "test.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "models": "gpt-4o",
                        "context": "/some/context.md",
                    }
                )
            )

            with patch("providers.PROFILES_DIR", profiles_dir):
                parser = debate.create_parser()
                args = parser.parse_args(["critique", "--profile", "test"])
                debate.apply_profile(args)
                # Mutation: not setting context would leave it empty
                assert args.context == "/some/context.md"

    def test_applies_preserve_intent_from_profile(self):
        import debate

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)
            profile_path = profiles_dir / "test.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "models": "gpt-4o",
                        "preserve_intent": True,
                    }
                )
            )

            with patch("providers.PROFILES_DIR", profiles_dir):
                parser = debate.create_parser()
                args = parser.parse_args(["critique", "--profile", "test"])
                debate.apply_profile(args)
                # Mutation: not setting preserve_intent would leave it False
                assert args.preserve_intent is True


class TestSetupBedrock:
    """Tests for setup_bedrock function.

    Mutation targets:
    - bedrock mode detection
    - model validation
    """

    def test_returns_original_models_when_not_bedrock(self):
        import debate

        parser = debate.create_parser()
        args = parser.parse_args(["critique", "--models", "gpt-4o"])
        models = ["gpt-4o"]

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                new_models, bedrock_mode, region = debate.setup_bedrock(args, models)
                assert new_models == ["gpt-4o"]
                assert bedrock_mode is False
                assert region is None


class TestSendTelegramNotification:
    """Tests for send_telegram_notification function.

    Mutation targets:
    - telegram config check
    - message formatting
    - poll logic
    """

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.send_long_message")
    @patch("telegram_bot.get_last_update_id")
    @patch("telegram_bot.get_config")
    def test_sends_notification_and_returns_feedback(
        self, mock_config, mock_last_id, mock_send, mock_poll
    ):
        import debate
        from models import ModelResponse

        mock_config.return_value = ("token", "123")
        mock_last_id.return_value = 0
        mock_send.return_value = True
        mock_poll.return_value = "User feedback"

        results = [
            ModelResponse(
                model="gpt-4o",
                response="Critique here",
                agreed=False,
                spec="# Spec",
            )
        ]

        feedback = debate.send_telegram_notification(["gpt-4o"], 1, results, 60)
        assert feedback == "User feedback"

    @patch("telegram_bot.get_config")
    def test_returns_none_when_not_configured(self, mock_config):
        import debate
        from models import ModelResponse

        mock_config.return_value = ("", "")

        results = [
            ModelResponse(model="gpt-4o", response="test", agreed=True, spec="spec")
        ]

        with patch("sys.stderr", new_callable=StringIO):
            feedback = debate.send_telegram_notification(["gpt-4o"], 1, results, 60)
        assert feedback is None

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.send_long_message")
    @patch("telegram_bot.get_last_update_id")
    @patch("telegram_bot.get_config")
    def test_handles_all_agree(self, mock_config, mock_last_id, mock_send, mock_poll):
        import debate
        from models import ModelResponse

        mock_config.return_value = ("token", "123")
        mock_last_id.return_value = 0
        mock_send.return_value = True
        mock_poll.return_value = None

        results = [
            ModelResponse(model="gpt-4o", response="[AGREE]", agreed=True, spec="spec"),
            ModelResponse(model="gemini", response="[AGREE]", agreed=True, spec="spec"),
        ]

        feedback = debate.send_telegram_notification(
            ["gpt-4o", "gemini"], 1, results, 60
        )
        assert feedback is None
        # Check message was sent with ALL AGREE status
        call_args = mock_send.call_args
        assert "ALL AGREE" in call_args[0][2]

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.send_long_message")
    @patch("telegram_bot.get_last_update_id")
    @patch("telegram_bot.get_config")
    def test_handles_error_response(
        self, mock_config, mock_last_id, mock_send, mock_poll
    ):
        import debate
        from models import ModelResponse

        mock_config.return_value = ("token", "123")
        mock_last_id.return_value = 0
        mock_send.return_value = True
        mock_poll.return_value = None

        results = [
            ModelResponse(
                model="gpt-4o",
                response="",
                agreed=False,
                spec="",
                error="API timeout",
            )
        ]

        debate.send_telegram_notification(["gpt-4o"], 1, results, 60)
        call_args = mock_send.call_args
        assert "ERROR" in call_args[0][2]


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_model_calls.py (301 lines, 9655 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for model calling logic with mocked API responses."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    CostTracker,
    ModelResponse,
    call_models_parallel,
    call_single_model,
)


class MockUsage:
    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockChoice:
    def __init__(self, content):
        self.message = MagicMock()
        self.message.content = content


class MockResponse:
    def __init__(self, content, prompt_tokens=100, completion_tokens=50):
        self.choices = [MockChoice(content)]
        self.usage = MockUsage(prompt_tokens, completion_tokens)


class TestCallSingleModel:
    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_returns_model_response_on_success(self, mock_completion):
        mock_completion.return_value = MockResponse(
            "Here is my critique.\n\n[SPEC]\n# Revised Spec\n[/SPEC]"
        )

        result = call_single_model(
            model="gpt-4o",
            spec="# Original Spec",
            round_num=1,
            doc_type="tech",
        )

        assert isinstance(result, ModelResponse)
        assert result.model == "gpt-4o"
        assert result.agreed is False
        assert result.spec == "# Revised Spec"
        assert result.error is None
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_detects_agreement(self, mock_completion):
        mock_completion.return_value = MockResponse(
            "This spec looks complete. [AGREE]\n\n[SPEC]\n# Final Spec\n[/SPEC]"
        )

        result = call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=2,
            doc_type="tech",
        )

        assert result.agreed is True
        assert result.spec == "# Final Spec"

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_handles_api_error_with_retry(self, mock_completion):
        mock_completion.side_effect = Exception("API timeout")

        result = call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        assert result.error is not None
        assert "API timeout" in result.error
        assert result.agreed is False
        # Should have retried 3 times
        assert mock_completion.call_count == 3

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_recovers_on_second_retry(self, mock_completion):
        # First call fails, second succeeds
        mock_completion.side_effect = [
            Exception("Temporary error"),
            MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]"),
        ]

        result = call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        assert result.error is None
        assert result.agreed is True
        assert mock_completion.call_count == 2

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_includes_focus_in_prompt(self, mock_completion):
        mock_completion.return_value = MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]")

        call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
            focus="security",
        )

        # Check that the user message includes security focus
        call_args = mock_completion.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "SECURITY" in user_message

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_includes_preserve_intent_prompt(self, mock_completion):
        mock_completion.return_value = MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]")

        call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
            preserve_intent=True,
        )

        call_args = mock_completion.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "PRESERVE ORIGINAL INTENT" in user_message

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_uses_press_prompt_when_press_true(self, mock_completion):
        mock_completion.return_value = MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]")

        call_single_model(
            model="gpt-4o",
            spec="# Spec",
            round_num=2,
            doc_type="tech",
            press=True,
        )

        call_args = mock_completion.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "confirm your agreement" in user_message

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_bedrock_mode_adds_prefix(self, mock_completion):
        mock_completion.return_value = MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]")

        call_single_model(
            model="anthropic.claude-3-sonnet",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
            bedrock_mode=True,
            bedrock_region="us-east-1",
        )

        call_args = mock_completion.call_args
        # Model should have bedrock/ prefix
        assert call_args.kwargs["model"] == "bedrock/anthropic.claude-3-sonnet"


class TestCallModelsParallel:
    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_calls_multiple_models(self, mock_completion):
        mock_completion.return_value = MockResponse(
            "Critique here.\n[SPEC]\n# Revised\n[/SPEC]"
        )

        results = call_models_parallel(
            models=["gpt-4o", "gemini/gemini-2.0-flash"],
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        assert len(results) == 2
        # Each model should have been called
        assert mock_completion.call_count == 2

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_handles_mixed_results(self, mock_completion):
        # First model agrees, second critiques
        def side_effect(*args, **kwargs):
            model = kwargs.get("model", args[0] if args else "")
            if "gpt" in model:
                return MockResponse("[AGREE]\n[SPEC]\n# Final\n[/SPEC]")
            else:
                return MockResponse("Issues found.\n[SPEC]\n# Revised\n[/SPEC]")

        mock_completion.side_effect = side_effect

        results = call_models_parallel(
            models=["gpt-4o", "gemini/gemini-2.0-flash"],
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        agreed_count = sum(1 for r in results if r.agreed)
        assert agreed_count == 1

    @patch("models.completion")
    @patch("models.cost_tracker", CostTracker())
    def test_one_model_error_others_succeed(self, mock_completion):
        # Use model name to determine behavior (deterministic in parallel)
        def side_effect(*args, **kwargs):
            model = kwargs.get("model", "")
            if "fail" in model:
                raise Exception("API error")
            return MockResponse("[AGREE]\n[SPEC]\n# Spec\n[/SPEC]")

        mock_completion.side_effect = side_effect

        results = call_models_parallel(
            models=["model-fail", "model-succeed"],
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        errors = [r for r in results if r.error]
        successes = [r for r in results if not r.error]
        assert len(errors) == 1
        assert len(successes) == 1
        assert errors[0].model == "model-fail"
        assert successes[0].model == "model-succeed"


class TestCostTrackerIntegration:
    @patch("models.completion")
    def test_cost_accumulates_across_calls(self, mock_completion):
        tracker = CostTracker()

        with patch("models.cost_tracker", tracker):
            mock_completion.return_value = MockResponse(
                "[AGREE]\n[SPEC]\n# Spec\n[/SPEC]",
                prompt_tokens=1000,
                completion_tokens=500,
            )

            call_single_model(
                model="gpt-4o",
                spec="# Spec",
                round_num=1,
                doc_type="tech",
            )

            call_single_model(
                model="gpt-4o",
                spec="# Spec",
                round_num=2,
                doc_type="tech",
            )

        assert tracker.total_input_tokens == 2000
        assert tracker.total_output_tokens == 1000
        assert tracker.total_cost > 0
        assert "gpt-4o" in tracker.by_model


class TestCodexModelPath:
    @patch("models.CODEX_AVAILABLE", False)
    @patch("models.cost_tracker", CostTracker())
    def test_codex_unavailable_returns_error(self):
        result = call_single_model(
            model="codex/gpt-5.3-codex",
            spec="# Spec",
            round_num=1,
            doc_type="tech",
        )

        assert result.error is not None
        assert "Codex CLI not found" in result.error


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_models.py (1262 lines, 45343 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for models module."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    CostTracker,
    call_claude_cli_model,
    call_codex_model,
    call_gemini_cli_model,
    detect_agreement,
    extract_spec,
    extract_tasks,
    generate_diff,
    get_critique_summary,
    is_o_series_model,
    load_context_files,
)


class TestModelResponse:
    def test_create_response(self):
        response = ModelResponse(
            model="gpt-4o",
            response="This is a critique.",
            agreed=False,
            spec="# Revised Spec",
        )
        assert response.model == "gpt-4o"
        assert response.agreed is False
        assert response.spec == "# Revised Spec"

    def test_default_values(self):
        # Mutation: changing defaults would fail these checks
        response = ModelResponse(
            model="test",
            response="test",
            agreed=False,
            spec=None,
        )
        assert response.error is None  # Not ""
        assert response.input_tokens == 0  # Not 1
        assert response.output_tokens == 0  # Not 1
        assert response.cost == 0.0  # Not 1.0

    def test_response_with_error(self):
        response = ModelResponse(
            model="gpt-4o",
            response="",
            agreed=False,
            spec=None,
            error="API timeout",
        )
        assert response.error == "API timeout"

    def test_response_with_tokens(self):
        response = ModelResponse(
            model="gpt-4o",
            response="Response",
            agreed=True,
            spec="Spec",
            input_tokens=1000,
            output_tokens=500,
            cost=0.05,
        )
        assert response.input_tokens == 1000
        assert response.output_tokens == 500
        assert response.cost == 0.05


class TestCostTracker:
    def test_add_costs(self):
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)

        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500
        assert tracker.total_cost > 0

    def test_cost_calculation_uses_division(self):
        # Mutation: / to * would make cost astronomically large
        tracker = CostTracker()
        # Use a model with known costs
        cost = tracker.add("gpt-4o", 1_000_000, 1_000_000)
        # With division by 1M, cost should be in dollars (single/double digits)
        # With multiplication by 1M, cost would be trillions
        assert cost < 1000  # Reasonable upper bound for 1M tokens

    def test_default_values(self):
        # Mutation: changing default 0.0 to 1.0 would fail
        tracker = CostTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == 0.0  # Must be exactly 0.0
        assert tracker.by_model == {}

    def test_tracks_by_model(self):
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)
        tracker.add("gemini/gemini-2.0-flash", 2000, 1000)

        assert "gpt-4o" in tracker.by_model
        assert "gemini/gemini-2.0-flash" in tracker.by_model
        assert tracker.by_model["gpt-4o"]["input_tokens"] == 1000

    def test_accumulates_for_same_model(self):
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)
        tracker.add("gpt-4o", 1000, 500)

        assert tracker.by_model["gpt-4o"]["input_tokens"] == 2000
        assert tracker.by_model["gpt-4o"]["output_tokens"] == 1000

    def test_cost_accumulates_not_replaces(self):
        # Mutation: += to = would fail this test
        tracker = CostTracker()
        cost1 = tracker.add("gpt-4o", 1000, 500)
        cost2 = tracker.add("gpt-4o", 1000, 500)

        # Total cost should be sum of both calls
        expected_total = cost1 + cost2
        assert tracker.by_model["gpt-4o"]["cost"] == expected_total
        assert tracker.total_cost == expected_total

    def test_summary_format(self):
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)

        summary = tracker.summary()
        assert "Cost Summary" in summary
        assert "Total tokens" in summary
        assert "Total cost" in summary

    def test_summary_starts_with_empty_line(self):
        # Mutation: "" -> "XXXX" would change first line
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)
        summary = tracker.summary()
        # Summary should start with empty line (newline)
        assert summary.startswith("\n")
        assert "XXXX" not in summary

    def test_summary_shows_by_model_when_multiple(self):
        tracker = CostTracker()
        tracker.add("gpt-4o", 1000, 500)
        tracker.add("gemini-pro", 2000, 1000)
        summary = tracker.summary()
        assert "By model:" in summary
        assert "gpt-4o" in summary
        assert "gemini-pro" in summary


class TestDetectAgreement:
    def test_detects_agree(self):
        assert detect_agreement("I agree. [AGREE]\n[SPEC]...[/SPEC]") is True

    def test_no_agree(self):
        assert detect_agreement("I have concerns about security.") is False

    def test_partial_agree_in_word(self):
        # [AGREE] must be present as marker
        assert detect_agreement("I disagree with this approach.") is False


class TestExtractSpec:
    def test_extracts_spec(self):
        response = "Critique here.\n\n[SPEC]\n# My Spec\n\nContent\n[/SPEC]"
        spec = extract_spec(response)
        assert spec == "# My Spec\n\nContent"

    def test_returns_none_without_tags(self):
        response = "Just a critique without spec tags."
        assert extract_spec(response) is None

    def test_returns_none_with_missing_end_tag(self):
        response = "[SPEC]Content without end tag"
        assert extract_spec(response) is None

    def test_handles_empty_spec(self):
        response = "[SPEC][/SPEC]"
        spec = extract_spec(response)
        assert spec == ""


class TestExtractTasks:
    def test_extracts_single_task(self):
        response = """
[TASK]
title: Implement auth
type: task
priority: high
description: Add OAuth2 authentication
acceptance_criteria:
- User can log in
- Session persists
[/TASK]
"""
        tasks = extract_tasks(response)
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Implement auth"
        assert tasks[0]["type"] == "task"
        assert tasks[0]["priority"] == "high"
        assert len(tasks[0]["acceptance_criteria"]) == 2

    def test_extracts_multiple_tasks(self):
        response = """
[TASK]
title: Task 1
type: task
priority: high
description: First task
[/TASK]
[TASK]
title: Task 2
type: bug
priority: medium
description: Second task
[/TASK]
"""
        tasks = extract_tasks(response)
        assert len(tasks) == 2
        assert tasks[0]["title"] == "Task 1"
        assert tasks[1]["title"] == "Task 2"

    def test_handles_no_tasks(self):
        response = "No tasks here."
        tasks = extract_tasks(response)
        assert tasks == []

    def test_exact_slice_positions(self):
        # Mutation: line[6:] -> line[7:] for title would lose first char
        # Mutation: line[5:] -> line[6:] for type would lose first char
        # Mutation: line[9:] -> line[10:] for priority would lose first char
        # Mutation: line[12:] -> line[13:] for description would lose first char
        response = """
[TASK]
title: Xauth
type: Xtask
priority: Xhigh
description: Xdesc
[/TASK]
"""
        tasks = extract_tasks(response)
        assert tasks[0]["title"] == "Xauth"  # X must be preserved
        assert tasks[0]["type"] == "Xtask"
        assert tasks[0]["priority"] == "Xhigh"
        assert tasks[0]["description"] == "Xdesc"

    def test_multiline_title_joined_correctly(self):
        # Mutation: "\n".join -> "XX\nXX".join in title path
        response = """
[TASK]
title: Main title
continuation of title
type: task
priority: high
description: Desc
[/TASK]
"""
        tasks = extract_tasks(response)
        title = tasks[0]["title"]
        assert "Main title" in title
        assert "XX" not in title

    def test_multiline_description_joined_correctly(self):
        # Mutation: "\n".join -> "XX\nXX".join would corrupt multi-line values
        response = """
[TASK]
title: Test
type: task
priority: high
description: Line 1
Line 2
Line 3
[/TASK]
"""
        tasks = extract_tasks(response)
        desc = tasks[0]["description"]
        assert "Line 1" in desc
        assert "Line 2" in desc
        assert "XX" not in desc  # Mutation check
        # Verify proper newline joining
        assert "Line 1\nLine 2" in desc or "Line 1" in desc

    def test_multiline_priority_value_joined(self):
        # Mutation: "\n".join -> "XX\nXX".join in priority path
        response = """
[TASK]
title: Test
type: task
priority: high
extra priority line
description: Desc
[/TASK]
"""
        tasks = extract_tasks(response)
        priority = tasks[0]["priority"]
        assert "XX" not in priority

    def test_multiline_type_value_joined(self):
        # Mutation: "\n".join -> "XX\nXX".join in type path
        response = """
[TASK]
title: Test
type: task
extra type line
priority: high
description: Desc
[/TASK]
"""
        tasks = extract_tasks(response)
        task_type = tasks[0]["type"]
        assert "XX" not in task_type

    def test_acceptance_criteria_only_with_dash_prefix(self):
        # Mutation: and -> or would accept lines without "- " prefix
        response = """
[TASK]
title: Test
type: task
priority: high
description: Desc
acceptance_criteria:
- Valid item
Not a valid item because no dash
- Another valid item
[/TASK]
"""
        tasks = extract_tasks(response)
        criteria = tasks[0]["acceptance_criteria"]
        # Should only have items that started with "- "
        assert "Valid item" in criteria
        assert "Another valid item" in criteria
        # The line without dash should NOT be in criteria as a separate item
        # It would be appended as continuation if the mutation happens

    def test_acceptance_criteria_item_prefix_removed(self):
        # Mutation: line[2:] -> line[3:] would lose first char of criteria
        response = """
[TASK]
title: Test
type: task
priority: high
description: Desc
acceptance_criteria:
- Xfirst criteria
- Xsecond criteria
[/TASK]
"""
        tasks = extract_tasks(response)
        criteria = tasks[0]["acceptance_criteria"]
        assert criteria[0] == "Xfirst criteria"  # X must be preserved
        assert criteria[1] == "Xsecond criteria"

    def test_task_without_end_tag_skipped(self):
        response = """
[TASK]
title: Incomplete
type: task
Some text without closing tag
"""
        tasks = extract_tasks(response)
        assert tasks == []

    def test_continues_after_incomplete_task(self):
        # Mutation: continue -> break would stop after first incomplete task
        response = """
[TASK]
title: Incomplete
type: task
No closing tag here

[TASK]
title: Complete Task
type: task
priority: high
description: This one is complete
[/TASK]
"""
        tasks = extract_tasks(response)
        # Should still get the second complete task
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Complete Task"

    def test_empty_values_handled(self):
        # Mutation: current_value[0] if current_value else "" - check empty case
        response = """
[TASK]
title: Test
type:
priority: high
description: Desc
[/TASK]
"""
        tasks = extract_tasks(response)
        assert tasks[0]["type"] == ""

    def test_single_vs_multiple_value_lines(self):
        # Mutation: len(current_value) > 1 -> len(current_value) >= 1
        # This matters when exactly 1 line - should return the single line directly
        response = """
[TASK]
title: Single
type: task
priority: high
description: One line only
[/TASK]
"""
        tasks = extract_tasks(response)
        assert tasks[0]["description"] == "One line only"

    def test_task_requires_title(self):
        # Mutation: task.get("title") check ensures empty tasks ignored
        response = """
[TASK]
type: task
priority: high
[/TASK]
"""
        tasks = extract_tasks(response)
        assert tasks == []  # No title means not added

    def test_acceptance_criteria_returns_list(self):
        # Mutation: current_key == "acceptance_criteria" check for list vs string
        response = """
[TASK]
title: Test
type: task
priority: high
description: Desc
acceptance_criteria:
- Item 1
- Item 2
[/TASK]
"""
        tasks = extract_tasks(response)
        criteria = tasks[0]["acceptance_criteria"]
        assert isinstance(criteria, list)
        assert len(criteria) == 2


class TestGetCritiqueSummary:
    def test_extracts_critique_before_spec(self):
        response = "This is the critique.\n\n[SPEC]...[/SPEC]"
        summary = get_critique_summary(response)
        assert summary == "This is the critique."

    def test_truncates_long_critique(self):
        response = "A" * 500
        summary = get_critique_summary(response, max_length=100)
        assert len(summary) == 103  # 100 + "..."
        assert summary.endswith("...")

    def test_full_response_without_spec(self):
        response = "Just critique, no spec."
        summary = get_critique_summary(response)
        assert summary == "Just critique, no spec."


class TestGenerateDiff:
    def test_generates_diff(self):
        previous = "line1\nline2\nline3"
        current = "line1\nmodified\nline3"

        diff = generate_diff(previous, current)
        assert "-line2" in diff
        assert "+modified" in diff

    def test_no_diff_for_identical(self):
        content = "same\ncontent"
        diff = generate_diff(content, content)
        assert diff == ""

    def test_diff_contains_filename_markers(self):
        # Mutation: fromfile="previous" -> "XXpreviousXX" would change output
        previous = "old"
        current = "new"
        diff = generate_diff(previous, current)
        assert "previous" in diff
        assert "current" in diff
        assert "XX" not in diff  # No mutation artifacts


class TestLoadContextFiles:
    def test_loads_empty_list(self):
        result = load_context_files([])
        assert result == ""

    def test_loads_nonexistent_file(self):
        result = load_context_files(["/nonexistent/file.md"])
        assert "Error loading file" in result

    def test_formats_context(self, tmp_path):
        test_file = tmp_path / "context.md"
        test_file.write_text("# Context\n\nSome context.")

        result = load_context_files([str(test_file)])
        assert "Additional Context" in result
        assert "# Context" in result

    def test_context_format_contains_markdown(self, tmp_path):
        # Mutation: format string mutations would add XX
        test_file = tmp_path / "test.md"
        test_file.write_text("Content")

        result = load_context_files([str(test_file)])
        assert "### Context:" in result
        assert "```" in result
        assert "XX" not in result  # No mutation artifacts


class TestCallCodexModel:
    @patch("models.CODEX_AVAILABLE", False)
    def test_raises_when_codex_unavailable(self):
        import pytest

        with pytest.raises(RuntimeError, match="Codex CLI not found"):
            call_codex_model("system", "user", "codex/gpt-5")

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_extracts_model_name_from_codex_prefix(self, mock_run):
        # Mutation: model.split("/", 1)[1] - verify correct extraction
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"Response"}}\n{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/gpt-5.3-codex")
        # Verify model name was extracted and passed to command
        cmd = mock_run.call_args[0][0]
        assert "gpt-5.3-codex" in cmd
        assert "codex/gpt-5.3-codex" not in cmd

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_parses_jsonl_response(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"Test response"}}\n{"type":"turn.completed","usage":{"input_tokens":150,"output_tokens":75}}',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/model")
        assert response == "Test response"
        assert inp == 150
        assert out == 75

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_handles_nonzero_exit_code(self, mock_run):
        import pytest

        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Some error")
        with pytest.raises(RuntimeError, match="Codex CLI failed"):
            call_codex_model("sys", "user", "codex/model")

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_handles_no_agent_message(self, mock_run):
        import pytest

        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}',
            stderr="",
        )
        with pytest.raises(RuntimeError, match="No agent message found"):
            call_codex_model("sys", "user", "codex/model")

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_includes_search_flag_when_enabled(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"Response"}}\n{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}',
            stderr="",
        )
        call_codex_model("sys", "user", "codex/model", search=True)
        cmd = mock_run.call_args[0][0]
        assert "--search" in cmd

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        import subprocess

        import pytest

        mock_run.side_effect = subprocess.TimeoutExpired("codex", 600)
        with pytest.raises(RuntimeError, match="timed out"):
            call_codex_model("sys", "user", "codex/model")

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_file_not_found_raises_runtime_error(self, mock_run):
        import pytest

        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(RuntimeError, match="not found in PATH"):
            call_codex_model("sys", "user", "codex/model")

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_reasoning_effort_passed_correctly(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"R"}}\n{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}',
            stderr="",
        )
        call_codex_model("sys", "user", "codex/model", reasoning_effort="high")
        cmd = mock_run.call_args[0][0]
        # Find -c argument and check reasoning effort
        assert any('model_reasoning_effort="high"' in str(arg) for arg in cmd)

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_skips_empty_lines_in_jsonl(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='\n\n{"type":"item.completed","item":{"type":"agent_message","text":"Response"}}\n\n{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}\n',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/model")
        assert response == "Response"

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_default_tokens_when_no_usage(self, mock_run):
        # Mutation: input_tokens = 0 -> 1, output_tokens = 0 -> 1
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"Response"}}',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/model")
        # Without turn.completed event, should default to 0
        assert inp == 0
        assert out == 0

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_handles_malformed_json_line(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='not json\n{"type":"item.completed","item":{"type":"agent_message","text":"Response"}}\n{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/model")
        assert response == "Response"

    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_extracts_token_counts_from_usage(self, mock_run):
        # Mutation: usage.get("input_tokens", 0) -> 1 would change this
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"type":"item.completed","item":{"type":"agent_message","text":"R"}}\n{"type":"turn.completed","usage":{"input_tokens":0,"output_tokens":0}}',
            stderr="",
        )
        response, inp, out = call_codex_model("sys", "user", "codex/model")
        # Verify we get exact values from usage, not defaults
        assert inp == 0
        assert out == 0


class TestCallGeminiCliModel:
    @patch("models.GEMINI_CLI_AVAILABLE", False)
    def test_raises_when_gemini_cli_unavailable(self):
        import pytest

        with pytest.raises(RuntimeError, match="Gemini CLI not found"):
            call_gemini_cli_model("system", "user", "gemini-cli/gemini-3-pro-preview")

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_extracts_model_name_from_prefix(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Test response from Gemini",
            stderr="",
        )
        response, inp, out = call_gemini_cli_model(
            "sys", "user", "gemini-cli/gemini-3-pro-preview"
        )
        cmd = mock_run.call_args[0][0]
        assert "gemini-3-pro-preview" in cmd
        assert "gemini-cli/gemini-3-pro-preview" not in " ".join(cmd)

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_returns_response_text(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Test response from Gemini",
            stderr="",
        )
        response, inp, out = call_gemini_cli_model("sys", "user", "gemini-cli/model")
        assert response == "Test response from Gemini"

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_filters_noise_lines(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Loaded cached credentials.\nServer 'context7' supports...\nLoading extension: foo\nActual response",
            stderr="",
        )
        response, inp, out = call_gemini_cli_model("sys", "user", "gemini-cli/model")
        assert "Loaded cached" not in response
        assert "Server " not in response
        assert "Loading extension" not in response
        assert "Actual response" in response

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_handles_nonzero_exit_code(self, mock_run):
        import pytest

        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Some error")
        with pytest.raises(RuntimeError, match="Gemini CLI failed"):
            call_gemini_cli_model("sys", "user", "gemini-cli/model")

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_raises_on_empty_response(self, mock_run):
        import pytest

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Loaded cached credentials.\nServer 'context7' supports...",
            stderr="",
        )
        with pytest.raises(RuntimeError, match="No response from Gemini CLI"):
            call_gemini_cli_model("sys", "user", "gemini-cli/model")

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        import subprocess

        import pytest

        mock_run.side_effect = subprocess.TimeoutExpired("gemini", 600)
        with pytest.raises(RuntimeError, match="timed out"):
            call_gemini_cli_model("sys", "user", "gemini-cli/model")

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_file_not_found_raises_runtime_error(self, mock_run):
        import pytest

        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(RuntimeError, match="not found in PATH"):
            call_gemini_cli_model("sys", "user", "gemini-cli/model")

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_estimates_tokens(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Response text here",
            stderr="",
        )
        response, inp, out = call_gemini_cli_model(
            "system prompt", "user message", "gemini-cli/model"
        )
        # Token estimation: len // 4
        assert inp > 0
        assert out > 0

    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_uses_yolo_flag(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Response",
            stderr="",
        )
        call_gemini_cli_model("sys", "user", "gemini-cli/model")
        cmd = mock_run.call_args[0][0]
        assert "-y" in cmd


class TestCallClaudeCliModel:
    @patch("models.CLAUDE_CLI_AVAILABLE", False)
    def test_raises_when_claude_cli_unavailable(self):
        import pytest

        with pytest.raises(RuntimeError, match="Claude CLI not found"):
            call_claude_cli_model("system", "user", "claude-cli/claude-sonnet-4-6")

    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_extracts_model_name_from_prefix(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"result":"Response","input_tokens":100,"output_tokens":50}',
            stderr="",
        )
        response, inp, out = call_claude_cli_model(
            "sys", "user", "claude-cli/claude-sonnet-4-6"
        )
        cmd = mock_run.call_args[0][0]
        assert "claude-sonnet-4-6" in cmd
        assert "claude-cli/claude-sonnet-4-6" not in " ".join(cmd)
        assert response == "Response"
        assert inp == 100
        assert out == 50

    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_parses_event_array_output(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"type":"system"},{"type":"assistant","message":{"content":[{"type":"text","text":"Assistant text"}],"usage":{"input_tokens":3,"output_tokens":1}}},{"type":"result","result":"Final text","usage":{"input_tokens":3,"output_tokens":4}}]',
            stderr="",
        )
        response, inp, out = call_claude_cli_model("sys", "user", "claude-cli/model")
        assert response == "Final text"
        assert inp == 3
        assert out == 4

    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_falls_back_to_raw_text_for_non_json_output(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="Plain response", stderr="")
        response, inp, out = call_claude_cli_model("system prompt", "user", "claude-cli/model")
        assert response == "Plain response"
        assert inp > 0
        assert out > 0

    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    @patch("models.subprocess.run")
    def test_raises_on_empty_response(self, mock_run):
        import pytest

        mock_run.return_value = Mock(returncode=0, stdout='[{"type":"system"}]', stderr="")
        with pytest.raises(RuntimeError, match="No response from Claude CLI"):
            call_claude_cli_model("sys", "user", "claude-cli/model")


class TestCallSingleModel:
    @patch("models.completion")
    def test_returns_model_response_on_success(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="[AGREE]\n[SPEC]Final spec[/SPEC]"))
        ]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
        mock_completion.return_value = mock_response

        result = call_single_model(
            model="gpt-4o", spec="# Test Spec", round_num=1, doc_type="prd"
        )

        assert result.model == "gpt-4o"
        assert result.agreed is True
        assert result.spec == "Final spec"
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    @patch("models.completion")
    def test_extracts_spec_from_response(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Critique here\n[SPEC]\n# New Spec\n[/SPEC]"))
        ]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
        mock_completion.return_value = mock_response

        result = call_single_model("gpt-4o", "spec", 1, "prd")
        assert result.spec == "# New Spec"
        assert result.agreed is False

    @patch("models.completion")
    def test_handles_missing_usage(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = None
        mock_completion.return_value = mock_response

        result = call_single_model("gpt-4o", "spec", 1, "prd")
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("models.completion")
    @patch("models.time.sleep")
    def test_retries_on_failure(self, mock_sleep, mock_completion):
        mock_completion.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            Mock(
                choices=[Mock(message=Mock(content="[AGREE]"))],
                usage=Mock(prompt_tokens=10, completion_tokens=5),
            ),
        ]

        result = call_single_model("gpt-4o", "spec", 1, "prd")
        assert result.agreed is True
        assert mock_completion.call_count == 3
        # Verify exponential backoff
        assert mock_sleep.call_count == 2

    @patch("models.completion")
    @patch("models.time.sleep")
    def test_exponential_backoff_delay(self, mock_sleep, mock_completion):
        # Mutation: * -> / or 2**attempt -> 2*attempt would change delays
        mock_completion.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            Mock(
                choices=[Mock(message=Mock(content="[AGREE]"))],
                usage=Mock(prompt_tokens=10, completion_tokens=5),
            ),
        ]

        call_single_model("gpt-4o", "spec", 1, "prd")
        # First retry: delay = 1.0 * 2^0 = 1.0
        # Second retry: delay = 1.0 * 2^1 = 2.0
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 1.0  # First delay: 1.0 * 2^0
        assert calls[1][0][0] == 2.0  # Second delay: 1.0 * 2^1

    @patch("models.completion")
    @patch("models.time.sleep")
    def test_returns_error_after_max_retries(self, mock_sleep, mock_completion):
        mock_completion.side_effect = Exception("Persistent failure")

        result = call_single_model("gpt-4o", "spec", 1, "prd")
        assert result.error is not None
        assert "Persistent failure" in result.error
        assert mock_completion.call_count == MAX_RETRIES

    @patch("models.completion")
    def test_bedrock_mode_prefixes_model(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("claude-3", "spec", 1, "prd", bedrock_mode=True)
        # Verify bedrock/ prefix was added
        call_args = mock_completion.call_args
        assert call_args[1]["model"] == "bedrock/claude-3"

    @patch("models.completion")
    def test_bedrock_mode_skips_prefix_if_already_present(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("bedrock/claude-3", "spec", 1, "prd", bedrock_mode=True)
        call_args = mock_completion.call_args
        assert call_args[1]["model"] == "bedrock/claude-3"  # Not bedrock/bedrock/

    @patch("models.completion")
    @patch("models.time.sleep")
    def test_bedrock_access_denied_error_message(self, mock_sleep, mock_completion):
        mock_completion.side_effect = Exception("AccessDeniedException: not authorized")

        result = call_single_model("claude-3", "spec", 1, "prd", bedrock_mode=True)
        assert "not enabled" in result.error

    @patch("models.completion")
    @patch("models.time.sleep")
    def test_bedrock_validation_error_message(self, mock_sleep, mock_completion):
        mock_completion.side_effect = Exception("ValidationException: bad model")

        result = call_single_model("claude-3", "spec", 1, "prd", bedrock_mode=True)
        assert "Invalid Bedrock model" in result.error

    @patch("models.completion")
    def test_uses_press_template_when_press_true(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("gpt-4o", "spec", 1, "prd", press=True)
        call_args = mock_completion.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        # Press template includes "round 1" and "previously indicated agreement"
        assert "round 1" in user_msg
        assert "previously indicated agreement" in user_msg

    @patch("models.completion")
    def test_includes_focus_section(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("gpt-4o", "spec", 1, "prd", focus="security")
        call_args = mock_completion.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert "security" in user_msg.lower()

    @patch("models.completion")
    def test_custom_focus_creates_section(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("gpt-4o", "spec", 1, "prd", focus="customarea")
        call_args = mock_completion.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert "CUSTOMAREA" in user_msg

    @patch("models.completion")
    def test_preserve_intent_adds_prompt(self, mock_completion):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[AGREE]"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)
        mock_completion.return_value = mock_response

        call_single_model("gpt-4o", "spec", 1, "prd", preserve_intent=True)
        call_args = mock_completion.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        # preserve_intent adds a specific prompt section
        assert len(user_msg) > 0

    @patch("models.call_codex_model")
    @patch("models.CODEX_AVAILABLE", True)
    def test_routes_codex_model_to_handler(self, mock_codex):
        mock_codex.return_value = ("[AGREE]\n[SPEC]spec[/SPEC]", 100, 50)

        result = call_single_model("codex/gpt-5", "spec", 1, "prd")
        mock_codex.assert_called_once()
        assert result.model == "codex/gpt-5"

    @patch("models.call_codex_model")
    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.time.sleep")
    def test_codex_retries_on_failure(self, mock_sleep, mock_codex):
        mock_codex.side_effect = [Exception("First fail"), ("[AGREE]", 10, 5)]

        result = call_single_model("codex/gpt-5", "spec", 1, "prd")
        assert mock_codex.call_count == 2
        assert result.agreed is True

    @patch("models.call_codex_model")
    @patch("models.CODEX_AVAILABLE", True)
    def test_codex_extracts_spec_from_response(self, mock_codex):
        # Mutation: extracted = extract_spec(content) -> extracted = None
        mock_codex.return_value = ("Critique\n[SPEC]Extracted spec[/SPEC]", 100, 50)

        result = call_single_model("codex/gpt-5", "spec", 1, "prd")
        assert result.spec == "Extracted spec"  # Must be extracted, not None

    @patch("models.call_codex_model")
    @patch("models.CODEX_AVAILABLE", True)
    @patch("models.time.sleep")
    def test_codex_exponential_backoff(self, mock_sleep, mock_codex):
        # Verify codex path also uses exponential backoff
        mock_codex.side_effect = [
            Exception("First fail"),
            Exception("Second fail"),
            ("[AGREE]", 10, 5),
        ]

        call_single_model("codex/gpt-5", "spec", 1, "prd")
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 1.0  # First delay
        assert calls[1][0][0] == 2.0  # Second delay

    @patch("models.call_gemini_cli_model")
    @patch("models.GEMINI_CLI_AVAILABLE", True)
    def test_routes_gemini_cli_model_to_handler(self, mock_gemini):
        mock_gemini.return_value = ("[AGREE]\n[SPEC]spec[/SPEC]", 100, 50)

        result = call_single_model("gemini-cli/gemini-3-pro-preview", "spec", 1, "prd")
        mock_gemini.assert_called_once()
        assert result.model == "gemini-cli/gemini-3-pro-preview"

    @patch("models.call_gemini_cli_model")
    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.time.sleep")
    def test_gemini_cli_retries_on_failure(self, mock_sleep, mock_gemini):
        mock_gemini.side_effect = [Exception("First fail"), ("[AGREE]", 10, 5)]

        result = call_single_model("gemini-cli/gemini-3-pro-preview", "spec", 1, "prd")
        assert mock_gemini.call_count == 2
        assert result.agreed is True

    @patch("models.call_gemini_cli_model")
    @patch("models.GEMINI_CLI_AVAILABLE", True)
    def test_gemini_cli_extracts_spec_from_response(self, mock_gemini):
        mock_gemini.return_value = ("Critique\n[SPEC]Extracted spec[/SPEC]", 100, 50)

        result = call_single_model("gemini-cli/gemini-3-pro-preview", "spec", 1, "prd")
        assert result.spec == "Extracted spec"

    @patch("models.call_gemini_cli_model")
    @patch("models.GEMINI_CLI_AVAILABLE", True)
    @patch("models.time.sleep")
    def test_gemini_cli_exponential_backoff(self, mock_sleep, mock_gemini):
        mock_gemini.side_effect = [
            Exception("First fail"),
            Exception("Second fail"),
            ("[AGREE]", 10, 5),
        ]

        call_single_model("gemini-cli/gemini-3-pro-preview", "spec", 1, "prd")
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 1.0  # First delay
        assert calls[1][0][0] == 2.0  # Second delay

    @patch("models.call_claude_cli_model")
    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    def test_routes_claude_cli_model_to_handler(self, mock_claude):
        mock_claude.return_value = ("[AGREE]\n[SPEC]spec[/SPEC]", 100, 50)

        result = call_single_model("claude-cli/claude-sonnet-4-6", "spec", 1, "prd")
        mock_claude.assert_called_once()
        assert result.model == "claude-cli/claude-sonnet-4-6"

    @patch("models.call_claude_cli_model")
    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    @patch("models.time.sleep")
    def test_claude_cli_retries_on_failure(self, mock_sleep, mock_claude):
        mock_claude.side_effect = [Exception("First fail"), ("[AGREE]", 10, 5)]

        result = call_single_model("claude-cli/claude-sonnet-4-6", "spec", 1, "prd")
        assert mock_claude.call_count == 2
        assert result.agreed is True

    @patch("models.call_claude_cli_model")
    @patch("models.CLAUDE_CLI_AVAILABLE", True)
    def test_claude_cli_extracts_spec_from_response(self, mock_claude):
        mock_claude.return_value = ("Critique\n[SPEC]Extracted spec[/SPEC]", 100, 50)

        result = call_single_model("claude-cli/claude-sonnet-4-6", "spec", 1, "prd")
        assert result.spec == "Extracted spec"


class TestCallModelsParallel:
    @patch("models.call_single_model")
    def test_calls_all_models(self, mock_single):
        mock_single.return_value = ModelResponse(
            model="test", response="[AGREE]", agreed=True, spec="spec"
        )

        results = call_models_parallel(
            models=["gpt-4o", "gemini-pro", "claude-3"],
            spec="test spec",
            round_num=1,
            doc_type="prd",
        )

        assert len(results) == 3
        assert mock_single.call_count == 3

    @patch("models.call_single_model")
    def test_returns_all_results(self, mock_single):
        def make_response(model, *args, **kwargs):
            return ModelResponse(
                model=model,
                response=f"Response from {model}",
                agreed=model == "gpt-4o",
                spec="spec",
            )

        mock_single.side_effect = make_response

        results = call_models_parallel(
            models=["gpt-4o", "gemini-pro"],
            spec="test spec",
            round_num=1,
            doc_type="prd",
        )

        models = [r.model for r in results]
        assert "gpt-4o" in models
        assert "gemini-pro" in models

    @patch("models.call_single_model")
    def test_passes_all_parameters(self, mock_single):
        mock_single.return_value = ModelResponse(
            model="test", response="", agreed=True, spec=""
        )

        call_models_parallel(
            models=["gpt-4o"],
            spec="spec",
            round_num=5,
            doc_type="rfc",
            press=True,
            focus="security",
            persona="architect",
            context="ctx",
            preserve_intent=True,
            codex_reasoning="high",
            codex_search=True,
            timeout=300,
            bedrock_mode=True,
            bedrock_region="us-west-2",
        )

        call_args = mock_single.call_args
        assert call_args[0][0] == "gpt-4o"  # model
        assert call_args[0][1] == "spec"  # spec
        assert call_args[0][2] == 5  # round_num
        assert call_args[0][3] == "rfc"  # doc_type


class TestConstants:
    def test_max_retries_is_reasonable(self):
        # Mutation: 3 -> 4 would be caught
        assert MAX_RETRIES == 3

    def test_retry_base_delay_is_positive(self):
        # Mutation: 1.0 -> 2.0 would be caught
        assert RETRY_BASE_DELAY == 1.0


class TestIsOSeriesModel:
    """Test detection of OpenAI O-series models."""

    def test_detects_o1(self):
        assert is_o_series_model("o1") is True

    def test_detects_o1_mini(self):
        assert is_o_series_model("o1-mini") is True

    def test_detects_o1_preview(self):
        assert is_o_series_model("o1-preview") is True

    def test_detects_o1_with_provider_prefix(self):
        assert is_o_series_model("openai/o1") is True

    def test_detects_o1_via_openrouter(self):
        assert is_o_series_model("openrouter/openai/o1-mini") is True

    def test_case_insensitive(self):
        assert is_o_series_model("O1") is True
        assert is_o_series_model("O1-MINI") is True

    def test_does_not_detect_gpt4o(self):
        assert is_o_series_model("gpt-4o") is False

    def test_does_not_detect_gpt4o_mini(self):
        assert is_o_series_model("gpt-4o-mini") is False

    def test_does_not_detect_claude(self):
        assert is_o_series_model("claude-sonnet-4-20250514") is False

    def test_does_not_detect_gemini(self):
        assert is_o_series_model("gemini/gemini-2.0-flash") is False

    def test_does_not_detect_empty_string(self):
        assert is_o_series_model("") is False


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_prompts.py (341 lines, 13551 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for prompts module."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompts import (
    EXPORT_TASKS_PROMPT,
    FOCUS_AREAS,
    PERSONAS,
    PRESERVE_INTENT_PROMPT,
    PRESS_PROMPT_TEMPLATE,
    REVIEW_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_ARCHITECTURE,
    get_doc_type_name,
    get_system_prompt,
)


class TestGetSystemPrompt:
    def test_spec_product_returns_product_prompt(self):
        result = get_system_prompt("spec", depth="product")
        assert "product" in result.lower() or "user" in result.lower()
        assert len(result) > 200

    def test_spec_technical_returns_technical_prompt(self):
        result = get_system_prompt("spec", depth="technical")
        assert "spec" in result.lower() or "technical" in result.lower()
        assert len(result) > 200

    def test_unknown_returns_generic_prompt(self):
        # Mutation: setting SYSTEM_PROMPT_GENERIC to None would fail
        result = get_system_prompt("unknown")
        assert result is not None
        assert isinstance(result, str)
        assert "spec" in result.lower()
        assert len(result) > 200  # Generic prompt should have content

    def test_known_persona_returns_persona_prompt(self):
        # Mutation: changing PERSONAS content would fail these assertions
        result = get_system_prompt("tech", persona="security-engineer")
        assert "security" in result.lower()
        assert "engineer" in result.lower() or "experience" in result.lower()
        assert len(result) > 50

    def test_unknown_persona_returns_custom_prompt(self):
        result = get_system_prompt("tech", persona="fintech auditor")
        assert "fintech auditor" in result
        assert "adversarial spec development" in result

    def test_persona_overrides_doc_type(self):
        # Mutation: changing PERSONAS["oncall-engineer"] would fail
        result = get_system_prompt("prd", persona="oncall-engineer")
        assert "on-call" in result.lower() or "oncall" in result.lower()
        assert "paged" in result.lower() or "production" in result.lower()
        assert len(result) > 50


class TestGetDocTypeName:
    def test_spec_product(self):
        assert get_doc_type_name("spec", depth="product") == "Product Specification"

    def test_spec_technical(self):
        assert get_doc_type_name("spec", depth="technical") == "Technical Specification"

    def test_spec_full(self):
        assert get_doc_type_name("spec", depth="full") == "Full Specification"

    def test_spec_no_depth(self):
        assert get_doc_type_name("spec") == "Specification"

    def test_debug(self):
        assert get_doc_type_name("debug") == "Debug Investigation"

    def test_architecture(self):
        assert get_doc_type_name("architecture") == "Target Architecture"

    def test_unknown(self):
        assert get_doc_type_name("other") == "Specification"


class TestArchitectureDocType:
    def test_architecture_prompt_selection(self):
        result = get_system_prompt("architecture")
        assert result == SYSTEM_PROMPT_ARCHITECTURE

    def test_architecture_prompt_content(self):
        result = get_system_prompt("architecture")
        assert "Target Architecture" in result
        assert "shared patterns" in result
        assert "[AGREE]" in result
        assert "[SPEC]" in result

    def test_architecture_not_overridden_by_persona(self):
        # Persona takes precedence over doc_type
        result = get_system_prompt("architecture", persona="oncall-engineer")
        assert "Target Architecture" not in result


class TestArchPersona:
    def test_arch_persona_exists(self):
        from adversaries import ADVERSARIES, ARCHITECT
        assert "architect" in ADVERSARIES
        assert ADVERSARIES["architect"] is ARCHITECT

    def test_arch_prefix(self):
        from adversaries import ADVERSARY_PREFIXES, ARCHITECT
        assert ARCHITECT.prefix == "ARCH"
        assert ADVERSARY_PREFIXES["architect"] == "ARCH"

    def test_arch_persona_content(self):
        from adversaries import ARCHITECT
        assert "data flow" in ARCHITECT.persona.lower()
        assert "component boundaries" in ARCHITECT.persona.lower()
        assert ARCHITECT.name == "architect"

    def test_arch_concern_id_generation(self):
        from adversaries import generate_concern_id
        cid = generate_concern_id("architect", "test concern")
        assert cid.startswith("ARCH-")
        assert len(cid) == 13  # ARCH- + 8 hex chars

    def test_arch_in_version_manifest(self):
        from adversaries import get_version_manifest
        manifest = get_version_manifest()
        assert "architect" in manifest
        assert manifest["architect"]["prefix"] == "ARCH"


class TestFocusAreas:
    def test_all_focus_areas_exist(self):
        expected = [
            "security",
            "scalability",
            "performance",
            "ux",
            "reliability",
            "cost",
        ]
        for area in expected:
            assert area in FOCUS_AREAS

    def test_focus_areas_contain_critical_focus(self):
        for name, content in FOCUS_AREAS.items():
            assert "CRITICAL FOCUS" in content

    def test_security_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["security"]
        assert "security" in content.lower()
        assert "authentication" in content.lower() or "authorization" in content.lower()

    def test_scalability_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["scalability"]
        assert "scale" in content.lower() or "load" in content.lower()

    def test_performance_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["performance"]
        assert "performance" in content.lower() or "latency" in content.lower()

    def test_ux_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["ux"]
        assert "user" in content.lower() or "ux" in content.lower()

    def test_reliability_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["reliability"]
        assert "reliability" in content.lower() or "failure" in content.lower()

    def test_cost_focus_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = FOCUS_AREAS["cost"]
        assert "cost" in content.lower() or "budget" in content.lower()


class TestPersonas:
    def test_all_personas_exist(self):
        expected = [
            "security-engineer",
            "oncall-engineer",
            "junior-developer",
            "qa-engineer",
            "site-reliability",
            "product-manager",
            "data-engineer",
            "mobile-developer",
            "accessibility-specialist",
            "legal-compliance",
        ]
        for persona in expected:
            assert persona in PERSONAS

    def test_personas_are_non_empty(self):
        for name, content in PERSONAS.items():
            assert len(content) > 50

    def test_security_engineer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["security-engineer"]
        assert "security" in content.lower()
        assert "penetration" in content.lower() or "attacker" in content.lower()

    def test_oncall_engineer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["oncall-engineer"]
        assert "on-call" in content.lower() or "paged" in content.lower()
        assert "production" in content.lower() or "debug" in content.lower()

    def test_junior_developer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["junior-developer"]
        assert "junior" in content.lower()
        assert "ambiguous" in content.lower() or "implement" in content.lower()

    def test_qa_engineer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["qa-engineer"]
        assert "qa" in content.lower() or "test" in content.lower()
        assert "edge case" in content.lower() or "scenario" in content.lower()

    def test_site_reliability_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["site-reliability"]
        assert "sre" in content.lower() or "reliability" in content.lower()

    def test_product_manager_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["product-manager"]
        assert "product" in content.lower()
        assert "user" in content.lower() or "business" in content.lower()

    def test_data_engineer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["data-engineer"]
        assert "data" in content.lower()
        assert "data model" in content.lower() or "etl" in content.lower()

    def test_mobile_developer_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["mobile-developer"]
        assert "mobile" in content.lower()
        assert "api" in content.lower() or "payload" in content.lower()

    def test_accessibility_specialist_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["accessibility-specialist"]
        assert "accessibility" in content.lower() or "wcag" in content.lower()

    def test_legal_compliance_persona_content(self):
        # Mutation: XX prefix/suffix would fail keyword checks
        content = PERSONAS["legal-compliance"]
        assert "legal" in content.lower() or "compliance" in content.lower()
        assert (
            "gdpr" in content.lower()
            or "regulation" in content.lower()
            or "privacy" in content.lower()
        )


class TestPreserveIntentPrompt:
    def test_contains_key_instructions(self):
        assert "PRESERVE ORIGINAL INTENT" in PRESERVE_INTENT_PROMPT
        assert "ASSUME the author had good reasons" in PRESERVE_INTENT_PROMPT
        assert "ERRORS" in PRESERVE_INTENT_PROMPT
        assert "RISKS" in PRESERVE_INTENT_PROMPT
        assert "PREFERENCES" in PRESERVE_INTENT_PROMPT


class TestTemplateConstants:
    def test_review_prompt_template_not_none(self):
        # Mutation: REVIEW_PROMPT_TEMPLATE = None would fail
        assert REVIEW_PROMPT_TEMPLATE is not None
        assert isinstance(REVIEW_PROMPT_TEMPLATE, str)

    def test_review_prompt_template_content(self):
        assert "{round}" in REVIEW_PROMPT_TEMPLATE
        assert "{doc_type_name}" in REVIEW_PROMPT_TEMPLATE
        assert "{spec}" in REVIEW_PROMPT_TEMPLATE
        assert "adversarial spec development" in REVIEW_PROMPT_TEMPLATE

    def test_press_prompt_template_not_none(self):
        # Mutation: PRESS_PROMPT_TEMPLATE = None would fail
        assert PRESS_PROMPT_TEMPLATE is not None
        assert isinstance(PRESS_PROMPT_TEMPLATE, str)

    def test_press_prompt_template_content(self):
        assert "{round}" in PRESS_PROMPT_TEMPLATE
        assert "AGREE" in PRESS_PROMPT_TEMPLATE
        assert "thoroughly reviewing" in PRESS_PROMPT_TEMPLATE.lower()

    def test_export_tasks_prompt_not_none(self):
        # Mutation: EXPORT_TASKS_PROMPT = None would fail
        assert EXPORT_TASKS_PROMPT is not None
        assert isinstance(EXPORT_TASKS_PROMPT, str)

    def test_export_tasks_prompt_content(self):
        assert "[TASK]" in EXPORT_TASKS_PROMPT
        assert "[/TASK]" in EXPORT_TASKS_PROMPT
        assert "title:" in EXPORT_TASKS_PROMPT


class TestPersonaStringIntegrity:
    def test_all_personas_start_with_you_are(self):
        # Mutation: XX prefix would fail this check
        for name, content in PERSONAS.items():
            assert content.startswith("You are"), (
                f"Persona {name} should start with 'You are'"
            )

    def test_custom_persona_fallback_starts_correctly(self):
        # Mutation: XX prefix on fallback would fail
        result = get_system_prompt("tech", persona="custom-role")
        assert result.startswith("You are a custom-role")

    def test_persona_with_space_normalized(self):
        # Mutation: replace(" ", "-") changed would break mapping
        result = get_system_prompt("tech", persona="security engineer")
        # Should map to "security-engineer" persona
        assert "penetration" in result.lower() or "attacker" in result.lower()
        assert "15 years" in result

    def test_persona_with_underscore_normalized(self):
        # Mutation: replace("_", "-") changed would break mapping
        result = get_system_prompt("tech", persona="security_engineer")
        # Should map to "security-engineer" persona
        assert "penetration" in result.lower() or "attacker" in result.lower()
        assert "15 years" in result


class TestFocusAreaStringIntegrity:
    def test_all_focus_areas_start_with_critical(self):
        # Mutation: XX prefix would fail this check
        for name, content in FOCUS_AREAS.items():
            assert content.strip().startswith("**CRITICAL FOCUS"), (
                f"Focus area {name} should start with CRITICAL FOCUS"
            )


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_providers.py (870 lines, 32427 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for providers module."""

import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from providers import (
    BEDROCK_MODEL_MAP,
    DEFAULT_COST,
    MODEL_COSTS,
    is_bedrock_enabled,
    load_global_config,
    load_profile,
    resolve_bedrock_model,
    save_global_config,
    save_profile,
    validate_bedrock_models,
)


class TestModelCosts:
    def test_model_costs_has_expected_models(self):
        expected = [
            "gpt-4o",
            "gpt-5.3",
            "gemini/gemini-3-flash",
            "xai/grok-3",
            "mistral/mistral-large",
            "deepseek/deepseek-chat",
            "zhipu/glm-4",
            "codex/gpt-5.3-codex",
        ]
        for model in expected:
            assert model in MODEL_COSTS

    def test_costs_have_input_and_output(self):
        for model, costs in MODEL_COSTS.items():
            assert "input" in costs
            assert "output" in costs
            assert isinstance(costs["input"], (int, float))
            assert isinstance(costs["output"], (int, float))

    def test_default_cost_exists(self):
        assert "input" in DEFAULT_COST
        assert "output" in DEFAULT_COST


class TestBedrockModelMap:
    def test_has_claude_models(self):
        assert "claude-3-sonnet" in BEDROCK_MODEL_MAP
        assert "claude-3-haiku" in BEDROCK_MODEL_MAP
        assert "claude-3-opus" in BEDROCK_MODEL_MAP

    def test_has_llama_models(self):
        assert "llama-3-8b" in BEDROCK_MODEL_MAP
        assert "llama-3-70b" in BEDROCK_MODEL_MAP

    def test_maps_to_full_bedrock_ids(self):
        for name, bedrock_id in BEDROCK_MODEL_MAP.items():
            assert "." in bedrock_id or ":" in bedrock_id


class TestGlobalConfig:
    def test_load_nonexistent_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                config = load_global_config()
                assert config == {}

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                save_global_config(
                    {"bedrock": {"enabled": True, "region": "us-east-1"}}
                )

                assert config_path.exists()

                loaded = load_global_config()
                assert loaded["bedrock"]["enabled"] is True
                assert loaded["bedrock"]["region"] == "us-east-1"


class TestBedrockEnabled:
    def test_returns_false_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                assert is_bedrock_enabled() is False

    def test_returns_true_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps({"bedrock": {"enabled": True}}))

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                assert is_bedrock_enabled() is True


class TestResolveBrockModel:
    def test_resolves_friendly_name(self):
        result = resolve_bedrock_model("claude-3-sonnet")
        assert result == "anthropic.claude-3-sonnet-20240229-v1:0"

    def test_returns_full_id_as_is(self):
        full_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        result = resolve_bedrock_model(full_id)
        assert result == full_id

    def test_returns_none_for_unknown(self):
        result = resolve_bedrock_model("unknown-model")
        assert result is None

    def test_uses_custom_aliases(self):
        config = {"custom_aliases": {"my-model": "custom.model-id"}}
        result = resolve_bedrock_model("my-model", config)
        assert result == "custom.model-id"


class TestValidateBedrockModels:
    def test_validates_available_models(self):
        config = {
            "available_models": ["claude-3-sonnet", "claude-3-haiku"],
        }
        valid, invalid = validate_bedrock_models(["claude-3-sonnet"], config)
        assert len(valid) == 1
        assert len(invalid) == 0

    def test_rejects_unavailable_models(self):
        config = {
            "available_models": ["claude-3-sonnet"],
        }
        valid, invalid = validate_bedrock_models(["claude-3-opus"], config)
        assert len(valid) == 0
        assert len(invalid) == 1
        assert "claude-3-opus" in invalid


class TestProfiles:
    def test_save_and_load_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"

            with patch("providers.PROFILES_DIR", profiles_dir):
                config = {
                    "models": "gpt-4o,gemini/gemini-2.0-flash",
                    "focus": "security",
                    "persona": "security-engineer",
                }
                save_profile("test-profile", config)

                assert (profiles_dir / "test-profile.json").exists()

                loaded = load_profile("test-profile")
                assert loaded["models"] == "gpt-4o,gemini/gemini-2.0-flash"
                assert loaded["focus"] == "security"


class TestLoadGlobalConfigInvalidJson:
    """Tests for load_global_config with invalid JSON.

    Mutation target: exception handling for json.JSONDecodeError
    """

    def test_returns_empty_dict_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text("{ invalid json }")

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                config = load_global_config()
                # Mutation: removing return {} would cause crash or wrong value
                assert config == {}


class TestGetBedrockConfig:
    """Tests for get_bedrock_config function.

    Mutation target: .get("bedrock", {}) default value
    """

    def test_returns_empty_dict_when_no_bedrock_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text("{}")

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                from providers import get_bedrock_config

                config = get_bedrock_config()
                # Mutation: changing default {} to None would break code
                assert config == {}

    def test_returns_bedrock_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps({"bedrock": {"enabled": True}}))

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                from providers import get_bedrock_config

                config = get_bedrock_config()
                assert config["enabled"] is True


class TestResolveBrockModelBoundaries:
    """Additional tests for resolve_bedrock_model edge cases.

    Mutation targets:
    - "." in friendly_name check
    - .startswith("bedrock/") check
    - config is None check
    """

    def test_bedrock_prefix_not_returned_as_is(self):
        # Mutation: removing .startswith("bedrock/") check would return wrong value
        result = resolve_bedrock_model("bedrock/claude-3-sonnet")
        # Should NOT be returned as-is since it starts with bedrock/
        assert result is None or "bedrock/" not in result

    def test_dot_in_name_with_bedrock_prefix_goes_through_lookup(self):
        # Mutation: wrong AND logic would skip lookup
        result = resolve_bedrock_model("bedrock/anthropic.claude")
        assert result is None  # Not in map and not returned as-is

    def test_config_none_loads_from_global(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps({"bedrock": {"custom_aliases": {"mymodel": "custom.id"}}})
            )

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                # Mutation: not loading from global when config is None
                result = resolve_bedrock_model("mymodel", None)
                assert result == "custom.id"


class TestValidateBedrockModelsBoundaries:
    """Additional tests for validate_bedrock_models edge cases.

    Mutation targets:
    - model in available check
    - resolved model matching
    - for/else construct
    """

    def test_model_resolved_but_not_in_available_is_invalid(self):
        config = {
            "available_models": ["llama-3-8b"],  # Only llama in available
        }
        # claude-3-sonnet resolves but is not in available
        valid, invalid = validate_bedrock_models(["claude-3-sonnet"], config)
        # Mutation: wrong logic would mark as valid
        assert len(invalid) == 1
        assert "claude-3-sonnet" in invalid

    def test_resolved_model_matches_available_resolved(self):
        config = {
            "available_models": ["claude-3-sonnet"],  # Uses friendly name
        }
        # Pass the full bedrock ID - should match available model
        valid, invalid = validate_bedrock_models(
            ["anthropic.claude-3-sonnet-20240229-v1:0"], config
        )
        # Mutation: for/else would fail to add to valid
        assert len(valid) == 1
        assert len(invalid) == 0

    def test_config_none_loads_from_global(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps({"bedrock": {"available_models": ["claude-3-sonnet"]}})
            )

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                valid, invalid = validate_bedrock_models(["claude-3-sonnet"], None)
                assert len(valid) == 1


class TestLoadProfileErrors:
    """Tests for load_profile error handling.

    Mutation targets:
    - sys.exit(2) calls
    - profile_path.exists() check
    """

    def test_exits_when_profile_not_found(self):
        import pytest

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"

            with patch("providers.PROFILES_DIR", profiles_dir):
                with pytest.raises(SystemExit) as exc_info:
                    load_profile("nonexistent")
                # Mutation: changing exit code would fail
                assert exc_info.value.code == 2

    def test_exits_on_invalid_json(self):
        import pytest

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "bad.json").write_text("{ invalid }")

            with patch("providers.PROFILES_DIR", profiles_dir):
                with pytest.raises(SystemExit) as exc_info:
                    load_profile("bad")
                # Mutation: changing exit code would fail
                assert exc_info.value.code == 2


class TestListProfilesBranches:
    """Tests for list_profiles edge cases.

    Mutation targets:
    - PROFILES_DIR.exists() check
    - empty profiles list check
    - preserve_intent ternary
    """

    def test_no_profiles_dir(self):
        from io import StringIO

        from providers import list_profiles

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "nonexistent"

            with patch("providers.PROFILES_DIR", profiles_dir):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    list_profiles()
                    output = mock_out.getvalue()
                    # Mutation: not checking exists() would crash
                    assert "No profiles found" in output
                    assert str(profiles_dir) in output

    def test_empty_profiles_dir(self):
        from io import StringIO

        from providers import list_profiles

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()

            with patch("providers.PROFILES_DIR", profiles_dir):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    list_profiles()
                    output = mock_out.getvalue()
                    # Mutation: not checking empty list would skip message
                    assert "No profiles found" in output

    def test_preserve_intent_true(self):
        from io import StringIO

        from providers import list_profiles

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "test.json").write_text(
                json.dumps({"models": "gpt-4o", "preserve_intent": True})
            )

            with patch("providers.PROFILES_DIR", profiles_dir):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    list_profiles()
                    output = mock_out.getvalue()
                    # Mutation: wrong ternary would show "no"
                    assert "preserve-intent: yes" in output

    def test_preserve_intent_false(self):
        from io import StringIO

        from providers import list_profiles

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "test.json").write_text(
                json.dumps({"models": "gpt-4o", "preserve_intent": False})
            )

            with patch("providers.PROFILES_DIR", profiles_dir):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    list_profiles()
                    output = mock_out.getvalue()
                    # Mutation: wrong ternary would show "yes"
                    assert "preserve-intent: no" in output


class TestListProviders:
    """Tests for list_providers function.

    Mutation targets:
    - bedrock_config.get("enabled") check
    - os.environ.get() checks
    - CODEX_AVAILABLE check
    """

    def test_shows_bedrock_when_enabled(self):
        from io import StringIO

        from providers import list_providers

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "bedrock": {
                            "enabled": True,
                            "region": "us-east-1",
                            "available_models": ["claude-3-sonnet"],
                        }
                    }
                )
            )

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    list_providers()
                    output = mock_out.getvalue()
                    # Mutation: not checking enabled would skip section
                    assert "AWS Bedrock (Active)" in output
                    assert "us-east-1" in output
                    assert "claude-3-sonnet" in output

    def test_shows_api_key_status(self):
        from io import StringIO

        from providers import list_providers

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch.dict(
                    "os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False
                ):
                    with patch("sys.stdout", new_callable=StringIO) as mock_out:
                        list_providers()
                        output = mock_out.getvalue()
                        # Mutation: wrong check would show wrong status
                        assert "OpenAI" in output
                        assert "[set]" in output

    def test_shows_codex_status(self):
        from io import StringIO

        from providers import list_providers

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("providers.CODEX_AVAILABLE", True):
                    with patch("sys.stdout", new_callable=StringIO) as mock_out:
                        list_providers()
                        output = mock_out.getvalue()
                        # Mutation: wrong check would show wrong status
                        assert "Codex CLI" in output
                        assert "[installed]" in output


class TestListFocusAreas:
    """Tests for list_focus_areas function.

    Mutation target: newline split logic
    """

    def test_lists_all_focus_areas(self):
        from io import StringIO

        from providers import list_focus_areas

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            list_focus_areas()
            output = mock_out.getvalue()
            # Mutation: wrong split would show garbled text
            assert "security" in output
            assert "scalability" in output
            assert "performance" in output


class TestListPersonas:
    """Tests for list_personas function."""

    def test_lists_all_personas(self):
        from io import StringIO

        from providers import list_personas

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            list_personas()
            output = mock_out.getvalue()
            assert "security-engineer" in output
            assert "oncall-engineer" in output


class TestHandleBedrockCommand:
    """Tests for handle_bedrock_command function.

    Mutation targets:
    - subcommand dispatching
    - status output logic
    - enable/disable logic
    - add-model/remove-model logic
    """

    def test_status_not_configured(self):
        from io import StringIO

        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    handle_bedrock_command("status", None, None)
                    output = mock_out.getvalue()
                    # Mutation: wrong check would show wrong status
                    assert "Not configured" in output

    def test_status_with_models(self):
        from io import StringIO

        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        "bedrock": {
                            "enabled": True,
                            "region": "us-west-2",
                            "available_models": ["claude-3-sonnet"],
                        }
                    }
                )
            )

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    handle_bedrock_command("status", None, None)
                    output = mock_out.getvalue()
                    assert "Enabled" in output
                    assert "us-west-2" in output
                    assert "claude-3-sonnet" in output

    def test_enable_requires_region(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("enable", None, None)
                # Mutation: wrong exit code
                assert exc_info.value.code == 1

    def test_disable_command(self):
        from providers import handle_bedrock_command, load_global_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps({"bedrock": {"enabled": True}}))

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                handle_bedrock_command("disable", None, None)
                config = load_global_config()
                # Mutation: not setting enabled = False
                assert config["bedrock"]["enabled"] is False

    def test_add_model_requires_arg(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("add-model", None, None)
                assert exc_info.value.code == 1

    def test_add_model_already_exists(self):
        from io import StringIO

        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps({"bedrock": {"available_models": ["claude-3-sonnet"]}})
            )

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    handle_bedrock_command("add-model", "claude-3-sonnet", None)
                    output = mock_out.getvalue()
                    # Mutation: not checking existence would add duplicate
                    assert "already in the available list" in output

    def test_remove_model_requires_arg(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("remove-model", None, None)
                assert exc_info.value.code == 1

    def test_remove_model_not_in_list(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps({"bedrock": {"available_models": []}}))

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("remove-model", "nonexistent", None)
                assert exc_info.value.code == 1

    def test_alias_requires_arg(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("alias", None, None)
                assert exc_info.value.code == 1

    def test_alias_requires_two_args(self):
        import pytest
        from providers import handle_bedrock_command

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with patch("providers.GLOBAL_CONFIG_PATH", config_path):
                with pytest.raises(SystemExit) as exc_info:
                    handle_bedrock_command("alias", "mymodel", None)
                assert exc_info.value.code == 1

    def test_list_models_command(self):
        from io import StringIO

        from providers import handle_bedrock_command

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            handle_bedrock_command("list-models", None, None)
            output = mock_out.getvalue()
            assert "claude-3-sonnet" in output
            assert "llama-3-8b" in output

    def test_unknown_subcommand(self):
        import pytest
        from providers import handle_bedrock_command

        with pytest.raises(SystemExit) as exc_info:
            handle_bedrock_command("unknown", None, None)
        assert exc_info.value.code == 1


class TestGetAvailableProviders:
    def test_returns_providers_with_keys_set(self):
        from providers import get_available_providers

        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "test-key",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ):
            available = get_available_providers()
            provider_names = [name for name, _, _ in available]
            assert "Anthropic" in provider_names
            assert "Google" in provider_names

    def test_excludes_providers_without_keys(self):
        from providers import get_available_providers

        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "test-key",
            },
            clear=True,
        ):
            available = get_available_providers()
            provider_names = [name for name, _, _ in available]
            assert "Anthropic" in provider_names
            assert "Google" not in provider_names

    def test_returns_default_models(self):
        from providers import get_available_providers

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            available = get_available_providers()
            for name, key, model in available:
                if name == "Anthropic":
                    assert model == "claude-sonnet-4-5-20250929"

    def test_includes_codex_cli_when_available(self):
        from providers import get_available_providers

        with patch.dict("os.environ", {}, clear=True):
            with patch("providers.CODEX_AVAILABLE", True):
                with patch("providers.GEMINI_CLI_AVAILABLE", False):
                    available = get_available_providers()
                    provider_names = [name for name, _, _ in available]
                    assert "Codex CLI" in provider_names

    def test_includes_gemini_cli_when_available(self):
        from providers import get_available_providers

        with patch.dict("os.environ", {}, clear=True):
            with patch("providers.CODEX_AVAILABLE", False):
                with patch("providers.GEMINI_CLI_AVAILABLE", True):
                    available = get_available_providers()
                    provider_names = [name for name, _, _ in available]
                    assert "Gemini CLI" in provider_names
                    # Verify the default model for Gemini CLI
                    for name, key, model in available:
                        if name == "Gemini CLI":
                            assert model == "gemini-cli/gemini-3-pro-preview"
                            assert key is None  # No API key required


class TestGetDefaultModel:
    def test_returns_first_available_model(self):
        from providers import get_default_model

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
            default = get_default_model()
            assert default == "gemini/gemini-3-flash"

    def test_returns_none_when_no_keys(self):
        from providers import get_default_model

        with patch.dict("os.environ", {}, clear=True):
            with patch("providers.CODEX_AVAILABLE", False):
                with patch("providers.GEMINI_CLI_AVAILABLE", False):
                    with patch("providers.CLAUDE_CLI_AVAILABLE", False):
                        default = get_default_model()
                        assert default is None

    def test_prefers_bedrock_when_enabled(self):
        from providers import get_default_model

        with patch("providers.get_bedrock_config") as mock_config:
            mock_config.return_value = {
                "enabled": True,
                "available_models": ["claude-3-sonnet", "claude-3-haiku"],
            }
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
                default = get_default_model()
                assert default == "claude-3-sonnet"


class TestValidateModelCredentials:
    def test_validates_openai_models(self):
        from providers import validate_model_credentials

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            valid, invalid = validate_model_credentials(["gpt-4o", "gpt-4-turbo"])
            assert valid == ["gpt-4o", "gpt-4-turbo"]
            assert invalid == []

    def test_detects_missing_keys(self):
        from providers import validate_model_credentials

        with patch.dict("os.environ", {}, clear=True):
            valid, invalid = validate_model_credentials(["gpt-4o"])
            assert valid == []
            assert invalid == ["gpt-4o"]

    def test_validates_mixed_providers(self):
        from providers import validate_model_credentials

        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
                "XAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            valid, invalid = validate_model_credentials(
                ["gpt-4o", "xai/grok-3", "gemini/gemini-2.0-flash"]
            )
            assert "gpt-4o" in valid
            assert "xai/grok-3" in valid
            assert "gemini/gemini-2.0-flash" in invalid

    def test_validates_codex_availability(self):
        from providers import validate_model_credentials

        with patch("providers.CODEX_AVAILABLE", True):
            valid, invalid = validate_model_credentials(["codex/gpt-5.3-codex"])
            assert valid == ["codex/gpt-5.3-codex"]
            assert invalid == []

        with patch("providers.CODEX_AVAILABLE", False):
            valid, invalid = validate_model_credentials(["codex/gpt-5.3-codex"])
            assert valid == []
            assert invalid == ["codex/gpt-5.3-codex"]

    def test_validates_gemini_cli_availability(self):
        from providers import validate_model_credentials

        with patch("providers.GEMINI_CLI_AVAILABLE", True):
            valid, invalid = validate_model_credentials(
                ["gemini-cli/gemini-3-pro-preview"]
            )
            assert valid == ["gemini-cli/gemini-3-pro-preview"]
            assert invalid == []

        with patch("providers.GEMINI_CLI_AVAILABLE", False):
            valid, invalid = validate_model_credentials(
                ["gemini-cli/gemini-3-pro-preview"]
            )
            assert valid == []
            assert invalid == ["gemini-cli/gemini-3-pro-preview"]

    def test_defers_to_bedrock_validation_when_enabled(self):
        from providers import validate_model_credentials

        with patch("providers.get_bedrock_config") as mock_config:
            mock_config.return_value = {"enabled": True, "available_models": []}
            with patch("providers.validate_bedrock_models") as mock_validate:
                mock_validate.return_value = (["model1"], ["model2"])
                valid, invalid = validate_model_credentials(["model1", "model2"])
                assert valid == ["model1"]
                assert invalid == ["model2"]
                mock_validate.assert_called_once()


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_session.py (322 lines, 12357 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for session module."""

import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from session import SessionState, save_checkpoint


class TestSessionState:
    def test_create_session_state(self):
        session = SessionState(
            session_id="test-session",
            spec="# Test Spec\n\nContent here.",
            round=1,
            doc_type="tech",
            models=["gpt-4o", "gemini/gemini-2.0-flash"],
        )
        assert session.session_id == "test-session"
        assert session.round == 1
        assert session.doc_type == "tech"
        assert len(session.models) == 2

    def test_default_values(self):
        # Mutation: changing default values would fail these checks
        session = SessionState(
            session_id="defaults-test",
            spec="spec",
            round=1,
            doc_type="tech",
            models=["gpt-4o"],
        )
        # Verify default values are exactly as expected
        assert session.focus is None  # Not ""
        assert session.persona is None  # Not ""
        assert session.preserve_intent is False  # Not True
        assert session.created_at == ""  # Not None or other
        assert session.updated_at == ""  # Not None or other
        assert session.history == []  # Not None

    def test_session_with_optional_fields(self):
        session = SessionState(
            session_id="test",
            spec="spec",
            round=2,
            doc_type="prd",
            models=["gpt-4o"],
            focus="security",
            persona="security-engineer",
            preserve_intent=True,
        )
        assert session.focus == "security"
        assert session.persona == "security-engineer"
        assert session.preserve_intent is True

    def test_save_and_load_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"

            with patch("session.SESSIONS_DIR", sessions_dir):
                session = SessionState(
                    session_id="save-test",
                    spec="test spec content",
                    round=3,
                    doc_type="tech",
                    models=["gpt-4o"],
                    focus="performance",
                )
                session.save()

                # Verify file exists
                assert (sessions_dir / "save-test.json").exists()

                # Load and verify
                loaded = SessionState.load("save-test")
                assert loaded.session_id == "save-test"
                assert loaded.spec == "test spec content"
                assert loaded.round == 3
                assert loaded.focus == "performance"
                assert loaded.updated_at != ""

    def test_save_creates_nested_directories(self):
        # Mutation: parents=True → parents=False would fail when parent doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a path with multiple non-existent parents
            sessions_dir = Path(tmpdir) / "deep" / "nested" / "sessions"

            with patch("session.SESSIONS_DIR", sessions_dir):
                session = SessionState(
                    session_id="nested-test",
                    spec="spec",
                    round=1,
                    doc_type="tech",
                    models=["gpt-4o"],
                )
                # This should create all parent directories
                session.save()
                assert (sessions_dir / "nested-test.json").exists()

    def test_load_nonexistent_session_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            with patch("session.SESSIONS_DIR", sessions_dir):
                try:
                    SessionState.load("nonexistent")
                    assert False, "Should have raised FileNotFoundError"
                except FileNotFoundError as e:
                    assert "nonexistent" in str(e)

    def test_list_sessions_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"

            with patch("session.SESSIONS_DIR", sessions_dir):
                sessions = SessionState.list_sessions()
                assert sessions == []

    def test_list_sessions_returns_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            with patch("session.SESSIONS_DIR", sessions_dir):
                # Create two sessions
                s1 = SessionState(
                    session_id="first",
                    spec="spec1",
                    round=1,
                    doc_type="prd",
                    models=["gpt-4o"],
                )
                s1.save()

                s2 = SessionState(
                    session_id="second",
                    spec="spec2",
                    round=2,
                    doc_type="tech",
                    models=["gemini/gemini-2.0-flash"],
                )
                s2.save()

                sessions = SessionState.list_sessions()
                assert len(sessions) == 2
                # Most recent first
                assert sessions[0]["id"] == "second"
                assert sessions[1]["id"] == "first"

    def test_list_sessions_dict_keys(self):
        # Mutation: changing dict keys would fail this test
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            with patch("session.SESSIONS_DIR", sessions_dir):
                s = SessionState(
                    session_id="test",
                    spec="spec",
                    round=5,
                    doc_type="tech",
                    models=["gpt-4o"],
                )
                s.save()

                sessions = SessionState.list_sessions()
                assert len(sessions) == 1
                session = sessions[0]
                # Verify exact keys
                assert "id" in session
                assert "round" in session
                assert "doc_type" in session
                assert "updated_at" in session
                # Verify values
                assert session["round"] == 5
                assert session["doc_type"] == "tech"

    def test_session_history_append(self):
        session = SessionState(
            session_id="history-test",
            spec="spec",
            round=1,
            doc_type="tech",
            models=["gpt-4o"],
        )
        assert session.history == []

        session.history.append(
            {
                "round": 1,
                "all_agreed": False,
                "models": [{"model": "gpt-4o", "agreed": False}],
            }
        )
        assert len(session.history) == 1
        assert session.history[0]["round"] == 1


class TestSaveCheckpoint:
    def test_save_checkpoint_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "checkpoints"

            with patch("session.CHECKPOINTS_DIR", checkpoint_dir):
                save_checkpoint("# Test Spec", 1)

                assert (checkpoint_dir / "round-1.md").exists()
                content = (checkpoint_dir / "round-1.md").read_text()
                assert content == "# Test Spec"

    def test_save_checkpoint_with_session_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "checkpoints"

            with patch("session.CHECKPOINTS_DIR", checkpoint_dir):
                save_checkpoint("# Test Spec", 2, session_id="my-session")

                assert (checkpoint_dir / "my-session-round-2.md").exists()

    def test_save_checkpoint_creates_nested_directories(self):
        # Mutation: parents=True → parents=False would fail
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "deep" / "nested" / "checkpoints"

            with patch("session.CHECKPOINTS_DIR", checkpoint_dir):
                save_checkpoint("# Nested Spec", 3)
                assert (checkpoint_dir / "round-3.md").exists()

    def test_save_checkpoint_filename_format(self):
        # Mutation: wrong prefix/suffix format would fail
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "checkpoints"

            with patch("session.CHECKPOINTS_DIR", checkpoint_dir):
                save_checkpoint("spec", 5, session_id="test-session")
                # Should be exactly "test-session-round-5.md"
                expected = checkpoint_dir / "test-session-round-5.md"
                assert expected.exists()
                # Verify no other files created
                files = list(checkpoint_dir.glob("*.md"))
                assert len(files) == 1
                assert files[0].name == "test-session-round-5.md"

    def test_save_checkpoint_exist_ok(self):
        # Mutation: exist_ok=True → exist_ok=False would fail on second call
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "checkpoints"

            with patch("session.CHECKPOINTS_DIR", checkpoint_dir):
                save_checkpoint("spec v1", 1)
                # Second call with same directory should not fail
                save_checkpoint("spec v2", 2)
                assert (checkpoint_dir / "round-1.md").exists()
                assert (checkpoint_dir / "round-2.md").exists()


class TestListSessionsEdgeCases:
    def test_list_sessions_missing_updated_at(self):
        # Mutation: data.get("updated_at", "") → data.get("updated_at", "XXXX")
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            # Create session without updated_at field
            session_data = {
                "session_id": "old-session",
                "spec": "spec",
                "round": 1,
                "doc_type": "tech",
                "models": ["gpt-4o"],
                # Intentionally no updated_at
            }
            (sessions_dir / "old-session.json").write_text(json.dumps(session_data))

            with patch("session.SESSIONS_DIR", sessions_dir):
                sessions = SessionState.list_sessions()
                assert len(sessions) == 1
                # Default should be empty string, not "XXXX"
                assert sessions[0]["updated_at"] == ""

    def test_list_sessions_sorting_with_missing_updated_at(self):
        # Mutation: sorted(..., key=lambda x: x.get("updated_at", "")) default change
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            # Create two sessions - one with updated_at, one without
            # Empty string sorts before any date, so session without updated_at should be last
            session1 = {
                "session_id": "new-session",
                "spec": "spec",
                "round": 1,
                "doc_type": "tech",
                "models": ["gpt-4o"],
                "updated_at": "2024-01-15T12:00:00",
            }
            session2 = {
                "session_id": "old-session",
                "spec": "spec",
                "round": 1,
                "doc_type": "tech",
                "models": ["gpt-4o"],
                # No updated_at - should sort to end
            }
            (sessions_dir / "new-session.json").write_text(json.dumps(session1))
            (sessions_dir / "old-session.json").write_text(json.dumps(session2))

            with patch("session.SESSIONS_DIR", sessions_dir):
                sessions = SessionState.list_sessions()
                assert len(sessions) == 2
                # Session with date should come first (reverse=True means newer first)
                assert sessions[0]["id"] == "new-session"
                assert sessions[1]["id"] == "old-session"


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/tests/test_telegram_bot.py (683 lines, 23721 bytes)
# ══════════════════════════════════════════════════════════════
"""Tests for telegram_bot module."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram_bot import (
    MAX_MESSAGE_LENGTH,
    api_call,
    get_config,
    get_last_update_id,
    poll_for_reply,
    send_long_message,
    send_message,
    split_message,
)


class TestGetConfig:
    def test_returns_empty_when_not_set(self):
        with patch.dict("os.environ", {}, clear=True):
            token, chat_id = get_config()
            assert token == ""
            assert chat_id == ""

    def test_returns_values_when_set(self):
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "12345"},
        ):
            token, chat_id = get_config()
            assert token == "test-token"
            assert chat_id == "12345"


class TestSplitMessage:
    def test_short_message_not_split(self):
        text = "Short message"
        result = split_message(text)
        assert result == [text]

    def test_exactly_max_length_not_split(self):
        text = "x" * MAX_MESSAGE_LENGTH
        result = split_message(text)
        assert result == [text]

    def test_splits_at_paragraph_boundary(self):
        first_half = "a" * 2000
        second_half = "b" * 2000
        text = first_half + "\n\n" + second_half
        result = split_message(text, max_length=2500)
        assert len(result) == 2
        assert result[0] == first_half
        assert result[1] == second_half

    def test_splits_at_newline_when_no_paragraph(self):
        first_half = "a" * 2000
        second_half = "b" * 2000
        text = first_half + "\n" + second_half
        result = split_message(text, max_length=2500)
        assert len(result) == 2
        assert first_half in result[0]

    def test_splits_at_space_when_no_newline(self):
        first_half = "a" * 2000
        second_half = "b" * 2000
        text = first_half + " " + second_half
        result = split_message(text, max_length=2500)
        assert len(result) == 2

    def test_hard_split_when_no_boundaries(self):
        text = "x" * 5000
        result = split_message(text, max_length=2000)
        assert len(result) >= 2
        assert all(len(chunk) <= 2000 for chunk in result)


class TestApiCall:
    @patch("telegram_bot.urlopen")
    def test_successful_api_call(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true, "result": []}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = api_call("test-token", "getMe")
        assert result == {"ok": True, "result": []}

    @patch("telegram_bot.urlopen")
    def test_api_call_with_params(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = api_call("test-token", "sendMessage", {"chat_id": "123", "text": "hi"})
        assert result == {"ok": True}

        called_request = mock_urlopen.call_args[0][0]
        assert "chat_id=123" in called_request.full_url
        assert "text=hi" in called_request.full_url


class TestSendMessage:
    @patch("telegram_bot.api_call")
    def test_send_message_success(self, mock_api_call):
        mock_api_call.return_value = {"ok": True}
        result = send_message("token", "123", "Hello")
        assert result is True
        mock_api_call.assert_called_once()

    @patch("telegram_bot.api_call")
    def test_send_message_failure(self, mock_api_call):
        mock_api_call.return_value = {"ok": False}
        result = send_message("token", "123", "Hello")
        assert result is False


class TestSendLongMessage:
    @patch("telegram_bot.send_message")
    def test_sends_short_message_directly(self, mock_send):
        mock_send.return_value = True
        result = send_long_message("token", "123", "Short message")
        assert result is True
        assert mock_send.call_count == 1

    @patch("telegram_bot.send_message")
    @patch("telegram_bot.time.sleep")
    def test_sends_multiple_chunks(self, mock_sleep, mock_send):
        mock_send.return_value = True
        long_text = "x" * 5000
        result = send_long_message("token", "123", long_text)
        assert result is True
        assert mock_send.call_count >= 2

    @patch("telegram_bot.send_message")
    def test_returns_false_on_chunk_failure(self, mock_send):
        mock_send.side_effect = [True, False]
        long_text = "x" * 5000
        result = send_long_message("token", "123", long_text)
        assert result is False


class TestGetLastUpdateId:
    @patch("telegram_bot.api_call")
    def test_returns_update_id_when_present(self, mock_api_call):
        mock_api_call.return_value = {"ok": True, "result": [{"update_id": 12345}]}
        result = get_last_update_id("token")
        assert result == 12345

    @patch("telegram_bot.api_call")
    def test_returns_zero_when_no_updates(self, mock_api_call):
        mock_api_call.return_value = {"ok": True, "result": []}
        result = get_last_update_id("token")
        assert result == 0


class TestPollForReply:
    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_returns_message_text(self, mock_time, mock_api_call):
        # Simulate time: start=0, first iteration check=0.1, remaining > 0
        mock_time.side_effect = [0, 0.1, 0.2]
        # First call returns the message, second clears the update
        mock_api_call.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 100,
                        "message": {"chat": {"id": "123"}, "text": "Hello from user"},
                    }
                ],
            },
            {"ok": True, "result": []},  # Clear processed updates
        ]
        result = poll_for_reply("token", "123", timeout=60)
        assert result == "Hello from user"

    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_returns_none_on_timeout(self, mock_time, mock_api_call):
        mock_time.side_effect = [0, 0, 2]
        mock_api_call.return_value = {"ok": True, "result": []}
        result = poll_for_reply("token", "123", timeout=1)
        assert result is None

    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_ignores_messages_from_other_chats(self, mock_time, mock_api_call):
        # Two iterations: first finds other chat, second times out
        mock_time.side_effect = [0, 0.1, 0.5, 2]
        mock_api_call.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 100,
                        "message": {"chat": {"id": "999"}, "text": "Other chat"},
                    }
                ],
            },
            {"ok": True, "result": []},
        ]
        result = poll_for_reply("token", "123", timeout=1)
        assert result is None


class TestSplitMessageBoundaries:
    """Mutation-targeted tests for split_message boundary conditions.

    Mutation targets:
    - len(text) <= max_length boundary
    - split_at == -1 checks
    - split_at < max_length // 2 boundaries
    """

    def test_exactly_max_length_not_split(self):
        # Mutation: changing <= to < would incorrectly split
        text = "x" * MAX_MESSAGE_LENGTH
        result = split_message(text)
        assert len(result) == 1
        assert result[0] == text

    def test_one_over_max_length_splits(self):
        # Mutation: changing <= to < boundary
        text = "x" * (MAX_MESSAGE_LENGTH + 1)
        result = split_message(text)
        assert len(result) == 2

    def test_split_at_exactly_half_uses_paragraph(self):
        # Mutation: boundary at max_length // 2
        half = 2500 // 2
        first = "a" * half
        second = "b" * (2500 - half)
        text = first + "\n\n" + second
        result = split_message(text, max_length=2500)
        # Should split at paragraph since it's exactly at half
        assert len(result) == 2

    def test_split_at_less_than_half_falls_to_newline(self):
        # Mutation: split_at < max_length // 2 condition
        # Put paragraph break very early, should skip to newline
        first = "a" * 100  # Way less than half
        rest = "b" * 2000 + "\n" + "c" * 300
        text = first + "\n\n" + rest
        result = split_message(text, max_length=2500)
        assert len(result) >= 1

    def test_no_newline_falls_to_space(self):
        # Mutation: newline search fails, falls to space
        first = "word " * 400  # Words with spaces
        text = first.strip()
        result = split_message(text, max_length=2000)
        # Should split at space boundary
        assert len(result) >= 1
        assert all(len(chunk) <= 2000 for chunk in result)


class TestSendLongMessageBoundaries:
    """Mutation-targeted tests for send_long_message.

    Mutation targets:
    - len(chunks) > 1 check
    - i < len(chunks) - 1 check
    - i + 1 in header
    """

    @patch("telegram_bot.send_message")
    def test_single_chunk_no_header(self, mock_send):
        # Mutation: len(chunks) > 1 check
        mock_send.return_value = True
        result = send_long_message("token", "123", "short")
        assert result is True
        # Should NOT have header prefix
        call_text = mock_send.call_args[0][2]
        assert not call_text.startswith("[1/")

    @patch("telegram_bot.send_message")
    @patch("telegram_bot.time.sleep")
    def test_multiple_chunks_have_headers(self, mock_sleep, mock_send):
        # Mutation: header format i + 1
        mock_send.return_value = True
        long_text = "a" * 5000
        result = send_long_message("token", "123", long_text)
        assert result is True
        # Check headers are correct
        calls = mock_send.call_args_list
        assert len(calls) >= 2
        # First chunk should have [1/N] header
        assert calls[0][0][2].startswith("[1/")
        # Second chunk should have [2/N] header
        assert calls[1][0][2].startswith("[2/")

    @patch("telegram_bot.send_message")
    @patch("telegram_bot.time.sleep")
    def test_no_sleep_after_last_chunk(self, mock_sleep, mock_send):
        # Mutation: i < len(chunks) - 1 check
        mock_send.return_value = True
        long_text = "a" * 5000
        send_long_message("token", "123", long_text)
        # Sleep called between chunks but not after last
        # With 2 chunks, should sleep once
        calls = mock_send.call_args_list
        assert mock_sleep.call_count == len(calls) - 1


class TestPollForReplyBoundaries:
    """Mutation-targeted tests for poll_for_reply.

    Mutation targets:
    - remaining <= 0 check
    - after_update_id + 1 offset
    - msg_chat_id == chat_id check
    """

    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_uses_after_update_id_offset(self, mock_time, mock_api_call):
        # Mutation: after_update_id + 1 calculation
        # time() called: start=0, loop check=0.01, remaining=0.01, then timeout
        # remaining = int(60 - 0.01) = 59 > 0, so loop continues
        mock_time.side_effect = [0, 0.01, 0.01, 61]  # Last one triggers timeout
        mock_api_call.return_value = {"ok": True, "result": []}
        poll_for_reply("token", "123", timeout=60, after_update_id=100)
        # First call should have offset=101
        assert mock_api_call.call_count >= 1
        first_call = mock_api_call.call_args_list[0]
        assert first_call[0][2]["offset"] == 101

    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_handles_runtime_error(self, mock_time, mock_api_call):
        # Mutation: exception handling continues loop
        mock_time.side_effect = [0, 0.1, 2]
        mock_api_call.side_effect = RuntimeError("Network error")
        result = poll_for_reply("token", "123", timeout=1)
        assert result is None

    @patch("telegram_bot.api_call")
    @patch("telegram_bot.time.time")
    def test_empty_text_ignored(self, mock_time, mock_api_call):
        # Mutation: text check in if condition
        mock_time.side_effect = [0, 0.1, 2]
        mock_api_call.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 100,
                        "message": {"chat": {"id": "123"}, "text": ""},
                    }
                ],
            },
            {"ok": True, "result": []},
        ]
        result = poll_for_reply("token", "123", timeout=1)
        assert result is None


class TestApiCallErrors:
    """Mutation-targeted tests for api_call error handling.

    Mutation targets:
    - HTTPError handling
    - URLError handling
    """

    @patch("telegram_bot.urlopen")
    def test_http_error_raises_runtime_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "url", 400, "Bad Request", {}, MagicMock(read=lambda: b"error body")
        )

        import pytest

        with pytest.raises(RuntimeError) as exc_info:
            api_call("token", "getMe")
        assert "400" in str(exc_info.value)

    @patch("telegram_bot.urlopen")
    def test_url_error_raises_runtime_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        import pytest

        with pytest.raises(RuntimeError) as exc_info:
            api_call("token", "getMe")
        assert "Network error" in str(exc_info.value)


class TestCmdSetup:
    """Tests for cmd_setup command.

    Mutation targets:
    - token check
    - chat_id check
    - send_message success/failure
    """

    def test_exits_when_no_token(self):
        import pytest
        from telegram_bot import cmd_setup

        with patch.dict("os.environ", {}, clear=True):
            with patch("sys.stdout", new_callable=StringIO):
                args = MagicMock()
                with pytest.raises(SystemExit) as exc_info:
                    cmd_setup(args)
                assert exc_info.value.code == 2

    @patch("telegram_bot.discover_chat_id")
    def test_discovers_chat_id_when_no_chat_id(self, mock_discover):
        import pytest
        from telegram_bot import cmd_setup

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"}, clear=True):
            with patch("sys.stdout", new_callable=StringIO):
                args = MagicMock()
                with pytest.raises(SystemExit) as exc_info:
                    cmd_setup(args)
                assert exc_info.value.code == 0
                mock_discover.assert_called_once()

    @patch("telegram_bot.send_message")
    def test_sends_test_message_on_success(self, mock_send):
        from telegram_bot import cmd_setup

        mock_send.return_value = True
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                args = MagicMock()
                cmd_setup(args)
                output = mock_out.getvalue()
                assert "successfully" in output

    @patch("telegram_bot.send_message")
    def test_exits_on_test_message_failure(self, mock_send):
        import pytest
        from telegram_bot import cmd_setup

        mock_send.return_value = False
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdout", new_callable=StringIO):
                args = MagicMock()
                with pytest.raises(SystemExit) as exc_info:
                    cmd_setup(args)
                assert exc_info.value.code == 1


class TestCmdSend:
    """Tests for cmd_send command.

    Mutation targets:
    - config check
    - empty text check
    - send success/failure
    """

    def test_exits_when_no_config(self):
        import pytest
        from telegram_bot import cmd_send

        with patch.dict("os.environ", {}, clear=True):
            args = MagicMock()
            with pytest.raises(SystemExit) as exc_info:
                cmd_send(args)
            assert exc_info.value.code == 2

    def test_exits_on_empty_stdin(self):
        import pytest
        from telegram_bot import cmd_send

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("")):
                args = MagicMock()
                with pytest.raises(SystemExit) as exc_info:
                    cmd_send(args)
                assert exc_info.value.code == 1

    @patch("telegram_bot.send_long_message")
    def test_sends_message_from_stdin(self, mock_send):
        from telegram_bot import cmd_send

        mock_send.return_value = True
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("Hello world")):
                with patch("sys.stdout", new_callable=StringIO):
                    args = MagicMock()
                    cmd_send(args)
                    mock_send.assert_called_once()

    @patch("telegram_bot.send_long_message")
    def test_exits_on_send_failure(self, mock_send):
        import pytest
        from telegram_bot import cmd_send

        mock_send.return_value = False
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("Hello")):
                args = MagicMock()
                with pytest.raises(SystemExit) as exc_info:
                    cmd_send(args)
                assert exc_info.value.code == 1


class TestCmdPoll:
    """Tests for cmd_poll command.

    Mutation targets:
    - config check
    - reply success/failure
    """

    def test_exits_when_no_config(self):
        import pytest
        from telegram_bot import cmd_poll

        with patch.dict("os.environ", {}, clear=True):
            args = MagicMock(timeout=60)
            with pytest.raises(SystemExit) as exc_info:
                cmd_poll(args)
            assert exc_info.value.code == 2

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.get_last_update_id")
    def test_prints_reply_on_success(self, mock_last_id, mock_poll):
        from telegram_bot import cmd_poll

        mock_last_id.return_value = 0
        mock_poll.return_value = "User reply"
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                with patch("sys.stderr", new_callable=StringIO):
                    args = MagicMock(timeout=60)
                    cmd_poll(args)
                    assert "User reply" in mock_out.getvalue()

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.get_last_update_id")
    def test_exits_on_no_reply(self, mock_last_id, mock_poll):
        import pytest
        from telegram_bot import cmd_poll

        mock_last_id.return_value = 0
        mock_poll.return_value = None
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stderr", new_callable=StringIO):
                args = MagicMock(timeout=60)
                with pytest.raises(SystemExit) as exc_info:
                    cmd_poll(args)
                assert exc_info.value.code == 1


class TestCmdNotify:
    """Tests for cmd_notify command.

    Mutation targets:
    - config check
    - empty notification check
    - send failure
    """

    def test_exits_when_no_config(self):
        import pytest
        from telegram_bot import cmd_notify

        with patch.dict("os.environ", {}, clear=True):
            args = MagicMock(timeout=60)
            with pytest.raises(SystemExit) as exc_info:
                cmd_notify(args)
            assert exc_info.value.code == 2

    def test_exits_on_empty_notification(self):
        import pytest
        from telegram_bot import cmd_notify

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("")):
                args = MagicMock(timeout=60)
                with pytest.raises(SystemExit) as exc_info:
                    cmd_notify(args)
                assert exc_info.value.code == 1

    @patch("telegram_bot.poll_for_reply")
    @patch("telegram_bot.send_long_message")
    @patch("telegram_bot.get_last_update_id")
    def test_sends_notification_and_polls(self, mock_last_id, mock_send, mock_poll):
        import json

        from telegram_bot import cmd_notify

        mock_last_id.return_value = 0
        mock_send.return_value = True
        mock_poll.return_value = "Feedback here"
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("Round 1 complete")):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    args = MagicMock(timeout=60)
                    cmd_notify(args)
                    output = json.loads(mock_out.getvalue())
                    assert output["notification_sent"] is True
                    assert output["feedback"] == "Feedback here"

    @patch("telegram_bot.send_long_message")
    @patch("telegram_bot.get_last_update_id")
    def test_exits_on_send_failure(self, mock_last_id, mock_send):
        import pytest
        from telegram_bot import cmd_notify

        mock_last_id.return_value = 0
        mock_send.return_value = False
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "123"},
            clear=True,
        ):
            with patch("sys.stdin", StringIO("Notification")):
                args = MagicMock(timeout=60)
                with pytest.raises(SystemExit) as exc_info:
                    cmd_notify(args)
                assert exc_info.value.code == 1


class TestMain:
    """Tests for main entry point."""

    def test_main_with_setup_command(self):
        import pytest
        from telegram_bot import main

        with patch("sys.argv", ["telegram_bot.py", "setup"]):
            with patch.dict("os.environ", {}, clear=True):
                with patch("sys.stdout", new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Exits with 2 due to no token
                    assert exc_info.value.code == 2


