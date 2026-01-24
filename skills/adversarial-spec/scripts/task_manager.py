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
            subject="Run execution planning pipeline",
            description="FR-1: Spec Intake, FR-2: Scope Assessment, FR-3: Task Plan, FR-4: Test Strategy, FR-5: Over-Decomposition Guard, FR-6: Parallelization",
            active_form="Running execution planning pipeline",
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
