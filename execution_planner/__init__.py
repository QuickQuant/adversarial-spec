"""
Execution Planner - Bridges finalized PRDs and implementation.

This module decomposes specs into tasks, assigns test strategies,
and dispatches Claude Code agents.
"""

from execution_planner.spec_intake import (
    SpecIntake,
    SpecDocument,
    SpecIntakeError,
    UserStory,
    FunctionalRequirement,
    NonFunctionalRequirement,
    Risk,
    Decision,
    Dependencies,
)
from execution_planner.scope_assessor import (
    ScopeAssessor,
    ScopeAssessment,
    ScopeRecommendation,
    ConfidenceLevel,
    ScopeAssessorError,
)
from execution_planner.task_planner import (
    TaskPlanner,
    TaskPlan,
    Task,
    TaskPlanError,
    CircularDependencyError,
    ValidationStrategy,
)
from execution_planner.agent_dispatch import (
    AgentDispatcher,
    DispatchResult,
    AgentStatus,
    DispatchError,
    ClaudeCodeNotFoundError,
    SecretDetectedError,
)

__all__ = [
    # spec_intake
    "SpecIntake",
    "SpecDocument",
    "SpecIntakeError",
    "UserStory",
    "FunctionalRequirement",
    "NonFunctionalRequirement",
    "Risk",
    "Decision",
    "Dependencies",
    # scope_assessor
    "ScopeAssessor",
    "ScopeAssessment",
    "ScopeRecommendation",
    "ConfidenceLevel",
    "ScopeAssessorError",
    # task_planner
    "TaskPlanner",
    "TaskPlan",
    "Task",
    "TaskPlanError",
    "CircularDependencyError",
    "ValidationStrategy",
    # agent_dispatch
    "AgentDispatcher",
    "DispatchResult",
    "AgentStatus",
    "DispatchError",
    "ClaudeCodeNotFoundError",
    "SecretDetectedError",
]
