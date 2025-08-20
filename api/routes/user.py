"""
User API routes for authenticated user data.

Provides endpoints for user profile, preferences, and Zeno-specific data.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.middleware.clerk_auth import get_current_user
from core.storage import get_database_session, User, Task, Briefing, UserSession


router = APIRouter()


@router.get("/me")
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_database_session)
) -> Dict[str, Any]:
    """Get current user's profile information."""
    clerk_user_id = current_user["clerk_user_id"]
    
    # Get user from database
    db_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found in database")
    
    return {
        "clerk_user_id": db_user.clerk_user_id,
        "email": db_user.email,
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "created_at": db_user.created_at,
        "last_active_at": db_user.last_active_at,
        "preferences": db_user.preferences,
        "timezone": db_user.timezone
    }


@router.get("/tasks")
async def get_user_tasks(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_database_session),
    completed: bool = False,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get current user's tasks."""
    clerk_user_id = current_user["clerk_user_id"]
    
    # Get user's tasks
    tasks = db.query(Task).filter(
        Task.user_id == clerk_user_id,
        Task.status == ("completed" if completed else "pending")
    ).limit(limit).all()
    
    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "category": task.category,
            "status": task.status,
            "due_date": task.due_date,
            "created_at": task.created_at,
            "task_metadata": task.task_metadata
        }
        for task in tasks
    ]


@router.post("/tasks")
async def create_user_task(
    task_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_database_session)
) -> Dict[str, Any]:
    """Create a new task for the current user."""
    clerk_user_id = current_user["clerk_user_id"]
    
    # Create new task
    new_task = Task(
        user_id=clerk_user_id,
        title=task_data.get("title", ""),
        description=task_data.get("description"),
        priority=task_data.get("priority", 3),
        category=task_data.get("category", "general"),
        status="pending",
        due_date=task_data.get("due_date"),
        task_metadata=task_data.get("metadata", {})
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return {
        "id": new_task.id,
        "title": new_task.title,
        "description": new_task.description,
        "priority": new_task.priority,
        "category": new_task.category,
        "status": new_task.status,
        "created_at": new_task.created_at,
        "message": "Task created successfully"
    }


@router.get("/briefings")
async def get_user_briefings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_database_session),
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get current user's recent briefings."""
    clerk_user_id = current_user["clerk_user_id"]
    
    # Get user's briefings
    briefings = db.query(Briefing).filter(
        Briefing.user_id == clerk_user_id
    ).order_by(Briefing.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": briefing.id,
            "briefing_date": briefing.briefing_date,
            "briefing_type": briefing.briefing_type,
            "summary": briefing.summary,
            "user_goals": briefing.user_goals,
            "created_at": briefing.created_at
        }
        for briefing in briefings
    ]


@router.get("/sessions")
async def get_user_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_database_session),
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Get current user's recent agent sessions."""
    clerk_user_id = current_user["clerk_user_id"]
    
    # Get user's recent sessions
    sessions = db.query(UserSession).filter(
        UserSession.user_id == clerk_user_id
    ).order_by(UserSession.started_at.desc()).limit(limit).all()
    
    return [
        {
            "id": session.id,
            "session_type": session.session_type,
            "agent_type": session.agent_type,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "is_active": session.is_active
        }
        for session in sessions
    ]


@router.post("/test-auth")
async def test_authentication(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Test endpoint to verify authentication is working."""
    return {
        "message": "Authentication successful!",
        "user": {
            "clerk_user_id": current_user["clerk_user_id"],
            "email": current_user["email"],
            "name": f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
        },
        "timestamp": "2025-08-20T12:00:00Z"
    }
