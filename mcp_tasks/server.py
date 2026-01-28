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
