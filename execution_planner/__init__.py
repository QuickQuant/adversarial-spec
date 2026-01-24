"""
Execution Planner - Bridges finalized PRDs and implementation.

This module decomposes specs into tasks, assigns test strategies,
and dispatches Claude Code agents.
"""

from execution_planner.spec_intake import (
    SpecIntake,
    SpecDocument,
    SpecIntakeError,
    DocType,
    # PRD types
    UserStory,
    FunctionalRequirement,
    NonFunctionalRequirement,
    Risk,
    Decision,
    Dependencies,
    # Tech Spec types
    Goal,
    DataModel,
    APIEndpoint,
    ScheduledFunction,
    ErrorCode,
    PerformanceSLA,
    GauntletDecision,
    TechSpecSection,
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
    SpecReference,
    ConcernReference,
)
from execution_planner.agent_dispatch import (
    AgentDispatcher,
    DispatchResult,
    AgentStatus,
    DispatchError,
    ClaudeCodeNotFoundError,
    SecretDetectedError,
)
from execution_planner.execution_control import (
    ExecutionController,
    ExecutionState,
    ControlAction,
    ControlActionRecord,
    TaskExecutionState,
    ApprovalRecord,
)
from execution_planner.progress import (
    ProgressTracker,
    ProgressReport,
    TaskStatus,
    BranchStatus,
    LogEntry,
    LogLevel,
    cli_show_status,
    cli_show_logs,
)
from execution_planner.test_strategy import (
    TestStrategyManager,
    StrategyPlan,
    StrategyAssignment,
    StrategyReason,
    TestTask,
)
from execution_planner.over_decomposition import (
    OverDecompositionGuard,
    GuardResult,
    ConsolidationSuggestion,
)
from execution_planner.parallelization import (
    ParallelizationAdvisor,
    ParallelizationPlan,
    Workstream,
    MergePoint,
    BranchPattern,
)
from execution_planner.gauntlet_concerns import (
    GauntletConcern,
    GauntletConcernParser,
    GauntletReport,
    LinkedConcern,
    load_concerns_for_spec,
)

__all__ = [
    # spec_intake - core
    "SpecIntake",
    "SpecDocument",
    "SpecIntakeError",
    "DocType",
    # spec_intake - PRD types
    "UserStory",
    "FunctionalRequirement",
    "NonFunctionalRequirement",
    "Risk",
    "Decision",
    "Dependencies",
    # spec_intake - Tech Spec types
    "Goal",
    "DataModel",
    "APIEndpoint",
    "ScheduledFunction",
    "ErrorCode",
    "PerformanceSLA",
    "GauntletDecision",
    "TechSpecSection",
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
    "SpecReference",
    "ConcernReference",
    # agent_dispatch
    "AgentDispatcher",
    "DispatchResult",
    "AgentStatus",
    "DispatchError",
    "ClaudeCodeNotFoundError",
    "SecretDetectedError",
    # execution_control
    "ExecutionController",
    "ExecutionState",
    "ControlAction",
    "ControlActionRecord",
    "TaskExecutionState",
    "ApprovalRecord",
    # progress
    "ProgressTracker",
    "ProgressReport",
    "TaskStatus",
    "BranchStatus",
    "LogEntry",
    "LogLevel",
    "cli_show_status",
    "cli_show_logs",
    # test_strategy
    "TestStrategyManager",
    "StrategyPlan",
    "StrategyAssignment",
    "StrategyReason",
    "TestTask",
    # over_decomposition
    "OverDecompositionGuard",
    "GuardResult",
    "ConsolidationSuggestion",
    # parallelization
    "ParallelizationAdvisor",
    "ParallelizationPlan",
    "Workstream",
    "MergePoint",
    "BranchPattern",
    # gauntlet_concerns
    "GauntletConcern",
    "GauntletConcernParser",
    "GauntletReport",
    "LinkedConcern",
    "load_concerns_for_spec",
]
