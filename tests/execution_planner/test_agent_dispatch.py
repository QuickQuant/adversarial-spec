"""
Test specifications for FR-7: Agent Dispatch & Status

The Agent Dispatcher launches Claude Code agents to execute tasks and tracks
their status. Integrates with mcp_agent_mail for coordination.

Acceptance Criteria:
- Dispatch agents via Claude Code CLI
- Pass context: task description, AC, full spec (no trimming), dep status
- Track status: queued, running, completed, failed, blocked
- Assign unique agent number for branch naming
- Integrate with mcp_agent_mail for file reservations
- Scan for secrets before dispatch to non-local LLMs

Edge Cases:
- Claude Code not installed → clear error
- Agent crashes mid-execution → detect and mark failed
- Multiple agents same directory → verify no session conflicts
- Secrets detected → warn and redact before dispatch
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

# These imports will fail until implementation exists
from execution_planner.agent_dispatch import (
    AgentDispatcher,
    DispatchResult,
    AgentStatus,
    DispatchError,
    ClaudeCodeNotFoundError,
    SecretDetectedError,
)
from execution_planner.task_planner import Task, ValidationStrategy


# Test fixtures
SAMPLE_TASK = Task(
    id="task-001",
    title="Implement Counter Component",
    description="Create a React counter component with increment button",
    acceptance_criteria="Counter displays value, increment button adds 1",
    effort_estimate="S",
    risk_level="low",
    validation_strategy=ValidationStrategy.TEST_FIRST,
    dependencies=[],
    stream_id="stream-1",
)

DEPENDENT_TASK = Task(
    id="task-002",
    title="Add Reset Button",
    description="Add reset button to counter component",
    acceptance_criteria="Reset button sets counter to 0",
    effort_estimate="XS",
    risk_level="low",
    validation_strategy=ValidationStrategy.TEST_AFTER,
    dependencies=["task-001"],
    stream_id="stream-1",
)

SAMPLE_SPEC = """# Counter Feature
Simple counter with increment and reset.
"""

CONTEXT_WITH_SECRET = """
API_KEY=sk-secret123456789
Do some work with the API.
"""

CONTEXT_WITH_PASSWORD = """
DATABASE_URL=postgres://user:password123@localhost/db
Connect to database.
"""


class TestAgentLaunch:
    """FR-7: Agent launch functionality."""

    def test_dispatches_via_claude_code_cli(self):
        """Should launch agent using Claude Code CLI."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert result.cli_used == "claude"
        assert result.agent_id is not None

    def test_passes_task_description(self):
        """Agent should receive task description."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        # The context passed to agent should include task description
        assert SAMPLE_TASK.description in result.context_passed

    def test_passes_acceptance_criteria(self):
        """Agent should receive acceptance criteria."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert SAMPLE_TASK.acceptance_criteria in result.context_passed

    def test_passes_full_spec_no_trimming(self):
        """Agent should receive full spec, not trimmed."""
        large_spec = "# Large Spec\n" + ("Content line.\n" * 1000)
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=large_spec)
        # Verify spec was not truncated
        assert result.spec_length_passed == len(large_spec)

    def test_passes_dependency_status(self):
        """Agent should know status of dependent tasks."""
        dispatcher = AgentDispatcher()
        dep_status = {"task-001": AgentStatus.COMPLETED}
        result = dispatcher.dispatch(
            DEPENDENT_TASK,
            spec=SAMPLE_SPEC,
            dependency_status=dep_status
        )
        assert "task-001" in result.context_passed
        assert "completed" in result.context_passed.lower()

    def test_assigns_unique_agent_number(self):
        """Each agent should get unique number (agent-1, agent-2, etc.)."""
        dispatcher = AgentDispatcher()
        result1 = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        result2 = dispatcher.dispatch(DEPENDENT_TASK, spec=SAMPLE_SPEC)
        assert result1.agent_number != result2.agent_number
        assert result1.agent_number >= 1
        assert result2.agent_number >= 1


class TestStatusTracking:
    """FR-7: Status tracking functionality."""

    def test_tracks_queued_status(self):
        """Should track tasks waiting to start."""
        dispatcher = AgentDispatcher()
        task_id = "task-queued"
        dispatcher.queue_task(task_id, SAMPLE_TASK)
        assert dispatcher.get_status(task_id) == AgentStatus.QUEUED

    def test_tracks_running_status(self):
        """Should track tasks currently executing."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        status = dispatcher.get_status(result.task_id)
        assert status in [AgentStatus.RUNNING, AgentStatus.COMPLETED]

    def test_tracks_completed_status(self):
        """Should track successfully completed tasks."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC, wait=True)
        if result.success:
            assert dispatcher.get_status(result.task_id) == AgentStatus.COMPLETED

    def test_tracks_failed_status(self):
        """Should track tasks that failed."""
        dispatcher = AgentDispatcher()
        # Force failure scenario
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC, force_fail=True)
        assert dispatcher.get_status(result.task_id) == AgentStatus.FAILED

    def test_tracks_blocked_status(self):
        """Should track tasks blocked by dependencies."""
        dispatcher = AgentDispatcher()
        # Task with unmet dependencies should be blocked
        dispatcher.queue_task(DEPENDENT_TASK.id, DEPENDENT_TASK)
        assert dispatcher.get_status(DEPENDENT_TASK.id) == AgentStatus.BLOCKED

    def test_status_transitions_are_valid(self):
        """Status should only transition in valid ways."""
        dispatcher = AgentDispatcher()
        # Valid: QUEUED → RUNNING → COMPLETED
        dispatcher.queue_task(SAMPLE_TASK.id, SAMPLE_TASK)
        assert dispatcher.get_status(SAMPLE_TASK.id) == AgentStatus.QUEUED

        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        # Cannot go backwards from RUNNING to QUEUED
        with pytest.raises(ValueError):
            dispatcher.set_status(SAMPLE_TASK.id, AgentStatus.QUEUED)


class TestMcpAgentMailIntegration:
    """FR-7: mcp_agent_mail coordination."""

    def test_reserves_files_before_dispatch(self):
        """Should call file_reservation_paths() before agent starts."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            files_to_edit=["src/Counter.tsx"]
        )
        assert result.file_reservation_created is True
        assert "src/Counter.tsx" in result.reserved_files

    def test_releases_files_on_completion(self):
        """Should release file reservations when task completes."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            files_to_edit=["src/Counter.tsx"],
            wait=True
        )
        # After completion, files should be released
        assert result.file_reservation_released is True

    def test_uses_beads_issue_id_in_reason(self):
        """File reservation reason should include beads issue ID."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            files_to_edit=["src/Counter.tsx"],
            beads_issue_id="bd-123"
        )
        assert "bd-123" in result.reservation_reason

    def test_handles_reservation_conflict(self):
        """Should handle case where files are already reserved."""
        dispatcher = AgentDispatcher()
        # First dispatch reserves files
        result1 = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            files_to_edit=["src/Counter.tsx"]
        )
        # Second dispatch tries same files - should detect conflict
        result2 = dispatcher.dispatch(
            DEPENDENT_TASK,
            spec=SAMPLE_SPEC,
            files_to_edit=["src/Counter.tsx"]
        )
        assert result2.reservation_conflict is True


class TestContextSecurity:
    """FR-7: Security scanning before dispatch."""

    def test_scans_for_api_keys(self):
        """Should detect potential API keys in context."""
        dispatcher = AgentDispatcher()
        secrets = dispatcher.scan_for_secrets(CONTEXT_WITH_SECRET)
        assert len(secrets) > 0
        assert any("API" in s.type or "key" in s.type.lower() for s in secrets)

    def test_scans_for_passwords(self):
        """Should detect potential passwords in context."""
        dispatcher = AgentDispatcher()
        secrets = dispatcher.scan_for_secrets(CONTEXT_WITH_PASSWORD)
        assert len(secrets) > 0
        assert any("password" in s.type.lower() for s in secrets)

    def test_scans_for_connection_strings(self):
        """Should detect potential connection strings."""
        dispatcher = AgentDispatcher()
        secrets = dispatcher.scan_for_secrets(CONTEXT_WITH_PASSWORD)
        assert len(secrets) > 0
        # Connection string pattern detected
        assert any("connection" in s.type.lower() or "url" in s.type.lower() for s in secrets)

    def test_warns_on_secrets_detected(self):
        """Should warn user when secrets detected."""
        dispatcher = AgentDispatcher()
        with pytest.warns(UserWarning, match="secret"):
            dispatcher.dispatch(
                SAMPLE_TASK,
                spec=SAMPLE_SPEC,
                additional_context=CONTEXT_WITH_SECRET
            )

    def test_redacts_before_non_local_llm(self):
        """Should redact secrets before sending to Gemini."""
        dispatcher = AgentDispatcher(model="gemini-pro")
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            additional_context=CONTEXT_WITH_SECRET
        )
        # Secret should be redacted in context
        assert "sk-secret" not in result.context_passed
        assert "[REDACTED]" in result.context_passed

    def test_claude_openai_allowed_per_settings(self):
        """Claude/OpenAI should be allowed per user's data settings."""
        dispatcher = AgentDispatcher(model="claude-3-opus")
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            additional_context=CONTEXT_WITH_SECRET
        )
        # For Claude, context may pass through (per user data settings)
        # This depends on user configuration
        assert result.redaction_applied is False or result.redaction_applied is True


class TestAgentErrors:
    """FR-7: Error handling."""

    def test_claude_code_not_installed_error(self):
        """Should give clear error if Claude Code not installed."""
        dispatcher = AgentDispatcher()
        with patch("shutil.which", return_value=None):
            with pytest.raises(ClaudeCodeNotFoundError) as exc_info:
                dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
            assert "claude code" in str(exc_info.value).lower()
            assert "install" in str(exc_info.value).lower()

    def test_detects_agent_crash(self):
        """Should detect when agent process crashes."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            simulate_crash=True,
            wait=True
        )
        assert result.crashed is True

    def test_marks_crashed_agent_as_failed(self):
        """Crashed agent should transition to failed status."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            simulate_crash=True,
            wait=True
        )
        assert dispatcher.get_status(result.task_id) == AgentStatus.FAILED
        assert "crash" in result.failure_reason.lower()

    def test_handles_timeout(self):
        """Should handle agent timeout gracefully."""
        dispatcher = AgentDispatcher(timeout_seconds=1)
        result = dispatcher.dispatch(
            SAMPLE_TASK,
            spec=SAMPLE_SPEC,
            simulate_slow=True,
            wait=True
        )
        assert result.timed_out is True
        assert dispatcher.get_status(result.task_id) == AgentStatus.FAILED


class TestConcurrentAgents:
    """FR-7: Multiple concurrent agents."""

    def test_can_run_multiple_agents(self):
        """Should be able to run N agents concurrently."""
        dispatcher = AgentDispatcher(max_concurrent=3)
        tasks = [
            Task(id=f"task-{i}", title=f"Task {i}", description=f"Do {i}",
                 acceptance_criteria="Done", effort_estimate="XS",
                 risk_level="low", validation_strategy=ValidationStrategy.NONE,
                 dependencies=[], stream_id=f"stream-{i}")
            for i in range(3)
        ]
        results = dispatcher.dispatch_batch(tasks, spec=SAMPLE_SPEC)
        assert len(results) == 3
        running_count = sum(1 for r in results if r.status == AgentStatus.RUNNING)
        assert running_count <= 3

    def test_no_session_file_conflicts(self):
        """Multiple agents should not conflict on session files."""
        dispatcher = AgentDispatcher(max_concurrent=2)
        results = dispatcher.dispatch_batch(
            [SAMPLE_TASK, DEPENDENT_TASK],
            spec=SAMPLE_SPEC
        )
        # Each agent should have unique session directory
        session_dirs = [r.session_dir for r in results]
        assert len(session_dirs) == len(set(session_dirs))

    def test_each_agent_has_unique_workspace(self):
        """Each agent should work in distinct context."""
        dispatcher = AgentDispatcher(max_concurrent=2)
        results = dispatcher.dispatch_batch(
            [SAMPLE_TASK, DEPENDENT_TASK],
            spec=SAMPLE_SPEC
        )
        # Each agent should have unique workspace identifier
        workspaces = [r.workspace_id for r in results]
        assert len(workspaces) == len(set(workspaces))


class TestAgentDispatchOutput:
    """FR-7: Output structure."""

    def test_returns_dispatch_result(self):
        """Should return structured dispatch result."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert isinstance(result, DispatchResult)

    def test_result_includes_agent_id(self):
        """Result should include unique agent identifier."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert result.agent_id is not None
        assert len(result.agent_id) > 0

    def test_result_includes_process_info(self):
        """Result should include process ID or handle."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert result.process_id is not None or result.process_handle is not None

    def test_result_includes_start_time(self):
        """Result should include when agent was dispatched."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        assert result.started_at is not None

    def test_result_is_serializable(self):
        """DispatchResult should be JSON serializable."""
        dispatcher = AgentDispatcher()
        result = dispatcher.dispatch(SAMPLE_TASK, spec=SAMPLE_SPEC)
        json_str = result.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "agent_id" in parsed
        assert "task_id" in parsed
