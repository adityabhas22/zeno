"""
Task Management Tools for Zeno Agent

Tools for managing daily tasks and to-dos within Zeno using database persistence.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, List
from datetime import datetime, date, time

from livekit.agents import function_tool, RunContext

from core.storage.task_operations import TaskOperations
from core.storage.database import session_scope
from core.storage.timezone_utils import TimezoneManager

logger = logging.getLogger(__name__)


class TaskTools:
    """Task management tools with database persistence for Zeno agent."""

    def __init__(self):
        # No longer using in-memory storage - now using database
        pass

    @function_tool()
    async def create_task(
        self,
        context: RunContext,
        title: str,
        description: Optional[str] = None,
        priority: int = 3,
        due_date: Optional[str] = None,
        category: str = "general",
    ) -> dict[str, Any]:
        """Create a new task for daily planning.

        Args:
            title: Task title/description
            description: Optional detailed description
            priority: Priority from 1 (highest) to 5 (lowest)
            due_date: Optional due date in ISO format (YYYY-MM-DD)
            category: Task category (work, personal, health, etc.)
        Returns:
            Created task information
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated"}

        session_id = getattr(context.session.userdata, 'session_id', None)
        timezone = getattr(context.session.userdata, 'timezone', 'UTC')

        # Parse due date if provided
        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = date.fromisoformat(due_date)
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}

        with session_scope() as session:
            task = TaskOperations.create_task(
                session=session,
                user_id=user_id,
                session_id=session_id,
                title=title,
                description=description,
                priority=priority,
                due_date=parsed_due_date,
                category=category,
                timezone=timezone
            )

            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date is not None else None,
                "category": task.category,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "message": f"Task created successfully: {title}"
            }

    @function_tool()
    async def list_tasks(
        self,
        context: RunContext,
        category: Optional[str] = None,
        priority_min: Optional[int] = None,
        completed: Optional[bool] = None,
        limit: int = 20,
    ) -> List[dict[str, Any]]:
        """List tasks with optional filtering.

        Args:
            category: Filter by category
            priority_min: Minimum priority level (1-5)
            completed: Filter by completion status
            limit: Maximum number of tasks to return
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return []

        with session_scope() as session:
            tasks = TaskOperations.get_user_tasks(
                session=session,
                user_id=user_id,
                category=category,
                priority_min=priority_min,
                completed=completed,
                limit=limit
            )

            # Convert to dictionary format for API compatibility
            return [{
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date is not None else None,
                "reminder_time": task.reminder_time.isoformat() if task.reminder_time is not None else None,
                "category": task.category,
                "status": task.status,
                "completed": task.status == "completed",
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "tags": task.tags,
                "task_metadata": task.task_metadata
            } for task in tasks]

    @function_tool()
    async def complete_task(
        self,
        context: RunContext,
        task_id: str,
    ) -> dict[str, Any]:
        """Mark a task as completed.

        Args:
            task_id: ID of the task to complete
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated"}

        with session_scope() as session:
            task = TaskOperations.complete_task(
                session=session,
                task_id=task_id,
                user_id=user_id
            )

            if not task:
                return {"error": f"Task {task_id} not found"}

            return {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "completed_at": task.completed_at.isoformat() if task.completed_at is not None else None,
                "message": f"Task completed: {task.title}"
            }

    @function_tool()
    async def get_priority_tasks(
        self,
        context: RunContext,
        max_priority: int = 2,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Get high-priority tasks for morning briefing.

        Args:
            max_priority: Maximum priority level to include (1-5)
            max_results: Maximum number of tasks to return
        """
        tasks = await self.list_tasks(
            context,
            priority_min=max_priority,
            completed=False,
            limit=max_results
        )

        return {
            "priority_tasks": tasks,
            "total_count": len(tasks),
            "has_urgent_tasks": any(t.get("priority", 5) == 1 for t in tasks)
        }

    @function_tool()
    async def get_today_tasks(
        self,
        context: RunContext,
    ) -> dict[str, Any]:
        """Get tasks due today for daily planning."""
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"today_tasks": [], "total_count": 0, "has_overdue": False}

        with session_scope() as session:
            tasks = TaskOperations.get_today_tasks(session, user_id)

            # Convert to dictionary format
            today_tasks = [{
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date is not None else None,
                "reminder_time": task.reminder_time.isoformat() if task.reminder_time is not None else None,
                "category": task.category,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "tags": task.tags,
                "task_metadata": task.task_metadata
            } for task in tasks]

            return {
                "today_tasks": today_tasks,
                "total_count": len(today_tasks),
                "has_overdue": False  # TODO: Implement overdue logic based on timezone
            }

    @function_tool()
    async def update_task_priority(
        self,
        context: RunContext,
        task_id: str,
        priority: int,
    ) -> dict[str, Any]:
        """Update the priority of a task.

        Args:
            task_id: ID of the task to update
            priority: New priority level (1-5)
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated"}

        with session_scope() as session:
            task = TaskOperations.update_task_priority(
                session=session,
                task_id=task_id,
                user_id=user_id,
                priority=priority
            )

            if not task:
                return {"error": f"Task {task_id} not found"}

            return {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "updated_at": task.updated_at.isoformat(),
                "message": f"Updated priority to {priority} for: {task.title}"
            }

    @function_tool()
    async def delete_task(
        self,
        context: RunContext,
        task_id: str,
    ) -> dict[str, Any]:
        """Delete a task.

        Args:
            task_id: ID of the task to delete
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated"}

        with session_scope() as session:
            # First get the task to return its title
            task = TaskOperations.get_task_by_id(session, task_id, user_id)
            if not task:
                return {"error": f"Task {task_id} not found"}

            title = task.title

            # Delete the task
            deleted = TaskOperations.delete_task(session, task_id, user_id)

            if deleted:
                return {"message": f"Task '{title}' deleted successfully"}
            else:
                return {"error": f"Failed to delete task {task_id}"}

    @function_tool()
    async def get_task_summary(
        self,
        context: RunContext,
    ) -> str:
        """Get a summary of tasks for morning briefing."""
        all_tasks = await self.list_tasks(context, completed=False)
        priority_tasks = [t for t in all_tasks if t.get("priority", 5) <= 2]
        today_tasks = (await self.get_today_tasks(context))["today_tasks"]

        if not all_tasks:
            return "You have no pending tasks."

        summary_parts = [f"You have {len(all_tasks)} pending tasks."]

        if priority_tasks:
            summary_parts.append(f"{len(priority_tasks)} are high priority:")
            for task in priority_tasks[:3]:  # Show top 3 priority tasks
                priority_label = "🔴 Urgent" if task.get("priority") == 1 else "🟡 High"
                summary_parts.append(f"  • {priority_label}: {task['title']}")

        if today_tasks:
            summary_parts.append(f"{len(today_tasks)} tasks are due today.")

        return "\n".join(summary_parts)

    @function_tool()
    async def share_tasks_to_doc(
        self,
        context: RunContext,
        include_all_tasks: bool = False,
        doc_title: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a Google Doc with current tasks and todos.

        Args:
            include_all_tasks: Whether to include all tasks or just priority ones
            doc_title: Custom title for the document
        Returns:
            Document creation result with URL
        """
        from datetime import date

        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        try:
            from core.integrations.google.drive import DriveService
            drive_service = DriveService(user_id=user_id)

            # Get tasks
            if include_all_tasks:
                all_tasks = await self.list_tasks(context, completed=False)
                priority_tasks = [t for t in all_tasks if t.get("priority", 5) <= 2]
            else:
                priority_result = await self.get_priority_tasks(context)
                priority_tasks = priority_result.get("priority_tasks", [])
                all_tasks = priority_tasks

            # Create the document
            today = date.today().isoformat()
            doc_result = drive_service.create_task_summary_doc(
                today, all_tasks, priority_tasks
            )

            return {
                "success": True,
                "document": doc_result,
                "total_tasks": len(all_tasks),
                "priority_tasks": len(priority_tasks),
                "message": f"Created task summary document: {doc_result['title']}"
            }

        except Exception as e:
            logger.error(f"Failed to create task document for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create task document: {str(e)}"
            }

    # New method to create tasks from goals text with intelligent parsing
    @function_tool()
    async def create_tasks_from_goals(
        self,
        context: RunContext,
        goals_text: str,
    ) -> dict[str, Any]:
        """Intelligently parse user goals and create individual tasks.

        Args:
            goals_text: Raw text containing user goals and targets
        Returns:
            Created tasks information
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated", "created_tasks": []}

        session_id = getattr(context.session.userdata, 'session_id', None)
        timezone = getattr(context.session.userdata, 'timezone', 'UTC')

        with session_scope() as session:
            created_tasks = TaskOperations.create_tasks_from_goals(
                session=session,
                user_id=user_id,
                session_id=session_id,
                goals_text=goals_text,
                timezone=timezone
            )

            return {
                "created_tasks": len(created_tasks),
                "tasks": [{
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "category": task.category
                } for task in created_tasks],
                "message": f"Created {len(created_tasks)} tasks from your goals"
            }

    # New method to set preferred time for tasks
    @function_tool()
    async def set_task_time(
        self,
        context: RunContext,
        task_id: str,
        preferred_time: str,
    ) -> dict[str, Any]:
        """Set preferred time for a task.

        Args:
            task_id: ID of the task to update
            preferred_time: Time in HH:MM format (24-hour)
        Returns:
            Updated task information
        """
        # Get user context
        user_id = getattr(context.session.userdata, 'user_id', None)
        if not user_id:
            return {"error": "User not authenticated"}

        timezone = getattr(context.session.userdata, 'timezone', 'UTC')

        # Parse time with intelligent parsing
        try:
            parsed_time, normalized_timezone = TimezoneManager.parse_time_with_timezone(
                preferred_time, timezone
            )
            # Update timezone to the normalized one
            timezone = normalized_timezone
        except Exception as e:
            return {"error": f"Invalid time format: {str(e)}. Try formats like '2:30 PM', '14:30', or 'morning'"}

        with session_scope() as session:
            task = TaskOperations.update_task_time(
                session=session,
                task_id=task_id,
                user_id=user_id,
                preferred_time=parsed_time,
                timezone=timezone
            )

            if not task:
                return {"error": f"Task {task_id} not found"}

            return {
                "id": task.id,
                "title": task.title,
                "reminder_time": task.reminder_time.isoformat() if task.reminder_time is not None else None,
                "message": f"Set reminder time to {preferred_time} for: {task.title}"
            }
