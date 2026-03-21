# ══════════════════════════════════════════════════════════════
# FILE: mcp_tasks/__init__.py (5 lines, 112 bytes)
# ══════════════════════════════════════════════════════════════
"""MCP Task Management Server for cross-agent task coordination."""

from .server import mcp

__all__ = ["mcp"]


# ══════════════════════════════════════════════════════════════
# FILE: mcp_tasks/server.py (366 lines, 12035 bytes)
# ══════════════════════════════════════════════════════════════
#!/usr/bin/env python3
"""
MCP Task Management Server

Provides TaskCreate, TaskGet, TaskList, TaskUpdate tools for cross-agent task coordination.
Tasks are stored per-project in .claude/tasks.json relative to the working directory.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Task Manager")

# Project directory detection - NO CACHING
# Caching caused tasks to go to wrong project when server started from home dir


def _find_project_root(start_path: Path) -> Optional[Path]:
    """Walk up from start_path to find a project root.

    Looks for common project markers (.git, .claude, pyproject.toml, package.json).
    """
    current = start_path.resolve()

    # Don't go above home directory
    home = Path.home()

    while current != current.parent and current >= home:
        # Check for project markers
        if (current / ".git").exists():
            return current
        if (current / ".claude").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if (current / "package.json").exists():
            return current
        current = current.parent

    return None


def get_working_dir() -> Path:
    """Get the working directory for task storage.

    Priority:
    1. MCP_WORKING_DIR environment variable (explicit override)
    2. Detect project root from PWD/cwd (fresh each call - no caching!)
    3. Fall back to PWD or cwd

    NO CACHING: Each call detects fresh. This is important because Claude Code
    sessions can switch projects, and we want tasks to go to the right place.
    """
    # Explicit override always wins
    if os.environ.get("MCP_WORKING_DIR"):
        return Path(os.environ["MCP_WORKING_DIR"])

    # Detect project root fresh each time (no caching!)
    start = Path(os.environ.get("PWD", os.getcwd()))
    project_root = _find_project_root(start)

    return project_root if project_root else start


def get_tasks_file(project_dir: Optional[str] = None) -> Path:
    """Get the path to the tasks.json file for current project."""
    if project_dir:
        base_dir = Path(project_dir)
    else:
        base_dir = get_working_dir()
    tasks_dir = base_dir / ".claude"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir / "tasks.json"


def load_tasks(project_dir: Optional[str] = None) -> dict:
    """Load tasks from the JSON file."""
    tasks_file = get_tasks_file(project_dir)
    if tasks_file.exists():
        with open(tasks_file, "r") as f:
            return json.load(f)
    return {"tasks": [], "next_id": 1}


def save_tasks(data: dict, project_dir: Optional[str] = None) -> None:
    """Save tasks to the JSON file."""
    tasks_file = get_tasks_file(project_dir)
    with open(tasks_file, "w") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def TaskCreate(
    subject: str,
    description: str,
    activeForm: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Create a new task in the task list.

    Args:
        subject: A brief title for the task (imperative form, e.g., "Fix login bug")
        description: A detailed description of what needs to be done
        activeForm: Present continuous form shown when in_progress (e.g., "Fixing login bug")
        metadata: Optional arbitrary metadata to attach to the task

    Returns:
        The created task object with its assigned ID
    """
    data = load_tasks()

    task = {
        "id": str(data["next_id"]),
        "subject": subject,
        "description": description,
        "status": "pending",
        "owner": None,
        "blockedBy": [],
        "blocks": [],
        "activeForm": activeForm or f"Working on: {subject}",
        "metadata": metadata or {},
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    }

    data["tasks"].append(task)
    data["next_id"] += 1
    save_tasks(data)

    return task


@mcp.tool()
def TaskGet(taskId: str) -> dict:
    """
    Retrieve a task by its ID.

    Args:
        taskId: The ID of the task to retrieve

    Returns:
        The full task object including subject, description, status, dependencies, etc.
    """
    data = load_tasks()

    for task in data["tasks"]:
        if task["id"] == taskId:
            return task

    return {"error": f"Task with ID {taskId} not found"}


@mcp.tool()
def TaskList(
    session_id: Optional[str] = None,
    context_name: Optional[str] = None,
    status: Optional[str] = None,
    list_contexts: bool = False,
) -> dict:
    """
    List all tasks in the task list, or list available contexts.

    Args:
        session_id: Optional filter - only return tasks with this session_id in metadata
        context_name: Optional filter - only return tasks with this context_name in metadata
        status: Optional filter - only return tasks with this status (pending, in_progress, completed)
        list_contexts: If true, return a summary of all contexts with task counts instead of task list

    Returns:
        If list_contexts=True: Summary of contexts with their task counts and last activity
        Otherwise: A summary of all tasks with their IDs, subjects, statuses, owners, and blockedBy lists
    """
    data = load_tasks()

    # If list_contexts is True, return context summary instead of task list
    if list_contexts:
        contexts = {}
        for task in data["tasks"]:
            ctx_name = task.get("metadata", {}).get("context_name", "unnamed")
            if ctx_name not in contexts:
                contexts[ctx_name] = {
                    "context_name": ctx_name,
                    "session_id": task.get("metadata", {}).get("session_id"),
                    "total": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "last_updated": None,
                }
            contexts[ctx_name]["total"] += 1
            task_status = task.get("status", "pending")
            if task_status == "pending":
                contexts[ctx_name]["pending"] += 1
            elif task_status == "in_progress":
                contexts[ctx_name]["in_progress"] += 1
            elif task_status == "completed":
                contexts[ctx_name]["completed"] += 1
            # Track most recent update
            task_updated = task.get("updatedAt")
            if task_updated:
                if contexts[ctx_name]["last_updated"] is None or task_updated > contexts[ctx_name]["last_updated"]:
                    contexts[ctx_name]["last_updated"] = task_updated

        # Filter to contexts with active work (pending or in_progress)
        active_contexts = [c for c in contexts.values() if c["pending"] > 0 or c["in_progress"] > 0]
        return {
            "contexts": active_contexts,
            "total_contexts": len(active_contexts),
        }

    summary = []
    for task in data["tasks"]:
        # Filter by session_id if provided
        if session_id:
            task_session = task.get("metadata", {}).get("session_id")
            if task_session != session_id:
                continue

        # Filter by context_name if provided
        if context_name:
            task_context = task.get("metadata", {}).get("context_name")
            if task_context != context_name:
                continue

        # Filter by status if provided
        if status and task.get("status") != status:
            continue
        # Only show blockedBy tasks that are not yet completed
        open_blockers = []
        for blocker_id in task.get("blockedBy", []):
            for other in data["tasks"]:
                if other["id"] == blocker_id and other["status"] != "completed":
                    open_blockers.append(blocker_id)
                    break

        summary.append({
            "id": task["id"],
            "subject": task["subject"],
            "status": task["status"],
            "owner": task.get("owner"),
            "blockedBy": open_blockers,
            "context_name": task.get("metadata", {}).get("context_name"),
        })

    return {
        "tasks": summary,
        "total": len(summary),
        "pending": len([t for t in summary if t["status"] == "pending"]),
        "in_progress": len([t for t in summary if t["status"] == "in_progress"]),
        "completed": len([t for t in summary if t["status"] == "completed"]),
    }


@mcp.tool()
def TaskUpdate(
    taskId: str,
    status: Optional[str] = None,
    subject: Optional[str] = None,
    description: Optional[str] = None,
    activeForm: Optional[str] = None,
    owner: Optional[str] = None,
    metadata: Optional[dict] = None,
    addBlocks: Optional[list[str]] = None,
    addBlockedBy: Optional[list[str]] = None,
) -> dict:
    """
    Update a task in the task list.

    Args:
        taskId: The ID of the task to update
        status: New status (pending, in_progress, completed)
        subject: New subject/title for the task
        description: New description for the task
        activeForm: New activeForm text shown when in_progress
        owner: New owner for the task (agent name)
        metadata: Metadata keys to merge into the task (set a key to null to delete it)
        addBlocks: Task IDs that this task blocks (will be added to existing)
        addBlockedBy: Task IDs that block this task (will be added to existing)

    Returns:
        The updated task object
    """
    data = load_tasks()

    task = None
    task_index = None
    for i, t in enumerate(data["tasks"]):
        if t["id"] == taskId:
            task = t
            task_index = i
            break

    if task is None:
        return {"error": f"Task with ID {taskId} not found"}

    # Update simple fields
    if status is not None:
        if status not in ("pending", "in_progress", "completed"):
            return {"error": f"Invalid status: {status}. Must be pending, in_progress, or completed"}
        task["status"] = status

    if subject is not None:
        task["subject"] = subject

    if description is not None:
        task["description"] = description

    if activeForm is not None:
        task["activeForm"] = activeForm

    if owner is not None:
        task["owner"] = owner

    # Merge metadata
    if metadata is not None:
        existing_metadata = task.get("metadata", {})
        for key, value in metadata.items():
            if value is None:
                existing_metadata.pop(key, None)
            else:
                existing_metadata[key] = value
        task["metadata"] = existing_metadata

    # Add to blocks list
    if addBlocks:
        existing_blocks = set(task.get("blocks", []))
        existing_blocks.update(addBlocks)
        task["blocks"] = list(existing_blocks)

        # Also update the blockedBy of the target tasks
        for blocked_id in addBlocks:
            for other in data["tasks"]:
                if other["id"] == blocked_id:
                    other_blocked_by = set(other.get("blockedBy", []))
                    other_blocked_by.add(taskId)
                    other["blockedBy"] = list(other_blocked_by)

    # Add to blockedBy list
    if addBlockedBy:
        existing_blocked_by = set(task.get("blockedBy", []))
        existing_blocked_by.update(addBlockedBy)
        task["blockedBy"] = list(existing_blocked_by)

        # Also update the blocks of the blocking tasks
        for blocker_id in addBlockedBy:
            for other in data["tasks"]:
                if other["id"] == blocker_id:
                    other_blocks = set(other.get("blocks", []))
                    other_blocks.add(taskId)
                    other["blocks"] = list(other_blocks)

    task["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    data["tasks"][task_index] = task
    save_tasks(data)

    return task


if __name__ == "__main__":
    mcp.run()


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/task_manager.py (687 lines, 23268 bytes)
# ══════════════════════════════════════════════════════════════
#!/usr/bin/env python3
"""
Task Manager - Python API for adversarial-spec task coordination.

This module provides a Python interface to the MCP Tasks system, sharing
the same storage format (.claude/tasks.json) so tasks are visible to both
Python scripts and Claude Code's MCP tools.

Usage:
    from task_manager import TaskManager, create_adversarial_spec_session

    # Create a new session with all phase tasks
    tm = TaskManager()
    session = create_adversarial_spec_session(tm, doc_type="prd")

    # Update task status
    tm.update_task(session.phase1_tasks[0], status="in_progress")

    # Add implementation tasks from execution plan
    tm.create_implementation_task(
        title="Implement orders schema",
        description="Create database schema for orders",
        concern_ids=["PARA-abc123"],
        spec_refs=["Section 3.2"],
        effort="S",
        risk_level="medium",
        blocked_by=[session.phase6_tasks[-1]],  # blocked by execution planning
    )
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_working_dir() -> Path:
    """Get the working directory for task storage.

    Priority:
    1. MCP_WORKING_DIR environment variable (set by Claude Code)
    2. PWD environment variable
    3. Current working directory
    """
    cwd = os.environ.get("MCP_WORKING_DIR") or os.environ.get("PWD") or os.getcwd()
    return Path(cwd)


def get_tasks_file(project_dir: Optional[Path] = None) -> Path:
    """Get the path to the tasks.json file.

    Args:
        project_dir: Optional explicit project directory. If not provided,
                     uses get_working_dir() which respects MCP_WORKING_DIR.

    Returns:
        Path to .claude/tasks.json in the project directory.
    """
    base_dir = project_dir or get_working_dir()
    tasks_dir = base_dir / ".claude"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir / "tasks.json"


@dataclass
class Task:
    """Represents a task in the system."""
    id: str
    subject: str
    description: str
    status: str = "pending"
    owner: Optional[str] = None
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    active_form: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            subject=data["subject"],
            description=data["description"],
            status=data.get("status", "pending"),
            owner=data.get("owner"),
            blocked_by=data.get("blockedBy", []),
            blocks=data.get("blocks", []),
            active_form=data.get("activeForm", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "blockedBy": self.blocked_by,
            "blocks": self.blocks,
            "activeForm": self.active_form,
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class TaskManager:
    """Manages tasks with the same storage format as MCP Tasks server.

    By default, uses the same file as MCP Tasks (.claude/tasks.json in the
    working directory). When used as part of adversarial-spec skill, the
    working directory is set by Claude Code to the project being worked on.
    """

    OWNER_PREFIX = "adv-spec:"

    def __init__(
        self,
        tasks_file: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ):
        """Initialize TaskManager.

        Args:
            tasks_file: Explicit path to tasks.json file.
            project_dir: Project directory (uses project_dir/.claude/tasks.json).
                         Ignored if tasks_file is provided.
        """
        self.tasks_file = tasks_file or get_tasks_file(project_dir)

    def _load(self) -> dict:
        """Load tasks from JSON file."""
        if self.tasks_file.exists():
            with open(self.tasks_file) as f:
                return json.load(f)
        return {"tasks": [], "next_id": 1}

    def _save(self, data: dict) -> None:
        """Save tasks to JSON file."""
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, "w") as f:
            json.dump(data, f, indent=2)

    def create_task(
        self,
        subject: str,
        description: str,
        active_form: Optional[str] = None,
        owner: Optional[str] = None,
        metadata: Optional[dict] = None,
        blocked_by: Optional[list[str]] = None,
    ) -> Task:
        """Create a new task."""
        data = self._load()
        now = datetime.utcnow().isoformat() + "Z"

        task_dict = {
            "id": str(data["next_id"]),
            "subject": subject,
            "description": description,
            "status": "pending",
            "owner": owner,
            "blockedBy": blocked_by or [],
            "blocks": [],
            "activeForm": active_form or f"Working on: {subject}",
            "metadata": metadata or {},
            "createdAt": now,
            "updatedAt": now,
        }

        # Update blocks for blocking tasks
        if blocked_by:
            for blocker_id in blocked_by:
                for t in data["tasks"]:
                    if t["id"] == blocker_id:
                        blocks = set(t.get("blocks", []))
                        blocks.add(task_dict["id"])
                        t["blocks"] = list(blocks)

        data["tasks"].append(task_dict)
        data["next_id"] += 1
        self._save(data)

        return Task.from_dict(task_dict)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        data = self._load()
        for t in data["tasks"]:
            if t["id"] == task_id:
                return Task.from_dict(t)
        return None

    def list_tasks(
        self,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        data = self._load()
        tasks = []

        for t in data["tasks"]:
            if status and t.get("status") != status:
                continue
            if owner and t.get("owner") != owner:
                continue
            if session_id and t.get("metadata", {}).get("session_id") != session_id:
                continue
            tasks.append(Task.from_dict(t))

        return tasks

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        metadata: Optional[dict] = None,
        add_blocked_by: Optional[list[str]] = None,
    ) -> Optional[Task]:
        """Update a task."""
        data = self._load()

        task = None
        task_idx = None
        for i, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                task = t
                task_idx = i
                break

        if task is None:
            return None

        if status is not None:
            task["status"] = status

        if owner is not None:
            task["owner"] = owner

        if metadata is not None:
            existing = task.get("metadata", {})
            for k, v in metadata.items():
                if v is None:
                    existing.pop(k, None)
                else:
                    existing[k] = v
            task["metadata"] = existing

        if add_blocked_by:
            blocked_by = set(task.get("blockedBy", []))
            blocked_by.update(add_blocked_by)
            task["blockedBy"] = list(blocked_by)

            # Update blocks on blocking tasks
            for blocker_id in add_blocked_by:
                for t in data["tasks"]:
                    if t["id"] == blocker_id:
                        blocks = set(t.get("blocks", []))
                        blocks.add(task_id)
                        t["blocks"] = list(blocks)

        task["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        data["tasks"][task_idx] = task
        self._save(data)

        return Task.from_dict(task)

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        return self.update_task(task_id, status="completed")

    def start_task(self, task_id: str, owner: Optional[str] = None) -> Optional[Task]:
        """Mark a task as in_progress."""
        return self.update_task(task_id, status="in_progress", owner=owner)


@dataclass
class AdversarialSpecSession:
    """Holds task IDs for an adversarial-spec session."""
    session_id: str
    doc_type: str
    phase1_tasks: list[str] = field(default_factory=list)  # Requirements
    phase2_tasks: list[str] = field(default_factory=list)  # Debate
    phase3_tasks: list[str] = field(default_factory=list)  # Gauntlet
    phase4_tasks: list[str] = field(default_factory=list)  # Finalization
    phase5_tasks: list[str] = field(default_factory=list)  # PRD → Tech
    phase6_tasks: list[str] = field(default_factory=list)  # Execution Planning
    phase7_tasks: list[str] = field(default_factory=list)  # Implementation


def create_adversarial_spec_session(
    tm: TaskManager,
    doc_type: str = "tech",
    include_interview: bool = True,
    include_gauntlet: bool = True,
    include_prd_to_tech: bool = False,
    include_execution_planning: bool = True,
) -> AdversarialSpecSession:
    """
    Create all tasks for an adversarial-spec session.

    Args:
        tm: TaskManager instance
        doc_type: "prd", "tech", or "debug"
        include_interview: Whether to include interview tasks
        include_gauntlet: Whether to include gauntlet phase
        include_prd_to_tech: Whether to include PRD → Tech continuation
        include_execution_planning: Whether to include execution planning

    Returns:
        AdversarialSpecSession with all task IDs
    """
    session_id = f"adv-spec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    session = AdversarialSpecSession(session_id=session_id, doc_type=doc_type)

    base_metadata = {"session_id": session_id, "doc_type": doc_type}
    owner = f"{TaskManager.OWNER_PREFIX}orchestrator"

    # Phase 1: Requirements Gathering
    phase1_meta = {**base_metadata, "phase": "requirements"}

    t1 = tm.create_task(
        subject="Determine document type",
        description="Ask user for document type: PRD, tech spec, or debug investigation",
        active_form="Determining document type",
        owner=owner,
        metadata=phase1_meta,
    )
    session.phase1_tasks.append(t1.id)

    t2 = tm.create_task(
        subject="Identify starting point",
        description="Get existing file path or description of what to build",
        active_form="Identifying starting point",
        owner=owner,
        metadata=phase1_meta,
        blocked_by=[t1.id],
    )
    session.phase1_tasks.append(t2.id)

    if include_interview and doc_type != "debug":
        t3 = tm.create_task(
            subject="Offer interview mode",
            description="Ask if user wants in-depth requirements interview",
            active_form="Offering interview mode",
            owner=owner,
            metadata=phase1_meta,
            blocked_by=[t2.id],
        )
        session.phase1_tasks.append(t3.id)

        t4 = tm.create_task(
            subject="Conduct interview",
            description="Interview covering: Problem/Context, Users/Stakeholders, Functional Requirements, Technical Constraints, UI/UX, Tradeoffs, Risks, Success Criteria",
            active_form="Conducting requirements interview",
            owner=owner,
            metadata=phase1_meta,
            blocked_by=[t3.id],
        )
        session.phase1_tasks.append(t4.id)
        last_p1 = t4.id
    else:
        last_p1 = t2.id

    t_draft = tm.create_task(
        subject="Generate initial draft",
        description="Load existing file or generate initial document based on user input",
        active_form="Generating initial draft",
        owner=owner,
        metadata=phase1_meta,
        blocked_by=[last_p1],
    )
    session.phase1_tasks.append(t_draft.id)

    t_confirm = tm.create_task(
        subject="Confirm draft with user",
        description="Show draft to user and get confirmation before debate",
        active_form="Confirming draft with user",
        owner=owner,
        metadata=phase1_meta,
        blocked_by=[t_draft.id],
    )
    session.phase1_tasks.append(t_confirm.id)

    # Phase 2: Adversarial Debate
    phase2_meta = {**base_metadata, "phase": "debate"}

    t_providers = tm.create_task(
        subject="Check available API providers",
        description="Run providers command to see which APIs are configured",
        active_form="Checking API providers",
        owner=owner,
        metadata=phase2_meta,
        blocked_by=[t_confirm.id],
    )
    session.phase2_tasks.append(t_providers.id)

    t_select = tm.create_task(
        subject="Select opponent models",
        description="Let user choose which models to include in the debate",
        active_form="Selecting opponent models",
        owner=owner,
        metadata=phase2_meta,
        blocked_by=[t_providers.id],
    )
    session.phase2_tasks.append(t_select.id)

    t_consensus = tm.create_task(
        subject="Run debate until consensus",
        description="Iterate through debate rounds until all models agree. Add round tasks dynamically.",
        active_form="Running adversarial debate",
        owner=owner,
        metadata=phase2_meta,
        blocked_by=[t_select.id],
    )
    session.phase2_tasks.append(t_consensus.id)

    # Phase 3: Gauntlet (optional)
    if include_gauntlet:
        phase3_meta = {**base_metadata, "phase": "gauntlet"}

        t_offer_gauntlet = tm.create_task(
            subject="Offer gauntlet review",
            description="Ask user if they want adversarial stress testing with specialized personas",
            active_form="Offering gauntlet review",
            owner=owner,
            metadata=phase3_meta,
            blocked_by=[t_consensus.id],
        )
        session.phase3_tasks.append(t_offer_gauntlet.id)

        t_gauntlet_run = tm.create_task(
            subject="Run gauntlet phases",
            description="Phase 1: Adversary attacks, Phase 2: Evaluation, Phase 3: Rebuttals, Phase 4: Summary, Phase 5: Final Boss (optional)",
            active_form="Running gauntlet",
            owner=owner,
            metadata=phase3_meta,
            blocked_by=[t_offer_gauntlet.id],
        )
        session.phase3_tasks.append(t_gauntlet_run.id)

        t_integrate = tm.create_task(
            subject="Integrate accepted concerns",
            description="Add mitigations for accepted concerns into spec, save concerns JSON",
            active_form="Integrating gauntlet concerns",
            owner=owner,
            metadata=phase3_meta,
            blocked_by=[t_gauntlet_run.id],
        )
        session.phase3_tasks.append(t_integrate.id)
        last_before_final = t_integrate.id
    else:
        last_before_final = t_consensus.id

    # Phase 4: Finalization
    phase4_meta = {**base_metadata, "phase": "finalization"}

    t_quality = tm.create_task(
        subject="Perform quality checks",
        description="Check completeness, consistency, clarity, actionability. Document-specific verification.",
        active_form="Performing quality checks",
        owner=owner,
        metadata=phase4_meta,
        blocked_by=[last_before_final],
    )
    session.phase4_tasks.append(t_quality.id)

    t_output = tm.create_task(
        subject="Output final document",
        description="Print to terminal, write to file, send summary, Telegram if enabled",
        active_form="Outputting final document",
        owner=owner,
        metadata=phase4_meta,
        blocked_by=[t_quality.id],
    )
    session.phase4_tasks.append(t_output.id)

    t_review = tm.create_task(
        subject="User review period",
        description="Accept / Request changes / Run another cycle",
        active_form="Awaiting user review",
        owner=owner,
        metadata=phase4_meta,
        blocked_by=[t_output.id],
    )
    session.phase4_tasks.append(t_review.id)

    # Phase 5: PRD → Tech Spec (optional)
    if include_prd_to_tech and doc_type == "prd":
        phase5_meta = {**base_metadata, "phase": "prd-to-tech"}

        t_offer_tech = tm.create_task(
            subject="Offer tech spec continuation",
            description="Ask if user wants to generate tech spec from finalized PRD",
            active_form="Offering tech spec continuation",
            owner=owner,
            metadata=phase5_meta,
            blocked_by=[t_review.id],
        )
        session.phase5_tasks.append(t_offer_tech.id)

        t_gen_tech = tm.create_task(
            subject="Generate tech spec from PRD",
            description="Load PRD as context, run interview if requested, generate initial tech spec, run debate",
            active_form="Generating tech spec from PRD",
            owner=owner,
            metadata=phase5_meta,
            blocked_by=[t_offer_tech.id],
        )
        session.phase5_tasks.append(t_gen_tech.id)
        last_before_exec = t_gen_tech.id
    else:
        last_before_exec = t_review.id

    # Phase 6: Execution Planning (optional)
    if include_execution_planning:
        phase6_meta = {**base_metadata, "phase": "execution-planning"}

        t_offer_exec = tm.create_task(
            subject="Offer execution plan generation",
            description="Ask if user wants to generate implementation plan from spec",
            active_form="Offering execution plan",
            owner=f"{TaskManager.OWNER_PREFIX}planner",
            metadata=phase6_meta,
            blocked_by=[last_before_exec],
        )
        session.phase6_tasks.append(t_offer_exec.id)

        t_run_pipeline = tm.create_task(
            subject="Create execution plan from spec and gauntlet output",
            description="Claude creates plan directly using guidelines in phases/06-execution.md (pipeline deprecated Feb 2026)",
            active_form="Creating execution plan",
            owner=f"{TaskManager.OWNER_PREFIX}planner",
            metadata=phase6_meta,
            blocked_by=[t_offer_exec.id],
        )
        session.phase6_tasks.append(t_run_pipeline.id)

        t_review_plan = tm.create_task(
            subject="Review execution plan with user",
            description="Present plan, discuss workstreams, confirm before implementation",
            active_form="Reviewing execution plan",
            owner=f"{TaskManager.OWNER_PREFIX}planner",
            metadata=phase6_meta,
            blocked_by=[t_run_pipeline.id],
        )
        session.phase6_tasks.append(t_review_plan.id)

    return session


def add_debate_round_task(
    tm: TaskManager,
    session: AdversarialSpecSession,
    round_number: int,
    models: list[str],
) -> str:
    """Add a task for a specific debate round."""
    base_metadata = {
        "session_id": session.session_id,
        "doc_type": session.doc_type,
        "phase": "debate",
        "round": round_number,
        "models": models,
    }

    # Block by previous round if exists
    blocked_by = []
    if session.phase2_tasks:
        blocked_by = [session.phase2_tasks[-1]]

    task = tm.create_task(
        subject=f"Debate round {round_number}",
        description=f"Send spec to {', '.join(models)}, receive critiques, synthesize, revise",
        active_form=f"Running debate round {round_number}",
        owner=f"{TaskManager.OWNER_PREFIX}debate",
        metadata=base_metadata,
        blocked_by=blocked_by,
    )

    session.phase2_tasks.append(task.id)
    return task.id


def add_implementation_task(
    tm: TaskManager,
    session: AdversarialSpecSession,
    title: str,
    description: str,
    concern_ids: Optional[list[str]] = None,
    spec_refs: Optional[list[str]] = None,
    workstream: Optional[str] = None,
    effort: str = "M",
    risk_level: str = "medium",
    validation: str = "test-after",
    blocked_by: Optional[list[str]] = None,
) -> str:
    """Add an implementation task from the execution plan."""
    metadata = {
        "session_id": session.session_id,
        "doc_type": session.doc_type,
        "phase": "implementation",
        "concern_ids": concern_ids or [],
        "spec_refs": spec_refs or [],
        "effort": effort,
        "risk_level": risk_level,
        "validation": validation,
    }

    if workstream:
        metadata["workstream"] = workstream

    owner = f"{TaskManager.OWNER_PREFIX}impl"
    if workstream:
        owner = f"{TaskManager.OWNER_PREFIX}impl:{workstream}"

    # If no explicit blockers, block by last execution planning task
    if blocked_by is None and session.phase6_tasks:
        blocked_by = [session.phase6_tasks[-1]]

    task = tm.create_task(
        subject=title,
        description=description,
        active_form=f"Implementing: {title}",
        owner=owner,
        metadata=metadata,
        blocked_by=blocked_by,
    )

    session.phase7_tasks.append(task.id)
    return task.id


def get_session_summary(tm: TaskManager, session_id: str) -> dict:
    """Get a summary of tasks for a session."""
    tasks = tm.list_tasks(session_id=session_id)

    by_phase = {}
    for task in tasks:
        phase = task.metadata.get("phase", "unknown")
        if phase not in by_phase:
            by_phase[phase] = {"pending": 0, "in_progress": 0, "completed": 0}
        by_phase[phase][task.status] += 1

    return {
        "session_id": session_id,
        "total_tasks": len(tasks),
        "pending": len([t for t in tasks if t.status == "pending"]),
        "in_progress": len([t for t in tasks if t.status == "in_progress"]),
        "completed": len([t for t in tasks if t.status == "completed"]),
        "by_phase": by_phase,
    }


if __name__ == "__main__":
    # Demo usage
    tm = TaskManager()

    print("Creating adversarial-spec session...")
    session = create_adversarial_spec_session(
        tm,
        doc_type="tech",
        include_interview=True,
        include_gauntlet=True,
        include_execution_planning=True,
    )

    print(f"\nSession ID: {session.session_id}")
    print(f"Phase 1 tasks: {len(session.phase1_tasks)}")
    print(f"Phase 2 tasks: {len(session.phase2_tasks)}")
    print(f"Phase 3 tasks: {len(session.phase3_tasks)}")
    print(f"Phase 4 tasks: {len(session.phase4_tasks)}")
    print(f"Phase 6 tasks: {len(session.phase6_tasks)}")

    summary = get_session_summary(tm, session.session_id)
    print(f"\nTotal tasks: {summary['total_tasks']}")
    print(f"By phase: {summary['by_phase']}")


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/telegram_bot.py (443 lines, 12803 bytes)
# ══════════════════════════════════════════════════════════════
#!/usr/bin/env python3
"""
Telegram bot utilities for adversarial spec development.

Usage:
    python3 telegram_bot.py setup              # Setup instructions and chat_id discovery
    python3 telegram_bot.py send <<< "message" # Send message from stdin
    python3 telegram_bot.py poll --timeout 60  # Poll for reply

Environment:
    TELEGRAM_BOT_TOKEN - Bot token from @BotFather
    TELEGRAM_CHAT_ID   - Your chat ID (get via setup command)

Exit codes:
    0 - Success
    1 - Error (API failure, timeout, etc.)
    2 - Missing configuration
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TELEGRAM_API: str = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE_LENGTH: int = 4096


def get_config() -> tuple[str, str]:
    """Get bot token and chat ID from environment.

    Returns:
        Tuple of (token, chat_id). Empty strings if not set.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def api_call(
    token: str, method: str, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Make Telegram Bot API call.

    Args:
        token: Bot API token.
        method: API method name (e.g., sendMessage, getUpdates).
        params: Optional query parameters.

    Returns:
        Parsed JSON response from Telegram API.

    Raises:
        RuntimeError: On HTTP or network errors.
    """
    url = TELEGRAM_API.format(token=token, method=method)
    if params:
        url += "?" + urlencode(params)

    try:
        req = Request(url, headers={"User-Agent": "adversarial-spec/1.0"})
        with urlopen(req, timeout=30) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Telegram API error {e.code}: {body}")
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")


def send_message(token: str, chat_id: str, text: str) -> bool:
    """Send a single message.

    Args:
        token: Bot API token.
        chat_id: Target chat identifier.
        text: Message text (supports Markdown).

    Returns:
        True on success, False on failure.
    """
    result = api_call(
        token,
        "sendMessage",
        {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
    )
    return result.get("ok", False)


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split long message into chunks, preferring paragraph boundaries.

    Args:
        text: The message text to split.
        max_length: Maximum length per chunk.

    Returns:
        List of message chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to split at paragraph boundary
        split_at = remaining.rfind("\n\n", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            # Try single newline
            split_at = remaining.rfind("\n", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            # Fall back to space
            split_at = remaining.rfind(" ", 0, max_length)
        if split_at == -1:
            # Hard split
            split_at = max_length

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()

    return chunks


def send_long_message(token: str, chat_id: str, text: str) -> bool:
    """Send message, splitting if necessary.

    Args:
        token: Bot API token.
        chat_id: Target chat identifier.
        text: Message text (may exceed 4096 chars).

    Returns:
        True if all chunks sent successfully.
    """
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            header = f"[{i + 1}/{len(chunks)}]\n"
            chunk = header + chunk
        if not send_message(token, chat_id, chunk):
            return False
        if i < len(chunks) - 1:
            time.sleep(0.5)  # Rate limit
    return True


def get_last_update_id(token: str) -> int:
    """Get the ID of the most recent update.

    Args:
        token: Bot API token.

    Returns:
        The update_id of the most recent update, or 0 if none.
    """
    result = api_call(token, "getUpdates", {"limit": 1, "offset": -1})
    updates = result.get("result", [])
    if updates:
        return updates[-1]["update_id"]
    return 0


def poll_for_reply(
    token: str, chat_id: str, timeout: int = 60, after_update_id: int = 0
) -> Optional[str]:
    """Poll for a reply from the specified chat.

    Args:
        token: Bot API token.
        chat_id: Chat to poll for replies from.
        timeout: Maximum seconds to wait.
        after_update_id: Only consider updates after this ID.

    Returns:
        Message text if received within timeout, None otherwise.
    """
    start_time = time.time()
    offset = after_update_id + 1 if after_update_id else None

    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        if remaining <= 0:
            break

        params = {"timeout": min(remaining, 30)}
        if offset:
            params["offset"] = offset

        try:
            result = api_call(token, "getUpdates", params)
            updates = result.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                msg_chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "")

                if msg_chat_id == chat_id and text:
                    # Clear processed updates
                    api_call(token, "getUpdates", {"offset": offset})
                    return text

        except RuntimeError:
            time.sleep(1)
            continue

    return None


def discover_chat_id(token: str) -> None:
    """Poll for messages and print chat IDs.

    Args:
        token: Bot API token.

    Runs until interrupted with Ctrl+C.
    """
    print("Waiting for messages... Send any message to your bot.")
    print("Press Ctrl+C to stop.\n")

    seen_chats = set()
    offset = None

    try:
        while True:
            params = {"timeout": 10}
            if offset:
                params["offset"] = offset

            result = api_call(token, "getUpdates", params)
            updates = result.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                chat_type = chat.get("type", "unknown")
                username = chat.get("username", "")
                first_name = chat.get("first_name", "")

                if chat_id and chat_id not in seen_chats:
                    seen_chats.add(chat_id)
                    name = username or first_name or "Unknown"
                    print(f"Found chat: {name} ({chat_type})")
                    print(f"  TELEGRAM_CHAT_ID={chat_id}")
                    print()

    except KeyboardInterrupt:
        print("\nDone.")


def cmd_setup(args: argparse.Namespace) -> None:
    """Print setup instructions and discover chat ID.

    Args:
        args: Parsed command-line arguments.
    """
    token, chat_id = get_config()

    print("=" * 50)
    print("Telegram Bot Setup for Adversarial Spec")
    print("=" * 50)
    print()

    if not token:
        print("Step 1: Create a Telegram bot")
        print("  1. Open Telegram and message @BotFather")
        print("  2. Send /newbot and follow the prompts")
        print("  3. Copy the bot token")
        print("  4. Set: export TELEGRAM_BOT_TOKEN='your-token-here'")
        print()
        print("Then run this command again.")
        sys.exit(2)

    print("Step 1: Bot token [OK]")
    print()

    if not chat_id:
        print("Step 2: Get your chat ID")
        print("  1. Open Telegram and message your bot (any message)")
        print("  2. This script will detect your chat ID")
        print()
        discover_chat_id(token)
        print()
        print("Set: export TELEGRAM_CHAT_ID='your-chat-id'")
        sys.exit(0)

    print("Step 2: Chat ID [OK]")
    print()
    print("Configuration complete. Testing...")
    print()

    if send_message(token, chat_id, "Adversarial Spec bot connected."):
        print("Test message sent successfully.")
    else:
        print("Failed to send test message. Check your configuration.")
        sys.exit(1)


def cmd_send(args: argparse.Namespace) -> None:
    """Send message from stdin.

    Args:
        args: Parsed command-line arguments.
    """
    token, chat_id = get_config()
    if not token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(2)

    text = sys.stdin.read().strip()
    if not text:
        print("Error: No message provided via stdin", file=sys.stderr)
        sys.exit(1)

    if send_long_message(token, chat_id, text):
        print("Message sent.")
    else:
        print("Failed to send message.", file=sys.stderr)
        sys.exit(1)


def cmd_poll(args: argparse.Namespace) -> None:
    """Poll for reply.

    Args:
        args: Parsed command-line arguments (includes timeout).
    """
    token, chat_id = get_config()
    if not token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(2)

    last_update = get_last_update_id(token)
    print(f"Polling for reply (timeout: {args.timeout}s)...", file=sys.stderr)

    reply = poll_for_reply(token, chat_id, args.timeout, last_update)
    if reply:
        print(reply)
    else:
        print("No reply received.", file=sys.stderr)
        sys.exit(1)


def cmd_notify(args: argparse.Namespace) -> None:
    """Send round notification and poll for feedback.

    Args:
        args: Parsed command-line arguments (includes timeout).
    """
    token, chat_id = get_config()
    if not token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(2)

    # Read notification from stdin
    notification = sys.stdin.read().strip()
    if not notification:
        print("Error: No notification provided via stdin", file=sys.stderr)
        sys.exit(1)

    # Get last update ID before sending
    last_update = get_last_update_id(token)

    # Send notification
    notification += (
        f"\n\n_Reply within {args.timeout}s to add feedback, or wait to continue._"
    )
    if not send_long_message(token, chat_id, notification):
        print("Failed to send notification.", file=sys.stderr)
        sys.exit(1)

    # Poll for reply
    reply = poll_for_reply(token, chat_id, args.timeout, last_update)

    # Output as JSON
    result = {"notification_sent": True, "feedback": reply}
    print(json.dumps(result))


def main() -> None:
    """Entry point for the telegram_bot CLI."""
    parser = argparse.ArgumentParser(
        description="Telegram bot utilities for adversarial spec development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup
    setup_parser = subparsers.add_parser(
        "setup", help="Setup instructions and chat ID discovery"
    )
    setup_parser.set_defaults(func=cmd_setup)

    # send
    send_parser = subparsers.add_parser("send", help="Send message from stdin")
    send_parser.set_defaults(func=cmd_send)

    # poll
    poll_parser = subparsers.add_parser("poll", help="Poll for reply")
    poll_parser.add_argument(
        "--timeout", "-t", type=int, default=60, help="Timeout in seconds"
    )
    poll_parser.set_defaults(func=cmd_poll)

    # notify
    notify_parser = subparsers.add_parser(
        "notify", help="Send notification and poll for feedback"
    )
    notify_parser.add_argument(
        "--timeout", "-t", type=int, default=60, help="Timeout in seconds"
    )
    notify_parser.set_defaults(func=cmd_notify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════
# FILE: execution_planner/__init__.py (23 lines, 560 bytes)
# ══════════════════════════════════════════════════════════════
"""
Execution Planner - Gauntlet concern parsing and linking.

Most of this package was deprecated in Feb 2026 (Option B+ decision).
Generation logic moved to LLM guidelines in phases/06-execution.md.
Only gauntlet concern parsing remains as code.
"""

from execution_planner.gauntlet_concerns import (
    GauntletConcern,
    GauntletConcernParser,
    GauntletReport,
    LinkedConcern,
    load_concerns_for_spec,
)

__all__ = [
    "GauntletConcern",
    "GauntletConcernParser",
    "GauntletReport",
    "LinkedConcern",
    "load_concerns_for_spec",
]


# ══════════════════════════════════════════════════════════════
# FILE: execution_planner/gauntlet_concerns.py (344 lines, 11781 bytes)
# ══════════════════════════════════════════════════════════════
"""
Gauntlet Concern Parsing and Linking

Parses gauntlet concern JSON files and links concerns to spec sections
for richer execution plans.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add adversarial-spec scripts to path for shared imports
# Works whether execution_planner is in project root or skill directory
_PARENT = Path(__file__).parent.parent
_SCRIPTS_PATH = _PARENT / "scripts"  # Skill directory layout
if not _SCRIPTS_PATH.exists():
    _SCRIPTS_PATH = _PARENT / "skills" / "adversarial-spec" / "scripts"  # Project layout
if str(_SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PATH))

from adversaries import ADVERSARY_PREFIXES, generate_concern_id  # noqa: E402


@dataclass
class GauntletConcern:
    """A concern raised during gauntlet review."""

    adversary: str
    text: str
    severity: str
    id: str = ""  # Stable ID for linking (auto-generated if empty)
    section_refs: list[str] = field(default_factory=list)
    title: Optional[str] = None
    failure_mode: Optional[str] = None
    detection: Optional[str] = None
    blast_radius: Optional[str] = None
    consequence: Optional[str] = None

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = generate_concern_id(self.adversary, self.text)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "adversary": self.adversary,
            "text": self.text,
            "severity": self.severity,
            "section_refs": self.section_refs,
            "title": self.title,
            "failure_mode": self.failure_mode,
            "detection": self.detection,
            "blast_radius": self.blast_radius,
            "consequence": self.consequence,
        }


@dataclass
class LinkedConcern:
    """A concern linked to specific spec elements."""

    concern: GauntletConcern
    spec_section: Optional[str] = None  # e.g., "4.3", "6.2"
    spec_title: Optional[str] = None  # e.g., "Nonce Management"
    data_model: Optional[str] = None  # e.g., "order_queue"
    api_endpoint: Optional[str] = None  # e.g., "orders:placeArbitrage"
    related_data_models: list[str] = field(default_factory=list)
    related_endpoints: list[str] = field(default_factory=list)


@dataclass
class GauntletReport:
    """Complete parsed gauntlet concerns with linking."""

    concerns: list[GauntletConcern] = field(default_factory=list)
    linked_concerns: list[LinkedConcern] = field(default_factory=list)
    by_section: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    by_adversary: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    by_severity: dict[str, list[GauntletConcern]] = field(default_factory=dict)
    source_path: Optional[str] = None

    def get_concerns_for_section(self, section: str) -> list[GauntletConcern]:
        """Get all concerns that reference a specific section."""
        return self.by_section.get(section, [])

    def get_high_severity(self) -> list[GauntletConcern]:
        """Get all high severity concerns."""
        return self.by_severity.get("high", [])

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            {
                "concerns": [c.to_dict() for c in self.concerns],
                "by_section": {
                    k: [c.to_dict() for c in v] for k, v in self.by_section.items()
                },
                "source_path": self.source_path,
            },
            indent=2,
        )


class GauntletConcernParser:
    """Parser for gauntlet concern JSON files."""

    # Patterns for extracting section references
    SECTION_PATTERNS = [
        r"\(Section\s*(\d+(?:\.\d+)?)\)",  # (Section 4.3)
        r"\((\d+\.\d+)\)",  # (4.3)
        r"Section\s+(\d+(?:\.\d+)?)",  # Section 4.3
        r"§\s*(\d+(?:\.\d+)?)",  # § 4.3
        r"\[Section\s*(\d+(?:\.\d+)?)\]",  # [Section 4.3]
    ]

    # Patterns for extracting data model references
    DATA_MODEL_PATTERNS = [
        r"`(\w+_\w+)`",  # `order_queue`
        r"`(\w+)`\s+table",  # `orders` table
        r"(\w+)\s+table",  # orders table
    ]

    # Patterns for extracting API endpoint references
    API_PATTERNS = [
        r"`(\w+:\w+)`",  # `orders:placeDma`
        r"(\w+:\w+)\s+action",  # orders:placeDma action
    ]

    @classmethod
    def parse(cls, content: str) -> GauntletReport:
        """
        Parse gauntlet concerns from JSON content.

        Args:
            content: Raw JSON content

        Returns:
            GauntletReport with parsed and linked concerns
        """
        data = json.loads(content)
        report = GauntletReport()

        for item in data:
            concern = cls._parse_concern(item)
            report.concerns.append(concern)

            # Index by section
            for ref in concern.section_refs:
                if ref not in report.by_section:
                    report.by_section[ref] = []
                report.by_section[ref].append(concern)

            # Index by adversary
            if concern.adversary not in report.by_adversary:
                report.by_adversary[concern.adversary] = []
            report.by_adversary[concern.adversary].append(concern)

            # Index by severity
            if concern.severity not in report.by_severity:
                report.by_severity[concern.severity] = []
            report.by_severity[concern.severity].append(concern)

        return report

    @classmethod
    def parse_file(cls, path: Path) -> GauntletReport:
        """
        Parse gauntlet concerns from a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            GauntletReport with parsed concerns
        """
        if not path.exists():
            raise FileNotFoundError(f"Gauntlet file not found: {path}")

        content = path.read_text(encoding="utf-8")
        report = cls.parse(content)
        report.source_path = str(path)
        return report

    @classmethod
    def _parse_concern(cls, item: dict) -> GauntletConcern:
        """Parse a single concern from a dict."""
        text = item.get("text", "")

        # Extract section references
        section_refs = cls._extract_section_refs(text)

        # Extract title (often in **bold**)
        title = cls._extract_title(text)

        # Extract failure mode, detection, blast radius, consequence
        failure_mode = cls._extract_field(text, "Failure Mode")
        detection = cls._extract_field(text, "Detection", "How Operators Find Out")
        blast_radius = cls._extract_field(text, "Blast Radius")
        consequence = cls._extract_field(text, "Consequence")

        return GauntletConcern(
            adversary=item.get("adversary", ""),
            text=text,
            severity=item.get("severity", "medium"),
            id=item.get("id", ""),  # ID from JSON, or auto-generate via __post_init__
            section_refs=section_refs,
            title=title,
            failure_mode=failure_mode,
            detection=detection,
            blast_radius=blast_radius,
            consequence=consequence,
        )

    @classmethod
    def _extract_section_refs(cls, text: str) -> list[str]:
        """Extract section references from concern text."""
        refs = set()
        for pattern in cls.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                refs.add(match.group(1))
        return sorted(refs)

    @classmethod
    def _extract_title(cls, text: str) -> Optional[str]:
        """Extract title from concern text (usually in **bold**)."""
        match = re.search(r"\*\*([^*]+)\*\*", text)
        if match:
            title = match.group(1).strip()
            # Remove trailing colon or punctuation
            title = re.sub(r"[:\s]+$", "", title)
            return title
        return None

    @classmethod
    def _extract_field(cls, text: str, *field_names: str) -> Optional[str]:
        """Extract a field value from concern text."""
        for name in field_names:
            pattern = rf"\*\*{re.escape(name)}:?\*\*:?\s*(.+?)(?=\*\*|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def link_to_spec(
        cls,
        report: GauntletReport,
        spec_doc: "SpecDocument",  # noqa: F821
    ) -> None:
        """
        Link concerns to spec elements.

        Updates the report's linked_concerns list with references to
        specific spec elements (data models, endpoints, etc.).
        """
        from execution_planner.spec_intake import SpecDocument

        report.linked_concerns = []

        for concern in report.concerns:
            linked = LinkedConcern(concern=concern)

            # Find matching spec section
            for ref in concern.section_refs:
                section = spec_doc.get_section_by_number(ref)
                if section:
                    linked.spec_section = ref
                    linked.spec_title = section.title
                    break

            # Find related data models
            for pattern in cls.DATA_MODEL_PATTERNS:
                for match in re.finditer(pattern, concern.text):
                    model_name = match.group(1)
                    for dm in spec_doc.data_models:
                        if dm.name.lower() == model_name.lower():
                            linked.related_data_models.append(dm.name)
                            if not linked.data_model:
                                linked.data_model = dm.name
                            break

            # Find related API endpoints
            for pattern in cls.API_PATTERNS:
                for match in re.finditer(pattern, concern.text):
                    endpoint_name = match.group(1)
                    for ep in spec_doc.api_endpoints:
                        if ep.name.lower() == endpoint_name.lower():
                            linked.related_endpoints.append(ep.name)
                            if not linked.api_endpoint:
                                linked.api_endpoint = ep.name
                            break

            report.linked_concerns.append(linked)


def load_concerns_for_spec(
    spec_path: Path,
    concerns_path: Optional[Path] = None,
) -> Optional[GauntletReport]:
    """
    Load gauntlet concerns for a spec file.

    If concerns_path is not provided, tries to find a matching concerns file
    in the same directory (e.g., gauntlet-concerns-*.json).

    Args:
        spec_path: Path to the spec file
        concerns_path: Optional explicit path to concerns JSON

    Returns:
        GauntletReport or None if no concerns found
    """
    if concerns_path and concerns_path.exists():
        return GauntletConcernParser.parse_file(concerns_path)

    # Try to find concerns file automatically
    spec_dir = spec_path.parent
    spec_stem = spec_path.stem

    # Look for patterns like:
    # - gauntlet-concerns-2026-01-23.json
    # - gauntlet-{spec_name}-concerns.json
    # - {spec_name}-gauntlet.json
    patterns = [
        "gauntlet-concerns-*.json",
        "gauntlet-*-concerns*.json",
        f"*{spec_stem}*gauntlet*.json",
    ]

    for pattern in patterns:
        matches = list(spec_dir.glob(pattern))
        if matches:
            # Return the most recent one
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return GauntletConcernParser.parse_file(matches[0])

    return None


# ══════════════════════════════════════════════════════════════
# FILE: skills/adversarial-spec/scripts/scope.py (606 lines, 18787 bytes)
# ══════════════════════════════════════════════════════════════
#!/usr/bin/env python3
"""
Scope Management for Adversarial Spec.

Detects scope expansion during spec refinement, generates mini-specs for
tangential discoveries, and manages user checkpoints for scope decisions.

Key concepts:
- ScopeDiscovery: A potential feature or expansion discovered during refinement
- MiniSpec: A stub document for a discovered feature (to be refined later)
- ScopeCheckpoint: A decision point where the user chooses how to handle discoveries
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# =============================================================================
# DATA STRUCTURES
# =============================================================================


class DiscoveryType(Enum):
    """Classification of scope discoveries."""

    TANGENTIAL_FEATURE = "tangential_feature"  # Nice-to-have, not blocking
    SCOPE_EXPANSION = "scope_expansion"  # Core task is bigger than expected
    PREREQUISITE = "prerequisite"  # Need this before the main task
    DECOMPOSITION = "decomposition"  # Task should split into multiple specs


class DiscoveryPriority(Enum):
    """Priority classification for discoveries."""

    NICE_TO_HAVE = "nice_to_have"  # Could be useful, not critical
    RECOMMENDED = "recommended"  # Should consider, improves quality
    IMPORTANT = "important"  # Significantly impacts the spec
    BLOCKING = "blocking"  # Cannot proceed without addressing


@dataclass
class ScopeDiscovery:
    """A potential feature or scope expansion discovered during refinement."""

    id: str
    name: str
    description: str
    discovery_type: DiscoveryType
    priority: DiscoveryPriority
    trigger_text: str  # The critique/concern that triggered this discovery
    source_model: str  # Which model identified this
    user_value: str  # Why this matters to users
    stub_location: Optional[str] = None  # Where to reference in main spec
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "discovery_type": self.discovery_type.value,
            "priority": self.priority.value,
            "trigger_text": self.trigger_text,
            "source_model": self.source_model,
            "user_value": self.user_value,
            "stub_location": self.stub_location,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScopeDiscovery":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            discovery_type=DiscoveryType(data["discovery_type"]),
            priority=DiscoveryPriority(data["priority"]),
            trigger_text=data["trigger_text"],
            source_model=data["source_model"],
            user_value=data["user_value"],
            stub_location=data.get("stub_location"),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class ScopeDecision:
    """User's decision about a discovery."""

    discovery_id: str
    action: str  # "stub", "expand", "defer", "reject"
    notes: Optional[str] = None
    decided_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScopeReport:
    """Complete scope analysis from a refinement session."""

    discoveries: list[ScopeDiscovery]
    decisions: list[ScopeDecision] = field(default_factory=list)
    original_scope: str = ""
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "discoveries": [d.to_dict() for d in self.discoveries],
            "decisions": [
                {
                    "discovery_id": d.discovery_id,
                    "action": d.action,
                    "notes": d.notes,
                    "decided_at": d.decided_at,
                }
                for d in self.decisions
            ],
            "original_scope": self.original_scope,
            "session_id": self.session_id,
        }

    def get_pending_decisions(self) -> list[ScopeDiscovery]:
        """Get discoveries that haven't been decided yet."""
        decided_ids = {d.discovery_id for d in self.decisions}
        return [d for d in self.discoveries if d.id not in decided_ids]

    def get_stubs(self) -> list[ScopeDiscovery]:
        """Get discoveries marked as stubs."""
        stub_ids = {d.discovery_id for d in self.decisions if d.action == "stub"}
        return [d for d in self.discoveries if d.id in stub_ids]

    def get_expansions(self) -> list[ScopeDiscovery]:
        """Get discoveries marked for expansion."""
        expand_ids = {d.discovery_id for d in self.decisions if d.action == "expand"}
        return [d for d in self.discoveries if d.id in expand_ids]


# =============================================================================
# MINI-SPEC TEMPLATE
# =============================================================================

MINI_SPEC_TEMPLATE = """# Suggested Feature: {name}

**Status**: Stub (discovered during adversarial review)
**Discovered**: {created_at}
**Source**: {source_model}
**Priority**: {priority}

## Summary

{description}

## User Value

{user_value}

## Trigger

This feature was identified when reviewing the main spec:

> {trigger_text}

## Scope Notes

- **Type**: {discovery_type}
- **Stub Location**: {stub_location}

## Next Steps

- [ ] Decide if this should be a separate spec
- [ ] If yes, run `/adversarial-spec` on this document to flesh it out
- [ ] Link back to original spec if implemented

---
*Generated by adversarial-spec scope management*
"""

STUB_REFERENCE_TEMPLATE = """
> **Scope Note**: {name}
>
> {description}
>
> See: [suggested-features/{slug}.md](suggested-features/{slug}.md)
"""


def generate_mini_spec(discovery: ScopeDiscovery) -> str:
    """Generate a mini-spec document from a discovery."""
    return MINI_SPEC_TEMPLATE.format(
        name=discovery.name,
        created_at=discovery.created_at[:10],
        source_model=discovery.source_model,
        priority=discovery.priority.value.replace("_", " ").title(),
        description=discovery.description,
        user_value=discovery.user_value,
        trigger_text=discovery.trigger_text[:500],
        discovery_type=discovery.discovery_type.value.replace("_", " ").title(),
        stub_location=discovery.stub_location or "N/A",
    )


def generate_stub_reference(discovery: ScopeDiscovery) -> str:
    """Generate a stub reference to insert into the main spec."""
    slug = slugify(discovery.name)
    return STUB_REFERENCE_TEMPLATE.format(
        name=discovery.name,
        description=discovery.description[:200],
        slug=slug,
    )


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


# =============================================================================
# SCOPE DETECTION
# =============================================================================

SCOPE_DETECTION_PROMPT = """Analyze this critique/response for scope implications.

You are looking for signs that:
1. The task is bigger than originally thought (SCOPE_EXPANSION)
2. A tangential feature was discovered that's worth noting (TANGENTIAL_FEATURE)
3. Something needs to be done first (PREREQUISITE)
4. The task should be split into multiple specs (DECOMPOSITION)

MODEL RESPONSE TO ANALYZE:
{response}

ORIGINAL SPEC CONTEXT:
{spec_summary}

For each scope implication found, output in this exact JSON format:
```json
{{
  "discoveries": [
    {{
      "name": "Short feature/task name",
      "description": "1-2 sentences describing what was discovered",
      "discovery_type": "tangential_feature|scope_expansion|prerequisite|decomposition",
      "priority": "nice_to_have|recommended|important|blocking",
      "trigger_text": "The specific text that triggered this discovery",
      "user_value": "Why this matters to users"
    }}
  ]
}}
```

If no scope implications found, output:
```json
{{"discoveries": []}}
```

IMPORTANT:
- Only flag genuine scope discoveries, not minor implementation details
- A critique about missing error handling is NOT a scope discovery
- A critique suggesting "you should also add user preferences" IS a tangential feature
- Focus on things that would require NEW design work, not just fixes to the current spec
"""

SCOPE_CHECKPOINT_PROMPT = """## Scope Checkpoint

During review, {count} potential scope {items} discovered:

{discoveries_summary}

### Options

For each discovery, choose:
- **stub**: Create a mini-spec and continue with core task
- **expand**: Add to current scope (increases complexity)
- **defer**: Note it but don't create stub
- **reject**: Not relevant, ignore

What would you like to do?
"""


def format_scope_checkpoint(discoveries: list[ScopeDiscovery]) -> str:
    """Format a user checkpoint prompt for scope decisions."""
    count = len(discoveries)
    items = "expansion was" if count == 1 else "expansions were"

    summaries = []
    for i, d in enumerate(discoveries, 1):
        priority_marker = ""
        if d.priority == DiscoveryPriority.BLOCKING:
            priority_marker = " [BLOCKING]"
        elif d.priority == DiscoveryPriority.IMPORTANT:
            priority_marker = " [IMPORTANT]"

        summaries.append(
            f"{i}. **{d.name}**{priority_marker} ({d.discovery_type.value.replace('_', ' ')})\n"
            f"   {d.description}\n"
            f"   _User value: {d.user_value}_"
        )

    return SCOPE_CHECKPOINT_PROMPT.format(
        count=count,
        items=items,
        discoveries_summary="\n\n".join(summaries),
    )


def parse_scope_discoveries(
    response: str,
    model: str,
    spec_summary: str,
) -> list[ScopeDiscovery]:
    """Parse scope discoveries from a model response.

    This is a simple heuristic parser. For production, you'd use the
    SCOPE_DETECTION_PROMPT with a model call.
    """
    import uuid

    discoveries = []

    # Look for JSON in the response
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            for d in data.get("discoveries", []):
                discoveries.append(
                    ScopeDiscovery(
                        id=str(uuid.uuid4())[:8],
                        name=d.get("name", "Unnamed"),
                        description=d.get("description", ""),
                        discovery_type=DiscoveryType(
                            d.get("discovery_type", "tangential_feature")
                        ),
                        priority=DiscoveryPriority(
                            d.get("priority", "nice_to_have")
                        ),
                        trigger_text=d.get("trigger_text", ""),
                        source_model=model,
                        user_value=d.get("user_value", ""),
                    )
                )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    return discoveries


# =============================================================================
# SCOPE DETECTION (HEURISTIC)
# =============================================================================

# Keywords that suggest scope expansion
EXPANSION_KEYWORDS = [
    "should also",
    "would also need",
    "additionally requires",
    "this implies",
    "you'll also need",
    "consider adding",
    "might want to add",
    "would benefit from",
    "requires a separate",
    "out of scope but",
    "beyond the scope but",
    "future enhancement",
    "nice to have",
    "could also",
    "extends to",
]

PREREQUISITE_KEYWORDS = [
    "first need to",
    "before this",
    "prerequisite",
    "depends on",
    "requires first",
    "must have",
    "blocking on",
]

DECOMPOSITION_KEYWORDS = [
    "should be split",
    "separate spec",
    "multiple phases",
    "break this into",
    "too much for one",
    "should be its own",
]


def detect_scope_hints_heuristic(response: str) -> list[dict]:
    """Detect potential scope discoveries using keyword heuristics.

    Returns list of hints with the triggering text and suggested type.
    This is a fast, cheap alternative to using a model for detection.
    """
    hints = []
    response_lower = response.lower()

    # Check for expansion keywords
    for keyword in EXPANSION_KEYWORDS:
        if keyword in response_lower:
            # Extract surrounding context
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "tangential_feature",
                    "keyword": keyword,
                    "context": context,
                }
            )

    # Check for prerequisite keywords
    for keyword in PREREQUISITE_KEYWORDS:
        if keyword in response_lower:
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "prerequisite",
                    "keyword": keyword,
                    "context": context,
                }
            )

    # Check for decomposition keywords
    for keyword in DECOMPOSITION_KEYWORDS:
        if keyword in response_lower:
            idx = response_lower.find(keyword)
            start = max(0, idx - 50)
            end = min(len(response), idx + len(keyword) + 150)
            context = response[start:end]

            hints.append(
                {
                    "type": "decomposition",
                    "keyword": keyword,
                    "context": context,
                }
            )

    return hints


# =============================================================================
# PERSISTENCE
# =============================================================================

SCOPE_DIR = Path.home() / ".adversarial-spec" / "scope"


def save_mini_spec(discovery: ScopeDiscovery, output_dir: Optional[Path] = None) -> Path:
    """Save a mini-spec to disk.

    Args:
        discovery: The discovery to save
        output_dir: Directory to save to (default: ~/.adversarial-spec/scope/suggested-features/)

    Returns:
        Path to the saved file
    """
    if output_dir is None:
        output_dir = SCOPE_DIR / "suggested-features"

    output_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(discovery.name)
    filename = f"{slug}.md"
    filepath = output_dir / filename

    content = generate_mini_spec(discovery)
    filepath.write_text(content)

    return filepath


def save_scope_report(report: ScopeReport, session_id: str) -> Path:
    """Save a scope report to disk.

    Args:
        report: The scope report to save
        session_id: Session identifier

    Returns:
        Path to the saved file
    """
    SCOPE_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"scope-report-{session_id}.json"
    filepath = SCOPE_DIR / filename

    filepath.write_text(json.dumps(report.to_dict(), indent=2))

    return filepath


def load_scope_report(session_id: str) -> Optional[ScopeReport]:
    """Load a scope report from disk.

    Args:
        session_id: Session identifier

    Returns:
        ScopeReport if found, None otherwise
    """
    filename = f"scope-report-{session_id}.json"
    filepath = SCOPE_DIR / filename

    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text())
        return ScopeReport(
            discoveries=[ScopeDiscovery.from_dict(d) for d in data.get("discoveries", [])],
            decisions=[
                ScopeDecision(
                    discovery_id=d["discovery_id"],
                    action=d["action"],
                    notes=d.get("notes"),
                    decided_at=d.get("decided_at", datetime.now().isoformat()),
                )
                for d in data.get("decisions", [])
            ],
            original_scope=data.get("original_scope", ""),
            session_id=data.get("session_id"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


# =============================================================================
# FORMATTING
# =============================================================================


def format_discoveries_summary(discoveries: list[ScopeDiscovery]) -> str:
    """Format a brief summary of discoveries for output."""
    if not discoveries:
        return "No scope discoveries."

    lines = [f"=== Scope Discoveries ({len(discoveries)}) ===", ""]

    by_type: dict[str, list[ScopeDiscovery]] = {}
    for d in discoveries:
        type_name = d.discovery_type.value.replace("_", " ").title()
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(d)

    for type_name, type_discoveries in by_type.items():
        lines.append(f"**{type_name}**:")
        for d in type_discoveries:
            priority = f"[{d.priority.value.upper()}]" if d.priority != DiscoveryPriority.NICE_TO_HAVE else ""
            lines.append(f"  - {d.name} {priority}")
            lines.append(f"    {d.description[:100]}...")
        lines.append("")

    return "\n".join(lines)


def format_scope_notes_section(stubs: list[ScopeDiscovery]) -> str:
    """Format a scope notes section to append to a spec."""
    if not stubs:
        return ""

    lines = [
        "",
        "---",
        "",
        "## Scope Notes",
        "",
        "The following items were identified during adversarial review but deferred:",
        "",
    ]

    for stub in stubs:
        slug = slugify(stub.name)
        lines.append(f"### {stub.name}")
        lines.append("")
        lines.append(f"{stub.description}")
        lines.append("")
        lines.append(f"_Priority: {stub.priority.value.replace('_', ' ').title()}_")
        lines.append(f"_See: [suggested-features/{slug}.md](suggested-features/{slug}.md)_")
        lines.append("")

    return "\n".join(lines)


