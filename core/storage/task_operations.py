"""
Database Operations for Task Management

Provides CRUD operations for tasks with proper error handling and timezone support.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, update

from .models import Task, UserSession
from .database import session_scope
from .timezone_utils import TimezoneManager

logger = logging.getLogger(__name__)


class TaskOperations:
    """Database operations for task management with timezone awareness."""

    @staticmethod
    def create_task(
        session: Session,
        user_id: str,
        session_id: Optional[str] = None,
        title: str = "",
        description: Optional[str] = None,
        priority: int = 3,
        due_date: Optional[date] = None,
        preferred_time: Optional[time] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        task_metadata: Optional[Dict[str, Any]] = None,
        timezone: str = "UTC"
    ) -> Task:
        """
        Create a new task in the database.

        Args:
            session: Database session
            user_id: User's Clerk ID
            session_id: Optional session ID that created this task
            title: Task title
            description: Optional detailed description
            priority: Priority level (1=highest, 5=lowest)
            due_date: Due date (if not provided, defaults to today)
            preferred_time: Preferred time for the task
            category: Task category
            tags: Optional list of tags
            task_metadata: Additional metadata
            timezone: User's timezone for proper time handling

        Returns:
            Created Task object
        """
        if not due_date:
            due_date = date.today()

        # Combine preferred time with due date if provided
        reminder_time = None
        if preferred_time:
            # Create timezone-aware datetime
            reminder_time = TimezoneManager.create_datetime_with_timezone(
                due_date, preferred_time, timezone
            )

        task = Task(
            user_id=user_id,
            created_by_session_id=session_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            reminder_time=reminder_time,
            category=category,
            tags=tags or [],
            task_metadata={
                **(task_metadata or {}),
                "timezone": timezone,
                "created_via": "agent_interaction"
            },
            status="pending"
        )

        session.add(task)
        session.flush()  # Get the ID without committing
        logger.info(f"Created task {task.id} for user {user_id}: {title}")
        return task

    @staticmethod
    def create_tasks_from_goals(
        session: Session,
        user_id: str,
        session_id: Optional[str] = None,
        goals_text: str = "",
        timezone: str = "UTC"
    ) -> List[Task]:
        """
        Intelligently parse user goals text and create individual tasks.
        Enhanced to handle numbered lists and extract time information.

        Args:
            session: Database session
            user_id: User's Clerk ID
            session_id: Session ID
            goals_text: Raw text from user containing their goals
            timezone: User's timezone

        Returns:
            List of created Task objects
        """
        if not goals_text.strip():
            return []

        # Enhanced goal parsing - handle numbered lists and time extraction
        goals = []

        # First, extract any time information that applies to the entire text
        global_time_info = None
        time_pattern = r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)'
        time_match = re.search(time_pattern, goals_text, re.IGNORECASE)
        if time_match:
            global_time_info = time_match.group(1).strip()

        # Enhanced parsing for mixed content - handle numbered lists better
        # First check if this looks like a numbered list
        if re.search(r'\d+[\)\.]\s*', goals_text):
            # Remove common prefixes
            cleaned_text = re.sub(r'^Tasks for tomorrow:\s*', '', goals_text.strip())

            # Split by numbered patterns
            parts = re.split(r'\s*(\d+)\)\s*', cleaned_text)

            # Extract the actual task texts (skip the numbers)
            for i in range(2, len(parts), 2):
                if i < len(parts):
                    task_text = parts[i].strip()
                    # Remove any trailing content after the next number or "Meeting"
                    task_text = re.split(r'\s*(?=\d+\)|Meeting|at)', task_text)[0].strip()
                    if task_text and len(task_text) > 5:
                        goals.append(task_text)

            # Also extract the meeting part if present
            meeting_match = re.search(r'Meeting with ([^.]+?)(?:\s*at|$)', cleaned_text)
            if meeting_match:
                meeting_text = f"Meeting with {meeting_match.group(1).strip()}"
                goals.append(meeting_text)
        else:
            # Fallback to line-by-line parsing for other formats
            lines = goals_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check for bullet points
                for bullet in ['•', '-', '*', '·']:
                    if line.startswith(bullet):
                        goal_text = line[len(bullet):].strip()
                        if goal_text:
                            goals.append(goal_text)
                        break
                else:
                    # If no clear delimiters but has multiple sentences, split by periods
                    if '.' in line and len(line.split('.')) > 1:
                        sentences = line.split('.')
                        for sentence in sentences:
                            sentence = sentence.strip()
                            # Skip very short fragments and time references
                            if (sentence and len(sentence) > 5 and
                                not sentence.lower().startswith(('meeting', 'at '))):
                                goals.append(sentence)
                    else:
                        # Single goal
                        goals.append(line)

        # Remove duplicates and clean up
        goals = list(dict.fromkeys(goals))  # Remove duplicates while preserving order

        # If no clear delimiters found, treat as single goal
        if not goals:
            goals = [goals_text.strip()]

        created_tasks = []
        for i, goal in enumerate(goals):
            # Extract time information specific to this goal
            goal_time = None
            time_match = re.search(time_pattern, goal, re.IGNORECASE)
            if time_match:
                goal_time = time_match.group(1).strip()
                # Remove time from goal text
                goal = re.sub(time_pattern, '', goal, flags=re.IGNORECASE).strip()

            # If no specific time for this goal, use global time
            if not goal_time and global_time_info:
                goal_time = global_time_info

            # Determine priority based on keywords
            priority = 3  # default
            goal_lower = goal.lower()

            if any(word in goal_lower for word in ['urgent', 'asap', 'critical', 'important', 'deadline']):
                priority = 1
            elif any(word in goal_lower for word in ['soon', 'priority', 'key', 'meeting']):
                priority = 2

            # Determine category based on keywords
            category = "general"
            if any(word in goal_lower for word in ['work', 'meeting', 'project', 'call', 'presentation', 'report', 'research']):
                category = "work"
            elif any(word in goal_lower for word in ['health', 'exercise', 'gym', 'run', 'tennis', 'sport']):
                category = "health"
            elif any(word in goal_lower for word in ['shopping', 'buy', 'purchase', 'personal']):
                category = "personal"
            elif any(word in goal_lower for word in ['marketing', 'plan', 'challenge', 'hustle']):
                category = "work"  # Business-related

            # Convert goal_time string to time object if present
            preferred_time_obj = None
            if goal_time:
                try:
                    preferred_time_obj = TimezoneManager.parse_time_with_timezone(goal_time, timezone)[0]
                except Exception as e:
                    logger.warning(f"Failed to parse time '{goal_time}': {e}")
                    preferred_time_obj = None

            # Create the task
            task = TaskOperations.create_task(
                session=session,
                user_id=user_id,
                session_id=session_id,
                title=goal,
                priority=priority,
                category=category,
                preferred_time=preferred_time_obj,
                timezone=timezone,
                task_metadata={
                    "source": "goal_parsing",
                    "original_text": goal,
                    "parsing_method": "enhanced_delimiter_split",
                    "goal_index": i,
                    "extracted_time": goal_time
                }
            )
            created_tasks.append(task)

        logger.info(f"Created {len(created_tasks)} tasks from goals for user {user_id}")
        return created_tasks

    @staticmethod
    def get_user_tasks(
        session: Session,
        user_id: str,
        category: Optional[str] = None,
        priority_min: Optional[int] = None,
        completed: Optional[bool] = None,
        limit: int = 20
    ) -> List[Task]:
        """Get tasks for a user with optional filtering."""
        query = session.query(Task).filter(Task.user_id == user_id)

        if category:
            query = query.filter(Task.category == category)

        if priority_min is not None:
            query = query.filter(Task.priority <= priority_min)

        if completed is not None:
            status = "completed" if completed else "pending"
            query = query.filter(Task.status == status)

        # Sort by priority then by created date
        query = query.order_by(Task.priority, Task.created_at.desc())

        return query.limit(limit).all()

    @staticmethod
    def get_today_tasks(session: Session, user_id: str) -> List[Task]:
        """Get tasks due today."""
        today = date.today()
        return session.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.due_date == today,
                Task.status != "completed"
            )
        ).order_by(Task.priority).all()

    @staticmethod
    def complete_task(session: Session, task_id: str, user_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        task = session.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()

        if task:
            # Update task status and timestamps
            setattr(task, 'status', "completed")
            setattr(task, 'completed_at', datetime.utcnow())
            setattr(task, 'updated_at', datetime.utcnow())
            session.commit()
            logger.info(f"Completed task {task_id} for user {user_id}")

        return task

    @staticmethod
    def update_task_time(
        session: Session,
        task_id: str,
        user_id: str,
        preferred_time: time,
        timezone: str = "UTC"
    ) -> Optional[Task]:
        """Update a task's preferred time."""
        task = session.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()

        if task:
            # Create timezone-aware datetime
            task_due_date = getattr(task, 'due_date')
            setattr(task, 'reminder_time', TimezoneManager.create_datetime_with_timezone(
                task_due_date, preferred_time, timezone
            ))

            # Get current metadata and update it
            current_metadata = getattr(task, 'task_metadata', {}) or {}
            setattr(task, 'task_metadata', {
                **current_metadata,
                "timezone": timezone,
                "time_updated": datetime.utcnow().isoformat()
            })

            setattr(task, 'updated_at', datetime.utcnow())
            session.commit()
            logger.info(f"Updated time for task {task_id} to {preferred_time}")

        return task

    @staticmethod
    def get_task_by_id(session: Session, task_id: str, user_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        return session.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()

    @staticmethod
    def delete_task(session: Session, task_id: str, user_id: str) -> bool:
        """Delete a task."""
        task = session.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()

        if task:
            session.delete(task)
            session.commit()
            logger.info(f"Deleted task {task_id} for user {user_id}")
            return True

        return False

    @staticmethod
    def get_tasks_by_session(
        session: Session,
        session_id: str,
        user_id: str
    ) -> List[Task]:
        """Get all tasks created in a specific session."""
        return session.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.created_by_session_id == session_id
            )
        ).order_by(Task.created_at).all()

    @staticmethod
    def update_task_priority(
        session: Session,
        task_id: str,
        user_id: str,
        priority: int
    ) -> Optional[Task]:
        """Update a task's priority."""
        task = session.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()

        if task:
            setattr(task, 'priority', priority)
            setattr(task, 'updated_at', datetime.utcnow())
            session.commit()
            logger.info(f"Updated priority for task {task_id} to {priority}")

        return task
