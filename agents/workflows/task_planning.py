"""
Task Planning Workflow for Zeno

Handles complex task management and planning workflows.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, date

from livekit.agents import RunContext


class TaskPlanningWorkflow:
    """
    Workflow for task planning and management.
    
    Handles:
    - Task prioritization
    - Daily task planning
    - Project breakdown
    - Deadline management
    """
    
    def __init__(self):
        self.name = "TaskPlanningWorkflow"
        self.description = "Manages task planning and prioritization"
    
    async def plan_daily_tasks(
        self,
        context: RunContext,
        existing_tasks: List[Dict[str, Any]],
        calendar_events: List[Dict[str, Any]],
        priority_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Plan daily tasks based on existing tasks and calendar.
        
        Args:
            context: Runtime context
            existing_tasks: List of existing tasks
            calendar_events: Calendar events for the day
            priority_level: Priority level for planning
            
        Returns:
            Planned task structure
        """
        # Simple task planning logic
        planned_tasks = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "scheduled_tasks": [],
            "suggested_time_blocks": []
        }
        
        # Categorize existing tasks by priority
        for task in existing_tasks:
            priority = task.get("priority", "medium").lower()
            task_list = planned_tasks.get(f"{priority}_priority", planned_tasks["medium_priority"])
            task_list.append(task)
        
        # Find time blocks between calendar events
        available_blocks = self._find_available_time_blocks(calendar_events)
        planned_tasks["suggested_time_blocks"] = available_blocks
        
        return {
            "planned_tasks": planned_tasks,
            "total_tasks": len(existing_tasks),
            "available_time_blocks": len(available_blocks),
            "planning_date": datetime.now().isoformat()
        }
    
    async def prioritize_tasks(
        self,
        context: RunContext,
        tasks: List[Dict[str, Any]],
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Prioritize tasks based on various criteria.
        
        Args:
            context: Runtime context
            tasks: List of tasks to prioritize
            criteria: Prioritization criteria
            
        Returns:
            Prioritized task list
        """
        # Simple prioritization logic
        criteria = criteria or {
            "deadline_weight": 0.4,
            "importance_weight": 0.3,
            "effort_weight": 0.2,
            "dependency_weight": 0.1
        }
        
        # Score and sort tasks
        scored_tasks = []
        for task in tasks:
            score = self._calculate_task_score(task, criteria)
            task_with_score = task.copy()
            task_with_score["priority_score"] = score
            scored_tasks.append(task_with_score)
        
        # Sort by priority score (highest first)
        scored_tasks.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return scored_tasks
    
    async def break_down_project(
        self,
        context: RunContext,
        project_description: str,
        estimated_duration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Break down a complex project into manageable tasks.
        
        Args:
            context: Runtime context
            project_description: Description of the project
            estimated_duration: Estimated time to complete
            
        Returns:
            Project breakdown structure
        """
        # Simple project breakdown logic
        # In a real implementation, this could use AI to intelligently break down projects
        
        breakdown = {
            "project_name": project_description,
            "estimated_duration": estimated_duration,
            "phases": [
                {
                    "phase": "Planning",
                    "tasks": [
                        "Define project scope",
                        "Identify requirements",
                        "Create timeline"
                    ],
                    "estimated_time": "1-2 days"
                },
                {
                    "phase": "Execution",
                    "tasks": [
                        "Implement main features",
                        "Create deliverables",
                        "Regular progress reviews"
                    ],
                    "estimated_time": "70% of total time"
                },
                {
                    "phase": "Completion",
                    "tasks": [
                        "Quality review",
                        "Final testing",
                        "Documentation",
                        "Project closure"
                    ],
                    "estimated_time": "20% of total time"
                }
            ],
            "total_estimated_tasks": 10,
            "created_at": datetime.now().isoformat()
        }
        
        return breakdown
    
    def _find_available_time_blocks(self, calendar_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find available time blocks between calendar events."""
        # Simple implementation - find gaps between events
        available_blocks = []
        
        if not calendar_events:
            # If no events, suggest standard work blocks
            return [
                {"start": "09:00", "end": "10:30", "duration": "1.5 hours"},
                {"start": "10:45", "end": "12:00", "duration": "1.25 hours"},
                {"start": "14:00", "end": "15:30", "duration": "1.5 hours"},
                {"start": "15:45", "end": "17:00", "duration": "1.25 hours"}
            ]
        
        # For now, return some default blocks
        # In a real implementation, this would analyze calendar gaps
        available_blocks = [
            {"start": "Morning", "duration": "2 hours", "suggested_for": "High-focus tasks"},
            {"start": "Afternoon", "duration": "1.5 hours", "suggested_for": "Meetings and collaboration"}
        ]
        
        return available_blocks
    
    def _calculate_task_score(self, task: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """Calculate priority score for a task."""
        score = 0.0
        
        # Deadline urgency (higher score for sooner deadlines)
        deadline = task.get("deadline")
        if deadline:
            # Simple scoring based on deadline
            score += criteria.get("deadline_weight", 0.4) * 0.8
        
        # Importance level
        importance = task.get("importance", "medium")
        importance_scores = {"high": 1.0, "medium": 0.6, "low": 0.3}
        score += criteria.get("importance_weight", 0.3) * importance_scores.get(importance, 0.5)
        
        # Effort (lower effort = higher score for quick wins)
        effort = task.get("effort", "medium")
        effort_scores = {"low": 1.0, "medium": 0.6, "high": 0.3}
        score += criteria.get("effort_weight", 0.2) * effort_scores.get(effort, 0.5)
        
        # Dependencies (tasks without dependencies score higher)
        has_dependencies = task.get("dependencies", [])
        dependency_score = 0.3 if has_dependencies else 1.0
        score += criteria.get("dependency_weight", 0.1) * dependency_score
        
        return score
