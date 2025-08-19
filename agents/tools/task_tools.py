"""
Task Management Tools for Zeno Agent

Tools for managing daily tasks and to-dos within Zeno.
"""

from __future__ import annotations

from typing import Any, Optional, List
from datetime import datetime, date

from livekit.agents import function_tool, RunContext

# Note: These will connect to the database layer when implemented
# For now, using in-memory storage as placeholder


class TaskTools:
    """Task management tools for Zeno agent."""
    
    def __init__(self):
        # Placeholder in-memory storage - will be replaced with database
        self._tasks = {}
        self._task_counter = 1

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
            due_date: Optional due date in ISO format
            category: Task category (work, personal, health, etc.)
        Returns:
            Created task information
        """
        task_id = str(self._task_counter)
        self._task_counter += 1
        
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "category": category,
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        self._tasks[task_id] = task
        return task

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
        tasks = list(self._tasks.values())
        
        # Apply filters
        if category:
            tasks = [t for t in tasks if t.get("category") == category]
        
        if priority_min:
            tasks = [t for t in tasks if t.get("priority", 5) <= priority_min]
        
        if completed is not None:
            tasks = [t for t in tasks if t.get("completed") == completed]
        
        # Sort by priority (lower number = higher priority) then by created date
        tasks.sort(key=lambda t: (t.get("priority", 5), t.get("created_at", "")))
        
        return tasks[:limit]

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
        if task_id not in self._tasks:
            return {"error": f"Task {task_id} not found"}
        
        self._tasks[task_id]["completed"] = True
        self._tasks[task_id]["updated_at"] = datetime.now().isoformat()
        self._tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        return self._tasks[task_id]

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
        today = date.today().isoformat()
        
        all_tasks = await self.list_tasks(context, completed=False)
        today_tasks = []
        
        for task in all_tasks:
            due_date = task.get("due_date")
            if due_date and due_date.startswith(today):
                today_tasks.append(task)
        
        return {
            "today_tasks": today_tasks,
            "total_count": len(today_tasks),
            "has_overdue": False  # TODO: Implement overdue logic
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
        if task_id not in self._tasks:
            return {"error": f"Task {task_id} not found"}
        
        self._tasks[task_id]["priority"] = priority
        self._tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        return self._tasks[task_id]

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
        if task_id not in self._tasks:
            return {"error": f"Task {task_id} not found"}
        
        deleted_task = self._tasks.pop(task_id)
        return {"message": f"Task '{deleted_task['title']}' deleted successfully"}

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
        from core.integrations.google.drive import DriveService
        
        try:
            drive_service = DriveService()
            
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
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create task document: {str(e)}"
            }
